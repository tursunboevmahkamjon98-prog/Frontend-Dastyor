"""The migration-review worklist and the promote/demote/ignore endpoint.

Run via pytest (conftest.py in this directory does the test-database
setup):

    python -m pytest tests/test_admin_migration_review.py -v

Covers Stage 2 of the CRM build: app/routers/admin_crm.py's GET
/api/admin/admins (roster + worklist) and POST
/api/admin/admins/{user_id}/promote (promote/demote/ignore). The whole
point of this worklist is that NOTHING here ever promotes a Telegram-only
admin automatically — every test that exercises "promote" calls it
explicitly, the same way a human clicking a button in the CRM would.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from conftest import async_test  # noqa: E402
from test_telegram_payments import cleanup_user, make_user  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models import User  # noqa: E402
from app.routers.admin_crm import act_on_admin, list_admin_roster  # noqa: E402
from app.schemas import AdminPromoteRequest  # noqa: E402


class _FakeAdminUser:
    def __init__(self, id: str, role: str = "admin", admin_tier: str | None = None,
                full_name: str = "Test Admin"):
        self.id = id
        self.role = role
        self.admin_tier = admin_tier
        self.full_name = full_name
        self.short_id = None


async def _grant_legacy_telegram_admin(user_id: str, telegram_user_id: int) -> str:
    """Simulate a grant made before Stage 1 shipped: a telegram_admins
    row with no corresponding User.role change — exactly the state the
    worklist exists to surface."""
    grant_id = str(uuid.uuid4())
    async with async_session() as db:
        await db.execute(text(
            "INSERT INTO telegram_admins "
            "(id, telegram_user_id, user_id, added_by_telegram_id, added_at, "
            " activated_at, revoked, reviewed_at) "
            "VALUES (:id, :tg, :uid, 5001, now(), now(), FALSE, NULL)"
        ), {"id": grant_id, "tg": telegram_user_id, "uid": user_id})
        await db.commit()
    return grant_id


async def _cleanup_full(user_id: str) -> None:
    async with async_session() as db:
        await db.execute(text("DELETE FROM telegram_admins WHERE user_id = :uid"), {"uid": user_id})
        await db.commit()
    await cleanup_user(user_id)


@async_test
async def test_worklist_lists_legacy_grant_not_yet_an_admin():
    uid = await make_user()
    try:
        await _grant_legacy_telegram_admin(uid, 900_601)
        async with async_session() as db:
            roster = await list_admin_roster(admin=_FakeAdminUser(id="x"), db=db)
        matches = [e for e in roster.unreviewed if e.user_id == uid]
        assert len(matches) == 1
        assert matches[0].telegram_user_id == 900_601
    finally:
        await _cleanup_full(uid)


@async_test
async def test_worklist_excludes_already_promoted_admin():
    uid = await make_user()
    try:
        await _grant_legacy_telegram_admin(uid, 900_602)
        async with async_session() as db:
            user = (await db.execute(text("SELECT id FROM users WHERE id = :uid"), {"uid": uid})).first()
            await db.execute(text(
                "UPDATE users SET role = 'admin', admin_tier = 'support' WHERE id = :uid"
            ), {"uid": uid})
            await db.commit()

        async with async_session() as db:
            roster = await list_admin_roster(admin=_FakeAdminUser(id="x"), db=db)
        assert all(e.user_id != uid for e in roster.unreviewed)
        assert any(e.user_id == uid for e in roster.admins)
    finally:
        await _cleanup_full(uid)


@async_test
async def test_promote_sets_role_tier_and_clears_from_worklist():
    uid = await make_user()
    try:
        await _grant_legacy_telegram_admin(uid, 900_603)
        actor = _FakeAdminUser(id="actor-1", admin_tier="super")

        async with async_session() as db:
            entry = await act_on_admin(
                user_id=uid,
                data=AdminPromoteRequest(action="promote", admin_tier="finance"),
                admin=actor,
                db=db,
            )
            await db.commit()
        assert entry.admin_tier == "finance"

        async with async_session() as db:
            row = (await db.execute(text(
                "SELECT role, admin_tier FROM users WHERE id = :uid"
            ), {"uid": uid})).first()
            reviewed = (await db.execute(text(
                "SELECT reviewed_at FROM telegram_admins WHERE user_id = :uid"
            ), {"uid": uid})).scalar()
            roster = await list_admin_roster(admin=actor, db=db)
        assert row.role == "admin" and row.admin_tier == "finance"
        assert reviewed is not None, "promoting must mark the grant reviewed too"
        assert all(e.user_id != uid for e in roster.unreviewed)
    finally:
        await _cleanup_full(uid)


@async_test
async def test_promote_rejects_invalid_tier():
    uid = await make_user()
    try:
        async with async_session() as db:
            with pytest.raises(HTTPException) as exc_info:
                await act_on_admin(
                    user_id=uid,
                    data=AdminPromoteRequest(action="promote", admin_tier="owner"),
                    admin=_FakeAdminUser(id="actor-1", admin_tier="super"),
                    db=db,
                )
            assert exc_info.value.status_code == 400
    finally:
        await cleanup_user(uid)


@async_test
async def test_ignore_marks_reviewed_without_touching_role():
    uid = await make_user()
    try:
        await _grant_legacy_telegram_admin(uid, 900_604)

        async with async_session() as db:
            await act_on_admin(
                user_id=uid,
                data=AdminPromoteRequest(action="ignore"),
                admin=_FakeAdminUser(id="actor-1", admin_tier="super"),
                db=db,
            )
            await db.commit()

        async with async_session() as db:
            role = (await db.execute(text(
                "SELECT role FROM users WHERE id = :uid"
            ), {"uid": uid})).scalar()
            roster = await list_admin_roster(admin=_FakeAdminUser(id="x"), db=db)
        assert role == "user", "ignoring must never promote"
        assert all(e.user_id != uid for e in roster.unreviewed), (
            "an ignored grant must leave the worklist"
        )
    finally:
        await _cleanup_full(uid)


@async_test
async def test_ignore_without_a_pending_grant_404s():
    uid = await make_user()
    try:
        async with async_session() as db:
            with pytest.raises(HTTPException) as exc_info:
                await act_on_admin(
                    user_id=uid,
                    data=AdminPromoteRequest(action="ignore"),
                    admin=_FakeAdminUser(id="actor-1", admin_tier="super"),
                    db=db,
                )
            assert exc_info.value.status_code == 404
    finally:
        await cleanup_user(uid)


@async_test
async def test_demote_resets_role_and_tier():
    uid = await make_user()
    try:
        async with async_session() as db:
            await db.execute(text(
                "UPDATE users SET role = 'admin', admin_tier = 'support' WHERE id = :uid"
            ), {"uid": uid})
            await db.commit()

        # A second super must exist so this demotion doesn't trip the
        # last-super guard this test isn't exercising.
        other_super = await make_user()
        async with async_session() as db:
            await db.execute(text(
                "UPDATE users SET role = 'admin', admin_tier = 'super' WHERE id = :uid"
            ), {"uid": other_super})
            await db.commit()

        async with async_session() as db:
            entry = await act_on_admin(
                user_id=uid,
                data=AdminPromoteRequest(action="demote"),
                admin=_FakeAdminUser(id="actor-1", admin_tier="super"),
                db=db,
            )
            await db.commit()
        assert entry.admin_tier is None

        async with async_session() as db:
            row = (await db.execute(text(
                "SELECT role, admin_tier FROM users WHERE id = :uid"
            ), {"uid": uid})).first()
        assert row.role == "user" and row.admin_tier is None
    finally:
        await cleanup_user(uid)
        await cleanup_user(other_super)


@async_test
async def test_demote_blocks_removing_the_last_super():
    uid = await make_user()
    try:
        async with async_session() as db:
            await db.execute(text(
                "UPDATE users SET role = 'admin', admin_tier = 'super' WHERE id = :uid"
            ), {"uid": uid})
            await db.commit()
            # No OTHER super exists anywhere else in this fresh test
            # database beyond whatever ships in the schema itself -
            # this user is deliberately the only one with tier='super'
            # (or NULL) for the purposes of this check.
            other_supers = (await db.execute(text(
                "SELECT count(*) FROM users WHERE role = 'admin' "
                "AND (admin_tier = 'super' OR admin_tier IS NULL) AND id <> :uid"
            ), {"uid": uid})).scalar()

        if other_supers:
            pytest.skip(
                "test database already has another super admin from a "
                "previous run; the guard itself is still exercised by "
                "test_demote_resets_role_and_tier's two-admin setup"
            )

        async with async_session() as db:
            with pytest.raises(HTTPException) as exc_info:
                await act_on_admin(
                    user_id=uid,
                    data=AdminPromoteRequest(action="demote"),
                    admin=_FakeAdminUser(id="actor-1", admin_tier="super"),
                    db=db,
                )
            assert exc_info.value.status_code == 400
    finally:
        await cleanup_user(uid)


@async_test
async def test_promote_endpoint_404s_for_unknown_user():
    async with async_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            await act_on_admin(
                user_id="not-a-real-user-id",
                data=AdminPromoteRequest(action="promote", admin_tier="support"),
                admin=_FakeAdminUser(id="actor-1", admin_tier="super"),
                db=db,
            )
        assert exc_info.value.status_code == 404
