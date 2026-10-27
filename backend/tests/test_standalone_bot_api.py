"""Service API integration tests against the isolated Postgres test database."""
import os
import sys
import uuid

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import async_test
from test_telegram_payments import balance_of, cleanup_user, ledger_rows, make_user

from app.config import get_settings
from app.database import async_session
from app.main import app
from app.models import User
from app.routers import bot_api
from app.routers.billing import (
    create_standalone_telegram_code, create_standalone_telegram_link,
    standalone_telegram_link_status,
)
from app.telegram import service


async def _linked_user():
    uid = await make_user()
    telegram_id = 800_000_000 + uuid.uuid4().int % 100_000_000
    async with async_session() as db:
        await db.execute(text(
            "INSERT INTO telegram_accounts "
            "(id,user_id,chat_id,telegram_user_id,linked_at,last_seen_at,revoked) "
            "VALUES (:id,:uid,:tg,:tg,now(),now(),FALSE)"
        ), {"id": str(uuid.uuid4()), "uid": uid, "tg": telegram_id})
        await db.commit()
    return uid, telegram_id


@async_test
async def test_service_bearer_required(monkeypatch):
    monkeypatch.setattr(get_settings(), "DASTYOR_BOT_API_TOKEN", "test-only-" + "x" * 36)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://testserver") as client:
        assert (await client.get("/api/bot/v1/users/123/balance")).status_code == 401
        assert (await client.get("/api/bot/v1/users/123/balance",
                                  headers={"Authorization": "Bearer wrong"})).status_code == 401
        assert (await client.get("/api/bot/v1/users/123/balance",
                                  headers={"Authorization": "Bearer " + get_settings().DASTYOR_BOT_API_TOKEN})).status_code == 404


@async_test
async def test_startup_handshake_is_authorized_and_contains_no_secrets(monkeypatch):
    settings = get_settings()
    service_token = "test-service-" + "X" * 36
    telegram_token = "123456:" + "Y" * 36
    monkeypatch.setattr(settings, "DASTYOR_BOT_API_TOKEN", service_token)
    monkeypatch.setattr(settings, "DASTYOR_STANDALONE_TELEGRAM_TOKEN", telegram_token)
    monkeypatch.setattr(settings, "DASTYOR_STANDALONE_BOT_USERNAME", "test_balance_bot")
    monkeypatch.setattr(settings, "DASTYOR_BOT_ROOT_ADMIN_ID", 5001)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        assert (await client.get("/api/bot/v1/health")).status_code == 401
        response = await client.get("/api/bot/v1/health", headers={"Authorization": "Bearer " + service_token})
        assert response.status_code == 200
        assert response.json()["telegram_bot_id"] == 123456
        assert response.json()["root_admin_id"] == 5001
        assert service_token not in response.text and telegram_token not in response.text


@async_test
async def test_one_use_link_binds_only_the_redeeming_telegram_id(monkeypatch):
    monkeypatch.setattr(get_settings(), "DASTYOR_BOT_API_TOKEN", "test-only-" + "x" * 36)
    uid = await make_user()
    tg = 800_000_000 + uuid.uuid4().int % 100_000_000
    try:
        issued = await service.issue_link_token(uid, bot_username="dastyor_standalone_test_bot")
        token = issued.start_command.split()[1]
        headers = {"Authorization": "Bearer " + get_settings().DASTYOR_BOT_API_TOKEN}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://testserver") as client:
            body = {"token": token, "telegram_id": tg, "chat_id": tg}
            linked = await client.post("/api/bot/v1/link/redeem", json=body, headers=headers)
            assert linked.status_code == 200
            assert linked.json()["status"] == "linked"
            assert (await client.get(f"/api/bot/v1/users/{tg}/balance",
                                     headers=headers)).json()["balance_dirams"] == 0
            assert (await client.post("/api/bot/v1/link/redeem", json=body,
                                      headers=headers)).status_code == 409
            assert (await client.get(f"/api/bot/v1/users/{tg + 1}/balance",
                                     headers=headers)).status_code == 404
    finally:
        await cleanup_user(uid)


