from datetime import datetime

from pydantic import BaseModel


class SubscriptionStatus(BaseModel):
    tier: str
    expires_at: datetime | None
    monthly_limit: int | None
    used_this_month: int
    remaining: int | None
    unlimited: bool


class UpgradeRequest(BaseModel):
    tier: str = "pro"
    duration_days: int | None = 30
