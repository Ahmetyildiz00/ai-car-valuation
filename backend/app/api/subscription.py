from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.subscription import SubscriptionStatus, UpgradeRequest
from app.services.subscription_service import (
    TIER_FREE,
    TIER_LIMITS,
    TIER_PRO,
    downgrade_to_free,
    get_or_create_subscription,
    get_remaining,
    get_usage_count,
    upgrade_to_pro,
)

router = APIRouter(prefix="/subscription", tags=["Subscription"])


def _build_status(user: User, db: Session) -> SubscriptionStatus:
    sub = get_or_create_subscription(user, db)
    limit = TIER_LIMITS.get(sub.tier)
    used = get_usage_count(user.id, db)
    remaining = get_remaining(user, db)
    return SubscriptionStatus(
        tier=sub.tier,
        expires_at=sub.expires_at,
        monthly_limit=limit,
        used_this_month=used,
        remaining=remaining,
        unlimited=limit is None,
    )


@router.get("", response_model=SubscriptionStatus)
def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _build_status(current_user, db)


@router.post("/upgrade", response_model=SubscriptionStatus)
def upgrade(
    data: UpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test-only upgrade endpoint. Replace with payment webhook in production."""
    if data.tier != TIER_PRO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only 'pro' tier is available",
        )
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=data.duration_days)
        if data.duration_days
        else None
    )
    upgrade_to_pro(current_user, db, expires_at=expires_at)
    return _build_status(current_user, db)


@router.post("/cancel", response_model=SubscriptionStatus)
def cancel(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    downgrade_to_free(current_user, db)
    return _build_status(current_user, db)
