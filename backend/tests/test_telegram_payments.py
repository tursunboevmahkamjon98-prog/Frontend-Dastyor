"""Telegram payment flow: integration tests against a real Postgres.

Run from the backend directory:

    python tests/test_telegram_payments.py

These need a real Postgres because the guarantees under test *are*
Postgres behaviour: ``UPDATE ... WHERE status = 'pending' RETURNING`` as
a compare-and-swap, a partial unique index, row-level locking under
concurrent approval, and transaction rollback. SQLite would pass while
proving nothing.

The tests create and use their own database (default ``dastyor_bot_test``)
derived from DATABASE_URL, so the development data is never touched. Set
TELEGRAM_TEST_DATABASE to override the name.

Nothing here reaches Telegram or an OCR binary: the Bot API client is a
recording fake, and receipt scans are built from text fixtures. No real
payment is made and no real admin is messaged.
"""

import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------
# Point the app at a dedicated test database BEFORE importing anything
# that builds an engine. app.database creates its engine at import time
# from the settings, so this has to happen first.
# ---------------------------------------------------------------------

from dotenv import dotenv_values  # noqa: E402

_env = dotenv_values(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), ".env"))

_TEST_DB = os.environ.get("TELEGRAM_TEST_DATABASE", "dastyor_bot_test")


def _swap_database(url: str, name: str) -> str:
    head, _, _ = url.rpartition("/")
    return f"{head}/{name}"


_async_url = os.environ.get("DATABASE_URL") or _env.get("DATABASE_URL")
_sync_url = os.environ.get("DATABASE_URL_SYNC") or _env.get("DATABASE_URL_SYNC")

if not _async_url:
    print("DATABASE_URL is not set and backend/.env has none - cannot run "
          "integration tests")
    sys.exit(2)

os.environ["DATABASE_URL"] = _swap_database(_async_url, _TEST_DB)
if _sync_url:
    os.environ["DATABASE_URL_SYNC"] = _swap_database(_sync_url, _TEST_DB)
os.environ.setdefault("SECRET_KEY", _env.get("SECRET_KEY") or "test-only")
os.environ.setdefault("AI_API_KEY", _env.get("AI_API_KEY") or "test-only")

# Bot config for the tests. The token is a syntactically valid dummy and
# is never sent anywhere: every Bot API call goes to the fake below.
os.environ["TELEGRAM_BOT_TOKEN"] = "1111111111:TESTTESTTESTTESTTESTTESTTESTTESTTEST"
os.environ["TELEGRAM_BOT_USERNAME"] = "dastyor_test_bot"
os.environ["TELEGRAM_ADMIN_IDS"] = "5001,5002"
os.environ["TELEGRAM_PAY_INSTRUCTIONS"] = "TEST ONLY - no real account details."
os.environ["TELEGRAM_PAY_RECIPIENT"] = "DASTYOR LLC"
os.environ["TELEGRAM_LINK_TOKEN_TTL_SECONDS"] = "600"

_ASYNCPG_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")


async def _ensure_database() -> None:
    """Create the test database if it does not exist yet."""
    import asyncpg

    admin_url = _swap_database(_ASYNCPG_URL, "postgres")
    conn = await asyncpg.connect(admin_url)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", _TEST_DB
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{_TEST_DB}"')
            print(f"created test database {_TEST_DB}")
    finally:
        await conn.close()


asyncio.run(_ensure_database())

from sqlalchemy import text  # noqa: E402

from app import limits  # noqa: E402
from app.database import async_session, init_db  # noqa: E402
from app.telegram import ocr, service  # noqa: E402
from app.telegram.api import TelegramApiError, TelegramTransportError  # noqa: E402
from app.telegram.bot import PaymentBot  # noqa: E402
from app.telegram.config import get_telegram_settings  # noqa: E402

FAIL = []


