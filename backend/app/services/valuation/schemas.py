"""Shared dataclasses passed between valuation pipeline stages."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CarFeatures:
    """Resolved input describing the car being appraised.

    Fields with `None` are unknown; downstream stages decide how to
    handle missing values (skip filter, default in feature vector, etc.).
    """

    brand: str
    model: str
    year: int
    mileage: int
    fuel_type: str | None = None
    transmission: str | None = None
    body_type: str | None = None
    color: str | None = None
    engine_size: str | None = None
    damage_records: str | None = None
    image_analysis: dict[str, Any] | None = None

    def text_repr(self) -> str:
        parts = [self.brand, self.model, str(self.year)]
        for v in (self.fuel_type, self.transmission, self.body_type, self.color):
            if v:
                parts.append(v)
        parts.append(f"{self.mileage}km")
        return " ".join(parts)


@dataclass
class ValuationResult:
    predicted_price: float
    price_min: float
    price_max: float
    condition_score: float
    analysis: str
    sources: dict[str, Any] = field(default_factory=dict)
