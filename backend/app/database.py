import asyncio
from contextlib import asynccontextmanager
import secrets
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@asynccontextmanager
async def released(db: AsyncSession):
    await db.close()
    try:
        yield
    finally:
        pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await asyncio.wait_for(session.commit(), timeout=20.0)
        except Exception:
            await session.rollback()
            raise


async def init_db():
    from app import models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # payment_cards.card_number_encrypted needs pgp_sym_encrypt/
        # pgp_sym_decrypt (routers/admin_crm.py). This is also the only
        # statement in alembic/versions/..._enable_pgcrypto's upgrade() -
        # duplicated here, not moved here, because that migration's
        # body never runs on a brand-new database: app.db_bootstrap
        # stamps a fresh database straight to head (every table/column
        # alembic's other migrations would add already exists, freshly
        # made by create_all() above, so there is nothing safe left for
        # those migrations to actually run) and create_all() has no
        # equivalent of "CREATE EXTENSION" to fall back on. Idempotent
        # either way, so having it in both places costs nothing.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20)"
        ))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        await conn.execute(text(
            "ALTER TABLE users ALTER COLUMN email DROP NOT NULL"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"
        ))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_dirams INTEGER NOT NULL DEFAULT 0"
        ))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255)"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_id ON users (google_id)"
        ))
        for _col in ("free_konspekt_used", "free_lektsiya_used", "free_test_used", "free_prezentatsiya_used",
                    "free_amaliy_used", "free_igra_used"):
            await conn.execute(text(
                f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {_col} INTEGER NOT NULL DEFAULT 0"
            ))
            await conn.execute(text(f"""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'users'
                          AND column_name = '{_col}'
                          AND data_type = 'boolean'
                    ) THEN
                        ALTER TABLE users ALTER COLUMN {_col} DROP DEFAULT;
                        ALTER TABLE users ALTER COLUMN {_col} TYPE INTEGER
                            USING (CASE WHEN {_col} THEN 1 ELSE 0 END);
                        ALTER TABLE users ALTER COLUMN {_col} SET DEFAULT 0;
                    END IF;
                END $$;
            """))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS free_generation_used "
            "BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        await conn.execute(text(
            "UPDATE users SET free_generation_used = TRUE "
            "WHERE free_generation_used = FALSE AND ("
            " free_konspekt_used > 0 OR free_lektsiya_used > 0 OR free_test_used > 0"
            " OR free_prezentatsiya_used > 0 OR free_amaliy_used > 0 OR free_igra_used > 0)"
        ))
        for _type, _col in (
            ("konspekt", "free_konspekt_used"),
            ("lektsiya", "free_lektsiya_used"),
            ("test", "free_test_used"),
            ("prezentatsiya", "free_prezentatsiya_used"),
        ):
            await conn.execute(text(
                f"UPDATE users SET {_col} = 1 WHERE {_col} = 0 AND id IN ("
                " SELECT user_id FROM balance_transactions"
                " WHERE kind = 'free' AND material_type = :mtype)"
            ), {"mtype": _type})
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS short_id VARCHAR(6)"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_short_id ON users (short_id)"
        ))
        missing = (await conn.execute(text(
            "SELECT id FROM users WHERE short_id IS NULL"
        ))).scalars().all()
        if missing:
            existing = set((await conn.execute(text(
                "SELECT short_id FROM users WHERE short_id IS NOT NULL"
            ))).scalars().all())
            for user_id in missing:
                for _ in range(20):
                    candidate = f"{secrets.randbelow(1_000_000):06d}"
                    if candidate not in existing:
                        existing.add(candidate)
                        await conn.execute(
                            text("UPDATE users SET short_id = :sid WHERE id = :uid"),
                            {"sid": candidate, "uid": user_id},
                        )
                        break

        await conn.execute(text(
            "ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS user_agent TEXT"
        ))
        await conn.execute(text(
            "ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS login_at TIMESTAMPTZ NOT NULL DEFAULT now()"
        ))
        await conn.execute(text(
            "ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS platform VARCHAR(10) NOT NULL DEFAULT 'mobile'"
        ))
        await conn.execute(text(
            "ALTER TABLE qr_login_sessions ADD COLUMN IF NOT EXISTS browser_user_agent TEXT"
        ))
        await conn.execute(text(
            "ALTER TABLE tests ADD COLUMN IF NOT EXISTS time_limit_seconds INTEGER"
        ))

        for _table in ("konspekts", "lectures", "presentations", "tests",
                       "practical_tasks", "games"):
            await conn.execute(text(
                f"CREATE INDEX IF NOT EXISTS ix_{_table}_owner_created "
                f"ON {_table} (owner_id, created_at DESC)"
            ))

        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_rate_limit_purpose_key_created "
            "ON rate_limit_attempts (purpose, key, created_at DESC)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_admin_login_identifier_created "
            "ON admin_login_attempts (identifier, created_at DESC)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_test_attempts_test_user_created "
            "ON test_attempts (test_id, user_id, created_at DESC)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_game_attempts_game_user_score "
            "ON game_attempts (game_id, user_id, score DESC)"
        ))
        await conn.execute(text("DROP TABLE IF EXISTS curriculum_days CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS curriculums CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS wheel_questions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS wheels CASCADE"))

        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_balance_tx_user_created "
            "ON balance_transactions (user_id, created_at DESC)"
        ))

        # Telegram top-up columns on the existing ledger.
        for _col, _type in (
            ("actor_telegram_id", "BIGINT"),
            ("idempotency_key", "VARCHAR(64)"),
            ("public_code", "VARCHAR(20)"),
        ):
            await conn.execute(text(
                f"ALTER TABLE balance_transactions "
                f"ADD COLUMN IF NOT EXISTS {_col} {_type}"
            ))

        # The guarantee behind "pressing confirm twice credits once".
        # Partial, so the rows that predate this feature — and every
        # generation charge, which carries no key — do not all collide
        # on NULL.
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_balance_tx_idempotency "
            "ON balance_transactions (idempotency_key) "
            "WHERE idempotency_key IS NOT NULL"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_balance_tx_public_code "
            "ON balance_transactions (public_code) "
            "WHERE public_code IS NOT NULL"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_balance_tx_admin_created "
            "ON balance_transactions (actor_telegram_id, created_at DESC) "
            "WHERE actor_telegram_id IS NOT NULL"
        ))

        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_payment_requests_user_created "
            "ON payment_requests (user_id, created_at DESC)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_payment_requests_status_created "
            "ON payment_requests (status, created_at DESC)"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_requests_approved_reference "
            "ON payment_requests (reference_normalized) "
            "WHERE status = 'approved' AND reference_normalized IS NOT NULL"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_payment_audit_request_created "
            "ON payment_audit_log (payment_request_id, created_at)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_telegram_link_tokens_user_created "
            "ON telegram_link_tokens (user_id, created_at DESC)"
        ))

        # telegram_processed_updates was first created with update_id as
        # the sole primary key. That is wrong as soon as a second bot
        # exists: update ids are per-bot, so the admin bot's update 7
        # would be rejected as a duplicate of the user bot's update 7 and
        # the approval behind it would be silently dropped. Add the `bot`
        # column and widen the key.
        #
        # Rows already present predate the admin bot, so they are all
        # from the user bot and backfill to 'user'.
        # telegram_admins was first created keyed on telegram_user_id,
        # which made it impossible to grant admin to a Dastyor account
        # that had not linked Telegram yet — there was no key to store.
        # Re-key on a surrogate id so a grant can sit PENDING with a NULL
        # telegram_user_id and activate on link.
        await conn.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = 'telegram_admins'
                ) AND NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'telegram_admins' AND column_name = 'id'
                ) THEN
                    ALTER TABLE telegram_admins
                        DROP CONSTRAINT IF EXISTS telegram_admins_pkey;
                    ALTER TABLE telegram_admins
                        ADD COLUMN id VARCHAR(36);
                    UPDATE telegram_admins
                        SET id = gen_random_uuid()::text WHERE id IS NULL;
                    ALTER TABLE telegram_admins ALTER COLUMN id SET NOT NULL;
                    ALTER TABLE telegram_admins
                        ADD CONSTRAINT telegram_admins_pkey PRIMARY KEY (id);
                    ALTER TABLE telegram_admins
                        ALTER COLUMN telegram_user_id DROP NOT NULL;
                END IF;
            END $$;
        """))
        await conn.execute(text(
            "ALTER TABLE telegram_admins "
            "ADD COLUMN IF NOT EXISTS activated_at TIMESTAMPTZ"
        ))

        # Lets "/addadmin @username" resolve from our own records; the
        # Bot API cannot look a user up by username.
        await conn.execute(text(
            "ALTER TABLE telegram_accounts "
            "ADD COLUMN IF NOT EXISTS username VARCHAR(64)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_telegram_accounts_username "
            "ON telegram_accounts (username) WHERE username IS NOT NULL"
        ))

        # One active grant per Telegram id, and one per Dastyor account.
        # Partial so revoked rows stay as history and a pending grant
        # (NULL telegram id) does not collide with another pending one.
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_telegram_admins_active_tg "
            "ON telegram_admins (telegram_user_id) "
            "WHERE revoked = FALSE AND telegram_user_id IS NOT NULL"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_telegram_admins_active_user "
            "ON telegram_admins (user_id) "
            "WHERE revoked = FALSE AND user_id IS NOT NULL"
        ))

        await conn.execute(text(
            "ALTER TABLE telegram_processed_updates "
            "ADD COLUMN IF NOT EXISTS bot VARCHAR(20)"
        ))
        await conn.execute(text(
            "UPDATE telegram_processed_updates SET bot = 'user' WHERE bot IS NULL"
        ))
        await conn.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'telegram_processed_updates'
                      AND column_name = 'bot'
                      AND is_nullable = 'YES'
                ) THEN
                    ALTER TABLE telegram_processed_updates
                        ALTER COLUMN bot SET NOT NULL;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'telegram_processed_updates_pkey'
                      AND array_length(conkey, 1) = 1
                ) THEN
                    ALTER TABLE telegram_processed_updates
                        DROP CONSTRAINT telegram_processed_updates_pkey;
                    ALTER TABLE telegram_processed_updates
                        ADD CONSTRAINT telegram_processed_updates_pkey
                        PRIMARY KEY (bot, update_id);
                END IF;
            END $$;
        """))
