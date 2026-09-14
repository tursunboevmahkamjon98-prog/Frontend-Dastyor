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

# __file__ is app/routers/auth.py, two levels below the backend root where
# main.py mounts StaticFiles(UPLOAD_DIR="<root>/uploads") — this must land
# in that same directory or uploaded avatars save successfully but then
# 404 forever from the mounted /uploads/... URL (previously only went up
# one level, landing in app/uploads/ instead, which nothing serves).
AVATAR_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "avatars")
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}

# ── DB-backed rate limiter ───────────────────────────────────────────────
# Was a handful of plain in-memory dicts — reset on every restart and
# invisible to any other worker process/replica, so brute-force
# protection quietly weakened itself exactly when scaling past one
# process is what makes it matter. See models.RateLimitAttempt's
# docstring. "purpose" strings below (register_code/login/login_verify/
# email_login/forgot_password/verify_code) are what used to be six
# separate dicts, now six independent counters in one table.
_RATE_WINDOW = settings.RATE_WINDOW


async def _check_sms_limits(db: AsyncSession, request: Request) -> bool:
    """True if one more verification code may be sent.

    Three checks, in the order of what they protect:

    1. the DAILY BUDGET across every caller — the only limit that bounds
       what this can cost, because an attacker with many addresses
       defeats any per-address rule;
    2. a burst window per address, which catches machine speed without
       touching a school or a carrier's shared address (see config);
    3. an hourly ceiling per address, for slow grinding.

    The per-PHONE limiter at each call site is separate and unchanged —
    that one is precise, and protects an individual number from being
    flooded with texts no matter where the requests come from."""
    ip = _client_ip(request)
    if not await _check_rate_limit(db, "sms_ip_burst", ip,
                                   settings.MAX_SMS_PER_IP_BURST,
                                   settings.RATE_WINDOW_IP_BURST):
        return False
    if not await _check_rate_limit(db, "sms_ip", ip,
                                   settings.MAX_SMS_PER_IP,
                                   settings.RATE_WINDOW_IP):
        return False
    # The budget is charged LAST, and only by a request that has passed
    # everything else. Charging it first meant a burst of 120 blocked
    # requests still spent 120 of the day's 500 — an attacker could
    # exhaust the budget with requests that never sent an SMS, and take
    # the codes away from real users without paying for a single text.
    # Measured; that is exactly what happened.
    if not await _check_rate_limit(db, "sms_global", "all",
                                   settings.MAX_SMS_PER_DAY, 86400):
        logger.error("SMS DAILY BUDGET REACHED — no further codes will be sent today. "
                     "Either this is an attack, or MAX_SMS_PER_DAY needs raising.")
        return False
    return True


def _client_ip(request: Request) -> str:
    """The caller's address, as far as it can be trusted.

    Behind Cloudflare the socket address is Cloudflare's edge — every
    user would share one address and one quota, which is precisely the
    lock-out this must avoid. CF-Connecting-IP carries the real client
    and is set by Cloudflare itself; X-Forwarded-For's first hop is the
    fallback for a plain nginx in front.

    Both headers are caller-supplied and therefore forgeable. That is
    acceptable for throttling — a forger gets a fresh quota, i.e. the
    position they would be in with no limit at all, while an ordinary
    flood from one address is still stopped. It must never be used for
    anything that grants access.
    """
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()[:60]
    forwarded = request.headers.get("x-forwarded-for") or ""
    if forwarded:
        return forwarded.split(",")[0].strip()[:60]
    return (request.client.host if request.client else "unknown")[:60]



async def _check_rate_limit(db: AsyncSession, purpose: str, key: str, max_attempts: int,
                            window: int | None = None) -> bool:
    """True and records this attempt if (purpose, key) is still under
    max_attempts within the last _RATE_WINDOW seconds; False (without
    recording) if not — a rejected attempt shouldn't itself extend how
    long the caller stays locked out.

    Commits immediately rather than just flushing: this is called before
    the caller's real work (e.g. checking a password), which routinely
    ends by *raising* HTTPException for the totally expected "wrong
    password" case — get_db's dependency rolls back the whole request's
    transaction on any exception, which was silently wiping out every
    recorded attempt for exactly the failed-login case rate limiting
    exists to catch. Committing here first means the attempt record
    survives regardless of what the rest of the request does.
    """
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


# ── Register (phone + SMS OTP) ────────────────────────────────────────────
# Two steps: send-code sends the SMS and stores nothing user-facing yet;
# register verifies that code and only THEN creates the User row — unlike
# the old email flow there's never a "registered but unconfirmed" account
# sitting in the users table.

