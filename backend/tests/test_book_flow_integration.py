"""ASGI + isolated PostgreSQL book flow; AI and payments never leave the test."""

import io
import json
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import select, text

from conftest import async_test
from app import book_sources, limits
from app.auth import create_access_token
from app.database import async_session
from app.main import app
from app.models import Konspekt, User


def pdf(*pages: str) -> bytes:
    buffer = io.BytesIO()
    writer = canvas.Canvas(buffer)
    for page in pages:
        if page:
            writer.drawString(40, 750, page)
        writer.showPage()
    writer.save()
    return buffer.getvalue()


def payload(source_id: str, types: list[str], scope: str = "all", **selection) -> dict:
    return {"source_id": source_id, "scope": scope, "topic": "", "subject": "Biology",
            "grade": "7", "language": "English", "level": "Medium",
            "types": types, **selection}


async def ai_from_selected_pages(**kwargs):
    source = kwargs["source_text"]
    assert "[Page " in source and "cells" in source.lower()
    assert kwargs["strict_source"] is True
    return {**{kind: ({"questions": [{"question": "What is a cell?"}]}
                      if kind == "test" else {"main_content": "Cells have membranes"})
               for kind in kwargs["types"]}, "errors": {}}


@async_test
async def test_book_upload_quote_generate_save_refund_and_owner():
    marker = uuid.uuid4().hex[:10]
    async with async_session() as db:
        first = User(full_name="Book test teacher", email=f"book-{marker}@example.test",
                     hashed_password="unused", language="English", balance_dirams=0)
        second = User(full_name="Other test teacher", email=f"other-{marker}@example.test",
                      hashed_password="unused", language="English", balance_dirams=0)
        db.add_all([first, second])
        await db.commit()
        owner_id, other_id = first.id, second.id

    owner = {"Authorization": f"Bearer {create_access_token(owner_id)}"}
    other = {"Authorization": f"Bearer {create_access_token(other_id)}"}
    raw = pdf("Chapter 1 Biology cells and tissues", "Cells have membranes and cytoplasm",
              "Chapter 2 Photosynthesis cells", "Green cells use sunlight in photosynthesis")

    with tempfile.TemporaryDirectory() as directory, \
         patch.object(book_sources, "STORE_DIR", Path(directory)), \
         patch("app.routers.materials._guard_topic"), \
         patch("app.routers.materials.enforce_generation_quota"), \
         patch("app.routers.materials.generate_all_materials", side_effect=ai_from_selected_pages), \
         patch.object(limits, "PILOT_FREE_FOR_ALL", False):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            upload_url = "/api/materials/book-sources"
            assert (await client.post(upload_url, files={"file": ("book.pdf", raw, "application/pdf")})).status_code == 401
            for contents, name, mime, status in (
                (b"", "empty.pdf", "application/pdf", 422),
                (b"broken", "broken.pdf", "application/pdf", 422),
                (raw, "book.txt", "text/plain", 422),
                (b"%PDF-" + b"x" * (book_sources.MAX_BYTES + 1), "huge.pdf", "application/pdf", 413),
            ):
                bad = await client.post(upload_url, headers=owner,
                                        files={"file": (name, contents, mime)})
                assert bad.status_code == status, (name, bad.status_code)
            upload = await client.post(upload_url, headers=owner,
                                       files={"file": ("book.pdf", raw, "application/pdf")})
            assert upload.status_code == 200, upload.text
            metadata = upload.json()
            assert metadata["page_count"] == 4 and len(metadata["chapters"]) == 2
            source_id = metadata["id"]
            assert "pages" not in metadata
            assert (await client.get(f"{upload_url}/{source_id}", headers=owner)).status_code == 200
            assert (await client.get(f"{upload_url}/{source_id}", headers=other)).status_code == 404

            quote = await client.post("/api/materials/quote", headers=owner,
                                      json={"types": ["konspekt"]})
            assert quote.status_code == 200 and quote.json()["free_count"] == 1
            assert quote.json()["balance_dirams"] == 0
            async with async_session() as db:
                user = (await db.execute(select(User).where(User.id == owner_id))).scalar_one()
                assert user.free_konspekt_used == 0
                assert (await db.execute(text(
                    "SELECT count(*) FROM balance_transactions WHERE user_id = :uid"
                ), {"uid": owner_id})).scalar_one() == 0

            generation = await client.post("/api/materials/generate-from-book", headers=owner,
                                           json=payload(source_id, ["konspekt"]))
            assert generation.status_code == 200, generation.text
            body = generation.json()
            assert body["source"]["used_pages"] == [1, 2, 3, 4]
            assert body["was_free"]["konspekt"] is True
            async with async_session() as db:
                saved = (await db.execute(select(Konspekt).where(Konspekt.id == body["ids"]["konspekt"]))).scalar_one()
                assert saved.owner_id == owner_id
                assert json.loads(saved.content)["source"]["used_pages"] == [1, 2, 3, 4]

            assert (await client.post("/api/materials/generate-from-book", headers=other,
                                      json=payload(source_id, ["konspekt"]))).status_code == 404
            assert (await client.post("/api/materials/generate-from-book-stream",
                                      json=payload(source_id, ["konspekt"]))).status_code == 401
            assert (await client.post("/api/materials/generate-from-book-stream", headers=other,
                                      json=payload(source_id, ["konspekt"]))).status_code == 404
            assert (await client.post("/api/materials/generate-from-book", headers=owner,
                                      json=payload(source_id, ["konspekt", "konspekt"]))).status_code == 400

            stream = await client.post("/api/materials/generate-from-book-stream", headers=owner,
                                       json=payload(source_id, ["test"], "chapter", chapter_index=1))
            assert stream.status_code == 200
            events = [json.loads(line[6:]) for line in stream.text.splitlines() if line.startswith("data: ")]
            assert events[-1]["type"] == "complete", events[-1]
            assert events[-1]["source"]["used_pages"] == [3, 4]
            assert events[-1]["source"]["chapter"].startswith("Chapter 2")

            async with async_session() as db:
                user = (await db.execute(select(User).where(User.id == owner_id))).scalar_one()
                user.balance_dirams = limits.GENERATION_PRICE_DIRAMS
                await db.commit()
            paid_quote = await client.post("/api/materials/quote", headers=owner,
                                           json={"types": ["konspekt"]})
            assert paid_quote.json()["required_dirams"] == limits.GENERATION_PRICE_DIRAMS
            paid = await client.post("/api/materials/generate-from-book", headers=owner,
                                     json=payload(source_id, ["konspekt"], "pages", page_start=2, page_end=2))
            assert paid.status_code == 200, paid.text
            assert paid.json()["source"]["used_pages"] == [2]
            assert paid.json()["was_free"]["konspekt"] is False
            assert (await limits.current_balance(owner_id)) == 0

            insufficient = await client.post("/api/materials/generate-from-book", headers=owner,
                                              json=payload(source_id, ["konspekt"]))
            assert insufficient.status_code == 402
            stream_insufficient = await client.post("/api/materials/generate-from-book-stream",
                                                    headers=owner, json=payload(source_id, ["konspekt"]))
            stream_errors = [json.loads(line[6:]) for line in stream_insufficient.text.splitlines()
                             if line.startswith("data: ")]
            assert stream_errors[-1]["type"] == "error" and stream_errors[-1]["status"] == 402
            async with async_session() as db:
                user = (await db.execute(select(User).where(User.id == owner_id))).scalar_one()
                user.balance_dirams = limits.GENERATION_PRICE_DIRAMS
                await db.commit()
            with patch("app.routers.materials.generate_all_materials", side_effect=RuntimeError("test AI failure")):
                failed = await client.post("/api/materials/generate-from-book", headers=owner,
                                           json=payload(source_id, ["konspekt"]))
            assert failed.status_code == 500
            assert (await limits.current_balance(owner_id)) == limits.GENERATION_PRICE_DIRAMS
            with patch("app.routers.materials.generate_all_materials", side_effect=RuntimeError("test AI failure")):
                stream_failed = await client.post("/api/materials/generate-from-book-stream", headers=owner,
                                                  json=payload(source_id, ["konspekt"]))
            stream_failure_events = [json.loads(line[6:]) for line in stream_failed.text.splitlines()
                                     if line.startswith("data: ")]
            assert stream_failure_events[-1]["type"] == "error"
            assert (await limits.current_balance(owner_id)) == limits.GENERATION_PRICE_DIRAMS
            async with async_session() as db:
                kinds = (await db.execute(text(
                    "SELECT kind FROM balance_transactions WHERE user_id = :uid ORDER BY created_at"
                ), {"uid": owner_id})).scalars().all()
                assert "free" in kinds and "charge" in kinds and "refund" in kinds


