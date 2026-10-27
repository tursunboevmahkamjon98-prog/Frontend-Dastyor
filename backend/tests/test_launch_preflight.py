"""Launch checks and migrations, using only the isolated test database."""
import importlib.util
import io
import logging
import uuid
from pathlib import Path

import httpx
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from PIL import Image
from sqlalchemy import create_engine, inspect, text
from fastapi import HTTPException

from conftest import async_test
from app.config import get_settings
from app.logger import RedactingFormatter
from app.preflight import ConfigurationError, database_report, validate_backend_config
from app.routers import bot_api


def test_configuration_errors_never_contain_values():
    settings = get_settings().model_copy(update={
        "DATABASE_URL_SYNC": "postgresql://secret_user:DO_NOT_PRINT@elsewhere/test_only",
        "DASTYOR_BOT_API_TOKEN": "SHORT_PRIVATE_VALUE",
    })
    with pytest.raises(ConfigurationError) as raised:
        validate_backend_config(settings, require_bot=True)
    message = str(raised.value)
    assert "DATABASE_URL" in message and "DASTYOR_BOT_API_TOKEN" in message
    assert "DO_NOT_PRINT" not in message and "SHORT_PRIVATE_VALUE" not in message
    assert "DO_NOT_PRINT" not in repr(settings)
    assert "SHORT_PRIVATE_VALUE" not in str(settings)


def test_database_preflight_matches_current_schema():
    report = database_report(get_settings())
    assert report["database"] == "reachable"
    assert report["revision"] == report["head"]
    assert not report["pending"]


def test_migrations_preserve_precreated_admin_table(monkeypatch):
    # All DDL is inside a rollback-only transaction in the isolated test DB.
    engine = create_engine(get_settings().DATABASE_URL_SYNC)
    schema = "launch_check_" + uuid.uuid4().hex
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                connection.execute(text("CREATE TABLE payment_requests (id varchar(36) PRIMARY KEY)"))
                connection.execute(text("CREATE TABLE standalone_bot_admins (telegram_user_id bigint PRIMARY KEY, granted_by_telegram_id bigint NOT NULL, granted_at timestamptz NOT NULL)"))
                connection.execute(text("INSERT INTO standalone_bot_admins VALUES (100, 200, now())"))
                context = MigrationContext.configure(connection)
                for filename in ("9e21b0d7c4a1_standalone_bot_api.py", "a41d8e7c2b90_standalone_bot_notifications.py"):
                    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / filename
                    spec = importlib.util.spec_from_file_location("migration_under_test", path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    monkeypatch.setattr(module, "op", Operations(context))
                    module.upgrade()
                assert connection.execute(text("SELECT count(*) FROM standalone_bot_admins")).scalar_one() == 1
                columns = {c["name"] for c in inspect(connection).get_columns("payment_requests", schema=schema)}
                assert {"client_request_key", "receipt_kind", "standalone_notification_sent_at"} <= columns
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def test_backend_log_redacts_tokens(monkeypatch):
    secret = "sensitive-service-token-for-test-only"
    monkeypatch.setattr(get_settings(), "DASTYOR_BOT_API_TOKEN", secret)
    token = "123456:" + "A" * 36
    record = logging.LogRecord("check", logging.ERROR, "", 0,
        f"request failed https://api.telegram.org/bot{token}/getFile {secret}", (), None)
    rendered = RedactingFormatter().format(record)
    assert secret not in rendered and token not in rendered


@async_test
async def test_receipt_bytes_are_validated_without_telegram(monkeypatch):
    monkeypatch.setattr(get_settings(), "DASTYOR_STANDALONE_TELEGRAM_TOKEN", "123456:" + "A" * 36)
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, "PNG")
    payload = buffer.getvalue()
    def handler(request):
        if request.url.path.endswith("/getFile"):
            return httpx.Response(200, json={"ok": True, "result": {"file_path": "photos/test.png", "file_size": len(payload)}})
        return httpx.Response(200, content=payload)
    client_class = httpx.AsyncClient
    monkeypatch.setattr(bot_api.httpx, "AsyncClient", lambda **kwargs: client_class(transport=httpx.MockTransport(handler), **kwargs))
    assert await bot_api.verify_receipt("file-id", "image/png", "photo") == len(payload)
    payload = b"invalid image"
    with pytest.raises(HTTPException) as invalid:
        await bot_api.verify_receipt("file-id", "image/png", "photo")
    assert invalid.value.status_code == 422
    assert "123456:" not in str(invalid.value)
