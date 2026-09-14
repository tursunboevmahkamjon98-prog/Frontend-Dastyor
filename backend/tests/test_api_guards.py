# -*- coding: utf-8 -*-
"""End-to-end checks against a running server: the guards have to hold on
the wire, not just in the functions."""
import os
import asyncio
import sys
import uuid

import httpx
from sqlalchemy import text

from app.auth import create_access_token, hash_password
from app.database import async_session

BASE = os.environ.get("DASTYOR_TEST_BASE", "http://127.0.0.1:8010")
FAIL = []


def check(name, condition, detail=""):
    print(("  PASS  " if condition else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not condition:
        FAIL.append(name)


async def make_user(role="user", balance=0, free_used=True) -> str:
    uid = str(uuid.uuid4())
    async with async_session() as db:
        await db.execute(
            text(
                "INSERT INTO users (id, full_name, hashed_password, language, role, "
                " balance_dirams, free_generation_used, phone_verified, is_premium, "
                " free_konspekt_used, free_lektsiya_used, free_test_used, "
                " free_prezentatsiya_used, free_amaliy_used, free_igra_used, created_at) "
                "VALUES (:id, 'guard test', :pw, 'Русский', :role, :bal, :free, "
                "        false, false, false, false, false, false, false, false, now())"
            ),
            {"id": uid, "pw": hash_password("x"), "role": role, "bal": balance, "free": free_used},
        )
        await db.commit()
    return uid


async def cleanup(uid):
    async with async_session() as db:
        for t in ("balance_transactions", "rate_limit_attempts"):
            col = "user_id" if t == "balance_transactions" else "key"
            await db.execute(text(f"DELETE FROM {t} WHERE {col} = :u"), {"u": uid})
        await db.execute(text("DELETE FROM games WHERE owner_id = :u"), {"u": uid})
        await db.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})
        await db.commit()


async def main():
    user_id = await make_user(role="user", balance=1000)
    admin_id = await make_user(role="admin", balance=1000)
    user_h = {"Authorization": f"Bearer {create_access_token(user_id)}"}
    admin_h = {"Authorization": f"Bearer {create_access_token(admin_id)}"}

    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
            print("\n1. Oversized request body is refused before it is read")
            r = await c.post(
                "/api/materials/generate",
                headers={**user_h, "Content-Type": "application/json"},
                content=b"x" * (21 * 1024 * 1024),
            )
            check("413 Payload Too Large", r.status_code == 413, f"status={r.status_code}")

            print("\n2. The game section is closed to an ordinary account")
            r = await c.post("/api/materials/games", headers=user_h,
                             json={"title": "t", "subject": "Химия", "grade": "9"})
            check("POST /games -> 403", r.status_code == 403, f"status={r.status_code}")
            r = await c.post("/api/materials/quiz-set", headers=user_h,
                             json={"topic": "t", "subject": "Химия", "level": "Средний",
                                   "grade": "9", "language": "Русский", "count": 3})
            check("POST /quiz-set -> 403", r.status_code == 403, f"status={r.status_code}")
            r = await c.post("/api/materials/generate", headers=user_h,
                             json={"material_type": "igra", "topic": "t", "subject": "Химия",
                                   "level": "Средний", "grade": "9", "language": "Русский"})
            check("POST /generate (igra) -> 403", r.status_code == 403, f"status={r.status_code}")

            print("\n3. ...and open to an administrator")
            r = await c.post("/api/materials/games", headers=admin_h,
                             json={"title": "t", "subject": "Химия", "grade": "9"})
            check("POST /games -> 201", r.status_code == 201, f"status={r.status_code}")

            print("\n4. Admin API refuses an ordinary account's token")
            for path in ("/api/admin/stats", "/api/admin/users"):
                r = await c.get(path, headers=user_h)
                check(f"GET {path} -> 403", r.status_code == 403, f"status={r.status_code}")
            r = await c.put(f"/api/admin/users/{user_id}/balance", headers=user_h,
                            json={"amount_somoni": 9999})
            check("PUT balance as non-admin -> 403", r.status_code == 403, f"status={r.status_code}")

            print("\n5. Balance is not settable, only creditable, and it is bounded")
            before = await balance_of(user_id)
            r = await c.put(f"/api/admin/users/{user_id}/balance", headers=admin_h,
                            json={"balance_dirams": 999999, "amount_somoni": 5})
            after = await balance_of(user_id)
            check("an extra 'balance_dirams' field is ignored",
                  after == before + 500, f"{before} -> {after}")
            r = await c.put(f"/api/admin/users/{user_id}/balance", headers=admin_h,
                            json={"amount_somoni": 999999})
            check("an absurd top-up is rejected by validation",
                  r.status_code == 422, f"status={r.status_code}")
            r = await c.put(f"/api/admin/users/{user_id}/balance", headers=admin_h,
                            json={"amount_somoni": -50})
            check("a negative top-up is rejected", r.status_code == 422, f"status={r.status_code}")

            print("\n6. Every top-up is in the ledger, attributed to the admin who made it")
            r = await c.get(f"/api/admin/users/{user_id}/balance-history", headers=admin_h)
            check("history readable by admin", r.status_code == 200, f"status={r.status_code}")
            rows = r.json() if r.status_code == 200 else []
            check("the 5-somoni credit is recorded",
                  any(x["kind"] == "topup" and x["amount_somoni"] == 5 for x in rows),
                  f"rows={len(rows)}")
            check("it names the acting admin",
                  any(x["kind"] == "topup" and x["actor_name"] == "guard test" for x in rows))

            print("\n7. An unauthenticated caller gets nowhere")
            for path in ("/api/materials/stats", "/api/admin/users", "/api/billing/balance"):
                r = await c.get(path)
                check(f"GET {path} without a token -> 401/403",
                      r.status_code in (401, 403), f"status={r.status_code}")

            print("\n8. One account cannot read another's material")
            other = await make_user(role="user")
            try:
                other_h = {"Authorization": f"Bearer {create_access_token(other)}"}
                gid = (await c.post("/api/materials/games", headers=admin_h,
                                    json={"title": "secret", "subject": "Химия",
                                          "grade": "9"})).json()["id"]
                r = await c.get(f"/api/materials/games/{gid}", headers=other_h)
                check("GET another account's game -> 404",
                      r.status_code == 404, f"status={r.status_code}")
            finally:
                await cleanup(other)

    finally:
        await cleanup(user_id)
        await cleanup(admin_id)

    print()
    if FAIL:
        print(f"{len(FAIL)} FAILED: {FAIL}")
        sys.exit(1)
    print("all API guard checks passed")


async def balance_of(uid):
    async with async_session() as db:
        return (await db.execute(
            text("SELECT balance_dirams FROM users WHERE id = :u"), {"u": uid}
        )).scalar()


asyncio.run(main())
