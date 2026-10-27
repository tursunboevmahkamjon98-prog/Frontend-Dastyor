"""Receipt reading and cross-checking.

What this module is for and what it is emphatically not for
-----------------------------------------------------------

It extracts fields from a payment receipt so a human reviewer sees the
numbers without squinting, and it raises flags when something does not
line up. That is the whole job.

It does **not** verify a payment, and nothing in this file sets a flag
that could be mistaken for verification. A receipt is a picture: it can
be edited, re-sent, or belong to somebody else's transfer entirely. The
only evidence that money arrived is the receiving account itself, which
this software has no access to and does not claim to have. Every output
here is an aid to the admin's own check, which is why
:func:`summarize_for_admin` always ends with the reminder that the admin
must confirm arrival independently.

Three text sources, in order of how much they can be trusted:

1. **PDF text layer** (``pypdf``, already a dependency). A bank's own PDF
   carries real characters, so there is no recognition step and no
   recognition error. Highest confidence.
2. **Tesseract** over an image, when the binary is installed.
3. **Nothing** — ``tesseract`` absent, or an unreadable image. This is a
   supported outcome, not a crash: the scan comes back with
   ``engine="unavailable"``, zero confidence and an explicit warning, and
   the admin reviews the attached image by eye exactly as before. A
   payment flow must not stop because an OCR package is missing.
"""

from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from app.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------
# Optional engines. Both are probed once, at import, and their absence is
# a degraded mode rather than an error.
# ---------------------------------------------------------------------

# Pillow and pytesseract are probed SEPARATELY. An earlier version
# imported them in one try-block, so a machine with Pillow but no
# pytesseract — the normal state of a dev box — silently lost Pillow
# too. That was masked only because scan_image() checks for tesseract
# first and returns before touching an image. It stops being masked the
# moment anything else needs Pillow, such as the dimension guard below.
try:  # pragma: no cover - depends on the host image
    from PIL import Image, ImageFilter, ImageOps

    _PIL_OK = True
except Exception:  # pragma: no cover
    Image = ImageFilter = ImageOps = None  # type: ignore[assignment]
    _PIL_OK = False

try:  # pragma: no cover - depends on the host image
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]

try:  # pragma: no cover
    from pypdf import PdfReader

    _PDF_OK = True
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore[assignment]
    _PDF_OK = False


# Tajik bank receipts are written in Cyrillic, with Latin for card
# numbers and reference codes. "tgk" traineddata is not in Debian's
# tesseract-ocr-* packages, so rus+eng is the realistic pair; the Tajik
# letters ғ қ ҳ ҷ ӣ ӯ are not in `rus`, which is a known and accepted
# limitation — they appear in names and labels, not in the amount, the
# reference or the date, which are the fields a reviewer needs.
TESSERACT_LANGS = "rus+eng"

# Hard ceiling on how many pixels a receipt may decode to.
#
# Pillow's own guard is far too loose for this host: it only raises
# above 2x MAX_IMAGE_PIXELS (~179 million) and merely warns below that,
# so a 157 KB PNG declaring 12000x12000 passes the 8 MB upload check,
# passes Pillow, and then costs hundreds of megabytes across the
# grayscale/autocontrast/sharpen copies in _preprocess. The deployment
# target is a 2 GB VPS whose Dockerfile already records one
# out-of-memory incident, and nothing rate-limits how many receipts a
# linked user may send.
#
# 40 megapixels is ~8x the largest real phone photo and still only
# ~40 MB as 8-bit grey, so no genuine receipt is refused.
MAX_RECEIPT_PIXELS = 40_000_000

# Ceiling on how much extracted text the field patterns run over. See
# extract_fields for why this is applied before scanning, not after.
MAX_RECEIPT_TEXT_CHARS = 20_000

WARNING_CODES = (
    "ocr_unavailable",
    "no_text",
    "amount_missing",
    "amount_mismatch",
    "currency_unexpected",
    "sender_missing",
    "recipient_missing",
    "recipient_mismatch",
    "reference_missing",
    "reference_duplicate",
    "date_missing",
    "low_confidence",
    "status_not_successful",
)


