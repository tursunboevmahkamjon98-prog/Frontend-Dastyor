"""AI edit endpoint checks that do not need a database or AI service."""

import asyncio
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings

# Keep this standalone unit test independent of the local .env and any DB.
Settings.model_config = {**Settings.model_config, "env_file": None}
os.environ.update({
    "DATABASE_URL": "postgresql+asyncpg://test:test@127.0.0.1:1/unit_test",
    "DATABASE_URL_SYNC": "postgresql://test:test@127.0.0.1:1/unit_test",
    "SECRET_KEY": "unit-test-only",
    "AI_API_KEY": "unit-test-only",
})

from app.routers import materials
from app.schemas import ChatEditRequest, RegenerateItemRequest


class AiEditEndpointTests(unittest.TestCase):
    def setUp(self):
        self.user = SimpleNamespace(id="test-user", email="test@example.invalid")
        self.db = SimpleNamespace(close=AsyncMock())

    def test_regenerate_item_releases_request_session_before_ai_call(self):
        data = RegenerateItemRequest(
            material_type="test", topic="Atoms", subject="Physics",
            language="English", level="Medium", grade="8",
        )

        async def fake_ai(**kwargs):
            self.db.close.assert_awaited_once()
            self.assertEqual(kwargs["material_type"], "test")
            return {"question": "What is an atom?"}

        with patch.object(materials, "enforce_ai_edit_quota", new_callable=AsyncMock) as quota, \
             patch.object(materials, "regenerate_item", side_effect=fake_ai) as ai:
            result = asyncio.run(materials.regenerate_item_endpoint(data, self.user, self.db))

        quota.assert_awaited_once_with(self.user)
        ai.assert_awaited_once()
        self.assertEqual(result["status"], "ok")

    def test_chat_edit_releases_request_session_before_ai_call(self):
        data = ChatEditRequest(
            material_type="konspekt", topic="Atoms", subject="Physics",
            language="English", level="Medium", grade="8",
            instruction="Simplify", content={"title": "Atoms"},
        )

        async def fake_ai(**kwargs):
            self.db.close.assert_awaited_once()
            self.assertEqual(kwargs["instruction"], "Simplify")
            return {"title": "Simple atoms"}

        with patch.object(materials, "enforce_ai_edit_quota", new_callable=AsyncMock) as quota, \
             patch.object(materials, "chat_edit_material", side_effect=fake_ai) as ai:
            result = asyncio.run(materials.chat_edit_endpoint(data, self.user, self.db))

        quota.assert_awaited_once_with(self.user)
        ai.assert_awaited_once()
        self.assertEqual(result["content"], {"title": "Simple atoms"})


if __name__ == "__main__":
    unittest.main()
