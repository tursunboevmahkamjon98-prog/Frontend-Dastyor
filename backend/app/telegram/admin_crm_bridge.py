"""Bot access to the CRM's Cards/Expenses/Reports/Audit read endpoints.

Calls routers/admin_crm.py's functions directly (as plain Python, not
over HTTP) so there is exactly one implementation per operation - the
same SQL the web CRM uses. FastAPI's own Depends(require_permission(...))
on those functions does NOT run when called this way, so every function
here re-checks permission itself via service.has_admin_permission before
touching the database. This is the actual backend enforcement; nothing
in bot.py's menu/keyboard code is trusted to gate anything.

View-only on purpose: the product requirement is that an admin can SEE
cards/expenses/reports/audit from the bot. Creating/editing a card
still goes through the web CRM (Stage 3), which keeps the
pay_instructions-sync and audit side effects in one place rather than
needing them re-triggered from a second entry point.
"""

from app.database import async_session
from app.routers import admin_crm
from app.telegram import service
from sqlalchemy import text


class _ViewOnlyAdmin:
    """Placeholder for admin_crm.py's `admin: User` parameter.

    The list_* functions this module calls never read `admin` in their
    bodies - it exists only for FastAPI's Depends() gate, which does
    not run on a direct call. Safe as a stand-in precisely because
    nothing here is a mutation.
    """
    id = None
    full_name = "telegram-bot"


async def cards_text(telegram_user_id: int) -> str:
    if not await service.has_admin_permission(telegram_user_id, "cards.manage"):
        return "⛔ Недостаточно прав для просмотра карт."
    async with async_session() as db:
        try:
            cards = await admin_crm.list_cards(admin=_ViewOnlyAdmin(), db=db)
        except Exception:
            return "⚠️ Карты не настроены (нет CARD_ENCRYPTION_KEY) или произошла ошибка."
    if not cards:
        return "Карт пока нет. Добавьте через веб-консоль CRM."
    lines = ["💳 Карты:"]
    for c in cards:
        status = "✅" if c.is_active else "⛔"
        lines.append(f"{status} {c.bank_name} — {c.card_number_masked} ({c.holder_name})")
    return "\n".join(lines)


async def expenses_text(telegram_user_id: int) -> str:
    if not await service.has_admin_permission(telegram_user_id, "expenses.manage"):
        return "⛔ Недостаточно прав для просмотра расходов."
    async with async_session() as db:
        expenses = await admin_crm.list_expenses(
            category=None, limit=20, offset=0, admin=_ViewOnlyAdmin(), db=db,
        )
    if not expenses:
        return "Расходов пока нет."
    total = sum(e.amount_somoni for e in expenses)
    lines = [f"💰 Последние расходы (сумма: {total:.2f} сомони):"]
    for e in expenses:
        lines.append(f"• {e.category}: {e.amount_somoni:.2f} сомони — {e.note or '—'}")
    return "\n".join(lines)


async def finance_report_text_all_time_legacy(telegram_user_id: int) -> str:
    if not await service.has_admin_permission(telegram_user_id, "reports.view"):
        return "⛔ Недостаточно прав для просмотра финансов."
    async with async_session() as db:
        topups = await admin_crm.list_balance_transactions(
            user_id=None, kind="topup", date_from=None, date_to=None,
            limit=1000, offset=0, admin=_ViewOnlyAdmin(), db=db,
        )
        expenses = await admin_crm.list_expenses(
            category=None, limit=1000, offset=0, admin=_ViewOnlyAdmin(), db=db,
        )
    topup_total = sum(t.amount_somoni for t in topups)
    expense_total = sum(e.amount_somoni for e in expenses)
    return (
        "📈 Финансы (за всё время):\n"
        f"Подтверждённые пополнения: {topup_total:.2f} сомони\n"
        f"Расходы: {expense_total:.2f} сомони\n"
        f"Разница: {topup_total - expense_total:.2f} сомони\n\n"
        "Не включает расходы на AI/сервер, если они не внесены в «Расходы»."
    )


async def finance_report_text(telegram_user_id: int) -> str:
    if not await service.has_admin_permission(telegram_user_id, "reports.view"):
        return "Ruxsat yo‘q: moliyaviy hisobot faqat vakolatli adminlar uchun."
    async with async_session() as db:
        requests = (await db.execute(text(
            "SELECT COUNT(DISTINCT user_id) AS people, "
            "COUNT(*) FILTER (WHERE status = 'approved') AS approved, "
            "COUNT(*) FILTER (WHERE status = 'rejected') AS rejected, "
            "COUNT(*) FILTER (WHERE status IN ('pending','needs_info','awaiting_receipt')) AS waiting "
            "FROM payment_requests WHERE created_at >= now() - interval '7 days'"
        ))).first()
        topup_total = (await db.execute(text(
            "SELECT COALESCE(SUM(amount_dirams), 0) FROM balance_transactions "
            "WHERE kind = 'topup' AND amount_dirams > 0 "
            "AND created_at >= now() - interval '7 days'"
        ))).scalar_one() / 100
        expense_total = (await db.execute(text(
            "SELECT COALESCE(SUM(amount_dirams), 0) FROM expenses "
            "WHERE spent_at >= now() - interval '7 days'"
        ))).scalar_one() / 100
    return (
        "📊 Haftalik moliyaviy hisobot (so‘nggi 7 kun):\n"
        f"So‘rov yuborgan odamlar: {requests.people}\n"
        f"Tasdiqlandi: {requests.approved} · rad etildi: {requests.rejected} · kutilmoqda: {requests.waiting}\n"
        f"Tasdiqlangan tushum: {topup_total:.2f} somoni\n"
        f"Qayd etilgan xarajat: {expense_total:.2f} somoni\n"
        f"Sof farq: {topup_total - expense_total:.2f} somoni\n\n"
        "AI/server xarajatlari faqat Xarajatlar bo‘limiga kiritilgan bo‘lsa hisoblanadi."
    )


async def audit_log_text(telegram_user_id: int) -> str:
    if not await service.has_admin_permission(telegram_user_id, "audit.view"):
        return "⛔ Недостаточно прав для просмотра журнала."
    async with async_session() as db:
        entries = await admin_crm.list_audit_log(
            event=None, actor_user_id=None, actor_telegram_id=None,
            date_from=None, date_to=None, limit=15, offset=0,
            admin=_ViewOnlyAdmin(), db=db,
        )
    if not entries:
        return "Журнал пуст."
    lines = ["📋 Последние события аудита:"]
    for e in entries:
        who = e.actor_name or (f"TG {e.actor_telegram_id}" if e.actor_telegram_id else e.actor_user_id or "—")
        lines.append(f"• {e.created_at:%d.%m %H:%M} {e.event} — {who}")
    return "\n".join(lines)
