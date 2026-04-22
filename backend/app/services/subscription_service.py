from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.subscription import Subscription, ValuationUsage
from app.models.user import User

TIER_FREE = "free"
TIER_PRO = "pro"

TIER_LIMITS = {
    TIER_FREE: settings.FREE_TIER_MONTHLY_LIMIT,
    TIER_PRO: None,  # unlimited
}


def current_period_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def get_or_create_subscription(user: User, db: Session) -> Subscription:
    if user.subscription:
        sub = user.subscription
    else:
        sub = Subscription(user_id=user.id, tier=TIER_FREE)
        db.add(sub)
        db.commit()
        db.refresh(sub)

    if sub.tier == TIER_PRO and sub.expires_at and sub.expires_at < datetime.now(timezone.utc):
        sub.tier = TIER_FREE
        sub.expires_at = None
        db.commit()
        db.refresh(sub)

    return sub


def _get_or_create_usage(user_id, db: Session) -> ValuationUsage:
    period = current_period_start()
    usage = (
        db.query(ValuationUsage)
        .filter(ValuationUsage.user_id == user_id, ValuationUsage.period_start == period)
        .first()
    )
    if usage:
        return usage

    usage = ValuationUsage(user_id=user_id, period_start=period, count=0)
    db.add(usage)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        usage = (
            db.query(ValuationUsage)
            .filter(ValuationUsage.user_id == user_id, ValuationUsage.period_start == period)
            .first()
        )
    db.refresh(usage)
    return usage


def get_usage_count(user_id, db: Session) -> int:
    period = current_period_start()
    usage = (
        db.query(ValuationUsage)
        .filter(ValuationUsage.user_id == user_id, ValuationUsage.period_start == period)
        .first()
    )
    return usage.count if usage else 0


def get_remaining(user: User, db: Session) -> int | None:
    sub = get_or_create_subscription(user, db)
    limit = TIER_LIMITS.get(sub.tier)
    if limit is None:
        return None
    used = get_usage_count(user.id, db)
    return max(0, limit - used)


def has_quota(user: User, db: Session) -> bool:
    remaining = get_remaining(user, db)
    return remaining is None or remaining > 0


def increment_usage(user: User, db: Session) -> ValuationUsage:
    usage = _get_or_create_usage(user.id, db)
    usage.count += 1
    db.commit()
    db.refresh(usage)
    return usage


def upgrade_to_pro(user: User, db: Session, expires_at: datetime | None = None) -> Subscription:
    sub = get_or_create_subscription(user, db)
    sub.tier = TIER_PRO
    sub.expires_at = expires_at
    db.commit()
    db.refresh(sub)
    return sub


def downgrade_to_free(user: User, db: Session) -> Subscription:
    sub = get_or_create_subscription(user, db)
    sub.tier = TIER_FREE
    sub.expires_at = None
    db.commit()
    db.refresh(sub)
    return sub