def check(name, condition, detail=""):
    print(("  PASS  " if condition else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not condition:
        FAIL.append(name)


def section(title):
    print()
    print(title)


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------

async def make_user(balance_dirams: int = 0, language: str = "Тоҷикӣ") -> str:
    uid = str(uuid.uuid4())
    async with async_session() as db:
        await db.execute(
            text(
                "INSERT INTO users (id, full_name, hashed_password, language, role, "
                " balance_dirams, free_generation_used, phone_verified, is_premium, "
                " short_id, free_konspekt_used, free_lektsiya_used, free_test_used, "
                " free_prezentatsiya_used, free_amaliy_used, free_igra_used, created_at) "
                "VALUES (:id, 'Telegram test teacher', 'x', :lang, 'user', :bal, "
                "        TRUE, FALSE, FALSE, :sid, 99, 99, 99, 99, 99, 99, now())"
            ),
            {"id": uid, "bal": balance_dirams, "lang": language,
             "sid": str(abs(hash(uid)) % 1000000).zfill(6)},
        )
        await db.commit()
    return uid


async def cleanup_user(uid: str) -> None:
    async with async_session() as db:
        for table, column in (
            ("payment_audit_log", None),
            ("payment_requests", "user_id"),
            ("telegram_link_tokens", "user_id"),
            ("telegram_accounts", "user_id"),
            ("balance_transactions", "user_id"),
        ):
            if column is None:
                await db.execute(text(
                    "DELETE FROM payment_audit_log WHERE payment_request_id IN "
                    "(SELECT id FROM payment_requests WHERE user_id = :uid)"
                ), {"uid": uid})
            else:
                await db.execute(
                    text(f"DELETE FROM {table} WHERE {column} = :uid"), {"uid": uid}
                )
        await db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
        await db.commit()


async def balance_of(uid: str) -> int:
    async with async_session() as db:
        return (await db.execute(
            text("SELECT balance_dirams FROM users WHERE id = :uid"), {"uid": uid}
        )).scalar()


async def ledger_rows(uid: str) -> list[tuple]:
    async with async_session() as db:
        return (await db.execute(
            text("SELECT kind, amount_dirams, balance_before, balance_after, reason "
                 "FROM balance_transactions WHERE user_id = :uid "
                 "ORDER BY created_at"),
            {"uid": uid},
        )).all()


async def audit_events(request_id: str) -> list[str]:
    async with async_session() as db:
        return [r[0] for r in (await db.execute(
            text("SELECT event FROM payment_audit_log "
                 "WHERE payment_request_id = :id ORDER BY created_at"),
            {"id": request_id},
        )).all()]


def receipt_scan(amount_dirams: int, reference: str = "TXN-0001",
                 recipient: str = "DASTYOR LLC") -> ocr.ReceiptScan:
    """A scan built from a text fixture - no image, no tesseract."""
    somoni = f"{amount_dirams / 100:.2f}".replace(".", ",")
    return ocr.extract_fields(
        f"Маблаг: {somoni} TJS\n"
        f"Фиристанда: TEST TEACHER\n"
        f"Кабулкунанда: {recipient}\n"
        f"Раками амалиёт: {reference}\n"
        f"Сана: 19.10.2026 12:00\n"
        f"Холат: Муваффак\n"
    )


class FakeTelegram:
    """Recording stand-in for TelegramClient.

    ``fail_sends`` makes every outbound message raise, which is how the
    notification-failure case is exercised without touching the network.
    """

    def __init__(self, fail_sends: bool = False):
        self.fail_sends = fail_sends
        self.messages: list[tuple[int, str]] = []
        self.photos: list[tuple[int, str]] = []
        self.documents: list[tuple[int, str]] = []
        self.answers: list[dict] = []
        self.cleared: list[tuple[int, int]] = []
        self.uploaded: list[tuple] = []
        self.deleted: list[tuple[int, int]] = []
        self._message_id = 1000

    def _next_id(self) -> int:
        self._message_id += 1
        return self._message_id

    async def send_message(self, chat_id, text_body, **kwargs):
        if self.fail_sends:
            raise TelegramTransportError("fake: network down")
        self.messages.append((chat_id, text_body))
        return {"message_id": self._next_id()}

    async def send_photo(self, chat_id, photo, caption=None, **kwargs):
        if self.fail_sends:
            raise TelegramApiError("sendPhoto", 403, "fake: bot blocked by user")
        self.photos.append((chat_id, caption or ""))
        return {"message_id": self._next_id()}

    async def send_document(self, chat_id, document, caption=None, **kwargs):
        if self.fail_sends:
            raise TelegramApiError("sendDocument", 403, "fake: blocked")
        self.documents.append((chat_id, caption or ""))
        return {"message_id": self._next_id()}

    async def answer_callback_query(self, callback_query_id, text=None,
                                    show_alert=False):
        self.answers.append({"id": callback_query_id, "text": text,
                             "alert": show_alert})
        return {}

    async def edit_message_reply_markup(self, chat_id, message_id,
                                        reply_markup=None):
        self.cleared.append((chat_id, message_id))
        return {}

    async def get_file(self, file_id):
        return {"file_path": f"photos/{file_id}.jpg", "file_size": 2048}

    async def download_file(self, file_path, *, max_bytes):
        return b"\xff\xd8\xff\xe0 fake jpeg bytes"

    async def call(self, method, payload=None, *, files=None, attempts=None):
        """Raw multipart path, used when a separate admin bot has to
        re-upload the receipt bytes instead of resending a file_id."""
        if self.fail_sends:
            raise TelegramApiError(method, 403, "fake: blocked")
        payload = payload or {}
        caption = payload.get("caption") or ""
        chat_id = payload.get("chat_id")
        if method == "sendDocument":
            self.documents.append((chat_id, caption))
        else:
            self.photos.append((chat_id, caption))
        self.uploaded.append((method, files and list(files)))
        return {"message_id": self._next_id()}

    async def delete_message(self, chat_id, message_id):
        self.deleted.append((chat_id, message_id))
        return True

    async def get_me(self):
        return {"username": "dastyor_test_bot", "id": 1111111111}

    async def aclose(self):
        return None

    def texts_to(self, chat_id: int) -> list[str]:
        return [body for cid, body in self.messages if cid == chat_id]

    def all_text(self) -> str:
        return "\n".join(body for _, body in self.messages)


# ---------------------------------------------------------------------
# Account linking
# ---------------------------------------------------------------------

async def test_linking():
    section("Secure account linking")

    uid = await make_user()
    chat_id = 900001
    try:
        issued = await service.issue_link_token(uid)
        token = issued.deep_link.split("start=", 1)[1]

        check("deep link points at the configured bot",
              issued.deep_link.startswith("https://t.me/dastyor_test_bot?start="),
              issued.deep_link)
        check("deep link leaks no user id", uid not in issued.deep_link)

        # Only the hash is persisted.
        async with async_session() as db:
            stored = (await db.execute(
                text("SELECT token_hash FROM telegram_link_tokens WHERE user_id = :u"),
                {"u": uid},
            )).scalar()
        check("only a sha256 hash is stored, never the raw token",
              stored == service.hash_link_token(token) and stored != token,
              str(stored)[:16])

        result = await service.redeem_link_token(token, chat_id, 7001)
        check("valid token links the account", result.outcome == "linked",
              result.outcome)
        check("linked account is the authenticated one",
              result.account is not None and result.account.user_id == uid)

        account = await service.account_for_chat(chat_id)
        check("chat now resolves to the account", account is not None
              and account.user_id == uid)
        check("account label exposes only short id and name",
              account.short_id in account.label and "@" not in account.label,
              account.label)

        # The non-sensitive view must not carry contact details at all.
        fields = set(vars(account).keys())
        check("LinkedAccount carries no email/phone/password/token field",
              not (fields & {"email", "phone", "hashed_password", "access_token"}),
              str(fields))
    finally:
        await cleanup_user(uid)


async def test_token_reuse_and_expiry():
    section("Expired and reused linking tokens")

    uid = await make_user()
    try:
        issued = await service.issue_link_token(uid)
        token = issued.deep_link.split("start=", 1)[1]

        first = await service.redeem_link_token(token, 900002, 7002)
        check("first redemption succeeds", first.outcome == "linked", first.outcome)

        second = await service.redeem_link_token(token, 900003, 7003)
        check("the same token cannot be redeemed twice",
              second.outcome == "used", second.outcome)
        check("a replayed token links nothing", second.account is None)

        third = await service.account_for_chat(900003)
        check("the replaying chat was NOT linked", third is None)

        # Expiry: write a token whose expires_at is already past.
        raw = service.generate_link_token()
        async with async_session() as db:
            await db.execute(
                text("INSERT INTO telegram_link_tokens "
                     "(id, user_id, token_hash, expires_at, used, created_at) "
                     "VALUES (:id, :uid, :h, now() - interval '1 minute', FALSE, now())"),
                {"id": str(uuid.uuid4()), "uid": uid,
                 "h": service.hash_link_token(raw)},
            )
            await db.commit()

        expired = await service.redeem_link_token(raw, 900004, 7004)
        check("an expired token is refused", expired.outcome == "expired",
              expired.outcome)
        check("the expiring chat was NOT linked",
              await service.account_for_chat(900004) is None)

        again = await service.redeem_link_token(raw, 900004, 7004)
        check("an expired token is burned, so a retry reports used/expired",
              again.outcome in ("used", "expired"), again.outcome)

        check("an unknown token is invalid",
              (await service.redeem_link_token(
                  service.generate_link_token(), 900005, 7005)).outcome == "invalid")
        check("a too-short token is rejected without a database lookup",
              (await service.redeem_link_token("x", 900006, 7006)).outcome == "invalid")

        # Issuing a new token must invalidate the previous unused one.
        a = await service.issue_link_token(uid)
        b = await service.issue_link_token(uid)
        token_a = a.deep_link.split("start=", 1)[1]
        stale = await service.redeem_link_token(token_a, 900007, 7007)
        check("issuing a new link invalidates the previous unused one",
              stale.outcome == "used", stale.outcome)
        fresh = await service.redeem_link_token(
            b.deep_link.split("start=", 1)[1], 900002, 7002)
        check("the newest link still works", fresh.outcome == "linked", fresh.outcome)
    finally:
        await cleanup_user(uid)
        async with async_session() as db:
            for chat in (900002, 900003, 900004, 900005, 900006, 900007):
                await db.execute(
                    text("DELETE FROM telegram_accounts WHERE chat_id = :c"),
                    {"c": chat})
            await db.commit()


async def test_chat_cannot_be_hijacked():
    section("One chat cannot serve two accounts")

    victim = await make_user()
    attacker = await make_user()
    chat_id = 900010
    try:
        v = await service.issue_link_token(victim)
        await service.redeem_link_token(v.deep_link.split("start=", 1)[1], chat_id, 7010)

        a = await service.issue_link_token(attacker)
        result = await service.redeem_link_token(
            a.deep_link.split("start=", 1)[1], chat_id, 7010)

        check("a chat already linked elsewhere is refused",
              result.outcome == "chat_taken", result.outcome)
        still = await service.account_for_chat(chat_id)
        check("the original account keeps the chat",
              still is not None and still.user_id == victim)
    finally:
        await cleanup_user(victim)
        await cleanup_user(attacker)


# ---------------------------------------------------------------------
# Approve / reject / more info
# ---------------------------------------------------------------------

async def _linked_user(chat_id: int, balance: int = 0) -> str:
    uid = await make_user(balance_dirams=balance)
    issued = await service.issue_link_token(uid)
    await service.redeem_link_token(
        issued.deep_link.split("start=", 1)[1], chat_id, chat_id)
    return uid


async def test_approve_credits_once():
    section("Approval credits the balance exactly once, atomically")

    chat_id = 900020
    uid = await _linked_user(chat_id, balance=1000)
    try:
        request = await service.create_payment_request(uid, chat_id, 5000)
        check("request opens awaiting a receipt",
              request.status == service.STATUS_AWAITING_RECEIPT, request.status)
        check("request has a unique public code before any receipt exists",
              request.public_code.startswith("DP-"), request.public_code)

        scan = ocr.cross_check(receipt_scan(5000), requested_dirams=5000,
                               expected_recipient="DASTYOR LLC")
        duplicate = await service.attach_receipt(
            request.id, file_id="f1", mime="image/jpeg", size_bytes=2048, scan=scan)
        check("no duplicate on a first receipt", duplicate is None, str(duplicate))

        pending = await service.get_request(request.id)
        check("request moves to pending after a receipt",
              pending.status == service.STATUS_PENDING, pending.status)
        check("balance unchanged while pending", await balance_of(uid) == 1000)

        result = await service.approve_payment(request.id, 5001)
        check("approval applies", result.outcome == "applied", result.outcome)
        check("credited amount is the reviewed amount",
              result.credited_dirams == 5000, str(result.credited_dirams))
        check("balance went 1000 -> 6000", await balance_of(uid) == 6000,
              str(await balance_of(uid)))
        check("returned new balance matches the database",
              result.new_balance_dirams == 6000, str(result.new_balance_dirams))

        rows = await ledger_rows(uid)
        topups = [r for r in rows if r[0] == "topup"]
        check("exactly one topup ledger row", len(topups) == 1, str(len(topups)))
        check("ledger row records before/after correctly",
              topups[0][1] == 5000 and topups[0][2] == 1000 and topups[0][3] == 6000,
              str(topups[0]))
        check("ledger reason names the request and the acting admin",
              request.public_code in topups[0][4] and "5001" in topups[0][4],
              topups[0][4])

        stored = await service.get_request(request.id)
        check("request records who decided it",
              stored.status == service.STATUS_APPROVED, stored.status)
        check("request links to its balance transaction",
              stored.credited_dirams == 5000)

        events = await audit_events(request.id)
        check("audit trail covers created, receipt, approval",
              events == ["created", "receipt_attached", "approved"], str(events))

        # Repeat approval: the second must not credit again.
        again = await service.approve_payment(request.id, 5001)
        check("a second approval is refused as already decided",
              again.outcome == "already_decided", again.outcome)
        check("balance is unchanged by the repeat approval",
              await balance_of(uid) == 6000, str(await balance_of(uid)))
        check("no second topup row was written",
              len([r for r in await ledger_rows(uid) if r[0] == "topup"]) == 1)
    finally:
        await cleanup_user(uid)


async def test_reject_and_more_info():
    section("Reject and request-more-info never touch the balance")

    chat_id = 900021
    uid = await _linked_user(chat_id, balance=2000)
    try:
        req = await service.create_payment_request(uid, chat_id, 3000)
        scan = ocr.cross_check(receipt_scan(3000, reference="TXN-REJ1"),
                               requested_dirams=3000)
        await service.attach_receipt(req.id, file_id="f2", mime="image/jpeg",
                                     size_bytes=100, scan=scan)

        rejected = await service.reject_payment(req.id, 5002)
        check("rejection applies", rejected.outcome == "applied", rejected.outcome)
        check("balance unchanged by rejection", await balance_of(uid) == 2000,
              str(await balance_of(uid)))
        check("no topup row exists after rejection",
              not [r for r in await ledger_rows(uid) if r[0] == "topup"])
        check("status recorded as rejected",
              (await service.get_request(req.id)).status == service.STATUS_REJECTED)
        check("the original receipt is preserved",
              (await service.get_request(req.id)).receipt_file_id == "f2")
        check("audit records the rejection",
              "rejected" in await audit_events(req.id))

        after = await service.approve_payment(req.id, 5001)
        check("a rejected request cannot later be approved",
              after.outcome == "already_decided", after.outcome)
        check("balance still unchanged", await balance_of(uid) == 2000)

        # more-info keeps the request decidable
        req2 = await service.create_payment_request(uid, chat_id, 4000)
        scan2 = ocr.cross_check(receipt_scan(4000, reference="TXN-INFO1"),
                                requested_dirams=4000)
        await service.attach_receipt(req2.id, file_id="f3", mime="image/jpeg",
                                      size_bytes=100, scan=scan2)
        more = await service.request_more_info(req2.id, 5001)
        check("more-info applies", more.outcome == "applied", more.outcome)
        check("balance unchanged by more-info", await balance_of(uid) == 2000)
        check("status is needs_info",
              (await service.get_request(req2.id)).status == service.STATUS_NEEDS_INFO)

        later = await service.approve_payment(req2.id, 5001)
        check("a needs_info request can still be approved afterwards",
              later.outcome == "applied", later.outcome)
        check("balance credited after the follow-up approval",
              await balance_of(uid) == 6000, str(await balance_of(uid)))
        check("audit shows more_info then approval",
              await audit_events(req2.id) ==
              ["created", "receipt_attached", "more_info_requested", "approved"],
              str(await audit_events(req2.id)))
    finally:
        await cleanup_user(uid)


async def test_concurrent_approval():
    section("Concurrent approvals and duplicate callbacks")

    chat_id = 900022
    uid = await _linked_user(chat_id, balance=0)
    try:
        req = await service.create_payment_request(uid, chat_id, 7000)
        scan = ocr.cross_check(receipt_scan(7000, reference="TXN-RACE1"),
                               requested_dirams=7000)
        await service.attach_receipt(req.id, file_id="f4", mime="image/jpeg",
                                      size_bytes=100, scan=scan)

        # Two admins tapping at the same instant, on two connections.
        results = await asyncio.gather(
            service.approve_payment(req.id, 5001),
            service.approve_payment(req.id, 5002),
        )
        outcomes = sorted(r.outcome for r in results)
        check("exactly one concurrent approval applies",
              outcomes == ["already_decided", "applied"], str(outcomes))
        check("balance credited exactly once under the race",
              await balance_of(uid) == 7000, str(await balance_of(uid)))
        check("exactly one topup ledger row under the race",
              len([r for r in await ledger_rows(uid) if r[0] == "topup"]) == 1)

        # Five simultaneous taps on an already-approved request.
        repeats = await asyncio.gather(*[
            service.approve_payment(req.id, 5001) for _ in range(5)
        ])
        check("every repeat is refused",
              all(r.outcome == "already_decided" for r in repeats),
              str([r.outcome for r in repeats]))
        check("balance still 7000 after five repeat taps",
              await balance_of(uid) == 7000, str(await balance_of(uid)))

        # Update de-duplication (the first line of defence for a
        # redelivered callback).
        update_id = 77000001
        first = await service.claim_update("user", update_id)
        second = await service.claim_update("user", update_id)
        check("an update id is claimable once", first is True and second is False,
              f"{first}/{second}")
        concurrent = await asyncio.gather(*[
            service.claim_update("user", 77000002) for _ in range(4)
        ])
        check("concurrent claims of one update yield exactly one winner",
              sum(1 for c in concurrent if c) == 1, str(concurrent))

        # The two bots allocate update ids independently, so the SAME id
        # from the admin bot must still be claimable. Keying on update_id
        # alone would make the admin bot's update 77000001 look like a
        # replay of the user bot's and drop the approval it carried.
        admin_first = await service.claim_update("admin", update_id)
        admin_second = await service.claim_update("admin", update_id)
        check("the same update id from the OTHER bot is claimable",
              admin_first is True, str(admin_first))
        check("but only once per bot", admin_second is False, str(admin_second))

        # Offsets are per-bot for the same reason.
        await service.set_poll_offset("user", 111)
        await service.set_poll_offset("admin", 222)
        check("per-bot poll offsets do not overwrite each other",
              await service.get_poll_offset("user") == 111
              and await service.get_poll_offset("admin") == 222,
              f"{await service.get_poll_offset('user')}/"
              f"{await service.get_poll_offset('admin')}")

        # Regression: prune_processed_updates() used to build its interval
        # by string concatenation, which made asyncpg infer the bind
        # parameter as text and reject the int it is given. The error was
        # caught and logged as a warning at bot startup, so the prune
        # silently never ran and the dedupe table grew without bound.
        # This asserts it actually executes.
        try:
            removed = await service.prune_processed_updates()
            pruned_ok = isinstance(removed, int)
            detail = f"returned {removed}"
        except Exception as e:
            pruned_ok = False
            detail = f"{type(e).__name__}: {e}"
        check("prune_processed_updates runs instead of raising a DataError",
              pruned_ok, detail)

        # An old row must actually be deleted, and a fresh one kept.
        async with async_session() as db:
            await db.execute(text(
                "INSERT INTO telegram_processed_updates "
                "  (bot, update_id, processed_at) "
                "VALUES ('user', 77000003, now() - interval '400 days') "
                "ON CONFLICT (bot, update_id) DO UPDATE "
                "SET processed_at = now() - interval '400 days'"))
            await db.commit()
        await service.prune_processed_updates()
        async with async_session() as db:
            stale = (await db.execute(text(
                "SELECT 1 FROM telegram_processed_updates WHERE update_id = 77000003"
            ))).scalar()
            fresh = (await db.execute(text(
                "SELECT 1 FROM telegram_processed_updates WHERE update_id = 77000002"
            ))).scalar()
        check("prune deletes an expired update id", stale is None)
        check("prune keeps a recent update id", fresh is not None)
    finally:
        await cleanup_user(uid)
        async with async_session() as db:
            await db.execute(text(
                "DELETE FROM telegram_processed_updates WHERE update_id IN "
                "(77000001, 77000002, 77000003)"))
            await db.execute(text(
                "DELETE FROM telegram_bot_state WHERE key LIKE 'poll_offset%'"))
            await db.commit()


async def test_duplicate_reference():
    section("Duplicate transaction references")

    chat_a, chat_b = 900030, 900031
    uid_a = await _linked_user(chat_a, balance=0)
    uid_b = await _linked_user(chat_b, balance=0)
    try:
        ref = "TXN-DUP-55512345"

        req_a = await service.create_payment_request(uid_a, chat_a, 5000)
        scan_a = ocr.cross_check(receipt_scan(5000, reference=ref),
                                 requested_dirams=5000)
        await service.attach_receipt(req_a.id, file_id="d1", mime="image/jpeg",
                                      size_bytes=100, scan=scan_a)
        approved = await service.approve_payment(req_a.id, 5001)
        check("the first use of a reference is approved",
              approved.outcome == "applied", approved.outcome)

        # A second user submits a receipt with the same bank reference.
        req_b = await service.create_payment_request(uid_b, chat_b, 5000)
        scan_b = ocr.cross_check(receipt_scan(5000, reference=ref),
                                 requested_dirams=5000)
        duplicate_of = await service.attach_receipt(
            req_b.id, file_id="d2", mime="image/jpeg", size_bytes=100, scan=scan_b)
        check("the duplicate is detected and reported to the admin",
              duplicate_of == req_a.public_code, str(duplicate_of))

        stored = await service.get_request(req_b.id)
        check("the duplicate warning is persisted with the request",
              "reference_duplicate" in stored.ocr_warnings, str(stored.ocr_warnings))

        # The partial unique index must stop a second credit for the same
        # bank reference even if an admin taps approve anyway.
        second = await service.approve_payment(req_b.id, 5001)
        check("approving a duplicate reference is refused by the database",
              second.outcome == "duplicate_reference", second.outcome)
        check("the duplicate credits nothing", await balance_of(uid_b) == 0,
              str(await balance_of(uid_b)))
        check("no ledger row for the refused duplicate",
              not [r for r in await ledger_rows(uid_b) if r[0] == "topup"])
        check("the refused request stays decidable rather than silently approved",
              (await service.get_request(req_b.id)).status
              in (service.STATUS_PENDING, service.STATUS_NEEDS_INFO),
              (await service.get_request(req_b.id)).status)

        # A receipt with no readable reference must still be approvable:
        # the index is partial on NOT NULL for exactly this reason.
        req_c = await service.create_payment_request(uid_b, chat_b, 1000)
        blank = ocr.cross_check(ocr.ReceiptScan(engine="unavailable"),
                                requested_dirams=1000)
        await service.attach_receipt(req_c.id, file_id="d3", mime="image/jpeg",
                                      size_bytes=100, scan=blank)
        ok = await service.approve_payment(req_c.id, 5001)
        check("a receipt with no reference can still be approved by a human",
              ok.outcome == "applied", ok.outcome)
        check("that approval credits normally", await balance_of(uid_b) == 1000,
              str(await balance_of(uid_b)))
    finally:
        await cleanup_user(uid_a)
        await cleanup_user(uid_b)


async def test_amount_mismatch_is_flagged_not_blocked():
    section("OCR amount mismatch is surfaced, not silently acted on")

    chat_id = 900040
    uid = await _linked_user(chat_id, balance=0)
    try:
        req = await service.create_payment_request(uid, chat_id, 10000)
        # Receipt says 50.00, the teacher asked for 100.00.
        scan = ocr.cross_check(receipt_scan(5000, reference="TXN-MISM1"),
                               requested_dirams=10000,
                               expected_recipient="DASTYOR LLC")
        await service.attach_receipt(req.id, file_id="m1", mime="image/jpeg",
                                      size_bytes=100, scan=scan)

        stored = await service.get_request(req.id)
        check("mismatch warning is stored for the admin",
              "amount_mismatch" in stored.ocr_warnings, str(stored.ocr_warnings))
        check("the request is still pending, not auto-rejected",
              stored.status == service.STATUS_PENDING, stored.status)
        check("nothing was credited on the strength of OCR alone",
              await balance_of(uid) == 0)

        # A one-tap approval credits the REVIEWED amount, never the OCR one.
        result = await service.approve_payment(req.id, 5001)
        check("one-tap approval credits the requested amount, not the OCR amount",
              result.credited_dirams == 10000, str(result.credited_dirams))
        check("balance reflects the reviewed amount", await balance_of(uid) == 10000)
    finally:
        await cleanup_user(uid)


async def test_amount_correction_requires_reason():
    section("Amount correction is audited and cannot be done silently")

    chat_id = 900041
    uid = await _linked_user(chat_id, balance=0)
    try:
        req = await service.create_payment_request(uid, chat_id, 10000)
        scan = ocr.cross_check(receipt_scan(5000, reference="TXN-CORR1"),
                               requested_dirams=10000)
        await service.attach_receipt(req.id, file_id="c1", mime="image/jpeg",
                                      size_bytes=100, scan=scan)

        no_reason = await service.approve_payment(
            req.id, 5001, amount_override_dirams=5000)
        check("an override without a reason is refused",
              no_reason.outcome == "amount_conflict", no_reason.outcome)
        check("the refused override credits nothing", await balance_of(uid) == 0)
        check("the request is untouched by the refused override",
              (await service.get_request(req.id)).status == service.STATUS_PENDING)

        negative = await service.approve_payment(
            req.id, 5001, amount_override_dirams=-100,
            correction_reason="trying to steal")
        check("a negative override is refused",
              negative.outcome == "amount_conflict", negative.outcome)
        check("balance cannot be driven negative", await balance_of(uid) == 0)

        corrected = await service.approve_payment(
            req.id, 5001, amount_override_dirams=5000,
            correction_reason="receipt shows 50.00, teacher typed 100.00")
        check("an override with a reason applies", corrected.outcome == "applied",
              corrected.outcome)
        check("the corrected amount is credited, not the requested one",
              await balance_of(uid) == 5000, str(await balance_of(uid)))

        events = await audit_events(req.id)
        check("the correction is audited as its own event",
              "approved_with_correction" in events, str(events))

        async with async_session() as db:
            detail = (await db.execute(
                text("SELECT detail FROM payment_audit_log "
                     "WHERE payment_request_id = :id AND event = "
                     "'approved_with_correction'"),
                {"id": req.id},
            )).scalar()
        check("the audit detail records the reason and both amounts",
              "teacher typed" in detail and "5000" in detail and "10000" in detail,
              detail[:120])
    finally:
        await cleanup_user(uid)


async def test_rollback_on_missing_user():
    section("Rollback: an approval that cannot credit applies nothing")

    chat_id = 900050
    uid = await _linked_user(chat_id, balance=0)
    request_id = None
    try:
        req = await service.create_payment_request(uid, chat_id, 9000)
        request_id = req.id
        scan = ocr.cross_check(receipt_scan(9000, reference="TXN-GONE1"),
                               requested_dirams=9000)
        await service.attach_receipt(req.id, file_id="g1", mime="image/jpeg",
                                      size_bytes=100, scan=scan)

        # Delete the user behind the request, but keep the request row, so
        # the status CAS succeeds and the credit cannot.
        async with async_session() as db:
            await db.execute(text(
                "ALTER TABLE payment_requests DROP CONSTRAINT IF EXISTS "
                "payment_requests_user_id_fkey"))
            await db.execute(text("DELETE FROM balance_transactions "
                                  "WHERE user_id = :u"), {"u": uid})
            await db.execute(text("DELETE FROM telegram_accounts "
                                  "WHERE user_id = :u"), {"u": uid})
            await db.execute(text("DELETE FROM telegram_link_tokens "
                                  "WHERE user_id = :u"), {"u": uid})
            await db.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})
            await db.commit()

        result = await service.approve_payment(req.id, 5001)
        check("an approval that cannot credit reports not_found",
              result.outcome == "not_found", result.outcome)

        after = await service.get_request(req.id)
        check("the status change was rolled back with the credit",
              after.status == service.STATUS_PENDING, after.status)
        check("no credited amount was recorded", after.credited_dirams == 0,
              str(after.credited_dirams))
        check("no approval audit row survives the rollback",
              "approved" not in await audit_events(req.id),
              str(await audit_events(req.id)))
    finally:
        async with async_session() as db:
            if request_id:
                await db.execute(text("DELETE FROM payment_audit_log "
                                      "WHERE payment_request_id = :id"),
                                 {"id": request_id})
                await db.execute(text("DELETE FROM payment_requests WHERE id = :id"),
                                 {"id": request_id})
            # Put the foreign key back explicitly. init_db() will NOT do
            # it: create_all only creates missing tables and never adds a
            # constraint back to a table that already exists, so relying
            # on it would silently leave the test database off-schema for
            # every later run.
            await db.execute(text(
                "ALTER TABLE payment_requests "
                "ADD CONSTRAINT payment_requests_user_id_fkey "
                "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"))
            await db.commit()


