"""Telegram-bot-side CRM access: tier permission + view bridges — pytest.

Run via pytest (conftest.py does the test-database setup):

    python -m pytest tests/test_bot_admin_crm.py -v

Covers the bot's direct calls into routers/admin_crm.py (bypassing
FastAPI's Depends(require_permission(...)), which does not run on a
plain Python call) - every bridge function must re-check permission
itself via service.has_admin_permission, not rely on bot.py's menu
hiding a button.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from conftest import async_test  # noqa: E402
from test_telegram_payments import cleanup_user, make_user  # noqa: E402

from app.database import async_session  # noqa: E402
from app.telegram import admin_crm_bridge, service  # noqa: E402

ROOT_ADMIN_TG_ID = 5001


async def _link_telegram(user_id: str, tg_id: int) -> None:
    async with async_session() as db:
        await db.execute(text(
            "INSERT INTO telegram_accounts (id, user_id, chat_id, telegram_user_id, linked_at, last_seen_at, revoked) "
            "VALUES (:id, :uid, :tg, :tg, now(), now(), FALSE)"
        ), {"id": str(uuid.uuid4()), "uid": user_id, "tg": tg_id})
        await db.commit()


async def _set_role(user_id: str, role: str, tier: str | None) -> None:
    async with async_session() as db:
        await db.execute(text(
            "UPDATE users SET role = :role, admin_tier = :tier WHERE id = :uid"
        ), {"role": role, "tier": tier, "uid": user_id})
        await db.commit()


@async_test
async def test_root_admin_is_always_super_tier_with_full_permission():
    assert await service.admin_tier_label(ROOT_ADMIN_TG_ID) == "super"
    assert await service.has_admin_permission(ROOT_ADMIN_TG_ID, "cards.manage")
    assert await service.has_admin_permission(ROOT_ADMIN_TG_ID, "admins.manage")


@async_test
async def test_readonly_tier_denied_cards_but_allowed_audit():
    uid = await make_user()
    tg_id = 900_801
    try:
        await _link_telegram(uid, tg_id)
        await _set_role(uid, "admin", "readonly")

        assert not await service.has_admin_permission(tg_id, "cards.manage")
        assert await service.has_admin_permission(tg_id, "audit.view")

        cards_msg = await admin_crm_bridge.cards_text(tg_id)
        assert "Недостаточно прав" in cards_msg

        audit_msg = await admin_crm_bridge.audit_log_text(tg_id)
        assert "Недостаточно прав" not in audit_msg
    finally:
        async with async_session() as db:
            await db.execute(text("DELETE FROM telegram_accounts WHERE user_id = :uid"), {"uid": uid})
            await db.commit()
        await cleanup_user(uid)


@async_test
async def test_finance_tier_can_view_cards_and_expenses():
    uid = await make_user()
    tg_id = 900_802
    try:
        await _link_telegram(uid, tg_id)
        await _set_role(uid, "admin", "finance")

        assert await service.has_admin_permission(tg_id, "cards.manage")
        assert await service.has_admin_permission(tg_id, "expenses.manage")

        cards_msg = await admin_crm_bridge.cards_text(tg_id)
        expenses_msg = await admin_crm_bridge.expenses_text(tg_id)
        assert "Недостаточно прав" not in cards_msg
        assert "Недостаточно прав" not in expenses_msg
    finally:
        async with async_session() as db:
            await db.execute(text("DELETE FROM telegram_accounts WHERE user_id = :uid"), {"uid": uid})
            await db.commit()
        await cleanup_user(uid)


@async_test
async def test_support_tier_denied_admins_manage():
    uid = await make_user()
    tg_id = 900_803
    try:
        await _link_telegram(uid, tg_id)
        await _set_role(uid, "admin", "support")
        assert not await service.has_admin_permission(tg_id, "admins.manage")
    finally:
        async with async_session() as db:
            await db.execute(text("DELETE FROM telegram_accounts WHERE user_id = :uid"), {"uid": uid})
            await db.commit()
        await cleanup_user(uid)


@async_test
async def test_add_admin_by_short_id_with_explicit_tier():
    uid = await make_user()
    tg_id = 900_804
    try:
        await _link_telegram(uid, tg_id)
        async with async_session() as db:
            short_id = (await db.execute(text(
                "SELECT short_id FROM users WHERE id = :uid"
            ), {"uid": uid})).scalar()

        result = await service.add_admin_by_short_id(short_id, ROOT_ADMIN_TG_ID, tier="readonly")
        assert result.outcome == "added"

        async with async_session() as db:
            tier = (await db.execute(text(
                "SELECT admin_tier FROM users WHERE id = :uid"
            ), {"uid": uid})).scalar()
        assert tier == "readonly"
    finally:
        async with async_session() as db:
            await db.execute(text("DELETE FROM telegram_admins WHERE user_id = :uid"), {"uid": uid})
            await db.execute(text("DELETE FROM telegram_accounts WHERE user_id = :uid"), {"uid": uid})
            await db.commit()
        await cleanup_user(uid)


@async_test
async def test_add_admin_rejects_invalid_tier_falls_back_to_default():
    uid = await make_user()
    try:
        async with async_session() as db:
            short_id = (await db.execute(text(
                "SELECT short_id FROM users WHERE id = :uid"
            ), {"uid": uid})).scalar()

        result = await service.add_admin_by_short_id(short_id, ROOT_ADMIN_TG_ID, tier="not-a-real-tier")
        assert result.outcome == "added_pending"

        async with async_session() as db:
            tier = (await db.execute(text(
                "SELECT admin_tier FROM users WHERE id = :uid"
            ), {"uid": uid})).scalar()
        assert tier == "support", "an invalid tier string must not be written verbatim"
    finally:
        async with async_session() as db:
            await db.execute(text("DELETE FROM telegram_admins WHERE user_id = :uid"), {"uid": uid})
            await db.commit()
        await cleanup_user(uid)
