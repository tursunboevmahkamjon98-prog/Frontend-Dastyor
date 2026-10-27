"""Administrator top-up flow: integration tests against a real Postgres.

Run from the backend directory:

    python tests/test_telegram_topup.py

This is the flow the brief makes primary: an administrator who already
knows the money arrived records it, and the balance moves. There is no
receipt in it and no "did the money arrive" button, so what has to be
proved here is different from the receipt-review tests:

  * a credit happens exactly once, even when the confirm button is
    tapped twice or two taps race each other,
  * the amount that lands in the ledger is the one the admin typed, in
    integer dirams, with no floating point anywhere in the path,
  * nothing is credited on any rejection path, and
  * a failure to notify the teacher never looks like a failure to
    credit, because by then the money has already moved.

The database guarantees under test are Postgres behaviour — a partial
unique index on the idempotency key, ``UPDATE ... RETURNING`` as the
atomic read-modify-write — so a real Postgres is required. The test
database (``dastyor_bot_test`` by default) and the fixtures are shared
with test_telegram_payments, which is imported for them; importing it
runs no tests.

Nothing here reaches Telegram. No real administrator is messaged and no
real payment is made.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Brings the test-database environment, the recording Bot API fake and
# the user fixtures. Importing it executes only module-level setup.
from test_telegram_payments import (  # noqa: E402
    FAIL,
    FakeTelegram,
    balance_of,
    check,
    cleanup_user,
    make_user,
    section,
)

from sqlalchemy import text  # noqa: E402

from app.database import async_session, init_db  # noqa: E402
from app.telegram import service, topup  # noqa: E402
from app.telegram.api import TelegramApiError, TelegramTransportError  # noqa: E402
from app.telegram.bot import CB_CREDIT_NO, CB_CREDIT_OK, PaymentBot  # noqa: E402
from app.telegram.config import get_telegram_settings  # noqa: E402

ADMIN = 5001
ADMIN_CHAT = 5001
OUTSIDER = 4242


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

async def link_chat(uid: str, chat_id: int) -> None:
    """Attach a Telegram chat to an account without going through /start."""
    issued = await service.issue_link_token(uid)
    token = issued.deep_link.split("start=", 1)[1]
    await service.redeem_link_token(token, chat_id, chat_id)


async def short_id_of(uid: str) -> str:
    async with async_session() as db:
        return (await db.execute(
            text("SELECT short_id FROM users WHERE id = :uid"), {"uid": uid}
        )).scalar()


async def topup_rows(uid: str) -> list[tuple]:
    async with async_session() as db:
        return (await db.execute(text(
            "SELECT amount_dirams, balance_before, balance_after, "
            "       actor_telegram_id, public_code, idempotency_key, reason "
            "FROM balance_transactions "
            "WHERE user_id = :uid AND actor_telegram_id IS NOT NULL "
            "ORDER BY created_at"
        ), {"uid": uid})).all()


async def say(bot: PaymentBot, body: str, chat_id: int = ADMIN_CHAT,
              from_id: int = ADMIN) -> None:
    """Deliver one admin-bot message."""
    await bot.handle_admin_update({"message": {
        "chat": {"id": chat_id, "type": "private"},
        "from": {"id": from_id},
        "text": body,
    }})


async def tap(bot: PaymentBot, data: str, chat_id: int = ADMIN_CHAT,
              from_id: int = ADMIN, callback_id: str = "cb-1") -> None:
    """Deliver one inline-button tap on the admin bot."""
    await bot.handle_admin_update({"callback_query": {
        "id": callback_id,
        "data": data,
        "from": {"id": from_id},
        "message": {"message_id": 7, "chat": {"id": chat_id, "type": "private"}},
    }})


def staged_key(bot: PaymentBot) -> str | None:
    """The idempotency key of the single staged top-up, if there is one."""
    keys = list(bot._staged_topups)
    return keys[-1] if keys else None


# ---------------------------------------------------------------------
# Amount handling
# ---------------------------------------------------------------------

async def test_amount_parsing():
    section("Amounts are parsed as integer dirams, never as floats")

    # A somoni is 100 dirams. Every one of these has to land on an exact
    # integer: the first time a balance is a float, it is wrong by a
    # diram and nobody can say where it went.
    for raw, expected in [
        ("25", 2500),
        ("25.5", 2550),
        ("25,50", 2550),
        ("0.01", 1),
        ("1 000", 100000),
        ("1 000,25", 100025),
    ]:
        got = topup.parse_amount(raw)
        check(f"parse_amount({raw!r}) == {expected}", got == expected,
              f"got {got}")
        check(f"parse_amount({raw!r}) is an int", isinstance(got, int),
              type(got).__name__)

    # Shapes that look numeric to float() but are not an amount anyone
    # typed on purpose. 1e5 would be a hundred thousand somoni.
    for raw in ("abc", "", "1e5", "25.555", "0x10", "--5", "２５"):
        check(f"parse_amount({raw!r}) is rejected",
              topup.parse_amount(raw) is None, repr(topup.parse_amount(raw)))

    checks = {
        "0": "not_positive",
        "-5": "not_positive",
        "abc": "not_a_number",
        "99999999": "too_large",
    }
    for raw, problem in checks.items():
        result = topup.validate_amount(raw)
        check(f"validate_amount({raw!r}) -> {problem}",
              not result.ok and result.problem == problem,
              f"ok={result.ok} problem={result.problem}")

    ok = topup.validate_amount("25,50")
    check("a good amount validates", ok.ok and ok.dirams == 2550,
          f"{ok.ok} {ok.dirams}")


# ---------------------------------------------------------------------
# Finding the right person
# ---------------------------------------------------------------------

async def test_find_user():
    section("Finding the user to credit")

    uid = await make_user(balance_dirams=1234)
    sid = await short_id_of(uid)
    try:
        found = await topup.find_user(sid)
        check("found by 6-digit account id", found is not None
              and found.user_id == uid, repr(found and found.short_id))
        check("the balance comes with it",
              found is not None and found.balance_dirams == 1234,
              str(found and found.balance_dirams))

        check("found by internal uuid",
              (await topup.find_user(uid)) is not None)
        check("an unknown id finds nobody",
              (await topup.find_user("000000")) is None)

        matches = await topup.search_users("Telegram test")
        check("a name search finds it", any(m.user_id == uid for m in matches),
              str(len(matches)))

        # A wildcard typed by an admin must be a literal, or "%" would
        # match every teacher in the system and the list would be
        # useless at best.
        wild = await topup.search_users("%")
        check("a bare % is not treated as a wildcard", wild == [],
              str(len(wild)))
        under = await topup.search_users("_")
        check("a bare _ is not treated as a wildcard", under == [],
              str(len(under)))
    finally:
        await cleanup_user(uid)


async def test_pick_from_several():
    section("Several name matches are offered, never auto-picked")

    a = await make_user(balance_dirams=0)
    b = await make_user(balance_dirams=0)
    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        await say(bot, "/credit")
        await say(bot, "Telegram test teacher")

        state = bot._state(ADMIN_CHAT)
        check("nobody was picked automatically", state.topup_user_id is None,
              repr(state.topup_user_id))
        check("the flow is still on the user step",
              state.topup_stage == "user", repr(state.topup_stage))
        check("the admin is shown the candidates to choose from",
              "Нашёл несколько"
              in fake.all_text(), fake.all_text()[-160:])

        sid = await short_id_of(a)
        check("both candidates are listed", sid in fake.all_text(), sid)
    finally:
        bot._states.clear()
        await cleanup_user(a)
        await cleanup_user(b)


async def test_unknown_user_credits_nothing():
    section("An unrecognised identifier credits nothing")

    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        await say(bot, "/credit")
        await say(bot, "000000")
        check("the admin is told nobody matched",
              "Никого не нашёл"
              in fake.all_text(), fake.all_text()[-120:])
        check("and is told what an account id looks like",
              "6 цифр" in fake.all_text())
        check("nothing was staged", not bot._staged_topups,
              str(list(bot._staged_topups)))
    finally:
        bot._states.clear()


# ---------------------------------------------------------------------
# The flow end to end
# ---------------------------------------------------------------------

async def test_credit_end_to_end():
    section("Admin credits a user: the whole flow")

    uid = await make_user(balance_dirams=1000)
    sid = await short_id_of(uid)
    chat_id = 900501
    await link_chat(uid, chat_id)

    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        await say(bot, "/credit")
        check("the admin is asked who to credit",
              "Кому начислить"
              in fake.all_text(), fake.all_text()[-80:])

        await say(bot, sid)
        check("the chosen user is echoed back by name and id",
              sid in fake.all_text(), sid)
        check("with their current balance, so a mistake is visible",
              "10,00" in fake.all_text(), fake.all_text()[-200:])

        await say(bot, "абв")
        check("a non-numeric amount is refused",
              "Не понял сумму"
              in fake.all_text(), fake.all_text()[-80:])
        check("and the flow stays on the amount step",
              bot._state(ADMIN_CHAT).topup_stage == "amount",
              repr(bot._state(ADMIN_CHAT).topup_stage))

        await say(bot, "25,50")
        await say(bot, "Korti Milli")

        check("a confirmation is staged, not applied",
              len(bot._staged_topups) == 1, str(len(bot._staged_topups)))
        check("and the balance has not moved yet",
              await balance_of(uid) == 1000, str(await balance_of(uid)))

        preview = fake.all_text()
        check("the preview shows the balance before", "10,00" in preview)
        check("the amount", "25,50" in preview)
        check("and the balance after", "35,50" in preview, preview[-240:])
        check("the comment is shown for checking",
              "Korti Milli" in preview, preview[-240:])

        key = staged_key(bot)
        await tap(bot, f"{CB_CREDIT_OK}:{key}")

        check("the balance is credited", await balance_of(uid) == 3550,
              str(await balance_of(uid)))
        rows = await topup_rows(uid)
        check("exactly one ledger row was written", len(rows) == 1,
              str(len(rows)))
        if rows:
            amount, before, after, actor, code, stored_key, reason = rows[0]
            check("the ledger amount is what the admin typed", amount == 2550,
                  str(amount))
            check("before and after are consistent",
                  (before, after) == (1000, 3550), f"{before} -> {after}")
            check("the acting admin is recorded", actor == ADMIN, str(actor))
            check("an operation code was issued",
                  bool(code) and code.startswith("TX-"), repr(code))
            check("the idempotency key is stored", stored_key == key,
                  repr(stored_key))
            check("the comment is kept as the reason", reason == "Korti Milli",
                  repr(reason))

        # The teacher is told, in their own language, with the code they
        # would quote if they ever had to ask about it.
        teacher_text = "\n".join(fake.texts_to(chat_id))
        check("the teacher is notified", bool(teacher_text),
              teacher_text[:60])
        check("the notice states the credited amount",
              "25,50" in teacher_text, teacher_text[:160])
        check("and the new balance", "35,50" in teacher_text,
              teacher_text[:160])
        check("and the operation code",
              rows and rows[0][4] in teacher_text, teacher_text[:160])

        admin_text = "\n".join(fake.texts_to(ADMIN_CHAT))
        check("the admin is told it was applied",
              "Начислено" in admin_text,
              admin_text[-200:])
        check("and that the user was reached",
              "уведомлён" in admin_text,
              admin_text[-200:])
        check("the staged entry is consumed", not bot._staged_topups,
              str(list(bot._staged_topups)))
        check("and the conversation is reset",
              bot._state(ADMIN_CHAT).topup_stage is None,
              repr(bot._state(ADMIN_CHAT).topup_stage))
    finally:
        bot._states.clear()
        await cleanup_user(uid)


async def test_skip_the_comment():
    section("The comment can be skipped")

    uid = await make_user(balance_dirams=0)
    sid = await short_id_of(uid)
    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        await say(bot, "/credit")
        await say(bot, sid)
        await say(bot, "40")
        await say(bot, "/skip")
        check("a confirmation is still staged", len(bot._staged_topups) == 1,
              str(len(bot._staged_topups)))
        await tap(bot, f"{CB_CREDIT_OK}:{staged_key(bot)}")
        check("the credit still applies", await balance_of(uid) == 4000,
              str(await balance_of(uid)))
        rows = await topup_rows(uid)
        check("and the reason is left empty rather than invented",
              rows and rows[0][6] is None, repr(rows and rows[0][6]))
    finally:
        bot._states.clear()
        await cleanup_user(uid)


# ---------------------------------------------------------------------
# Exactly once
# ---------------------------------------------------------------------

async def test_double_tap_credits_once():
    section("Tapping confirm twice credits once")

    uid = await make_user(balance_dirams=0)
    sid = await short_id_of(uid)
    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        await say(bot, "/credit")
        await say(bot, sid)
        await say(bot, "30")
        await say(bot, "/skip")
        key = staged_key(bot)

        await tap(bot, f"{CB_CREDIT_OK}:{key}", callback_id="cb-a")
        first = await balance_of(uid)
        await tap(bot, f"{CB_CREDIT_OK}:{key}", callback_id="cb-b")
        second = await balance_of(uid)

        check("the first tap credits", first == 3000, str(first))
        check("the second changes nothing", second == 3000, str(second))
        check("and only one ledger row exists",
              len(await topup_rows(uid)) == 1,
              str(len(await topup_rows(uid))))
        check("the admin is told it was already done",
              "уже выполнена"
              in "\n".join(fake.texts_to(ADMIN_CHAT)),
              "\n".join(fake.texts_to(ADMIN_CHAT))[-160:])
    finally:
        bot._states.clear()
        await cleanup_user(uid)


async def test_concurrent_confirmations():
    section("Five simultaneous confirmations credit once")

    uid = await make_user(balance_dirams=0)
    key = topup.new_idempotency_key()
    try:
        results = await asyncio.gather(*[
            topup.credit_user(uid, 500, ADMIN, key) for _ in range(5)
        ])
        outcomes = [r.outcome for r in results]
        check("exactly one call reports applied",
              outcomes.count("applied") == 1, str(outcomes))
        check("the rest report duplicate",
              outcomes.count("duplicate") == 4, str(outcomes))
        check("the balance moved once", await balance_of(uid) == 500,
              str(await balance_of(uid)))
        check("one ledger row", len(await topup_rows(uid)) == 1,
              str(len(await topup_rows(uid))))
        codes = {r.operation_code for r in results}
        check("and every caller is told the same operation code",
              len(codes) == 1, str(codes))
    finally:
        await cleanup_user(uid)


async def test_cancel_credits_nothing():
    section("Cancelling credits nothing")

    uid = await make_user(balance_dirams=700)
    sid = await short_id_of(uid)
    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        await say(bot, "/credit")
        await say(bot, sid)
        await say(bot, "15")
        await say(bot, "/skip")
        key = staged_key(bot)
        await tap(bot, f"{CB_CREDIT_NO}:{key}")

        check("the balance is untouched", await balance_of(uid) == 700,
              str(await balance_of(uid)))
        check("no ledger row was written", await topup_rows(uid) == [],
              str(await topup_rows(uid)))
        check("the admin is told it was cancelled",
              "отменена"
              in "\n".join(fake.texts_to(ADMIN_CHAT)).lower(),
              "\n".join(fake.texts_to(ADMIN_CHAT))[-120:])
        check("nothing stays staged", not bot._staged_topups,
              str(list(bot._staged_topups)))

        # And the same via /cancel part-way through, before any amount.
        await say(bot, "/credit")
        await say(bot, sid)
        await say(bot, "/cancel")
        check("/cancel mid-flow clears the conversation",
              bot._state(ADMIN_CHAT).topup_stage is None,
              repr(bot._state(ADMIN_CHAT).topup_stage))
        check("and still credits nothing", await balance_of(uid) == 700,
              str(await balance_of(uid)))
    finally:
        bot._states.clear()
        await cleanup_user(uid)


async def test_stale_confirmation():
    section("A confirmation the bot no longer remembers credits nothing")

    uid = await make_user(balance_dirams=0)
    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        # What a button tapped after a restart looks like: the key is
        # well-formed but nothing is staged and nothing was ever applied.
        await tap(bot, f"{CB_CREDIT_OK}:{topup.new_idempotency_key()}")
        check("the balance is untouched", await balance_of(uid) == 0,
              str(await balance_of(uid)))
        check("and the admin is told to start again",
              "не актуальна"
              in "\n".join(fake.texts_to(ADMIN_CHAT)),
              "\n".join(fake.texts_to(ADMIN_CHAT))[-160:])
    finally:
        bot._states.clear()
        await cleanup_user(uid)


# ---------------------------------------------------------------------
# Authorization and limits
# ---------------------------------------------------------------------

async def test_only_admins_can_credit():
    section("Only an administrator can credit")

    uid = await make_user(balance_dirams=0)
    sid = await short_id_of(uid)
    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        # An outsider messaging the admin bot gets nowhere near the flow.
        await say(bot, "/credit", chat_id=OUTSIDER, from_id=OUTSIDER)
        check("a non-admin cannot start the flow",
              bot._state(OUTSIDER).topup_stage is None,
              repr(bot._state(OUTSIDER).topup_stage))

        # And cannot finish one somebody else started, even holding the
        # key: the callback is authorized on its sender, not its payload.
        await say(bot, "/credit")
        await say(bot, sid)
        await say(bot, "20")
        await say(bot, "/skip")
        key = staged_key(bot)
        await tap(bot, f"{CB_CREDIT_OK}:{key}", chat_id=OUTSIDER,
                  from_id=OUTSIDER, callback_id="cb-out")

        check("an outsider's tap credits nothing",
              await balance_of(uid) == 0, str(await balance_of(uid)))
        check("and is refused with an alert",
              any(a["alert"] for a in fake.answers), str(fake.answers[-1:]))
        check("the staged entry survives for the real admin",
              key in bot._staged_topups, str(list(bot._staged_topups)))

        await tap(bot, f"{CB_CREDIT_OK}:{key}", callback_id="cb-ok")
        check("who can still apply it", await balance_of(uid) == 2000,
              str(await balance_of(uid)))
    finally:
        bot._states.clear()
        await cleanup_user(uid)


async def test_ceiling_is_enforced_in_the_service():
    section("The per-operation ceiling holds even if the bot is bypassed")

    uid = await make_user(balance_dirams=0)
    ceiling = get_telegram_settings().TELEGRAM_MAX_TOPUP_DIRAMS
    try:
        check("the ceiling is a whole number of dirams",
              isinstance(ceiling, int), type(ceiling).__name__)
        over = await topup.credit_user(uid, ceiling + 1, ADMIN,
                                       topup.new_idempotency_key())
        check("a credit above the ceiling is refused",
              over.outcome == "invalid_amount", over.outcome)
        check("and nothing was written", await balance_of(uid) == 0,
              str(await balance_of(uid)))

        for amount in (0, -100):
            r = await topup.credit_user(uid, amount, ADMIN,
                                        topup.new_idempotency_key())
            check(f"a credit of {amount} is refused",
                  r.outcome == "invalid_amount", r.outcome)
        check("the balance is still zero", await balance_of(uid) == 0,
              str(await balance_of(uid)))

        # Exactly at the ceiling is allowed: the limit is a maximum,
        # not something to be off by one about.
        at_limit = await topup.credit_user(uid, ceiling, ADMIN,
                                           topup.new_idempotency_key())
        check("a credit exactly at the ceiling is allowed",
              at_limit.outcome == "applied", at_limit.outcome)
    finally:
        await cleanup_user(uid)


async def test_missing_user_rolls_back():
    section("Crediting a deleted account writes nothing")

    import uuid as _uuid
    gone = await topup.credit_user(str(_uuid.uuid4()), 500, ADMIN,
                                   topup.new_idempotency_key())
    check("the outcome says the user is gone", gone.outcome == "user_gone",
          gone.outcome)
    check("no operation code was handed out",
          gone.operation_code is None, repr(gone.operation_code))


# ---------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------

async def test_notification_failure_keeps_the_credit():
    section("A failed notification never undoes a credit")

    uid = await make_user(balance_dirams=0)
    sid = await short_id_of(uid)
    chat_id = 900502
    await link_chat(uid, chat_id)

    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    # No waiting: the retry schedule is what is under test, not the
    # wall-clock patience of the test runner.
    bot.NOTIFY_BACKOFF_SECONDS = (0.0, 0.0, 0.0)
    try:
        await say(bot, "/credit")
        await say(bot, sid)
        await say(bot, "12")
        await say(bot, "/skip")
        key = staged_key(bot)

        sends_before = len(fake.messages)
        fake.fail_sends = True
        await tap(bot, f"{CB_CREDIT_OK}:{key}")
        fake.fail_sends = False

        check("the credit stands", await balance_of(uid) == 1200,
              str(await balance_of(uid)))
        check("the ledger row is there", len(await topup_rows(uid)) == 1,
              str(len(await topup_rows(uid))))
        check("nothing at all was delivered", len(fake.messages) == sends_before,
              f"{sends_before} -> {len(fake.messages)}")
    finally:
        bot._states.clear()
        await cleanup_user(uid)


async def test_transport_failure_is_retried():
    section("A transient send failure is retried; a refusal is not")

    uid = await make_user(balance_dirams=0)
    chat_id = 900503
    await link_chat(uid, chat_id)

    class FlakyOnce(FakeTelegram):
        """Fails the first send, then behaves."""

        def __init__(self):
            super().__init__()
            self.attempts = 0

        async def send_message(self, chat_id, text_body, **kwargs):
            self.attempts += 1
            if self.attempts == 1:
                raise TelegramTransportError("fake: connection reset")
            return await super().send_message(chat_id, text_body, **kwargs)

    class Blocked(FakeTelegram):
        """Telegram answers, and the answer is no."""

        def __init__(self):
            super().__init__()
            self.attempts = 0

        async def send_message(self, chat_id, text_body, **kwargs):
            self.attempts += 1
            raise TelegramApiError("sendMessage", 403,
                                   "fake: bot was blocked by the user")

    try:
        flaky = FlakyOnce()
        bot = PaymentBot(client=flaky)
        bot.NOTIFY_BACKOFF_SECONDS = (0.0, 0.0, 0.0)
        result = await topup.credit_user(uid, 300, ADMIN,
                                         topup.new_idempotency_key())
        user = await topup.find_user(uid)
        delivered = await bot._notify_credited(user, result, None)
        check("a retry delivers the notice", delivered is True, str(delivered))
        check("and it took two attempts", flaky.attempts == 2,
              str(flaky.attempts))

        blocked = Blocked()
        bot2 = PaymentBot(client=blocked)
        bot2.NOTIFY_BACKOFF_SECONDS = (0.0, 0.0, 0.0)
        result2 = await topup.credit_user(uid, 300, ADMIN,
                                          topup.new_idempotency_key())
        delivered2 = await bot2._notify_credited(
            await topup.find_user(uid), result2, None)
        check("a refusal reports failure", delivered2 is False,
              str(delivered2))
        check("and is not retried", blocked.attempts == 1,
              str(blocked.attempts))
        check("both credits still stand", await balance_of(uid) == 600,
              str(await balance_of(uid)))
    finally:
        await cleanup_user(uid)


async def test_unlinked_user_is_credited_anyway():
    section("A user with no Telegram is still credited")

    uid = await make_user(balance_dirams=0)
    sid = await short_id_of(uid)
    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        await say(bot, "/credit")
        await say(bot, sid)
        await say(bot, "18")
        await say(bot, "/skip")
        preview = "\n".join(fake.texts_to(ADMIN_CHAT))
        check("the preview says the user will not get a message",
              "не привязан" in preview,
              preview[-200:])

        await tap(bot, f"{CB_CREDIT_OK}:{staged_key(bot)}")
        check("the balance is credited regardless",
              await balance_of(uid) == 1800, str(await balance_of(uid)))
        check("and the admin is told the notice could not be sent",
              "не удалось"
              in "\n".join(fake.texts_to(ADMIN_CHAT)),
              "\n".join(fake.texts_to(ADMIN_CHAT))[-200:])
    finally:
        bot._states.clear()
        await cleanup_user(uid)


# ---------------------------------------------------------------------
# History, statistics, and the teacher's own view
# ---------------------------------------------------------------------

async def test_history_and_statistics():
    section("History and statistics report what happened")

    uid = await make_user(balance_dirams=0)
    sid = await short_id_of(uid)
    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        before = await topup.topup_stats()

        for amount in ("10", "5,50"):
            await say(bot, "/credit")
            await say(bot, sid)
            await say(bot, amount)
            await say(bot, "Наличные")
            await tap(bot, f"{CB_CREDIT_OK}:{staged_key(bot)}",
                      callback_id=f"cb-{amount}")

        check("both credits landed", await balance_of(uid) == 1550,
              str(await balance_of(uid)))

        entries = await topup.topup_history(user_id=uid)
        check("history returns both, newest first", len(entries) == 2,
              str(len(entries)))
        check("newest first", entries and entries[0].amount_dirams == 550,
              str(entries and entries[0].amount_dirams))
        check("with the admin who did it",
              all(e.admin_telegram_id == ADMIN for e in entries))

        after = await topup.topup_stats()
        check("the total count went up by two",
              after.total_count == before.total_count + 2,
              f"{before.total_count} -> {after.total_count}")
        check("and the total amount by 15,50",
              after.total_dirams == before.total_dirams + 1550,
              f"{before.total_dirams} -> {after.total_dirams}")
        check("today's figures moved too",
              after.today_dirams >= 1550, str(after.today_dirams))

        fake.messages.clear()
        await say(bot, "/topups")
        shown = "\n".join(fake.texts_to(ADMIN_CHAT))
        check("the admin's history screen lists the operation codes",
              entries and entries[0].operation_code in shown, shown[:200])
        check("and the amounts", "5,50" in shown, shown[:200])

        fake.messages.clear()
        await say(bot, "/stats")
        stats_text = "\n".join(fake.texts_to(ADMIN_CHAT))
        check("the statistics screen renders",
              "Статистика" in stats_text,
              stats_text[:160])
    finally:
        bot._states.clear()
        await cleanup_user(uid)


async def test_teacher_sees_the_topup():
    section("The teacher's own screens show the credit")

    uid = await make_user(balance_dirams=0, language="Русский")
    sid = await short_id_of(uid)
    chat_id = 900504
    await link_chat(uid, chat_id)

    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        await say(bot, "/credit")
        await say(bot, sid)
        await say(bot, "22")
        await say(bot, "Korti Milli")
        await tap(bot, f"{CB_CREDIT_OK}:{staged_key(bot)}")

        fake.messages.clear()
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "/history"})
        history = "\n".join(fake.texts_to(chat_id))
        check("the history screen shows the top-up",
              "22,00" in history, history[:200])
        check("marked as an increase", "➕" in history, history[:200])
        check("with the comment", "Korti Milli" in history, history[:200])
        check("and the current balance underneath",
              "22,00" in history.rsplit("\n", 1)[-1], history[-80:])

        fake.messages.clear()
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "/account"})
        account = "\n".join(fake.texts_to(chat_id))
        check("the account screen shows the id the admin needs",
              sid in account, account[:200])
        check("and the balance", "22,00" in account, account[:200])

        # A charge and a credit must be told apart on sight: the same
        # number with the wrong sign is the one mistake a teacher
        # cannot be expected to catch.
        async with async_session() as db:
            await db.execute(text(
                "INSERT INTO balance_transactions (id, user_id, kind, "
                " amount_dirams, balance_before, balance_after, reason, "
                " material_type, created_at) "
                "VALUES (gen_random_uuid()::text, :uid, 'charge', -500, 2200, "
                "        1700, NULL, 'konspekt', now())"
            ), {"uid": uid})
            await db.commit()

        fake.messages.clear()
        await bot.handle_message({"chat": {"id": chat_id, "type": "private"},
                                  "from": {"id": chat_id}, "text": "/history"})
        mixed = "\n".join(fake.texts_to(chat_id))
        check("a charge is shown as a decrease", "➖" in mixed,
              mixed[:240])
        check("with its own amount", "5,00" in mixed, mixed[:240])
        check("and the top-up is still there", "22,00" in mixed, mixed[:240])
    finally:
        bot._states.clear()
        await cleanup_user(uid)


async def test_history_does_not_leak_across_users():
    """Two teachers, two chats. Neither ever sees the other's history.

    The brief explicitly wants this tested. There is no code path to
    test as an attack here — /history and /status take no user-supplied
    id at all, they read whichever account is linked to the chat the
    command arrived in — so this test demonstrates that structurally:
    distinct, distinguishable amounts for each teacher, then checks
    each one's own screen for exactly their own figure and never the
    other's, from both directions.
    """
    section("A teacher's history never shows another teacher's")

    uid_a = await make_user(balance_dirams=0, language="Русский")
    uid_b = await make_user(balance_dirams=0, language="Русский")
    sid_a = await short_id_of(uid_a)
    sid_b = await short_id_of(uid_b)
    chat_a, chat_b = 900601, 900602
    await link_chat(uid_a, chat_a)
    await link_chat(uid_b, chat_b)

    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        await say(bot, "/credit")
        await say(bot, sid_a)
        await say(bot, "17")
        await say(bot, "/skip")
        await tap(bot, f"{CB_CREDIT_OK}:{staged_key(bot)}")

        await say(bot, "/credit")
        await say(bot, sid_b)
        await say(bot, "31")
        await say(bot, "/skip")
        await tap(bot, f"{CB_CREDIT_OK}:{staged_key(bot)}")

        fake.messages.clear()
        await bot.handle_message({"chat": {"id": chat_a, "type": "private"},
                                  "from": {"id": chat_a}, "text": "/history"})
        history_a = "\n".join(fake.texts_to(chat_a))
        check("A's history shows A's own credit", "17,00" in history_a, history_a[:160])
        check("A's history never shows B's credit", "31,00" not in history_a, history_a[:160])

        fake.messages.clear()
        await bot.handle_message({"chat": {"id": chat_b, "type": "private"},
                                  "from": {"id": chat_b}, "text": "/history"})
        history_b = "\n".join(fake.texts_to(chat_b))
        check("B's history shows B's own credit", "31,00" in history_b, history_b[:160])
        check("B's history never shows A's credit", "17,00" not in history_b, history_b[:160])

        fake.messages.clear()
        await bot.handle_message({"chat": {"id": chat_a, "type": "private"},
                                  "from": {"id": chat_a}, "text": "/account"})
        account_a = "\n".join(fake.texts_to(chat_a))
        check("A's /account shows A's own id", sid_a in account_a, account_a[:160])
        check("A's /account never shows B's id", sid_b not in account_a, account_a[:160])
    finally:
        bot._states.clear()
        await cleanup_user(uid_a)
        await cleanup_user(uid_b)


async def test_ledger_explains_the_balance():
    section("The ledger accounts for every diram it wrote")

    uid = await make_user(balance_dirams=0)
    try:
        for amount in (100, 250, 1):
            await topup.credit_user(uid, amount, ADMIN,
                                    topup.new_idempotency_key())
        rec = await topup.reconcile_balance(uid)
        check("the stored balance equals the sum of the ledger",
              rec is not None and rec.unexplained == 0,
              f"stored={rec and rec.stored} ledger={rec and rec.from_ledger}")
        check("which is the exact integer total",
              rec is not None and rec.stored == 351, str(rec and rec.stored))
    finally:
        await cleanup_user(uid)


# ---------------------------------------------------------------------
# Button labels drive the same handlers as the commands
# ---------------------------------------------------------------------

async def test_buttons_reach_the_same_handlers():
    section("The admin panel buttons work as the commands do")

    from app.telegram.texts import ADMIN_BUTTONS

    uid = await make_user(balance_dirams=0)
    sid = await short_id_of(uid)
    fake = FakeTelegram()
    bot = PaymentBot(client=fake)
    try:
        await say(bot, ADMIN_BUTTONS["credit"])
        check("the credit button starts the flow",
              bot._state(ADMIN_CHAT).topup_stage == "user",
              repr(bot._state(ADMIN_CHAT).topup_stage))

        await say(bot, ADMIN_BUTTONS["cancel"])
        check("the cancel button ends it",
              bot._state(ADMIN_CHAT).topup_stage is None,
              repr(bot._state(ADMIN_CHAT).topup_stage))

        await say(bot, ADMIN_BUTTONS["finduser"])
        await say(bot, sid)
        found = "\n".join(fake.texts_to(ADMIN_CHAT))
        check("the find button reports the user without crediting",
              sid in found, found[-200:])
        check("and really credited nothing", await balance_of(uid) == 0,
              str(await balance_of(uid)))

        # A button tapped mid-flow must win over the step that is
        # waiting for text, or an admin who changes their mind is stuck.
        await say(bot, ADMIN_BUTTONS["credit"])
        await say(bot, ADMIN_BUTTONS["stats"])
        stats = "\n".join(fake.texts_to(ADMIN_CHAT))
        check("a button mid-flow is not read as a user id",
              "Статистика" in stats,
              stats[-160:])
    finally:
        bot._states.clear()
        await cleanup_user(uid)


async def main() -> int:
    await init_db()

    await test_amount_parsing()
    await test_find_user()
    await test_pick_from_several()
    await test_unknown_user_credits_nothing()
    await test_credit_end_to_end()
    await test_skip_the_comment()
    await test_double_tap_credits_once()
    await test_concurrent_confirmations()
    await test_cancel_credits_nothing()
    await test_stale_confirmation()
    await test_only_admins_can_credit()
    await test_ceiling_is_enforced_in_the_service()
    await test_missing_user_rolls_back()
    await test_notification_failure_keeps_the_credit()
    await test_transport_failure_is_retried()
    await test_unlinked_user_is_credited_anyway()
    await test_history_and_statistics()
    await test_teacher_sees_the_topup()
    await test_history_does_not_leak_across_users()
    await test_ledger_explains_the_balance()
    await test_buttons_reach_the_same_handlers()

    print()
    if FAIL:
        print(f"{len(FAIL)} FAILED:")
        for name in FAIL:
            print(f"  - {name}")
        return 1
    print("all top-up checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