@async_test
async def test_six_digit_link_code_is_private_and_single_use(monkeypatch):
    settings = get_settings()
    token = "test-only-" + "x" * 36
    monkeypatch.setattr(settings, "DASTYOR_BOT_API_TOKEN", token)
    monkeypatch.setattr(settings, "DASTYOR_STANDALONE_TELEGRAM_TOKEN", "123456:" + "Y" * 36)
    monkeypatch.setattr(settings, "DASTYOR_STANDALONE_BOT_USERNAME", "dastyor_balance_bot")
    monkeypatch.setattr(settings, "DASTYOR_BOT_ROOT_ADMIN_ID", 5001)
    uid = await make_user()
    tg = 800_000_000 + uuid.uuid4().int % 100_000_000
    try:
        async with async_session() as db:
            user = await db.get(User, uid)
            issued = await create_standalone_telegram_code(user)
        assert len(issued.code) == 6 and issued.code.isdigit()
        assert issued.bot_username == "dastyor_balance_bot"
        async with async_session() as db:
            stored = (await db.execute(text(
                "SELECT id, token_hash FROM telegram_link_tokens WHERE user_id=:uid "
                "ORDER BY created_at DESC LIMIT 1"
            ), {"uid": uid})).one()
        assert issued.code not in stored.token_hash
        assert stored.token_hash == service.hash_link_code(stored.id, issued.code)

        headers = {"Authorization": "Bearer " + token}
        body = {"token": issued.code, "telegram_id": tg, "chat_id": tg}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://testserver") as client:
            linked = await client.post("/api/bot/v1/link/redeem", json=body, headers=headers)
            assert linked.status_code == 200
            assert linked.json()["status"] == "linked"
            replay = await client.post("/api/bot/v1/link/redeem", json=body, headers=headers)
            assert replay.status_code == 409
    finally:
        await cleanup_user(uid)


@async_test
async def test_authenticated_balance_link_targets_standalone_bot(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "DASTYOR_STANDALONE_BOT_USERNAME", "dastyor_standalone_test_bot")
    monkeypatch.setattr(settings, "DASTYOR_STANDALONE_TELEGRAM_TOKEN", "test-only-bot-token")
    monkeypatch.setattr(settings, "DASTYOR_BOT_API_TOKEN", "test-only-" + "x" * 36)
    monkeypatch.setattr(settings, "DASTYOR_BOT_ROOT_ADMIN_ID", 5001)
    uid = await make_user()
    try:
        async with async_session() as db:
            user = await db.get(User, uid)
            status = await standalone_telegram_link_status(user)
            assert status.bot_configured
            assert status.bot_username == "dastyor_standalone_test_bot"
            link = await create_standalone_telegram_link(user)
            assert link.deep_link.startswith("https://t.me/dastyor_standalone_test_bot?start=")
            assert link.start_command.startswith("/start ")
    finally:
        await cleanup_user(uid)


@async_test
async def test_admin_grant_and_revocation_are_checked_server_side(monkeypatch):
    monkeypatch.setattr(get_settings(), "DASTYOR_BOT_ROOT_ADMIN_ID", 5001)
    candidate = 900_000_000 + uuid.uuid4().int % 100_000_000
    async with async_session() as db:
        with pytest.raises(HTTPException) as forbidden:
            await bot_api.require_admin_id(db, candidate)
        assert forbidden.value.status_code == 403
        with pytest.raises(HTTPException) as wrong_root:
            await bot_api.grant_admin(candidate, bot_api.AdminGrantIn(root_telegram_id=1234), db)
        assert wrong_root.value.status_code == 403
        await bot_api.grant_admin(candidate, bot_api.AdminGrantIn(root_telegram_id=5001), db)
    async with async_session() as db:
        await bot_api.require_admin_id(db, candidate)
        await bot_api.revoke_admin(candidate, bot_api.AdminGrantIn(root_telegram_id=5001), db)
    async with async_session() as db:
        with pytest.raises(HTTPException) as revoked:
            await bot_api.require_admin_id(db, candidate)
        assert revoked.value.status_code == 403