@dataclass
class ReceiptScan:
    """Everything read off one receipt, plus how much to trust it."""

    engine: str = "unavailable"
    raw_text: str = ""

    amount_dirams: int | None = None
    currency: str | None = None
    sender: str | None = None
    recipient: str | None = None
    reference: str | None = None
    paid_at_text: str | None = None
    status_text: str | None = None

    # 0-100. A heuristic over which fields were found and how the text was
    # obtained — not a probability, and never a basis for auto-approval.
    confidence: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def reference_normalized(self) -> str | None:
        return normalize_reference(self.reference)

    def add_warning(self, code: str) -> None:
        if code not in self.warnings:
            self.warnings.append(code)


# ---------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------

# Non-breaking, thin and zero-width spaces. Bank PDFs put these between
# thousands groups and NFKC leaves several of them alone, so without this
# the amount patterns below read "1 000,00" as two separate numbers.
_SPACE_LIKE = (
    " ", " ", " ", " ", " ", "​", "﻿",
)


def normalize_text(text: str) -> str:
    """Fold the characters OCR confuses before any pattern runs.

    Done once, centrally, because otherwise every regex below needs its
    own alternation for a non-breaking space and three dash variants.
    """
    out = unicodedata.normalize("NFKC", text or "")
    for ch in _SPACE_LIKE:
        out = out.replace(ch, " ")
    out = out.replace("–", "-").replace("—", "-").replace("−", "-")
    out = out.replace("«", '"').replace("»", '"')
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def normalize_reference(reference: str | None) -> str | None:
    """Reduce a reference to its comparable core.

    Upper-cased and stripped of separators so ``TXN-1234 5678`` and
    ``txn12345678`` are recognised as the same transfer. This is the value
    the duplicate check and the unique index on approved rows both use, so
    two spellings of one bank reference cannot be credited twice.
    """
    if not reference:
        return None
    core = re.sub(r"[^0-9A-Za-zА-Яа-яЁё]", "", reference).upper()
    return core or None


# ---------------------------------------------------------------------
# Amount
# ---------------------------------------------------------------------

CURRENCY_TOKENS = {
    "TJS": "TJS", "ТЧС": "TJS", "СМН": "TJS", "SM": "TJS",
    "СОМОНӢ": "TJS", "СОМОНИ": "TJS", "СОМОНӤ": "TJS",
    "RUB": "RUB", "РУБ": "RUB", "РУБЛЬ": "RUB", "₽": "RUB",
    "USD": "USD", "ДОЛЛАР": "USD", "$": "USD",
    "EUR": "EUR", "ЕВРО": "EUR", "€": "EUR",
}

_CURRENCY_ALTERNATION = "|".join(
    sorted((re.escape(k) for k in CURRENCY_TOKENS), key=len, reverse=True)
)

# A money-shaped number: optional thousands groups, optional 1-2 decimals.
_NUMBER = r"\d{1,3}(?:[ .,']\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?"

_AMOUNT_WITH_CURRENCY = re.compile(
    rf"(?P<num>{_NUMBER})\s*(?P<cur>{_CURRENCY_ALTERNATION})\b", re.IGNORECASE
)
_CURRENCY_WITH_AMOUNT = re.compile(
    rf"(?P<cur>{_CURRENCY_ALTERNATION})\s*(?P<num>{_NUMBER})", re.IGNORECASE
)

AMOUNT_LABELS = (
    "маблағ", "маблаг", "мablag", "сумма", "сумма перевода", "сумма операции",
    "amount", "total", "итого", "к оплате", "списано", "зачислено",
    "интиқол", "интикол", "пардохт",
)

_AMOUNT_NEAR_LABEL = re.compile(
    rf"(?:{'|'.join(re.escape(l) for l in AMOUNT_LABELS)})"
    rf"[^0-9\n]{{0,40}}(?P<num>{_NUMBER})",
    re.IGNORECASE,
)


def _to_dirams(raw: str) -> int | None:
    """Parse a money-shaped string into integer dirams.

    The hard part is that ``1.234`` is ambiguous: a thousands separator in
    one locale and a decimal point in another. Resolved by shape — exactly
    three digits after a single separator with no other separator present
    is read as thousands, which is what Tajik and Russian receipts mean.
    """
    text = (raw or "").strip().replace(" ", "").replace("'", "")
    if not text:
        return None

    dots, commas = text.count("."), text.count(",")

    if dots and commas:
        # Both present: the rightmost one is the decimal separator.
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif commas == 1:
        tail = text.split(",")[1]
        text = text.replace(",", "") if len(tail) == 3 else text.replace(",", ".")
    elif commas > 1:
        text = text.replace(",", "")
    elif dots == 1:
        tail = text.split(".")[1]
        if len(tail) == 3:
            text = text.replace(".", "")
    elif dots > 1:
        text = text.replace(".", "")

    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if value < 0:
        value = -value
    dirams = int((value * 100).to_integral_value(rounding="ROUND_HALF_UP"))
    # A receipt for more than a million somoni, or for nothing at all, is
    # a misread rather than a transfer.
    if dirams <= 0 or dirams > 100_000_000:
        return None
    return dirams


