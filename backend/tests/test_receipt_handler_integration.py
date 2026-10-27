"""PaymentBot.handle_receipt() — the actual wiring, not just its pieces.

Run via pytest (conftest.py does the test-database setup):

    python -m pytest tests/test_receipt_handler_integration.py -v

Audit finding this closes: test_telegram_payments.py's receipt tests
all call service.attach_receipt(...) directly with a hand-built scan
(via ocr.cross_check(receipt_scan(...), ...)) - none of them ever call
bot.handle_receipt() itself, so nothing proves the real message handler
actually invokes OCR/cross_check before filing the request, or that an
OCR crash still reaches admin review instead of being silently lost.
grep confirms zero references to handle_receipt in that file.

Reading app/telegram/bot.py:744-861 shows the real sequence is
scan_receipt() -> cross_check() -> service.attach_receipt() ->
notify_admins(), with every OCR-failure engine still falling through
to attach_receipt/notify_admins rather than returning early. These
tests exercise that sequence through the real method, with a fake
Telegram client (download_file returns deterministic bytes) and
scan_receipt patched for determinism regardless of whether tesseract
is installed in the environment running this suite.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from conftest import async_test  # noqa: E402
from test_telegram_payments import FakeTelegram, balance_of, cleanup_user, make_user  # noqa: E402

from app.database import async_session  # noqa: E402
from app.telegram import bot as bot_module  # noqa: E402
from app.telegram import ocr, service  # noqa: E402
from app.telegram.bot import PaymentBot  # noqa: E402

CHAT_ID = 900_900


async def _link(user_id: str, chat_id: int) -> None:
    async with async_session() as db:
        await db.execute(text(
            "INSERT INTO telegram_accounts (id, user_id, chat_id, telegram_user_id, linked_at, last_seen_at, revoked) "
            "VALUES (:id, :uid, :chat, :chat, now(), now(), FALSE)"
        ), {"id": str(uuid.uuid4()), "uid": user_id, "chat": chat_id})
        await db.commit()


async def _request_row(request_id: str):
    async with async_session() as db:
        return (await db.execute(text(
            "SELECT status, ocr_engine, ocr_warnings, ocr_amount_dirams, credited_dirams "
            "FROM payment_requests WHERE id = :id"
        ), {"id": request_id})).first()


async def _cleanup(request_id: str, user_id: str) -> None:
    async with async_session() as db:
        await db.execute(text("DELETE FROM payment_audit_log WHERE payment_request_id = :id"), {"id": request_id})
        await db.execute(text("DELETE FROM payment_requests WHERE id = :id"), {"id": request_id})
        await db.execute(text("DELETE FROM telegram_accounts WHERE user_id = :uid"), {"uid": user_id})
        await db.commit()
    await cleanup_user(user_id)


@async_test
async def test_handle_receipt_calls_real_ocr_and_cross_check_before_filing():
    """The exact chain the audit asked to verify: scan_receipt() is
    actually invoked with the downloaded bytes, its result goes through
    cross_check() (which adds a recipient_mismatch warning here, since
    the fake recipient does not match TELEGRAM_PAY_RECIPIENT="DASTYOR
    LLC"), and THAT mutated scan - not a blank one - is what
    attach_receipt persists."""
    uid = await make_user()
    await _link(uid, CHAT_ID)
    req = await service.create_payment_request(uid, CHAT_ID, 5_000)

    calls = []

    def fake_scan_receipt(data: bytes, mime: str | None) -> ocr.ReceiptScan:
        calls.append((data, mime))
        return ocr.extract_fields(
            "Маблаг: 50,00 TJS\n"
            "Кабулкунанда: SOMEONE ELSE\n"
            "Раками амалиёт: TXN-WIRING-1\n"
        )

    original = bot_module.scan_receipt
    bot_module.scan_receipt = fake_scan_receipt
    try:
        fake = FakeTelegram()
        pbot = PaymentBot(client=fake, admin_client=fake)
        await pbot.handle_receipt(CHAT_ID, {"photo": [{"file_id": "wire1", "file_size": 999}]})
    finally:
        bot_module.scan_receipt = original

    assert len(calls) == 1, "scan_receipt must be called exactly once with the downloaded bytes"
    assert calls[0][0] == b"\xff\xd8\xff\xe0 fake jpeg bytes"

    row = await _request_row(req.id)
    assert row.status == "pending", "a receipt must land in pending (admin review), never auto-approved"
    assert row.ocr_engine is not None, "the persisted row must carry the REAL scan's engine, not a blank default"
    assert row.ocr_amount_dirams == 5000
    assert "recipient_mismatch" in (row.ocr_warnings or "")
    assert row.credited_dirams in (0, None)
    assert await balance_of(uid) == 0, "no balance change before any admin decision"

    assert fake.messages or fake.photos or fake.documents, "the admin must have been notified"
    sent_text = " ".join(m[1] for m in fake.messages) + " ".join(p[1] for p in fake.photos) + " ".join(d[1] for d in fake.documents)
    # The admin caption is intentionally short (product decision) and no
    # longer prints the raw OCR reference or public_code - the real proof
    # that OCR/cross_check ran on the actual scan is the persisted row
    # assertions above (engine, amount, recipient_mismatch warning).
    assert "50,00" in sent_text, "the admin message must show the OCR'd amount"

    await _cleanup(req.id, uid)


@async_test
async def test_ocr_crash_still_reaches_admin_review_not_silently_dropped():
    """scan_receipt raising must still reach the admin - a decode/
    infra failure (engine='scan-error') says nothing about whether the
    file itself is a real receipt, and is explicitly excluded from the
    amount-based bounce-back (see the _OCR_FAILURE_ENGINES comment in
    bot.py) specifically so this degrades to manual review rather than
    rejecting every receipt whenever OCR itself is unavailable."""
    uid = await make_user()
    await _link(uid, CHAT_ID + 1)
    req = await service.create_payment_request(uid, CHAT_ID + 1, 3_000)

    def crashing_scan_receipt(data: bytes, mime: str | None) -> ocr.ReceiptScan:
        raise RuntimeError("simulated OCR crash")

    original = bot_module.scan_receipt
    bot_module.scan_receipt = crashing_scan_receipt
    try:
        fake = FakeTelegram()
        pbot = PaymentBot(client=fake, admin_client=fake)
        await pbot.handle_receipt(CHAT_ID + 1, {"photo": [{"file_id": "wire2", "file_size": 999}]})
    finally:
        bot_module.scan_receipt = original

    row = await _request_row(req.id)
    assert row is not None
    assert row.status == "pending", "an OCR crash must still file the request for human review"
    assert row.ocr_engine == "scan-error"
    assert row.credited_dirams in (0, None)
    assert await balance_of(uid) == 0

    assert fake.messages or fake.photos or fake.documents, "the admin must still be notified when OCR itself crashed"

    await _cleanup(req.id, uid)


@async_test
async def test_clean_scan_with_no_amount_asks_for_resend_without_admin():
    """OCR running successfully (engine='text', not a failure engine)
    on an image with no amount in it at all - e.g. a logo sheet - must
    still bounce back to the teacher rather than reach the admin."""
    uid = await make_user()
    await _link(uid, CHAT_ID + 3)
    req = await service.create_payment_request(uid, CHAT_ID + 3, 3_000)

    def no_amount_scan(data: bytes, mime: str | None) -> ocr.ReceiptScan:
        return ocr.extract_fields("Dastyor - o'qituvchilar uchun sun'iy intellekt yordamchisi")

    original = bot_module.scan_receipt
    bot_module.scan_receipt = no_amount_scan
    try:
        fake = FakeTelegram()
        pbot = PaymentBot(client=fake, admin_client=fake)
        await pbot.handle_receipt(CHAT_ID + 3, {"photo": [{"file_id": "wire4", "file_size": 999}]})
    finally:
        bot_module.scan_receipt = original

    row = await _request_row(req.id)
    assert row.status == "awaiting_receipt"
    admin_ids = {5001, 5002}
    assert not any(m[0] in admin_ids for m in fake.messages)
    assert await balance_of(uid) == 0

    await _cleanup(req.id, uid)
