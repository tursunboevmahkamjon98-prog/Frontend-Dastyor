"""Global ledger browser and audit log — pytest.

Run via pytest (conftest.py in this directory does the test-database
setup):

    python -m pytest tests/test_ledger_audit_endpoints.py -v

Covers Stage 5: app/routers/admin_crm.py's list_balance_transactions
and list_audit_log — both read-only, no state changes to verify beyond
"the filters actually filter and the right user/actor names resolve".
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
from app.routers.admin_crm import list_audit_log, list_balance_transactions  # noqa: E402


class _FakeAdmin:
    def __init__(self, id: str = "actor-ledger"):
        self.id = id


ACTOR = _FakeAdmin()


async def _insert_tx(user_id: str, kind: str, amount_dirams: int = 100) -> str:
    tx_id = str(uuid.uuid4())
    async with async_session() as db:
        await db.execute(text(
            "INSERT INTO balance_transactions "
            "(id, user_id, kind, amount_dirams, balance_before, balance_after, created_at) "
            "VALUES (:id, :uid, :kind, :amt, 0, :amt, now())"
        ), {"id": tx_id, "uid": user_id, "kind": kind, "amt": amount_dirams})
        await db.commit()
    return tx_id


async def _insert_audit(event: str, actor_user_id: str | None = None) -> str:
    entry_id = str(uuid.uuid4())
    async with async_session() as db:
        await db.execute(text(
            "INSERT INTO payment_audit_log "
            "(id, payment_request_id, event, actor_kind, actor_user_id, detail, created_at) "
            "VALUES (:id, :subject, :event, 'admin_web', :actor, '{}', now())"
        ), {"id": entry_id, "subject": "test-subject", "event": event, "actor": actor_user_id})
        await db.commit()
    return entry_id


async def _cleanup_tx(*tx_ids: str) -> None:
    async with async_session() as db:
        for tid in tx_ids:
            await db.execute(text("DELETE FROM balance_transactions WHERE id = :id"), {"id": tid})
        await db.commit()


async def _cleanup_audit(*entry_ids: str) -> None:
    async with async_session() as db:
        for eid in entry_ids:
            await db.execute(text("DELETE FROM payment_audit_log WHERE id = :id"), {"id": eid})
        await db.commit()


@async_test
async def test_balance_transactions_filters_by_user_and_shows_user_name():
    uid = await make_user()
    other = await make_user()
    try:
        tx1 = await _insert_tx(uid, "topup", 500)
        tx2 = await _insert_tx(other, "topup", 900)

        async with async_session() as db:
            rows = await list_balance_transactions(
                user_id=uid, kind=None, date_from=None, date_to=None,
                limit=100, offset=0, admin=ACTOR, db=db,
            )
        ids = [r.id for r in rows]
        assert tx1 in ids
        assert tx2 not in ids
        match = next(r for r in rows if r.id == tx1)
        assert match.user_id == uid
        assert match.amount_somoni == 5.0
    finally:
        await _cleanup_tx(tx1, tx2)
        await cleanup_user(uid)
        await cleanup_user(other)


@async_test
async def test_balance_transactions_filters_by_kind():
    uid = await make_user()
    try:
        tx_topup = await _insert_tx(uid, "topup", 100)
        tx_charge = await _insert_tx(uid, "charge", -50)

        async with async_session() as db:
            rows = await list_balance_transactions(
                user_id=uid, kind="charge", date_from=None, date_to=None,
                limit=100, offset=0, admin=ACTOR, db=db,
            )
        ids = [r.id for r in rows]
        assert tx_charge in ids
        assert tx_topup not in ids
    finally:
        await _cleanup_tx(tx_topup, tx_charge)
        await cleanup_user(uid)


@async_test
async def test_audit_log_filters_by_event_and_actor():
    entry_a = await _insert_audit("card_created", actor_user_id="actor-A")
    entry_b = await _insert_audit("expense_created", actor_user_id="actor-B")
    try:
        async with async_session() as db:
            by_event = await list_audit_log(
                event="card_created", actor_user_id=None, actor_telegram_id=None,
                date_from=None, date_to=None, limit=100, offset=0,
                admin=ACTOR, db=db,
            )
        event_ids = [r.id for r in by_event]
        assert entry_a in event_ids
        assert entry_b not in event_ids

        async with async_session() as db:
            by_actor = await list_audit_log(
                event=None, actor_user_id="actor-B", actor_telegram_id=None,
                date_from=None, date_to=None, limit=100, offset=0,
                admin=ACTOR, db=db,
            )
        actor_ids = [r.id for r in by_actor]
        assert entry_b in actor_ids
        assert entry_a not in actor_ids
    finally:
        await _cleanup_audit(entry_a, entry_b)


@async_test
async def test_balance_transactions_respects_limit():
    uid = await make_user()
    tx_ids = [await _insert_tx(uid, "topup", 10) for _ in range(5)]
    try:
        async with async_session() as db:
            rows = await list_balance_transactions(
                user_id=uid, kind=None, date_from=None, date_to=None,
                limit=2, offset=0, admin=ACTOR, db=db,
            )
        assert len(rows) == 2
    finally:
        await _cleanup_tx(*tx_ids)
        await cleanup_user(uid)
