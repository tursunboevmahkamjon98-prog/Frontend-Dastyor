"""Startup-safety checks for the Telegram bot - pytest, no network, no DB.

Covers the "one token, one poller" requirement: if TELEGRAM_ADMIN_BOT_TOKEN
is ever set to the exact same value as TELEGRAM_BOT_TOKEN (copy-paste
mistake), the bot must not open a second long-poll loop against the same
bot - two pollers on one token fight over getUpdates and Telegram 409s
one of them, and every teacher would get every message twice.

Also checks the actual deploy wiring (docker-compose.yml) rather than
just the Python-side guard, since that is the other way a second
poller could appear: scaling the telegram-bot service, or it starting
by accident under a plain `docker compose up -d --build`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.telegram.config import TelegramSettings  # noqa: E402


def _settings(**overrides) -> TelegramSettings:
    base = dict(
        TELEGRAM_BOT_TOKEN="111:AAA-user-token",
        TELEGRAM_BOT_USERNAME="dastyor_bot",
        TELEGRAM_ADMIN_IDS="5001",
        TELEGRAM_PAY_INSTRUCTIONS="card 1234",
    )
    base.update(overrides)
    return TelegramSettings(**base)


def test_same_token_for_both_bots_is_not_treated_as_separate():
    settings = _settings(TELEGRAM_ADMIN_BOT_TOKEN="111:AAA-user-token")
    assert settings.has_separate_admin_bot is False, (
        "an identical admin token must fall back to single-bot mode, "
        "never open a second poller against the same bot"
    )


def test_a_genuinely_different_admin_token_is_recognized():
    settings = _settings(TELEGRAM_ADMIN_BOT_TOKEN="222:BBB-admin-token")
    assert settings.has_separate_admin_bot is True


def test_empty_admin_token_is_single_bot_mode():
    settings = _settings(TELEGRAM_ADMIN_BOT_TOKEN="")
    assert settings.has_separate_admin_bot is False


def test_bootstrap_check_flags_the_same_token_mistake():
    import scripts.telegram_bootstrap as bootstrap

    settings = _settings(TELEGRAM_ADMIN_BOT_TOKEN="111:AAA-user-token")

    class _FakeClient:
        def __init__(self, token=None, **kw):
            pass

        async def get_me(self):
            return {"id": 1, "username": "dastyor_bot"}

        async def aclose(self):
            pass

    import asyncio

    original_get_settings = bootstrap.get_telegram_settings
    original_client = bootstrap.TelegramClient
    bootstrap.get_telegram_settings = lambda: settings
    bootstrap.TelegramClient = _FakeClient
    try:
        rc = asyncio.run(bootstrap.cmd_check())
    finally:
        bootstrap.get_telegram_settings = original_get_settings
        bootstrap.TelegramClient = original_client

    assert rc == 1, "the same-token mistake must fail the check, not pass silently"


def test_compose_starts_the_bot_with_the_default_up_and_no_extra_file():
    # Parsed as text, not via PyYAML, so this test does not pull in a
    # dependency the Docker image never installs (PyYAML is only on this
    # dev machine transitively, via uvicorn/pydantic-settings extras).
    #
    # 2026-10-24: this service used to be behind `profiles: ["telegram"]`
    # and read a second, gitignored env_file - safer, but it assumed a
    # deploy path that could run an extra compose command and write a
    # second file to the server. The only path actually available is
    # `git pull` + the one default `docker compose up -d --build`, so
    # the bot now has to start with that alone, config included.
    compose_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..",
        "docker-compose.yml",
    )
    with open(compose_path, encoding="utf-8") as f:
        text = f.read()

    start = text.index("telegram-bot:")
    end = text.find("\nvolumes:", start)
    block_lines = [
        line for line in text[start:end if end != -1 else len(text)].splitlines()
        if not line.strip().startswith("#")
    ]
    block = "\n".join(block_lines)

    assert "profiles:" not in block, (
        "a plain `docker compose up -d --build` must start the bot too - "
        "there is no other deploy step available to gate it behind"
    )
    assert ".env.telegram" not in block, (
        "the server cannot have this gitignored file written to it, so "
        "the service must not depend on it existing"
    )
    assert "deploy:" not in block, (
        "no replica/scale config - exactly one poller is load-bearing, "
        "not just a convention"
    )
    assert "ports:" not in block, (
        "the bot only makes outbound calls; it must not publish a port"
    )
