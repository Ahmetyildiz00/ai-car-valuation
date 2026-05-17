"""Statistical price baseline from a list of comparable listings.

We use a simple but robust approach: fit a 1-D linear regression
`price ~ mileage`, evaluate at the target's mileage, then derive a
min/max envelope from the residuals.

If the comparables don't show meaningful mileage variation (or there's
too few of them), we fall back to median-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from app.models.valuation import ScrapedCar

MIN_FOR_REGRESSION = 8
ENVELOPE_PCT = 0.15  # ±15% fallback envelope when residuals are tiny


@dataclass
class BaselineResult:
    price: float
    price_min: float
    price_max: float
    method: str  # "linear", "median"
    n_samples: int


def statistical_baseline(
    cars: Sequence[ScrapedCar], target_mileage: int
) -> BaselineResult | None:
    if not cars:
        return None

    prices = np.array([c.price for c in cars], dtype=float)
    mileages = np.array([c.mileage for c in cars], dtype=float)

    if len(cars) < MIN_FOR_REGRESSION or float(mileages.std()) < 1.0:
        med = float(np.median(prices))
        return BaselineResult(
            price=med,
            price_min=med * (1 - ENVELOPE_PCT),
            price_max=med * (1 + ENVELOPE_PCT),
            method="median",
            n_samples=len(cars),
        )

    # Linear fit: price = a*mileage + b
    a, b = np.polyfit(mileages, prices, deg=1)
    predicted = float(a * target_mileage + b)

    residuals = prices - (a * mileages + b)
    spread = float(np.percentile(np.abs(residuals), 80))
    spread = max(spread, predicted * ENVELOPE_PCT * 0.5)

    return BaselineResult(
        price=max(predicted, 0.0),
        price_min=max(predicted - spread, 0.0),
        price_max=predicted + spread,
        method="linear",
        n_samples=len(cars),
    )
