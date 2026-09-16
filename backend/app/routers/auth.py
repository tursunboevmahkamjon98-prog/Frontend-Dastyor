import os
import uuid
import secrets
import httpx
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.database import get_db
from app.models import User, PhoneVerificationCode, RateLimitAttempt
from app.schemas import (
    UserRegister, SendRegisterCodeRequest, UserLogin, LoginSendCodeRequest, LoginVerifyRequest,
    EmailRegister, EmailLogin, GoogleAuthRequest,
    UserOut, UserUpdate, PasswordChange,
    TokenResponse, RefreshRequest, LogoutRequest, SessionOut,
    ForgotPasswordRequest, VerifyCodeRequest, ResetPasswordRequest,
)
from app.auth import (
    hash_password, verify_password, create_access_token, get_current_user,
    create_refresh_token, rotate_refresh_token, revoke_refresh_token, revoke_all_refresh_tokens,
    list_sessions, revoke_session, create_trusted_device, is_trusted_device,
)
from app.security import (
    admin_login_blocked, record_admin_login_failure, clear_admin_login_failures,
    password_strength_error,
)
from app.sms_service import send_sms_code
from app.http_client import SSL_CONTEXT
from app.logger import get_logger
from app.i18n import get_message
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/auth", tags=["auth"])

AVATAR_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "avatars")
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}

_RATE_WINDOW = settings.RATE_WINDOW


async def _check_sms_limits(db: AsyncSession, request: Request) -> bool:
    ip = _client_ip(request)
    if not await _check_rate_limit(db, "sms_ip_burst", ip,
                                   settings.MAX_SMS_PER_IP_BURST,
                                   settings.RATE_WINDOW_IP_BURST):
        return False
    if not await _check_rate_limit(db, "sms_ip", ip,
                                   settings.MAX_SMS_PER_IP,
                                   settings.RATE_WINDOW_IP):
        return False
    if not await _check_rate_limit(db, "sms_global", "all",
                                   settings.MAX_SMS_PER_DAY, 86400):
        logger.error("SMS DAILY BUDGET REACHED — no further codes will be sent today. "
                     "Either this is an attack, or MAX_SMS_PER_DAY needs raising.")
        return False
    return True


def _client_ip(request: Request) -> str:
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()[:60]
    forwarded = request.headers.get("x-forwarded-for") or ""
    if forwarded:
        return forwarded.split(",")[0].strip()[:60]
    return (request.client.host if request.client else "unknown")[:60]



async def _check_rate_limit(db: AsyncSession, purpose: str, key: str, max_attempts: int,
                            window: int | None = None) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window or _RATE_WINDOW)
    count = (await db.execute(
        select(func.count()).select_from(RateLimitAttempt).where(
            RateLimitAttempt.purpose == purpose,
            RateLimitAttempt.key == key,
            RateLimitAttempt.created_at >= cutoff,
        )
    )).scalar() or 0
    if count >= max_attempts:
        return False
    db.add(RateLimitAttempt(purpose=purpose, key=key))
    await db.commit()
    return True



