"""Regression tests for focused konspekt generation and the teacher review pass."""
import unittest
from unittest.mock import AsyncMock, patch

from app import ai_service


class KonspektPromptQualityTests(unittest.TestCase):
    def test_math_examples_and_visuals_are_topic_sized_not_forced(self):
        prompt = ai_service._konspekt_prompt(
            "Quadratic equations", next(iter(ai_service._WORKED_EXAMPLE_SUBJECTS)), "???????", "8", "English"
        )
        self.assertIn("3-6 fully worked examples", prompt)
        self.assertIn("visual_blocks\": include 0-3", prompt)
        self.assertNotIn("EXACTLY 5 entries", prompt)
        self.assertNotIn("16-20 of them", prompt)
        self.assertIn("Do not pad the lesson", prompt)
        self.assertIn('"lesson_images": 0-2 entries', prompt)
        self.assertIn("JSON arrays below show the expected shape, not a required item count", prompt)
        self.assertNotIn("3-5 items per list", prompt)

    def test_exercise_subjects_get_compact_examples_and_practice(self):
        prompt = ai_service._konspekt_prompt(
            "Parts of speech", next(iter(ai_service._EXERCISE_SUBJECTS)), "???????", "6", "English"
        )
        self.assertIn("3-6 concrete, fully worked exercises", prompt)
        self.assertIn("3-6 distinct unsolved tasks", prompt)
        self.assertIn("Never repeat tasks just to reach a count", prompt)


class KonspektReviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_review_receives_pedagogical_and_strict_source_context(self):
        source = "[Page 4] A square has four equal sides."
        mocked_ai = AsyncMock(return_value={"fixes": []})
        content = {"title": "Squares", "main_content": "A square has four equal sides."}
        with patch.object(ai_service, "_call_ai", mocked_ai):
            result = await ai_service._verify_and_fix(
                "konspekt", content, "English", "Squares", "Mathematics", "5", source, True
            )
        self.assertIs(result, content)
        prompt = mocked_ai.await_args.args[1]
        self.assertIn("lesson sequence", prompt)
        self.assertIn("Objectives, examples, activities", prompt)
        self.assertIn("sole authority", prompt)
        self.assertIn(source, prompt)
        self.assertIn("grade=5", prompt)


if __name__ == "__main__":
    unittest.main()
