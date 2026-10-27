"""Read-only quote and reservation parity without a database connection."""

import os
import json
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings

Settings.model_config = {**Settings.model_config, "env_file": None}
os.environ.update({
    "DATABASE_URL": "postgresql+asyncpg://test:test@127.0.0.1:1/unit_test",
    "DATABASE_URL_SYNC": "postgresql://test:test@127.0.0.1:1/unit_test",
    "SECRET_KEY": "unit-test-only",
    "AI_API_KEY": "unit-test-only",
})

from fastapi import HTTPException
from app import limits
from app.auth import get_current_user
from app.routers import materials
from app.routers.materials import _resolve_generate_all_types, quote_generation
from app.schemas import GenerateAllRequest, GenerationQuoteRequest


class Result:
    def __init__(self, row=None, rowcount=0):
        self.row = row
        self.rowcount = rowcount

    def first(self):
        return self.row

    def scalar(self):
        return self.row[0] if self.row else None


class MemoryDb:
    def __init__(self, balance, used):
        self.balance = balance
        self.used = {t: used.get(t, 0) for t in limits.FREE_SLOT_COLUMN}
        self.ledger = []
        self.writes = 0

    async def __aenter__(self):
        self._before = (self.balance, self.used.copy(), len(self.ledger))
        return self

    async def __aexit__(self, *_):
        return False

    async def connection(self):
        return self

    async def commit(self):
        self.writes += 1

    async def rollback(self):
        self.writes += 1
        self.balance, self.used, ledger_length = self._before
        del self.ledger[ledger_length:]

    async def execute(self, statement, params):
        sql = str(statement)
        if sql.startswith("SELECT balance_dirams,"):
            return Result((self.balance, *(self.used[t] for t in limits.FREE_SLOT_COLUMN)))
        if sql.startswith("SELECT balance_dirams"):
            return Result((self.balance,))
        self.writes += 1
        if sql.startswith("UPDATE users SET balance_dirams = balance_dirams -"):
            if self.balance < params["amt"]:
                return Result()
            self.balance -= params["amt"]
            return Result((self.balance,), rowcount=1)
        if sql.startswith("UPDATE users SET"):
            column = re.search(r"SET (free_\w+_used)", sql).group(1)
            material_type = next(t for t, c in limits.FREE_SLOT_COLUMN.items() if c == column)
            if self.used[material_type] >= params["limit"]:
                return Result()
            self.used[material_type] += 1
            return Result(rowcount=1)
        if sql.startswith("INSERT INTO balance_transactions"):
            self.ledger.append(params)
            return Result(rowcount=1)
        raise AssertionError(f"Unexpected SQL: {sql}")


class GenerationQuoteTests(unittest.IsolatedAsyncioTestCase):
    async def check_case(self, types, balance, used, free_limit, expected_free):
        db = MemoryDb(balance, used)
        with patch.object(limits, "async_session", return_value=db), \
             patch.object(limits, "get_settings", return_value=SimpleNamespace(
                 FREE_GENERATIONS_PER_TYPE=free_limit)):
            quote = await limits.quote("test-user", len(types), types)
            self.assertEqual((db.balance, db.used, db.ledger, db.writes),
                             (balance, {t: used.get(t, 0) for t in limits.FREE_SLOT_COLUMN}, [], 0))
            charge = await limits.reserve("test-user", types)

        self.assertEqual(quote["free_count"], expected_free)
        self.assertEqual(quote["required_dirams"], charge.dirams)
        self.assertEqual(quote["affordable"], True)
        self.assertEqual(quote["balance_dirams"], balance)
        self.assertEqual(quote["items"], [
            {"material_type": item.material_type, "was_free": item.was_free,
             "price_dirams": item.dirams} for item in charge.items
        ])
        self.assertEqual(db.balance, balance - charge.dirams)

    async def test_free_paid_and_mixed_quotes_match_reservations(self):
        await self.check_case(["konspekt"], 0, {}, 1, 1)
        await self.check_case(["konspekt"], 50, {"konspekt": 1}, 1, 0)
        await self.check_case(["konspekt", "test", "amaliy"], 100,
                              {"konspekt": 1, "test": 0, "amaliy": 1}, 1, 1)

    async def test_free_limit_above_one_matches_reservation(self):
        await self.check_case(["konspekt", "test"], 50,
                              {"konspekt": 1, "test": 2}, 2, 1)
        await self.check_case(["konspekt", "konspekt"], 0, {}, 2, 2)

    async def test_insufficient_balance_is_quoted_and_reservation_rolls_back(self):
        db = MemoryDb(0, {"test": 1})
        with patch.object(limits, "async_session", return_value=db), \
             patch.object(limits, "get_settings", return_value=SimpleNamespace(
                 FREE_GENERATIONS_PER_TYPE=1)):
            quote = await limits.quote("test-user", 2, ["konspekt", "test"])
            self.assertEqual((quote["required_dirams"], quote["affordable"]), (50, False))
            with self.assertRaises(limits.InsufficientBalance):
                await limits.reserve("test-user", ["konspekt", "test"])
        self.assertEqual(db.balance, 0)
        self.assertEqual(db.used["konspekt"], 0)
        self.assertEqual(db.ledger, [])

    async def test_quote_rejects_mismatched_count(self):
        with self.assertRaises(ValueError):
            await limits.quote("test-user", 2, ["test"])

    async def test_quote_api_rejects_invalid_duplicate_and_empty_types(self):
        for types in (["test", "test"], ["test", "unknown"], []):
            with self.subTest(types=types), self.assertRaises(HTTPException) as caught:
                await quote_generation(GenerationQuoteRequest(types=types),
                                       SimpleNamespace(id="test-user"))
            self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(_resolve_generate_all_types(["test", "konspekt"]),
                         ["konspekt", "test"])

    async def test_quote_api_requires_user_and_does_not_write(self):
        route = next(r for r in materials.router.routes if r.path == "/api/materials/quote")
        self.assertIn(get_current_user, [d.call for d in route.dependant.dependencies])
        db = MemoryDb(100, {"test": 1})
        with patch.object(limits, "async_session", return_value=db), \
             patch.object(limits, "get_settings", return_value=SimpleNamespace(
                 FREE_GENERATIONS_PER_TYPE=1)):
            result = await quote_generation(
                GenerationQuoteRequest(types=["test", "konspekt"]),
                SimpleNamespace(id="test-user"))
        self.assertEqual(result["required_dirams"], 50)
        self.assertEqual(result["balance_dirams"], 100)
        self.assertEqual((db.writes, db.ledger, db.balance), (0, [], 100))

    async def test_stream_preserves_402_for_client_refresh(self):
        data = GenerateAllRequest(topic="Atoms", subject="Physics", language="English",
                                  level="Medium", grade="8", types=["test"])
        db = MemoryDb(0, {})
        with patch.object(materials, "async_session", return_value=db), \
             patch.object(materials, "_generate_all_impl", new_callable=AsyncMock,
                          side_effect=HTTPException(status_code=402, detail="Not enough balance")):
            response = await materials.generate_all_stream(
                data, SimpleNamespace(is_disconnected=AsyncMock(return_value=False)),
                SimpleNamespace(id="test-user"))
            frames = [frame async for frame in response.body_iterator]
        error = json.loads(frames[-1].removeprefix("data: ").strip())
        self.assertEqual(error["status"], 402)
        self.assertEqual(error["type"], "error")


if __name__ == "__main__":
    unittest.main()
