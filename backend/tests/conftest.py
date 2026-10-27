"""Shared pytest setup for backend/tests/*.

This project's existing integration tests (test_telegram_payments.py and
friends) are standalone scripts, each repeating the same few lines at the
top: point DATABASE_URL/DATABASE_URL_SYNC at a dedicated test database
*before* anything imports app.database (which builds its engine at
import time), create that database if it doesn't exist yet, then bring
its schema up to date.

New tests written against pytest should not have to repeat that dance in
every file — this conftest.py does it once, at collection time, the same
way the standalone scripts do it at their own import time. The two
conventions share one database (dastyor_bot_test by default, override via
TELEGRAM_TEST_DATABASE) and one schema-bootstrap path, so running both
the old scripts and `pytest backend/tests/` against the same running
Postgres never fights over what state the test database should be in.

Nothing here reaches a real Telegram server or OCR binary, and nothing
here touches the development database — only the test one.
"""

import asyncio
import functools
import os
import re
import sys
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import dotenv_values  # noqa: E402

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env = dotenv_values(os.path.join(_BACKEND_DIR, ".env"))

_TEST_DB = os.environ.get("TELEGRAM_TEST_DATABASE", "dastyor_bot_test")


def _swap_database(url: str, name: str) -> str:
    head, _, _ = url.rpartition("/")
    return f"{head}/{name}"


_async_url = os.environ.get("DATABASE_URL") or _env.get("DATABASE_URL")
_sync_url = os.environ.get("DATABASE_URL_SYNC") or _env.get("DATABASE_URL_SYNC")

if not _async_url or not _sync_url:
    print("DATABASE_URL/DATABASE_URL_SYNC not set and backend/.env has "
          "none - cannot run integration tests", file=sys.stderr)
    raise SystemExit(2)

if (not re.fullmatch(r"[a-z][a-z0-9_]{2,62}", _TEST_DB)
        or ("test" not in _TEST_DB and "_it_" not in _TEST_DB)
        or _TEST_DB in {urlsplit(_async_url).path.rsplit("/", 1)[-1],
                        urlsplit(_sync_url).path.rsplit("/", 1)[-1], "postgres"}
        or urlsplit(_async_url).hostname not in {"localhost", "127.0.0.1", "::1"}):
    raise SystemExit("Refusing tests: a distinct, local test database is required")

os.environ["DATABASE_URL"] = _swap_database(_async_url, _TEST_DB)
os.environ["DATABASE_URL_SYNC"] = _swap_database(_sync_url, _TEST_DB)
os.environ["SECRET_KEY"] = "isolated-test-secret"
os.environ["AI_API_KEY"] = "isolated-test-ai-disabled"
os.environ["CARD_ENCRYPTION_KEY"] = "isolated-test-card-encryption-key-not-for-production"

# Same dummy-but-valid bot config the standalone telegram tests use —
# harmless here even for tests that never touch the bot, and keeps every
# test in this directory free to assume TelegramSettings() won't explode.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "1111111111:TESTTESTTESTTESTTESTTESTTESTTESTTEST")
os.environ.setdefault("TELEGRAM_BOT_USERNAME", "dastyor_test_bot")
os.environ.setdefault("TELEGRAM_ADMIN_IDS", "5001,5002")
os.environ.setdefault("TELEGRAM_PAY_INSTRUCTIONS", "TEST ONLY - no real account details.")
os.environ.setdefault("TELEGRAM_PAY_RECIPIENT", "DASTYOR LLC")
os.environ.setdefault("TELEGRAM_LINK_TOKEN_TTL_SECONDS", "600")

_ASYNCPG_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")

# Only the database connection is borrowed from .env. Loading the full file
# into Settings can import unrelated live credentials or reject extra keys.
from app.config import Settings  # noqa: E402
Settings.model_config = {**Settings.model_config, "env_file": None}


async def _ensure_database() -> None:
    import asyncpg

    admin_url = _swap_database(_ASYNCPG_URL, "postgres")
    conn = await asyncpg.connect(admin_url)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", _TEST_DB
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{_TEST_DB}"')
    finally:
        await conn.close()


asyncio.run(_ensure_database())

from app.database import engine, init_db  # noqa: E402
from app import db_bootstrap  # noqa: E402

# db_bootstrap FIRST, THEN init_db() — same order as entrypoint.sh runs
# them in the actual container (db_bootstrap, then uvicorn's lifespan
# calling init_db()). Getting this backwards is not a style choice:
# init_db()'s create_all() creates any brand-new table straight from
# models.py (payment_cards, expenses, ...), and a migration that ALSO
# tries to create that same table (op.create_table) collides with it —
# "relation already exists" — the moment it runs after create_all
# already has. Migrations for brand-new tables rely on create_all to
# make the table at all; they only add what create_all cannot
# (extensions, check constraints, columns on tables that already
# existed). Running them in the wrong order here would hide that class
# of bug in every test, right up until the real deploy order breaks.
db_bootstrap.run()


async def _bootstrap_schema() -> None:
    await init_db()
    # Disposes the connections init_db() just opened, in the SAME loop
    # that's about to close. Skipping this leaves them pooled on
    # app.database.engine; the first test's own asyncio.run() (see
    # async_test below) opens a NEW event loop, and Windows'
    # ProactorEventLoop breaks the moment one of those stale pooled
    # connections gets reused under it.
    await engine.dispose()


asyncio.run(_bootstrap_schema())

def async_test(fn):
    """Run an async test body under pytest without the pytest-asyncio
    plugin — this project otherwise has no async-test dependency, and
    one coroutine per test via asyncio.run() is all that's needed.

    Disposes app.database's async engine at the end of every test, in
    the SAME loop asyncio.run() is about to close. Without this, the
    engine's asyncpg connections stay pooled across tests; the next
    test's asyncio.run() opens a brand new event loop, and Windows'
    ProactorEventLoop breaks the moment a connection opened under the
    old loop is reused under the new one ("'NoneType' object has no
    attribute 'send'", from a torn-down proactor). Disposing forces
    each test's connections to be opened fresh, inside its own loop.

    Usage: decorate an `async def test_...()` with @async_test instead
    of @pytest.mark.asyncio.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        async def _runner():
            try:
                return await fn(*args, **kwargs)
            finally:
                from app.database import engine
                await engine.dispose()

        return asyncio.run(_runner())

    return wrapper


# These predate pytest in this project and are standalone scripts, not
# pytest modules — each drives its own asyncio.run() at import time
# (`python tests/test_X.py`), which pytest's own collection/import
# machinery does not run the same way (importing rather than executing
# as __main__ breaks their event-loop setup on Windows). Keep running
# them exactly as documented in TELEGRAM_BOT.md; pytest only collects
# genuinely new test modules written for pytest.
collect_ignore = [
    "test_api_guards.py",
    "test_limits.py",
    "test_presentation_templates.py",
    "test_quality_gate.py",
    "test_startup_assets.py",
    "test_teacher_flow.py",
    "test_telegram_payments.py",
    "test_telegram_topup.py",
    "test_telegram_unit.py",
    "test_topic_guard.py",
]