@router.post("/register/send-code")
async def send_register_code(request: Request, data: SendRegisterCodeRequest,
                             db: AsyncSession = Depends(get_db)):
    try:
        if not await _check_sms_limits(db, request):
            logger.warning(f"SMS rate limit exceeded for IP {_client_ip(request)}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))
        if not await _check_rate_limit(db, "register_code", data.phone, settings.MAX_REGISTER_CODE_ATTEMPTS):
            logger.warning(f"Rate limit exceeded for register code: {data.phone}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))

        existing = await db.execute(select(User).where(User.phone == data.phone))
        if existing.scalar_one_or_none():
            logger.warning(f"Registration attempt with existing phone: {data.phone}")
            raise HTTPException(status_code=400, detail=get_message("phone_already_registered"))

        await db.execute(
            delete(PhoneVerificationCode).where(
                PhoneVerificationCode.phone == data.phone,
                PhoneVerificationCode.purpose == "register",
                PhoneVerificationCode.used == False,
            )
        )

        code = f"{secrets.randbelow(1000000):06d}"
        row = PhoneVerificationCode(
            phone=data.phone,
            code=code,
            purpose="register",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        db.add(row)
        await db.flush()

        sent = await send_sms_code(data.phone, code)
        if not sent:
            logger.error(f"Failed to send register code to {data.phone}")
            raise HTTPException(status_code=500, detail=get_message("sms_send_error"))

        logger.info(f"Register code sent to {data.phone}")
        return {"status": "ok", "message": "Code sent"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send register code error for {data.phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to send code")


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: Request, data: UserRegister, db: AsyncSession = Depends(get_db)):
    try:
        if not await _check_rate_limit(db, "register_ip", _client_ip(request),
                                       settings.MAX_REGISTER_PER_IP, settings.RATE_WINDOW_IP):
            logger.warning(f"Registration rate limit exceeded for IP {_client_ip(request)}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))

        existing = await db.execute(select(User).where(User.phone == data.phone))
        if existing.scalar_one_or_none():
            logger.warning(f"Registration attempt with existing phone: {data.phone}")
            raise HTTPException(status_code=400, detail=get_message("phone_already_registered"))

        result = await db.execute(
            select(PhoneVerificationCode).where(
                PhoneVerificationCode.phone == data.phone,
                PhoneVerificationCode.code == data.code,
                PhoneVerificationCode.purpose == "register",
                PhoneVerificationCode.used == False,
            ).order_by(PhoneVerificationCode.created_at.desc())
        )
        row = result.scalar_one_or_none()
        if not row:
            logger.warning(f"Invalid register code for {data.phone}")
            raise HTTPException(status_code=400, detail=get_message("invalid_code"))

        now = datetime.now(timezone.utc)
        expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        if expires < now:
            logger.warning(f"Expired register code for {data.phone}")
            raise HTTPException(status_code=400, detail=get_message("code_expired"))

        row.used = True

        user = User(
            full_name=data.full_name,
            phone=data.phone,
            phone_verified=True,
            hashed_password=hash_password(data.password),
        )
        db.add(user)
        await db.flush()

        token = create_access_token(user.id)
        refresh_token = await create_refresh_token(
            db, user.id,
            user_agent=request.headers.get("user-agent"),
            platform=request.headers.get("x-client-platform", "mobile"),
        )
        logger.info(f"New user registered: {user.phone}")
        return TokenResponse(
            access_token=token,
            refresh_token=refresh_token,
            user=UserOut.model_validate(user),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error for {data.phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        if not await _check_rate_limit(db, "login", data.phone, settings.MAX_LOGIN_ATTEMPTS):
            logger.warning(f"Rate limit exceeded for login: {data.phone}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))

        if await admin_login_blocked(data.phone):
            logger.warning(f"Admin sign-in blocked (lockout active): {data.phone}")
            raise HTTPException(status_code=429, detail=get_message("admin_locked"))

        result = await db.execute(select(User).where(User.phone == data.phone))
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.hashed_password):
            logger.warning(f"Failed login attempt for phone: {data.phone}")
            if user is not None and user.role == "admin":
                await record_admin_login_failure(data.phone, _client_ip(request))
            raise HTTPException(status_code=401, detail=get_message("invalid_credentials"))

        if user.role == "admin":
            await clear_admin_login_failures(data.phone)

        token = create_access_token(user.id)
        refresh_token = await create_refresh_token(
            db, user.id,
            user_agent=request.headers.get("user-agent"),
            platform=request.headers.get("x-client-platform", "mobile"),
        )
        logger.info(f"User logged in: {user.id} (role={user.role})")
        return TokenResponse(
            access_token=token,
            refresh_token=refresh_token,
            user=UserOut.model_validate(user),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {data.phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/login/send-code")
async def login_send_code(request: Request, data: LoginSendCodeRequest, db: AsyncSession = Depends(get_db)):
    try:
        if not await _check_sms_limits(db, request):
            logger.warning(f"SMS rate limit exceeded for IP {_client_ip(request)}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))
        if not await _check_rate_limit(db, "login", data.phone, settings.MAX_LOGIN_ATTEMPTS):
            logger.warning(f"Rate limit exceeded for login send-code: {data.phone}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))
        if await admin_login_blocked(data.phone):
            logger.warning(f"Admin sign-in blocked (lockout active): {data.phone}")
            raise HTTPException(status_code=429, detail=get_message("admin_locked"))

        result = await db.execute(select(User).where(User.phone == data.phone))
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.hashed_password):
            logger.warning(f"Failed login (send-code) attempt for phone: {data.phone}")
            if user is not None and user.role == "admin":
                await record_admin_login_failure(data.phone, _client_ip(request))
            raise HTTPException(status_code=401, detail=get_message("invalid_credentials"))

        trusted = await is_trusted_device(db, user.id, data.device_token)
        bypass = settings.OTP_BYPASS_PHONE
        if (bypass and data.phone == bypass) or user.role == "admin" or trusted:
            token = create_access_token(user.id)
            refresh_token = await create_refresh_token(
                db, user.id,
                user_agent=request.headers.get("user-agent"),
                platform=request.headers.get("x-client-platform", "mobile"),
            )
            logger.info(
                f"User logged in (OTP skipped, "
                f"{'trusted device' if trusted else 'bypass account'}): {user.phone}"
            )
            return TokenResponse(
                access_token=token,
                refresh_token=refresh_token,
                user=UserOut.model_validate(user),
            )

        await db.execute(
            delete(PhoneVerificationCode).where(
                PhoneVerificationCode.phone == data.phone,
                PhoneVerificationCode.purpose == "login",
                PhoneVerificationCode.used == False,
            )
        )

        code = f"{secrets.randbelow(1000000):06d}"
        row = PhoneVerificationCode(
            phone=data.phone,
            code=code,
            purpose="login",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        db.add(row)
        await db.flush()

        sent = await send_sms_code(data.phone, code, user.language)
        if not sent:
            logger.error(f"Failed to send login code to {data.phone}")
            raise HTTPException(status_code=500, detail=get_message("sms_send_error"))

        logger.info(f"Login code sent to {data.phone}")
        return {"status": "otp_required", "message": "Code sent"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login send-code error for {data.phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/login/verify", response_model=TokenResponse)
async def login_verify(request: Request, data: LoginVerifyRequest, db: AsyncSession = Depends(get_db)):
    try:
        if not await _check_rate_limit(db, "login_verify", data.phone, settings.MAX_VERIFY_ATTEMPTS):
            logger.warning(f"Rate limit exceeded for login verify: {data.phone}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))

        result = await db.execute(
            select(PhoneVerificationCode).where(
                PhoneVerificationCode.phone == data.phone,
                PhoneVerificationCode.code == data.code,
                PhoneVerificationCode.purpose == "login",
                PhoneVerificationCode.used == False,
            ).order_by(PhoneVerificationCode.created_at.desc())
        )
        row = result.scalar_one_or_none()
        if not row:
            logger.warning(f"Invalid login code for {data.phone}")
            raise HTTPException(status_code=400, detail=get_message("invalid_code"))

        now = datetime.now(timezone.utc)
        expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        if expires < now:
            logger.warning(f"Expired login code for {data.phone}")
            raise HTTPException(status_code=400, detail=get_message("code_expired"))

        row.used = True

        result = await db.execute(select(User).where(User.phone == data.phone))
        user = result.scalar_one_or_none()
        if not user:
            logger.error(f"User not found during login verify: {data.phone}")
            raise HTTPException(status_code=404, detail=get_message("user_not_found"))

        user_agent = request.headers.get("user-agent")
        platform = request.headers.get("x-client-platform", "mobile")
        token = create_access_token(user.id)
        refresh_token = await create_refresh_token(
            db, user.id, user_agent=user_agent, platform=platform,
        )
        device_token = None
        if data.remember_device:
            device_token = await create_trusted_device(
                db, user.id, user_agent=user_agent, platform=platform,
            )
        logger.info(f"User logged in (OTP verified): {user.phone}")
        return TokenResponse(
            access_token=token,
            refresh_token=refresh_token,
            user=UserOut.model_validate(user),
            device_token=device_token,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login verify error for {data.phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Login verify failed")


@router.post("/register-email", response_model=TokenResponse, status_code=201)
async def register_email(request: Request, data: EmailRegister, db: AsyncSession = Depends(get_db)):
    try:
        existing = await db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            logger.warning(f"Registration attempt with existing email: {data.email}")
            raise HTTPException(status_code=400, detail=get_message("email_already_registered"))

        user = User(
            full_name=data.full_name,
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        db.add(user)
        await db.flush()

        token = create_access_token(user.id)
        refresh_token = await create_refresh_token(
            db, user.id,
            user_agent=request.headers.get("user-agent"),
            platform=request.headers.get("x-client-platform", "mobile"),
        )
        logger.info(f"New user registered via email: {user.email}")
        return TokenResponse(
            access_token=token,
            refresh_token=refresh_token,
            user=UserOut.model_validate(user),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email registration error for {data.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login-email", response_model=TokenResponse)
async def login_email(request: Request, data: EmailLogin, db: AsyncSession = Depends(get_db)):
    try:
        if not await _check_rate_limit(db, "email_login", data.email, settings.MAX_LOGIN_ATTEMPTS):
            logger.warning(f"Rate limit exceeded for email login: {data.email}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))

        if await admin_login_blocked(data.email):
            logger.warning(f"Admin sign-in blocked (lockout active): {data.email}")
            raise HTTPException(status_code=429, detail=get_message("admin_locked"))

        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.hashed_password):
            logger.warning(f"Failed email login attempt for: {data.email}")
            if user is not None and user.role == "admin":
                await record_admin_login_failure(data.email, _client_ip(request))
            raise HTTPException(status_code=401, detail=get_message("invalid_email_credentials"))

        if user.role == "admin":
            await clear_admin_login_failures(data.email)

        token = create_access_token(user.id)
        refresh_token = await create_refresh_token(
            db, user.id,
            user_agent=request.headers.get("user-agent"),
            platform=request.headers.get("x-client-platform", "mobile"),
        )
        logger.info(f"User logged in via email: {user.email}")
        return TokenResponse(
            access_token=token,
            refresh_token=refresh_token,
            user=UserOut.model_validate(user),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email login error for {data.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/google", response_model=TokenResponse)
async def google_auth(request: Request, data: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=SSL_CONTEXT) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": data.credential},
            )
        if resp.status_code != 200:
            logger.warning(f"Google token verification failed: HTTP {resp.status_code}")
            raise HTTPException(status_code=401, detail=get_message("invalid_token"))
        payload = resp.json()

        if not settings.GOOGLE_CLIENT_ID or payload.get("aud") != settings.GOOGLE_CLIENT_ID:
            logger.warning("Google token audience mismatch")
            raise HTTPException(status_code=401, detail=get_message("invalid_token"))

        google_id = payload.get("sub")
        email = payload.get("email")
        if not google_id:
            raise HTTPException(status_code=401, detail=get_message("invalid_token"))

        result = await db.execute(select(User).where(User.google_id == google_id))
        user = result.scalar_one_or_none()

        if user is None and email:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user is not None:
                user.google_id = google_id

        if user is None:
            user = User(
                full_name=payload.get("name") or (email.split("@")[0] if email else "Google user"),
                email=email,
                google_id=google_id,
                avatar_url=payload.get("picture"),
                hashed_password=hash_password(secrets.token_urlsafe(32)),
            )
            db.add(user)
            await db.flush()
            logger.info(f"New user registered via Google: {email or google_id}")
        else:
            logger.info(f"User logged in via Google: {email or google_id}")

        token = create_access_token(user.id)
        refresh_token = await create_refresh_token(
            db, user.id,
            user_agent=request.headers.get("user-agent"),
            platform=request.headers.get("x-client-platform", "mobile"),
        )
        return TokenResponse(
            access_token=token,
            refresh_token=refresh_token,
            user=UserOut.model_validate(user),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google auth error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Google auth failed")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    rotated = await rotate_refresh_token(
        db, data.refresh_token, user_agent=request.headers.get("user-agent")
    )
    if rotated is None:
        logger.info("Refresh attempted with invalid/expired/revoked token")
        raise HTTPException(status_code=401, detail=get_message("invalid_token"))
    user_id, new_refresh_token = rotated

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail=get_message("invalid_token"))

    access_token = create_access_token(user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=UserOut.model_validate(user),
    )


@router.post("/logout")
async def logout(data: LogoutRequest, db: AsyncSession = Depends(get_db)):
    await revoke_refresh_token(db, data.refresh_token)
    return {"status": "ok"}



@router.get("/sessions", response_model=list[SessionOut])
async def get_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_sessions(db, user.id)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await revoke_session(db, user.id, session_id):
        raise HTTPException(status_code=404, detail=get_message("not_found"))
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.flush()
    return UserOut.model_validate(user)


@router.put("/me", response_model=UserOut)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.language is not None:
        user.language = data.language
    await db.flush()
    return UserOut.model_validate(user)


@router.post("/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(status_code=400, detail=get_message("invalid_file_type"))

        content = await file.read()
        if len(content) > settings.MAX_AVATAR_SIZE:
            raise HTTPException(status_code=400, detail=get_message("file_too_large"))

        os.makedirs(AVATAR_DIR, exist_ok=True)

        if user.avatar_url:
            old_path = os.path.join(AVATAR_DIR, os.path.basename(user.avatar_url))
            if os.path.exists(old_path):
                os.remove(old_path)
                logger.info(f"Old avatar removed for user {user.phone}")

        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(AVATAR_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(content)

        user.avatar_url = f"/uploads/avatars/{filename}"
        await db.flush()
        logger.info(f"Avatar uploaded for user {user.phone}")
        return UserOut.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar upload error for user {user.phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Avatar upload failed")


@router.delete("/avatar")
async def delete_avatar(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.avatar_url:
        raise HTTPException(status_code=404, detail=get_message("no_avatar"))
    filepath = os.path.join(os.path.dirname(__file__), "..", "..", user.avatar_url.lstrip("/"))
    if os.path.exists(filepath):
        os.remove(filepath)
    user.avatar_url = None
    await db.flush()
    logger.info(f"Avatar deleted for user {user.phone}")
    return UserOut.model_validate(user)


@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.current_password, user.hashed_password):
        logger.warning(f"Invalid password change attempt for user {user.id}")
        raise HTTPException(status_code=400, detail=get_message("invalid_current_password", user.language))
    if user.role == "admin":
        problem = password_strength_error(
            data.new_password, min_length=settings.ADMIN_MIN_PASSWORD_LENGTH
        )
        if problem:
            raise HTTPException(status_code=400, detail=get_message(problem, user.language))
    user.hashed_password = hash_password(data.new_password)
    await db.flush()
    await revoke_all_refresh_tokens(db, user.id)
    logger.info(f"Password changed for user {user.phone}")
    return {"status": "ok", "message": get_message("password_changed", user.language)}


@router.delete("/me")
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.delete(user)
    await db.flush()
    logger.info(f"Account deleted for user {user.phone}")
    return {"status": "ok", "message": get_message("account_deleted", user.language)}



@router.post("/forgot-password")
async def forgot_password(request: Request, data: ForgotPasswordRequest,
                          db: AsyncSession = Depends(get_db)):
    try:
        if not await _check_sms_limits(db, request):
            logger.warning(f"SMS rate limit exceeded for IP {_client_ip(request)}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))
        if not await _check_rate_limit(db, "forgot_password", data.phone, settings.MAX_FORGOT_ATTEMPTS):
            logger.warning(f"Rate limit exceeded for forgot password: {data.phone}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))

        result = await db.execute(select(User).where(User.phone == data.phone))
        user = result.scalar_one_or_none()
        if not user:
            return {"status": "ok", "message": "If the phone number exists, a code has been sent"}

        await db.execute(
            delete(PhoneVerificationCode).where(
                PhoneVerificationCode.phone == data.phone,
                PhoneVerificationCode.purpose == "reset",
                PhoneVerificationCode.used == False,
            )
        )

        code = f"{secrets.randbelow(1000000):06d}"
        row = PhoneVerificationCode(
            phone=data.phone,
            code=code,
            purpose="reset",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        db.add(row)
        await db.flush()

        sent = await send_sms_code(data.phone, code, user.language)
        if not sent:
            logger.error(f"Failed to send reset code to {data.phone}")
            raise HTTPException(status_code=500, detail=get_message("sms_send_error"))

        logger.info(f"Password reset code sent to {data.phone}")
        return {"status": "ok", "message": "Code sent"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forgot password error for {data.phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Forgot password failed")


@router.post("/verify-code")
async def verify_code(data: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    try:
        if not await _check_rate_limit(db, "verify_code", data.phone, settings.MAX_VERIFY_ATTEMPTS):
            logger.warning(f"Rate limit exceeded for verify code: {data.phone}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))

        result = await db.execute(
            select(PhoneVerificationCode).where(
                PhoneVerificationCode.phone == data.phone,
                PhoneVerificationCode.code == data.code,
                PhoneVerificationCode.purpose == "reset",
                PhoneVerificationCode.used == False,
                PhoneVerificationCode.verified == False,
            ).order_by(PhoneVerificationCode.created_at.desc())
        )
        row = result.scalar_one_or_none()

        if not row:
            logger.warning(f"Invalid verification code for {data.phone}")
            raise HTTPException(status_code=400, detail=get_message("invalid_code"))

        now = datetime.now(timezone.utc)
        expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        if expires < now:
            logger.warning(f"Expired verification code for {data.phone}")
            raise HTTPException(status_code=400, detail=get_message("code_expired"))

        row.verified = True
        await db.flush()

        logger.info(f"Code verified for {data.phone}")
        return {"status": "ok", "message": get_message("code_verified")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verify code error for {data.phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Verify code failed")


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(PhoneVerificationCode).where(
                PhoneVerificationCode.phone == data.phone,
                PhoneVerificationCode.code == data.code,
                PhoneVerificationCode.purpose == "reset",
                PhoneVerificationCode.verified == True,
                PhoneVerificationCode.used == False,
            ).order_by(PhoneVerificationCode.created_at.desc())
        )
        row = result.scalar_one_or_none()

        if not row:
            logger.warning(f"Invalid reset password token for {data.phone}")
            raise HTTPException(status_code=400, detail=get_message("invalid_code"))

        now = datetime.now(timezone.utc)
        expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        if expires < now:
            logger.warning(f"Expired reset password token for {data.phone}")
            raise HTTPException(status_code=400, detail=get_message("code_expired"))

        row.used = True

        user_result = await db.execute(select(User).where(User.phone == data.phone))
        user = user_result.scalar_one_or_none()
        if not user:
            logger.error(f"User not found during password reset: {data.phone}")
            raise HTTPException(status_code=404, detail=get_message("user_not_found"))

        if user.role == "admin":
            problem = password_strength_error(
                data.new_password, min_length=settings.ADMIN_MIN_PASSWORD_LENGTH
            )
            if problem:
                raise HTTPException(status_code=400, detail=get_message(problem, user.language))

        user.hashed_password = hash_password(data.new_password)
        await db.flush()
        await revoke_all_refresh_tokens(db, user.id)
        if user.role == "admin":
            await clear_admin_login_failures(data.phone)

        logger.info(f"Password reset successfully for {data.phone}")
        return {"status": "ok", "message": get_message("password_changed")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error for {data.phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Reset password failed")
