import logging
import random
import time

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.valuation import ScrapedCar

logger = logging.getLogger(__name__)

BASE_URL = "https://www.arabam.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BRAND_SLUGS = {
    "BMW": "bmw",
    "Mercedes": "mercedes-benz",
    "Audi": "audi",
    "Volkswagen": "volkswagen",
    "Toyota": "toyota",
    "Honda": "honda",
    "Ford": "ford",
    "Renault": "renault",
    "Fiat": "fiat",
    "Hyundai": "hyundai",
    "Opel": "opel",
    "Peugeot": "peugeot",
    "Citroen": "citroen",
    "Nissan": "nissan",
    "Kia": "kia",
    "Volvo": "volvo",
    "Skoda": "skoda",
    "Dacia": "dacia",
}


def _parse_listing_page(html: str) -> list[dict]:
    """Parse a listing page and extract car links."""
    soup = BeautifulSoup(html, "lxml")
    listings = []

    for item in soup.select("tr.listing-list-item, div.listing-card"):
        link = item.select_one("a[href*='/ilan/']")
        if not link:
            continue

        href = link.get("href", "")
        if href and not href.startswith("http"):
            href = BASE_URL + href

        price_el = item.select_one("span.listing-price, div.listing-price-new")
        price_text = price_el.get_text(strip=True) if price_el else ""
        price = _parse_price(price_text)

        listings.append({"url": href, "price": price})

    return listings


def _parse_price(text: str) -> float | None:
    """Extract numeric price from text like '450.000 TL'."""
    if not text:
        return None
    cleaned = text.replace("TL", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_detail_page(html: str) -> dict:
    """Extract car details from a detail page."""
    soup = BeautifulSoup(html, "lxml")
    info = {}

    for row in soup.select("div.property-item, li.property-item"):
        label_el = row.select_one("span.property-key, div.property-key")
        value_el = row.select_one("span.property-value, div.property-value")
        if label_el and value_el:
            key = label_el.get_text(strip=True).lower()
            val = value_el.get_text(strip=True)
            info[key] = val

    # Extract image
    img_el = soup.select_one("img.detail-image, img.gallery-image, div.image-gallery img")
    if img_el:
        info["image_url"] = img_el.get("src", "")

    return info


def _map_fields(raw: dict) -> dict:
    """Map Turkish field names to model fields."""
    field_map = {
        "marka": "brand",
        "seri": "model",
        "model": "model",
        "yıl": "year",
        "kilometre": "mileage",
        "yakıt tipi": "fuel_type",
        "yakıt": "fuel_type",
        "vites tipi": "transmission",
        "vites": "transmission",
        "kasa tipi": "body_type",
        "renk": "color",
        "motor hacmi": "engine_size",
    }

    mapped = {}
    for raw_key, raw_val in raw.items():
        for tr_key, en_key in field_map.items():
            if tr_key in raw_key:
                mapped[en_key] = raw_val
                break

    if "image_url" in raw:
        mapped["image_url"] = raw["image_url"]

    # Parse numeric fields
    if "year" in mapped:
        try:
            mapped["year"] = int(mapped["year"])
        except ValueError:
            mapped.pop("year", None)

    if "mileage" in mapped:
        try:
            cleaned = mapped["mileage"].replace(".", "").replace("km", "").strip()
            mapped["mileage"] = int(cleaned)
        except ValueError:
            mapped.pop("mileage", None)

    return mapped


def scrape_brand(brand: str, max_pages: int = 2, db: Session | None = None) -> list[dict]:
    """Scrape listings for a specific brand from arabam.com."""
    slug = BRAND_SLUGS.get(brand, brand.lower())
    all_cars = []

    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            url = f"{BASE_URL}/ikinci-el/{slug}?page={page}"
            logger.info(f"Scraping: {url}")

            try:
                resp = client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch {url}: {e}")
                continue

            listings = _parse_listing_page(resp.text)

            for listing in listings:
                if not listing.get("url"):
                    continue

                time.sleep(random.uniform(1.5, 3.0))

                try:
                    detail_resp = client.get(listing["url"])
                    detail_resp.raise_for_status()
                except httpx.HTTPError as e:
                    logger.error(f"Failed to fetch detail {listing['url']}: {e}")
                    continue

                details = _parse_detail_page(detail_resp.text)
                mapped = _map_fields(details)
                mapped["source_url"] = listing["url"]
                mapped["price"] = listing.get("price")
                mapped.setdefault("brand", brand)

                if mapped.get("price") and mapped.get("year") and mapped.get("mileage"):
                    all_cars.append(mapped)

                    if db:
                        _save_to_db(mapped, db)

            time.sleep(random.uniform(2.0, 4.0))

    logger.info(f"Scraped {len(all_cars)} cars for {brand}")
    return all_cars


def _save_to_db(car_data: dict, db: Session) -> None:
    """Save a scraped car to the database, skipping duplicates."""
    exists = (
        db.query(ScrapedCar)
        .filter(ScrapedCar.source_url == car_data["source_url"])
        .first()
    )
    if exists:
        return

    car = ScrapedCar(
        source_url=car_data["source_url"],
        brand=car_data.get("brand", ""),
        model=car_data.get("model", ""),
        year=car_data.get("year", 0),
        mileage=car_data.get("mileage", 0),
        fuel_type=car_data.get("fuel_type", ""),
        transmission=car_data.get("transmission", ""),
        price=car_data.get("price", 0),
        color=car_data.get("color"),
        body_type=car_data.get("body_type"),
        image_url=car_data.get("image_url"),
    )
    db.add(car)
    db.commit()


def get_market_data(brand: str, model: str, year: int, db: Session) -> list[ScrapedCar]:
    """Get scraped market data for comparison."""
    query = db.query(ScrapedCar).filter(
        ScrapedCar.brand.ilike(f"%{brand}%"),
        ScrapedCar.model.ilike(f"%{model}%"),
    )

    if year:
        query = query.filter(
            ScrapedCar.year.between(year - 2, year + 2)
        )

    return query.limit(50).all()
