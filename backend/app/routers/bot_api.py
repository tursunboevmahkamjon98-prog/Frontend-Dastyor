"""Service-only HTTP API for the separate Dastyor Telegram bot.

The bearer authenticates the bot process. Telegram IDs are still resolved
against backend links and reviewer grants on every relevant operation.
"""
from __future__ import annotations

import hmac
import io
import secrets
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import PaymentAuditLog, PaymentRequest, StandaloneBotAdmin, TelegramAccount, User
from app.security import enforce_user_quota
from app.telegram import service
from app.telegram.config import get_telegram_settings

router = APIRouter(prefix="/api/bot/v1", tags=["standalone-bot"])


def require_bot(authorization: str | None = Header(default=None)) -> None:
    expected = get_settings().DASTYOR_BOT_API_TOKEN
    if len(expected) < 32:
        raise HTTPException(status_code=503, detail="Bot API is not configured")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not authorization or not authorization.startswith("Bearer ") or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/health", dependencies=[Depends(require_bot)])
async def bot_health(db: AsyncSession = Depends(get_db)):
    """Non-secret handshake for the bot's startup; no writes or Telegram calls."""
    from app.preflight import ConfigurationError, validate_backend_config
    settings = get_settings()
    try:
        validate_backend_config(settings, require_bot=True)
    except ConfigurationError:
        raise HTTPException(status_code=503, detail="Bot configuration incomplete") from None
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "api_version": 1,
            "root_admin_id": settings.DASTYOR_BOT_ROOT_ADMIN_ID,
            "bot_username": settings.DASTYOR_STANDALONE_BOT_USERNAME.lstrip("@"),
            "telegram_bot_id": int(settings.DASTYOR_STANDALONE_TELEGRAM_TOKEN.split(":", 1)[0]),
            "max_topup_dirams": min(1_000_000, get_telegram_settings().TELEGRAM_MAX_TOPUP_DIRAMS)}


class LinkIn(BaseModel):
    token: str = Field(min_length=6, max_length=128,
                       pattern=r"^(?:[0-9]{6}|[A-Za-z0-9_-]{20,128})$")
    telegram_id: int = Field(gt=0)
    chat_id: int = Field(gt=0)


class TopupIn(BaseModel):
    telegram_id: int = Field(gt=0)
    chat_id: int = Field(gt=0)
    amount_dirams: int = Field(gt=0)
    telegram_file_id: str = Field(min_length=5, max_length=255)
    receipt_mime: str = Field(max_length=100)
    receipt_kind: str = Field(max_length=20)
    client_request_key: str = Field(pattern=r"^[A-Za-z0-9:_-]{8,100}$")


class DecisionIn(BaseModel):
    admin_telegram_id: int = Field(gt=0)
    reason: str = Field(default="", max_length=500)


class AdminGrantIn(BaseModel):
    root_telegram_id: int = Field(gt=0)


async def linked_user(db: AsyncSession, telegram_id: int, chat_id: int | None = None) -> User:
    query = (select(User).join(TelegramAccount, TelegramAccount.user_id == User.id)
             .where(TelegramAccount.telegram_user_id == telegram_id,
                    TelegramAccount.revoked.is_(False)))
    if chat_id is not None:
        query = query.where(TelegramAccount.chat_id == chat_id)
    user = (await db.execute(query)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Linked account not found")
    return user


async def require_admin_id(db: AsyncSession, telegram_id: int) -> None:
    if telegram_id <= 0:
        raise HTTPException(status_code=403, detail="Administrator required")
    root = get_settings().DASTYOR_BOT_ROOT_ADMIN_ID
    if root > 0 and telegram_id == root:
        return
    granted = (await db.execute(select(StandaloneBotAdmin.telegram_user_id).where(
        StandaloneBotAdmin.telegram_user_id == telegram_id))).scalar_one_or_none()
    if granted is None:
        raise HTTPException(status_code=403, detail="Administrator required")


async def review_admin(db: AsyncSession, x_telegram_admin_id: int | None) -> None:
    await require_admin_id(db, x_telegram_admin_id or 0)


async def verify_receipt(file_id: str, mime: str, kind: str) -> int:
    """Fetch with this bot's token and validate bytes; never persist raw media."""
    if kind not in ("photo", "document") or mime not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=422, detail="Unsupported receipt format")
    token = get_settings().DASTYOR_STANDALONE_TELEGRAM_TOKEN
    if not token:
        raise HTTPException(status_code=503, detail="Receipt verification is not configured")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            info = await client.post(f"https://api.telegram.org/bot{token}/getFile", json={"file_id": file_id})
            info.raise_for_status()
            payload = info.json()
            if not payload.get("ok"):
                raise ValueError("Telegram file lookup failed")
            file = payload["result"]
            if file.get("file_size", 0) > 8 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Receipt too large")
            file_path = file["file_path"]
            if not isinstance(file_path, str) or not file_path.startswith(("photos/", "documents/")) or ".." in file_path:
                raise ValueError("Invalid Telegram file path")
            async with client.stream("GET", f"https://api.telegram.org/file/bot{token}/{file_path}") as response:
                response.raise_for_status()
                chunks = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 8 * 1024 * 1024:
                        raise HTTPException(status_code=413, detail="Receipt too large")
                    chunks.append(chunk)
            with Image.open(io.BytesIO(b"".join(chunks))) as image:
                if image.format not in ("JPEG", "PNG", "WEBP"):
                    raise ValueError("Unsupported image")
                image.verify()
            return size
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, KeyError, OSError):
        raise HTTPException(status_code=422, detail="Receipt could not be verified") from None


