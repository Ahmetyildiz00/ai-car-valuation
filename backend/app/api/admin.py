from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.models.valuation import ScrapedCar
from app.services.valuation import ml_model
from app.tasks.model_tasks import (
    backfill_embeddings_task,
    clear_embed_status,
    clear_train_status,
    get_embed_status,
    get_train_status,
    train_model_task,
)
from app.tasks.scraper_tasks import (
    clear_scrape_status,
    get_scrape_status,
    scrape_top_models_task,
)

router = APIRouter(prefix="/admin", tags=["Admin"])

STALE_AFTER = timedelta(minutes=5)


def _is_stale(status_payload: dict) -> bool:
    ts = status_payload.get("updated_at")
    if not ts:
        return True
    try:
        last = datetime.fromisoformat(ts)
    except ValueError:
        return True
    return datetime.now(timezone.utc) - last > STALE_AFTER


@router.post("/scrape-top-models", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scrape_top_models(
    per_model: int = 500,
    current_user: User = Depends(require_admin),
):
    """Kick off a background scrape of top brand/model pairs."""
    status_now = get_scrape_status()
    if status_now.get("state") == "running" and not _is_stale(status_now):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A scrape job is already running",
        )
    await scrape_top_models_task.kiq(per_model=per_model)
    return {"queued": True, "per_model": per_model}


@router.post("/scrape-reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_scrape_status(current_user: User = Depends(require_admin)):
    """Force-clear a stuck scrape status (e.g. after worker crash)."""
    clear_scrape_status()


@router.get("/scrape-status")
def scrape_status(current_user: User = Depends(require_admin)):
    return get_scrape_status()


@router.get("/stats")
def admin_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return {
        "users": db.query(User).count(),
        "scraped_cars": db.query(ScrapedCar).count(),
    }


@router.post("/train-model", status_code=status.HTTP_202_ACCEPTED)
async def trigger_train_model(current_user: User = Depends(require_admin)):
    status_now = get_train_status()
    if status_now.get("state") == "running" and not _is_stale(status_now):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A training job is already running",
        )
    await train_model_task.kiq()
    return {"queued": True}


@router.post("/train-reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_train_status(current_user: User = Depends(require_admin)):
    clear_train_status()


@router.get("/train-status")
def train_status(current_user: User = Depends(require_admin)):
    return get_train_status()


@router.get("/model-info")
def model_info(current_user: User = Depends(require_admin)):
    # force-reload so a freshly-trained model (written by the worker) is
    # picked up by the backend process on the next request.
    loaded = ml_model.load_model(force=True)
    if loaded is None:
        return {"loaded": False}
    return {"loaded": True, **loaded[1].__dict__}


@router.post("/backfill-embeddings", status_code=status.HTTP_202_ACCEPTED)
async def trigger_backfill_embeddings(
    force: bool = False,
    current_user: User = Depends(require_admin),
):
    status_now = get_embed_status()
    if status_now.get("state") == "running" and not _is_stale(status_now):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An embedding backfill job is already running",
        )
    await backfill_embeddings_task.kiq(force=force)
    return {"queued": True, "force": force}


@router.post("/backfill-embeddings-reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_backfill_embeddings(current_user: User = Depends(require_admin)):
    clear_embed_status()


@router.get("/backfill-embeddings-status")
def backfill_embeddings_status(current_user: User = Depends(require_admin)):
    return get_embed_status()