# ---------------------------------------------------------------------
# Bot-level behaviour
# ---------------------------------------------------------------------

async def test_unauthorized_admin_actions():
    section("Unauthorized admin actions")

    chat_id = 900060
    uid = await _linked_user(chat_id, balance=0)
    try:
        req = await service.create_payment_request(uid, chat_id, 4500)
        scan = ocr.cross_check(receipt_scan(4500, reference="TXN-AUTH1"),
                               requested_dirams=4500)
        await service.attach_receipt(req.id, file_id="a1", mime="image/jpeg",
                                      size_bytes=100, scan=scan)

        fake = FakeTelegram()
        bot = PaymentBot(client=fake)

        for intruder in (999999, 0, None, 5003):
            await bot.handle_callback({
                "id": "cb-intruder",
                "data": f"pay:ok:{req.id}",
                "from": {"id": intruder} if intruder is not None else {},
            })
            check(f"telegram id {intruder} cannot approve",
                  await balance_of(uid) == 0, str(await balance_of(uid)))

        check("the request is still pending after every intruder tap",
              (await service.get_request(req.id)).status == service.STATUS_PENDING)
        check("no approval audit row from an unauthorized tap",
              "approved" not in await audit_events(req.id),
              str(await audit_events(req.id)))
        check("the intruder is told the action is admin-only",
              any("только администраторам" in (a["text"] or "")
                  for a in fake.answers), str(fake.answers[:2]))

        # The teacher who owns the request must not be able to approve it.
        await bot.handle_callback({
            "id": "cb-self", "data": f"pay:ok:{req.id}", "from": {"id": chat_id},
        })
        check("the requesting teacher cannot approve their own payment",
              await balance_of(uid) == 0, str(await balance_of(uid)))

        for action in ("pay:no", "pay:more"):
            await bot.handle_callback({
                "id": "cb-x", "data": f"{action}:{req.id}", "from": {"id": 424242},
            })
        check("unauthorized reject/more-info change nothing",
              (await service.get_request(req.id)).status == service.STATUS_PENDING)

        # And a genuine admin still works.
        await bot.handle_callback({
            "id": "cb-admin", "data": f"pay:ok:{req.id}", "from": {"id": 5001},
        })
        check("a configured admin CAN approve", await balance_of(uid) == 4500,
              str(await balance_of(uid)))
    finally:
        await cleanup_user(uid)


async def test_notification_failure_does_not_lose_the_credit():
    section("Notification delivery failure")

    chat_id = 900070
    uid = await _linked_user(chat_id, balance=1000)
    try:
        req = await service.create_payment_request(uid, chat_id, 2500)
        scan = ocr.cross_check(receipt_scan(2500, reference="TXN-NOTIF1"),
                               requested_dirams=2500)
        await service.attach_receipt(req.id, file_id="n1", mime="image/jpeg",
                                      size_bytes=100, scan=scan)

        # Every outbound send raises - the teacher has blocked the bot.
        broken = FakeTelegram(fail_sends=True)
        bot = PaymentBot(client=broken)

        await bot.handle_callback({
            "id": "cb-notify", "data": f"pay:ok:{req.id}", "from": {"id": 5001},
        })

        check("the credit still applied despite the failed notification",
              await balance_of(uid) == 3500, str(await balance_of(uid)))
        check("exactly one topup row despite the failure",
              len([r for r in await ledger_rows(uid) if r[0] == "topup"]) == 1)
        check("the request is recorded as approved",
              (await service.get_request(req.id)).status == service.STATUS_APPROVED)
        check("the audit row exists even though the message did not send",
              "approved" in await audit_events(req.id))

        # A retried tap after a failed notification must not re-credit.
        await bot.handle_callback({
            "id": "cb-notify-2", "data": f"pay:ok:{req.id}", "from": {"id": 5001},
        })
        check("re-tapping after a failed notification does not re-credit",
              await balance_of(uid) == 3500, str(await balance_of(uid)))

        # Admin notification failure must not lose the request either.
        req2 = await service.create_payment_request(uid, chat_id, 1500)
        scan2 = ocr.cross_check(receipt_scan(1500, reference="TXN-NOTIF2"),
                                requested_dirams=1500)
        await service.attach_receipt(req2.id, file_id="n2", mime="image/jpeg",
                                      size_bytes=100, scan=scan2)
        account = await service.account_for_chat(chat_id)
        await bot.notify_admins(req2, account, scan2, None, "n2", "image/jpeg")
        check("a request whose admin notification failed is still pending in the db",
              (await service.get_request(req2.id)).status == service.STATUS_PENDING)
        check("so a restart can still surface it for review",
              req2.id in [r.id for r in await service.list_requests(uid)])
    finally:
        await cleanup_user(uid)