def extract_amount(text: str) -> tuple[int | None, str | None]:
    """Best amount and currency from receipt text.

    Preference order, strongest evidence first: a number sitting next to a
    currency token, then a number next to an amount label, then the
    largest money-shaped number in the text. The last one is a guess and
    is reflected in the confidence score rather than presented as fact.
    """
    for pattern in (_AMOUNT_WITH_CURRENCY, _CURRENCY_WITH_AMOUNT):
        for match in pattern.finditer(text):
            dirams = _to_dirams(match.group("num"))
            if dirams is not None:
                token = match.group("cur").upper()
                return dirams, CURRENCY_TOKENS.get(token, token)

    for match in _AMOUNT_NEAR_LABEL.finditer(text):
        dirams = _to_dirams(match.group("num"))
        if dirams is not None:
            return dirams, None

    candidates: list[int] = []
    for match in re.finditer(_NUMBER, text):
        raw = match.group(0)
        # A bare integer with no separator is usually a card fragment, a
        # phone number or a reference, not an amount.
        if not re.search(r"[.,]", raw):
            continue
        dirams = _to_dirams(raw)
        if dirams is not None:
            candidates.append(dirams)
    if candidates:
        return max(candidates), None

    return None, None


# ---------------------------------------------------------------------
# Parties, reference, date, status
# ---------------------------------------------------------------------

def _labelled_value(text: str, labels: tuple[str, ...], *, max_len: int = 80) -> str | None:
    for label in labels:
        pattern = re.compile(
            rf"{re.escape(label)}\s*[:\-]?\s*(?P<val>[^\n]{{2,{max_len}}})",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            value = match.group("val").strip(" .,:;-\t")
            value = re.sub(r"\s{2,}", " ", value)
            if value and not re.fullmatch(r"[\W_]+", value):
                return value[:max_len]
    return None


SENDER_LABELS = (
    "фиристанда", "фиристодашуда", "аз ҳисоби", "аз хисоби",
    "отправитель", "плательщик", "от кого", "со счёта", "со счета",
    "sender", "from account", "payer", "from",
)

RECIPIENT_LABELS = (
    "қабулкунанда", "кабулкунанда", "гиранда", "ба ҳисоби", "ба хисоби",
    "получатель", "получателю", "кому", "на счёт", "на счет", "в пользу",
    "recipient", "beneficiary", "to account", "payee", "to",
)

REFERENCE_LABELS = (
    "рақами амалиёт", "раками амалиёт", "рақами интиқол", "рақами чек",
    "номер операции", "номер транзакции", "номер документа", "номер чека",
    "код операции", "идентификатор", "квитанция №", "ссылка",
    "transaction id", "transaction number", "reference", "ref no", "ref",
    "receipt no", "receipt number", "operation id", "rrn", "утрн",
)

STATUS_SUCCESS_TOKENS = (
    "муваффақ", "муваффак", "иҷро шуд", "ичро шуд", "қабул шуд",
    "успешно", "выполнено", "исполнено", "проведено", "завершено",
    "success", "successful", "completed", "approved", "paid", "done", "ok",
)

STATUS_FAILURE_TOKENS = (
    "ноком", "рад шуд", "иҷро нашуд",
    "отклонено", "отказано", "не выполнено", "ошибка", "отменено",
    "failed", "declined", "rejected", "cancelled", "canceled", "error",
    "pending", "в обработке", "дар раванд",
)

# Internal spaces are allowed because banks group a long reference
# ("TXN-4471 9920"); stopping at the first space truncates it, and a
# truncated reference both weakens duplicate detection and can collide
# with a different reference sharing the same prefix. normalize_reference
# strips the separators afterwards, so the grouping costs nothing.
_REFERENCE_VALUE = re.compile(r"[0-9A-Za-z](?:[0-9A-Za-z\-/]| (?=[0-9A-Za-z]))*")

_DATE_PATTERNS = (
    re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}(?:[ ,]+\d{1,2}:\d{2}(?::\d{2})?)?\b"),
    re.compile(r"\b\d{4}[./-]\d{1,2}[./-]\d{1,2}(?:[ ,T]+\d{1,2}:\d{2}(?::\d{2})?)?\b"),
    re.compile(
        r"\b\d{1,2}\s+(?:янв|фев|мар|апр|ма[йя]|июн|июл|авг|сен|окт|ноя|дек|"
        r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[а-яa-z.]*\s+\d{2,4}"
        r"(?:[ ,]+\d{1,2}:\d{2})?\b",
        re.IGNORECASE,
    ),
)


