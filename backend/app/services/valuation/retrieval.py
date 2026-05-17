"""Find comparable scraped listings for a target car.

Strategy (progressively widens the net until enough samples):
    1. Strict: brand + model + year±2 + fuel + transmission + mileage band
    2. Loosen: drop fuel/transmission constraints
    3. Loosen: widen year window to ±4, drop mileage band
    4. Loosen: same brand+model only
    5. Fallback: same brand only (semantic-similar models)

After retrieval, prices are filtered for outliers via a robust
median ± 3 * MAD criterion (Median Absolute Deviation).
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Sequence

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.valuation import ScrapedCar
from app.services.valuation.schemas import CarFeatures

MIN_SAMPLES = 10
TARGET_SAMPLES = 50
MAD_K = 3.0


@dataclass
class RetrievalResult:
    cars: list[ScrapedCar]
    strategy: str  # which level matched
    n_raw: int
    n_after_outlier: int


def _mileage_band(mileage: int, pct: float = 0.4) -> tuple[int, int]:
    delta = max(int(mileage * pct), 20_000)
    return max(0, mileage - delta), mileage + delta


def _query_base(db: Session, *, brand: str, model: str):
    return db.query(ScrapedCar).filter(
        ScrapedCar.brand.ilike(f"%{brand}%"),
        ScrapedCar.model.ilike(f"%{model}%"),
    )


def _try(query, label: str) -> tuple[list[ScrapedCar], str]:
    rows = query.limit(TARGET_SAMPLES * 2).all()
    return rows, label


def _retrieve_layers(db: Session, c: CarFeatures) -> tuple[list[ScrapedCar], str]:
    """Try progressively looser filters; return first layer with enough samples."""
    mileage_min, mileage_max = _mileage_band(c.mileage)

    # Layer 1 — strict
    q = _query_base(db, brand=c.brand, model=c.model).filter(
        ScrapedCar.year.between(c.year - 2, c.year + 2),
        ScrapedCar.mileage.between(mileage_min, mileage_max),
    )
    if c.fuel_type:
        q = q.filter(ScrapedCar.fuel_type.ilike(c.fuel_type))
    if c.transmission:
        q = q.filter(ScrapedCar.transmission.ilike(c.transmission))
    rows, _ = _try(q, "strict")
    if len(rows) >= MIN_SAMPLES:
        return rows, "strict"

    # Layer 2 — drop fuel/transmission
    q = _query_base(db, brand=c.brand, model=c.model).filter(
        ScrapedCar.year.between(c.year - 2, c.year + 2),
        ScrapedCar.mileage.between(mileage_min, mileage_max),
    )
    rows, _ = _try(q, "no-fuel-trans")
    if len(rows) >= MIN_SAMPLES:
        return rows, "no-fuel-trans"

    # Layer 3 — wider year, no mileage band
    q = _query_base(db, brand=c.brand, model=c.model).filter(
        ScrapedCar.year.between(c.year - 4, c.year + 4),
    )
    rows, _ = _try(q, "wide-year")
    if len(rows) >= MIN_SAMPLES:
        return rows, "wide-year"

    # Layer 4 — same brand+model only
    q = _query_base(db, brand=c.brand, model=c.model)
    rows, _ = _try(q, "brand-model")
    if len(rows) >= MIN_SAMPLES:
        return rows, "brand-model"

    # Layer 5 — fallback to same brand only
    q = db.query(ScrapedCar).filter(ScrapedCar.brand.ilike(f"%{c.brand}%"))
    rows, _ = _try(q, "brand-only")
    return rows, "brand-only"


def _drop_outliers(cars: Sequence[ScrapedCar]) -> list[ScrapedCar]:
    """Reject prices outside median ± MAD_K * MAD. Robust to a few bad scrapes."""
    if len(cars) < 4:
        return list(cars)
    prices = [c.price for c in cars]
    m = median(prices)
    mad = median(abs(p - m) for p in prices) or 1.0
    lo, hi = m - MAD_K * mad, m + MAD_K * mad
    return [c for c in cars if lo <= c.price <= hi]


def find_comparable_cars(db: Session, features: CarFeatures) -> RetrievalResult:
    rows, strategy = _retrieve_layers(db, features)
    filtered = _drop_outliers(rows)
    return RetrievalResult(
        cars=filtered,
        strategy=strategy,
        n_raw=len(rows),
        n_after_outlier=len(filtered),
    )