def topup_out(row: PaymentRequest, telegram_id: int | None = None,
              account_id: str | None = None, *, include_receipt: bool = False) -> dict:
    return {
        "id": row.id, "number": row.public_code, "amount_dirams": row.requested_dirams,
        "status": row.status, "created_at": row.created_at,
        "telegram_id": telegram_id if telegram_id is not None else row.chat_id,
        "account_id": account_id, "reason": row.decision_note,
        **({"receipt_file_id": row.receipt_file_id,
            "receipt_kind": row.receipt_kind or "document"} if include_receipt else {}),
    }


@router.post("/link/redeem", dependencies=[Depends(require_bot)])
async def redeem_link(body: LinkIn):
    if body.chat_id != body.telegram_id:
        raise HTTPException(status_code=422, detail="Private Telegram chat required")
    await enforce_user_quota(str(body.telegram_id), "telegram_link_redeem",
                             max_attempts=6, window_seconds=900)
    await enforce_user_quota("all", "telegram_link_redeem_global",
                             max_attempts=120, window_seconds=900)
    result = await service.redeem_link_token(body.token, body.chat_id, body.telegram_id)
    if result.outcome in ("invalid", "expired", "used"):
        raise HTTPException(status_code=409, detail="Link token invalid or expired")
    if result.outcome == "chat_taken":
        raise HTTPException(status_code=409, detail="Telegram account already linked elsewhere")
    if result.account is None:
        raise HTTPException(status_code=409, detail="Account could not be linked")
    return {"status": "linked", "account_id": result.account.short_id or result.account.user_id}


@router.get("/users/{telegram_id}/account", dependencies=[Depends(require_bot)])
async def account(telegram_id: int, db: AsyncSession = Depends(get_db)):
    user = await linked_user(db, telegram_id)
    return {"account_id": user.short_id or user.id}


@router.get("/users/{telegram_id}/balance", dependencies=[Depends(require_bot)])
async def balance(telegram_id: int, db: AsyncSession = Depends(get_db)):
    user = await linked_user(db, telegram_id)
    return {"balance_dirams": user.balance_dirams}


@router.get("/users/{telegram_id}/topups", dependencies=[Depends(require_bot)])
async def my_topups(telegram_id: int, db: AsyncSession = Depends(get_db)):
    user = await linked_user(db, telegram_id)
    rows = (await db.execute(select(PaymentRequest).where(PaymentRequest.user_id == user.id)
                             .order_by(PaymentRequest.created_at.desc()).limit(20))).scalars().all()
    return [topup_out(row, telegram_id, user.short_id or user.id) for row in rows]


