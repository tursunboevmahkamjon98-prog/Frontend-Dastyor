"""Extracts a textbook's table of contents once, caches it, and reuses it.

No live call to the product's own AI provider (Cerebras) happens here on
purpose -- the actual cleanup of noisy, heuristically-found heading
candidates into a final topic list is done ahead of time by Claude Code
agents (small/fast Claude models, run during development via
scripts/refresh_book_topics.py), not by the running backend. That keeps this
module AI-call-free and the main generation model/queue (app.ai_service,
app.security.ai_slot) completely untouched, per product requirement.

Flow:
  1. book_library.extract() gives us a book's page text (already done by the
     book-library select endpoints).
  2. _candidate_headings() scans it with a cheap regex for lines that *look*
     like chapter/section/topic headings -- recall-heavy, precision-light,
     with a table-of-contents-page filter to drop the densest false-positive
     source (a contents page lists many headings back-to-back with inline
     page numbers; real chapter pages have at most one).
  3. ensure_topics() stores that heuristic list immediately (status="ready")
     so a dropdown is available the very first time a book is opened.
  4. scripts/refresh_book_topics.py can later replace it with an
     agent-cleaned version (status stays "ready", topics_json is overwritten)
     for better quality, without changing the read path at all.

Every teacher who later opens the same book gets the cached list straight
from the database -- extraction work (heuristic or agent-cleaned) never
reruns for a book that already has a row.
"""

from __future__ import annotations

import json
import re

from sqlalchemy.exc import IntegrityError

from app.logger import get_logger
from app.models import BookTopics

logger = get_logger(__name__)

_MAX_TOPICS = 200
_MAX_CANDIDATES_PER_PAGE = 4  # a real content page has at most ~1 heading;
# a table-of-contents page lists many back-to-back -- treat that as noise.

_HEADING_RE = re.compile(
    r"^(?:"
    r"§\s*\d+[.\)]?|"
    r"боб(?:и)?\s*[ivxlcdm\d]+|"
    r"фасл(?:и)?\s*\d+|"
    r"мавз[уў]ъ[аи]?\s*[:.]?\s*\d*|"
    r"дарс(?:и)?\s*\d+|"
    r"параграф\s*\d*|"
    r"глава\s+\d+|"
    r"раздел\s+\d+|"
    r"тема\s*\d*[:.]?|"
    r"урок\s*\d*|"
    r"chapter\s+\d+|"
    r"unit\s+\d+|"
    r"\d{1,2}(?:\.\d{1,2}){1,2}[.\)]?\s+\S"  # multi-level numbering like "1.2 Title", not a bare "1."
    r")",
    re.IGNORECASE,
)
# Comprehension-question / exercise lines ("1. Нажод чист?", "2. X; 3. Y")
# match the same keyword prefixes as real headings but are never topics.
_QUESTION_RE = re.compile(r"\?\s*$")
_MULTI_ENUM_RE = re.compile(r"\d+\s*[.\)]\s*\S.*;\s*\d+\s*[.\)]")


def _candidate_headings(pages: list[str]) -> list[dict]:
    seen: set[str] = set()
    by_page: dict[int, list[dict]] = {}
    for number, text in enumerate(pages, 1):
        for raw_line in text.splitlines()[:15]:
            line = " ".join(raw_line.split())
            if not (3 <= len(line) <= 140):
                continue
            if _is_toc_title_line(line):
                continue
            if _QUESTION_RE.search(line) or _MULTI_ENUM_RE.search(line):
                continue
            if not _HEADING_RE.match(line):
                continue
            key = line.casefold()
            if key in seen:
                continue
            seen.add(key)
            by_page.setdefault(number, []).append({"page": number, "text": line})

    candidates: list[dict] = []
    for number in sorted(by_page):
        page_hits = by_page[number]
        if len(page_hits) > _MAX_CANDIDATES_PER_PAGE:
            # Looks like a table-of-contents / index page, not real content.
            continue
        candidates.extend(page_hits)
    return candidates