@async_test
async def test_real_pdf_rendering_without_local_ocr_binary_reports_error():
    # PDFium is real here. This test does not pretend Tesseract is installed.
    import importlib.util
    from app.telegram.ocr import tesseract_available

    assert importlib.util.find_spec("pypdfium2") is not None
    if tesseract_available():
        pytest.skip("Tesseract is already available in this environment")
    try:
        book_sources.extract_pdf(pdf(""), "scan.pdf", "application/pdf")
    except book_sources.BookError as exc:
        assert str(exc) == "ocr_unavailable"
    else:
        raise AssertionError("blank scanned PDF was accepted without OCR")


def test_real_scanned_pdf_ocr_with_installed_english_data():
    executable = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    font_path = Path(r"C:\Windows\Fonts\arial.ttf")
    if not executable.exists() or not font_path.exists():
        pytest.skip("Local Tesseract or readable font is unavailable")
    image = Image.new("RGB", (1200, 220), "white")
    draw = ImageDraw.Draw(image)
    draw.text((35, 65), "Cells have membranes and cytoplasm",
              fill="black", font=ImageFont.truetype(str(font_path), 43))
    buffer = io.BytesIO()
    writer = canvas.Canvas(buffer)
    writer.drawImage(ImageReader(image), 25, 620, width=560, height=103)
    writer.showPage()
    writer.save()
    with patch.dict(os.environ, {"PATH": f"{executable.parent};{os.environ.get('PATH', '')}"}):
        extracted = book_sources.extract_pdf(buffer.getvalue(), "scanned.pdf", "application/pdf")
    assert extracted["ocr_pages"] == 1
    assert "cells" in extracted["pages"][0].lower()
    assert "membranes" in extracted["pages"][0].lower()