def extract_reference(text: str) -> str | None:
    for label in REFERENCE_LABELS:
        pattern = re.compile(
            rf"{re.escape(label)}\s*[:#\-]?\s*(?P<val>[0-9A-Za-z][0-9A-Za-z\-/ ]{{4,40}})",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            value = match.group("val").strip(" .,:;-")
            inner = _REFERENCE_VALUE.search(value)
            if inner:
                candidate = inner.group(0).strip()
                # Five alphanumerics is the floor for something that can
                # identify a transfer; below that it is a label fragment
                # or a stray digit, and recording it as "the reference"
                # would make the duplicate check compare noise.
                if len(re.sub(r"[^0-9A-Za-z]", "", candidate)) >= 5:
                    return candidate[:40]

    # No label matched: fall back to a long digit/alnum run, which is what
    # an unlabelled reference looks like. Deliberately conservative — 10+
    # characters — so a date or a card's last four never lands here.
    match = re.search(r"\b(?=[0-9A-Za-z\-]*\d)[0-9A-Za-z]{10,40}\b", text)
    return match.group(0) if match else None


def extract_datetime_text(text: str) -> str | None:
    for pattern in _DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0).strip()
    return None


def extract_status(text: str) -> tuple[str | None, bool | None]:
    """Return the status words found, and whether they read as success.

    ``None`` for the second element means "no status wording on the
    receipt", which is different from "the receipt says it failed".
    """
    lowered = text.lower()
    for token in STATUS_FAILURE_TOKENS:
        if token in lowered:
            return token, False
    for token in STATUS_SUCCESS_TOKENS:
        if token in lowered:
            return token, True
    return None, None


def extract_fields(raw_text: str, *, engine: str = "text") -> ReceiptScan:
    """Pure text-to-fields step.

    Separated from image handling so the whole extraction can be tested
    with string fixtures and no tesseract, no Pillow and no network.
    """
    # Cap BEFORE scanning, not just before storing.
    #
    # An earlier version truncated only the copy it saved, then ran a
    # dozen regexes over the full text. A PDF with a megabyte-long text
    # layer therefore cost a megabyte of scanning per pattern, on a host
    # where nothing rate-limits how many receipts a linked user sends.
    #
    # A receipt is a page. Every field worth having — amount, reference,
    # date, the two parties — is in the first few thousand characters,
    # so nothing real is lost by stopping there.
    text = normalize_text(raw_text)[:MAX_RECEIPT_TEXT_CHARS]
    scan = ReceiptScan(engine=engine, raw_text=text[:8000])

    if not text:
        scan.add_warning("no_text")
        return scan

    scan.amount_dirams, scan.currency = extract_amount(text)
    scan.sender = _labelled_value(text, SENDER_LABELS)
    scan.recipient = _labelled_value(text, RECIPIENT_LABELS)
    scan.reference = extract_reference(text)
    scan.paid_at_text = extract_datetime_text(text)
    scan.status_text, _ = extract_status(text)

    scan.confidence = score_confidence(scan)
    return scan


def score_confidence(scan: ReceiptScan) -> int:
    """How complete the extraction is, 0-100.

    A completeness measure, not a probability of authenticity — a
    perfectly forged receipt scores 100. Weighted so the fields a
    reviewer actually reconciles against a bank statement (amount,
    reference) count for most of it.
    """
    if not scan.raw_text:
        return 0
    score = 0
    if scan.amount_dirams is not None:
        score += 35
        if scan.currency:
            score += 10
    if scan.reference:
        score += 20
    if scan.paid_at_text:
        score += 15
    if scan.recipient:
        score += 10
    if scan.sender:
        score += 5
    if scan.status_text:
        score += 5
    # A PDF's own text layer was not recognised, it was read; an image was
    # recognised and can be wrong per-character.
    if scan.engine == "pdf-text":
        score = min(100, score + 5)
    elif scan.engine.startswith("tesseract"):
        score = max(0, score - 5)
    return max(0, min(100, score))