# Many of these textbooks were typeset before Tajik's current standard
# orthography was universal, using Serbian/Macedonian-style lookalike
# letters for sounds that now have their own dedicated Cyrillic letters.
# This is a 1:1 spelling modernization (same words, same meaning, same
# order) -- not a rewrite -- applied so a teacher sees "ҳ/ғ/ҷ/қ/ӣ" like in
# every other textbook instead of a form that reads as broken/garbled.
_ARCHAIC_TO_MODERN_TAJIK = str.maketrans({
    "њ": "ҳ", "Њ": "Ҳ",
    "ѓ": "ғ", "Ѓ": "Ғ",
    "љ": "ҷ", "Љ": "Ҷ",
    "ќ": "қ", "Ќ": "Қ",
    "ї": "ӣ", "Ї": "Ӣ",
})


def _modernize(text: str) -> str:
    return text.translate(_ARCHAIC_TO_MODERN_TAJIK)


_MIN_CONFIDENT_TOPICS = 3

# A real table of contents page: most of its lines are "Title ..... 12" --
# text, a dot/space leader, then a trailing page number. Tajik textbooks
# commonly print this at the BACK of the book, not the front, so this scans
# every page rather than assuming a position.
_DOT_LEADER_RE = re.compile(r"^(.{3,}?[^\s.·…])[ .·…]{2,}(\d{1,4})\s*$")
_BARE_PAGE_NUMBER_RE = re.compile(r"^\d{1,4}$")
_CHAPTER_START_RE = re.compile(
    r"^(?:боб(?:и)?\s*[ivxlcdm\d]|глава\s+\d|раздел\s+\d|фасл(?:и)?\s*\d)",
    re.IGNORECASE,
)
_SECTION_START_RE = re.compile(
    r"^(?:§\s*\d+|параграф\s*\d+|дарс(?:и)?\s*\d+|мавз[уў]ъ[аи]?\s*\d+)",
    re.IGNORECASE,
)
_MIN_TOC_HITS_PER_PAGE = 3


def _is_toc_title_line(line: str) -> bool:
    """Matches the contents page's own heading ("Мундариҷа"/"Содержание"),
    including letter-spaced ("М У Н Д А Р И Ҷ А"), archaic-spelling, or
    OCR-garbled variants, and a "page/саҳ." column header sometimes glued
    onto the same line -- it's a label for the page, never a real topic."""
    compact = _modernize(re.sub(r"\s+", "", line)).casefold()
    return bool(re.match(r"^(?:мундари|содержан|оглавлен|contents|tableofcontents)", compact))


_LEADING_MARKER_RE = re.compile(
    r"^(?:"
    r"боб(?:и)?\s*[ivxlcdm\d]+\s*[.\):]?\s*|"
    r"глава\s+\d+\s*[.\):]?\s*|"
    r"раздел\s+\d+\s*[.\):]?\s*|"
    r"фасл(?:и)?\s*\d+\s*[.\):]?\s*|"
    r"§\s*\d+\s*[.\):]?\s*|"
    r"\d{1,3}\s*[.\):]\s*"
    r")",
    re.IGNORECASE,
)


def _strip_leading_marker(text: str) -> str:
    """Drops a leading list/section number ("14. ", "§ 3.", "Боби II.") so
    the dropdown shows a clean topic title instead of its numbering."""
    result = text
    for _ in range(2):  # handles at most a chapter marker + section marker
        stripped = _LEADING_MARKER_RE.sub("", result, count=1).strip()
        if not stripped or stripped == result:
            break
        result = stripped
    return result or text


def _toc_page_indices(pages: list[str]) -> list[int]:
    """Pages that look like a table of contents: several dot-leader lines."""
    hits = []
    for i, text in enumerate(pages):
        lines = [" ".join(line.split()) for line in text.splitlines()]
        dotted = sum(1 for line in lines if line and _DOT_LEADER_RE.match(line))
        if dotted >= _MIN_TOC_HITS_PER_PAGE:
            hits.append(i)
    return hits


