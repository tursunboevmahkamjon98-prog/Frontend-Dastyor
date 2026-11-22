"""Upserts agent-cleaned topic lists into book_topics.

Input: a JSON file mapping book_id -> list[str] (the cleaned topic list),
produced by a Claude Code agent from the candidate bundles that
refresh_book_topics.py --dump-dir writes out. Only overwrites rows that
already exist (ensure_topics seeds every resolvable book first) -- this
script never invents a book_id on its own.

Usage:
  .venv/Scripts/python.exe scripts/apply_cleaned_topics.py cleaned.json
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import async_session
from app.models import BookTopics


async def _apply(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    updated, missing = 0, 0
    async with async_session() as db:
        for book_id, topics in data.items():
            if not isinstance(topics, list):
                continue
            row = await db.get(BookTopics, book_id)
            if row is None:
                missing += 1
                continue
            row.status = "ready"
            row.topics_json = json.dumps([t for t in topics if isinstance(t, str)], ensure_ascii=False)
            updated += 1
        await db.commit()
    print(f"Updated {updated} book(s), {missing} book_id(s) not found (seed them first)")


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(1)
    asyncio.run(_apply(Path(sys.argv[1])))


if __name__ == "__main__":
    main()
