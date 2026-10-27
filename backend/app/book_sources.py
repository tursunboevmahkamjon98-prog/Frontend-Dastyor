"""Private, short-lived extracted text for user supplied teaching PDFs.

The PDF bytes are never persisted. Extracted pages live outside /uploads,
which FastAPI mounts publicly. Files expire after 24 hours and are removed
opportunistically on upload/read; a deployment can also schedule cleanup().
"""

import io
import json
import os
import re
import secrets
import time
from pathlib import Path

from pypdf import PdfReader

MAX_BYTES = 15 * 1024 * 1024
MAX_PAGES = 400
MAX_OCR_PAGES = 12
MAX_CONTEXT_CHARS = 19000
TTL_SECONDS = 24 * 60 * 60
STORE_DIR = Path(__file__).resolve().parent.parent / "private_sources"
_ID = re.compile(r"^[0-9a-f]{32}$")
_CHAPTER = re.compile(r"^(?:chapter|unit|section|глава|раздел|боб|фасл)\s*[\dIVXА-Яа-я]*[\s.:–-]+.{3,100}$", re.I)


class BookError(ValueError):
    """A safe error code for upload/selection responses."""


def _clean_title(value: str) -> str:
    title = Path(value.replace("\\", "/")).name.rsplit(".", 1)[0]
    title = " ".join(title.split())[:120]
    return title or "Book"


def _chapters(reader: PdfReader, pages: list[str]) -> list[dict]:
    found: list[dict] = []

    def visit(entries: list) -> None:
        for entry in entries:
            if isinstance(entry, list):
                visit(entry)
                continue
            try:
                number = reader.get_destination_page_number(entry) + 1
                title = " ".join(str(entry.title).split())[:120]
                if 1 <= number <= len(pages) and title:
                    found.append({"title": title, "start_page": number})
            except Exception:
                continue

    try:
        visit(reader.outline)
    except Exception:
        pass
    if not found:
        for number, text in enumerate(pages, 1):
            for line in text.splitlines()[:12]:
                title = " ".join(line.split())[:120]
                if _CHAPTER.match(title):
                    found.append({"title": title, "start_page": number})
                    break
    unique = {entry["start_page"]: entry for entry in found}
    starts = [unique[key] for key in sorted(unique)][:80]
    return [{**entry, "end_page": starts[i + 1]["start_page"] - 1 if i + 1 < len(starts) else len(pages)}
            for i, entry in enumerate(starts)]


def _ocr_page(raw: bytes, page_index: int) -> str:
    try:
        import pypdfium2 as pdfium
        import pytesseract
        from app.telegram.ocr import tesseract_available
        if not tesseract_available():
            raise BookError("ocr_unavailable")
        try:
            available = set(pytesseract.get_languages(config=""))
        except Exception as exc:
            raise BookError("ocr_unavailable") from exc
        languages = "+".join(code for code in ("rus", "eng") if code in available)
        if not languages:
            raise BookError("ocr_unavailable")
    except ImportError as exc:
        raise BookError("ocr_unavailable") from exc
    try:
        document = pdfium.PdfDocument(raw)
        try:
            image = document[page_index].render(scale=1.5).to_pil()
            return pytesseract.image_to_string(image, lang=languages, timeout=8).strip()
        finally:
            document.close()
    except Exception as exc:
        raise BookError("ocr_failed") from exc


def extract_pdf(raw: bytes, filename: str, content_type: str | None) -> dict:
    if not raw:
        raise BookError("empty_file")
    if len(raw) > MAX_BYTES:
        raise BookError("file_too_large")
    if not filename.lower().endswith(".pdf") or content_type not in ("application/pdf", "application/octet-stream"):
        raise BookError("unsupported_file")
    if not raw.startswith(b"%PDF-"):
        raise BookError("invalid_pdf")
    try:
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise BookError("encrypted_pdf")
        page_count = len(reader.pages)
        if not 1 <= page_count <= MAX_PAGES:
            raise BookError("page_limit")
        pages = []
        for page in reader.pages:
            pages.append((page.extract_text() or "")[:16000].strip())
        blank = [index for index, text in enumerate(pages) if len(text) < 20]
        if len(blank) > MAX_OCR_PAGES:
            raise BookError("too_many_scanned_pages")
        ocr_error: BookError | None = None
        for index in blank:
            try:
                pages[index] = _ocr_page(raw, index)[:16000]
            except BookError as exc:
                ocr_error = exc
        if not any(len(text.strip()) >= 20 for text in pages):
            raise ocr_error or BookError("no_text")
        unreadable = sum(len(text.strip()) < 20 for text in pages)
        metadata_title = str(reader.metadata.title or "").strip() if reader.metadata else ""
        if metadata_title.casefold() in {"untitled", "document", "microsoft word"}:
            metadata_title = ""
        title = " ".join(metadata_title.split())[:120] or _clean_title(filename)
        return {"title": title, "page_count": page_count, "pages": pages,
                "chapters": _chapters(reader, pages), "ocr_pages": len(blank) - unreadable,
                "unreadable_pages": unreadable}
    except BookError:
        raise
    except Exception as exc:
        raise BookError("invalid_pdf") from exc


