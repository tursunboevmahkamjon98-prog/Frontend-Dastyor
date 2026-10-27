import io
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import BalanceTopupRequest, User
from app.schemas import (
    BalanceOut, PayInstructionsOut, TelegramLinkCodeOut, TelegramLinkOut, TelegramLinkStatusOut,
    TopupRequestOut,
)
from app.auth import get_current_user
from app.logger import get_logger
from app.security import enforce_user_quota
from app.telegram import service as telegram_service
from app.telegram.config import get_telegram_settings

logger = get_logger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])

_RECEIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "receipts")
_RECEIPT_MAX_DIM = 2000


def _save_receipt(raw: bytes) -> str | None:
    """Save an uploaded receipt photo, return its public `/uploads/...` path.

    Re-encoded to PNG the same way lesson images are — not to touch the
    teacher's photo, but so a corrupt or disguised non-image file (the
    thing an upload endpoint must never trust) fails here with `None`
    instead of landing on disk at all.
    """
    try:
        os.makedirs(_RECEIPTS_DIR, exist_ok=True)
        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            flat = Image.new("RGB", img.size, (255, 255, 255))
            flat.paste(img, mask=img.split()[-1])
            img = flat
        else:
            img = img.convert("RGB")
        img.thumbnail((_RECEIPT_MAX_DIM, _RECEIPT_MAX_DIM), Image.LANCZOS)
        filename = f"{uuid.uuid4().hex}.png"
        img.save(os.path.join(_RECEIPTS_DIR, filename), "PNG")
        return f"/uploads/receipts/{filename}"
    except Exception as e:
        logger.warning(f"Receipt image save failed: {e}")
        return None


def _topup_out(row: BalanceTopupRequest) -> TopupRequestOut:
    return TopupRequestOut(
        id=row.id,
        requested_somoni=row.requested_dirams / 100,
        note=row.note,
        receipt_url=row.receipt_path,
        status=row.status,
        credited_somoni=(row.credited_dirams / 100) if row.credited_dirams is not None else None,
        admin_note=row.admin_note,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
    )


@router.get("/balance", response_model=BalanceOut)
async def get_balance(user: User = Depends(get_current_user)):
    return BalanceOut(balance_somoni=user.balance_somoni)


@router.get("/telegram/status", response_model=TelegramLinkStatusOut)
async def telegram_link_status(user: User = Depends(get_current_user)):
    """Whether this account already has a Telegram chat bound to it.

    The app calls this to decide what the Telegram button says — "link"
    or "open" — and to hide the button entirely on a deployment where the
    bot has not been configured, rather than offering a dead link.
    """
    status = await telegram_service.link_status(user.id)
    return TelegramLinkStatusOut(**status)


@router.get("/telegram/standalone-status", response_model=TelegramLinkStatusOut)
async def standalone_telegram_link_status(user: User = Depends(get_current_user)):
    """Status of the separate bot used by the balance page."""
    from app.config import get_settings
    import re

    settings = get_settings()
    status = await telegram_service.link_status(user.id)
    username = settings.DASTYOR_STANDALONE_BOT_USERNAME.strip().lstrip("@")
    status["bot_username"] = username
    status["bot_configured"] = bool(
        re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", username)
        and len(settings.DASTYOR_BOT_API_TOKEN) >= 32
        and settings.DASTYOR_STANDALONE_TELEGRAM_TOKEN
        and settings.DASTYOR_BOT_ROOT_ADMIN_ID > 0
    )
    return TelegramLinkStatusOut(**status)