async def test_bot_commands_and_receipt_flow():
    section("Bot commands and the receipt upload path")

    chat_id = 900080
    uid = await _linked_user(chat_id, balance=1234)
    try:
        fake = FakeTelegram()
        bot = PaymentBot(client=fake)

        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "/balance"})
        check("/balance reports the stored balance",
              "12,34" in fake.all_text(), fake.all_text()[-120:])

        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "/help"})
        check("/help explains that an admin must see the money arrive",
              "администратор своими глазами увидел поступление" in fake.all_text(),
              fake.all_text()[:80])

        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "/pay"})
        check("/pay asks for an amount",
              "Сколько вы переводите" in fake.all_text(),
              fake.all_text()[-120:])

        # A receipt with no open request is refused.
        await bot.handle_message({
            "chat": {"id": chat_id, "type": "private"}, "from": {"id": chat_id},
            "photo": [{"file_id": "p0", "file_size": 500}],
        })
        check("a receipt with no open request is refused",
              "Сначала выберите сумму" in fake.all_text(),
              fake.all_text()[-120:])

        # Typed amount opens a request.
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "30"})
        open_req = await service.open_request_for_user(uid)
        check("a typed amount opens a request for 30,00 somoni",
              open_req is not None and open_req.requested_dirams == 3000,
              str(open_req.requested_dirams if open_req else None))
        check("the instructions message carries the request code",
              open_req.public_code in fake.all_text())
        check("the owner-configured instructions are shown verbatim",
              "TEST ONLY - no real account details." in fake.all_text())

        # An unsupported upload is rejected with a helpful message.
        await bot.handle_message({
            "chat": {"id": chat_id, "type": "private"}, "from": {"id": chat_id},
            "document": {"file_id": "bad", "mime_type": "application/zip",
                         "file_size": 100},
        })
        check("an unsupported file type is rejected",
              "Не могу прочитать этот тип файла" in fake.all_text(),
              fake.all_text()[-100:])
        check("the rejected upload did not change the request status",
              (await service.get_request(open_req.id)).status
              == service.STATUS_AWAITING_RECEIPT)

        # An oversized upload is rejected.
        await bot.handle_message({
            "chat": {"id": chat_id, "type": "private"}, "from": {"id": chat_id},
            "document": {"file_id": "big", "mime_type": "image/png",
                         "file_size": 99 * 1024 * 1024},
        })
        check("an oversized upload is rejected",
              "Файл слишком большой" in fake.all_text(), fake.all_text()[-100:])

        # A real photo upload goes through. tesseract is absent here, so
        # this also exercises the degraded OCR path end to end.
        await bot.handle_message({
            "chat": {"id": chat_id, "type": "private"}, "from": {"id": chat_id},
            "photo": [{"file_id": "p1", "file_size": 2048}],
        })
        after = await service.get_request(open_req.id)
        check("a valid photo moves the request to pending",
              after.status == service.STATUS_PENDING, after.status)
        check("the receipt file id is recorded", after.receipt_file_id == "p1")
        check("the admins were notified with review buttons",
              len(fake.photos) == 2, str(len(fake.photos)))

        caption = fake.photos[0][1]
        # Short by design (product feedback): the full OCR dump - request
        # code, Dastyor uuid, Telegram id, the disclaimer paragraph - no
        # longer prints in the caption itself. None of that was ever
        # load-bearing: approve/reject read request_id from the button's
        # own callback_data, never from this text.
        check("the admin caption carries the account's short id",
              "#" in caption, caption[:60])
        check("the admin caption carries the requested amount",
              "30,00" in caption, caption[:200])
        check("the admin caption contains no email or phone",
              "@" not in caption and "+992" not in caption, caption[:80])
        check("the admin caption contains no Dastyor user uuid",
              uid not in caption, caption[:200])

        # /status lists it.
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "/status"})
        check("/status lists the pending request",
              open_req.public_code in fake.all_text()
              and "проверяется" in fake.all_text(),
              fake.all_text()[-160:])

        # Group chats are ignored.
        before = len(fake.messages)
        await bot.handle_message({"chat": {"id": -100123, "type": "supergroup"},
                                  "from": {"id": chat_id}, "text": "/balance"})
        check("a group chat gets no reply", len(fake.messages) == before)
    finally:
        await cleanup_user(uid)


async def test_empty_photo_is_not_treated_as_a_receipt():
    section("A photo with no text at all is not forwarded as a receipt")

    import app.telegram.bot as bot_module
    from app.telegram.ocr import ReceiptScan

    chat_id = 900095
    uid = await _linked_user(chat_id, balance=0)
    try:
        fake = FakeTelegram()
        bot = PaymentBot(client=fake)

        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "/pay"})
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "20"})
        open_req = await service.open_request_for_user(uid)
        check("a typed amount opens a request", open_req is not None)

        # Simulate what a real environment's tesseract reports for a photo
        # with no legible characters in it at all (a selfie, a screenshot
        # of something unrelated) — OCR ran to completion and found
        # nothing, as opposed to the test harness's usual "tesseract is not
        # installed here" degraded path exercised elsewhere in this file.
        def fake_scan_receipt(data, mime):
            scan = ReceiptScan(engine="tesseract:eng")
            scan.add_warning("no_text")
            return scan

        original_scan_receipt = bot_module.scan_receipt
        bot_module.scan_receipt = fake_scan_receipt
        try:
            await bot.handle_message({
                "chat": {"id": chat_id, "type": "private"}, "from": {"id": chat_id},
                "photo": [{"file_id": "empty1", "file_size": 2048}],
            })
        finally:
            bot_module.scan_receipt = original_scan_receipt

        check("the teacher is told it does not look like a receipt",
              "не похоже на" in fake.all_text(), fake.all_text()[-160:])
        check("no admin notification was sent for it",
              len(fake.photos) == 0, str(len(fake.photos)))

        after = await service.get_request(open_req.id)
        check("the request is still open, not attached or decided",
              after.status == service.STATUS_AWAITING_RECEIPT, after.status)
        check("nothing was recorded as the receipt file",
              after.receipt_file_id is None, after.receipt_file_id)

        # A genuine follow-up photo (tesseract unavailable in this test
        # environment, same degraded path as test_bot_commands_and_receipt_flow)
        # still reaches the admin as before — this guard only narrows the
        # one specific "found literally nothing" case, nothing else.
        await bot.handle_message({
            "chat": {"id": chat_id, "type": "private"}, "from": {"id": chat_id},
            "photo": [{"file_id": "real1", "file_size": 2048}],
        })
        after2 = await service.get_request(open_req.id)
        check("a genuine follow-up photo still reaches the admin",
              after2.status == service.STATUS_PENDING, after2.status)
        check("and the admin was notified about it (not the empty one)",
              len(fake.photos) > 0, str(len(fake.photos)))
    finally:
        await cleanup_user(uid)


async def test_unlinked_chat_is_guided():
    section("An unlinked chat is told how to link securely")

    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    chat_id = 900090

    await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                              "from": {"id": chat_id}, "text": "/start"})
    body = fake.all_text()
    # The greeting now points at a BUTTON rather than at the app: a
    # teacher who has never used a bot has nothing to type.
    check("an unlinked /start points at the sign-in button",
          "Войти" in body, body[:120])
    check("it says what will be asked, so nothing is a surprise",
          "номер телефона" in body and "пароль" in body, body[:160])
    # But it must not turn the greeting itself into a password prompt —
    # credentials belong inside the /login flow, after the warning.
    check("the greeting does not ask for the password right there",
          "пришлите пароль" not in body.lower(), body[:160])

    for command in ("/balance", "/pay", "/status"):
        fake.messages.clear()
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": command})
        check(f"{command} on an unlinked chat refuses and points at the app",
              "не привязан" in fake.all_text(), fake.all_text()[:80])

    fake.messages.clear()
    await bot.cmd_start(chat_id, chat_id, "not-a-real-token-but-long-enough-xx")
    check("an invalid linking token gets the invalid-token message",
          "недействительна" in fake.all_text(), fake.all_text()[:80])


# ---------------------------------------------------------------------
# Integration with the existing balance / generation system
# ---------------------------------------------------------------------

async def test_generation_integration():
    section("Balance and material-generation integration")

    chat_id = 900100
    uid = await _linked_user(chat_id, balance=0)
    try:
        price = limits.GENERATION_PRICE_DIRAMS
        check("the bot reuses the existing generation price, not its own",
              service.generation_price_dirams() == price, str(price))

        # No balance, free slots already spent by make_user: generation
        # must be refused by the backend.
        try:
            await limits.reserve(uid, ["konspekt"])
            refused = False
        except limits.InsufficientBalance:
            refused = True
        check("generation is refused on a zero balance", refused)

        # Top up through the real approval path.
        req = await service.create_payment_request(uid, chat_id, price * 3)
        scan = ocr.cross_check(receipt_scan(price * 3, reference="TXN-GEN1"),
                               requested_dirams=price * 3)
        await service.attach_receipt(req.id, file_id="gen1", mime="image/jpeg",
                                      size_bytes=100, scan=scan)
        await service.approve_payment(req.id, 5001)
        check("balance covers three generations after approval",
              await balance_of(uid) == price * 3, str(await balance_of(uid)))

        charge = await limits.reserve(uid, ["konspekt"])
        check("generation now succeeds", bool(charge))
        check("it charged the existing price", charge.dirams == price,
              str(charge.dirams))
        check("balance decreased by exactly the price",
              await balance_of(uid) == price * 2, str(await balance_of(uid)))

        # The ledger must show the top-up and the charge in one history.
        kinds = [r[0] for r in await ledger_rows(uid)]
        check("the top-up and the charge share the existing ledger",
              "topup" in kinds and "charge" in kinds, str(kinds))

        # Spend the rest, then confirm the backend refuses again.
        await limits.reserve(uid, ["konspekt", "konspekt"])
        check("balance is now zero", await balance_of(uid) == 0,
              str(await balance_of(uid)))
        try:
            await limits.reserve(uid, ["konspekt"])
            refused_again = False
        except limits.InsufficientBalance:
            refused_again = True
        check("generation is refused again once the credit is spent", refused_again)

        quote = await limits.quote(uid, 1, ["konspekt"])
        check("the existing quote endpoint sees the same balance",
              quote["balance_dirams"] == 0 and quote["affordable"] is False,
              str(quote))
    finally:
        await cleanup_user(uid)


async def test_separate_admin_bot():
    section("Separate admin bot")

    chat_id = 900120
    uid = await _linked_user(chat_id, balance=0)
    try:
        user_bot = FakeTelegram()
        admin_bot = FakeTelegram()
        bot = PaymentBot(client=user_bot, admin_client=admin_bot)
        check("the two clients are recognised as separate bots",
              bot.separate_admin_bot is True)
        check("admin language defaults to Russian", bot.admin_lang == "ru",
              bot.admin_lang)

        req = await service.create_payment_request(uid, chat_id, 6000)
        scan = ocr.cross_check(receipt_scan(6000, reference="TXN-SPLIT1"),
                               requested_dirams=6000,
                               expected_recipient="DASTYOR LLC")
        await service.attach_receipt(req.id, file_id="s1", mime="image/jpeg",
                                      size_bytes=100, scan=scan)
        account = await service.account_for_chat(chat_id)
        await bot.notify_admins(req, account, scan, None, "s1", "image/jpeg",
                                receipt_bytes=b"\xff\xd8\xff fake jpeg")

        # The review must land on the admin bot and nowhere else.
        check("the review went to the ADMIN bot",
              len(admin_bot.photos) == 2, str(len(admin_bot.photos)))
        check("the public bot sent no review at all",
              len(user_bot.photos) == 0 and len(user_bot.documents) == 0,
              f"{len(user_bot.photos)}/{len(user_bot.documents)}")
        check("no review text leaked into the public bot",
              "DP-" not in "".join(b for _, b in user_bot.messages),
              user_bot.all_text()[:60])

        caption = admin_bot.photos[0][1]
        check("the review caption is in Russian",
              "Новая оплата" in caption, caption[:50])
        check("it does not carry the request code (removed for brevity)",
              req.public_code not in caption)
        check("it does not carry the raw Telegram id (removed for brevity)",
              str(chat_id) not in caption)
        check("it contains no Tajik leftovers",
              "Дархости нави пардохт" not in caption
              and "худатон санҷед" not in caption)

        # Buttons are Russian too, and lead with the one-tap pair.
        keyboard = bot._review_keyboard(req.id)
        labels = [r[0]["text"] for r in keyboard["inline_keyboard"]]
        check("the buttons are Russian",
              "Подтвердить оплату" in labels[0]
              and "Отклонить оплату" in labels[1], str(labels))

        # A review callback arriving on the PUBLIC bot must be refused
        # even when it comes from a real admin: those buttons are never
        # sent there, so it can only be hand-crafted callback data.
        await bot.handle_callback(
            {"id": "cb-public", "data": f"pay:ok:{req.id}", "from": {"id": 5001}},
            from_admin_bot=False,
        )
        check("a review callback on the public bot credits nothing",
              await balance_of(uid) == 0, str(await balance_of(uid)))
        check("the request stays pending after the public-bot attempt",
              (await service.get_request(req.id)).status == service.STATUS_PENDING)

        # The same callback on the admin bot, from a non-admin, is refused.
        await bot.handle_callback(
            {"id": "cb-stranger", "data": f"pay:ok:{req.id}", "from": {"id": 777}},
            from_admin_bot=True,
        )
        check("a stranger on the admin bot credits nothing",
              await balance_of(uid) == 0, str(await balance_of(uid)))
        check("the stranger is answered in Russian",
              any("только администраторам" in (a["text"] or "")
                  for a in admin_bot.answers), str(admin_bot.answers[-1:]))

        # And a real admin on the admin bot works.
        await bot.handle_callback(
            {"id": "cb-ok", "data": f"pay:ok:{req.id}", "from": {"id": 5001}},
            from_admin_bot=True,
        )
        check("a configured admin on the admin bot credits the balance",
              await balance_of(uid) == 6000, str(await balance_of(uid)))
        check("the teacher's confirmation went to the PUBLIC bot",
              any("тасдиқ шуд" in body.lower() or "подтверждена" in body.lower()
                  for body in user_bot.texts_to(chat_id)),
              str(user_bot.texts_to(chat_id)[-1:]))

        # A non-admin messaging the admin bot is redirected, not served.
        admin_bot.messages.clear()
        await bot.handle_admin_update({
            "message": {"chat": {"id": 777, "type": "private"},
                        "from": {"id": 777}, "text": "/pay"},
        })
        check("a stranger messaging the admin bot is redirected to the app",
              "приложение Dastyor" in admin_bot.all_text(),
              admin_bot.all_text()[:80])
        check("the admin bot does not open a payment request for them",
              len(await service.list_requests(uid)) == 1)
    finally:
        await cleanup_user(uid)


