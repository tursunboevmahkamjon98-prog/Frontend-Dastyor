import asyncio
import time
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.database import async_session
from app.logger import get_logger
from app.models import RateLimitAttempt

logger = get_logger(__name__)



class BodySizeLimitMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        declared = request.headers.get("content-length")
        if declared:
            try:
                size = int(declared)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
            limit = get_settings().MAX_REQUEST_BODY_BYTES
            if size > limit:
                logger.warning(
                    f"Rejected oversized request to {request.url.path}: "
                    f"{size} bytes (limit {limit})"
                )
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large"},
                )
        return await call_next(request)



class SecurityHeadersMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; sandbox",
        )
        host = (request.headers.get("host") or "").split(":")[0]
        if host not in ("localhost", "127.0.0.1"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response



async def enforce_user_quota(user_id: str, purpose: str, max_attempts: int,
                             window_seconds: int = 3600) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    async with async_session() as db:
        used = (await db.execute(
            select(func.count()).select_from(RateLimitAttempt).where(
                RateLimitAttempt.purpose == purpose,
                RateLimitAttempt.key == user_id,
                RateLimitAttempt.created_at >= cutoff,
            )
        )).scalar() or 0
        if used >= max_attempts:
            logger.warning(
                f"Per-user quota exceeded: user={user_id} purpose={purpose} "
                f"used={used} limit={max_attempts}"
            )
            raise HTTPException(
                status_code=429,
                detail="Слишком много запросов. Попробуйте позже.",
                headers={"Retry-After": str(window_seconds)},
            )
        db.add(RateLimitAttempt(purpose=purpose, key=user_id))
        await db.commit()


async def prune_rate_limit_attempts(older_than_seconds: int = 86_400) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)
    async with async_session() as db:
        result = await db.execute(
            text("DELETE FROM rate_limit_attempts WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        admin_result = await db.execute(
            text("DELETE FROM admin_login_attempts WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        await db.commit()
        return (result.rowcount or 0) + (admin_result.rowcount or 0)



async def admin_login_blocked(identifier: str) -> bool:
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.ADMIN_LOCKOUT_SECONDS)
    async with async_session() as db:
        failures = (await db.execute(
            text(
                "SELECT count(*) FROM admin_login_attempts "
                "WHERE identifier = :id AND created_at >= :cutoff"
            ),
            {"id": identifier, "cutoff": cutoff},
        )).scalar() or 0
    return failures >= settings.MAX_ADMIN_LOGIN_ATTEMPTS


async def record_admin_login_failure(identifier: str, ip: str | None) -> None:
    import uuid

    async with async_session() as db:
        await db.execute(
            text(
                "INSERT INTO admin_login_attempts (id, identifier, ip, created_at) "
                "VALUES (:id, :identifier, :ip, now())"
            ),
            {"id": str(uuid.uuid4()), "identifier": identifier, "ip": ip},
        )
        await db.commit()
    logger.warning(f"Failed admin sign-in for {identifier} from {ip}")


async def clear_admin_login_failures(identifier: str) -> None:
    async with async_session() as db:
        await db.execute(
            text("DELETE FROM admin_login_attempts WHERE identifier = :id"),
            {"id": identifier},
        )
        await db.commit()


def password_strength_error(password: str, *, min_length: int) -> str | None:
    if len(password) < min_length:
        return "weak_password"
    if not any(c.isupper() for c in password):
        return "weak_password"
    if not any(c.islower() for c in password):
        return "weak_password"
    if not any(c.isdigit() for c in password):
        return "weak_password"
    return None



_ai_semaphore: asyncio.Semaphore | None = None
_ai_waiting = 0


def _semaphore() -> asyncio.Semaphore:
    global _ai_semaphore
    if _ai_semaphore is None:
        _ai_semaphore = asyncio.Semaphore(get_settings().MAX_CONCURRENT_AI_CALLS)
    return _ai_semaphore


class ai_slot:

    def __init__(self, label: str = "ai"):
        self._label = label
        self._acquired = False
        self._t0 = 0.0

    async def __aenter__(self):
        global _ai_waiting
        settings = get_settings()
        sem = _semaphore()
        _ai_waiting += 1
        self._t0 = time.monotonic()
        try:
            await asyncio.wait_for(sem.acquire(), timeout=settings.AI_QUEUE_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            logger.error(
                f"AI queue full: {self._label} waited "
                f"{settings.AI_QUEUE_TIMEOUT_SECONDS}s for a slot "
                f"({_ai_waiting} waiting, limit {settings.MAX_CONCURRENT_AI_CALLS})"
            )
            raise HTTPException(
                status_code=503,
                detail="Сервис перегружен. Попробуйте через минуту.",
                headers={"Retry-After": "60"},
            ) from None
        finally:
            _ai_waiting -= 1
        self._acquired = True
        waited = time.monotonic() - self._t0
        if waited > 1.0:
            logger.info(f"AI slot for {self._label} acquired after {waited:.1f}s")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._acquired:
            _semaphore().release()
        return False


def ai_queue_depth() -> int:
    return _ai_waiting