@router.delete("/telegram/link", response_model=TelegramLinkStatusOut)
async def delete_telegram_link(user: User = Depends(get_current_user)):
    """Disconnect this account's Telegram chat.

    The bot has its own ``/unlink``, but that one needs the Telegram
    account. This path needs only the Dastyor password, which is what
    makes it the one that still works when the phone has been lost or
    sold with the Telegram session still signed in — exactly when
    unlinking matters most.

    Idempotent: unlinking an account that is not linked is a success,
    not an error, because the caller's goal is already true.
    """
    result = await telegram_service.unlink_account(
        user_id=user.id, actor="app"
    )
    if result.outcome == "unlinked":
        logger.warning(
            f"User {user.id} unlinked their Telegram chat from the app "
            f"(admin_revoked={result.admin_revoked}, "
            f"open_requests={result.open_requests})"
        )
    return TelegramLinkStatusOut(**await telegram_service.link_status(user.id))


@router.post("/telegram/link", response_model=TelegramLinkOut)
async def create_telegram_link(user: User = Depends(get_current_user)):
    """Mint a single-use deep link that binds this account to a Telegram chat.

    This is the only new HTTP route in the payment feature, and it is
    behind the same ``get_current_user`` JWT dependency as everything
    else — there is no unauthenticated endpoint anywhere in the flow, and
    in particular nothing that can approve a payment over HTTP.

    What goes into the link is one opaque random token and nothing else:
    no email, no phone, no balance, no access token, no user id. The
    backend stores only ``sha256(token)`` alongside the authenticated
    user id, so the link is useless to anyone who finds it after it has
    been redeemed or expired.

    Throttled per user because a stolen session should not be able to
    mint an unbounded supply of valid linking tokens.
    """
    settings = get_telegram_settings()
    if not settings.configured:
        # 503, not 500: the server is fine, the owner has not set
        # TELEGRAM_BOT_TOKEN / TELEGRAM_BOT_USERNAME yet. The app shows a
        # "not available yet" message instead of a broken button.
        raise HTTPException(
            status_code=503,
            detail="Telegram payment bot is not configured on this server",
        )

    # 30/hour, not 10.
    #
    # The throttle guards against a stolen session minting tokens in
    # bulk, but that buys an attacker nothing: a token is single-use,
    # dies in five minutes, and redeeming it binds the chat to the
    # authenticated account it was minted for — never to the attacker's.
    #
    # The cost of setting it too low is concrete, and was hit in
    # practice: when Telegram fails to open (an ISP blocking t.me, for
    # instance) a teacher presses the button again, and at ten per hour
    # they are locked out mid-problem by their own retries — with a
    # generic "too many requests" that explains none of it.
    try:
        await enforce_user_quota(user.id, "telegram_link", max_attempts=30,
                                 window_seconds=3600)
    except HTTPException as e:
        if e.status_code != 429:
            raise
        raise HTTPException(
            status_code=429,
            detail=(
                "Слишком много попыток привязки за последний час. "
                "Подождите немного и попробуйте снова — ваш аккаунт в "
                "порядке, это ограничение Dastyor, а не Telegram."
            ),
            headers=e.headers,
        ) from None

    issued = await telegram_service.issue_link_token(user.id)
    expires_in = max(
        0, int((issued.expires_at - datetime.now(timezone.utc)).total_seconds())
    )

    logger.info(f"Telegram link requested by user {user.id}")
    return TelegramLinkOut(
        deep_link=issued.deep_link,
        app_link=issued.app_link,
        start_command=issued.start_command,
        bot_username=issued.bot_username,
        expires_at=issued.expires_at,
        expires_in_seconds=expires_in,
    )


@router.get("/pay-instructions", response_model=PayInstructionsOut)
async def get_pay_instructions(user: User = Depends(get_current_user)):
    """The same card/requisites text an administrator sets with `/paycontrol`.

    One instruction either way a teacher reaches Dastyor — by bot or by
    the app — so there is exactly one place an administrator has to keep
    it current, not two that can drift apart.
    """
    return PayInstructionsOut(text=(await telegram_service.get_pay_instructions()).strip())