@router.post("/topups", status_code=201, dependencies=[Depends(require_bot)])
async def create_topup(body: TopupIn, db: AsyncSession = Depends(get_db)):
    if body.chat_id != body.telegram_id:
        raise HTTPException(status_code=422, detail="Private Telegram chat required")
    user = await linked_user(db, body.telegram_id, body.chat_id)
    ceiling = min(1_000_000, get_telegram_settings().TELEGRAM_MAX_TOPUP_DIRAMS)
    if body.amount_dirams < 100 or body.amount_dirams > ceiling:
        raise HTTPException(status_code=422, detail="Invalid amount")
    previous = (await db.execute(select(PaymentRequest).where(
        PaymentRequest.client_request_key == body.client_request_key))).scalar_one_or_none()
    if previous:
        if (previous.user_id != user.id or previous.chat_id != body.chat_id
                or previous.requested_dirams != body.amount_dirams
                or previous.receipt_file_id != body.telegram_file_id
                or previous.receipt_mime != body.receipt_mime
                or previous.receipt_kind != body.receipt_kind):
            raise HTTPException(status_code=409, detail="Request key reused with different data")
        return topup_out(previous, body.telegram_id, user.short_id or user.id)
    # Serialize requests for the same Telegram file even when the sender
    # retries under a different message ID. The database check alone would
    # race between two sessions; the transaction lock closes that gap.
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:file_id))"),
                     {"file_id": body.telegram_file_id})
    duplicate = (await db.execute(select(PaymentRequest.id).where(
        PaymentRequest.receipt_file_id == body.telegram_file_id))).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Receipt already submitted")
    size = await verify_receipt(body.telegram_file_id, body.receipt_mime, body.receipt_kind)
    await enforce_user_quota(user.id, "standalone_topup", max_attempts=3, window_seconds=3600)
    row = PaymentRequest(
        id=str(uuid.uuid4()), public_code=f"DP-{secrets.token_hex(4).upper()}",
        client_request_key=body.client_request_key, user_id=user.id,
        chat_id=body.chat_id, requested_dirams=body.amount_dirams,
        status="pending", receipt_file_id=body.telegram_file_id,
        receipt_mime=body.receipt_mime, receipt_kind=body.receipt_kind,
        receipt_bytes=size,
    )
    db.add(row)
    db.add(PaymentAuditLog(
        payment_request_id=row.id, event="created", actor_kind="user",
        actor_telegram_id=body.telegram_id,
        detail='{"source":"standalone_bot"}',
    ))
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        existing = (await db.execute(select(PaymentRequest).where(
            PaymentRequest.client_request_key == body.client_request_key))).scalar_one_or_none()
        if (existing and existing.user_id == user.id and existing.chat_id == body.chat_id
                and existing.requested_dirams == body.amount_dirams
                and existing.receipt_file_id == body.telegram_file_id
                and existing.receipt_mime == body.receipt_mime
                and existing.receipt_kind == body.receipt_kind):
            return topup_out(existing, body.telegram_id, user.short_id or user.id)
        raise HTTPException(status_code=409, detail="Request conflict") from None
    await db.commit()
    return topup_out(row, body.telegram_id, user.short_id or user.id)


