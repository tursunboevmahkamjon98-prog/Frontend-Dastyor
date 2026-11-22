"""Pre-populates app_topics for every (subject, grade) combo the live app can
resolve to a book, so no teacher is ever the first to pay the extraction cost.

Step 1 (this script, no AI): for every resolvable book, extract page text,
run the heuristic heading-candidate scan, and store it immediately as the
book's topic list (status="ready"). This is exactly what the live
book-library endpoints would do lazily on first selection -- running it here
just does it ahead of time for the whole catalog instead of one book at a
time as teachers happen to open them.

Step 2 (separate, see candidate dump below): the same candidates, written to
--dump-dir as JSON, are the input Claude Code agents clean up into a final
topic list (dropping page-number/table-of-contents noise, keeping every
heading's original text and order) via backend/scripts/apply_cleaned_topics.py.
That keeps the actual AI work outside the running backend entirely.

Usage:
  .venv/Scripts/python.exe scripts/refresh_book_topics.py [--dump-dir DIR] [--limit N]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import book_library, book_topics
from app.database import async_session


def _resolvable_books() -> dict[str, dict]:
    subjects = list(book_library.SUBJECT_BUCKETS.keys())
    grades = [f"{i} класс" for i in range(1, 12)]
    books: dict[str, dict] = {}
    for subject in subjects:
        for grade in grades:
            best = book_library.find_best(subject, grade)
            if best and best["id"] not in books:
                books[best["id"]] = best
    return books


async def _seed(db, book_id: str, title: str, pages: list[str]) -> dict:
    return await book_topics.ensure_topics(db, book_id, title, pages)


async def _run(items: list[dict], dump_dir: Path | None) -> None:
    ok, failed = 0, 0
    t0 = time.time()
    async with async_session() as db:
        for i, record in enumerate(items, 1):
            try:
                extracted = book_library.extract(record["id"])
            except Exception as exc:
                print(f"  [{i}/{len(items)}] FAILED extracting {record['relative_path']}: {exc}")
                failed += 1
                continue
            result = await _seed(db, record["id"], extracted["title"], extracted["pages"])
            n_topics = len(result.get("topics") or [])
            print(f"  [{i}/{len(items)}] {record['relative_path']} -> {n_topics} topics ({result['status']})")
            ok += 1

            if dump_dir:
                candidates = book_topics._candidate_headings(extracted["pages"])
                bundle = {
                    "book_id": record["id"],
                    "title": extracted["title"],
                    "relative_path": record["relative_path"],
                    "candidates": candidates,
                }
                (dump_dir / f"{record['id']}.json").write_text(
                    json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8",
                )
    print(f"Done: {ok} ok, {failed} failed, {time.time() - t0:.1f}s total")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump-dir", default=None, help="Write per-book candidate JSON here for agent cleanup")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    dump_dir = Path(args.dump_dir).expanduser() if args.dump_dir else None
    if dump_dir:
        dump_dir.mkdir(parents=True, exist_ok=True)

    books = _resolvable_books()
    items = list(books.values())
    if args.limit:
        items = items[:args.limit]
    print(f"Resolvable books: {len(books)}; processing {len(items)}")

    asyncio.run(_run(items, dump_dir))


if __name__ == "__main__":
    main()
