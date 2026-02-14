import uuid
from datetime import datetime

from pydantic import BaseModel


class ValuationRequest(BaseModel):
    brand: str
    model: str
    year: int
    mileage: int
    fuel_type: str
    transmission: str
    body_type: str | None = None
    color: str | None = None
    engine_size: str | None = None
    damage_records: str | None = None


class ValuationResponse(BaseModel):
    id: uuid.UUID
    brand: str
    model: str
    year: int
    mileage: int
    fuel_type: str
    transmission: str
    body_type: str | None
    color: str | None
    engine_size: str | None
    damage_records: str | None
    predicted_price: float | None
    price_min: float | None
    price_max: float | None
    condition_score: float | None
    ai_analysis: str | None
    image_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ValuationListResponse(BaseModel):
    valuations: list[ValuationResponse]
    total: int
