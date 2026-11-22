"""Upserts topic lists into book_topics, keyed by file path instead of hash.

Input: a JSON file mapping each book's path *relative to BOOK_LIBRARY_DIR*
(forward slashes, exact filename as on disk, e.g. "Синфи 5/Математика синфи 5 .pdf")
to a list[str] of its topics. Converts each path to the same book_id hash
book_library.py uses, then writes/overwrites that row as status="ready".

Usage:
  .venv/Scripts/python.exe scripts/apply_topics_by_path.py topics_by_path.json
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import book_library, book_topics
from app.database import async_session
from app.models import BookTopics


async def _apply(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    updated, created, skipped, kept_existing = 0, 0, 0, 0
    async with async_session() as db:
        for relative_path, topics in data.items():
            if not isinstance(topics, list):
                skipped += 1
                continue
            book_id = book_library._book_id(relative_path)
            clean_topics = book_topics._dedup_keep_order([
                book_topics.sanitize_topic(t) for t in topics if isinstance(t, str) and t.strip()
            ])
            row = await db.get(BookTopics, book_id)
            if row is None:
                row = BookTopics(
                    book_id=book_id,
                    title=Path(relative_path).stem[:200],
                    status="ready",
                    topics_json=json.dumps(clean_topics, ensure_ascii=False),
                )
                db.add(row)
                created += 1
            else:
                existing = json.loads(row.topics_json or "[]")
                if not clean_topics and existing:
                    # Don't let an empty/failed result from this batch erase
                    # topics this book already had.
                    kept_existing += 1
                    continue
                row.status = "ready"
                row.topics_json = json.dumps(clean_topics, ensure_ascii=False)
                updated += 1
        await db.commit()
    print(
        f"Created {created}, updated {updated}, kept existing {kept_existing}, "
        f"skipped {skipped} (of {len(data)} entries)"
    )


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(1)
    asyncio.run(_apply(Path(sys.argv[1])))


if __name__ == "__main__":
    main()
