"""New Admin CRM endpoints.

A sibling to routers/admin.py rather than an addition to it, on purpose:
admin.py already has an uncommitted SMS feature living in it (separate,
unrelated work), and every endpoint added here needs its own
migration-review / tiered-permission logic that has nothing to do with
that file's existing contents. Splitting avoids two unrelated features
colliding in the same diffs.

This file starts with the admin roster + migration-review worklist
(Stage 2 of the CRM build). Cards, expenses, the unified payments queue,
the balance ledger browser and the audit log endpoints are added here
in later stages, all behind app.admin_roles.require_permission.
"""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_roles import ADMIN_TIERS, require_permission
from app.auth import get_current_admin
from app.config import get_settings
from app.database import get_db
from app.logger import get_logger
from app.models import User
from app.schemas import (
    AdminPaymentApprove,
    AdminPaymentDecision,
    AdminPaymentRequestOut,
    AdminPromoteRequest,
    AdminRosterEntry,
    AdminRosterOut,
    AuditLogEntryOut,
    BalanceTransactionOut,
    CardCreate,
    CardDetailOut,
    CardOut,
    CardUpdate,
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
    UnreviewedTelegramAdminOut,
)
from app.telegram import service as telegram_service

logger = get_logger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin-crm"])


async def _audit(db: AsyncSession, actor: User, event: str, subject_user_id: str,
                 detail: dict) -> None:
    """Admin-management events land in the same append-only log as
    payments (payment_audit_log) rather than a second table — see the
    architecture plan's rationale: one history, not two half-stories.

    payment_request_id is reused as a generic subject key, exactly as
    telegram/service.py already does for grants ("admin:<telegram id>").
    Here it holds the Dastyor user_id directly: that column is only 36
    chars, which a uuid already fills, so there is no room for a prefix
    the way the shorter numeric Telegram id gets one.
    """
    await db.execute(text(
        "INSERT INTO payment_audit_log "
        "(id, payment_request_id, event, actor_kind, actor_telegram_id, "
        " actor_user_id, detail, created_at) "
        "VALUES (:id, :subject, :event, 'admin_web', NULL, :actor_uid, :detail, now())"
    ), {
        "id": str(uuid.uuid4()),
        "subject": subject_user_id,
        "event": event,
        "actor_uid": actor.id,
        "detail": json.dumps(detail, ensure_ascii=False, default=str),
    })


