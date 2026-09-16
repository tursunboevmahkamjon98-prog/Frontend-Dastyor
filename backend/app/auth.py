import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.config import get_settings
from app.database import get_db
from app.models import User, RefreshToken, TrustedDevice

settings = get_settings()
security = HTTPBearer()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_refresh_token(
    db: AsyncSession,
    user_id: str,
    *,
    user_agent: str | None = None,
    platform: str = "mobile",
    login_at: datetime | None = None,
) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(RefreshToken(
        user_id=user_id,
        token_hash=_hash_refresh_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=user_agent,
        platform=platform,
        login_at=login_at or datetime.now(timezone.utc),
    ))
    await db.flush()
    return raw


async def create_trusted_device(
    db: AsyncSession,
    user_id: str,
    *,
    user_agent: str | None = None,
    platform: str = "mobile",
) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(TrustedDevice(
        user_id=user_id,
        token_hash=_hash_refresh_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.TRUSTED_DEVICE_EXPIRE_DAYS),
        user_agent=user_agent,
        platform=platform,
    ))
    await db.flush()
    return raw


async def is_trusted_device(db: AsyncSession, user_id: str, raw_token: str | None) -> bool:
    if not raw_token:
        return False
    result = await db.execute(
        select(TrustedDevice).where(TrustedDevice.token_hash == _hash_refresh_token(raw_token))
    )
    device = result.scalar_one_or_none()
    if device is None or device.user_id != user_id:
        return False
    expires_at = device.expires_at if device.expires_at.tzinfo else device.expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return False
    device.last_used_at = datetime.now(timezone.utc)
    return True


async def rotate_refresh_token(
    db: AsyncSession, raw_token: str, *, user_agent: str | None = None
) -> tuple[str, str] | None:
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash_refresh_token(raw_token)))
    token = result.scalar_one_or_none()
    if token is None or token.revoked:
        return None
    expires_at = token.expires_at if token.expires_at.tzinfo else token.expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    token.revoked = True
    new_raw = await create_refresh_token(
        db,
        token.user_id,
        user_agent=user_agent or token.user_agent,
        platform=token.platform,
        login_at=token.login_at,
    )
    return token.user_id, new_raw


async def list_sessions(db: AsyncSession, user_id: str) -> list[RefreshToken]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > now,
            RefreshToken.platform == "web",
        )
        .order_by(RefreshToken.login_at.desc())
    )
    return list(result.scalars().all())


async def revoke_session(db: AsyncSession, user_id: str, session_id: str) -> bool:
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.id == session_id,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,
        )
        .values(revoked=True)
    )
    return result.rowcount > 0


async def revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == _hash_refresh_token(raw_token))
        .values(revoked=True)
    )
    await db.flush()


async def revoke_all_refresh_tokens(db: AsyncSession, user_id: str) -> None:
    await db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True))
    await db.flush()


async def _ensure_short_id(user: User, db: AsyncSession) -> None:
    if user.short_id:
        return
    for _ in range(20):
        candidate = f"{secrets.randbelow(1_000_000):06d}"
        exists = (await db.execute(select(User.id).where(User.short_id == candidate))).scalar_one_or_none()
        if exists is None:
            user.short_id = candidate
            await db.commit()
            return


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = decode_token(credentials.credentials)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    await _ensure_short_id(user, db)
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
