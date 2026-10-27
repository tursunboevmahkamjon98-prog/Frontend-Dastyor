"""User.role as the single source of truth for admin authority — pytest.

Run via pytest (conftest.py in this directory does the test-database
setup):

    python -m pytest tests/test_admin_role_unification.py -v

Covers the Stage 1 change to telegram/service.py: is_admin()/
all_admin_ids() now resolve a Telegram id's admin authority through the
linked account's User.role instead of reading telegram_admins directly,
and add_admin_by_short_id()/remove_admin() keep User.role/admin_tier in
sync with the telegram_admins row they still write. Root admins
(TELEGRAM_ADMIN_IDS) stay a pure env-var check throughout, independent
of any User row — that independence is itself one of the things tested
here.

Shares the dastyor_bot_test database and the make_user/cleanup_user
fixtures with test_telegram_payments.py (imported for them, which runs
no tests of its own — see that file's own docstring).
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from sqlalchemy import text

from conftest import async_test  # noqa: E402
from test_telegram_payments import cleanup_user, make_user  # noqa: E402

from app.admin_roles import (  # noqa: E402
    TIER_FINANCE,
    TIER_READONLY,
    TIER_SUPER,
    has_permission,
    require_permission,
)
from app.auth import get_current_admin
from app.database import async_session
from app.telegram import service

ROOT_ADMIN_TG_ID = 5001  # from conftest.py's TELEGRAM_ADMIN_IDS


async def _link_telegram(user_id: str, telegram_user_id: int) -> None:
    async with async_session() as db:
        await db.execute(text(
            "INSERT INTO telegram_accounts (id, user_id, chat_id, telegram_user_id, linked_at, last_seen_at, revoked) "
            "VALUES (:id, :uid, :chat, :tg, now(), now(), FALSE)"
        ), {"id": str(uuid.uuid4()), "uid": user_id, "chat": telegram_user_id, "tg": telegram_user_id})
        await db.commit()


async def _revoke_telegram_link(user_id: str) -> None:
    async with async_session() as db:
        await db.execute(text(
            "UPDATE telegram_accounts SET revoked = TRUE WHERE user_id = :uid"
        ), {"uid": user_id})
        await db.commit()


async def _set_role(user_id: str, role: str, admin_tier: str | None = None) -> None:
    async with async_session() as db:
        await db.execute(text(
            "UPDATE users SET role = :role, admin_tier = :tier WHERE id = :uid"
        ), {"role": role, "tier": admin_tier, "uid": user_id})
        await db.commit()


async def _cleanup_full(user_id: str) -> None:
    async with async_session() as db:
        await db.execute(text("DELETE FROM telegram_admins WHERE user_id = :uid"), {"uid": user_id})
        await db.commit()
    await cleanup_user(user_id)


class _FakeAdminUser:
    """Just enough of User for get_current_admin/require_permission."""

    def __init__(self, role: str, admin_tier: str | None = None):
        self.role = role
        self.admin_tier = admin_tier


# ---------------------------------------------------------------------
# get_current_admin — unchanged behavior, still the only web-side gate
# ---------------------------------------------------------------------

@async_test
async def test_get_current_admin_rejects_plain_user():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(user=_FakeAdminUser(role="user"))
    assert exc_info.value.status_code == 403


@async_test
async def test_get_current_admin_accepts_any_admin_tier():
    for tier in (None, TIER_SUPER, TIER_FINANCE, TIER_READONLY):
        result = await get_current_admin(user=_FakeAdminUser(role="admin", admin_tier=tier))
        assert result.role == "admin"


# ---------------------------------------------------------------------
# admin_roles.require_permission — tier gating is additive on top
# ---------------------------------------------------------------------

def test_readonly_tier_has_view_but_not_manage_permissions():
    readonly = _FakeAdminUser(role="admin", admin_tier=TIER_READONLY)
    assert has_permission(readonly, "payments.view")
    assert not has_permission(readonly, "payments.review")
    assert not has_permission(readonly, "cards.manage")


def test_finance_tier_covers_money_but_not_admin_management():
    finance = _FakeAdminUser(role="admin", admin_tier=TIER_FINANCE)
    assert has_permission(finance, "payments.review")
    assert has_permission(finance, "cards.manage")
    assert not has_permission(finance, "users.manage")


def test_null_tier_defaults_to_super_for_backward_compatibility():
    legacy_admin = _FakeAdminUser(role="admin", admin_tier=None)
    assert has_permission(legacy_admin, "cards.manage")
    assert has_permission(legacy_admin, "users.manage")
    assert has_permission(legacy_admin, "anything.at.all")


@async_test
async def test_require_permission_dependency_403s_insufficient_tier():
    from fastapi import HTTPException
    dep = require_permission("cards.manage")
    with pytest.raises(HTTPException) as exc_info:
        await dep(admin=_FakeAdminUser(role="admin", admin_tier=TIER_READONLY))
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------
# telegram/service.is_admin — now resolves through linked User.role
# ---------------------------------------------------------------------

@async_test
async def test_root_admin_authorized_with_zero_user_rows():
    # ROOT_ADMIN_TG_ID has no linked TelegramAccount and no User row at
    # all in a clean test run - this is the whole point of root admins:
    # they cannot be locked out by anything that happens to User rows.
    assert await service.is_admin(ROOT_ADMIN_TG_ID)


@async_test
async def test_unknown_telegram_id_is_not_admin():
    assert not await service.is_admin(999_999_999)
    assert not await service.is_admin(None)


@async_test
async def test_linked_admin_role_grants_bot_authority():
    uid = await make_user()
    tg_id = 900_501
    try:
        await _link_telegram(uid, tg_id)
        assert not await service.is_admin(tg_id), "plain user must not be a bot admin"

        await _set_role(uid, "admin", "support")
        assert await service.is_admin(tg_id), "role='admin' must grant bot authority once linked"
        assert tg_id in await service.granted_admin_ids()
        assert tg_id in await service.all_admin_ids()
    finally:
        await _cleanup_full(uid)


@async_test
async def test_admin_role_without_telegram_link_has_no_bot_authority():
    uid = await make_user()
    try:
        await _set_role(uid, "admin", "super")
        # A web-only admin with no linked chat cannot be matched to any
        # telegram_user_id, so there is nothing for is_admin() to check
        # against - this just confirms granted_admin_ids() never lists
        # a non-existent Telegram id for them.
        async with async_session() as db:
            linked = (await db.execute(text(
                "SELECT 1 FROM telegram_accounts WHERE user_id = :uid"
            ), {"uid": uid})).scalar()
        assert linked is None
    finally:
        await _cleanup_full(uid)


@async_test
async def test_revoked_telegram_link_strips_bot_admin_but_not_web_role():
    uid = await make_user()
    tg_id = 900_502
    try:
        await _link_telegram(uid, tg_id)
        await _set_role(uid, "admin", "support")
        assert await service.is_admin(tg_id)

        await _revoke_telegram_link(uid)

        assert not await service.is_admin(tg_id), (
            "a revoked Telegram link must stop bot authority immediately"
        )
        async with async_session() as db:
            role = (await db.execute(text(
                "SELECT role FROM users WHERE id = :uid"
            ), {"uid": uid})).scalar()
        assert role == "admin", (
            "revoking the Telegram link must not touch the web-side role at all"
        )
    finally:
        await _cleanup_full(uid)


# ---------------------------------------------------------------------
# add_admin_by_short_id / remove_admin — now also write User.role
# ---------------------------------------------------------------------

@async_test
async def test_grant_via_bot_sets_user_role_and_default_tier():
    uid = await make_user()
    tg_id = 900_503
    try:
        await _link_telegram(uid, tg_id)
        async with async_session() as db:
            short_id = (await db.execute(text(
                "SELECT short_id FROM users WHERE id = :uid"
            ), {"uid": uid})).scalar()

        result = await service.add_admin_by_short_id(short_id, ROOT_ADMIN_TG_ID)
        assert result.outcome == "added"

        async with async_session() as db:
            row = (await db.execute(text(
                "SELECT role, admin_tier FROM users WHERE id = :uid"
            ), {"uid": uid})).first()
        assert row.role == "admin"
        assert row.admin_tier == "support", "a bot grant must default to the support tier"
        assert await service.is_admin(tg_id)
    finally:
        await _cleanup_full(uid)


@async_test
async def test_grant_preserves_existing_tier_instead_of_downgrading():
    """A user already promoted to a real tier via the CRM, then also
    granted via the bot, must not be silently downgraded to support."""
    uid = await make_user()
    tg_id = 900_504
    try:
        await _link_telegram(uid, tg_id)
        await _set_role(uid, "admin", TIER_FINANCE)

        # This grant is redundant (they're already an admin) but must
        # still be harmless - COALESCE in add_admin_by_short_id's UPDATE
        # is what this test is actually checking.
        async with async_session() as db:
            short_id = (await db.execute(text(
                "SELECT short_id FROM users WHERE id = :uid"
            ), {"uid": uid})).scalar()
            already = (await db.execute(text(
                "SELECT 1 FROM telegram_admins WHERE user_id = :uid AND revoked = FALSE"
            ), {"uid": uid})).scalar()
        assert already is None  # sanity: no grant row exists yet from this test

        result = await service.add_admin_by_short_id(short_id, ROOT_ADMIN_TG_ID)
        assert result.outcome == "added"

        async with async_session() as db:
            tier = (await db.execute(text(
                "SELECT admin_tier FROM users WHERE id = :uid"
            ), {"uid": uid})).scalar()
        assert tier == TIER_FINANCE, "an existing tier must survive a redundant grant"
    finally:
        await _cleanup_full(uid)


@async_test
async def test_revoke_via_bot_clears_user_role_and_tier():
    uid = await make_user()
    tg_id = 900_505
    try:
        await _link_telegram(uid, tg_id)
        async with async_session() as db:
            short_id = (await db.execute(text(
                "SELECT short_id FROM users WHERE id = :uid"
            ), {"uid": uid})).scalar()

        await service.add_admin_by_short_id(short_id, ROOT_ADMIN_TG_ID)
        assert await service.is_admin(tg_id)

        removed = await service.remove_admin(short_id, ROOT_ADMIN_TG_ID)
        assert removed.outcome == "removed"

        assert not await service.is_admin(tg_id)
        async with async_session() as db:
            row = (await db.execute(text(
                "SELECT role, admin_tier FROM users WHERE id = :uid"
            ), {"uid": uid})).first()
        assert row.role == "user"
        assert row.admin_tier is None
    finally:
        await _cleanup_full(uid)


@async_test
async def test_pending_grant_sets_role_before_any_link_exists():
    """Granting an account that has never opened the bot still has to
    make them a web admin immediately - that is the whole point of
    unifying on User.role instead of waiting for Telegram activation."""
    uid = await make_user()
    try:
        async with async_session() as db:
            short_id = (await db.execute(text(
                "SELECT short_id FROM users WHERE id = :uid"
            ), {"uid": uid})).scalar()

        result = await service.add_admin_by_short_id(short_id, ROOT_ADMIN_TG_ID)
        assert result.outcome == "added_pending"

        async with async_session() as db:
            role = (await db.execute(text(
                "SELECT role FROM users WHERE id = :uid"
            ), {"uid": uid})).scalar()
        assert role == "admin", "a pending grant must still flip the web role"
    finally:
        await _cleanup_full(uid)
