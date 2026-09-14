# -*- coding: utf-8 -*-
"""Fires concurrent reservations at one account and checks that the
database, not luck, decides how many succeed.

This is the exact attack the old code lost to: N simultaneous /generate
calls, one balance. Run against the real PostgreSQL, because the
guarantee being tested (an UPDATE ... WHERE re-evaluating its condition
after waiting on a row lock) is the database's, not Python's — an
in-memory fake would pass while proving nothing.
"""
import asyncio
import sys
import uuid

from fastapi import HTTPException
from sqlalchemy import text

from app import limits
from app.database import async_session

FAIL = []


def check(name, condition, detail=""):
    print(("  PASS  " if condition else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not condition:
        FAIL.append(name)


async def make_user(balance_dirams: int, free_used: bool) -> str:
    """free_used=True means "this account has already spent its freebies",
    so reserve() must fall through to the balance.

    That has to be written to the PER-TYPE columns. This test used to send
    it to free_generation_used alone and hardcode every per-type column to
    false — the account-wide model that limits.FREE_SLOT_COLUMN replaced.
    The result was an account that claimed to have used its free slot
    while every slot was in fact untouched, so the five money assertions
    ("charged 50", "refused with 402", ...) failed against correct code
    and stayed red. free_generation_used is still set for the legacy
    column's sake; nothing in limits.py reads it."""
    uid = str(uuid.uuid4())
    async with async_session() as db:
        await db.execute(
            text(
                "INSERT INTO users (id, full_name, hashed_password, language, role, "
                " balance_dirams, free_generation_used, phone_verified, is_premium, "
                " free_konspekt_used, free_lektsiya_used, free_test_used, "
                " free_prezentatsiya_used, free_amaliy_used, free_igra_used, created_at) "
                "VALUES (:id, 'race test', 'x', 'Русский', 'user', :bal, :free, "
                "        false, false, :free, :free, :free, "
                "        :free, :free, :free, now())"
            ),
            {"id": uid, "bal": balance_dirams, "free": free_used},
        )
        await db.commit()
    return uid


async def cleanup(uid: str):
    async with async_session() as db:
        await db.execute(text("DELETE FROM balance_transactions WHERE user_id = :u"), {"u": uid})
        await db.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})
        await db.commit()


async def state(uid: str, mtype: str = "konspekt"):
    """Returns (balance, free-slot-used-for-[mtype], ledger rows). The
    flag is read from that type's own column, because that is the one
    _claim_free actually moves."""
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


# ── 1. The free material is claimed exactly once, under a stampede ───────
async def test_free_once():
    print("\n1. Twenty simultaneous reservations against a brand-new account (0 balance)")
    uid = await make_user(0, False)
    try:
        results = await asyncio.gather(*[try_reserve(uid, ["konspekt"]) for _ in range(20)])
        granted = [r for r in results if not isinstance(r, int)]
        refused = [r for r in results if r == 402]
        check("exactly one reservation granted", len(granted) == 1, f"granted={len(granted)}")
        check("the other nineteen got 402", len(refused) == 19, f"402s={len(refused)}")
        check("the granted one was the free slot",
              bool(granted) and granted[0].free_count == 1)
        balance, free_used, ledger = await state(uid)
        check("free flag is set", free_used is True)
        check("balance untouched at 0", balance == 0, f"balance={balance}")
        check("exactly one ledger row", ledger == 1, f"rows={ledger}")
    finally:
        await cleanup(uid)


# ── 2. A balance is spent at most once per 50 dirams ─────────────────────
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


# ── 3. A multi-type request is all-or-nothing ────────────────────────────
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


# ── 4. A failed generation is refunded ───────────────────────────────────
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


# ── 5. A failed FIRST generation gives the free slot back ────────────────
async def test_refund_free_slot():
    print("\n5. The free material fails — the account keeps its free one")
    uid = await make_user(0, False)
    try:
        charge = await limits.reserve(uid, ["konspekt"])
        _, free_used, _ = await state(uid)
        check("free slot claimed", free_used is True)
        await limits.refund(charge, reason="test")
        balance, free_used, _ = await state(uid)
        check("free slot handed back", free_used is False)
        check("no phantom balance credited", balance == 0, f"balance={balance}")
        # Re-reserve the SAME type. The old version asked for "test" here,
        # which under per-type slots just claimed a different untouched
        # freebie and would have passed even if the konspekt slot had
        # never come back.
        again = await try_reserve(uid, ["konspekt"])
        check("the free material is available again",
              not isinstance(again, int) and again.free_count == 1)
    finally:
        await cleanup(uid)


# ── 6. Partial refund of a multi-type charge ─────────────────────────────
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
