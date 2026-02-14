from fastapi import APIRouter, Depends
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.valuation import ScrapedCar
from app.scraper.arabam_scraper import BRAND_SLUGS
from app.tasks.scraper_tasks import scrape_all_brands_task, scrape_single_brand_task

router = APIRouter(prefix="/scraper", tags=["Scraper"])


@router.post("/scrape/{brand}")
async def trigger_scrape(
    brand: str,
    max_pages: int = 1,
    current_user: User = Depends(get_current_user),
):
    """Taskiq üzerinden tek marka scrape başlat."""
    if brand not in BRAND_SLUGS:
        return {"error": f"Unknown brand. Available: {list(BRAND_SLUGS.keys())}"}

    task = await scrape_single_brand_task.kiq(brand=brand, max_pages=max_pages)
    return {"message": f"Scrape task queued for {brand}", "task_id": task.task_id}


@router.post("/scrape-all")
async def trigger_scrape_all(
    current_user: User = Depends(get_current_user),
):
    """Start a Taskiq task to scrape all brands"""
    task = await scrape_all_brands_task.kiq()
    return {"message": "Scrape all brands task queued", "task_id": task.task_id}


@router.get("/brands")
def list_brands():
    """List available brands for scraping."""
    return {"brands": list(BRAND_SLUGS.keys())}


@router.get("/stats")
def scraper_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get statistics about scraped data."""
    total = db.query(ScrapedCar).count()
    brands = (
        db.query(ScrapedCar.brand, sa_func.count(ScrapedCar.id))
        .group_by(ScrapedCar.brand)
        .all()
    )
    return {
        "total_cars": total,
        "by_brand": {brand: count for brand, count in brands},
    }
