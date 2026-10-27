"""Telegram payment bot: everything testable without a database.

Covers receipt parsing, cross-check warnings, upload validation, admin
authorization, token shape and secret scrubbing. Written in the same
plain-script style as the other files in this directory (print PASS/FAIL,
collect failures, non-zero exit) so it runs the same way:

    python tests/test_telegram_unit.py

No network, no database, no Telegram, no tesseract. The OCR engine is
absent on purpose on most machines, which is itself one of the cases
under test — the pipeline must degrade rather than crash.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# app.config.Settings has required fields; these keep the import graph
# loadable without a real environment. Nothing below reaches a database.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/x")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://u:p@localhost:5432/x")
os.environ.setdefault("SECRET_KEY", "test-only-not-a-real-secret")
os.environ.setdefault("AI_API_KEY", "test-only")

from app.telegram import ocr, service  # noqa: E402
from app.telegram.api import scrub  # noqa: E402
from app.telegram.bot import PaymentBot  # noqa: E402
from app.telegram.config import TelegramSettings, get_telegram_settings  # noqa: E402
from app.telegram.texts import fmt_somoni, normalize_lang, t  # noqa: E402

FAIL = []


def check(name, condition, detail=""):
    print(("  PASS  " if condition else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not condition:
        FAIL.append(name)


def section(title):
    print()
    print(title)


# ---------------------------------------------------------------------
# Receipt field extraction
# ---------------------------------------------------------------------

TAJIK_RECEIPT = """
Амонатбонк
Интиколи пул аз корт ба корт
Маблаг: 500,00 TJS
Фиристанда: ТУРСУНБОЕВ М.
Кабулкунанда: DASTYOR LLC
Раками амалиёт: TXN-4471 9920
Сана: 19.10.2026 14:32
Холат: Муваффак
"""

RUSSIAN_RECEIPT = """
Банк Эсхата
Перевод с карты на карту
Сумма перевода: 1 250,50 смн
Отправитель: Иванов И.И.
Получатель: 5058 **** **** 1234
Номер операции: 998877665544
Дата: 2026-10-19 09:15:02
Статус: Успешно
"""

DECLINED_RECEIPT = """
Сумма: 300.00 TJS
Номер операции: 11223344556
Статус: Отклонено
Дата: 19.10.2026 10:00
"""

BLANK_RECEIPT = "   \n  \n "


def test_extraction():
    section("Receipt field extraction")

    tj = ocr.extract_fields(TAJIK_RECEIPT)
    check("tajik: amount read as 500.00 somoni", tj.amount_dirams == 50000,
          f"got {tj.amount_dirams}")
    check("tajik: currency normalised to TJS", tj.currency == "TJS", str(tj.currency))
    check("tajik: sender found", tj.sender is not None and "ТУРСУНБОЕВ" in tj.sender,
          repr(tj.sender))
    check("tajik: recipient found", tj.recipient == "DASTYOR LLC", repr(tj.recipient))
    check("tajik: full grouped reference kept, not truncated at the space",
          tj.reference == "TXN-4471 9920", repr(tj.reference))
    check("tajik: date+time found", tj.paid_at_text == "19.10.2026 14:32",
          repr(tj.paid_at_text))
    check("tajik: status wording found", tj.status_text is not None, repr(tj.status_text))
    check("tajik: confidence high on a complete receipt", tj.confidence >= 80,
          str(tj.confidence))

    ru = ocr.extract_fields(RUSSIAN_RECEIPT)
    check("russian: thousands-separated amount read", ru.amount_dirams == 125050,
          f"got {ru.amount_dirams}")
    check("russian: 'смн' recognised as TJS", ru.currency == "TJS", str(ru.currency))
    check("russian: masked card recipient kept",
          ru.recipient is not None and "1234" in ru.recipient, repr(ru.recipient))
    check("russian: reference found", ru.reference == "998877665544", repr(ru.reference))

    blank = ocr.extract_fields(BLANK_RECEIPT)
    check("blank receipt yields no_text warning", "no_text" in blank.warnings,
          str(blank.warnings))
    check("blank receipt has zero confidence", blank.confidence == 0,
          str(blank.confidence))
    check("blank receipt has no amount", blank.amount_dirams is None)


def test_amount_shapes():
    section("Amount parsing (locale separator ambiguity)")

    cases = [
        ("500,00", 50000),
        ("1 250,50", 125050),
        ("1.234,56", 123456),
        ("1,234.56", 123456),
        ("0,50", 50),
        ("99.99", 9999),
        # One separator with exactly three digits after it is a thousands
        # group, which is what Tajik and Russian receipts mean.
        ("1.234", 123400),
        ("1,234", 123400),
        ("", None),
        ("abc", None),
        ("0", None),
        ("0,00", None),
    ]
    for raw, expected in cases:
        got = ocr._to_dirams(raw)
        check(f"_to_dirams({raw!r}) == {expected}", got == expected, f"got {got}")


def test_reference_normalisation():
    section("Reference normalisation and duplicate equivalence")

    pairs = [
        ("TXN-4471 9920", "txn44719920", True),
        ("A/B-12345", "ab12345", True),
        ("998877665544", "998877665544", True),
        ("TXN-0001", "TXN-0002", False),
    ]
    for a, b, same in pairs:
        got = ocr.normalize_reference(a) == ocr.normalize_reference(b)
        check(f"{a!r} and {b!r} {'match' if same else 'differ'}", got == same,
              f"{ocr.normalize_reference(a)} vs {ocr.normalize_reference(b)}")

    check("normalize_reference(None) is None", ocr.normalize_reference(None) is None)
    check("normalize_reference('---') is None", ocr.normalize_reference("---") is None)


def test_cross_check_warnings():
    section("Cross-check warnings")

    exact = ocr.cross_check(
        ocr.extract_fields(TAJIK_RECEIPT),
        requested_dirams=50000,
        expected_recipient="DASTYOR LLC",
    )
    check("matching receipt raises no warnings", exact.warnings == [], str(exact.warnings))

    mismatch = ocr.cross_check(
        ocr.extract_fields(TAJIK_RECEIPT),
        requested_dirams=20000,
        expected_recipient="DASTYOR LLC",
    )
    check("amount mismatch is flagged", "amount_mismatch" in mismatch.warnings,
          str(mismatch.warnings))

    wrong_recipient = ocr.cross_check(
        ocr.extract_fields(TAJIK_RECEIPT),
        requested_dirams=50000,
        expected_recipient="SOMEBODY ELSE",
    )
    check("wrong recipient is flagged",
          "recipient_mismatch" in wrong_recipient.warnings,
          str(wrong_recipient.warnings))

    duplicate = ocr.cross_check(
        ocr.extract_fields(TAJIK_RECEIPT),
        requested_dirams=50000,
        expected_recipient="DASTYOR LLC",
        duplicate_of="DP-AAAAAA",
    )
    check("duplicate reference is flagged",
          "reference_duplicate" in duplicate.warnings, str(duplicate.warnings))

    declined = ocr.cross_check(
        ocr.extract_fields(DECLINED_RECEIPT), requested_dirams=30000
    )
    check("a receipt that says 'Отклонено' is flagged",
          "status_not_successful" in declined.warnings, str(declined.warnings))

    # A masked card on the receipt vs the configured one written
    # differently must still match on the trailing digits.
    masked = ocr.cross_check(
        ocr.extract_fields(RUSSIAN_RECEIPT),
        requested_dirams=125050,
        expected_recipient="5058********1234",
    )
    check("masked card recipient matches on trailing digits",
          "recipient_mismatch" not in masked.warnings, str(masked.warnings))

    unreadable = ocr.cross_check(
        ocr.ReceiptScan(engine="unavailable"), requested_dirams=50000
    )
    check("unreadable receipt flags ocr_unavailable",
          "ocr_unavailable" in unreadable.warnings, str(unreadable.warnings))
    check("unreadable receipt flags amount_missing",
          "amount_missing" in unreadable.warnings)
    check("unreadable receipt flags low_confidence",
          "low_confidence" in unreadable.warnings)


def test_ocr_never_confirms():
    section("OCR never confirms a payment")

    scan = ocr.cross_check(
        ocr.extract_fields(TAJIK_RECEIPT),
        requested_dirams=50000,
        expected_recipient="DASTYOR LLC",
    )
    # A perfect, warning-free, 100%-confidence scan must still carry no
    # field that any caller could read as "verified".
    fields = set(vars(scan).keys())
    forbidden = {"verified", "confirmed", "approved", "valid", "is_paid", "trusted"}
    check("ReceiptScan exposes no verified/confirmed/approved flag",
          not (fields & forbidden), str(fields & forbidden))

    # The admin summary defaults to Russian: the reviewer is the owner,
    # not the Tajik-speaking teacher who sent the receipt.
    admin_text = ocr.summarize_for_admin(scan)
    check("admin summary warns the admin must check the account himself",
          "проверьте сами" in admin_text, admin_text[-80:])
    check("admin summary states OCR does not confirm payment",
          "не подтверждает оплату" in admin_text, admin_text[:80])

    # The disclaimer is unconditional. A clean, warning-free,
    # 100%-confidence scan is exactly when a reviewer is most tempted to
    # approve on the picture alone, so it must still be there.
    check("the disclaimer survives a perfect scan with zero warnings",
          scan.warnings == [] and "не подтверждает оплату" in admin_text,
          str(scan.warnings))

    tajik_text = ocr.summarize_for_admin(scan, "tg")
    check("admin summary can still be rendered in Tajik",
          "худатон санҷед" in tajik_text, tajik_text[-60:])
    english_text = ocr.summarize_for_admin(scan, "en")
    check("admin summary can still be rendered in English",
          "does not confirm payment" in english_text, english_text[:60])

    check("degraded scan reports engine=unavailable when tesseract is absent",
          ocr.scan_image(b"not-an-image").engine in
          ("unavailable", "tesseract-error"),
          ocr.scan_image(b"not-an-image").engine)


def test_pdf_path():
    section("PDF receipt handling")

    not_a_pdf = ocr.scan_pdf(b"%PDF-1.4 truncated garbage")
    check("malformed PDF degrades instead of raising",
          not_a_pdf.engine in ("pdf-error", "pdf-no-text", "unavailable"),
          not_a_pdf.engine)
    check("malformed PDF warns no_text", "no_text" in not_a_pdf.warnings
          or "ocr_unavailable" in not_a_pdf.warnings, str(not_a_pdf.warnings))

    check("scan_receipt dispatches a %PDF- magic header to the PDF reader",
          ocr.scan_receipt(b"%PDF-1.4 x", "image/jpeg").engine.startswith("pdf")
          or ocr.scan_receipt(b"%PDF-1.4 x", "image/jpeg").engine == "unavailable")


# ---------------------------------------------------------------------
# Typed amounts and top-up bounds
# ---------------------------------------------------------------------

def test_decompression_bomb_guard():
    section("Oversized-image (decompression bomb) guard")

    try:
        from PIL import Image
    except Exception:
        check("Pillow available for this check", False, "Pillow missing")
        return

    import io

    check("Pillow is usable independently of pytesseract", ocr._PIL_OK,
          "an earlier version imported both in one try-block, so a box "
          "without pytesseract silently lost Pillow too")

    def png(side_w, side_h):
        img = Image.new("L", (side_w, side_h), 255)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        img.close()
        return buf.getvalue()

    # Sits in the window Pillow only WARNS about (above its 89M warning
    # line, below the 179M error line) and is far under the 8 MB upload
    # cap — so neither of the pre-existing limits stops it.
    bomb = png(12000, 12000)
    check("the bomb is small enough to pass the 8 MB upload cap",
          len(bomb) < 8 * 1024 * 1024, f"{len(bomb)} bytes")
    check("Pillow alone would NOT reject it",
          12000 * 12000 < Image.MAX_IMAGE_PIXELS * 2,
          f"{12000*12000:,} vs {Image.MAX_IMAGE_PIXELS*2:,}")

    scan = ocr.scan_receipt(bomb, "image/png")
    check("but our guard refuses it", scan.engine == "image-too-large",
          scan.engine)
    check("and it is reported as unreadable, not silently accepted",
          "no_text" in scan.warnings, str(scan.warnings))

    # The header is enough to decide, so no bitmap is ever materialised.
    check("the pixel count is read from the header",
          ocr.image_pixel_count(bomb) == 12000 * 12000,
          str(ocr.image_pixel_count(bomb)))

    # A real receipt photo must still go through.
    ordinary = png(1200, 1600)
    ok = ocr.scan_receipt(ordinary, "image/png")
    check("an ordinary receipt photo is not refused",
          ok.engine != "image-too-large", ok.engine)

    # Even a generous phone panorama stays under the limit.
    check("a 24 MP photo is comfortably within the limit",
          6000 * 4000 < ocr.MAX_RECEIPT_PIXELS,
          f"{6000*4000:,} vs {ocr.MAX_RECEIPT_PIXELS:,}")

    check("garbage bytes do not crash the pixel probe",
          ocr.image_pixel_count(b"not an image at all") is None)


def test_typed_amount():
    section("Teacher-typed amount parsing")

    cases = [
        ("25", 2500), ("25.5", 2550), ("25,50", 2550),
        ("1 000", 100000), ("0.5", 50),
        ("", None), ("abc", None), ("-5", None),
        ("25.555", None), ("1e5", None), ("0", None),
    ]
    for raw, expected in cases:
        got = service.parse_amount_to_dirams(raw)
        check(f"parse_amount_to_dirams({raw!r}) == {expected}", got == expected,
              f"got {got}")


def test_topup_bounds():
    section("Top-up bounds and presets")

    s = TelegramSettings(
        TELEGRAM_MIN_TOPUP_DIRAMS=50,
        TELEGRAM_MAX_TOPUP_DIRAMS=500000,
        TELEGRAM_TOPUP_PRESET_GENERATIONS="10,20,50,100",
    )
    presets = s.topup_presets_dirams()
    check("presets derive from the existing generation price, not a new list",
          presets == [500, 1000, 2500, 5000], str(presets))

    check("presets ignore junk entries",
          TelegramSettings(
              TELEGRAM_TOPUP_PRESET_GENERATIONS="10,abc,,0,-3,20"
          ).topup_presets_dirams() == [500, 1000])


def test_admin_authorization():
    section("Administrator authorization")

    s = TelegramSettings(TELEGRAM_ADMIN_IDS="111, 222 ,333")
    check("configured admin ids parsed", s.admin_ids == frozenset({111, 222, 333}),
          str(s.admin_ids))
    check("a configured admin is authorized", s.is_admin(222))
    check("an unknown telegram id is NOT authorized", not s.is_admin(999))
    check("None is NOT authorized", not s.is_admin(None))
    check("a string lookalike is NOT authorized", not s.is_admin("222"))

    empty = TelegramSettings(TELEGRAM_ADMIN_IDS="")
    check("empty config authorizes nobody (fails closed)",
          empty.admin_ids == frozenset() and not empty.is_admin(111))

    junk = TelegramSettings(TELEGRAM_ADMIN_IDS="abc,,12x,  ,444")
    check("unparseable entries are dropped, not guessed",
          junk.admin_ids == frozenset({444}), str(junk.admin_ids))


# ---------------------------------------------------------------------
# Upload validation
# ---------------------------------------------------------------------

def test_receipt_upload_validation():
    section("Receipt upload validation")

    extract = PaymentBot._extract_file

    photo_msg = {"photo": [
        {"file_id": "small", "file_size": 1000},
        {"file_id": "large", "file_size": 9000},
    ]}
    file_id, mime, size = extract(photo_msg)
    check("photo: largest size is chosen for OCR", file_id == "large", str(file_id))
    check("photo: treated as image/jpeg", mime == "image/jpeg", str(mime))
    check("photo: size reported", size == 9000, str(size))

    pdf_msg = {"document": {"file_id": "doc1", "mime_type": "application/PDF",
                            "file_size": 2048}}
    file_id, mime, size = extract(pdf_msg)
    check("document: mime lower-cased", mime == "application/pdf", str(mime))
    check("document: file id taken", file_id == "doc1")

    for unsupported in (
        {"text": "hello"},
        {"voice": {"file_id": "v"}},
        {"video": {"file_id": "vid"}},
        {"sticker": {"file_id": "s"}},
        {},
    ):
        file_id, _, _ = extract(unsupported)
        check(f"non-receipt message rejected: {list(unsupported) or ['empty']}",
              file_id is None, str(file_id))

    s = TelegramSettings()
    allowed = s.allowed_receipt_mimes
    check("jpeg allowed", "image/jpeg" in allowed)
    check("png allowed", "image/png" in allowed)
    check("pdf allowed", "application/pdf" in allowed)
    check("executables not allowed",
          "application/x-msdownload" not in allowed and
          "application/zip" not in allowed)
    check("default size ceiling is 8 MB", s.TELEGRAM_MAX_RECEIPT_BYTES == 8388608,
          str(s.TELEGRAM_MAX_RECEIPT_BYTES))


# ---------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------

def test_token_hygiene():
    section("Token hygiene")

    raw_a = service.generate_link_token()
    raw_b = service.generate_link_token()
    check("link tokens are long", len(raw_a) >= 40, str(len(raw_a)))
    check("link tokens are unique across calls", raw_a != raw_b)
    check("hash is sha256 hex", len(service.hash_link_token(raw_a)) == 64)
    check("hash is deterministic",
          service.hash_link_token(raw_a) == service.hash_link_token(raw_a))
    check("different tokens hash differently",
          service.hash_link_token(raw_a) != service.hash_link_token(raw_b))
    check("the raw token is not recoverable from its hash",
          raw_a not in service.hash_link_token(raw_a))

    # A token-shaped string must never survive into a log line, whether
    # or not it is the token this process is configured with.
    fake = "1234567890:AAbbCCddEEffGGhhIIjjKKllMMnnOOppQQr"
    scrubbed = scrub(f"POST https://api.telegram.org/bot{fake}/sendMessage failed")
    check("a bot-token-shaped string is scrubbed from log text",
          fake not in scrubbed, scrubbed)
    check("scrubbing leaves a visible placeholder", "<BOT_TOKEN>" in scrubbed, scrubbed)

    s = TelegramSettings(TELEGRAM_BOT_TOKEN=fake, TELEGRAM_BOT_USERNAME="bot")
    summary = s.redacted()
    check("redacted() never contains the secret half of the token",
          "AAbbCC" not in summary and fake not in summary, summary)
    check("redacted() still reports that a token is set", "set" in summary, summary)

    check("deep link carries only the opaque token",
          s.deep_link("TOKENVALUE") == "https://t.me/bot?start=TOKENVALUE",
          s.deep_link("TOKENVALUE"))

    # The account-linking brief asks for a 5-minute window specifically,
    # not "expiry works eventually" — this process sets no override, so
    # it is the real default a fresh deployment gets.
    ttl = get_telegram_settings().TELEGRAM_LINK_TOKEN_TTL_SECONDS
    check("the linking token's default lifetime is 5 minutes",
          ttl == 300, str(ttl))


def test_deep_link_leaks_nothing():
    section("Deep link carries no personal data")

    s = TelegramSettings(TELEGRAM_BOT_USERNAME="dastyor_pay_bot")
    token = service.generate_link_token()
    link = s.deep_link(token)
    for secret in ("@", "email", "992", "password", "Bearer", "eyJ"):
        check(f"deep link contains no {secret!r}", secret not in link, link)
    check("deep link is exactly the bot URL plus the token",
          link == f"https://t.me/dastyor_pay_bot?start={token}")


# ---------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------

def test_messages():
    section("Message catalogue")

    check("unknown language falls back to Tajik", normalize_lang("klingon") == "tg")
    check("'Тоҷикӣ' maps to tg", normalize_lang("Тоҷикӣ") == "tg")
    check("'Русский' maps to ru", normalize_lang("Русский") == "ru")
    check("'English' maps to en", normalize_lang("English") == "en")
    check("None falls back to Tajik", normalize_lang(None) == "tg")

    for lang in ("tg", "ru", "en"):
        for key in ("start_unlinked", "link_token_expired", "link_token_used",
                    "receipt_received", "approved_user", "rejected_user",
                    "needs_info_user", "temp_error", "help",
                    "receipt_unsupported", "receipt_too_large",
                    "link_token_invalid", "pay_not_configured"):
            value = t(key, lang)
            check(f"{lang}/{key} is translated", value != key and len(value) > 10,
                  value[:40])

    check("a missing key degrades to the key, not an exception",
          t("no_such_key_at_all", "tg") == "no_such_key_at_all")
    check("a template missing a placeholder does not raise",
          isinstance(t("approved_user", "tg"), str))

    check("somoni formatting uses a comma for tg", fmt_somoni(12345, "tg") == "123,45",
          fmt_somoni(12345, "tg"))
    check("somoni formatting uses a dot for en", fmt_somoni(12345, "en") == "123.45",
          fmt_somoni(12345, "en"))
    check("zero balance formats cleanly", fmt_somoni(0, "tg") == "0,00")

    # The user-facing text must not promise that a receipt alone pays.
    help_tg = t("help", "tg")
    # The wording was simplified for teachers, but the claim it makes
    # must not soften: a photo alone never credits anyone.
    check("Tajik help still says an admin must see the money arrive",
          "расидани пулро бо чашми худ бинад" in help_tg,
          help_tg[-200:])
    check("and that only then is the balance credited",
          "Тавозун танҳо баъд аз он пур мешавад" in help_tg, help_tg[-200:])
    # The receipt is now optional, and the help has to say so —
    # otherwise a teacher with no screenshot concludes they cannot
    # pay at all, which is the opposite of the intent.
    check("and that the receipt itself is optional",
          "ҳатмӣ нест" in help_tg,
          help_tg[-200:])
    receipt_tg = t("receipt_received", "tg", code="DP-X", amount="5,00",
                   currency="сомонӣ", ocr_summary="")
    check("receipt confirmation says the balance has NOT changed yet",
          "Тавозун ҳоло тағйир наёфт" in receipt_tg, receipt_tg[-80:])


def test_callback_data_shape():
    section("Callback data round-trip")

    import uuid as _uuid
    request_id = str(_uuid.uuid4())
    for prefix in ("pay:ok", "pay:no", "pay:more"):
        data = f"{prefix}:{request_id}"
        parsed_prefix, _, parsed_id = data.rpartition(":")
        check(f"{prefix} round-trips its request id",
              parsed_prefix == prefix and parsed_id == request_id,
              f"{parsed_prefix} / {parsed_id}")
        check(f"{prefix} fits Telegram's 64-byte callback_data limit",
              len(data.encode()) <= 64, str(len(data.encode())))


def main():
    print("Telegram payment bot - unit tests (no database, no network)")
    test_extraction()
    test_amount_shapes()
    test_reference_normalisation()
    test_cross_check_warnings()
    test_ocr_never_confirms()
    test_pdf_path()
    test_decompression_bomb_guard()
    test_typed_amount()
    test_topup_bounds()
    test_admin_authorization()
    test_receipt_upload_validation()
    test_token_hygiene()
    test_deep_link_leaks_nothing()
    test_messages()
    test_callback_data_shape()

    print()
    if FAIL:
        print(f"{len(FAIL)} FAILED:")
        for name in FAIL:
            print(f"  - {name}")
        return 1
    print("all unit checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
