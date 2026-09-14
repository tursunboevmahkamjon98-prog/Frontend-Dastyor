# -*- coding: utf-8 -*-
"""A per-IP request cap for the whole API.

What this is: a flood guard. It stops one address from hammering the API
— scripted registration attempts, a loop scraping endpoints, a stuck
client retrying forever, someone hoping to run the AI bill up.

What this is NOT: DDoS protection. A distributed attack arrives from
thousands of addresses, and by the time a request reaches this middleware
the server has already paid for the connection, the TLS handshake and the
parse. Volumetric attacks have to be absorbed in front of the
application — Cloudflare (which this deployment already fronts with) or
the reverse proxy. This is the layer that stops the single-source abuse
Cloudflare would let through because it looks like an ordinary client.

Counters live in this process's memory on purpose: it must not add a
database round trip to every request, which is the thing an attacker is
trying to make expensive. That means each worker enforces its own share
of the limit — with N workers the effective cap is N times the setting,
which is fine for a guard whose job is orders of magnitude, not
precision.
"""
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.logger import get_logger

logger = get_logger(__name__)

_WINDOW = 60.0

# Auth endpoints get a much tighter cap than the rest of the API, applied
# HERE — in memory, before any database work happens.
#
# Measured: 120 concurrent requests to /register/send-code timed out at
# thirty seconds. Not because of the SMS, but because each request does
# three rate-limit checks and each check COMMITS. The database becomes
# the bottleneck, which is the flood succeeding by another route. Cutting
# the burst in memory means the expensive checks only ever run for
# traffic that already looks human.
#
# Sixty a minute per address still clears a staffroom signing up
# together; a script doing hundreds a second never reaches the database.
_AUTH_PREFIX = "/api/auth/"
_AUTH_LIMIT = 60

# Endpoints exempt from the cap: a long poll or a progress stream is
# SUPPOSED to be called repeatedly, and counting it would break the
# feature rather than protect it.
_EXEMPT_PREFIXES = (
    "/api/curriculum/",     # generation progress polling
    "/api/auth/qr/",        # the website polls this while waiting for a scan
    "/uploads/",            # images already embedded in a rendered page
    "/docs",
    "/openapi.json",
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque] = defaultdict(deque)
        self._last_sweep = time.monotonic()

    def _ip(self, request: Request) -> str:
        # Same reasoning as auth.py's _client_ip: forgeable, used only to
        # throttle, never to grant. CF-Connecting-IP first — without it
        # everything behind Cloudflare shares one counter and the first
        # busy minute locks out every user at once.
        cf = request.headers.get("cf-connecting-ip")
        if cf:
            return cf.strip()[:60]
        forwarded = request.headers.get("x-forwarded-for") or ""
        if forwarded:
            return forwarded.split(",")[0].strip()[:60]
        return (request.client.host if request.client else "unknown")[:60]

    def _sweep(self, now: float) -> None:
        """Drops addresses that have gone quiet.

        Without this the dictionary grows one entry per address seen and
        never shrinks — which is itself a way to exhaust the server's
        memory, so the guard would become the vulnerability."""
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
