"""Read-only catalog for the school books kept in the local library folder.

The real library is organised as one folder per grade (e.g. "Синфи 5"), with
every subject's textbook sitting as a flat file inside it -- there are no
subject subfolders and filenames are inconsistent (typos, mixed Tajik /
Russian / transliterated spelling). Subjects are therefore detected from each
filename with a keyword map, not from the folder structure.

The catalog exposes metadata only. When a teacher's subject + grade resolves
to a book, its text is loaded into the existing short-lived ``book_sources``
store and the normal page/chapter selection and RAG generation flow is reused.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from app import book_sources
from app.config import get_settings
from app.document_extract import extract_source_text

# Extracting a library book can mean OCR-ing a fully scanned textbook (one to
# a few minutes). book_sources' own store only caches that per user for 24h,
# so every teacher who opened the same book paid that cost again. This cache
# is keyed by book_id and never expires -- OCR for a given book runs once,
# ever, not once per selection. Invalidated automatically if the source PDF
# on disk changes (mtime no longer matches).
_EXTRACTION_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "book_extractions"


LIBRARY_ROOT = Path(
    os.getenv("BOOK_LIBRARY_DIR", get_settings().BOOK_LIBRARY_DIR)
)
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}

_GRADE_RE = re.compile(r"(?:синф|класс|class|grade)\w*[\s_-]*([1-9]|1[01])\b", re.I)
_LEADING_NUMBER_RE = re.compile(r"([1-9]|1[01])\b")

_DIACRITICS = (("ё", "е"), ("ӣ", "и"), ("ӯ", "у"), ("ғ", "г"), ("ҳ", "х"), ("қ", "к"), ("ҷ", "ч"))


def _fold(value: str) -> str:
    text = (value or "").casefold()
    for original, replacement in _DIACRITICS:
        text = text.replace(original, replacement)
    return " ".join(text.split())


# Every label the frontend's subject dropdown can send, mapped to a canonical
# bucket. The Russian and Tajik labels for the same subject share a bucket so
# either UI language resolves to the same textbooks.
SUBJECT_BUCKETS: dict[str, str] = {
    "Математика": "mathematics",
    "Алгебра": "algebra",
    "Геометрия": "geometry",
    "Информатика": "informatics",
    "Физика": "physics",
    "Химия": "chemistry",
    "Биология": "biology",
    "География": "geography",
    "Русский язык": "russian_language",
    "Английский язык": "english_language",
    "Таджикский язык": "tajik_language",
    "Таджикская литература": "literature",
    "История Таджикистана": "history_tajikistan",
    "Всемирная история": "history_world",
    "Адабиёт": "literature",
    "Забони тоҷикӣ": "tajik_language",
    "Забони русӣ": "russian_language",
    "Забони англисӣ": "english_language",
    "Забони арабӣ": "arabic",
    "Забони фаронсавӣ": "french",
    "Забони немисӣ": "german",
    "Санъат": "art_music",
    "Суруд ва мусиқӣ": "music",
    "Технология": "technology",
    "Интихоби касб": "career_choice",
    "Маърифати оиладорӣ": "family_studies",
    "Омодагии ибтидоии ҳарбӣ": "military_prep",
    "Ҳуқуқ": "law",
    "Табиатшиносӣ": "nature_study",
    "Тарбияи ҷисмонӣ": "pe",
    "Ҷомеашиносӣ": "social_studies",
    "Соати тарбиявӣ": "class_hour",
    "Синфҳои ибтидоӣ": "primary_school",
}

# Keyword stems (compared after `_fold`) used to spot each bucket inside a
# messy real-world filename. Order inside a tuple does not matter.
_BUCKET_KEYWORDS: dict[str, tuple[str, ...]] = {
    "mathematics": ("математик", "matimatik", "matematik"),
    "algebra": ("алгебр", "algebra"),
    "geometry": ("геометр", "геометрия", "geometri"),
    "informatics": ("иттилоот", "информатик", "informatik"),
    "physics": ("физик", "fizika"),
    "chemistry": ("хими", "ximiya", "chimiya"),
    "biology": ("биолог", "ботаник", "зоолог", "zoologiy", "biologiy"),
    "geography": ("географ", "geography"),
    "russian_language": (
        "русский язык", "русская реч", "руская реч", "рус.яз", "рус яз",
        "русский язик", "руский язык", "забони руси", "zaboni русси",
    ),
    "english_language": ("англ", "english", "ангилис"),
    "tajik_language": ("забони точ", "забони тоик", "zaboni tojik", "забони модари"),
    "literature": ("адабиет", "adabiyot"),
    "history_tajikistan": (
        "таърихи точик", "таърихи халки точик", "таърихи х. точик",
        "таърихи х.точик", "tarixi tojik",
    ),
    "history_world": ("таърихи умум", "tarixi umumi"),
    "social_studies": ("чомеашинос", "обществ", "одоби муошират", "иктисод"),
    "ecology": ("эколог", "ecology"),
    "technology": (
        "технология", "таълими мехнат", "касбу хунар", "хунар",
        "техникаи бехатар", "накшакаши",
    ),
    "art_music": ("санъат",),
    "music": ("суруд", "мусики"),
    "pe": ("тарбияи чисмони", "т.чисмони"),
    "law": ("хукук",),
    "arabic": ("забони араби", "з. араби", "з.араби"),
    "french": ("фаронсави", "франсави"),
    "german": ("немис",),
    "career_choice": ("интихоби касб",),
    "family_studies": ("оиладори",),
    "military_prep": ("харби",),
    "nature_study": ("табиатшинос",),
    "class_hour": ("тарзи хаети солим",),
    "primary_school": ("алифбо", "буквар", "bukvar"),
}


def _book_id(relative_path: str) -> str:
    return hashlib.sha256(relative_path.casefold().encode("utf-8")).hexdigest()[:32]


def _title(path: Path) -> str:
    value = path.stem.replace("_", " ").replace("-", " ")
    return " ".join(value.split())[:160] or "Book"


def _grade_from_folder(name: str) -> str | None:
    match = _GRADE_RE.search(name)
    if match:
        return match.group(1)
    match = _LEADING_NUMBER_RE.search(name)
    return match.group(1) if match else None


def requested_grade_number(value: str | None) -> str | None:
    """Pull the leading grade number out of a UI value like "5 класс"."""
    if not value:
        return None
    match = _LEADING_NUMBER_RE.search(value)
    return match.group(1) if match else None


def _matched_buckets(filename: str) -> list[str]:
    folded = _fold(filename)
    return [bucket for bucket, keywords in _BUCKET_KEYWORDS.items()
            if any(_fold(keyword) in folded for keyword in keywords)]


def _subject_score(filename: str, bucket: str) -> int:
    folded = _fold(filename)
    keywords = _BUCKET_KEYWORDS.get(bucket, ())
    return sum(1 for keyword in keywords if _fold(keyword) in folded)


def _records(subject: str | None = None, grade: str | None = None) -> list[dict]:
    root = LIBRARY_ROOT.expanduser()
    if not root.exists() or not root.is_dir():
        return []

    bucket = SUBJECT_BUCKETS.get((subject or "").strip()) if subject else None
    wanted_grade = requested_grade_number(grade) if grade else None

    records: list[dict] = []
    for grade_dir in sorted(root.iterdir(), key=lambda path: path.name.casefold()):
        if not grade_dir.is_dir():
            continue
        grade_number = _grade_from_folder(grade_dir.name)
        if wanted_grade and grade_number != wanted_grade:
            continue
        try:
            paths = list(grade_dir.rglob("*"))
        except OSError:
            continue
        for path in paths:
            if not path.is_file() or path.suffix.casefold() not in SUPPORTED_EXTENSIONS:
                continue
            buckets = _matched_buckets(path.stem)
            if bucket and bucket not in buckets:
                continue
            try:
                relative = path.relative_to(root).as_posix()
                size = path.stat().st_size
            except OSError:
                continue
            records.append({
                "id": _book_id(relative),
                "title": _title(path),
                "subject": subject or "",
                "buckets": buckets,
                "extension": path.suffix.casefold().lstrip("."),
                "size_bytes": size,
                "grade_hint": grade_number,
                "relative_path": relative,
            })
    return records


def list_books(subject: str | None = None, grade: str | None = None) -> list[dict]:
    public_keys = ("id", "title", "subject", "extension", "size_bytes", "grade_hint")
    return [{key: record[key] for key in public_keys} for record in _records(subject, grade)]


# A subject that, at some grades, genuinely has no textbook of its own
# because the curriculum splits it into other subjects instead (e.g.
# "Математика" becomes "Алгебра" + "Геометрия" from grade 7 on). Falling
# back to those rather than reporting "no book found" matches what a
# teacher actually wants: *a* math book for the class, not a dead end.
_SUBJECT_FALLBACKS: dict[str, tuple[str, ...]] = {
    "Математика": ("Алгебра", "Геометрия"),
}


def _find_best_single(subject: str | None, grade: str | None) -> dict | None:
    bucket = SUBJECT_BUCKETS.get((subject or "").strip())
    if not bucket:
        return None
    candidates = _records(subject, grade)
    if not candidates:
        return None
    candidates.sort(key=lambda record: (
        -_subject_score(record["relative_path"], bucket),
        len(record["title"]),
        record["title"].casefold(),
    ))
    return candidates[0]


def find_best(subject: str | None, grade: str | None) -> dict | None:
    """Pick the single most likely textbook for a subject + grade pair.

    Returns ``None`` (not an error) when the subject is unrecognised or no
    file in the library matches it, even through a fallback -- callers
    decide how to surface that.
    """
    best = _find_best_single(subject, grade)
    if best is not None:
        return best
    for fallback in _SUBJECT_FALLBACKS.get((subject or "").strip(), ()):
        best = _find_best_single(fallback, grade)
        if best is not None:
            return best
    return None


def _record(book_id: str) -> tuple[dict, Path]:
    if not re.fullmatch(r"[0-9a-f]{32}", book_id or ""):
        raise book_sources.BookError("not_found")
    root = LIBRARY_ROOT.expanduser().resolve()
    for record in _records():
        if record["id"] != book_id:
            continue
        path = (root / record["relative_path"]).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise book_sources.BookError("not_found") from exc
        if not path.is_file():
            raise book_sources.BookError("not_found")
        return record, path
    raise book_sources.BookError("not_found")


def _extract_text_document(path: Path, raw: bytes) -> dict:
    text, _ = extract_source_text(path.name, raw)
    pages = [part.strip() for part in text.split("\f") if part.strip()]
    if not pages:
        pages = [text]
    expanded: list[str] = []
    for page in pages:
        if len(page) <= 16000:
            expanded.append(page)
        else:
            expanded.extend(page[index:index + 16000] for index in range(0, len(page), 16000))
    pages = expanded[:book_sources.MAX_PAGES]
    if not any(len(page) >= 20 for page in pages):
        raise book_sources.BookError("no_text")
    return {
        "title": _title(path),
        "page_count": len(pages),
        "pages": pages,
        "chapters": [],
        "ocr_pages": 0,
        "unreadable_pages": sum(len(page) < 20 for page in pages),
    }


def _cache_path(book_id: str) -> Path:
    return _EXTRACTION_CACHE_DIR / f"{book_id}.json"


def _load_cached_extraction(book_id: str, source_mtime: float) -> dict | None:
    cache_file = _cache_path(book_id)
    try:
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if cached.get("_source_mtime") != source_mtime:
        return None
    cached.pop("_source_mtime", None)
    return cached


def _store_cached_extraction(book_id: str, source_mtime: float, extracted: dict) -> None:
    try:
        _EXTRACTION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {**extracted, "_source_mtime": source_mtime}
        _cache_path(book_id).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # Caching is an optimization; extraction already succeeded without it.


def extract(book_id: str) -> dict:
    _, path = _record(book_id)
    try:
        source_mtime = path.stat().st_mtime
    except OSError as exc:
        raise book_sources.BookError("not_found") from exc
    cached = _load_cached_extraction(book_id, source_mtime)
    if cached is not None:
        return cached
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise book_sources.BookError("not_found") from exc
    if path.suffix.casefold() == ".pdf":
        extracted = book_sources.extract_pdf(
            raw,
            path.name,
            "application/pdf",
            max_bytes=book_sources.MAX_LIBRARY_BYTES,
            max_pages=book_sources.MAX_LIBRARY_PAGES,
            max_ocr_pages=book_sources.MAX_LIBRARY_OCR_PAGES,
        )
    else:
        extracted = _extract_text_document(path, raw)
    _store_cached_extraction(book_id, source_mtime, extracted)
    return extracted
