# -*- coding: utf-8 -*-
"""Server-side guards that sit in front of the expensive work.

Three separate problems, deliberately kept apart because they fail in
different ways and are sized from different numbers:

* **Body size** — a request can make the server allocate memory before a
  single line of application code runs. Capped in middleware, before the
  body is read.
* **Per-user throttles** — rate_limit.py counts per IP address, which
  cannot see one authenticated account working from a phone, a laptop
  and a script at once, and cannot see an attacker rotating addresses
  behind one stolen token. These count per user id, in the database, so
  the number holds across every worker process and every device.
* **AI concurrency** — the generation endpoints call an external model
  that takes tens of seconds. Without a ceiling, fifty simultaneous
  generations open fifty upstream connections, hold fifty database
  sessions, and make every ordinary API call queue behind them. A
  bounded semaphore turns that into a queue with a known depth.

None of this replaces a CDN/WAF for volumetric attack traffic (see
rate_limit.py's docstring on where that has to be absorbed). It bounds
what one authenticated client can make this process do.
"""
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


# ── Request body size ────────────────────────────────────────────────────

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects a request whose declared Content-Length exceeds the cap,
    before anything reads the body.

    Checking the header rather than streaming and counting is deliberate:
    the point is to refuse without allocating, and every real client
    (browsers, the Flutter app's http client, curl) sends Content-Length
    for a body it has in hand. A chunked upload with no Content-Length
    slips past this header check — Starlette still bounds what it will
    buffer, and the multipart endpoints re-check the real size after
    reading (see materials.py's /upload-source), so that path is covered
    where it matters.
    """

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


# ── Security headers ─────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Response headers that cost nothing and close whole classes of
    browser-side attack against anything this API serves directly.

    This API is consumed by a separate Next.js frontend and by the mobile
    app, so most of what it returns is JSON. The exception is /uploads —
    real files, uploaded by users, served from the same origin. An
    uploaded SVG or HTML file rendered inline there would run script in
    this origin's context, which is stored XSS; `X-Content-Type-Options:
    nosniff` plus a CSP that permits nothing is what stops that.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; sandbox",
        )
        # Only meaningful over TLS, and only for browsers; harmless
        # otherwise. Left off localhost so a developer's browser doesn't
        # pin http://localhost to HTTPS for the next two years.
        host = (request.headers.get("host") or "").split(":")[0]
        if host not in ("localhost", "127.0.0.1"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


# ── Per-user throttles ───────────────────────────────────────────────────

async def enforce_user_quota(user_id: str, purpose: str, max_attempts: int,
                             window_seconds: int = 3600) -> None:
    """Counts one use of [purpose] by [user_id] and raises 429 once the
    account is over [max_attempts] within the window.

    Counted in the database rather than in process memory: with several
    uvicorn workers, an in-memory counter gives each worker its own full
    quota, so the real limit is silently N times the configured one, and
    a client that reconnects lands on a different worker each time.

    Runs on its own short-lived session that commits immediately, for the
    same reason auth.py's _check_rate_limit does: the caller's request
    routinely ends in an exception (a refused generation, an AI failure),
    and get_db rolls the whole request transaction back — which would
    erase the very record the throttle depends on.
    """
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
    """Deletes rate-limit rows past any window that reads them.

    Every throttle in this codebase INSERTs a row per attempt and only
    ever reads back the last hour of them, so without this the table
    grows without bound — and it is queried on the hot path of login and
    of every generation, so its size is a latency problem, not just a
    disk one. Called from the startup sweep in main.py."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)
    async with async_session() as db:
        result = await db.execute(
            text("DELETE FROM rate_limit_attempts WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        # Same reasoning for the admin lockout table: a row per failed
        # sign-in, read back only within ADMIN_LOCKOUT_SECONDS (15
        # minutes), and it is read on the login path. A day is far outside
        # any window that consults it.
        admin_result = await db.execute(
            text("DELETE FROM admin_login_attempts WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        await db.commit()
        return (result.rowcount or 0) + (admin_result.rowcount or 0)


# ── Admin sign-in lockout ────────────────────────────────────────────────

async def admin_login_blocked(identifier: str) -> bool:
    """True if [identifier] (a normalized phone) has failed too many
    admin sign-ins recently.

    Keyed on the targeted account, not on the source address, because a
    password-guessing attempt spread over a botnet stays under every
    per-IP limit by construction — that is the whole design of one. The
    thing worth protecting is the admin account, so that is what gets
    counted and locked."""
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
    """Own session + immediate commit — the caller raises 401 straight
    after this, and the request's transaction is rolled back by that
    exception, which would discard the record."""
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
    """Called after a successful admin sign-in, so a teacher who simply
    mistyped their password a few times isn't left locked out for the
    rest of the window once they get it right."""
    async with async_session() as db:
        await db.execute(
            text("DELETE FROM admin_login_attempts WHERE identifier = :id"),
            {"id": identifier},
        )
        await db.commit()


def password_strength_error(password: str, *, min_length: int) -> str | None:
    """None if [password] is strong enough for an admin account,
    otherwise the i18n key describing what's wrong.

    Enforced on admin accounts only, and only when a password is being
    SET (change/reset), never at sign-in — applying a new policy at
    sign-in would lock an existing admin out of the only UI that could
    fix it."""
    if len(password) < min_length:
        return "weak_password"
    if not any(c.isupper() for c in password):
        return "weak_password"
    if not any(c.islower() for c in password):
        return "weak_password"
    if not any(c.isdigit() for c in password):
        return "weak_password"
    return None


# ── AI concurrency ───────────────────────────────────────────────────────

_ai_semaphore: asyncio.Semaphore | None = None
_ai_waiting = 0


def _semaphore() -> asyncio.Semaphore:
    """Built lazily, on first use, rather than at import time: an
    asyncio.Semaphore binds to the running loop, and at import there
    isn't one yet under every server/worker start-up."""
    global _ai_semaphore
    if _ai_semaphore is None:
        _ai_semaphore = asyncio.Semaphore(get_settings().MAX_CONCURRENT_AI_CALLS)
    return _ai_semaphore


class ai_slot:
    """Async context manager bounding how many AI generations run at once
    in this process.

    Used as `async with ai_slot():` around the generate call, NOT around
    the whole request — the database work, the save and the response
    serialisation don't need a slot and holding one through them would
    shrink the effective concurrency for no reason.

    Waiting is bounded. A request that cannot get a slot within
    AI_QUEUE_TIMEOUT_SECONDS gets 503 with Retry-After, rather than
    holding a connection open indefinitely behind a queue that is not
    draining — a client told to come back is a client that has stopped
    consuming a socket.
    """

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
    """How many requests are currently waiting for a slot — surfaced on
    /api/health so a saturated queue is visible without reading logs."""
    return _ai_waiting
