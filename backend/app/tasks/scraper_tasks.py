import logging

from app.core.broker import broker
from app.core.database import SessionLocal
from app.scraper.arabam_scraper import BRAND_SLUGS, scrape_brand

logger = logging.getLogger(__name__)


@broker.task(
    task_name="scrape_all_brands",
    schedule=[{"cron": "0 0 * * *"}],  # Her gece 00:00
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