@router.get("/topups/stats", dependencies=[Depends(require_bot)])
async def topup_stats(
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    x_telegram_admin_id: int | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    await review_admin(db, x_telegram_admin_id)
    query = select(PaymentRequest.status, func.count(PaymentRequest.id),
                   func.coalesce(func.sum(PaymentRequest.credited_dirams), 0)).group_by(PaymentRequest.status)
    if from_date:
        query = query.where(PaymentRequest.created_at >= from_date)
    if to_date:
        query = query.where(PaymentRequest.created_at < to_date)
    rows = (await db.execute(query)).all()
    counts = {status: count for status, count, _ in rows}
    total_dirams = sum(total for status, _, total in rows if status == "approved")
    return {"pending": counts.get("pending", 0), "approved": counts.get("approved", 0),
            "rejected": counts.get("rejected", 0), "total": total_dirams / 100}


@router.get("/topups", dependencies=[Depends(require_bot)])
async def list_topups(
    status: str = "pending", limit: int = Query(default=20, ge=1, le=100),
    x_telegram_admin_id: int | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    await review_admin(db, x_telegram_admin_id)
    if status not in ("pending", "approved", "rejected"):
        raise HTTPException(status_code=422, detail="Invalid status")
    rows = (await db.execute(select(PaymentRequest).where(PaymentRequest.status == status)
                             .order_by(PaymentRequest.created_at.desc()).limit(limit))).scalars().all()
    return [topup_out(row) for row in rows]


@router.get("/topups/{request_id}", dependencies=[Depends(require_bot)])
async def topup_detail(
    request_id: str, x_telegram_admin_id: int | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    await review_admin(db, x_telegram_admin_id)
    row = (await db.execute(select(PaymentRequest).where(PaymentRequest.id == request_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Request not found")
    user = (await db.execute(select(User).where(User.id == row.user_id))).scalar_one_or_none()
    return topup_out(row, account_id=(user.short_id or user.id) if user else None,
                     include_receipt=True)


async def decision(request_id: str, body: DecisionIn, action: str, db: AsyncSession) -> dict:
    await require_admin_id(db, body.admin_telegram_id)
    if action == "reject" and not body.reason.strip():
        raise HTTPException(status_code=422, detail="Reason required")
    result = (await service.approve_payment(request_id, body.admin_telegram_id)
              if action == "approve" else await service.reject_payment(request_id, body.admin_telegram_id, body.reason.strip()))
    if result.outcome == "not_found":
        raise HTTPException(status_code=404, detail="Request not found")
    if result.outcome == "already_decided":
        raise HTTPException(status_code=409, detail="Request already decided")
    if result.outcome == "self_approval":
        raise HTTPException(status_code=403, detail="Cannot approve own request")
    if result.outcome != "applied" or result.request is None:
        raise HTTPException(status_code=409, detail="Request could not be decided")
    row = result.request
    return {"id": row.id, "number": row.public_code, "status": row.status,
            "telegram_id": row.chat_id, "reason": body.reason.strip() if action == "reject" else ""}


@router.post("/topups/{request_id}/approve", dependencies=[Depends(require_bot)])
async def approve_topup(request_id: str, body: DecisionIn, db: AsyncSession = Depends(get_db)):
    return await decision(request_id, body, "approve", db)


@router.post("/topups/{request_id}/reject", dependencies=[Depends(require_bot)])
async def reject_topup(request_id: str, body: DecisionIn, db: AsyncSession = Depends(get_db)):
    return await decision(request_id, body, "reject", db)


@router.get("/notifications", dependencies=[Depends(require_bot)])
async def pending_notifications(db: AsyncSession = Depends(get_db)):
    """Terminal standalone decisions awaiting Telegram delivery."""
    rows = (await db.execute(
        select(PaymentRequest, TelegramAccount.telegram_user_id)
        .join(TelegramAccount, TelegramAccount.user_id == PaymentRequest.user_id)
        .where(PaymentRequest.client_request_key.is_not(None),
               PaymentRequest.status.in_(("approved", "rejected")),
               PaymentRequest.standalone_notification_sent_at.is_(None),
               TelegramAccount.revoked.is_(False))
        .order_by(PaymentRequest.decided_at, PaymentRequest.id)
        .limit(50)
    )).all()
    return [{"id": row.id, "number": row.public_code, "status": row.status,
             "telegram_id": telegram_id, "reason": row.decision_note or ""}
            for row, telegram_id in rows if telegram_id is not None]


@router.post("/notifications/{request_id}/ack", dependencies=[Depends(require_bot)])
async def acknowledge_notification(request_id: str, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(PaymentRequest).where(
        PaymentRequest.id == request_id,
        PaymentRequest.client_request_key.is_not(None),
        PaymentRequest.status.in_(("approved", "rejected"))))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if row.standalone_notification_sent_at is None:
        row.standalone_notification_sent_at = datetime.now(timezone.utc)
        await db.commit()
    return {"status": "acknowledged"}


@router.put("/admins/{telegram_id}", dependencies=[Depends(require_bot)])
async def grant_admin(telegram_id: int, body: AdminGrantIn, db: AsyncSession = Depends(get_db)):
    root = get_settings().DASTYOR_BOT_ROOT_ADMIN_ID
    if root <= 0 or body.root_telegram_id != root or telegram_id <= 0 or telegram_id == root:
        raise HTTPException(status_code=403, detail="Root administrator required")
    existing = await db.get(StandaloneBotAdmin, telegram_id)
    if not existing:
        db.add(StandaloneBotAdmin(telegram_user_id=telegram_id, granted_by_telegram_id=root))
        await db.flush()
        await db.commit()
    return {"telegram_id": telegram_id, "status": "granted"}


@router.delete("/admins/{telegram_id}", dependencies=[Depends(require_bot)])
async def revoke_admin(telegram_id: int, body: AdminGrantIn, db: AsyncSession = Depends(get_db)):
    root = get_settings().DASTYOR_BOT_ROOT_ADMIN_ID
    if root <= 0 or body.root_telegram_id != root or telegram_id == root:
        raise HTTPException(status_code=403, detail="Root administrator required")
    existing = await db.get(StandaloneBotAdmin, telegram_id)
    if existing:
        await db.delete(existing)
        await db.flush()
        await db.commit()
    return {"telegram_id": telegram_id, "status": "revoked"}