@router.post("/telegram/standalone-link", response_model=TelegramLinkOut)
async def create_standalone_telegram_link(user: User = Depends(get_current_user)):
    """Issue the existing one-use link token for the separate Telegram bot."""
    from app.config import get_settings
    import re

    bot_settings = get_settings()
    username = bot_settings.DASTYOR_STANDALONE_BOT_USERNAME.strip().lstrip("@")
    if (not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", username)
            or len(bot_settings.DASTYOR_BOT_API_TOKEN) < 32
            or not bot_settings.DASTYOR_STANDALONE_TELEGRAM_TOKEN
            or bot_settings.DASTYOR_BOT_ROOT_ADMIN_ID <= 0):
        raise HTTPException(status_code=503, detail="Standalone bot is not configured")
    await enforce_user_quota(user.id, "standalone_telegram_link", max_attempts=30,
                             window_seconds=3600)
    issued = await telegram_service.issue_link_token(user.id, bot_username=username)
    return TelegramLinkOut(
        deep_link=issued.deep_link, app_link=issued.app_link,
        start_command=issued.start_command, bot_username=issued.bot_username,
        expires_at=issued.expires_at,
        expires_in_seconds=max(0, int((issued.expires_at - datetime.now(timezone.utc)).total_seconds())),
    )


@router.post("/telegram/standalone-code", response_model=TelegramLinkCodeOut)
async def create_standalone_telegram_code(user: User = Depends(get_current_user)):
    """Issue a short-lived code from the logged-in account for manual bot linking."""
    from app.config import get_settings
    import re

    settings = get_settings()
    username = settings.DASTYOR_STANDALONE_BOT_USERNAME.strip().lstrip("@")
    if (not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", username)
            or len(settings.DASTYOR_BOT_API_TOKEN) < 32
            or not settings.DASTYOR_STANDALONE_TELEGRAM_TOKEN
            or settings.DASTYOR_BOT_ROOT_ADMIN_ID <= 0):
        raise HTTPException(status_code=503, detail="Standalone bot is not configured")
    await enforce_user_quota(user.id, "standalone_telegram_code", max_attempts=15,
                             window_seconds=3600)
    issued = await telegram_service.issue_link_code(user.id)
    return TelegramLinkCodeOut(
        code=issued.code,
        bot_username=username,
        expires_at=issued.expires_at,
        expires_in_seconds=max(0, int((issued.expires_at - datetime.now(timezone.utc)).total_seconds())),
    )


@router.post("/topup-requests", response_model=TopupRequestOut, status_code=201)
async def create_topup_request(
    amount_somoni: float = Form(...),
    note: str | None = Form(default=None),
    receipt: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """A teacher's declaration that they transferred money — credits nothing.

    Exactly like the Telegram flow this mirrors: an administrator reads
    this in the admin console, checks their own bank app, and types the
    amount to credit by hand. Nothing here touches `balance_dirams`.
    """
    if amount_somoni <= 0 or amount_somoni > 10_000:
        raise HTTPException(status_code=400, detail="Введите сумму от 0 до 10000 сомони")

    await enforce_user_quota(user.id, "topup_request", max_attempts=10, window_seconds=3600)

    receipt_path = None
    if receipt is not None:
        raw = await receipt.read()
        if len(raw) > 8 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Файл слишком большой (макс. 8 МБ)")
        receipt_path = _save_receipt(raw)
        if receipt_path is None:
            raise HTTPException(status_code=422, detail="Не удалось прочитать изображение")

    row = BalanceTopupRequest(
        user_id=user.id,
        requested_dirams=round(amount_somoni * 100),
        note=(note or "").strip()[:255] or None,
        receipt_path=receipt_path,
    )
    db.add(row)
    await db.flush()
    logger.info(f"Web top-up request {row.id} created by user {user.id}: {amount_somoni} somoni")
    return _topup_out(row)


@router.get("/topup-requests/mine", response_model=list[TopupRequestOut])
async def list_my_topup_requests(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BalanceTopupRequest)
        .where(BalanceTopupRequest.user_id == user.id)
        .order_by(BalanceTopupRequest.created_at.desc())
        .limit(20)
    )
    return [_topup_out(row) for row in result.scalars().all()]