async def test_single_bot_fallback():
    section("Fallback when no separate admin bot is configured")

    chat_id = 900130
    uid = await _linked_user(chat_id, balance=0)
    try:
        shared = FakeTelegram()
        bot = PaymentBot(client=shared)
        check("one client means no separate admin bot",
              bot.separate_admin_bot is False)
        check("the admin client IS the user client",
              bot.admin_client is bot.client)

        req = await service.create_payment_request(uid, chat_id, 2000)
        scan = ocr.cross_check(receipt_scan(2000, reference="TXN-FALL1"),
                               requested_dirams=2000)
        await service.attach_receipt(req.id, file_id="fb1", mime="image/jpeg",
                                      size_bytes=100, scan=scan)
        account = await service.account_for_chat(chat_id)
        await bot.notify_admins(req, account, scan, None, "fb1", "image/jpeg",
                                receipt_bytes=b"x")
        check("reviews still reach the admins through the one bot",
              len(shared.photos) == 2, str(len(shared.photos)))

        # With one bot the review callback legitimately arrives there.
        await bot.handle_callback(
            {"id": "cb", "data": f"pay:ok:{req.id}", "from": {"id": 5001}},
            from_admin_bot=False,
        )
        check("approval still works in single-bot mode",
              await balance_of(uid) == 2000, str(await balance_of(uid)))
    finally:
        await cleanup_user(uid)


async def test_admin_management():
    section("Granting and revoking admin from inside the bot")

    chat_id = 900140
    uid = await _linked_user(chat_id, balance=0)
    unlinked = await make_user()
    try:
        async with async_session() as db:
            short_id = (await db.execute(
                text("SELECT short_id FROM users WHERE id = :u"), {"u": uid}
            )).scalar()
            unlinked_short = (await db.execute(
                text("SELECT short_id FROM users WHERE id = :u"), {"u": unlinked}
            )).scalar()

        check("a fresh teacher is not an admin",
              not await service.is_admin(chat_id))
        check("the env root admin is an admin", await service.is_admin(5001))

        # Promote by Dastyor short id.
        result = await service.add_admin_by_short_id(short_id, 5001)
        check("an existing admin can grant admin", result.outcome == "added",
              result.outcome)
        check("the granted id is the account's LINKED telegram id",
              result.entry.telegram_user_id == chat_id,
              str(result.entry.telegram_user_id))
        check("the promoted teacher is now an admin",
              await service.is_admin(chat_id))
        check("they appear in all_admin_ids, so reviews reach them too",
              chat_id in await service.all_admin_ids())

        # Idempotent.
        again = await service.add_admin_by_short_id(short_id, 5001)
        check("granting twice is reported, not duplicated",
              again.outcome == "already", again.outcome)

        listed = await service.list_admins()
        roots = [e for e in listed if e.is_root]
        granted = [e for e in listed if not e.is_root]
        check("the listing separates root from granted",
              len(roots) == 2 and len(granted) == 1,
              f"{len(roots)} root / {len(granted)} granted")
        check("the listing records who granted it",
              granted[0].added_by_telegram_id == 5001,
              str(granted[0].added_by_telegram_id))

        # The grant is in the same append-only audit log as payments.
        async with async_session() as db:
            events = (await db.execute(text(
                "SELECT event, actor_telegram_id FROM payment_audit_log "
                "WHERE payment_request_id = :s ORDER BY created_at"
            ), {"s": f"admin:{chat_id}"})).all()
        check("the grant is audited", ("admin_granted", 5001) in
              [(e[0], e[1]) for e in events], str(events))

        # ANY user can be granted, including one who has never opened
        # the bot. The grant sits pending and carries no power until the
        # account links and proves which Telegram account it is.
        pending = await service.add_admin_by_short_id(unlinked_short, 5001)
        check("an unlinked account CAN be granted, as pending",
              pending.outcome == "added_pending", pending.outcome)
        check("a pending grant has no telegram id",
              pending.entry.telegram_user_id is None)
        check("a pending grant authorizes nobody yet",
              await service.granted_admin_ids() == {chat_id},
              str(await service.granted_admin_ids()))

        listed_pending = [e for e in await service.list_admins() if e.pending]
        check("the pending grant is listed and marked pending",
              len(listed_pending) == 1
              and listed_pending[0].short_id == unlinked_short,
              str(listed_pending))

        # Linking activates it.
        issued = await service.issue_link_token(unlinked)
        redeem = await service.redeem_link_token(
            issued.deep_link.split("start=", 1)[1], 900141, 900141)
        check("linking activates the pending grant",
              redeem.became_admin is True, redeem.outcome)
        check("the newly linked account is now a real admin",
              await service.is_admin(900141))
        check("and would receive reviews",
              900141 in await service.all_admin_ids())
        check("activation is audited",
              "admin_activated" in
              [e[0] for e in await _audit_for(f"admin:{900141}")])

        # An ordinary teacher linking must NOT become an admin.
        plain = await make_user()
        plain_issued = await service.issue_link_token(plain)
        plain_redeem = await service.redeem_link_token(
            plain_issued.deep_link.split("start=", 1)[1], 900142, 900142)
        check("linking without a pending grant does NOT grant admin",
              plain_redeem.became_admin is False)
        check("and that teacher is not an admin",
              not await service.is_admin(900142))
        await cleanup_user(plain)

        check("an unknown short id is rejected",
              (await service.add_admin_by_short_id("000000", 5001)).outcome
              == "not_found")
        # A non-numeric argument is now read as a @username and resolved
        # against our own stored copies. Junk simply finds nobody — the
        # value is a bound parameter, never interpolated.
        for junk in ("../etc", "'; DROP TABLE users; --", "@", "   "):
            outcome = (await service.add_admin_by_short_id(junk, 5001)).outcome
            check(f"junk argument {junk!r} grants nobody",
                  outcome in ("username_unknown", "not_found"), outcome)
        async with async_session() as db:
            still_there = (await db.execute(
                text("SELECT count(*) FROM users"))).scalar()
        check("the users table is intact after the injection attempt",
              still_there >= 1, str(still_there))

        # A granted admin can approve SOMEBODY ELSE'S payment.
        other_chat = 900143
        other = await _linked_user(other_chat, balance=0)
        req = await service.create_payment_request(other, other_chat, 1500)
        scan = ocr.cross_check(receipt_scan(1500, reference="TXN-NEWADM"),
                               requested_dirams=1500)
        await service.attach_receipt(req.id, file_id="na1", mime="image/jpeg",
                                      size_bytes=100, scan=scan)
        fake = FakeTelegram()
        bot = PaymentBot(client=fake)
        await bot.handle_callback(
            {"id": "cb-new", "data": f"pay:ok:{req.id}", "from": {"id": chat_id}},
            from_admin_bot=True,
        )
        check("a granted admin can approve someone else's payment",
              await balance_of(other) == 1500, str(await balance_of(other)))

        # But NOT their own — promoting a teacher must not hand them an
        # unlimited self-top-up.
        own = await service.create_payment_request(uid, chat_id, 9900)
        own_scan = ocr.cross_check(receipt_scan(9900, reference="TXN-SELF1"),
                                   requested_dirams=9900)
        await service.attach_receipt(own.id, file_id="self1",
                                      mime="image/jpeg", size_bytes=100,
                                      scan=own_scan)
        refused = await service.approve_payment(own.id, chat_id)
        check("a granted admin CANNOT approve their own request",
              refused.outcome == "self_approval", refused.outcome)
        check("their own request credits nothing",
              await balance_of(uid) == 0, str(await balance_of(uid)))
        check("and it stays pending for somebody else to review",
              (await service.get_request(own.id)).status
              == service.STATUS_PENDING)

        # A ROOT admin may self-approve — a one-person operation has to
        # be able to credit itself — but it is audited as its own event.
        root_req = await service.create_payment_request(uid, chat_id, 700)
        root_scan = ocr.cross_check(receipt_scan(700, reference="TXN-SELF2"),
                                    requested_dirams=700)
        await service.attach_receipt(root_req.id, file_id="self2",
                                      mime="image/jpeg", size_bytes=100,
                                      scan=root_scan)
        async with async_session() as db:
            await db.execute(text(
                "UPDATE telegram_accounts SET chat_id = 5001 "
                "WHERE chat_id = :c"), {"c": chat_id})
            await db.execute(text(
                "UPDATE payment_requests SET chat_id = 5001 "
                "WHERE id = :i"), {"i": root_req.id})
            await db.commit()
        root_ok = await service.approve_payment(root_req.id, 5001)
        check("a ROOT admin may approve their own request",
              root_ok.outcome == "applied", root_ok.outcome)
        check("and it is audited as a self-approval",
              "approved_self" in await audit_events(root_req.id),
              str(await audit_events(root_req.id)))
        async with async_session() as db:
            reason = (await db.execute(text(
                "SELECT reason FROM balance_transactions "
                "WHERE user_id = :u AND kind = 'topup' "
                "ORDER BY created_at DESC LIMIT 1"), {"u": uid})).scalar()
            await db.execute(text(
                "UPDATE telegram_accounts SET chat_id = :c "
                "WHERE chat_id = 5001"), {"c": chat_id})
            await db.commit()
        check("the existing ledger marks it SELF-APPROVED too",
              "SELF-APPROVED" in (reason or ""), str(reason))
        await cleanup_user(other)

        # Revocation.
        removed = await service.remove_admin(short_id, 5001)
        check("a granted admin can be revoked", removed.outcome == "removed",
              removed.outcome)
        check("they are no longer an admin", not await service.is_admin(chat_id))
        check("the revoke is audited",
              "admin_revoked" in [e[0] for e in (await _audit_for(f"admin:{chat_id}"))])

        # A root admin cannot be revoked through the bot: otherwise one
        # compromised admin could lock the owner out.
        root = await service.remove_admin("5001", 5001)
        check("a root admin cannot be revoked via the bot",
              root.outcome == "is_root", root.outcome)
        check("the root admin still has access", await service.is_admin(5001))

        check("revoking somebody who is not an admin is reported",
              (await service.remove_admin(short_id, 5001)).outcome
              == "not_found")
    finally:
        async with async_session() as db:
            await db.execute(text(
                "DELETE FROM telegram_admins WHERE telegram_user_id = ANY(:t) "
                "   OR user_id = :u"),
                {"t": [chat_id, 900141, 900142], "u": unlinked})
            await db.execute(text(
                "DELETE FROM payment_audit_log WHERE payment_request_id = ANY(:s)"),
                {"s": [f"admin:{chat_id}", "admin:900141", "admin:900142",
                       "admin:None"]})
            await db.execute(text(
                "DELETE FROM telegram_accounts WHERE chat_id = ANY(:c)"),
                {"c": [900141, 900142]})
            await db.commit()
        await cleanup_user(uid)
        await cleanup_user(unlinked)


async def _audit_for(subject: str) -> list[tuple]:
    async with async_session() as db:
        return (await db.execute(text(
            "SELECT event, actor_telegram_id FROM payment_audit_log "
            "WHERE payment_request_id = :s ORDER BY created_at"
        ), {"s": subject})).all()


