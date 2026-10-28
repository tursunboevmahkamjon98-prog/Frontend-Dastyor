"""Read-only startup checks. Output contains names and statuses, never values."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.config import get_settings

BACKEND = Path(__file__).resolve().parent.parent
BOT_FIELDS = ("DASTYOR_BOT_API_TOKEN", "DASTYOR_BOT_ROOT_ADMIN_ID",
              "DASTYOR_STANDALONE_BOT_USERNAME", "DASTYOR_STANDALONE_TELEGRAM_TOKEN")

LEGACY_BASELINE_COLUMNS = {
    "users": {"id", "full_name", "hashed_password", "role", "created_at"},
    "telegram_admins": {"id", "telegram_user_id", "added_at", "revoked"},
    "payment_requests": {
        "id", "public_code", "user_id", "chat_id", "requested_dirams",
        "status", "created_at",
    },
}
POST_BASELINE_COLUMNS = {
    "users": {"admin_tier"},
    "telegram_admins": {"reviewed_at"},
    "payment_requests": {
        "client_request_key", "receipt_kind", "standalone_notification_sent_at",
    },
}


class ConfigurationError(RuntimeError):
    pass


def validate_backend_config(settings, *, require_bot: bool = False) -> None:
    errors = []
    for field in ("DATABASE_URL", "DATABASE_URL_SYNC", "SECRET_KEY", "AI_API_KEY"):
        if not str(getattr(settings, field, "")).strip():
            errors.append(field)
    try:
        asynchronous = make_url(settings.DATABASE_URL)
        synchronous = make_url(settings.DATABASE_URL_SYNC)
        if asynchronous.drivername not in ("postgresql+asyncpg", "postgresql+psycopg"):
            errors.append("DATABASE_URL (async PostgreSQL driver required)")
        if synchronous.drivername not in ("postgresql", "postgresql+psycopg2", "postgresql+psycopg"):
            errors.append("DATABASE_URL_SYNC (sync PostgreSQL driver required)")
        def target(url):
            return (url.host, url.port or 5432, url.database, url.username, url.password)
        if target(asynchronous) != target(synchronous):
            errors.append("DATABASE_URL/DATABASE_URL_SYNC (targets or credentials differ)")
        if not asynchronous.host or not asynchronous.database or not asynchronous.username:
            errors.append("DATABASE_URL/DATABASE_URL_SYNC (incomplete connection)")
    except Exception:
        errors.append("DATABASE_URL/DATABASE_URL_SYNC (invalid URL)")
    bot_enabled = require_bot or any(getattr(settings, key, None) for key in BOT_FIELDS)
    if bot_enabled:
        if len(settings.DASTYOR_BOT_API_TOKEN.strip()) < 32:
            errors.append("DASTYOR_BOT_API_TOKEN (at least 32 characters)")
        if settings.DASTYOR_BOT_ROOT_ADMIN_ID <= 0:
            errors.append("DASTYOR_BOT_ROOT_ADMIN_ID")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", settings.DASTYOR_STANDALONE_BOT_USERNAME.lstrip("@")):
            errors.append("DASTYOR_STANDALONE_BOT_USERNAME")
        if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{30,}", settings.DASTYOR_STANDALONE_TELEGRAM_TOKEN):
            errors.append("DASTYOR_STANDALONE_TELEGRAM_TOKEN")
        if settings.DASTYOR_BOT_API_TOKEN and settings.DASTYOR_BOT_API_TOKEN == settings.DASTYOR_STANDALONE_TELEGRAM_TOKEN:
            errors.append("DASTYOR_BOT_API_TOKEN (must differ from Telegram token)")
    if errors:
        raise ConfigurationError("Configuration errors: " + "; ".join(errors))


def migration_scripts() -> ScriptDirectory:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    scripts = ScriptDirectory.from_config(config)
    if len(scripts.get_heads()) != 1:
        raise ConfigurationError("Alembic must have exactly one head")
    return scripts


def database_report(settings, *, require_current: bool = True,
                    allow_legacy_baseline: bool = False) -> dict:
    """Inspect the configured DB in a READ ONLY transaction. Never run DDL."""
    validate_backend_config(settings)
    scripts = migration_scripts()
    head = scripts.get_current_head()
    engine = create_engine(settings.DATABASE_URL_SYNC, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection, connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text("SET LOCAL statement_timeout = '5000ms'"))
            connection.execute(text("SELECT 1"))
            inspector = inspect(connection)
            tables = set(inspector.get_table_names())
            current = MigrationContext.configure(connection).get_current_heads()
            if len(current) > 1:
                raise ConfigurationError("Database has multiple Alembic revisions; migration review required")
            if not current:
                if "users" in tables:
                    if not allow_legacy_baseline:
                        raise ConfigurationError("Existing database has no Alembic revision; baseline audit required")
                    for table, required_columns in LEGACY_BASELINE_COLUMNS.items():
                        if table not in tables:
                            raise ConfigurationError(f"Legacy baseline audit failed: missing table {table}")
                        actual_columns = {c["name"] for c in inspector.get_columns(table)}
                        missing = required_columns - actual_columns
                        if missing:
                            raise ConfigurationError(
                                f"Legacy baseline audit failed: {table} missing columns "
                                + ", ".join(sorted(missing))
                            )
                        unexpected_new = POST_BASELINE_COLUMNS[table] & actual_columns
                        if unexpected_new:
                            raise ConfigurationError(
                                f"Legacy baseline audit failed: {table} has unversioned post-baseline columns "
                                + ", ".join(sorted(unexpected_new))
                            )
                    return {"database": "legacy", "revision": None,
                            "head": head, "pending": True}
                if tables - {"alembic_version"}:
                    raise ConfigurationError("Unversioned non-empty database; schema audit required")
                if require_current:
                    raise ConfigurationError("Empty database; run python -m app.db_bootstrap first")
                return {"database": "empty", "revision": None, "head": head, "pending": True}
            revision = current[0]
            try:
                scripts.get_revision(revision)
                applied = {item.revision for item in scripts.iterate_revisions(revision, "base")}
                pending = list(scripts.iterate_revisions(head, revision))
            except Exception:
                raise ConfigurationError("Database revision is unknown or not an ancestor of head") from None
            # Protect against a prior stamp hiding missing columns, or manual DDL
            # that would collide with the additive migrations on the next start.
            markers = {
                "6084e6741bb1": (("users", "admin_tier"),),
                "41caac9563f9": (("telegram_admins", "reviewed_at"),),
                "9e21b0d7c4a1": (("payment_requests", "client_request_key"),
                                   ("payment_requests", "receipt_kind"),
                                   ("standalone_bot_admins", "telegram_user_id")),
                "a41d8e7c2b90": (("payment_requests", "standalone_notification_sent_at"),),
            }
            for change, columns in markers.items():
                for table, column in columns:
                    present = table in tables and column in {c["name"] for c in inspector.get_columns(table)}
                    # init_db/create_all may already have created this new
                    # table while the older revision was still stamped.
                    if present and change not in applied and table == "standalone_bot_admins":
                        columns_by_name = {c["name"]: c for c in inspector.get_columns(table)}
                        if (set(columns_by_name) != {"telegram_user_id", "granted_by_telegram_id", "granted_at"}
                                or inspector.get_pk_constraint(table)["constrained_columns"] != ["telegram_user_id"]
                                or any(columns_by_name[k]["nullable"] for k in columns_by_name)
                                or any(str(columns_by_name[k]["type"]) != "BIGINT" for k in ("telegram_user_id", "granted_by_telegram_id"))
                                or not getattr(columns_by_name["granted_at"]["type"], "timezone", False)):
                            raise ConfigurationError("Existing standalone_bot_admins table is incompatible with migration")
                        continue
                    if present != (change in applied):
                        raise ConfigurationError(f"Schema differs from Alembic history: {table}.{column}; manual review required")
            if pending and require_current:
                raise ConfigurationError("Pending Alembic migrations; run python -m app.db_bootstrap before starting")
            if pending:
                if not connection.execute(text("SELECT has_schema_privilege(current_user, current_schema(), 'CREATE')")).scalar():
                    raise ConfigurationError("Database role lacks schema CREATE permission for migrations")
                if "payment_requests" in tables and not connection.execute(text(
                        "SELECT pg_has_role(current_user, relowner, 'USAGE') FROM pg_class WHERE oid = 'payment_requests'::regclass")).scalar():
                    raise ConfigurationError("Database role cannot ALTER payment_requests for migrations")
                if not connection.execute(text("SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name='pgcrypto')")).scalar():
                    raise ConfigurationError("PostgreSQL pgcrypto extension is unavailable")
            return {"database": "reachable", "revision": revision, "head": head,
                    "pending": bool(pending)}
    except ConfigurationError:
        raise
    except Exception:
        raise ConfigurationError("Database check failed; verify DATABASE_URL_SYNC, PostgreSQL availability and permissions") from None
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-bot", action="store_true")
    parser.add_argument("--database", action="store_true")
    parser.add_argument("--allow-pending-migrations", action="store_true")
    args = parser.parse_args()
    try:
        settings = get_settings()
        validate_backend_config(settings, require_bot=args.require_bot)
        print("Backend configuration: OK")
        if args.database:
            result = database_report(settings, require_current=not args.allow_pending_migrations)
            print("Database:", result["database"])
            print("Alembic current:", result["revision"] or "empty")
            print("Alembic head:", result["head"])
            print("Pending migrations:", "yes" if result["pending"] else "no")
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
