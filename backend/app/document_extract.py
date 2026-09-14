"""Extracts plain text from a teacher-uploaded source document (.pdf/.docx/
.txt) so it can be fed to the AI as the primary source for a "book-based"
konspekt (see ai_service.py's generate_konspekt_stream / _konspekt_prompt's
source_text argument).

Kept stateless and file-agnostic on purpose: nothing here writes to disk or
the database — the router that calls extract_source_text() hands the
resulting string straight back to the caller, who holds onto it client-side
and resubmits it with the generation request. The .docx branch is also used
by routers/curriculum.py's /parse-docx (topic-list upload) — this module is
the single place that logic lives now, instead of being duplicated there.
"""

import io

from app.ai_service import fix_legacy_tajik_glyphs
from app.logger import get_logger

logger = get_logger(__name__)

# A sane upper bound on how much of an uploaded document is even worth
# holding onto client-side — not the AI prompt budget itself anymore
# (see ai_service.py's _select_relevant_excerpt, which windows this down
# further to whatever actually fits the model's prompt, centered on the
# topic instead of always keeping just the start of the document).
MAX_SOURCE_CHARS = 60000


def extract_text_from_docx(raw: bytes) -> str:
    """Pulls every paragraph and table cell out of a .docx, in document
    order. Same extraction shape routers/curriculum.py's /parse-docx always
    used (paragraphs first, then table cells) — moved here so both callers
    share one implementation instead of drifting apart."""
    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(raw))
    lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    lines.append(cell.text.strip())
    return fix_legacy_tajik_glyphs("\n".join(lines))


def extract_text_from_pdf(raw: bytes) -> str:
    """Page-by-page text extraction via pypdf. Scanned/image-only PDFs with
    no embedded text layer will yield an empty string here — the caller
    treats that the same as any other empty document."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw))
    pages = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception as e:
            # A single malformed page shouldn't sink the whole document —
            # skip it and keep going.
            logger.warning(f"PDF page extraction failed, skipping page: {e}")
            text = ""
        if text.strip():
            pages.append(text.strip())
    return fix_legacy_tajik_glyphs("\n\n".join(pages))


def extract_text_from_txt(raw: bytes) -> str:
    """Decodes a plain-text upload, trying UTF-8 first (the overwhelming
    common case) and falling back to legacy Cyrillic/Latin encodings a
    teacher's older document might actually be saved in, before giving up."""
    for encoding in ("utf-8", "cp1251", "latin-1"):
        try:
            return fix_legacy_tajik_glyphs(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    # Last resort: decode with replacement characters rather than fail
    # outright — the caller's empty-text check still catches a truly
    # unreadable file.
    return fix_legacy_tajik_glyphs(raw.decode("utf-8", errors="replace"))


_EXTRACTORS = {
    ".pdf": extract_text_from_pdf,
    ".docx": extract_text_from_docx,
    ".txt": extract_text_from_txt,
}


def extract_source_text(filename: str, raw: bytes) -> tuple[str, bool]:
    """Dispatches to the right extractor by extension, then trims to
    MAX_SOURCE_CHARS. Returns (text, was_truncated). Raises ValueError (the
    router turns this into a 400/422) for an unsupported extension or a
    document with no extractable text — e.g. a scanned image-only PDF."""
    name = (filename or "").lower()
    ext = next((e for e in _EXTRACTORS if name.endswith(e)), None)
    if ext is None:
        raise ValueError(f"Unsupported file type: {filename}")

    try:
        text = _EXTRACTORS[ext](raw)
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Document extraction failed for {filename}: {e}", exc_info=True)
        raise ValueError("parse_error") from e

    text = text.strip()
    if not text:
        raise ValueError("empty_document")

    truncated = len(text) > MAX_SOURCE_CHARS
    if truncated:
        text = text[:MAX_SOURCE_CHARS]
    return text, truncated
