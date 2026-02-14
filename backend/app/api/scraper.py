from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.valuation import ScrapedCar
from app.scraper.arabam_scraper import BRAND_SLUGS, scrape_brand

router = APIRouter(prefix="/scraper", tags=["Scraper"])


@router.post("/scrape/{brand}")
def trigger_scrape(
    brand: str,
    background_tasks: BackgroundTasks,
    max_pages: int = 1,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger a background scrape for a specific brand."""
    if brand not in BRAND_SLUGS:
        return {"error": f"Unknown brand. Available: {list(BRAND_SLUGS.keys())}"}

    background_tasks.add_task(scrape_brand, brand, max_pages, db)
    return {"message": f"Scraping started for {brand}", "max_pages": max_pages}


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