@router.post("/register/send-code")
async def send_register_code(request: Request, data: SendRegisterCodeRequest,
                             db: AsyncSession = Depends(get_db)):
    try:
        # Per-IP first: the phone-keyed check below is useless against a
        # script that changes the number every request, and every request
        # it lets through is a paid SMS.
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
        # Accounts are what the free tier is attached to (one free
        # konspekt, test, presentation and lecture each), so a script
        # that registers in a loop gets unlimited free generations —
        # which is AI spend, not just noise.
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

        # Checked BEFORE the password comparison and BEFORE the user
        # lookup result is acted on, so a locked admin account gets the
        # same answer whether or not the guessed password was right.
        if await admin_login_blocked(data.phone):
            logger.warning(f"Admin sign-in blocked (lockout active): {data.phone}")
            raise HTTPException(status_code=429, detail=get_message("admin_locked"))

        result = await db.execute(select(User).where(User.phone == data.phone))
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.hashed_password):
            logger.warning(f"Failed login attempt for phone: {data.phone}")
            # Recorded only for accounts that actually hold the admin
            # role. Counting failures against every account would let
            # anyone lock any teacher out of their own account just by
            # guessing wrong at their number five times — a denial of
            # service handed to the attacker. The admin panel is worth
            # that trade; an ordinary account is not, and is already
            # covered by the per-phone/per-IP throttles above.
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
    """Step 1 of the mobile app's OTP login. Checks credentials exactly
    like /login; on success either sends an SMS code (normal case) or —
    for settings.OTP_BYPASS_PHONE only — returns real tokens right away,
    same shape as /login, so a fixed test/demo account never has to wait
    on a code. The frontend tells the two cases apart by whether the
    response has `access_token`."""
    try:
        if not await _check_sms_limits(db, request):
            logger.warning(f"SMS rate limit exceeded for IP {_client_ip(request)}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))
        if not await _check_rate_limit(db, "login", data.phone, settings.MAX_LOGIN_ATTEMPTS):
            logger.warning(f"Rate limit exceeded for login send-code: {data.phone}")
            raise HTTPException(status_code=429, detail=get_message("too_many_attempts"))
        # Same admin lockout /login enforces — this endpoint checks the
        # same password against the same account, so leaving it out here
        # would just move the guessing one route over.
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

        # Admin accounts skip SMS entirely, not just the one fixed demo
        # number — they're hand-provisioned (see create_admin_*.py-style
        # scripts / the admin panel), and an admin stuck waiting on SMS
        # delivery to get into their own mobile app isn't the point of
        # the OTP step, which exists to verify a *new* teacher's phone.
        #
        # A device that already passed an OTP for this account skips it
        # too (see models.TrustedDevice): the code proves the person holds
        # the number, and re-proving that to the same laptop on every
        # single sign-in was the actual complaint — the password check
        # above still has to pass either way.
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
    """Step 2 — trades the code login_send_code sent for tokens."""
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
        # This request just proved the person holds the number, so the
        # device can be remembered and skip the code next time (see
        # models.TrustedDevice). This is the ONLY place a device token is
        # minted — the bypass path in login_send_code deliberately does
        # not, since nothing was verified there.
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
    """Direct email+password registration, no OTP step — see
    schemas.EmailRegister's docstring for why."""
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

        # The ADMIN_EMAIL-provisioned account (see main.py) is reachable
        # through this route as well as the phone one, so it gets the
        # same lockout, keyed on the email it was tried against.
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
    """Sign in (or silently register) via Google Identity Services. The
    frontend never sees anything but the opaque `credential` JWT GIS hands
    back — we're the only side that decodes it, and only after Google's
    own tokeninfo endpoint has confirmed the signature/expiry are valid,
    so nothing here trusts a claim the client could have forged.
    google_id (Google's stable "sub" claim) is the actual match key, the
    same role `phone` plays for the OTP flow above; email is a fallback
    match only, for a Google sign-in from someone who already has a
    phone+password account under that email."""
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
            # Link to a pre-existing phone+password account with the same
            # (Google-verified) email instead of creating a duplicate.
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
                # No password was ever set — a random, never-shown hash
                # makes password login mathematically impossible for this
                # account rather than leaving hashed_password blank
                # (every other code path assumes it's always a string).
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
    """Trades a still-valid refresh token for a new access token — what the
    frontend's api.ts calls automatically on a 401 instead of bouncing the
    teacher to /login just because the 24h access token expired mid-session.
    No Authorization header needed/checked here on purpose: the access token
    that just expired is exactly what a client in this situation no longer
    has a valid one of."""
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
    """Revokes the refresh token server-side so it can't be used to mint
    new access tokens after this device signs out — clearing it from
    localStorage alone (what logout did before refresh tokens existed)
    only stops *this* device from using it, not someone who copied it."""
    await revoke_refresh_token(db, data.refresh_token)
    return {"status": "ok"}


# ── Linked devices (mobile app's Profile → Bog'langan qurilmalar) ─────────
# One row per still-active *web* sign-in (QR or password) — see
# RefreshToken.platform's docstring for why the phone's own session never
# shows up in its own list here, same as WhatsApp's own such screen.

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

        # Remove old avatar file if exists
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
    # Stricter minimum for an account that can credit balances, read every
    # teacher's material and promote other admins. Applied when the
    # password is SET, never at sign-in — see security.password_strength_error.
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


# ── Forgot / Reset Password (phone + SMS OTP) ────────────────────────────
# Same verified->used two-step shape as the old email flow, just phone-
# keyed and purpose="reset" scoped in PhoneVerificationCode so a code sent
# here can never be replayed against the "register" purpose (or vice
# versa) for the same phone number.

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
            # Don't reveal whether this phone number is registered
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
        # An account that just proved control of the number and set a new
        # password is no longer the subject of an in-progress guessing
        # attempt; leaving the lockout in place would keep the legitimate
        # owner out of the panel they just recovered.
        if user.role == "admin":
            await clear_admin_login_failures(data.phone)

        logger.info(f"Password reset successfully for {data.phone}")
        return {"status": "ok", "message": get_message("password_changed")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error for {data.phone}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Reset password failed")
