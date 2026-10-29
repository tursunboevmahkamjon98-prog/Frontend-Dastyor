"""Integration checks using an explicitly supplied test PostgreSQL connection.

Run with DASTYOR_TEST_DATABASE_URL set to a SQLAlchemy async PostgreSQL URL.
All fixtures live in a unique schema inside a transaction that is rolled back.
The application's .env and production database are never used by this test.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import uuid
from unittest.mock import patch


async def main():
    test_url = os.environ.get("DASTYOR_TEST_DATABASE_URL")
    if not test_url:
        print("SKIP: set DASTYOR_TEST_DATABASE_URL to run database integration checks")
        return

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app import config
    settings = config.Settings(
        _env_file=None, DATABASE_URL=test_url, DATABASE_URL_SYNC=test_url,
        SECRET_KEY="isolated-summary-test", AI_API_KEY="isolated-summary-test",
    )
    with patch.object(config, "get_settings", return_value=settings):
        from app.auth import get_current_user
        from app.database import Base, get_db
        from app.models import User
        from app.routers import materials

    import httpx
    from fastapi import FastAPI
    from sqlalchemy import event, text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    engine = create_async_engine(test_url, pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                schema = "test_summaries_" + uuid.uuid4().hex
                await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                await connection.run_sync(Base.metadata.create_all)
                async with AsyncSession(bind=connection, expire_on_commit=False) as session:
                    user = User(full_name="Test Owner", email="owner@example.test", hashed_password="test")
                    other = User(full_name="Other Owner", email="other@example.test", hashed_password="test")
                    session.add_all([user, other])
                    await session.flush()
                    payload = '{"text":"' + "x" * 64000 + '"}'
                    fields = {
                        "konspekt": "content", "lektsiya": "content",
                        "test": "questions_json", "prezentatsiya": "slides_json",
                        "amaliy": "tasks_json", "igra": "game_json",
                    }
                    first_note = None
                    for kind, model in materials._MATERIAL_MODELS.items():
                        for index in range(25):
                            item = model(
                                owner_id=user.id,
                                title="Special lesson" if index == 0 else f"Lesson {index}",
                                subject="Math" if index % 2 == 0 else "History",
                                grade="8" if index % 3 == 0 else "9",
                                is_favorite=index == 0,
                                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index),
                                **{fields[kind]: payload},
                            )
                            session.add(item)
                            if kind == "konspekt" and index == 0:
                                first_note = item
                        session.add(model(owner_id=other.id, title="Private other user material",
                                          subject="Math", grade="8", **{fields[kind]: payload}))
                    await session.flush()

                    statements = []
                    def count_queries(conn, cursor, statement, parameters, context, executemany):
                        statements.append(statement)
                    event.listen(connection.sync_connection, "before_cursor_execute", count_queries)

                    async def test_session():
                        yield session

                    app = FastAPI()
                    app.include_router(materials.router)
                    app.dependency_overrides[get_db] = test_session
                    app.dependency_overrides[get_current_user] = lambda: user
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                        async def fetch(path, expected=200, queries=1):
                            statements.clear()
                            response = await client.get("/api/materials" + path)
                            assert response.status_code == expected, response.text
                            assert len(statements) == queries, (path, len(statements))
                            return response

                        stats = (await fetch("/stats")).json()
                        assert len(stats) == 6 and set(stats.values()) == {25}, stats
                        print("PASS: six correct, owner-scoped statistics in one database query")

                        library_response = await fetch("/library")
                        rows = library_response.json()
                        assert len(rows) == 125 and all(row["type"] != "igra" for row in rows)
                        assert all(row["is_favorite"] for row in rows[:5])
                        assert not any(row["is_favorite"] for row in rows[5:])
                        assert len(library_response.content) < 50000
                        assert all(not (set(fields.values()) & row.keys()) for row in rows)
                        print("PASS: library returns 125 metadata rows under 50 KB, favorites first")

                        rows = (await fetch("/search")).json()
                        assert len(rows) == 120
                        assert [row["created_at"] for row in rows] == sorted((row["created_at"] for row in rows), reverse=True)
                        assert (await fetch("/search?q=private")).json() == []
                        assert (await fetch("/library?q=private")).json() == []
                        rows = (await fetch("/search?q=Special&subject=Math&grade=8")).json()
                        assert len(rows) == 6
                        print("PASS: search limits, date order, filters and cross-account isolation")

                        rows = (await fetch("/library?material_type=test&page_size=3")).json()
                        assert len(rows) == 3 and rows[0]["is_favorite"]
                        assert all(row["type"] == "test" for row in rows)
                        next_page = (await fetch("/library?material_type=test&page_size=3&page=2")).json()
                        assert not ({row["id"] for row in rows} & {row["id"] for row in next_page})
                        for invalid in ("material_type=bad", "page=0", "page_size=101"):
                            await fetch("/library?" + invalid, expected=422, queries=0)
                        print("PASS: type selection, pagination and invalid-parameter validation")

                        detail = (await fetch("/konspekts/" + first_note.id)).json()
                        assert detail["content"] == payload
                        print("PASS: full material content remains available on the detail endpoint")
            finally:
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None)
