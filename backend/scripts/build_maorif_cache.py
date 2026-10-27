import json
import os
import re
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND_DIR)
from app.document_extract import extract_text_from_pdf

CACHE_DIR = os.path.join(_BACKEND_DIR, "app", "textbooks_cache")
BOOKS_JSON = os.path.join(os.path.dirname(__file__), "_maorif_books.json")


def maorif_pdf_url(path: str) -> str | None:
    m = re.search(r"url=(https://maorif\.tj/storage/libraries/[^&]+\.pdf)", path or "")
    return m.group(1) if m else None


def fetch_book_listing() -> dict:
    by_grade: dict[str, list] = {}
    for grade, category in enumerate(range(23, 34), start=1):
        url = f"https://www.maorif.tj/libraries?category={category}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        m = re.search(r"libraries:\s*JSON\.parse\('(.*?)'\)", html)
        if not m:
            print(f"grade {grade} (category {category}): no book listing found on the page")
            continue
        unescaped = json.loads('"' + m.group(1).replace('"', '\\"') + '"')
        books = json.loads(unescaped)
        by_grade[str(grade)] = [
            (b.get("id"), (b.get("name") or "").strip(), maorif_pdf_url(b.get("path") or ""))
            for b in books
        ]
    return by_grade


SUBJECT_MAP = {
    "Математика": "Математика",
    "Алгебра": "Алгебра",
    "Алгебра 2025": "Алгебра",
    "Геометрия": "Геометрия",
    "Гометрия 2025": "Геометрия",
    "Химия": "Химия",
    "Химияи органикӣ": "Химия",
    "Ботаника": "Биология",
    "Зоология": "Биология",
    "Биология": "Биология",
    "Экология": "Биология",
    "География": "География",
    "Географияи Тоҷикистон": "География",
    "Русский язык": "Русский язык",
    "Русскый язык": "Русский язык",
    "Русская речь": "Русский язык",
    "Забони англисӣ": "Английский язык",
    "Забони тоҷикӣ": "Таджикский язык",
    "Забони модарӣ": "Таджикский язык",
    "Адабиёти тоҷик": "Таджикская литература",
    "Адабиет 2025": "Таджикская литература",
    "Таърихи умумӣ": "Всемирная история",
    "Таърихи халқи тоҷик": "История Таджикистана",
    "Технологияи иттилоотӣ": "Информатика",
    "Технологияи иттилотӣ": "Информатика",
}


if os.path.exists(BOOKS_JSON):
    with open(BOOKS_JSON, encoding="utf-8") as f:
        by_grade = json.load(f)
else:
    by_grade = fetch_book_listing()
    with open(BOOKS_JSON, "w", encoding="utf-8") as f:
        json.dump(by_grade, f, ensure_ascii=False, indent=2)

with open(os.path.join(CACHE_DIR, "_manifest.json"), encoding="utf-8") as f:
    manifest = json.load(f)

headers = {"User-Agent": "Mozilla/5.0"}
for grade_str, books in by_grade.items():
    grade = int(grade_str)
    for book_id, name, pdf_url in books:
        subject = SUBJECT_MAP.get(name.strip())
        if not subject or not pdf_url:
            continue
        existing = manifest.get(subject, {}).get(str(grade))
        if existing and existing.get("name", "").startswith("local_"):
            print(f"skip {subject} g{grade}: already have a local konspekt")
            continue
        name_stem = f"maorif_{subject.lower().replace(' ', '_')}_{grade}"
        cache_path = os.path.join(CACHE_DIR, f"{name_stem}.txt")
        if os.path.exists(cache_path) and os.path.getsize(cache_path) > 3000:
            print(f"skip (cached): {subject} g{grade}")
        else:
            print(f"downloading {subject} g{grade} ({name}): {pdf_url}")
            try:
                req = urllib.request.Request(pdf_url, headers=headers)
                with urllib.request.urlopen(req, timeout=90) as resp:
                    raw = resp.read()
                text = extract_text_from_pdf(raw)
                print(f"  {len(raw)} bytes -> {len(text)} chars")
                if len(text) < 3000:
                    print(f"  WARNING: too short (likely scanned), skipping {subject} g{grade}")
                    continue
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(text)
            except Exception as e:
                print(f"  FAILED: {e}")
                continue
        manifest.setdefault(subject, {})[str(grade)] = {"name": name_stem, "images_ok": False}

with open(os.path.join(CACHE_DIR, "_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
print("done")
