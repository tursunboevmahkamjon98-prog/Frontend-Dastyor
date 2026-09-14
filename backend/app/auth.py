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
    """Issues a new opaque refresh token, storing only its hash (see
    RefreshToken's docstring) — returns the raw token, which is the one
    and only time it exists in plaintext. [login_at] is only ever passed
    by rotate_refresh_token, to carry the *original* sign-in time forward
    through rotation instead of resetting it on every silent refresh."""
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
    """Marks the calling device as already phone-verified for this user and
    returns the raw device token (stored hashed — see TrustedDevice). Called
    right after a successful OTP verification: that code proved the person
    holds the number, and this is what remembers it so the next login from
    the same device doesn't re-ask."""
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
    """True if [raw_token] is a live trusted-device token belonging to THIS
    user — the user_id match is what stops a token minted for one account
    from waiving the SMS step on another. Touches last_used_at on a hit.

    Deliberately returns a plain bool rather than raising: a bad/expired/
    foreign token is not an error, it just means this device still has to
    do the OTP round like any first-time device."""
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
    """Validates a refresh token and, if it's still good, atomically
    retires it and issues its replacement (rotation — see RefreshToken's
    docstring on why one-time-use). Returns (user_id, new_raw_token), or
    None if the token is unknown, expired, or already used/revoked.
    platform/login_at carry over from the retired row unconditionally —
    a refresh isn't a new sign-in — while user_agent prefers whatever the
    caller has fresh from *this* request, falling back to the old row's."""
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
    """Every still-active *web* session for [user_id] — the mobile app's
    "Linked devices" list. See RefreshToken.platform's docstring for why
    this only ever returns "web" rows."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > now,
            RefreshToken.platform == "web",
        )
        .order_by(RefreshToken.login_at.desc())
    )
    return list(result.scalars().all())


async def revoke_session(db: AsyncSession, user_id: str, session_id: str) -> bool:
    """Remote log-out of one linked device — scoped to [user_id] so one
    account can never revoke another's session by guessing an id. Returns
    False if no matching *active* row existed (already gone/expired is
    treated the same as "not found", not an error)."""
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.id == session_id,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,  # noqa: E712
        )
        .values(revoked=True)
    )
    return result.rowcount > 0


async def revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    """Best-effort logout — revokes the one token presented, if it's still
    valid. Never raises: an already-expired/unknown/garbage token means
    the session is over either way, which is exactly what logout wants."""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == _hash_refresh_token(raw_token))
        .values(revoked=True)
    )
    await db.flush()


async def revoke_all_refresh_tokens(db: AsyncSession, user_id: str) -> None:
    """Called on password change/reset — a credential compromise serious
    enough to change the password should also end every other session
    that was logged in with the old one, not just leave them valid for up
    to REFRESH_TOKEN_EXPIRE_DAYS more."""
    await db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True))
    await db.flush()


async def _ensure_short_id(user: User, db: AsyncSession) -> None:
    """Lazily assigns User.short_id (see models.py's docstring) the first
    time an account is loaded after this feature shipped — covers every
    pre-existing account without a separate backfill migration, and every
    freshly registered one the moment it first calls any authenticated
    endpoint (e.g. GET /auth/me right after register).

    Commits immediately rather than flush()-ing into the request's still-
    open transaction. This used to flush only, and get_db() (database.py)
    does not commit the request's session until the route handler
    RETURNS — so the UPDATE below sat as an uncommitted row lock on this
    user for the rest of the request. Any code later in that same request
    that opens its OWN connection and touches the same row — every one of
    them, since limits.reserve()/refund() and _claim_free()/_claim_balance
    all do — then blocked waiting for a lock that could only be released
    by this request finishing, which could not happen until that blocked
    call returned. A permanent self-deadlock, with no timeout on either
    side, reproducible on a SINGLE request with zero concurrency: it hit
    every brand-new account's first generate/billing call, every time.
    Confirmed via pg_stat_activity: the short_id UPDATE sat "idle in
    transaction" while reserve()'s UPDATE waited on it under wait_event
    "transactionid", both forever.
    Committing here ends this tiny transaction on the spot, so the lock
    is gone before generate() or anything else in the request gets a
    chance to want it."""
    if user.short_id:
        return
    for _ in range(20):
        candidate = f"{secrets.randbelow(1_000_000):06d}"
        exists = (await db.execute(select(User.id).where(User.short_id == candidate))).scalar_one_or_none()
        if exists is None:
            user.short_id = candidate
            await db.commit()
            return
    # Astronomically unlikely with 20 tries across a 6-digit space at this
    # app's scale — leave it null rather than loop forever; the next
    # request through here just tries again.


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
    """Same bearer token as every other endpoint — there's no separate
    admin login/token type. Just gates on User.role, set either by the
    ADMIN_EMAIL startup provisioning (see main.py's lifespan) or by
    another admin promoting the account via PUT /admin/users/{id}/role.
    403, not 404: an authenticated non-admin should see "not allowed",
    not be left guessing whether the admin API exists at all."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