@router.get("/admins", response_model=AdminRosterOut)
async def list_admin_roster(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Every admin.at-least-view-the-roster. Only the mutating endpoint
    below is tier-gated — seeing who else administers the system is not
    itself a privileged action."""
    current = (await db.execute(
        select(User).where(User.role == "admin").order_by(User.full_name)
    )).scalars().all()

    unreviewed_rows = (await db.execute(text(
        "SELECT ta.id, ta.telegram_user_id, ta.user_id, u.full_name, u.short_id, "
        "       ta.added_at "
        "FROM telegram_admins ta LEFT JOIN users u ON u.id = ta.user_id "
        "WHERE ta.revoked = FALSE AND ta.reviewed_at IS NULL "
        "  AND (u.id IS NULL OR u.role <> 'admin') "
        "ORDER BY ta.added_at"
    ))).all()

    return AdminRosterOut(
        admins=[
            AdminRosterEntry(
                user_id=u.id, full_name=u.full_name, short_id=u.short_id,
                admin_tier=u.admin_tier,
            )
            for u in current
        ],
        unreviewed=[
            UnreviewedTelegramAdminOut(
                grant_id=r.id, telegram_user_id=r.telegram_user_id,
                user_id=r.user_id, full_name=r.full_name, short_id=r.short_id,
                added_at=r.added_at,
            )
            for r in unreviewed_rows
        ],
    )


@router.post("/admins/{user_id}/promote", response_model=AdminRosterEntry)
async def act_on_admin(
    user_id: str,
    data: AdminPromoteRequest,
    admin: User = Depends(require_permission("admins.manage")),
    db: AsyncSession = Depends(get_db),
):
    """The one endpoint that changes who administers the system.

    Three actions, all requiring the "admins.manage" permission (which
    only the super tier's "*" wildcard matches - see admin_roles.py):

    - "promote": sets role='admin' + the given tier. Used both for the
      migration-review worklist (a pre-existing Telegram-only grant) and
      for ordinary tier changes on an already-promoted admin - the two
      are the same operation from here, idempotent either way.
    - "demote": sets role='user', admin_tier=NULL. Refuses to leave the
      system with zero super admins - checked by effective tier (NULL
      counts as super, same as admin_roles.has_permission's fallback),
      not by whether this is self-demotion, so the guarantee holds no
      matter who is doing the demoting.
    - "ignore": marks any pending telegram_admins grant for this user as
      reviewed, without changing role/tier at all. This is the only way
      a Telegram-only grant leaves the worklist without being promoted -
      nothing here or anywhere else promotes one automatically.
    """
    target = (await db.execute(
        select(User).where(User.id == user_id)
    )).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    if data.action == "promote":
        if data.admin_tier not in ADMIN_TIERS:
            raise HTTPException(status_code=400, detail="Invalid admin_tier")
        target.role = "admin"
        target.admin_tier = data.admin_tier
        await db.execute(text(
            "UPDATE telegram_admins SET reviewed_at = now() "
            "WHERE user_id = :uid AND revoked = FALSE AND reviewed_at IS NULL"
        ), {"uid": user_id})
        await _audit(db, admin, "admin_tier_set", user_id, {"tier": data.admin_tier})

    elif data.action == "demote":
        effective_tier = target.admin_tier or "super"
        if effective_tier == "super":
            other_supers = (await db.execute(text(
                "SELECT count(*) FROM users WHERE role = 'admin' "
                "AND (admin_tier = 'super' OR admin_tier IS NULL) AND id <> :uid"
            ), {"uid": target.id})).scalar()
            if not other_supers:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot remove the last super admin",
                )
        target.role = "user"
        target.admin_tier = None
        await _audit(db, admin, "admin_demoted", user_id, {})

    elif data.action == "ignore":
        result = await db.execute(text(
            "UPDATE telegram_admins SET reviewed_at = now() "
            "WHERE user_id = :uid AND revoked = FALSE AND reviewed_at IS NULL"
        ), {"uid": user_id})
        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="No unreviewed Telegram grant for this user",
            )
        await _audit(db, admin, "admin_review_ignored", user_id, {})

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {data.action!r}")

    await db.flush()
    logger.warning(
        f"Admin {admin.id} performed {data.action!r} on user {user_id} "
        f"(tier={data.admin_tier!r})"
    )
    return AdminRosterEntry(
        user_id=target.id, full_name=target.full_name, short_id=target.short_id,
        admin_tier=target.admin_tier,
    )


# ---------------------------------------------------------------------
# Cards — payment requisites. Never touches a balance, a transaction or
# a payment request; the only side effect any of these endpoints has
# outside the payment_cards table is keeping TelegramBotState's
# pay_instructions text (the one thing a teacher actually sees) in sync
# through the EXISTING set_pay_instructions_web, so there stays exactly
# one write path and one audit trail for that value.
# ---------------------------------------------------------------------

def _require_card_key() -> str:
    key = get_settings().CARD_ENCRYPTION_KEY
    if not key:
        # Same shape as an unconfigured Telegram bot: a server that
        # hasn't set this yet must not crash, and must not encrypt with
        # no key or something improvised instead - it just can't offer
        # this feature until someone sets it.
        raise HTTPException(
            status_code=503,
            detail="CARD_ENCRYPTION_KEY is not configured on this server",
        )
    return key


def _mask_card_number(raw: str) -> str:
    raw = raw.strip()
    if len(raw) <= 4:
        return "•" * len(raw)
    return "•" * (len(raw) - 4) + raw[-4:]


async def _sync_pay_instructions_from_cards(db: AsyncSession, admin: User, key: str) -> None:
    """Regenerate the single text block /pay and the web app show, from
    whichever cards are currently active - called after every create/
    update/delete below, so that blob never drifts from this table."""
    rows = (await db.execute(text(
        "SELECT bank_name, holder_name, "
        "       pgp_sym_decrypt(card_number_encrypted, :key) AS card_number, note "
        "FROM payment_cards WHERE is_active = TRUE "
        "ORDER BY sort_order, created_at"
    ), {"key": key})).all()

    if not rows:
        new_text = ""
    else:
        lines = []
        for r in rows:
            line = f"{r.bank_name}: {r.card_number} ({r.holder_name})"
            if r.note:
                line += f" — {r.note}"
            lines.append(line)
        new_text = "\n\n".join(lines)

    previous = await telegram_service.set_pay_instructions_web(new_text, admin.id)
    logger.warning(f"Admin {admin.id} changed pay instructions via the Cards page")

    try:
        admin_ids = await telegram_service.all_admin_ids()
        from app.telegram.api import TelegramApiError, TelegramClient, TelegramTransportError
        from app.telegram.config import get_telegram_settings

        settings = get_telegram_settings()
        client = TelegramClient(
            settings.TELEGRAM_ADMIN_BOT_TOKEN if settings.has_separate_admin_bot else None
        )
        message = (
            f"⚠️ Реквизиты оплаты изменены через страницу «Карты» "
            f"администратором {admin.full_name}.\n\n"
            f"Было:\n{(previous or '').strip() or '(пусто)'}\n\n"
            f"Стало:\n{new_text.strip() or '(пусто)'}"
        )
        for chat_id in admin_ids:
            try:
                await client.send_message(chat_id, message)
            except (TelegramApiError, TelegramTransportError) as e:
                logger.error(f"Pay-instructions change notice to {chat_id} failed: {e}")
    except Exception as e:
        # Never let a notification failure undo or mask the save above.
        logger.error(f"Could not notify Telegram admins of a Cards-page change: {e}")


def _card_out(row) -> CardOut:
    return CardOut(
        id=row.id, bank_name=row.bank_name, holder_name=row.holder_name,
        card_number_masked=_mask_card_number(row.card_number),
        currency=row.currency, note=row.note, is_active=row.is_active,
        sort_order=row.sort_order, created_at=row.created_at, updated_at=row.updated_at,
    )


@router.get("/cards", response_model=list[CardOut])
async def list_cards(
    admin: User = Depends(require_permission("cards.manage")),
    db: AsyncSession = Depends(get_db),
):
    key = _require_card_key()
    rows = (await db.execute(text(
        "SELECT id, bank_name, holder_name, "
        "       pgp_sym_decrypt(card_number_encrypted, :key) AS card_number, "
        "       currency, note, is_active, sort_order, created_at, updated_at "
        "FROM payment_cards ORDER BY sort_order, created_at"
    ), {"key": key})).all()
    return [_card_out(r) for r in rows]


@router.get("/cards/{card_id}", response_model=CardDetailOut)
async def get_card_detail(
    card_id: str,
    admin: User = Depends(require_permission("cards.manage")),
    db: AsyncSession = Depends(get_db),
):
    key = _require_card_key()
    row = (await db.execute(text(
        "SELECT id, bank_name, holder_name, "
        "       pgp_sym_decrypt(card_number_encrypted, :key) AS card_number, "
        "       currency, note, is_active, sort_order, created_at, updated_at "
        "FROM payment_cards WHERE id = :id"
    ), {"key": key, "id": card_id})).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return CardDetailOut(
        id=row.id, bank_name=row.bank_name, holder_name=row.holder_name,
        card_number_masked=_mask_card_number(row.card_number),
        card_number=row.card_number, currency=row.currency, note=row.note,
        is_active=row.is_active, sort_order=row.sort_order,
        created_at=row.created_at, updated_at=row.updated_at,
    )


@router.post("/cards", response_model=CardOut, status_code=201)
async def create_card(
    data: CardCreate,
    admin: User = Depends(require_permission("cards.manage")),
    db: AsyncSession = Depends(get_db),
):
    key = _require_card_key()
    card_id = str(uuid.uuid4())
    await db.execute(text(
        "INSERT INTO payment_cards "
        "(id, bank_name, holder_name, card_number_encrypted, currency, note, "
        " is_active, sort_order, created_by, created_at, updated_at) "
        "VALUES (:id, :bank, :holder, pgp_sym_encrypt(:num, :key), :currency, :note, "
        "        :active, :sort, :actor, now(), now())"
    ), {
        "id": card_id, "bank": data.bank_name, "holder": data.holder_name,
        "num": data.card_number, "key": key, "currency": data.currency,
        "note": data.note, "active": data.is_active, "sort": data.sort_order,
        "actor": admin.id,
    })
    await _audit(db, admin, "card_created", card_id, {"bank_name": data.bank_name})
    if data.is_active:
        await _sync_pay_instructions_from_cards(db, admin, key)
    await db.flush()

    row = (await db.execute(text(
        "SELECT id, bank_name, holder_name, "
        "       pgp_sym_decrypt(card_number_encrypted, :key) AS card_number, "
        "       currency, note, is_active, sort_order, created_at, updated_at "
        "FROM payment_cards WHERE id = :id"
    ), {"key": key, "id": card_id})).first()
    return _card_out(row)


@router.put("/cards/{card_id}", response_model=CardOut)
async def update_card(
    card_id: str,
    data: CardUpdate,
    admin: User = Depends(require_permission("cards.manage")),
    db: AsyncSession = Depends(get_db),
):
    key = _require_card_key()
    existing = (await db.execute(text(
        "SELECT id FROM payment_cards WHERE id = :id"
    ), {"id": card_id})).first()
    if existing is None:
        raise HTTPException(status_code=404, detail="Card not found")

    fields = data.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    sets = ["updated_at = now()"]
    params: dict = {"id": card_id, "key": key}
    for name in ("bank_name", "holder_name", "currency", "note", "is_active", "sort_order"):
        if name in fields:
            sets.append(f"{name} = :{name}")
            params[name] = fields[name]
    if "card_number" in fields:
        sets.append("card_number_encrypted = pgp_sym_encrypt(:card_number, :key)")
        params["card_number"] = fields["card_number"]

    await db.execute(text(
        f"UPDATE payment_cards SET {', '.join(sets)} WHERE id = :id"
    ), params)
    await _audit(db, admin, "card_updated", card_id, {"fields": list(fields.keys())})
    await _sync_pay_instructions_from_cards(db, admin, key)
    await db.flush()

    row = (await db.execute(text(
        "SELECT id, bank_name, holder_name, "
        "       pgp_sym_decrypt(card_number_encrypted, :key) AS card_number, "
        "       currency, note, is_active, sort_order, created_at, updated_at "
        "FROM payment_cards WHERE id = :id"
    ), {"key": key, "id": card_id})).first()
    return _card_out(row)


@router.delete("/cards/{card_id}", status_code=204)
async def delete_card(
    card_id: str,
    admin: User = Depends(require_permission("cards.manage")),
    db: AsyncSession = Depends(get_db),
):
    key = _require_card_key()
    result = await db.execute(text("DELETE FROM payment_cards WHERE id = :id"), {"id": card_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Card not found")
    await _audit(db, admin, "card_deleted", card_id, {})
    await _sync_pay_instructions_from_cards(db, admin, key)
    await db.flush()


# ---------------------------------------------------------------------
# Expenses — plain bookkeeping for the Reports/profit page. Never reads
# or writes balance_dirams, BalanceTransaction or any payment table.
# ---------------------------------------------------------------------

@router.get("/expenses", response_model=list[ExpenseOut])
async def list_expenses(
    category: str | None = None,
    limit: int = 100,
    offset: int = 0,
    admin: User = Depends(require_permission("expenses.manage")),
    db: AsyncSession = Depends(get_db),
):
    query = "SELECT id, category, amount_dirams, note, spent_at, created_by, created_at FROM expenses"
    params: dict = {}
    if category:
        query += " WHERE category = :category"
        params["category"] = category
    query += " ORDER BY spent_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = min(limit, 500)
    params["offset"] = max(offset, 0)

    rows = (await db.execute(text(query), params)).all()
    return [
        ExpenseOut(
            id=r.id, category=r.category, amount_somoni=r.amount_dirams / 100,
            note=r.note, spent_at=r.spent_at, created_by=r.created_by,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/expenses", response_model=ExpenseOut, status_code=201)
async def create_expense(
    data: ExpenseCreate,
    admin: User = Depends(require_permission("expenses.manage")),
    db: AsyncSession = Depends(get_db),
):
    expense_id = str(uuid.uuid4())
    amount_dirams = round(data.amount_somoni * 100)
    await db.execute(text(
        "INSERT INTO expenses (id, category, amount_dirams, note, spent_at, created_by, created_at) "
        "VALUES (:id, :category, :amount, :note, :spent_at, :actor, now())"
    ), {
        "id": expense_id, "category": data.category, "amount": amount_dirams,
        "note": data.note, "spent_at": data.spent_at, "actor": admin.id,
    })
    await _audit(db, admin, "expense_created", expense_id, {
        "category": data.category, "amount_somoni": data.amount_somoni,
    })
    await db.flush()
    return ExpenseOut(
        id=expense_id, category=data.category, amount_somoni=data.amount_somoni,
        note=data.note, spent_at=data.spent_at, created_by=admin.id,
        created_at=datetime.now(timezone.utc),
    )


@router.put("/expenses/{expense_id}", response_model=ExpenseOut)
async def update_expense(
    expense_id: str,
    data: ExpenseUpdate,
    admin: User = Depends(require_permission("expenses.manage")),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(text(
        "SELECT id FROM expenses WHERE id = :id"
    ), {"id": expense_id})).first()
    if existing is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    fields = data.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    sets = []
    params: dict = {"id": expense_id}
    for name in ("category", "note", "spent_at"):
        if name in fields:
            sets.append(f"{name} = :{name}")
            params[name] = fields[name]
    if "amount_somoni" in fields:
        sets.append("amount_dirams = :amount_dirams")
        params["amount_dirams"] = round(fields["amount_somoni"] * 100)

    await db.execute(text(f"UPDATE expenses SET {', '.join(sets)} WHERE id = :id"), params)
    await _audit(db, admin, "expense_updated", expense_id, {"fields": list(fields.keys())})
    await db.flush()

    row = (await db.execute(text(
        "SELECT id, category, amount_dirams, note, spent_at, created_by, created_at "
        "FROM expenses WHERE id = :id"
    ), {"id": expense_id})).first()
    return ExpenseOut(
        id=row.id, category=row.category, amount_somoni=row.amount_dirams / 100,
        note=row.note, spent_at=row.spent_at, created_by=row.created_by,
        created_at=row.created_at,
    )


@router.delete("/expenses/{expense_id}", status_code=204)
async def delete_expense(
    expense_id: str,
    admin: User = Depends(require_permission("expenses.manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("DELETE FROM expenses WHERE id = :id"), {"id": expense_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Expense not found")
    await _audit(db, admin, "expense_deleted", expense_id, {})
    await db.flush()


# ---------------------------------------------------------------------
# Payments — the Telegram-side queue (payment_requests), surfaced on
# the CRM's unified Payments page alongside the web-side queue
# (BalanceTopupRequest, already served by routers/admin.py's existing
# /topup-requests endpoints — untouched, reused as-is).
#
# Every mutation below calls straight into telegram.service's
# approve_payment/reject_payment/request_more_info - the SAME
# compare-and-swap, SAME ledger/audit code the bot's own inline buttons
# use. This file only resolves who the acting admin is and shapes the
# response; it never re-implements the decision itself.
# ---------------------------------------------------------------------

_PAYMENT_REQUEST_SELECT = (
    "SELECT pr.id, pr.public_code, pr.user_id, u.full_name AS user_name, "
    "       u.short_id AS user_short_id, pr.requested_dirams, pr.status, "
    "       pr.receipt_file_id, pr.receipt_mime, pr.ocr_amount_dirams, "
    "       pr.ocr_sender, pr.ocr_recipient, pr.ocr_reference, "
    "       pr.ocr_confidence, pr.ocr_warnings, pr.credited_dirams, "
    "       pr.decision_note, pr.created_at, pr.updated_at "
    "FROM payment_requests pr JOIN users u ON u.id = pr.user_id"
)


def _payment_request_out(row) -> AdminPaymentRequestOut:
    return AdminPaymentRequestOut(
        id=row.id, public_code=row.public_code, user_id=row.user_id,
        user_name=row.user_name, user_short_id=row.user_short_id,
        requested_somoni=row.requested_dirams / 100, status=row.status,
        receipt_file_id=row.receipt_file_id, receipt_mime=row.receipt_mime,
        ocr_amount_somoni=(row.ocr_amount_dirams / 100) if row.ocr_amount_dirams is not None else None,
        ocr_sender=row.ocr_sender, ocr_recipient=row.ocr_recipient,
        ocr_reference=row.ocr_reference, ocr_confidence=row.ocr_confidence,
        ocr_warnings=row.ocr_warnings,
        credited_somoni=(row.credited_dirams / 100) if row.credited_dirams else None,
        decision_note=row.decision_note, created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _admin_telegram_id(db: AsyncSession, user_id: str) -> int | None:
    """The acting web admin's own linked Telegram id, if they have one.

    Passed through to approve_payment/reject_payment/request_more_info
    so an admin who happens to be linked still shows up as themselves
    (not a generic "web admin") in the ledger reason and audit log -
    purely cosmetic, never a second source of authorization (that's
    still require_permission, checked before this is even called).
    """
    return (await db.execute(text(
        "SELECT telegram_user_id FROM telegram_accounts "
        "WHERE user_id = :uid AND revoked = FALSE"
    ), {"uid": user_id})).scalar()


def _raise_for_decision_outcome(outcome: str) -> None:
    if outcome == "not_found":
        raise HTTPException(status_code=404, detail="Payment request not found")
    if outcome == "already_decided":
        raise HTTPException(status_code=409, detail="This request was already decided")
    if outcome == "duplicate_reference":
        raise HTTPException(
            status_code=409,
            detail="This bank reference has already been credited on another request",
        )
    if outcome == "amount_conflict":
        raise HTTPException(
            status_code=400,
            detail="amount_override_somoni requires correction_reason",
        )
    if outcome == "self_approval":
        raise HTTPException(status_code=403, detail="Cannot approve your own payment")
    if outcome != "applied":
        raise HTTPException(status_code=500, detail=f"Unexpected outcome: {outcome}")


@router.get("/payment-requests", response_model=list[AdminPaymentRequestOut])
async def list_payment_requests(
    status: str | None = None,
    limit: int = 100,
    admin: User = Depends(require_permission("payments.view")),
    db: AsyncSession = Depends(get_db),
):
    query = _PAYMENT_REQUEST_SELECT
    params: dict = {"limit": min(limit, 200)}
    if status:
        query += " WHERE pr.status = :status"
        params["status"] = status
    query += " ORDER BY pr.created_at DESC LIMIT :limit"
    rows = (await db.execute(text(query), params)).all()
    return [_payment_request_out(r) for r in rows]


@router.post("/payment-requests/{request_id}/approve", response_model=AdminPaymentRequestOut)
async def approve_payment_request(
    request_id: str,
    data: AdminPaymentApprove,
    admin: User = Depends(require_permission("payments.review")),
    db: AsyncSession = Depends(get_db),
):
    telegram_id = await _admin_telegram_id(db, admin.id)
    result = await telegram_service.approve_payment(
        request_id,
        telegram_id,
        admin_user_id=admin.id,
        amount_override_dirams=(
            round(data.amount_override_somoni * 100)
            if data.amount_override_somoni is not None else None
        ),
        correction_reason=data.correction_reason,
    )
    _raise_for_decision_outcome(result.outcome)

    row = (await db.execute(text(
        f"{_PAYMENT_REQUEST_SELECT} WHERE pr.id = :id"
    ), {"id": request_id})).first()
    return _payment_request_out(row)


@router.post("/payment-requests/{request_id}/reject", response_model=AdminPaymentRequestOut)
async def reject_payment_request(
    request_id: str,
    data: AdminPaymentDecision,
    admin: User = Depends(require_permission("payments.review")),
    db: AsyncSession = Depends(get_db),
):
    telegram_id = await _admin_telegram_id(db, admin.id)
    result = await telegram_service.reject_payment(
        request_id, telegram_id, data.note, admin_user_id=admin.id,
    )
    _raise_for_decision_outcome(result.outcome)

    row = (await db.execute(text(
        f"{_PAYMENT_REQUEST_SELECT} WHERE pr.id = :id"
    ), {"id": request_id})).first()
    return _payment_request_out(row)


@router.post("/payment-requests/{request_id}/request-info", response_model=AdminPaymentRequestOut)
async def request_payment_info(
    request_id: str,
    data: AdminPaymentDecision,
    admin: User = Depends(require_permission("payments.review")),
    db: AsyncSession = Depends(get_db),
):
    telegram_id = await _admin_telegram_id(db, admin.id)
    result = await telegram_service.request_more_info(
        request_id, telegram_id, data.note, admin_user_id=admin.id,
    )
    _raise_for_decision_outcome(result.outcome)

    row = (await db.execute(text(
        f"{_PAYMENT_REQUEST_SELECT} WHERE pr.id = :id"
    ), {"id": request_id})).first()
    return _payment_request_out(row)


# ---------------------------------------------------------------------
# Global ledger browser and audit log — read-only, no state changes.
# ---------------------------------------------------------------------

@router.get("/balance-transactions", response_model=list[BalanceTransactionOut])
async def list_balance_transactions(
    user_id: str | None = None,
    kind: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
    admin: User = Depends(require_permission("reports.view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        "SELECT bt.id, bt.kind, bt.amount_dirams, bt.balance_before, "
        "       bt.balance_after, bt.reason, bt.material_type, bt.created_at, "
        "       bt.user_id, owner.full_name AS user_name, "
        "       actor.full_name AS actor_name "
        "FROM balance_transactions bt "
        "LEFT JOIN users owner ON owner.id = bt.user_id "
        "LEFT JOIN users actor ON actor.id = bt.actor_id"
    )
    clauses = []
    params: dict = {}
    if user_id:
        clauses.append("bt.user_id = :user_id")
        params["user_id"] = user_id
    if kind:
        clauses.append("bt.kind = :kind")
        params["kind"] = kind
    if date_from:
        clauses.append("bt.created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append("bt.created_at <= :date_to")
        params["date_to"] = date_to
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY bt.created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = min(limit, 500)
    params["offset"] = max(offset, 0)

    rows = (await db.execute(text(query), params)).all()
    return [
        BalanceTransactionOut(
            id=r.id, kind=r.kind, amount_somoni=r.amount_dirams / 100,
            balance_before_somoni=r.balance_before / 100,
            balance_after_somoni=r.balance_after / 100,
            actor_name=r.actor_name, reason=r.reason,
            material_type=r.material_type, created_at=r.created_at,
            user_id=r.user_id, user_name=r.user_name,
        )
        for r in rows
    ]


@router.get("/audit-log", response_model=list[AuditLogEntryOut])
async def list_audit_log(
    event: str | None = None,
    actor_user_id: str | None = None,
    actor_telegram_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
    admin: User = Depends(require_permission("audit.view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        "SELECT pal.id, pal.payment_request_id AS subject, pal.event, "
        "       pal.actor_kind, pal.actor_telegram_id, pal.actor_user_id, "
        "       u.full_name AS actor_name, pal.detail, pal.created_at "
        "FROM payment_audit_log pal "
        "LEFT JOIN users u ON u.id = pal.actor_user_id"
    )
    clauses = []
    params: dict = {}
    if event:
        clauses.append("pal.event = :event")
        params["event"] = event
    if actor_user_id:
        clauses.append("pal.actor_user_id = :actor_user_id")
        params["actor_user_id"] = actor_user_id
    if actor_telegram_id is not None:
        clauses.append("pal.actor_telegram_id = :actor_telegram_id")
        params["actor_telegram_id"] = actor_telegram_id
    if date_from:
        clauses.append("pal.created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append("pal.created_at <= :date_to")
        params["date_to"] = date_to
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY pal.created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = min(limit, 500)
    params["offset"] = max(offset, 0)

    rows = (await db.execute(text(query), params)).all()
    return [
        AuditLogEntryOut(
            id=r.id, subject=r.subject, event=r.event, actor_kind=r.actor_kind,
            actor_telegram_id=r.actor_telegram_id, actor_user_id=r.actor_user_id,
            actor_name=r.actor_name, detail=r.detail, created_at=r.created_at,
        )
        for r in rows
    ]
