import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND_DIR)
from app.document_extract import extract_text_from_pdf, extract_text_from_docx

CACHE_DIR = os.path.join(_BACKEND_DIR, "app", "textbooks_cache")
SOURCE_ROOT = r"C:\Users\user\Desktop\Канспект"

MANIFEST = [
    ("Математика", 5, r"Математика\Конспекти_Математика_Синфи_5пурра_Riyoziyot_TJ_.pdf", "local_matematika_5"),
    ("Алгебра", 7, r"Алгебра\КОНСПЕКТ_АЛГЕБРА_СИНФИ_7.pdf", "local_algebra_7"),
    ("Алгебра", 8, r"Алгебра\КОНСПЕКТ_АЛГЕБРА_СИНФИ_8_ (1).pdf", "local_algebra_8"),
    ("Алгебра", 9, r"Алгебра\Нақша_конспект_дарс_Алгебра,_синфи_9.pdf", "local_algebra_9"),
    ("Алгебра", 10, r"Алгебра\КОНСПЕКТ АЛГЕБРА С 10. (1).docx", "local_algebra_10"),
    ("Алгебра", 11, r"Алгебра\КОНСПЕКТ АЛГЕБРА С 11 (1).docx", "local_algebra_11"),
    ("Физика", 8, r"Физика\8Нақшаҳои_яксоата_физика_синфи8_2026_2027_2 (1).docx", "local_fizika_8"),
    ("Физика", 10, r"Физика\10Нақшаҳои_яксоата_физика_синфи10_2026_2027 (1).docx", "local_fizika_10"),
    ("Физика", 11, r"Физика\11Нақшаҳои_яксоата_физика_синфи11_2026_2027_1 (1).docx", "local_fizika_11"),
    ("Химия", 8, r"Химия\Конспекти химия-8.9 (2).docx", "local_khimiya_89"),
    ("Химия", 9, r"Химия\Конспекти химия-8.9 (2).docx", "local_khimiya_89"),
    ("Английский язык", 3, r"Забони англисӣ\конспекти синфи 3 англисӣ Учител.pdf", "local_english_3"),
    ("Английский язык", 7, r"Забони англисӣ\конспект англиси с 7 Учител пдф (1).pdf", "local_english_7"),
    ("Английский язык", 8, r"Забони англисӣ\Конспект англиси с 8 Учител пдф (1).pdf", "local_english_8"),
    ("Английский язык", 11, r"Забони англисӣ\Конспекти_забони_англиси_с_11_Учител_пдф.pdf", "local_english_11"),
    ("Английский язык", 10, r"Забони англисӣ\КОНСПЕКТИ_ЗАБОНИ_АНГЛИСИ_С_10_УЧИТЕЛ_пдф (1).pdf", "local_english_10"),
    ("Таджикский язык", 6, r"Забони тоҷикӣ\РОҲНАМОИ_ФАННИ_ЗАБОНИ_ТОҶИКӢ_БАРОИ_СИНФИ_6_УМ.pdf", "local_tajik_6"),
    ("Таджикский язык", 7, r"Забони тоҷикӣ\РОҲНАМОИ_ФАННИ_ЗАБОНИ_ТОҶИКӢ_БАРОИ_СИНФИ_7_УМ.pdf", "local_tajik_7"),
    ("Таджикский язык", 11, r"Забони тоҷикӣ\РОҲНАМОИ_ФАННИ_ЗАБОНИ_ТОҶИКӢ_БАРОИ_СИНФИ_11_УМ.pdf", "local_tajik_11"),
]

with open(os.path.join(CACHE_DIR, "_manifest.json"), encoding="utf-8") as f:
    manifest = json.load(f)

seen_names = set()
for subject, grade, rel_path, name in MANIFEST:
    cache_path = os.path.join(CACHE_DIR, f"{name}.txt")
    if name not in seen_names:
        seen_names.add(name)
        src_path = os.path.join(SOURCE_ROOT, rel_path)
        ext = os.path.splitext(src_path)[1].lower()
        print(f"extracting {subject} grade {grade}: {rel_path}")
        try:
            with open(src_path, "rb") as f:
                raw = f.read()
            text = extract_text_from_pdf(raw) if ext == ".pdf" else extract_text_from_docx(raw)
            print(f"  {len(text)} chars")
            if len(text) < 3000:
                print(f"  WARNING: too short, skipping cache write for {name}")
                continue
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            print(f"  FAILED: {e}")
            continue
    if not os.path.exists(cache_path):
        continue
    manifest.setdefault(subject, {})[str(grade)] = {"name": name, "images_ok": False}

with open(os.path.join(CACHE_DIR, "_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print("done")
