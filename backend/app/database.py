import asyncio
import secrets
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.config import get_settings

settings = get_settings()

# This project's venv is pinned to Python 3.13 (see README) specifically so
# asyncpg is always available — unlike the sibling Flutter-app backend, no
# psycopg/Python-3.14 fallback shim is needed here.
# Pool sizing is configuration, not a constant: the ceiling that matters
# is (pool_size + max_overflow) x worker processes <= PostgreSQL's
# max_connections. Hardcoding 5+10 means a two-worker deployment silently
# behaves differently from a six-worker one, and the six-worker one runs
# out of server connections under exactly the load the pool exists to
# survive.
#
# pool_timeout is the piece that was missing entirely. Without it,
# SQLAlchemy's default is to wait 30s for a connection — but with no
# explicit value the failure mode under saturation is a wall of requests
# all blocked on checkout with nothing in the logs saying so. Setting it
# explicitly makes exhaustion a fast, named error instead of a hang.
#
# pool_recycle closes connections before the idle timeouts that managed
# PostgreSQL services and connection poolers apply from their side —
# without it, the first query on a long-idle connection fails with a
# "server closed the connection unexpectedly" that pool_pre_ping then has
# to absorb on every request after a quiet period.
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


async def get_db():
    async with async_session() as session:
        try:
            yield session
            # Defensive timeout: the sibling backend hit a real driver hang on
            # commit() under a different Python/driver combo. Keeping the same
            # guard here costs nothing and turns any future recurrence into a
            # clean error instead of a silent freeze.
            await asyncio.wait_for(session.commit(), timeout=20.0)
        except Exception:
            await session.rollback()
            raise


