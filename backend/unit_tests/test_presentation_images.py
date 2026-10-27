"""Mocked tests for slide image coverage and duplicate-source filtering."""
import unittest
from unittest.mock import AsyncMock, patch

from app import ai_service, image_builder


class PresentationImageTests(unittest.IsolatedAsyncioTestCase):
    def test_prompt_requires_slide_specific_images_and_varied_slide_kinds(self):
        from app.subject_templates import BIOLOGY

        prompt = ai_service._presentation_prompt(
            "Cell division", BIOLOGY.label_ru, "Intermediate", "7", "English", 5
        )
        self.assertIn('"image_query": REQUIRED on EVERY slide', prompt)
        self.assertIn("specific to this exact slide", prompt)
        self.assertIn("Every slide should read differently", prompt)

    def _deck(self):
        return {
            "title": "Water cycle",
            "subject": "Biology",
            "grade": "7",
            "language": "English",
            "slides": [
                {"title": f"Water cycle stage {i}", "body": f"Stage {i} description",
                 "image_query": f"water cycle stage {i} diagram"}
                for i in range(1, 4)
            ],
        }

    async def test_searches_every_content_slide_and_keeps_distinct_images(self):
        deck = self._deck()
        candidates = [
            {"path": f"/uploads/images/{i}.jpg", "file_title": f"Stage {i} diagram.jpg",
             "source": f"https://commons.test/{i}", "description": "Stage diagram"}
            for i in range(1, 4)
        ]
        with patch.object(image_builder, "fetch_lesson_images", new_callable=AsyncMock) as fetch, \
             patch.object(ai_service, "_caption_and_verify_images", new_callable=AsyncMock,
                          side_effect=lambda _content, _topic, images, context_of=None: images):
            fetch.side_effect = [[image] for image in candidates]
            await ai_service._render_slide_images(deck, "Water cycle")

        self.assertEqual(fetch.await_count, 3)
        self.assertTrue(all(slide.get("image") for slide in deck["slides"]))

    async def test_duplicate_commons_file_is_not_reused_for_another_slide(self):
        deck = self._deck()
        candidates = [
            {"path": f"/uploads/images/random-{i}.jpg", "file_title": "Same diagram.jpg",
             "source": "https://commons.test/same", "description": "Stage diagram"}
            for i in range(1, 4)
        ]
        with patch.object(image_builder, "fetch_lesson_images", new_callable=AsyncMock) as fetch, \
             patch.object(ai_service, "_caption_and_verify_images", new_callable=AsyncMock,
                          side_effect=lambda _content, _topic, images, context_of=None: images):
            fetch.side_effect = [[image] for image in candidates]
            await ai_service._render_slide_images(deck, "Water cycle")

        self.assertEqual(deck["slides"][0]["image"]["path"], "/uploads/images/random-1.jpg")
        self.assertNotIn("image", deck["slides"][1])
        self.assertNotIn("image", deck["slides"][2])


if __name__ == "__main__":
    unittest.main()

