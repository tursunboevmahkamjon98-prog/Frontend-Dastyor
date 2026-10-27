"""Pure unit tests: no FastAPI lifespan, database, or payment calls."""

import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reportlab.pdfgen import canvas

from app import book_sources


def pdf_with_text(*pages: str) -> bytes:
    stream = io.BytesIO()
    writer = canvas.Canvas(stream)
    for text in pages:
        writer.drawString(50, 750, text)
        writer.showPage()
    writer.save()
    return stream.getvalue()


class BookSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.store_patch = patch.object(book_sources, "STORE_DIR", self.directory)
        self.store_patch.start()

    def tearDown(self):
        self.store_patch.stop()
        self.temp.cleanup()

    def test_valid_pdf_metadata_and_private_owner(self):
        extracted = book_sources.extract_pdf(
            pdf_with_text("Chapter 1 Cells and tissues in biology", "Cells contain a nucleus and membrane"),
            "biology.pdf", "application/pdf",
        )
        self.assertEqual(extracted["page_count"], 2)
        self.assertTrue(extracted["chapters"])
        metadata = book_sources.save("teacher-a", extracted)
        self.assertEqual(metadata["page_count"], 2)
        self.assertNotIn("pages", metadata)
        self.assertEqual(book_sources.load("teacher-a", metadata["id"])["pages"][0], extracted["pages"][0])
        with self.assertRaisesRegex(book_sources.BookError, "not_found"):
            book_sources.load("teacher-b", metadata["id"])
        if os.name != "nt":
            self.assertEqual((self.directory / f"{metadata['id']}.json").stat().st_mode & 0o777, 0o600)

    def test_invalid_uploads(self):
        cases = [
            (b"", "book.pdf", "application/pdf", "empty_file"),
            (b"broken", "book.pdf", "application/pdf", "invalid_pdf"),
            (b"%PDF-123", "book.txt", "text/plain", "unsupported_file"),
            (b"%PDF-" + b"x" * (book_sources.MAX_BYTES + 1), "book.pdf", "application/pdf", "file_too_large"),
        ]
        for raw, name, mime, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(book_sources.BookError, code):
                book_sources.extract_pdf(raw, name, mime)

    def test_scanned_pdf_without_ocr_has_explicit_error(self):
        with patch.object(book_sources, "_ocr_page", side_effect=book_sources.BookError("ocr_unavailable")):
            with self.assertRaisesRegex(book_sources.BookError, "ocr_unavailable"):
                book_sources.extract_pdf(pdf_with_text(""), "scan.pdf", "application/pdf")

    def test_scanned_pdf_uses_ocr_text_when_available(self):
        with patch.object(book_sources, "_ocr_page", return_value="Plants absorb sunlight through their leaves") as ocr:
            extracted = book_sources.extract_pdf(pdf_with_text(""), "scan.pdf", "application/pdf")
        self.assertEqual(extracted["ocr_pages"], 1)
        self.assertIn("sunlight", extracted["pages"][0])
        ocr.assert_called_once()

    def test_whole_book_chapter_and_pages(self):
        extracted = book_sources.extract_pdf(pdf_with_text(
            "Chapter 1 Biology cells and tissues", "Cells have membranes and cytoplasm",
            "Chapter 2 Photosynthesis in green plants", "Plants use sunlight in photosynthesis",
        ), "biology.pdf", "application/pdf")
        all_pages = book_sources.select_context(extracted, "all", None)
        self.assertEqual(all_pages["page_start"], 1)
        self.assertEqual(all_pages["page_end"], 4)
        chapter = book_sources.select_context(extracted, "chapter", None, chapter_index=1)
        self.assertEqual(chapter["page_start"], 3)
        self.assertEqual(chapter["page_end"], 4)
        pages = book_sources.select_context(extracted, "pages", "photosynthesis", page_start=3, page_end=4)
        self.assertIn(3, pages["used_pages"])
        self.assertIn("Photosynthesis", pages["text"])
        with self.assertRaisesRegex(book_sources.BookError, "invalid_pages"):
            book_sources.select_context(extracted, "pages", None, page_start=4, page_end=2)
        with self.assertRaisesRegex(book_sources.BookError, "topic_not_found"):
            book_sources.select_context(extracted, "all", "quantum cosmology")

    def test_expiry_cleanup(self):
        extracted = book_sources.extract_pdf(pdf_with_text("A biology textbook about living cells"), "book.pdf", "application/pdf")
        metadata = book_sources.save("teacher-a", extracted)
        book_sources.cleanup(now=metadata["expires_at"] + 1)
        with self.assertRaisesRegex(book_sources.BookError, "not_found"):
            book_sources.load("teacher-a", metadata["id"])


if __name__ == "__main__":
    unittest.main()
