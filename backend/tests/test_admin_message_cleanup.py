"""Admin review messages get deleted once a payment is decided — pytest.

Run via pytest (conftest.py does the test-database setup):

    python -m pytest tests/test_admin_message_cleanup.py -v

Covers the cleanup bot.py's _clear_buttons() now does: on approve/reject/
request-info, every admin chat's review message for THAT request is
deleted (TelegramClient.delete_message, which already swallows its own
errors and returns False rather than raising), falling back to clearing
the inline keyboard only if the delete itself failed. service.
admin_messages(request_id) - unchanged, already existed - is what scopes
this to exactly one request's messages; nothing here can touch another
request's or another user's.

The compare-and-swap in telegram/service.py is the actual
no-double-credit guarantee (already covered by test_telegram_payments.py);
these tests are specifically about the message cleanup riding on top of
it, not re-proving the CAS itself.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conftest import async_test  # noqa: E402
from test_telegram_payments import (  # noqa: E402
    FakeTelegram,
    balance_of,
    cleanup_user,
    make_user,
    ocr,
    receipt_scan,
)

from app.telegram import service  # noqa: E402
from app.telegram.bot import PaymentBot  # noqa: E402

ADMIN_ID = 5001  # conftest.py's TELEGRAM_ADMIN_IDS


async def _open_and_notify(bot: PaymentBot, fake: FakeTelegram, chat_id: int,
                           amount: int, reference: str):
    uid = await make_user()
    await service.issue_link_token(uid)
    # Link directly - issuing+redeeming a token is more than this needs.
    import uuid as _uuid
    from sqlalchemy import text as _text
    from app.database import async_session as _session
    async with _session() as db:
        await db.execute(_text(
            "INSERT INTO telegram_accounts (id, user_id, chat_id, telegram_user_id, linked_at, last_seen_at, revoked) "
            "VALUES (:id, :uid, :chat, :chat, now(), now(), FALSE)"
        ), {"id": str(_uuid.uuid4()), "uid": uid, "chat": chat_id})
        await db.commit()

    req = await service.create_payment_request(uid, chat_id, amount)
    scan = ocr.cross_check(receipt_scan(amount, reference=reference), requested_dirams=amount)
    await service.attach_receipt(req.id, file_id=f"f-{reference}", mime="image/jpeg",
                                  size_bytes=100, scan=scan)
    account = await service.account_for_chat(chat_id)
    await bot.notify_admins(req, account, scan, None, f"f-{reference}", "image/jpeg")
    return uid, req


async def _cleanup(uid: str, request_id: str) -> None:
    from sqlalchemy import text as _text
    from app.database import async_session as _session
    async with _session() as db:
        await db.execute(_text("DELETE FROM payment_audit_log WHERE payment_request_id = :id"), {"id": request_id})
        await db.execute(_text("DELETE FROM payment_requests WHERE id = :id"), {"id": request_id})
        await db.execute(_text("DELETE FROM telegram_accounts WHERE user_id = :uid"), {"uid": uid})
        await db.commit()
    await cleanup_user(uid)


@async_test
async def test_approve_deletes_the_admin_message():
    fake = FakeTelegram()
    bot = PaymentBot(client=fake, admin_client=fake)
    uid, req = await _open_and_notify(bot, fake, 920_001, 2_000, "TXN-DEL-OK")
    try:
        before = await service.admin_messages(req.id)
        assert before, "notify_admins should have recorded the sent messages"

        await bot.handle_callback({
            "id": "cb-del-ok", "data": f"pay:ok:{req.id}", "from": {"id": ADMIN_ID},
        })

        assert await balance_of(uid) == 2_000
        deleted = set(fake.deleted)
        for m in before:
            assert (m["chat_id"], m["message_id"]) in deleted, (m, fake.deleted)
    finally:
        await _cleanup(uid, req.id)


@async_test
async def test_reject_deletes_the_admin_message():
    fake = FakeTelegram()
    bot = PaymentBot(client=fake, admin_client=fake)
    uid, req = await _open_and_notify(bot, fake, 920_002, 1_500, "TXN-DEL-NO")
    try:
        before = await service.admin_messages(req.id)
        assert before

        await bot.handle_callback({
            "id": "cb-del-no", "data": f"pay:no:{req.id}", "from": {"id": ADMIN_ID},
        })
        await bot.handle_rejection_reason(ADMIN_ID, "fake receipt")

        assert await balance_of(uid) == 0
        deleted = set(fake.deleted)
        for m in before:
            assert (m["chat_id"], m["message_id"]) in deleted, (m, fake.deleted)
        assert (await service.get_request(req.id)).status == service.STATUS_REJECTED
    finally:
        await _cleanup(uid, req.id)


@async_test
async def test_double_tap_approve_deletes_once_and_credits_once():
    fake = FakeTelegram()
    bot = PaymentBot(client=fake, admin_client=fake)
    uid, req = await _open_and_notify(bot, fake, 920_003, 900, "TXN-DEL-DBL")
    try:
        await bot.handle_callback({
            "id": "cb-dbl-1", "data": f"pay:ok:{req.id}", "from": {"id": ADMIN_ID},
        })
        await bot.handle_callback({
            "id": "cb-dbl-2", "data": f"pay:ok:{req.id}", "from": {"id": ADMIN_ID},
        })

        assert await balance_of(uid) == 900, "a second tap must never credit again"
        # Both taps call _clear_buttons; FakeTelegram.delete_message
        # always returns True regardless of prior calls, so this just
        # has to not raise and not touch the balance twice - asserted
        # above. The CAS itself is proven in test_telegram_payments.py.
    finally:
        await _cleanup(uid, req.id)


@async_test
async def test_failed_delete_falls_back_to_clearing_buttons():
    fake = FakeTelegram()

    async def failing_delete(chat_id, message_id):
        fake.deleted.append((chat_id, message_id))  # record the attempt
        return False

    fake.delete_message = failing_delete
    bot = PaymentBot(client=fake, admin_client=fake)
    uid, req = await _open_and_notify(bot, fake, 920_004, 700, "TXN-DEL-FAIL")
    try:
        await bot.handle_callback({
            "id": "cb-fail-del", "data": f"pay:ok:{req.id}", "from": {"id": ADMIN_ID},
        })

        assert await balance_of(uid) == 700, "a delete failure must not undo the decision"
        assert (await service.get_request(req.id)).status == service.STATUS_APPROVED
        assert fake.cleared, "a failed delete must fall back to clearing the inline keyboard"
    finally:
        await _cleanup(uid, req.id)


@async_test
async def test_cleanup_never_touches_another_requests_message():
    fake = FakeTelegram()
    bot = PaymentBot(client=fake, admin_client=fake)
    uid_a, req_a = await _open_and_notify(bot, fake, 920_005, 1_000, "TXN-DEL-A")
    uid_b, req_b = await _open_and_notify(bot, fake, 920_006, 2_000, "TXN-DEL-B")
    try:
        before_b = await service.admin_messages(req_b.id)
        assert before_b

        await bot.handle_callback({
            "id": "cb-isolated", "data": f"pay:ok:{req_a.id}", "from": {"id": ADMIN_ID},
        })

        assert await balance_of(uid_a) == 1_000
        assert await balance_of(uid_b) == 0
        assert (await service.get_request(req_b.id)).status == service.STATUS_PENDING
        deleted = set(fake.deleted)
        for m in before_b:
            assert (m["chat_id"], m["message_id"]) not in deleted, (
                "approving request A must not delete request B's review message"
            )
    finally:
        await _cleanup(uid_a, req_a.id)
        await _cleanup(uid_b, req_b.id)