# ---------------------------------------------------------------------
# Image / PDF entry points
# ---------------------------------------------------------------------

def tesseract_available() -> bool:
    if not (_PIL_OK and pytesseract is not None):
        return False
    try:  # pragma: no cover - depends on the host image
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _preprocess(image):  # pragma: no cover - needs Pillow + a real image
    """Grayscale, upscale, autocontrast, sharpen.

    Phone screenshots of banking apps are small and low-contrast; without
    the 2x upscale tesseract routinely drops the decimals off an amount,
    which is the one field that must not be wrong.
    """
    image = ImageOps.exif_transpose(image)
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")
    image = ImageOps.grayscale(image)
    width, height = image.size
    if max(width, height) < 1600:
        scale = min(3.0, 1600 / max(width, height))
        image = image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
    image = ImageOps.autocontrast(image)
    return image.filter(ImageFilter.SHARPEN)


def image_pixel_count(data: bytes) -> int | None:
    """Declared pixel count from the header, without decoding.

    ``Image.open`` is lazy: it parses the header and stops. That is what
    makes the size guard cheap — an oversized receipt costs a header
    parse, never a bitmap. Returns None when the header cannot be read
    or Pillow is absent.
    """
    if not _PIL_OK:
        return None
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            return width * height
    except Exception:
        return None


def scan_image(data: bytes) -> ReceiptScan:
    """OCR an image, degrading to ``engine="unavailable"`` if it cannot."""
    # Size first, and independently of whether tesseract is installed:
    # the refusal should not depend on which optional package happens to
    # be present, and this way the guard is reachable in tests.
    pixels = image_pixel_count(data)
    if pixels is not None and pixels > MAX_RECEIPT_PIXELS:
        logger.warning(
            f"Refusing a receipt declaring {pixels:,} pixels, over the "
            f"{MAX_RECEIPT_PIXELS:,} limit"
        )
        scan = ReceiptScan(engine="image-too-large")
        scan.add_warning("no_text")
        return scan

    if not tesseract_available():
        scan = ReceiptScan(engine="unavailable")
        scan.add_warning("ocr_unavailable")
        return scan

    try:  # pragma: no cover - needs the binary
        with Image.open(io.BytesIO(data)) as image:
            prepared = _preprocess(image)
            text = pytesseract.image_to_string(prepared, lang=TESSERACT_LANGS)
    except Exception as e:  # pragma: no cover
        logger.warning(f"Receipt OCR failed: {type(e).__name__}: {e}")
        scan = ReceiptScan(engine="tesseract-error")
        scan.add_warning("no_text")
        return scan

    return extract_fields(text, engine=f"tesseract:{TESSERACT_LANGS}")


def scan_pdf(data: bytes) -> ReceiptScan:
    """Read a PDF's text layer; fall back to its first page as an image."""
    if not _PDF_OK:
        scan = ReceiptScan(engine="unavailable")
        scan.add_warning("ocr_unavailable")
        return scan
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = reader.pages[:3]
        text = "\n".join((page.extract_text() or "") for page in pages)
    except Exception as e:
        logger.warning(f"Receipt PDF parse failed: {type(e).__name__}: {e}")
        scan = ReceiptScan(engine="pdf-error")
        scan.add_warning("no_text")
        return scan

    if len(normalize_text(text)) < 12:
        # A scanned-to-PDF receipt has no text layer. Nothing further to
        # try here without a rasteriser, which this image does not carry.
        scan = ReceiptScan(engine="pdf-no-text")
        scan.add_warning("no_text")
        return scan

    return extract_fields(text, engine="pdf-text")


def scan_receipt(data: bytes, mime: str | None) -> ReceiptScan:
    """Dispatch on content type."""
    kind = (mime or "").lower()
    if "pdf" in kind or data[:5] == b"%PDF-":
        return scan_pdf(data)
    return scan_image(data)


# ---------------------------------------------------------------------
# Cross-checks
# ---------------------------------------------------------------------

AMOUNT_TOLERANCE_DIRAMS = 0


