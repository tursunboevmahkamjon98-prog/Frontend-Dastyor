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
    try:
        removed = await prune_rate_limit_attempts()
        if removed:
            logger.info(f"Pruned {removed} expired rate-limit attempt rows")
    except Exception as e:
        logger.warning(f"Rate-limit prune skipped: {e}")

    try:
        from app.export_builder import verify_pdf_fonts
        from app.math_render import verify_math_fonts
        from app.fonts import verify_fonts
        for problem in verify_pdf_fonts():
            logger.error(f"FONT PROBLEM: {problem}")
        for problem in verify_math_fonts():
            logger.error(f"MATH FONT PROBLEM: {problem}")
        for problem in verify_fonts():
            logger.error(f"DRAWING FONT PROBLEM: {problem}")
    except Exception as e:
        logger.warning(f"Startup asset check skipped: {e}")
    yield


_settings = get_settings()

app = FastAPI(
    title="TeachAIweb API",
    description="Backend for the TeachAIweb website — separate from the Flutter app's backend.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if _settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if _settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if _settings.DOCS_ENABLED else None,
)

settings = _settings

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
    return {"status": "ok", "app": "TeachAIweb", "ai_queue": ai_queue_depth()}