@async_test
async def test_request_idempotency_and_single_credit(monkeypatch):
    monkeypatch.setattr(get_settings(), "DASTYOR_BOT_ROOT_ADMIN_ID", 5001)
    monkeypatch.setattr(bot_api, "verify_receipt", _fake_receipt)
    uid, tg = await _linked_user()
    key = f"{tg}:42"
    body = bot_api.TopupIn(telegram_id=tg, chat_id=tg, amount_dirams=2500,
                           telegram_file_id="receipt-file-123", receipt_mime="image/jpeg",
                           receipt_kind="photo", client_request_key=key)
    try:
        async with async_session() as db:
            first = await bot_api.create_topup(body, db)
        async with async_session() as db:
            repeated = await bot_api.create_topup(body, db)
        assert first["id"] == repeated["id"]
        assert await balance_of(uid) == 0
        async with async_session() as db:
            with pytest.raises(HTTPException) as mismatch:
                await bot_api.create_topup(body.model_copy(update={"amount_dirams": 5000}), db)
        assert mismatch.value.status_code == 409
        async with async_session() as db:
            with pytest.raises(HTTPException) as reused_receipt:
                await bot_api.create_topup(body.model_copy(update={
                    "client_request_key": f"{tg}:44"}), db)
        assert reused_receipt.value.status_code == 409
        async with async_session() as db:
            with pytest.raises(HTTPException) as forbidden:
                await bot_api.approve_topup(first["id"], bot_api.DecisionIn(admin_telegram_id=1234), db)
        assert forbidden.value.status_code == 403
        async with async_session() as db:
            approved = await bot_api.approve_topup(first["id"],
                bot_api.DecisionIn(admin_telegram_id=5001), db)
        assert approved["status"] == "approved"
        assert await balance_of(uid) == 2500
        async with async_session() as db:
            notices = await bot_api.pending_notifications(db)
            assert any(n["id"] == first["id"] and n["telegram_id"] == tg
                       and n["status"] == "approved" for n in notices)
            await bot_api.acknowledge_notification(first["id"], db)
        async with async_session() as db:
            assert all(n["id"] != first["id"] for n in await bot_api.pending_notifications(db))
        async with async_session() as db:
            with pytest.raises(HTTPException) as repeated_decision:
                await bot_api.approve_topup(first["id"], bot_api.DecisionIn(admin_telegram_id=5001), db)
        assert repeated_decision.value.status_code == 409
        assert await balance_of(uid) == 2500
        assert len(await ledger_rows(uid)) == 1
    finally:
        await cleanup_user(uid)


@async_test
async def test_rejection_does_not_credit(monkeypatch):
    monkeypatch.setattr(get_settings(), "DASTYOR_BOT_ROOT_ADMIN_ID", 5001)
    monkeypatch.setattr(bot_api, "verify_receipt", _fake_receipt)
    uid, tg = await _linked_user()
    body = bot_api.TopupIn(telegram_id=tg, chat_id=tg, amount_dirams=1000,
                           telegram_file_id="receipt-file-456", receipt_mime="image/jpeg",
                           receipt_kind="photo", client_request_key=f"{tg}:43")
    try:
        async with async_session() as db:
            created = await bot_api.create_topup(body, db)
        async with async_session() as db:
            rejected = await bot_api.reject_topup(created["id"],
                bot_api.DecisionIn(admin_telegram_id=5001, reason="No transfer found"), db)
        assert rejected["status"] == "rejected"
        assert await balance_of(uid) == 0
        assert not await ledger_rows(uid)
        async with async_session() as db:
            assert any(n["id"] == created["id"] and n["reason"] == "No transfer found"
                       for n in await bot_api.pending_notifications(db))
    finally:
        await cleanup_user(uid)


async def _fake_receipt(*_args):
    return 1234
