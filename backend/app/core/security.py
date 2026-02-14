import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import RefreshToken, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": user_id, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: str, db: Session) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(
        payload, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM
    )

    db_token = RefreshToken(
        token=token,
        user_id=uuid.UUID(user_id),
        expires_at=expire,
    )
    db.add(db_token)
    db.commit()

    return token


def verify_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def verify_refresh_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


def rotate_refresh_token(old_token: str, db: Session) -> tuple[str, str] | None:
    """Verify old refresh token, revoke it, and issue new token pair."""
    payload = verify_refresh_token(old_token)
    if not payload:
        return None

    db_token = db.query(RefreshToken).filter(RefreshToken.token == old_token).first()
    if not db_token or db_token.is_revoked:
        # Possible token reuse attack — revoke all tokens for this user
        if db_token:
            db.query(RefreshToken).filter(
                RefreshToken.user_id == db_token.user_id
            ).update({"is_revoked": True})
            db.commit()
        return None

    # Revoke the old token
    db_token.is_revoked = True
    db.commit()

    user_id = payload["sub"]
    new_access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id, db)

    return new_access, new_refresh


def revoke_all_user_tokens(user_id: uuid.UUID, db: Session) -> None:
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update(
        {"is_revoked": True}
    )
    db.commit()


def authenticate_user(email: str, password: str, db: Session) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
