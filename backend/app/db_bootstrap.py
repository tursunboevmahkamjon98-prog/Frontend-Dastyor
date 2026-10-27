"""Initialize an empty DB or upgrade a versioned DB after read-only checks.

The container entrypoint and Windows launcher both use this module.
An existing unversioned or inconsistent database is rejected for an audit;
it must never be stamped at head without running its missing migrations.
A fresh database is stamped only after successful schema initialization.
"""

import asyncio
from pathlib import Path

from alembic.command import stamp, upgrade
from alembic.config import Config

from app.config import get_settings
from app.logger import get_logger, install_secret_redaction
from app.preflight import database_report

logger = get_logger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent


def _alembic_config() -> Config:
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    return cfg


def run() -> None:
    install_secret_redaction()
    settings = get_settings()
    report = database_report(settings, require_current=False)
    cfg = _alembic_config()
    if report["revision"]:
        logger.info("db_bootstrap: alembic_version present, running upgrade head")
        upgrade(cfg, "head")
        return
    # Do not stamp an empty database ahead of successful initialization.
    # Legacy unversioned databases are rejected by database_report.
    from app.database import engine, init_db
    async def initialize():
        try:
            await init_db()
        finally:
            await engine.dispose()
    asyncio.run(initialize())
    logger.info("db_bootstrap: fresh database initialized, stamping head")
    stamp(cfg, "head")


if __name__ == "__main__":
    try:
        run()
    except Exception:
        raise SystemExit("Database bootstrap failed. Run python -m app.preflight --database --allow-pending-migrations for a safe diagnostic.") from None
