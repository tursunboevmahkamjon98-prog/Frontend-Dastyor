import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.logger import get_logger

logger = get_logger(__name__)

_WINDOW = 60.0

_AUTH_PREFIX = "/api/auth/"
_AUTH_LIMIT = 60

_EXEMPT_PREFIXES = (
    "/api/curriculum/",
    "/api/auth/qr/",
    "/uploads/",
    "/docs",
    "/openapi.json",
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque] = defaultdict(deque)
        self._last_sweep = time.monotonic()

    def _ip(self, request: Request) -> str:
        cf = request.headers.get("cf-connecting-ip")
        if cf:
            return cf.strip()[:60]
        forwarded = request.headers.get("x-forwarded-for") or ""
        if forwarded:
            return forwarded.split(",")[0].strip()[:60]
        return (request.client.host if request.client else "unknown")[:60]

    def _sweep(self, now: float) -> None:
        if now - self._last_sweep < _WINDOW:
            return
        self._last_sweep = now
        for ip in [ip for ip, hits in self._hits.items()
                   if not hits or now - hits[-1] > _WINDOW]:
            del self._hits[ip]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or path.startswith(_EXEMPT_PREFIXES):
            return await call_next(request)

        limit = (_AUTH_LIMIT if path.startswith(_AUTH_PREFIX)
                 else get_settings().MAX_REQUESTS_PER_MINUTE)
        now = time.monotonic()
        self._sweep(now)

        bucket = ("auth:" if path.startswith(_AUTH_PREFIX) else "api:") + self._ip(request)
        hits = self._hits[bucket]
        while hits and now - hits[0] > _WINDOW:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = int(_WINDOW - (now - hits[0])) + 1
            logger.warning(f"Flood guard: {self._ip(request)} blocked on {path} "
                           f"({len(hits)} requests in the last minute, limit {limit})")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please wait a moment."},
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)
        return await call_next(request)
