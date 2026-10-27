"""First-run helper for the Telegram payment bot.

Three things have to be true before the bot is useful, and two of them
are easy to get wrong by hand. This script checks and discovers them so
the operator only ever pastes the token.

    cd backend
    python scripts/telegram_bootstrap.py check
    python scripts/telegram_bootstrap.py whoami

``check``   - does the token work, what bot does it belong to, does
              TELEGRAM_BOT_USERNAME agree with it, and is an admin
              configured. Read-only: it calls getMe and nothing else, so
              it never touches the update queue or messages anybody.

``whoami``  - prints the numeric Telegram id of whoever next messages the
              bot. That number is what goes in TELEGRAM_ADMIN_IDS, and
              hunting for it via @userinfobot is the step people skip or
              get wrong (a @username is not an id and must not be used as
              one - usernames can be changed and re-registered).

``whoami`` deliberately does **not** confirm the polling offset. Telegram
only treats updates as delivered once you ask again past them, so the
message you identify yourself with is re-delivered to the real bot when
it starts, instead of being silently swallowed by this script.

The token is read from the environment or backend/.env.telegram and is
never printed. Only the bot id (the public half, before the colon) and
the @username appear in the output.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.telegram.api import (  # noqa: E402
    TelegramApiError,
    TelegramClient,
    TelegramTransportError,
    install_token_scrubber,
)
from app.telegram.config import get_telegram_settings  # noqa: E402

WHOAMI_TIMEOUT_SECONDS = 180


def _fail(message: str) -> int:
    print(f"\n  PROBLEM  {message}")
    return 1


async def cmd_check() -> int:
    settings = get_telegram_settings()
    print("Telegram payment bot - configuration check")
    print(f"  config: {settings.redacted()}")
    print()

    if not settings.TELEGRAM_BOT_TOKEN:
        return _fail(
            "TELEGRAM_BOT_TOKEN is not set.\n"
            "           Create backend/.env.telegram from "
            ".env.telegram.example and paste the\n"
            "           token from @BotFather into it. That file is "
            "gitignored; do not put\n"
            "           the token in .env, which this repository commits."
        )

    client = TelegramClient()
    try:
        me = await client.get_me()
    except TelegramApiError as e:
        if e.status in (401, 404):
            return _fail(
                f"Telegram rejected the token (HTTP {e.status}).\n"
                "           It is wrong, or it was revoked. Revoking in "
                "@BotFather invalidates\n"
                "           the old token immediately - if you revoked, "
                "paste the NEW one."
            )
        return _fail(f"getMe failed: {e}")
    except TelegramTransportError as e:
        return _fail(f"Could not reach api.telegram.org: {e}")
    finally:
        await client.aclose()

    username = me.get("username") or ""
    print(f"  token works. It belongs to @{username} (bot id {me.get('id')}).")

    problems = []

    if not settings.TELEGRAM_BOT_USERNAME:
        problems.append(
            f"TELEGRAM_BOT_USERNAME is not set. Set it to: {username}\n"
            "           The app builds its deep link from this value."
        )
    elif settings.TELEGRAM_BOT_USERNAME.lower() != username.lower():
        problems.append(
            f"TELEGRAM_BOT_USERNAME is "
            f"{settings.TELEGRAM_BOT_USERNAME!r} but the token belongs to "
            f"@{username}.\n"
            "           Every deep link the app hands out would open the "
            "wrong bot."
        )
    else:
        print("  TELEGRAM_BOT_USERNAME matches the token.")

    # The review bot, if the owner split it out.
    if settings.has_separate_admin_bot:
        admin_client = TelegramClient(settings.TELEGRAM_ADMIN_BOT_TOKEN)
        try:
            admin_me = await admin_client.get_me()
        except TelegramApiError as e:
            problems.append(
                f"the ADMIN bot token was rejected (HTTP {e.status}). "
                "Check TELEGRAM_ADMIN_BOT_TOKEN."
            )
            admin_me = {}
        except TelegramTransportError as e:
            problems.append(f"could not reach the admin bot: {e}")
            admin_me = {}
        finally:
            await admin_client.aclose()

        admin_username = admin_me.get("username")
        if admin_username:
            if admin_username.lower() == username.lower():
                problems.append(
                    "TELEGRAM_ADMIN_BOT_TOKEN belongs to the SAME bot as "
                    "the user token.\n"
                    "           Two pollers on one bot fight over "
                    "getUpdates and Telegram 409s one of\n"
                    "           them. Create a second bot in @BotFather, "
                    "or leave the variable empty."
                )
            else:
                print(f"  admin reviews go to @{admin_username} "
                      f"(separate bot).")
    elif settings.TELEGRAM_ADMIN_BOT_TOKEN.strip():
        problems.append(
            "TELEGRAM_ADMIN_BOT_TOKEN is set to the same value as "
            "TELEGRAM_BOT_TOKEN and is being ignored."
        )
    else:
        print(
            "  NOTE   no separate admin bot. Reviews are sent to the admin "
            "ids through the\n"
            "         public bot, which works but puts the approve/reject "
            "buttons in the same\n"
            "         bot teachers use. Set TELEGRAM_ADMIN_BOT_TOKEN to a "
            "second @BotFather bot\n"
            "         to split them."
        )

    if not settings.admin_ids:
        problems.append(
            "TELEGRAM_ADMIN_IDS is empty, so no payment could ever be "
            "approved.\n"
            "           Run:  python scripts/telegram_bootstrap.py whoami\n"
            "           then message the bot to learn your numeric id."
        )
    else:
        print(f"  {len(settings.admin_ids)} administrator id(s) configured.")
        print(f"  admin messages are in: {settings.TELEGRAM_ADMIN_LANGUAGE}")

    if not settings.TELEGRAM_PAY_INSTRUCTIONS.strip():
        print(
            "  NOTE   TELEGRAM_PAY_INSTRUCTIONS is empty. The bot will "
            "start, but /pay will\n"
            "         tell teachers it is not configured rather than "
            "inventing account\n"
            "         details. Write the real transfer instructions before "
            "announcing it."
        )
    else:
        print("  payment instructions configured.")

    if not settings.TELEGRAM_PAY_RECIPIENT.strip():
        print(
            "  NOTE   TELEGRAM_PAY_RECIPIENT is empty, so receipts cannot "
            "be checked against\n"
            "         the expected recipient. Approval still works; the "
            "admin just loses one\n"
            "         automatic warning."
        )

    if problems:
        print()
        for problem in problems:
            print(f"  PROBLEM  {problem}")
        return 1

    print()
    print("  ready. Start the bot with:  python -m app.telegram.bot")
    return 0


async def cmd_whoami() -> int:
    settings = get_telegram_settings()
    if not settings.TELEGRAM_BOT_TOKEN:
        return _fail("TELEGRAM_BOT_TOKEN is not set.")

    # Listen on the ADMIN bot when one exists: the id being discovered
    # goes into TELEGRAM_ADMIN_IDS, which is what the admin bot checks,
    # and the admin is the person who will actually message it.
    if settings.has_separate_admin_bot:
        client = TelegramClient(settings.TELEGRAM_ADMIN_BOT_TOKEN)
        print("(listening on the ADMIN bot)")
    else:
        client = TelegramClient()
    try:
        try:
            me = await client.get_me()
        except (TelegramApiError, TelegramTransportError) as e:
            return _fail(f"could not reach the bot: {e}")

        print(f"Listening as @{me.get('username')}.")
        print()
        print("  Open Telegram, find that bot, and send it any message")
        print("  (/start is fine). The numeric id printed below is what "
              "goes into")
        print("  TELEGRAM_ADMIN_IDS.")
        print()
        print(f"  Waiting up to {WHOAMI_TIMEOUT_SECONDS}s. Ctrl-C to stop.")
        print()

        waited = 0
        seen: set[int] = set()
        while waited < WHOAMI_TIMEOUT_SECONDS:
            try:
                # offset 0 = "give me what you have, and do not treat
                # anything as delivered". Nothing is confirmed, so the
                # real bot still receives these updates later.
                updates = await client.get_updates(0, 10)
            except (TelegramApiError, TelegramTransportError) as e:
                print(f"  poll failed, retrying: {e}")
                await asyncio.sleep(3)
                waited += 3
                continue

            for update in updates:
                message = update.get("message") or {}
                sender = message.get("from") or {}
                chat = message.get("chat") or {}
                user_id = sender.get("id")
                if user_id is None or user_id in seen:
                    continue
                seen.add(user_id)
                name = sender.get("first_name") or ""
                handle = sender.get("username")
                print(f"  MESSAGE from {name}"
                      + (f" (@{handle})" if handle else ""))
                print(f"      numeric telegram id : {user_id}")
                print(f"      chat id             : {chat.get('id')}")
                print()
                print("  Put this in backend/.env.telegram:")
                print(f"      TELEGRAM_ADMIN_IDS={user_id}")
                print()
                print("  Nothing was consumed - the real bot will still see "
                      "this message.")
                return 0

            waited += 10

        return _fail(
            "no message arrived in time. Run it again and send the bot a "
            "message while it waits."
        )
    finally:
        await client.aclose()


def main() -> int:
    install_token_scrubber()
    command = (sys.argv[1] if len(sys.argv) > 1 else "check").lower()
    if command == "check":
        return asyncio.run(cmd_check())
    if command == "whoami":
        return asyncio.run(cmd_whoami())
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