def cleanup(now: float | None = None) -> None:
    if not STORE_DIR.exists():
        return
    cutoff = (now or time.time()) - TTL_SECONDS
    for path in STORE_DIR.glob("*.json"):
        if not _ID.fullmatch(path.stem):
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue


def save(owner_id: str, extracted: dict) -> dict:
    STORE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    cleanup()
    source_id = secrets.token_hex(16)
    record = {**extracted, "id": source_id, "owner_id": owner_id,
              "created_at": time.time(), "expires_at": time.time() + TTL_SECONDS}
    path = STORE_DIR / f"{source_id}.json"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False)
    return public_metadata(record)


def load(owner_id: str, source_id: str) -> dict:
    if not _ID.fullmatch(source_id):
        raise BookError("not_found")
    cleanup()
    try:
        record = json.loads((STORE_DIR / f"{source_id}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BookError("not_found") from exc
    if record.get("owner_id") != owner_id or record.get("expires_at", 0) <= time.time():
        raise BookError("not_found")
    return record


def public_metadata(record: dict) -> dict:
    return {key: record[key] for key in ("id", "title", "page_count", "chapters", "ocr_pages", "unreadable_pages", "expires_at")}


def select_context(record: dict, scope: str, topic: str | None,
                   chapter_index: int | None = None,
                   page_start: int | None = None, page_end: int | None = None) -> dict:
    total = record["page_count"]
    if scope == "all":
        start, end = 1, total
        section = None
    elif scope == "chapter":
        chapters = record["chapters"]
        if chapter_index is None or not 0 <= chapter_index < len(chapters):
            raise BookError("invalid_chapter")
        chapter = chapters[chapter_index]
        start, end = chapter["start_page"], chapter["end_page"]
        section = chapter["title"]
    elif scope == "pages":
        if page_start is None or page_end is None or not 1 <= page_start <= page_end <= total:
            raise BookError("invalid_pages")
        start, end = page_start, page_end
        section = None
    else:
        raise BookError("invalid_scope")

    candidates = [(number, record["pages"][number - 1]) for number in range(start, end + 1)
                  if len(record["pages"][number - 1].strip()) >= 20]
    words = {word.casefold() for word in re.findall(r"[^\W_]{4,}", topic or "")}
    scored = [(sum(text.casefold().count(word) for word in words), number, text)
              for number, text in candidates]
    if words and not any(score for score, _, _ in scored):
        raise BookError("topic_not_found")
    if words and any(score for score, _, _ in scored):
        ordered = sorted(scored, key=lambda entry: (-entry[0], entry[1]))
    else:
        # Spread context across the selected book/section instead of taking
        # only its opening pages when the teacher did not specify a topic.
        stride = max(1, len(scored) // 8)
        ordered = scored[::stride] + [entry for entry in scored if entry not in scored[::stride]]
    chunks, used, remaining = [], [], MAX_CONTEXT_CHARS
    for _, number, text in ordered:
        chunk = f"[Page {number}]\n{text[:4200]}\n"
        if len(chunk) > remaining:
            continue
        chunks.append(chunk)
        used.append(number)
        remaining -= len(chunk)
        if remaining < 500:
            break
    if not chunks:
        raise BookError("no_text")
    return {"text": "\n".join(chunks), "used_pages": sorted(used),
            "scope": scope, "page_start": start, "page_end": end,
            "chapter": section, "document_title": record["title"],
            "selection_is_excerpt": len(used) < end - start + 1,
            "unreadable_pages": [number for number in range(start, end + 1)
                                 if len(record["pages"][number - 1].strip()) < 20]}
