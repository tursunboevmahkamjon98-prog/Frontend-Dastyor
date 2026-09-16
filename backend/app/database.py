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