def _parse_toc_pages(pages: list[str], indices: list[int]) -> list[str]:
    """Reconstruct complete entries from contents-page text.

    A title can wrap across lines before its dot-leader + page number, and a
    bare chapter line ("Боби II. ...") has no page number of its own -- both
    are handled by buffering text until a terminator (a dotted line, or the
    start of the next chapter) is found.
    """
    entries: list[str] = []
    buffer = ""

    def flush() -> None:
        nonlocal buffer
        cleaned = buffer.strip(" .")
        if cleaned:
            entries.append(cleaned)
        buffer = ""

    for i in indices:
        for raw_line in pages[i].splitlines():
            line = " ".join(raw_line.split())
            if not line or _is_toc_title_line(line) or _BARE_PAGE_NUMBER_RE.match(line):
                continue
            if _CHAPTER_START_RE.match(line):
                flush()
                match = _DOT_LEADER_RE.match(line)
                entries.append(match.group(1).strip() if match else line)
                continue
            if buffer and _SECTION_START_RE.match(line):
                # A new "§N. ..." heading starting while something was still
                # buffered means that buffered text was its own thing (e.g. a
                # subtitle line with no page number of its own) -- it should
                # not get glued onto this next heading.
                flush()
            match = _DOT_LEADER_RE.match(line)
            if match:
                buffer = f"{buffer} {match.group(1)}".strip() if buffer else match.group(1).strip()
                flush()
            else:
                buffer = f"{buffer} {line}".strip() if buffer else line
    flush()
    return entries


def _dedup_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered = []
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def heuristic_topics(pages: list[str]) -> list[str]:
    """AI-free baseline topic list.

    Prefers a genuine table-of-contents page when the book has one -- its
    entries are complete (an in-body heading can wrap across lines and get
    truncated by a single-line scan) and already correctly cased. Falls back
    to scanning in-body heading-like lines only when no contents page is
    found at all.

    A book that yields only one or two hits either way is more likely a
    stray false positive (an index entry, an example sentence that happens
    to start with "Lesson") than a real topic list -- better to show nothing
    and let the teacher type their own topic than to present a wrong guess
    as if it were authoritative.
    """
    toc_pages = _toc_page_indices(pages)
    if toc_pages:
        entries = _dedup_keep_order(_parse_toc_pages(pages, toc_pages))
        if len(entries) >= _MIN_CONFIDENT_TOPICS:
            return _finalize(entries)

    candidates = [c["text"] for c in _candidate_headings(pages)]
    if len(candidates) < _MIN_CONFIDENT_TOPICS:
        return []
    return _finalize(candidates)


_TRAILING_DOT_RUN_RE = re.compile(r"[ .·…]{4,}\d{0,4}\s*$")


def sanitize_topic(text: str) -> str:
    """Shared cleanup for a single topic string, regardless of where it came
    from (this module's own heuristic, or an external/agent-produced list):
    strip a trailing dot-leader + page number, modernize archaic Tajik
    letters, and strip a leading chapter/section marker."""
    text = " ".join(text.split())
    match = _DOT_LEADER_RE.match(text)
    if match:
        text = match.group(1).strip()
    else:
        # A dot-leader whose page number got lost/cut (seen in some
        # externally-produced lists) -- still just trailing noise.
        text = _TRAILING_DOT_RUN_RE.sub("", text).strip()
    text = _strip_leading_marker(_modernize(text))
    return text.strip(" .")


def _finalize(entries: list[str]) -> list[str]:
    cleaned = [sanitize_topic(entry) for entry in entries]
    return _dedup_keep_order(cleaned)[:_MAX_TOPICS]


async def ensure_topics(db, book_id: str, title: str, pages: list[str]) -> dict:
    """Return the cached topics for this book, computing them once if needed.

    Safe to call on every book-library select: a cached row (heuristic or
    later agent-cleaned by scripts/refresh_book_topics.py) is never
    recomputed.
    """
    row = await db.get(BookTopics, book_id)
    if row is not None:
        return _status_payload(row)

    topics = heuristic_topics(pages)
    row = BookTopics(
        book_id=book_id, title=title[:200], status="ready",
        topics_json=json.dumps(topics, ensure_ascii=False),
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        # Another request computed it first (race) -- use what it stored.
        await db.rollback()
        row = await db.get(BookTopics, book_id)
        if row is not None:
            return _status_payload(row)
        return {"status": "ready", "topics": topics}
    return {"status": "ready", "topics": topics}


async def get_topics(db, book_id: str) -> dict:
    row = await db.get(BookTopics, book_id)
    if row is None:
        return {"status": "unavailable", "topics": None}
    return _status_payload(row)


def _status_payload(row: BookTopics) -> dict:
    if row.status == "ready":
        try:
            topics = json.loads(row.topics_json or "[]")
        except ValueError:
            topics = []
        return {"status": "ready", "topics": topics}
    return {"status": row.status, "topics": None}