async def test_admin_commands_over_the_bot():
    section("Admin commands as a real admin would type them")

    chat_id = 900150
    uid = await _linked_user(chat_id, balance=0)
    try:
        async with async_session() as db:
            short_id = (await db.execute(
                text("SELECT short_id FROM users WHERE id = :u"), {"u": uid}
            )).scalar()

        fake = FakeTelegram()
        bot = PaymentBot(client=fake)

        # A non-admin typing an admin command on the public bot gets the
        # ordinary unknown-command reply, not a hint that it exists.
        await bot.handle_message({
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": chat_id}, "text": f"/addadmin {short_id}",
        })
        check("a non-admin cannot use /addadmin",
              not await service.is_admin(chat_id))
        check("and is not told the command exists",
              "admin" not in fake.all_text().lower(), fake.all_text()[-80:])

        # A real admin can.
        fake.messages.clear()
        await bot.handle_admin_command(5001, 5001, f"/addadmin {short_id}")
        check("an admin's /addadmin promotes the account",
              await service.is_admin(chat_id))
        check("the admin gets a Russian confirmation",
              "теперь администратор" in fake.all_text(), fake.all_text()[:90])
        check("the promoted user is told, in their own chat",
              any("права администратора" in body
                  for body in fake.texts_to(chat_id)),
              str(fake.texts_to(chat_id)[-1:]))
        check("the promotion notice repeats that a receipt is not proof",
              any("не является подтверждением" in body
                  for body in fake.texts_to(chat_id)))

        fake.messages.clear()
        await bot.handle_admin_command(5001, 5001, "/admins")
        listing = fake.all_text()
        check("/admins lists the new admin", f"#{short_id}" in listing,
              listing[:120])
        check("/admins marks the root admins",
              "основной" in listing, listing[:120])

        fake.messages.clear()
        await bot.handle_admin_command(5001, 5001, "/addadmin")
        usage = fake.all_text()
        check("/addadmin with no argument explains both forms",
              "@username" in usage and "123456" in usage, usage[:90])
        check("and warns that @username only finds people who wrote to the bot",
              "писал боту" in usage, usage[-120:])

        fake.messages.clear()
        await bot.handle_admin_command(5001, 5001, f"/deladmin {short_id}")
        check("/deladmin revokes", not await service.is_admin(chat_id))
        check("and confirms", "снят" in fake.all_text(), fake.all_text()[:60])
    finally:
        async with async_session() as db:
            await db.execute(text(
                "DELETE FROM telegram_admins WHERE telegram_user_id = :t"),
                {"t": chat_id})
            await db.execute(text(
                "DELETE FROM payment_audit_log WHERE payment_request_id = :s"),
                {"s": f"admin:{chat_id}"})
            await db.commit()
        await cleanup_user(uid)


async def test_add_admin_by_username():
    section("Granting admin by @username")

    chat_id = 900160
    uid = await make_user()
    try:
        # Link, carrying a username the way a real /start does.
        issued = await service.issue_link_token(uid)
        await service.redeem_link_token(
            issued.deep_link.split("start=", 1)[1], chat_id, chat_id,
            username="@MahkamjonTest",
        )

        async with async_session() as db:
            stored = (await db.execute(text(
                "SELECT username FROM telegram_accounts WHERE chat_id = :c"
            ), {"c": chat_id})).scalar()
        check("the username is stored lower-cased, without the @",
              stored == "mahkamjontest", repr(stored))

        # Case and the leading @ must not matter.
        for form in ("@MahkamjonTest", "mahkamjontest", "@MAHKAMJONTEST"):
            check(f"normalize_username({form!r}) folds to the stored form",
                  service.normalize_username(form) == "mahkamjontest",
                  service.normalize_username(form))

        result = await service.add_admin_by_short_id("@MahkamjonTest", 5001)
        check("an admin can be granted by @username",
              result.outcome == "added", result.outcome)
        check("the grant is keyed on the telegram id, not the name",
              result.entry.telegram_user_id == chat_id,
              str(result.entry.telegram_user_id))
        check("the confirmation echoes the real account, so a stale name "
              "is visible", result.entry.short_id is not None)
        check("they are a real admin now", await service.is_admin(chat_id))

        # Revoke by username too.
        removed = await service.remove_admin("@mahkamjontest", 5001)
        check("revoking by @username works", removed.outcome == "removed",
              removed.outcome)
        check("and they lose access", not await service.is_admin(chat_id))

        # An unknown username is reported distinctly, because the fix is
        # different: the person has to write to the bot first.
        unknown = await service.add_admin_by_short_id("@nobody_here", 5001)
        check("an unknown @username gets its own outcome",
              unknown.outcome == "username_unknown", unknown.outcome)

        # A username change is picked up the next time they write.
        await service.remember_username(chat_id, "@RenamedUser")
        async with async_session() as db:
            refreshed = (await db.execute(text(
                "SELECT username FROM telegram_accounts WHERE chat_id = :c"
            ), {"c": chat_id})).scalar()
        check("a renamed user's stored username is refreshed on their next "
              "message", refreshed == "renameduser", repr(refreshed))
        check("the old name no longer resolves",
              (await service.add_admin_by_short_id(
                  "@mahkamjontest", 5001)).outcome == "username_unknown")
        check("the new name does",
              (await service.add_admin_by_short_id(
                  "@RenamedUser", 5001)).outcome == "added")

        # Someone with no username at all must not match a blank query.
        await service.remember_username(chat_id, None)
        check("a blank username does not match an account with none set",
              (await service.add_admin_by_short_id("@", 5001)).outcome
              in ("username_unknown", "not_found"))
    finally:
        async with async_session() as db:
            await db.execute(text(
                "DELETE FROM telegram_admins WHERE telegram_user_id = :t"),
                {"t": chat_id})
            await db.execute(text(
                "DELETE FROM payment_audit_log WHERE payment_request_id = :s"),
                {"s": f"admin:{chat_id}"})
            await db.commit()
        await cleanup_user(uid)


async def test_pending_queue():
    section("/pending — the safety net under failed notifications")

    chat_id = 900170
    uid = await _linked_user(chat_id, balance=0)
    try:
        before = await service.count_pending_reviews()

        # A request whose admin notification fails completely. This is
        # the exact case the queue exists for: until /pending there was
        # nothing in Telegram pointing at this row.
        req = await service.create_payment_request(uid, chat_id, 2500)
        # Receipt says 10.00 but 25.00 was requested, so this one also
        # exercises the warning counter in the listing.
        scan = ocr.cross_check(receipt_scan(1000, reference="TXN-PEND1"),
                               requested_dirams=2500)
        await service.attach_receipt(req.id, file_id="pq1", mime="image/jpeg",
                                      size_bytes=100, scan=scan)

        broken = FakeTelegram(fail_sends=True)
        broken_bot = PaymentBot(client=broken)
        account = await service.account_for_chat(chat_id)
        await broken_bot.notify_admins(req, account, scan, None, "pq1",
                                       "image/jpeg", receipt_bytes=b"x")
        check("the notification really did fail",
              not broken.photos and not broken.messages,
              f"{len(broken.photos)}/{len(broken.messages)}")

        # The request is nonetheless reachable.
        pending = await service.list_pending_reviews()
        codes = [p.public_code for p in pending]
        check("the unreachable request IS in the pending queue",
              req.public_code in codes, str(codes))
        check("the count went up by one",
              await service.count_pending_reviews() == before + 1)

        entry = next(p for p in pending if p.public_code == req.public_code)
        check("it carries the account so the admin knows whose it is",
              entry.short_id is not None and entry.full_name)
        check("it carries the requested amount",
              entry.requested_dirams == 2500, str(entry.requested_dirams))
        check("it carries the OCR warnings so the queue can flag it",
              "amount_mismatch" in entry.ocr_warnings, str(entry.ocr_warnings))
        check("a fresh request reports an age under an hour",
              entry.age_hours() < 1, str(entry.age_hours()))

        # Oldest first: the teacher waiting longest is the one chased.
        second = await service.create_payment_request(uid, chat_id, 500)
        scan2 = ocr.cross_check(receipt_scan(500, reference="TXN-PEND2"),
                                requested_dirams=500)
        await service.attach_receipt(second.id, file_id="pq2",
                                      mime="image/jpeg", size_bytes=100,
                                      scan=scan2)
        ordered = [p.public_code for p in await service.list_pending_reviews()]
        check("the queue is oldest first",
              ordered.index(req.public_code) < ordered.index(second.public_code),
              str(ordered))

        # Now drive the command and confirm it is actionable.
        fake = FakeTelegram()
        bot = PaymentBot(client=fake)
        await bot.cmd_pending(5001)
        body = fake.all_text() + " ".join(c for _, c in fake.photos)
        check("/pending names the lost request", req.public_code in body,
              body[:120])
        check("/pending shows how long it has waited",
              "ждёт" in body, body[:120])

        # Each listed request is re-sent WITH its buttons, so the queue
        # is not merely visible but usable.
        resent = len(fake.photos) + max(0, len(fake.messages) - 1)
        check("every listed request is re-sent individually",
              resent >= 2, str(resent))

        # And approving from that list really works.
        await bot.handle_callback(
            {"id": "cb-pq", "data": f"pay:ok:{req.id}", "from": {"id": 5001}},
            from_admin_bot=True,
        )
        check("a request can be approved straight from /pending",
              await balance_of(uid) == 2500, str(await balance_of(uid)))
        check("and it leaves the queue once decided",
              req.public_code not in
              [p.public_code for p in await service.list_pending_reviews()])

        # A request still awaiting its receipt is NOT a review item.
        awaiting = await service.create_payment_request(uid, chat_id, 100)
        check("an awaiting-receipt request is not in the review queue",
              awaiting.public_code not in
              [p.public_code for p in await service.list_pending_reviews()])

        # Empty queue reads as success, not as an error.
        fake.messages.clear()
        await service.reject_payment(second.id, 5001)
        async with async_session() as db:
            await db.execute(text(
                "UPDATE payment_requests SET status = :c "
                "WHERE status IN (:p, :n) AND user_id <> :u"),
                {"c": service.STATUS_CANCELLED, "p": service.STATUS_PENDING,
                 "n": service.STATUS_NEEDS_INFO, "u": uid})
            await db.commit()
        await bot.cmd_pending(5001)
        check("an empty queue says so plainly",
              "Нерассмотренных заявок нет" in fake.all_text(),
              fake.all_text()[:80])
    finally:
        await cleanup_user(uid)


async def test_unlink():
    section("Unlinking a Telegram account")

    chat_id = 900180
    uid = await _linked_user(chat_id, balance=1200)
    try:
        check("linked to start with",
              await service.account_for_chat(chat_id) is not None)

        # The bot command asks before doing it: unlinking cannot be
        # undone from the chat, only from the app.
        fake = FakeTelegram()
        bot = PaymentBot(client=fake)
        await bot.cmd_unlink(chat_id, None)
        check("a bare /unlink only asks for confirmation",
              await service.account_for_chat(chat_id) is not None)
        # The test teacher's stored language is Tajik, but teacher-facing
        # output is pinned to Russian — answering in Russian regardless
        # of the account's language is itself the correct behaviour
        # under test now.
        check("and says what will happen, in Russian",
              "Отвязать аккаунт" in fake.all_text(), fake.all_text()[:60])

        await bot.cmd_unlink(chat_id, "нет")
        check("a wrong confirmation word does nothing",
              await service.account_for_chat(chat_id) is not None)
        await bot.cmd_unlink(chat_id, "ҳа ҳа ҳа")
        check("a near-miss confirmation does nothing either",
              await service.account_for_chat(chat_id) is not None)

        # An open request must survive — the teacher may have really
        # sent money, and dropping it would lose it.
        req = await service.create_payment_request(uid, chat_id, 600)
        scan = ocr.cross_check(receipt_scan(600, reference="TXN-UNL1"),
                               requested_dirams=600)
        await service.attach_receipt(req.id, file_id="ul1", mime="image/jpeg",
                                      size_bytes=100, scan=scan)

        fake.messages.clear()
        await bot.cmd_unlink(chat_id, "ҳа")
        check("confirmed /unlink disconnects the chat",
              await service.account_for_chat(chat_id) is None)
        check("the teacher is told how to reconnect",
              "Пополнить баланс через Telegram" in fake.all_text(),
              fake.all_text()[:90])
        check("and warned about the open request",
              "открытых заявок" in fake.all_text(), fake.all_text()[-140:])

        # Nothing about the money changed.
        check("the balance is untouched", await balance_of(uid) == 1200,
              str(await balance_of(uid)))
        check("the payment request still exists for the admin",
              (await service.get_request(req.id)).status
              == service.STATUS_PENDING)
        check("it is still in the admin's pending queue",
              req.public_code in
              [p.public_code for p in await service.list_pending_reviews()])
        check("the receipt is preserved",
              (await service.get_request(req.id)).receipt_file_id == "ul1")

        # An unlinked chat is a stranger again.
        fake.messages.clear()
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "/balance"})
        check("the unlinked chat can no longer see the balance",
              "1200" not in fake.all_text() and "12,00" not in fake.all_text(),
              fake.all_text()[:80])
        check("and is pointed back at the app",
              "пайваст нест" in fake.all_text()
              or "не привязан" in fake.all_text(), fake.all_text()[:80])

        fake.messages.clear()
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "/pay"})
        check("and cannot open a new payment request",
              await service.open_request_for_user(uid) is None
              or (await service.open_request_for_user(uid)).id == req.id)

        # A stale deep link must not silently restore the connection.
        stale = await service.issue_link_token(uid)
        await service.unlink_account(user_id=uid, actor="test")
        replay = await service.redeem_link_token(
            stale.deep_link.split("start=", 1)[1], chat_id, chat_id)
        check("a link token minted before the unlink is dead",
              replay.outcome == "used", replay.outcome)

        # Re-linking from the app works and is a clean slate.
        fresh = await service.issue_link_token(uid)
        again = await service.redeem_link_token(
            fresh.deep_link.split("start=", 1)[1], chat_id, chat_id)
        check("the teacher can link again afterwards",
              again.outcome == "linked", again.outcome)
        check("and sees the same balance", again.account.balance_dirams == 1200,
              str(again.account.balance_dirams))

        check("unlinking twice is reported, not an error",
              (await service.unlink_account(user_id=uid)).outcome == "unlinked"
              and (await service.unlink_account(user_id=uid)).outcome
              == "not_linked")
    finally:
        await cleanup_user(uid)


