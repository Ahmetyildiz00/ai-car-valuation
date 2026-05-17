import json
import logging
from datetime import datetime, timezone

from redis import Redis

from app.core.broker import broker
from app.core.config import settings
from app.core.database import SessionLocal
from app.scraper.arabam_scraper import BRAND_SLUGS, TOP_MODELS, scrape_brand, scrape_path

logger = logging.getLogger(__name__)

SCRAPE_STATUS_KEY = "admin:scrape_top_models:status"


def _redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _set_status(payload: dict) -> None:
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    _redis().set(SCRAPE_STATUS_KEY, json.dumps(payload), ex=60 * 60 * 24)


def get_scrape_status() -> dict:
    raw = _redis().get(SCRAPE_STATUS_KEY)
    if not raw:
        return {"state": "idle"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"state": "idle"}


def clear_scrape_status() -> None:
    _redis().delete(SCRAPE_STATUS_KEY)


@broker.task(
    task_name="scrape_all_brands",
    schedule=[{"cron": "0 0 * * *"}],
)
async def scrape_all_brands_task() -> dict:
    """Scrape all brands nightly."""
    db = SessionLocal()
    results = {}
    try:
        for brand in BRAND_SLUGS:
            try:
                cars = scrape_brand(brand, max_pages=2, db=db)
                results[brand] = len(cars)
                logger.info(f"Scraped {len(cars)} cars for {brand}")
            except Exception as e:
                logger.error(f"Failed to scrape {brand}: {e}")
                results[brand] = f"error: {str(e)}"
    finally:
        db.close()

    logger.info(f"Nightly scrape completed: {results}")
    return results


@broker.task(task_name="scrape_single_brand")
async def scrape_single_brand_task(brand: str, max_pages: int = 2) -> dict:
    """Scrape a single brand."""
    db = SessionLocal()
    try:
        cars = scrape_brand(brand, max_pages=max_pages, db=db)
        return {"brand": brand, "scraped": len(cars)}
    finally:
        db.close()


@broker.task(task_name="scrape_top_models")
async def scrape_top_models_task(per_model: int = 500) -> dict:
    """Scrape ~`per_model` listings for each of TOP_MODELS. Admin-triggered."""
    db = SessionLocal()
    total_target = per_model * len(TOP_MODELS)
    aggregate = 0
    per_model_results: dict[str, int] = {}

    _set_status({
        "state": "running",
        "per_model_target": per_model,
        "total_target": total_target,
        "scraped_total": 0,
        "current": None,
        "completed_models": [],
        "errors": {},
    })

    try:
        for idx, (brand, model, slug) in enumerate(TOP_MODELS, start=1):
            label = f"{brand} {model}"
            _set_status({
                "state": "running",
                "per_model_target": per_model,
                "total_target": total_target,
                "scraped_total": aggregate,
                "current": {"index": idx, "total": len(TOP_MODELS), "label": label},
                "completed_models": list(per_model_results.keys()),
                "errors": {},
            })

            try:
                cars = scrape_path(slug, brand=brand, max_listings=per_model, db=db)
                per_model_results[label] = len(cars)
                aggregate += len(cars)
                logger.info(f"Top-models scrape: {label} -> {len(cars)}")
            except Exception as e:
                logger.error(f"Top-models scrape failed for {label}: {e}")
                per_model_results[label] = 0
                _set_status({
                    "state": "running",
                    "per_model_target": per_model,
                    "total_target": total_target,
                    "scraped_total": aggregate,
                    "current": {"index": idx, "total": len(TOP_MODELS), "label": label},
                    "completed_models": list(per_model_results.keys()),
                    "errors": {label: str(e)},
                })
    finally:
        db.close()

    _set_status({
        "state": "completed",
        "per_model_target": per_model,
        "total_target": total_target,
        "scraped_total": aggregate,
        "per_model_results": per_model_results,
    })
    return {"total": aggregate, "per_model": per_model_results}
