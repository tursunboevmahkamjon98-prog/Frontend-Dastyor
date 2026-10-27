"""The CRM's Payments endpoints vs. the bot's own approve/reject — pytest.

Run via pytest (conftest.py in this directory does the test-database
setup):

    python -m pytest tests/test_payment_review_crm_parity.py -v

Covers Stage 4: app/routers/admin_crm.py's payment-requests endpoints
call directly into telegram.service.approve_payment/reject_payment/
request_more_info - the same compare-and-swap, same ledger/audit code
the bot's inline buttons use. The point of this suite is proving that
"CRM path" and "bot path" are the same path, not two implementations
that happen to agree today:

  * a double-approve race through the CRM endpoint collapses to
    exactly one credit, same as the existing bot-side race test,
  * a web admin with no linked Telegram chat is recorded correctly
    (actor_kind='admin_web', actor_user_id set, no telegram id at all),
  * reject/request-info never touch the balance regardless of caller.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from conftest import async_test  # noqa: E402
from test_telegram_payments import balance_of, cleanup_user, make_user  # noqa: E402

from app.database import async_session  # noqa: E402
from app.routers.admin_crm import (  # noqa: E402
    approve_payment_request,
    reject_payment_request,
    request_payment_info,
)
from app.schemas import AdminPaymentApprove, AdminPaymentDecision  # noqa: E402
from app.telegram import service  # noqa: E402

ADMIN_CHAT = 900_700  # a teacher's own chat, distinct from any admin id


class _FakeAdmin:
    def __init__(self, id: str, full_name: str = "Web Admin"):
        self.id = id
        self.full_name = full_name


async def _open_pending_request(user_id: str, requested_dirams: int = 10_000) -> str:
    view = await service.create_payment_request(user_id, ADMIN_CHAT, requested_dirams)
    async with async_session() as db:
        await db.execute(text(
            "UPDATE payment_requests SET status = 'pending' WHERE id = :id"
        ), {"id": view.id})
        await db.commit()
    return view.id


async def _cleanup_request(request_id: str, user_id: str) -> None:
    async with async_session() as db:
        await db.execute(text(
            "DELETE FROM payment_audit_log WHERE payment_request_id = :id"
        ), {"id": request_id})
        await db.execute(text(
            "DELETE FROM payment_requests WHERE id = :id"
        ), {"id": request_id})
        await db.commit()
    await cleanup_user(user_id)


@async_test
async def test_crm_approve_credits_exactly_once_via_same_cas():
    uid = await make_user()
    actor = _FakeAdmin(id=await make_user())
    try:
        request_id = await _open_pending_request(uid, requested_dirams=5_000)
        before = await balance_of(uid)

        async with async_session() as db:
            out = await approve_payment_request(
                request_id=request_id, data=AdminPaymentApprove(),
                admin=actor, db=db,
            )
            await db.commit()
        assert out.status == "approved"
        assert out.credited_somoni == 50.0
        assert await balance_of(uid) == before + 5_000

        # Second attempt must be a clean "already decided", not a
        # second credit - this is the CAS in approve_payment, exercised
        # through the CRM endpoint this time instead of the bot.
        async with async_session() as db:
            with pytest.raises(HTTPException) as exc_info:
                await approve_payment_request(
                    request_id=request_id, data=AdminPaymentApprove(),
                    admin=actor, db=db,
                )
            assert exc_info.value.status_code == 409
        assert await balance_of(uid) == before + 5_000
    finally:
        await _cleanup_request(request_id, uid)
        await cleanup_user(actor.id)


@async_test
async def test_concurrent_crm_approve_calls_credit_once():
    uid = await make_user()
    actor = _FakeAdmin(id=await make_user())
    try:
        request_id = await _open_pending_request(uid, requested_dirams=7_000)
        before = await balance_of(uid)

        async def _attempt():
            async with async_session() as db:
                try:
                    result = await approve_payment_request(
                        request_id=request_id, data=AdminPaymentApprove(),
                        admin=actor, db=db,
                    )
                    await db.commit()
                    return result
                except HTTPException as e:
                    return e

        results = await asyncio.gather(_attempt(), _attempt())
        outcomes = [r.status_code if isinstance(r, HTTPException) else "ok" for r in results]
        assert outcomes.count("ok") == 1, (
            f"exactly one of two concurrent approvals must win, got {outcomes}"
        )
        assert await balance_of(uid) == before + 7_000

        async with async_session() as db:
            tx_count = (await db.execute(text(
                "SELECT count(*) FROM balance_transactions WHERE user_id = :uid"
            ), {"uid": uid})).scalar()
        assert tx_count == 1
    finally:
        await _cleanup_request(request_id, uid)
        await cleanup_user(actor.id)


@async_test
async def test_web_admin_with_no_telegram_link_is_recorded_correctly():
    uid = await make_user()
    actor = _FakeAdmin(id=await make_user())
    try:
        request_id = await _open_pending_request(uid, requested_dirams=2_000)

        async with async_session() as db:
            await approve_payment_request(
                request_id=request_id, data=AdminPaymentApprove(), admin=actor, db=db,
            )
            await db.commit()

        async with async_session() as db:
            tx = (await db.execute(text(
                "SELECT reason, actor_id FROM balance_transactions WHERE user_id = :uid"
            ), {"uid": uid})).first()
            audit = (await db.execute(text(
                "SELECT actor_kind, actor_telegram_id, actor_user_id FROM payment_audit_log "
                "WHERE payment_request_id = :id AND event = 'approved'"
            ), {"id": request_id})).first()

        assert f"web admin {actor.id}" in tx.reason
        assert audit.actor_kind == "admin_web"
        assert audit.actor_telegram_id is None
        assert audit.actor_user_id == actor.id
    finally:
        await _cleanup_request(request_id, uid)
        await cleanup_user(actor.id)


@async_test
async def test_reject_via_crm_never_touches_balance():
    uid = await make_user()
    actor = _FakeAdmin(id=await make_user())
    try:
        request_id = await _open_pending_request(uid, requested_dirams=3_000)
        before = await balance_of(uid)

        async with async_session() as db:
            out = await reject_payment_request(
                request_id=request_id, data=AdminPaymentDecision(note="bad receipt"),
                admin=actor, db=db,
            )
            await db.commit()
        assert out.status == "rejected"
        assert await balance_of(uid) == before

        async with async_session() as db:
            tx_count = (await db.execute(text(
                "SELECT count(*) FROM balance_transactions WHERE user_id = :uid"
            ), {"uid": uid})).scalar()
        assert tx_count == 0
    finally:
        await _cleanup_request(request_id, uid)
        await cleanup_user(actor.id)


@async_test
async def test_request_info_via_crm_leaves_request_decidable():
    uid = await make_user()
    actor = _FakeAdmin(id=await make_user())
    try:
        request_id = await _open_pending_request(uid, requested_dirams=1_000)

        async with async_session() as db:
            out = await request_payment_info(
                request_id=request_id, data=AdminPaymentDecision(note="send a clearer photo"),
                admin=actor, db=db,
            )
            await db.commit()
        assert out.status == "needs_info"

        # Still decidable - approving afterwards must work normally.
        async with async_session() as db:
            approved = await approve_payment_request(
                request_id=request_id, data=AdminPaymentApprove(), admin=actor, db=db,
            )
            await db.commit()
        assert approved.status == "approved"
    finally:
        await _cleanup_request(request_id, uid)
        await cleanup_user(actor.id)


@async_test
async def test_approve_404s_for_unknown_request():
    actor = _FakeAdmin(id=await make_user())
    try:
        async with async_session() as db:
            with pytest.raises(HTTPException) as exc_info:
                await approve_payment_request(
                    request_id="00000000-0000-0000-0000-000000000000",
                    data=AdminPaymentApprove(), admin=actor, db=db,
                )
            assert exc_info.value.status_code == 404
    finally:
        await cleanup_user(actor.id)