async def test_unlink_revokes_admin():
    section("Unlinking takes the admin grant with it")

    chat_id = 900190
    uid = await _linked_user(chat_id, balance=0)
    try:
        async with async_session() as db:
            short_id = (await db.execute(
                text("SELECT short_id FROM users WHERE id = :u"), {"u": uid}
            )).scalar()

        await service.add_admin_by_short_id(short_id, 5001)
        check("granted admin first", await service.is_admin(chat_id))

        result = await service.unlink_account(chat_id=chat_id, actor="teacher")
        check("unlink reports the admin grant was revoked too",
              result.admin_revoked is True, str(result.admin_revoked))
        check("they are no longer an admin", not await service.is_admin(chat_id))
        check("and would receive no more reviews",
              chat_id not in await service.all_admin_ids())

        # The grant rested on the link proving which Telegram account
        # belonged to the Dastyor user. Withdrawing the proof has to
        # withdraw the power, or a sold phone keeps approving payments.
        listed = [e.telegram_user_id for e in await service.list_admins()]
        check("and they are gone from the admin listing",
              chat_id not in listed, str(listed))
    finally:
        async with async_session() as db:
            await db.execute(text(
                "DELETE FROM telegram_admins WHERE telegram_user_id = :t "
                "   OR user_id = :u"), {"t": chat_id, "u": uid})
            await db.execute(text(
                "DELETE FROM payment_audit_log WHERE payment_request_id = :s"),
                {"s": f"admin:{chat_id}"})
            await db.commit()
        await cleanup_user(uid)


async def test_password_login():
    section("Linking by phone + password")

    from app.auth import hash_password

    chat_id = 900200
    phone = "+992900555001"
    password = "CorrectHorse2026!"
    uid = await make_user()
    try:
        async with async_session() as db:
            await db.execute(text(
                "UPDATE users SET phone = :p, phone_verified = TRUE, "
                "  hashed_password = :h WHERE id = :u"
            ), {"p": phone, "h": hash_password(password), "u": uid})
            await db.commit()

        # Phone normalisation: people type it the way they say it.
        for typed in (phone, "992900555001", "900555001", "+992 90 055 50 01",
                      "992-900-555-001"):
            check(f"normalize_phone({typed!r}) -> {phone}",
                  service.normalize_phone(typed) == phone,
                  str(service.normalize_phone(typed)))
        for junk in ("", "abc", "12345", "+1234567890123456"):
            check(f"normalize_phone({junk!r}) is rejected",
                  service.normalize_phone(junk) is None)

        # Wrong password must not link.
        bad = await service.link_by_password(phone, "wrong", chat_id, chat_id)
        check("a wrong password does not link",
              bad.outcome == "bad_credentials", bad.outcome)
        check("and no account is bound",
              await service.account_for_chat(chat_id) is None)

        # An unknown phone gives the SAME answer, so the bot cannot be
        # used to discover which numbers are registered.
        unknown = await service.link_by_password(
            "+992900555999", password, chat_id, chat_id)
        check("an unknown phone is indistinguishable from a wrong password",
              unknown.outcome == "bad_credentials", unknown.outcome)

        # Correct credentials link.
        ok = await service.link_by_password(phone, password, chat_id, chat_id,
                                            username="@LoginTester")
        check("correct phone + password links the chat",
              ok.outcome == "linked", ok.outcome)
        check("the right account is bound",
              ok.account is not None and ok.account.user_id == uid)
        check("the username is captured on the way in",
              (await _username_for(chat_id)) == "logintester",
              str(await _username_for(chat_id)))

        # Outstanding deep-link tokens are spent by a successful login.
        stale = await service.issue_link_token(uid)
        await service.link_by_password(phone, password, chat_id, chat_id)
        replay = await service.redeem_link_token(
            stale.deep_link.split("start=", 1)[1], chat_id, chat_id)
        check("a pending deep link is dead after a password login",
              replay.outcome == "used", replay.outcome)

        # The chat cannot be stolen for another account.
        other = await make_user()
        other_phone = "+992900555002"
        async with async_session() as db:
            await db.execute(text(
                "UPDATE users SET phone = :p, hashed_password = :h "
                "WHERE id = :u"
            ), {"p": other_phone, "h": hash_password(password), "u": other})
            await db.commit()
        taken = await service.link_by_password(
            other_phone, password, chat_id, chat_id)
        check("a chat already linked elsewhere is refused",
              taken.outcome == "chat_taken", taken.outcome)
        still = await service.account_for_chat(chat_id)
        check("the original account keeps the chat",
              still is not None and still.user_id == uid)
        await cleanup_user(other)

        # The password must not reach the database anywhere.
        async with async_session() as db:
            hit = (await db.execute(text(
                "SELECT count(*) FROM payment_audit_log WHERE detail LIKE :p"
            ), {"p": f"%{password}%"})).scalar()
        check("the password appears in no audit row", hit == 0, str(hit))
    finally:
        async with async_session() as db:
            await db.execute(text(
                "DELETE FROM rate_limit_attempts WHERE key = :k"),
                {"k": f"tg:{chat_id}"})
            await db.commit()
        await cleanup_user(uid)


async def _username_for(chat_id: int) -> str | None:
    async with async_session() as db:
        return (await db.execute(text(
            "SELECT username FROM telegram_accounts WHERE chat_id = :c"
        ), {"c": chat_id})).scalar()


async def test_password_login_over_the_bot():
    section("/login as a teacher would type it")

    from app.auth import hash_password

    chat_id = 900210
    phone = "+992900555010"
    password = "AnotherPass2026!"
    uid = await make_user()
    try:
        async with async_session() as db:
            await db.execute(text(
                "UPDATE users SET phone = :p, hashed_password = :h "
                "WHERE id = :u"
            ), {"p": phone, "h": hash_password(password), "u": uid})
            await db.commit()

        fake = FakeTelegram()
        bot = PaymentBot(client=fake)

        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "/login"})
        check("/login asks for the phone",
              "рақами телефон" in fake.all_text().lower()
              or "номер" in fake.all_text().lower(), fake.all_text()[:70])

        fake.messages.clear()
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "not a phone"})
        check("a bad phone is rejected without moving on",
              bot._state(chat_id).awaiting_login_phone is True)

        fake.messages.clear()
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": phone})
        check("a good phone moves to the password step",
              bot._state(chat_id).awaiting_login_password is True)
        warning = fake.all_text()
        check("the password prompt warns against other bots",
              "нафиристед" in warning or "не отправляйте" in warning
              or "Never send" in warning, warning[:120])
        check("and names this bot so the warning is actionable",
              "DastyorPayBot" in warning or "@" in warning, warning[-60:])

        fake.messages.clear()
        await bot.handle_message({
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": chat_id}, "text": password,
            "message_id": 4242,
        })
        check("the correct password links the account",
              await service.account_for_chat(chat_id) is not None)

        # The whole point of the two-step flow: the password message is
        # taken back out of the chat.
        check("the password message was deleted from the chat",
              (chat_id, 4242) in fake.deleted, str(fake.deleted))
        check("the password is never echoed back",
              password not in fake.all_text(), "password appeared in a reply")

        # And the phone is not left sitting in memory afterwards.
        check("the phone is cleared from conversation state",
              bot._state(chat_id).login_phone is None)
        check("the password step is closed",
              bot._state(chat_id).awaiting_login_password is False)
    finally:
        async with async_session() as db:
            await db.execute(text(
                "DELETE FROM rate_limit_attempts WHERE key = :k"),
                {"k": f"tg:{chat_id}"})
            await db.commit()
        await cleanup_user(uid)


async def test_password_login_throttle():
    section("/login attempts are throttled")

    chat_id = 900220
    uid = await _linked_user(900221, balance=0)
    try:
        fake = FakeTelegram()
        bot = PaymentBot(client=fake)

        # Six wrong attempts against a limit of five.
        outcomes = []
        for i in range(6):
            bot._state(chat_id).login_phone = "+992900555099"
            bot._state(chat_id).awaiting_login_password = True
            fake.messages.clear()
            await bot.handle_login_password(
                chat_id, f"guess{i}", 1000 + i, chat_id, None)
            outcomes.append(fake.all_text())

        check("the first five attempts are answered as bad credentials",
              all("нодуруст" in o or "Неверный" in o or "Wrong" in o
                  for o in outcomes[:5]), str(outcomes[0][:60]))
        check("the sixth is throttled, not answered",
              "зиёд" in outcomes[5] or "Слишком много" in outcomes[5]
              or "Too many" in outcomes[5], outcomes[5][:80])
        check("every password message was deleted, even the failures",
              len(fake.deleted) == 6, str(len(fake.deleted)))
    finally:
        async with async_session() as db:
            await db.execute(text(
                "DELETE FROM rate_limit_attempts WHERE key = :k"),
                {"k": f"tg:{chat_id}"})
            await db.commit()
        await cleanup_user(uid)


