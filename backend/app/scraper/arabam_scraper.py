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
    """Parse a listing page and extract car data directly from listing rows."""
    soup = BeautifulSoup(html, "lxml")
    listings = []

    for item in soup.select("tr.listing-list-item"):
        link = item.select_one("a[href*='/ilan/']")
        if not link:
            continue

        href = link.get("href", "")
        if href and not href.startswith("http"):
            href = BASE_URL + href

        price_el = item.select_one("span.listing-price, span[class*='listing-price']")
        price_text = price_el.get_text(strip=True) if price_el else ""
        price = _parse_price(price_text)

        # Extract year, mileage, color from td.listing-text (in order)
        text_tds = item.select("td.listing-text")
        year = None
        mileage = None
        color = None
        if len(text_tds) >= 1:
            try:
                year = int(text_tds[0].get_text(strip=True))
            except (ValueError, IndexError):
                pass
        if len(text_tds) >= 2:
            raw_km = text_tds[1].get_text(strip=True).replace(".", "").replace("km", "").strip()
            try:
                mileage = int(raw_km)
            except (ValueError, IndexError):
                pass
        if len(text_tds) >= 3:
            color = text_tds[2].get_text(strip=True)

        # Extract thumbnail image
        img_el = item.select_one("img.listing-image")
        image_url = None
        if img_el:
            src = img_el.get("data-src") or img_el.get("src", "")
            if src and src.startswith("http") and "noImage" not in src:
                image_url = src

        # Extract model name
        model_td = item.select_one("td.listing-modelname")
        model_name = model_td.get_text(strip=True) if model_td else ""

        listings.append({
            "url": href,
            "price": price,
            "year": year,
            "mileage": mileage,
            "color": color,
            "image_url": image_url,
            "model_name": model_name,
        })

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

    # Extract image — arabam.com detail page
    img_el = soup.select_one(
        "div.photo-holder img, "
        "div.gallery-container img, "
        "img#main-photo, "
        "div.swiper-slide img, "
        "div.detail-photo img"
    )
    if img_el:
        src = img_el.get("src") or img_el.get("data-src") or img_el.get("data-lazy", "")
        if src and src.startswith("http"):
            info["image_url"] = src

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
        "vites tipi": "transmission",
        "vites": "transmission",
        "kasa tipi": "body_type",
        "renk": "color",
        "motor hacmi": "engine_size",
        "motor gücü": "engine_power",
        "boya-değişen": "damage_records",
        "hasar kaydı": "damage_records",
        "tramer": "damage_records",
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
            url = f"{BASE_URL}/ikinci-el/otomobil/{slug}?page={page}"
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

                # Start with listing-level data (year, mileage, color, image already extracted)
                mapped = {
                    "source_url": listing["url"],
                    "price": listing.get("price"),
                    "year": listing.get("year"),
                    "mileage": listing.get("mileage"),
                    "color": listing.get("color"),
                    "image_url": listing.get("image_url"),
                    "brand": brand,
                }

                # Parse model from listing model name (e.g. "BMW 4 Serisi 420d xDrive")
                model_name = listing.get("model_name", "")
                if model_name:
                    parts = model_name.split(" ", 2)
                    if len(parts) >= 3:
                        mapped["model"] = " ".join(parts[1:])
                    elif len(parts) == 2:
                        mapped["model"] = parts[1]

                # Fetch detail page for extra fields (fuel, transmission, body_type, etc.)
                time.sleep(random.uniform(0.3, 0.7))
                try:
                    detail_resp = client.get(listing["url"], timeout=10)
                    detail_resp.raise_for_status()
                    details = _parse_detail_page(detail_resp.text)
                    detail_mapped = _map_fields(details)
                    # Merge detail fields, don't overwrite listing fields
                    for k, v in detail_mapped.items():
                        if k not in mapped or mapped[k] is None:
                            mapped[k] = v
                except httpx.HTTPError as e:
                    logger.warning(f"Detail fetch failed for {listing['url']}: {e}")

                mapped.setdefault("brand", brand)

                if mapped.get("price") and mapped.get("year") and mapped.get("mileage"):
                    all_cars.append(mapped)
                    if db:
                        _save_to_db(mapped, db)

            time.sleep(random.uniform(0.5, 1.0))

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
        engine_power=car_data.get("engine_power"),
        damage_records=car_data.get("damage_records"),
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
