import io
import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import BalanceTopupRequest, PaymentRequest, User
from app.schemas import (
    BalanceOut, PayInstructionsOut, TelegramLinkCodeOut, TelegramLinkOut, TelegramLinkStatusOut,
    TopupRequestOut,
)
from app.auth import get_current_user
from app.logger import get_logger
from app.security import enforce_user_quota
from app.telegram import service as telegram_service
from app.telegram.ocr import cross_check, scan_receipt
from app.telegram.api import TelegramApiError, TelegramClient, TelegramTransportError
from app.telegram.config import get_telegram_settings
from app.telegram.admin_ui import review as review_keyboard

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
    return TelegramLinkStatusOut(linked=False, bot_configured=False, bot_username="")


@router.get("/telegram/standalone-status", response_model=TelegramLinkStatusOut)
async def standalone_telegram_link_status(user: User = Depends(get_current_user)):
    return TelegramLinkStatusOut(linked=False, bot_configured=False, bot_username="")


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
    raise HTTPException(status_code=410, detail="Payments are submitted on the website. The Telegram bot is for admins only.")


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
    raise HTTPException(status_code=410, detail="Payments are submitted on the website. The Telegram bot is for admins only.")


@router.post("/telegram/standalone-code", response_model=TelegramLinkCodeOut)
async def create_standalone_telegram_code(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Payments are submitted on the website. The Telegram bot is for admins only.")


@router.post("/topup-requests", response_model=TopupRequestOut, status_code=201)
async def create_topup_request(
    http_request: Request,
    amount_somoni: float = Form(...),
    note: str | None = Form(default=None),
    bank_name: str = Form(default=""),
    sender_wallet: str = Form(default=""),
    receipt: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a web balance top-up for an admin to review in Telegram."""
    if amount_somoni < 5 or amount_somoni > 100 or not amount_somoni.is_integer():
        raise HTTPException(status_code=400, detail="Miqdor 5 dan 100 somonigacha bo‘lishi kerak")
    bank_name = bank_name.strip()
    sender_wallet = sender_wallet.strip()
    if bank_name not in {"Eskhata", "Dushanbe City"}:
        raise HTTPException(status_code=400, detail="Bankni tanlang")
    if len(sender_wallet) < 5 or len(sender_wallet) > 64:
        raise HTTPException(status_code=400, detail="Hamyon raqamini tekshiring")
    if receipt is None:
        raise HTTPException(status_code=400, detail="Chek rasmini yuklang")

    await enforce_user_quota(user.id, "topup_request", max_attempts=10, window_seconds=3600)

    raw = await receipt.read()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Chek 8 MB dan kichik bo‘lishi kerak")
    mime = (receipt.content_type or "").lower()
    if mime not in {"image/jpeg", "image/png", "image/webp", "application/pdf"}:
        raise HTTPException(status_code=422, detail="JPG, PNG, WEBP yoki PDF chek yuklang")
    receipt_path = _save_receipt(raw) if mime != "application/pdf" else None
    if mime != "application/pdf" and receipt_path is None:
        raise HTTPException(status_code=422, detail="Chek faylini o‘qib bo‘lmadi")
    if mime == "application/pdf":
        os.makedirs(_RECEIPTS_DIR, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.pdf"
        with open(os.path.join(_RECEIPTS_DIR, filename), "wb") as out:
            out.write(raw)
        receipt_path = f"/uploads/receipts/{filename}"

    dirams = round(amount_somoni * 100)
    chat_id = 0  # Web payments have no customer Telegram chat.
    request = await telegram_service.create_payment_request(user.id, chat_id, dirams)
    scan = scan_receipt(raw, mime)
    scan.sender = sender_wallet
    scan.recipient = bank_name
    cross_check(scan, requested_dirams=dirams)
    public_file = f"{str(http_request.base_url).rstrip('/')}{receipt_path}"
    await telegram_service.attach_receipt(
        request.id, file_id=public_file, mime=mime, size_bytes=len(raw),
        scan=scan, stored_path=receipt_path,
    )

    admin_ids = sorted(await telegram_service.all_admin_ids())
    if admin_ids:
        try:
            async with TelegramClient() as client:
                caption = (
                    f"🔔 Новая заявка на пополнение: {request.public_code}\n"
                    f"Пользователь: {user.full_name} (#{user.short_id or '—'})\n"
                    f"Банк: {bank_name}\nКошелёк отправителя: {sender_wallet}\n"
                    f"Сумма: {amount_somoni:.2f} сомони\n"
                    "Проверьте поступление в банковском приложении, затем выберите действие."
                )
                keyboard = review_keyboard(request.id)
                for admin_id in admin_ids:
                    try:
                        is_pdf = mime == "application/pdf"
                        await client.call(
                            "sendDocument" if is_pdf else "sendPhoto",
                            {"chat_id": admin_id, "caption": caption,
                             "reply_markup": json.dumps(keyboard, ensure_ascii=False)},
                            files={"document" if is_pdf else "photo": (
                                "receipt.pdf" if is_pdf else "receipt.png", raw, mime
                            )},
                        )
                    except (TelegramApiError, TelegramTransportError) as exc:
                        logger.error(f"Telegram top-up notification failed for {request.public_code}: {exc}")
        except Exception as exc:
            logger.error(f"Could not initialize admin bot notification: {type(exc).__name__}")

    logger.info(f"Web payment request {request.public_code} created for user {user.id}")
    return TopupRequestOut(
        id=request.id, requested_somoni=amount_somoni,
        note=f"{bank_name} · {sender_wallet}", receipt_url=receipt_path,
        status="pending", created_at=datetime.now(timezone.utc),
    )


@router.get("/topup-requests/mine", response_model=list[TopupRequestOut])
async def list_my_topup_requests(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PaymentRequest)
        .where(PaymentRequest.user_id == user.id)
        .order_by(PaymentRequest.created_at.desc())
        .limit(20)
    )
    return [TopupRequestOut(
        id=row.id,
        requested_somoni=row.requested_dirams / 100,
        note=f"{row.ocr_recipient or ''} · {row.ocr_sender or ''}".strip(" ·"),
        receipt_url=row.receipt_path,
        status=row.status,
        credited_somoni=(row.credited_dirams / 100) if row.credited_dirams else None,
        admin_note=row.decision_note,
        created_at=row.created_at,
        resolved_at=row.decided_at,
    ) for row in result.scalars().all()]