async def test_paycontrol():
    section("/paycontrol — setting where the money goes")

    chat_id = 900230
    uid = await _linked_user(chat_id, balance=0)
    original = await service.get_pay_instructions()
    try:
        # Non-admins must not even learn the command exists.
        fake = FakeTelegram()
        bot = PaymentBot(client=fake)
        await bot.handle_message({
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": chat_id},
            "text": "/paycontrol Карта: 1111 2222 3333 4444",
        })
        check("a non-admin cannot change the payment details",
              await service.get_pay_instructions() == original,
              await service.get_pay_instructions())
        check("and is not told the command exists",
              "реквизит" not in fake.all_text().lower(), fake.all_text()[:70])

        # With no argument it reports the current value.
        fake.messages.clear()
        await bot.handle_admin_command(5001, 5001, "/paycontrol")
        check("/paycontrol with no argument shows the current details",
              "Сейчас учителя видят" in fake.all_text(), fake.all_text()[:80])
        check("and simply takes the next message, no format to remember",
              "следующим сообщением" in fake.all_text(), fake.all_text()[:160])

        # Setting it.
        card = "Карта: 1111 2222 3333 4444 (Алиф Банк)\nПолучатель: TEST OWNER"
        fake.messages.clear()
        await bot.handle_admin_command(5001, 5001, f"/paycontrol {card}")
        stored = await service.get_pay_instructions()
        check("an admin can set the payment details",
              "1111 2222 3333 4444" in stored, stored[:60])
        check("the confirmation echoes what teachers will see",
              "1111 2222 3333 4444" in fake.all_text())

        # THE POINT: /pay must now show exactly that card.
        fake.messages.clear()
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "/pay"})
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "5"})
        shown = fake.all_text()
        check("/pay shows the card the admin set",
              "1111 2222 3333 4444" in shown, shown[-200:])
        check("and shows it verbatim, including the recipient line",
              "TEST OWNER" in shown, shown[-200:])

        # The two-step form: tap/type the command, then just send the
        # details. No format to remember, no command prefix to repeat.
        fake.messages.clear()
        await bot.handle_admin_command(5001, 5001, "/paycontrol")
        check("the command alone opens the prompt",
              bot._state(5001).awaiting_pay_instructions is True)
        two_step = "Карта: 5555 4444 3333 2222\nПолучатель: TWO STEP"
        await bot.handle_admin_update({
            "message": {"chat": {"id": 5001, "type": "private"},
                        "from": {"id": 5001}, "text": two_step},
        })
        check("the next plain message becomes the new details",
              "5555 4444 3333 2222" in await service.get_pay_instructions(),
              (await service.get_pay_instructions())[:50])
        check("and the prompt closes",
              bot._state(5001).awaiting_pay_instructions is False)

        # /cancel leaves it alone.
        before_cancel = await service.get_pay_instructions()
        await bot.handle_admin_command(5001, 5001, "/paycontrol")
        fake.messages.clear()
        await bot.handle_admin_update({
            "message": {"chat": {"id": 5001, "type": "private"},
                        "from": {"id": 5001}, "text": "/cancel"},
        })
        check("/cancel keeps the old details",
              await service.get_pay_instructions() == before_cancel)
        check("and says so", "Оставил как было" in fake.all_text(),
              fake.all_text()[:50])

        # The SINGLE-BOT path, which is what a deployment without
        # TELEGRAM_ADMIN_BOT_TOKEN actually runs. An earlier version
        # wired this check only into handle_admin_update, so on the
        # live single-bot setup the card number fell through every
        # branch and the admin got the teacher greeting back.
        await bot.handle_admin_command(5001, 5001, "/paycontrol")
        check("the prompt opens in single-bot mode too",
              bot._state(5001).awaiting_pay_instructions is True)
        fake.messages.clear()
        await bot.handle_message({
            "chat": {"id": 5001, "type": "private"},
            "from": {"id": 5001}, "text": "1234123412341234",
        })
        check("a bare card number sent to handle_message is stored",
              "1234123412341234" in await service.get_pay_instructions(),
              (await service.get_pay_instructions())[:40])
        check("and the admin is NOT shown the teacher greeting",
              "Салом" not in fake.all_text(), fake.all_text()[:60])
        check("the prompt closes afterwards",
              bot._state(5001).awaiting_pay_instructions is False)

        # A non-admin in the same state must not be able to set it.
        bot._state(chat_id).awaiting_pay_instructions = True
        guarded = await service.get_pay_instructions()
        await bot.handle_message({
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": chat_id}, "text": "9999 9999 9999 9999",
        })
        check("a non-admin cannot set the details even mid-prompt",
              await service.get_pay_instructions() == guarded,
              (await service.get_pay_instructions())[:40])

        # The admin panel: tapping a label works like the command.
        fake.messages.clear()
        await bot.handle_admin_update({
            "message": {"chat": {"id": 5001, "type": "private"},
                        "from": {"id": 5001}, "text": "💳 Реквизиты"},
        })
        check("tapping the admin button opens the same prompt",
              bot._state(5001).awaiting_pay_instructions is True)
        bot._state(5001).awaiting_pay_instructions = False

        fake.messages.clear()
        await bot.handle_admin_update({
            "message": {"chat": {"id": 5001, "type": "private"},
                        "from": {"id": 5001}, "text": "📋 Заявки на проверку"},
        })
        check("and the pending button works too",
              "заяв" in fake.all_text().lower(), fake.all_text()[:60])

        # Restore for the notification assertions below.
        await service.set_pay_instructions(card, 5001)

        # Changing it is announced to the OTHER admins, because this
        # decides where everyone's money goes.
        fake.messages.clear()
        new_card = "Карта: 9999 8888 7777 6666"
        await bot.handle_admin_command(5001, 5001, f"/paycontrol {new_card}")
        to_other = fake.texts_to(5002)
        check("the other admin is notified of the change",
              any("изменил реквизиты" in m for m in to_other),
              str(to_other[:1]))
        check("the notice carries both the old and the new details",
              any("1111 2222 3333 4444" in m and "9999 8888 7777 6666" in m
                  for m in to_other), str(to_other[:1]))
        check("the admin who made the change is not notified twice",
              not any("изменил реквизиты" in m for m in fake.texts_to(5001)))

        # Both changes are in the append-only audit log, with before and
        # after, so a redirected card is reconstructable.
        async with async_session() as db:
            rows = (await db.execute(text(
                "SELECT detail FROM payment_audit_log "
                "WHERE event = 'pay_instructions_changed' "
                "ORDER BY created_at"))).scalars().all()
        check("every change is audited", len(rows) >= 2, str(len(rows)))
        check("the audit keeps the previous value",
              any("1111 2222 3333 4444" in r for r in rows), "missing old value")
        check("and the new one",
              any("9999 8888 7777 6666" in r for r in rows), "missing new value")
    finally:
        async with async_session() as db:
            await db.execute(text(
                "DELETE FROM telegram_bot_state WHERE key = 'pay_instructions'"))
            await db.execute(text(
                "DELETE FROM payment_audit_log "
                "WHERE event = 'pay_instructions_changed'"))
            await db.commit()
        await cleanup_user(uid)


async def test_admin_sets_the_amount():
    section("Admin decides how much to credit")

    chat_id = 900240
    uid = await _linked_user(chat_id, balance=0)
    try:
        # Teacher asks for 100.00 but the receipt shows 40.00.
        req = await service.create_payment_request(uid, chat_id, 10000)
        scan = ocr.cross_check(receipt_scan(4000, reference="TXN-SETAMT"),
                               requested_dirams=10000)
        await service.attach_receipt(req.id, file_id="sa1", mime="image/jpeg",
                                      size_bytes=100, scan=scan)

        fake = FakeTelegram()
        bot = PaymentBot(client=fake)

        # The review keyboard leads with the brief's exact one-tap pair;
        # "set a different amount" is an extra option below them, for
        # exactly this case — a receipt that shows a different figure.
        labels = [r[0]["text"] for r in
                  bot._review_keyboard(req.id)["inline_keyboard"]]
        check("the review keyboard leads with one-tap approve",
              labels[0].startswith("✅"), str(labels))
        check("one-tap approve is present",
              any(l.startswith("✅") for l in labels), str(labels))
        check("an explicit 'set a different amount' option is still offered",
              any("указать" in l.lower() for l in labels), str(labels))
        check("rejecting is still possible",
              any("Отклонить" in l for l in labels), str(labels))

        # Tapping it asks, and credits nothing yet.
        fake.messages.clear()
        await bot.handle_callback(
            {"id": "cb-set", "data": f"pay:amt:{req.id}", "from": {"id": 5001}},
            from_admin_bot=True,
        )
        check("tapping it asks for the figure",
              "Сколько поступило" in fake.all_text(), fake.all_text()[:80])
        check("and says that figure is what reaches the balance",
              "попадёт на баланс" in fake.all_text(), fake.all_text()[-120:])
        check("it shows what the teacher claimed, for comparison",
              "100,00" in fake.all_text(), fake.all_text()[:120])
        check("nothing is credited by asking",
              await balance_of(uid) == 0, str(await balance_of(uid)))
        check("the request is still pending",
              (await service.get_request(req.id)).status
              == service.STATUS_PENDING)

        # A typo keeps the prompt open rather than dropping the request.
        fake.messages.clear()
        await bot.handle_admin_update({
            "message": {"chat": {"id": 5001, "type": "private"},
                        "from": {"id": 5001}, "text": "сорок"},
        })
        check("an unreadable amount is rejected",
              "Не понял сумму" in fake.all_text(), fake.all_text()[:60])
        check("and the prompt stays open",
              bot._state(5001).correcting_request_id == req.id)
        check("still nothing credited", await balance_of(uid) == 0)

        # The real figure.
        fake.messages.clear()
        await bot.handle_admin_update({
            "message": {"chat": {"id": 5001, "type": "private"},
                        "from": {"id": 5001}, "text": "40"},
        })
        check("the admin's figure is what gets credited",
              await balance_of(uid) == 4000, str(await balance_of(uid)))
        check("NOT the amount the teacher asked for",
              await balance_of(uid) != 10000)
        check("the admin is told what was credited",
              "40,00" in fake.all_text(), fake.all_text()[:90])
        check("the teacher is told the real figure too",
              any("40,00" in m for m in fake.texts_to(chat_id)),
              str(fake.texts_to(chat_id)[-1:]))
        check("the prompt is closed",
              bot._state(5001).correcting_request_id is None)

        # It is recorded as a correction, with both figures, so a credit
        # that did not match the request is never silent.
        events = await audit_events(req.id)
        check("it is audited as a correction, not a plain approval",
              "approved_with_correction" in events, str(events))
        async with async_session() as db:
            detail = (await db.execute(text(
                "SELECT detail FROM payment_audit_log "
                "WHERE payment_request_id = :i AND event = "
                "'approved_with_correction'"), {"i": req.id})).scalar()
        check("the audit keeps the requested figure", "10000" in detail, detail[:120])
        check("and the credited one", "4000" in detail, detail[:120])
        check("and why it differed", "set by admin" in detail, detail[:160])

        # Cancelling leaves the request untouched.
        req2 = await service.create_payment_request(uid, chat_id, 500)
        scan2 = ocr.cross_check(receipt_scan(500, reference="TXN-SETAMT2"),
                                requested_dirams=500)
        await service.attach_receipt(req2.id, file_id="sa2", mime="image/jpeg",
                                      size_bytes=100, scan=scan2)
        await bot.handle_callback(
            {"id": "cb-set2", "data": f"pay:amt:{req2.id}", "from": {"id": 5001}},
            from_admin_bot=True,
        )
        fake.messages.clear()
        await bot.handle_admin_update({
            "message": {"chat": {"id": 5001, "type": "private"},
                        "from": {"id": 5001}, "text": "/cancel"},
        })
        check("cancelling says so", "Отменено" in fake.all_text(),
              fake.all_text()[:50])
        check("and leaves the request undecided",
              (await service.get_request(req2.id)).status
              == service.STATUS_PENDING)
        check("with nothing credited", await balance_of(uid) == 4000,
              str(await balance_of(uid)))

        # A decided request cannot be re-opened for a new amount.
        await service.reject_payment(req2.id, 5001)
        fake.messages.clear()
        await bot.handle_callback(
            {"id": "cb-set3", "data": f"pay:amt:{req2.id}", "from": {"id": 5001}},
            from_admin_bot=True,
        )
        check("a decided request refuses the amount prompt",
              bot._state(5001).correcting_request_id is None)
        check("and says it was already reviewed",
              any("уже рассмотрена" in (a["text"] or "") for a in fake.answers),
              str(fake.answers[-1:]))

        # A non-admin cannot reach the prompt at all.
        await bot.handle_callback(
            {"id": "cb-x", "data": f"pay:amt:{req.id}", "from": {"id": 4242}},
            from_admin_bot=True,
        )
        check("a non-admin cannot open the amount prompt",
              bot._state(4242).correcting_request_id is None)
    finally:
        await cleanup_user(uid)


async def test_link_status_for_the_app():
    section("Link status reported to the app")

    uid = await make_user()
    chat_id = 900110
    try:
        before = await service.link_status(uid)
        check("an unlinked account reports linked=False", before["linked"] is False)
        check("bot_configured is True when the server has a bot",
              before["bot_configured"] is True)
        check("the bot username is reported for the deep link",
              before["bot_username"] == "dastyor_test_bot", before["bot_username"])

        issued = await service.issue_link_token(uid)
        await service.redeem_link_token(
            issued.deep_link.split("start=", 1)[1], chat_id, chat_id)

        after = await service.link_status(uid)
        check("a linked account reports linked=True", after["linked"] is True)
        check("the link time is reported", after["linked_at"] is not None)
    finally:
        await cleanup_user(uid)


# ---------------------------------------------------------------------

async def main():
    print(f"Telegram payment flow - integration tests against {_TEST_DB}")
    print("Applying schema...")
    await init_db()
    print(f"Bot config: {get_telegram_settings().redacted()}")

    await test_linking()
    await test_token_reuse_and_expiry()
    await test_chat_cannot_be_hijacked()
    await test_approve_credits_once()
    await test_reject_and_more_info()
    await test_concurrent_approval()
    await test_duplicate_reference()
    await test_amount_mismatch_is_flagged_not_blocked()
    await test_amount_correction_requires_reason()
    await test_rollback_on_missing_user()
    await test_unauthorized_admin_actions()
    await test_notification_failure_does_not_lose_the_credit()
    await test_bot_commands_and_receipt_flow()
    await test_empty_photo_is_not_treated_as_a_receipt()
    await test_unlinked_chat_is_guided()
    await test_generation_integration()
    await test_separate_admin_bot()
    await test_single_bot_fallback()
    await test_admin_management()
    await test_admin_commands_over_the_bot()
    await test_unlink()
    await test_unlink_revokes_admin()
    await test_pending_queue()
    await test_add_admin_by_username()
    await test_password_login()
    await test_password_login_over_the_bot()
    await test_password_login_throttle()
    await test_paycontrol()
    await test_admin_sets_the_amount()
    await test_link_status_for_the_app()

    print()
    if FAIL:
        print(f"{len(FAIL)} FAILED:")
        for name in FAIL:
            print(f"  - {name}")
        return 1
    print("all integration checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
