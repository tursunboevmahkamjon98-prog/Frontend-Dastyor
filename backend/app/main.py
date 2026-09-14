import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.rate_limit import RateLimitMiddleware
from app.security import (
    BodySizeLimitMiddleware, SecurityHeadersMiddleware, ai_queue_depth,
    prune_rate_limit_attempts,
)
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from app.database import init_db, async_session
from app.config import get_settings
from app.routers import auth, materials, admin, billing, qr_auth
from app.auth import hash_password
from app.models import User
from app.logger import get_logger

logger = get_logger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(os.path.join(UPLOAD_DIR, "avatars"), exist_ok=True)


async def _provision_admin():
    """Ensures ADMIN_EMAIL (if set) is an admin: promotes it if the
    account already exists (e.g. someone registered normally first), or
    creates it with ADMIN_PASSWORD if not. Runs on every startup, not just
    the first — cheap no-op once the role is already "admin", and it
    means changing ADMIN_EMAIL in .env and restarting is enough to add
    another admin without needing a database console."""
    settings = get_settings()
    if not settings.ADMIN_EMAIL:
        return
    email = settings.ADMIN_EMAIL.strip().lower()
    phone = settings.ADMIN_PHONE.strip() or None
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            if not settings.ADMIN_PASSWORD:
                logger.warning(f"ADMIN_EMAIL={email} set but ADMIN_PASSWORD is empty — skipping admin provisioning")
                return
            user = User(
                full_name=settings.ADMIN_NAME,
                email=email,
                phone=phone,
                phone_verified=bool(phone),
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
            )
            db.add(user)
            await db.commit()
            logger.info(f"Provisioned new admin account: {email}")
        else:
            changed = False
            if user.role != "admin":
                user.role = "admin"
                changed = True
            # Backfills a phone onto an admin account that predates
            # ADMIN_PHONE existing — login is phone-only now (see
            # schemas.UserLogin), so without this the account would be
            # stuck admin-in-the-database but unable to actually sign in.
            if phone and not user.phone:
                user.phone = phone
                user.phone_verified = True
                changed = True
            if changed:
                await db.commit()
                logger.info(f"Updated admin account: {email}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.join(UPLOAD_DIR, "avatars"), exist_ok=True)
    await init_db()
    await _provision_admin()
    # rate_limit_attempts gets a row per login/OTP/generation attempt and
    # is read on the hot path of all three; nothing ever looks further
    # back than an hour. Sweeping on startup keeps it from growing into a
    # table scan on every sign-in. Failure here must not stop the app
    # from booting — a large table is slow, an app that won't start is
    # down.
    try:
        removed = await prune_rate_limit_attempts()
        if removed:
            logger.info(f"Pruned {removed} expired rate-limit attempt rows")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Rate-limit prune skipped: {e}")

    # Say out loud whether this machine can actually produce the files
    # the product sells. Both failures below are silent at runtime — a
    # missing font still returns a 200 PDF (of empty boxes) and a missing
    # LibreOffice still returns a 200 preview (of the wrong thing) — so
    # startup is the only place they can be noticed before a teacher
    # notices them.
    try:
        from app.export_builder import verify_pdf_fonts, verify_pptx_renderer
        for problem in verify_pdf_fonts():
            logger.error(f"FONT PROBLEM: {problem}")
        renderer = verify_pptx_renderer()
        if renderer:
            logger.warning(f"RENDERER: {renderer}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Startup asset check skipped: {e}")
    yield


_settings = get_settings()

app = FastAPI(
    title="TeachAIweb API",
    description="Backend for the TeachAIweb website — separate from the Flutter app's backend.",
    version="0.1.0",
    lifespan=lifespan,
    # None removes the route entirely rather than leaving it to 404 a
    # request it would otherwise have answered. See DOCS_ENABLED.
    docs_url="/docs" if _settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if _settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if _settings.DOCS_ENABLED else None,
)

settings = _settings

# Starlette runs middleware in REVERSE order of registration, so the ones
# added here run last-registered-first. Everything below is registered
# before CORSMiddleware and therefore runs after it — which is what makes
# a rejection (429/413) come back with CORS headers attached instead of
# surfacing in the browser as an opaque network error that says nothing
# about why the request failed.
#
# Order among themselves, cheapest rejection first: body size is a header
# comparison, the flood guard is an in-memory deque, and security headers
# only touch the response.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(BodySizeLimitMiddleware)

cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Content-Disposition isn't in the browser's default CORS-safelisted
    # response headers, so without this, frontend code reading it (to name
    # a downloaded file after its real title) would silently see null and
    # fall back to a generic name — this exposes it so that actually works.
    expose_headers=["Content-Disposition"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(materials.router)
app.include_router(materials.lessons_router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(qr_auth.router)


@app.get("/api/health")
async def health():
    # ai_queue is how many requests are currently waiting for a
    # generation slot (see security.ai_slot). A number that stays above
    # zero means MAX_CONCURRENT_AI_CALLS is the bottleneck, which is
    # worth seeing from outside rather than only in the logs.
    return {"status": "ok", "app": "TeachAIweb", "ai_queue": ai_queue_depth()}