async def init_db():
    # Imported for its side effect: a model class only registers itself on
    # Base.metadata when its module is executed, so create_all below sees
    # nothing unless app.models has been imported first. It normally has
    # been, because main.py imports it — but that makes correctness here
    # depend on an unrelated module's import order, and the failure is
    # silent: create_all simply creates fewer tables than it should, and
    # the first query against a missing one fails at runtime. Importing it
    # here makes init_db self-contained (and makes it callable from a
    # migration script or a test that doesn't go through main.py).
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # create_all only creates whole tables that don't exist yet — it
        # never ALTERs an existing one's columns. `users` already existed
        # in every deployed database before `phone`/`phone_verified` were
        # added to the User model (see models.py), so those columns need
        # to be added by hand here. No Alembic in this project; this is
        # the lightest mechanism that still works on both a fresh install
        # (columns already exist as part of create_all, so every statement
        # below is a no-op) and an existing database (columns get added
        # once, then every later startup is a no-op again thanks to
        # IF NOT EXISTS / the DO-block's existence check).
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
        # Per-type "free generation already used" flags — see models.py's
        # User docstring on why these replaced the old count==0 check.
        # Existing accounts get FALSE (never used their free one under the
        # new logic) rather than trying to backfill from current row
        # counts, which would've been wrong for anyone who'd already
        # deleted their first konspekt/test/etc.
        for _col in ("free_konspekt_used", "free_lektsiya_used", "free_test_used", "free_prezentatsiya_used",
                    "free_amaliy_used", "free_igra_used"):
            await conn.execute(text(
                f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {_col} INTEGER NOT NULL DEFAULT 0"
            ))
            # These were BOOLEAN ("this type's one freebie is spent") and
            # are counts now, so the allowance can be a setting instead of
            # the column type (see models.py and limits._claim_free).
            # Converted in place, TRUE becoming 1, so nobody gains or
            # loses a free generation at the moment of the change.
            #
            # Guarded on the CURRENT type rather than run unconditionally:
            # ALTER ... TYPE is not idempotent, and this runs on every
            # single startup. Reading information_schema is what makes a
            # second boot a no-op instead of an error that stops the app.
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
        # The single account-wide free generation (see app/limits.py).
        # Backfilled TRUE for anyone who had already spent ANY of the six
        # per-type free slots under the old rule — without that, the rule
        # change would silently hand a fresh freebie to every existing
        # account the moment this deployed.
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS free_generation_used "
            "BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        # "> 0", not a bare column name: these six are INTEGER counters
        # now (see the conversion above). Postgres will not accept an
        # integer where it wants a boolean, so left as it was this
        # statement raises at startup and the app never comes up.
        await conn.execute(text(
            "UPDATE users SET free_generation_used = TRUE "
            "WHERE free_generation_used = FALSE AND ("
            " free_konspekt_used > 0 OR free_lektsiya_used > 0 OR free_test_used > 0"
            " OR free_prezentatsiya_used > 0 OR free_amaliy_used > 0 OR free_igra_used > 0)"
        ))
        # ...and back the other way, because the rule is per-type again
        # (one free konspekt, lecture, test and presentation each — see
        # limits.FREE_SLOT_COLUMN).
        #
        # While the account-wide rule was live, spending the single
        # freebie set free_generation_used and left every per-type column
        # FALSE. Reading those columns again without this would hand each
        # of those accounts four fresh free materials. The ledger says
        # which type the freebie actually went on: reserve() writes a
        # kind='free' row carrying the material_type every time it claims
        # one, so replay those rows onto the matching column.
        #
        # Deliberately narrow — an account whose free row names a type
        # with no slot today ("amaliy", "igra"), or that predates the
        # ledger entirely, keeps its four slots. Being one material too
        # generous to a handful of early accounts is the better failure
        # than silently charging a teacher for something they were told
        # was free.
        for _type, _col in (
            ("konspekt", "free_konspekt_used"),
            ("lektsiya", "free_lektsiya_used"),
            ("test", "free_test_used"),
            ("prezentatsiya", "free_prezentatsiya_used"),
        ):
            # Counter semantics, same reason as above: mark one spent
            # (= 1) only where none is recorded yet (= 0), rather than
            # TRUE/FALSE against what is now an INTEGER column.
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
        # Backfill every pre-existing account right away instead of
        # waiting on app/auth.py's per-request lazy assignment (which only
        # fires for the account making the call) — an admin crediting a
        # user's balance needs that user's short_id to already be there,
        # not just whichever accounts happened to have logged in since
        # this shipped. No-op once every row already has one.
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

        # "Linked devices" feature (RefreshToken.user_agent/login_at/
        # platform, QrLoginSession.browser_user_agent) — refresh_tokens and
        # qr_login_sessions both already existed before these columns were
        # added to the models.
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
        # Online test-play (TestPlayer.tsx): per-question countdown a
        # teacher can set on an already-existing test. test_attempts itself
        # is a brand-new table, so create_all above already created it —
        # only this column on the pre-existing `tests` table needs the
        # manual ALTER.
        await conn.execute(text(
            "ALTER TABLE tests ADD COLUMN IF NOT EXISTS time_limit_seconds INTEGER"
        ))

        # ── Indexes for the queries that actually run ────────────────
        # Every material list endpoint filters by owner_id and orders by
        # created_at DESC. The model declares those as two SEPARATE
        # single-column indexes, which lets PostgreSQL use one of them —
        # it filters on owner_id, then sorts the result. That sort is the
        # cost, and it grows with how much one teacher owns. A composite
        # (owner_id, created_at DESC) index returns the rows already in
        # the required order, so the sort disappears and LIMIT can stop
        # early instead of reading every row the teacher owns.
        #
        # CREATE INDEX (not CONCURRENTLY): this runs inside init_db's
        # transaction, and CONCURRENTLY cannot run in one. These tables
        # are small enough at this scale that the brief lock on first
        # startup is not worth the extra machinery; IF NOT EXISTS makes
        # every later startup a no-op.
        for _table in ("konspekts", "lectures", "presentations", "tests",
                       "practical_tasks", "games"):
            await conn.execute(text(
                f"CREATE INDEX IF NOT EXISTS ix_{_table}_owner_created "
                f"ON {_table} (owner_id, created_at DESC)"
            ))

        # The throttles read (purpose, key, created_at >= cutoff) on the
        # hot path of every login and every generation. Separate indexes
        # on purpose and key each match only part of that; the composite
        # matches all of it.
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_rate_limit_purpose_key_created "
            "ON rate_limit_attempts (purpose, key, created_at DESC)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_admin_login_identifier_created "
            "ON admin_login_attempts (identifier, created_at DESC)"
        ))
        # Attempt history is always "this test/game, this user, newest
        # (or highest-scoring) first".
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_test_attempts_test_user_created "
            "ON test_attempts (test_id, user_id, created_at DESC)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_game_attempts_game_user_score "
            "ON game_attempts (game_id, user_id, score DESC)"
        ))
        # The curriculum feature was removed. Its two tables are dropped
        # here rather than left behind: they hold nothing anything reads
        # anymore, and a table whose model no longer exists is a trap for
        # the next person who goes looking for what writes to it.
        #
        # CASCADE because curriculum_days references curriculums; the
        # konspekts and tests those days pointed at are NOT touched, they
        # are ordinary materials owned by the teacher and simply appear in
        # the flat library now that nothing filters them out.
        await conn.execute(text("DROP TABLE IF EXISTS curriculum_days CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS curriculums CASCADE"))
        # The random wheel went the same way, for the same reason.
        await conn.execute(text("DROP TABLE IF EXISTS wheel_questions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS wheels CASCADE"))

        # The ledger is read as "this account's movements, newest first".
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_balance_tx_user_created "
            "ON balance_transactions (user_id, created_at DESC)"
        ))
