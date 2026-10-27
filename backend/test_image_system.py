import asyncio
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from app.ai_service import generate_material

CASES = [
    ("Биология", "Клеточное дыхание", "konspekt"),
    ("Физика", "Закон Ома", "lektsiya"),
    ("Математика", "Теорема Пифагора", "prezentatsiya"),
    ("История Таджикистана", "Государство Саманидов", "test"),
    ("География", "Климат Таджикистана", "konspekt"),
]


def _dump_images(material_type: str, content: dict):
    if material_type in ("konspekt", "lektsiya"):
        imgs = content.get("lesson_images") or []
        for im in imgs:
            print(f"    [{im.get('position_after')}] {im.get('file_title') or im.get('caption')}")
            print(f"      -> {im.get('explanation', '')[:150]}")
    elif material_type == "prezentatsiya":
        for s in content.get("slides") or []:
            if s.get("image"):
                print(f"    [slide: {s.get('title', '')[:40]}] {s['image'].get('caption') or s['image'].get('path')}")
                print(f"      -> {s['image'].get('explanation', '')[:150]}")
    elif material_type == "test":
        for q in content.get("questions") or []:
            if q.get("image"):
                print(f"    [q: {q.get('question', '')[:50]}] {q['image'].get('path')}")


async def main():
    for i, (subject, topic, mtype) in enumerate(CASES):
        if i > 0:
            print("\n  (waiting 60s for token quota...)")
            await asyncio.sleep(60)
        print(f"\n=== {mtype} / {subject}: {topic} ===")
        t0 = time.time()
        try:
            kwargs = dict(material_type=mtype, topic=topic, subject=subject,
                          language="Русский", level="Средний", grade="8")
            if mtype == "prezentatsiya":
                kwargs["slide_count"] = 6
            if mtype == "test":
                kwargs["question_count"] = 8
            content = await generate_material(**kwargs)
        except Exception as e:
            print(f"  FAILED: {e}")
            continue
        print(f"  generated in {time.time() - t0:.1f}s")
        _dump_images(mtype, content)


if __name__ == "__main__":
    asyncio.run(main())
