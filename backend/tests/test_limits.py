import asyncio
import sys
import uuid

from fastapi import HTTPException
from sqlalchemy import text

from app import limits
from app.config import get_settings
from app.database import async_session

FAIL = []


def check(name, condition, detail=""):
    print(("  PASS  " if condition else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not condition:
        FAIL.append(name)


async def make_user(balance_dirams: int, free_used: bool) -> str:
    uid = str(uuid.uuid4())
    async with async_session() as db:
        await db.execute(
            text(
                "INSERT INTO users (id, full_name, hashed_password, language, role, "
                " balance_dirams, free_generation_used, phone_verified, is_premium, "
                " free_konspekt_used, free_lektsiya_used, free_test_used, "
                " free_prezentatsiya_used, free_amaliy_used, free_igra_used, created_at) "
                "VALUES (:id, 'race test', 'x', 'Русский', 'user', :bal, :free_flag, "
                "        false, false, :spent, :spent, :spent, "
                "        :spent, :spent, :spent, now())"
            ),
            {
                "id": uid,
                "bal": balance_dirams,
                "free_flag": free_used,
                "spent": get_settings().FREE_GENERATIONS_PER_TYPE if free_used else 0,
            },
        )
        await db.commit()
    return uid


async def cleanup(uid: str):
    async with async_session() as db:
        await db.execute(text("DELETE FROM balance_transactions WHERE user_id = :u"), {"u": uid})
        await db.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})
        await db.commit()


async def state(uid: str, mtype: str = "konspekt"):
    column = limits.FREE_SLOT_COLUMN[mtype]
    async with async_session() as db:
        row = (await db.execute(
            text(f"SELECT balance_dirams, {column} FROM users WHERE id = :u"),
            {"u": uid},
        )).first()
        ledger = (await db.execute(
            text("SELECT count(*) FROM balance_transactions WHERE user_id = :u"), {"u": uid}
        )).scalar()
    return row[0], row[1], ledger


async def try_reserve(uid, types):
    try:
        return await limits.reserve(uid, types)
    except HTTPException as e:
        return e.status_code


async def test_free_once():
    free_n = get_settings().FREE_GENERATIONS_PER_TYPE
    attempts = free_n * 2
    print(f"\n1. {attempts} simultaneous reservations against a brand-new account (0 balance)")
    uid = await make_user(0, False)
    try:
        results = await asyncio.gather(*[try_reserve(uid, ["konspekt"]) for _ in range(attempts)])
        granted = [r for r in results if not isinstance(r, int)]
        refused = [r for r in results if r == 402]
        check(f"exactly {free_n} granted — the whole allowance, no more",
              len(granted) == free_n, f"granted={len(granted)}")
        check(f"the other {attempts - free_n} got 402",
              len(refused) == attempts - free_n, f"402s={len(refused)}")
        check("every granted one came from the free allowance",
              bool(granted) and all(g.free_count == 1 for g in granted))
        balance, free_used, ledger = await state(uid)
        check("counter landed exactly on the allowance — never overshot",
              free_used == free_n, f"counter={free_used}")
        check("balance untouched at 0", balance == 0, f"balance={balance}")
        check(f"exactly {free_n} ledger rows", ledger == free_n, f"rows={ledger}")
    finally:
        await cleanup(uid)


async def test_balance_not_overspent():
    print("\n2. Thirty simultaneous reservations against a 150-diram balance (free already used)")
    uid = await make_user(150, True)
    try:
        results = await asyncio.gather(*[try_reserve(uid, ["test"]) for _ in range(30)])
        granted = [r for r in results if not isinstance(r, int)]
        check("exactly three reservations granted (150 / 50)",
              len(granted) == 3, f"granted={len(granted)}")
        balance, _, ledger = await state(uid)
        check("balance is exactly 0, never negative", balance == 0, f"balance={balance}")
        check("three ledger rows", ledger == 3, f"rows={ledger}")
    finally:
        await cleanup(uid)


async def test_all_or_nothing():
    print("\n3. generate-all (4 types) against a balance that covers only 2")
    uid = await make_user(100, True)
    try:
        result = await try_reserve(uid, ["konspekt", "test", "prezentatsiya", "lektsiya"])
        check("refused with 402", result == 402, f"result={result}")
        balance, _, ledger = await state(uid)
        check("nothing was taken — balance still 100", balance == 100, f"balance={balance}")
        check("no ledger rows written for the refused request", ledger == 0, f"rows={ledger}")
    finally:
        await cleanup(uid)


async def test_refund():
    print("\n4. Reserve then refund (the AI-failed path)")
    uid = await make_user(200, True)
    try:
        charge = await limits.reserve(uid, ["konspekt"])
        balance, _, _ = await state(uid)
        check("charged 50", balance == 150, f"balance={balance}")
        await limits.refund(charge, reason="test")
        balance, _, ledger = await state(uid)
        check("refunded back to 200", balance == 200, f"balance={balance}")
        check("both movements recorded (charge + refund)", ledger == 2, f"rows={ledger}")
    finally:
        await cleanup(uid)


async def test_refund_free_slot():
    print("\n5. The free material fails — the account keeps its free one")
    uid = await make_user(0, False)
    try:
        charge = await limits.reserve(uid, ["konspekt"])
        _, free_used, _ = await state(uid)
        check("free slot claimed — counter went to 1", free_used == 1, f"counter={free_used}")
        await limits.refund(charge, reason="test")
        balance, free_used, _ = await state(uid)
        check("free slot handed back — counter back to 0", free_used == 0, f"counter={free_used}")
        check("no phantom balance credited", balance == 0, f"balance={balance}")
        again = await try_reserve(uid, ["konspekt"])
        check("the free material is available again",
              not isinstance(again, int) and again.free_count == 1)
    finally:
        await cleanup(uid)


async def test_partial_refund():
    print("\n6. generate-all where 2 of 4 types fail")
    uid = await make_user(400, True)
    try:
        charge = await limits.reserve(uid, ["konspekt", "test", "prezentatsiya", "lektsiya"])
        balance, _, _ = await state(uid)
        check("charged 4 x 50 = 200", balance == 200, f"balance={balance}")
        await limits.refund(charge, ["test", "lektsiya"], reason="test")
        balance, _, _ = await state(uid)
        check("refunded exactly 2 x 50", balance == 300, f"balance={balance}")
    finally:
        await cleanup(uid)


async def main():
    for t in (test_free_once, test_balance_not_overspent, test_all_or_nothing,
              test_refund, test_refund_free_slot, test_partial_refund):
        await t()
    print()
    if FAIL:
        print(f"{len(FAIL)} FAILED: {FAIL}")
        sys.exit(1)
    print("all limit checks passed")


asyncio.run(main())
