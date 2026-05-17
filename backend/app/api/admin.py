from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.models.valuation import ScrapedCar
from app.tasks.scraper_tasks import (
    get_scrape_status,
    scrape_top_models_task,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/scrape-top-models", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scrape_top_models(
    per_model: int = 500,
    current_user: User = Depends(require_admin),
):
    """Kick off a background scrape of top brand/model pairs."""
    status_now = get_scrape_status()
    if status_now.get("state") == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A scrape job is already running",
        )
    await scrape_top_models_task.kiq(per_model=per_model)
    return {"queued": True, "per_model": per_model}


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
