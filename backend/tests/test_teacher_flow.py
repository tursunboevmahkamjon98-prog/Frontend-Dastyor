# -*- coding: utf-8 -*-
"""The teacher's actual path, on the wire: sign up with a phone + SMS code,
log in, generate a material, open it, download every format, and get
refused once the free slot is gone.

Unlike the other suites this one spends a real AI call and takes a few
minutes. Run it against a server started with SMS_DRY_RUN=true (no real
texts) before shipping:

    PYTHONPATH=. python tests/test_teacher_flow.py

DASTYOR_TEST_BASE overrides the target; it defaults to the same
127.0.0.1:8010 test_api_guards.py uses. The account it creates is
deleted again in cleanup(), including its generated material."""
import asyncio, json, os, random, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import io as _io
import httpx
from pypdf import PdfReader
from sqlalchemy import text
from app.config import get_settings
from app.database import async_session

BASE = os.environ.get("DASTYOR_TEST_BASE", "http://127.0.0.1:8010")
FAIL = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        FAIL.append(name)


PHONE = "+992" + "".join(str(random.randint(0, 9)) for _ in range(9))


async def code_for(phone, purpose):
    async with async_session() as db:
        return (await db.execute(text(
            "SELECT code FROM phone_verification_codes WHERE phone=:p AND purpose=:u "
            "AND used=false ORDER BY created_at DESC LIMIT 1"), {"p": phone, "u": purpose})).scalar()


async def cleanup(phone):
    async with async_session() as db:
        uid = (await db.execute(text("SELECT id FROM users WHERE phone=:p"), {"p": phone})).scalar()
        if uid:
            for t, col in (("balance_transactions", "user_id"), ("konspekts", "owner_id"),
                           ("lectures", "owner_id"), ("presentations", "owner_id"),
                           ("tests", "owner_id"), ("practical_tasks", "owner_id"),
                           ("games", "owner_id"), ("refresh_tokens", "user_id"),
                           ("trusted_devices", "user_id")):
                await db.execute(text(f"DELETE FROM {t} WHERE {col}=:u"), {"u": uid})
            await db.execute(text("DELETE FROM users WHERE id=:u"), {"u": uid})
        await db.execute(text("DELETE FROM phone_verification_codes WHERE phone=:p"), {"p": phone})
        await db.commit()


async def main():
    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=300) as c:
            print(f"\n1. Ro'yxatdan o'tish ({PHONE})")
            r = await c.post("/api/auth/register/send-code", json={"phone": PHONE})
            check("SMS kod so'raldi", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
            code = await code_for(PHONE, "register")
            check("kod bazaga yozildi", bool(code))
            if not code:
                return

            r = await c.post("/api/auth/register", json={
                "full_name": "Test Muallim", "phone": PHONE, "code": code,
                "password": "TestParol123!", "language": "Таджикский"})
            check("hisob yaratildi", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
            if r.status_code != 201:
                return
            H = {"Authorization": f"Bearer {r.json()['access_token']}"}

            print("\n2. Kirish (login)")
            r = await c.post("/api/auth/login", json={"phone": PHONE, "password": "TestParol123!"})
            check("to'g'ri parol bilan kirdi", r.status_code in (200, 202), f"{r.status_code}")
            r = await c.post("/api/auth/login", json={"phone": PHONE, "password": "NotoqriParol1!"})
            check("noto'g'ri parol rad etildi", r.status_code == 401, f"{r.status_code}")

            print("\n3. Profil va balans")
            check("/auth/me ishlaydi", (await c.get("/api/auth/me", headers=H)).status_code == 200)
            r = await c.get("/api/billing/balance", headers=H)
            check("balans ko'rinadi", r.status_code == 200, r.text[:60])

            print("\n4. Material yaratish (tojik tilida, bepul slot)")
            r = await c.post("/api/materials/generate", headers=H, json={
                "material_type": "konspekt", "topic": "Реша ва вазифаҳои он",
                "subject": "Биология", "grade": "8 класс", "language": "Таджикский",
                "level": "Средний"})
            check("generate 200 qaytardi", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
            if r.status_code != 200:
                return
            mid = r.json().get("id")
            check("material id bor", bool(mid))
            if not mid:
                return

            print("\n5. Ochish va yuklab olish")
            r = await c.get(f"/api/materials/konspekts/{mid}", headers=H)
            check("materialni ochish", r.status_code == 200, f"{r.status_code}")
            # The API stores content as a JSON *string* (KonspektOut.content
            # is str|None) and the frontend JSON.parses it before use —
            # the download endpoints want the parsed dict.
            raw = r.json().get("content") if r.status_code == 200 else None
            content = json.loads(raw) if raw else None
            check("saqlangan kontent bor", isinstance(content, dict) and bool(content))
            if not content:
                return

            body = {"material_type": "konspekt", "content": content, "language": "Таджикский"}
            for fmt, ep in (("PDF", "download-pdf"), ("DOCX", "download-docx"), ("TXT", "download-txt")):
                r = await c.post(f"/api/materials/{ep}", headers=H, json=body)
                ok = r.status_code == 200 and len(r.content) > 500
                check(f"{fmt} yuklandi", ok, f"{r.status_code}, {len(r.content)} bayt")
                if r.status_code == 422:
                    for e in r.json()["detail"][:5]:
                        print("        ->", e.get("type"), e.get("loc"), str(e.get("msg"))[:80])
                if ok and fmt == "PDF":
                    txt = "\n".join(pg.extract_text() or "" for pg in
                                    PdfReader(_io.BytesIO(r.content)).pages)
                    check("PDF: tojikcha 'синф' bor, ruscha 'класс' yo'q",
                          "синф" in txt.lower() and "класс" not in txt.lower(),
                          f"синф={'синф' in txt.lower()} класс={'класс' in txt.lower()}")

            print("\n6. Ruxsatlar")
            r = await c.get(f"/api/materials/konspekts/{mid}")
            check("tokensiz ochish -> 401/403", r.status_code in (401, 403), f"{r.status_code}")
            r = await c.post("/api/materials/download-pdf", json=body)
            check("tokensiz yuklab olish -> 401/403", r.status_code in (401, 403), f"{r.status_code}")

            print("\n7. Bepul slot tugadi — ikkinchisi pul so'rashi kerak")
            # Spend the rest of the allowance directly in the database
            # rather than through the API. It used to be one free
            # konspekt, so a second /generate hit the paywall; the
            # allowance is Settings.FREE_GENERATIONS_PER_TYPE now, and
            # driving it to zero over the wire would mean nine more real
            # AI calls and several more minutes for a check that is
            # about the 402, not about generation.
            async with async_session() as db:
                await db.execute(
                    text("UPDATE users SET free_konspekt_used = :n WHERE phone = :p"),
                    {"n": get_settings().FREE_GENERATIONS_PER_TYPE, "p": PHONE},
                )
                await db.commit()
            r = await c.post("/api/materials/generate", headers=H, json={
                "material_type": "konspekt", "topic": "Фотосинтез", "subject": "Биология",
                "grade": "8 класс", "language": "Таджикский", "level": "Средний"})
            check("balanssiz ikkinchi konspekt -> 402", r.status_code == 402,
                  f"{r.status_code} {r.text[:120]}")
    finally:
        await cleanup(PHONE)

    print()
    if FAIL:
        print(f"{len(FAIL)} FAILED: {FAIL}")
        sys.exit(1)
    print("butun o'qituvchi yo'li ishladi")


asyncio.run(main())