def _fuzzy_contains(haystack: str | None, needle: str | None) -> bool:
    """Loose containment for a recipient name read by OCR.

    Compares only letters and digits, case-folded, because OCR routinely
    mangles punctuation and spacing in a name while getting the letters
    right.
    """
    if not haystack or not needle:
        return False
    def fold(value: str) -> str:
        return re.sub(r"[^0-9a-zа-яёғқҳҷӣӯ]", "", value.lower())
    a, b = fold(haystack), fold(needle)
    if not a or not b:
        return False
    if b in a or a in b:
        return True
    # A card number is usually masked differently on each side
    # ("1234****5678" vs "...5678"), so compare the trailing digits too.
    digits_a = re.sub(r"\D", "", haystack)
    digits_b = re.sub(r"\D", "", needle)
    if len(digits_a) >= 4 and len(digits_b) >= 4:
        return digits_a[-4:] == digits_b[-4:]
    return False


def cross_check(
    scan: ReceiptScan,
    *,
    requested_dirams: int,
    expected_recipient: str | None = None,
    duplicate_of: str | None = None,
    expected_currency: str = "TJS",
) -> ReceiptScan:
    """Add warnings for everything that does not line up.

    Mutates and returns ``scan`` so the caller keeps one object. Each
    warning is a reason for the admin to look harder; none of them, and no
    absence of them, approves anything.
    """
    if scan.engine == "unavailable":
        scan.add_warning("ocr_unavailable")

    if scan.amount_dirams is None:
        scan.add_warning("amount_missing")
    elif abs(scan.amount_dirams - requested_dirams) > AMOUNT_TOLERANCE_DIRAMS:
        scan.add_warning("amount_mismatch")

    if scan.currency and scan.currency != expected_currency:
        scan.add_warning("currency_unexpected")

    if not scan.sender:
        scan.add_warning("sender_missing")

    if expected_recipient:
        if not scan.recipient:
            scan.add_warning("recipient_missing")
        elif not _fuzzy_contains(scan.recipient, expected_recipient):
            scan.add_warning("recipient_mismatch")
    elif not scan.recipient:
        scan.add_warning("recipient_missing")

    if not scan.reference:
        scan.add_warning("reference_missing")
    if duplicate_of:
        scan.add_warning("reference_duplicate")

    if not scan.paid_at_text:
        scan.add_warning("date_missing")

    _, succeeded = extract_status(scan.raw_text)
    if succeeded is False:
        scan.add_warning("status_not_successful")

    if scan.confidence < 50:
        scan.add_warning("low_confidence")

    return scan


def summarize_for_user(scan: ReceiptScan, language: str | None = "tg") -> str:
    """One short, non-alarming line for the teacher.

    Deliberately thin: the teacher does not need the warning list, and
    showing "amount mismatch" to somebody who typed the right number and
    whose screenshot was merely blurry reads as an accusation.
    """
    if scan.amount_dirams is None:
        return ""
    from app.telegram.texts import currency, fmt_somoni, normalize_lang

    lang = normalize_lang(language)
    amount = fmt_somoni(scan.amount_dirams, lang)
    prefix = {
        "tg": "Дар расид хонда шуд",
        "ru": "На квитанции прочитано",
        "en": "Read from the receipt",
    }[lang]
    return f"{prefix}: {amount} {currency(lang)}"


def summarize_for_admin(scan: ReceiptScan, language: str | None = None) -> str:
    """The reviewer-facing block: fields, confidence, flags, and the caveat.

    Language defaults to the admin catalogue's default (Russian) rather
    than the teacher's locale: the reviewer is the owner, not the person
    who sent the receipt.

    The closing disclaimer is not optional and is not conditional on the
    warnings. A clean, high-confidence scan is exactly when a reviewer is
    most tempted to approve on the strength of the picture alone, so the
    reminder that only the receiving account proves anything has to be
    there every single time.
    """
    from app.telegram.texts import admin_t

    # The warnings themselves are already in the caption's one-line
    # "Предупреждения: ..." field (see bot.py's _admin_caption) - listing
    # them again here as bullets was pure duplication and made every
    # uncertain receipt's message twice as long for no new information.
    lines: list[str] = [
        admin_t("ocr_line", language, engine=scan.engine,
                confidence=scan.confidence),
        "",
        admin_t("disclaimer", language),
    ]
    return "\n".join(lines)
