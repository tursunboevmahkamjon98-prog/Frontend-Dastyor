import json
import os
import sys
import tempfile
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BACKEND_DIR)
from app.ai_service import fix_legacy_tajik_glyphs

BASE = "http://kitobkhona.tj/downloads/darsi/"
CACHE_DIR = os.path.join(_BACKEND_DIR, "app", "textbooks_cache")
PDF_DIR = os.path.join(tempfile.gettempdir(), "dastyor_textbook_pdfs")

MIN_IMAGE_DIMENSION = 150

MANIFEST = [
    ("Математика", 1, "s1/matematika.pdf", "matematika_1"),
    ("Математика", 2, "s2/matematika2.pdf", "matematika_2"),
    ("Математика", 5, "s5/Математика 5.pdf", "matematika_5"),
    ("Математика", 6, "s6/matematika.pdf", "matematika_6"),
    ("Алгебра", 7, "s7/alg.pdf", "algebra_7"),
    ("Геометрия", 7, "s7/geometry.pdf", "geometriya_7"),
    ("Алгебра", 8, "s8/algebra.pdf", "algebra_8"),
    ("Алгебра", 9, "s9/alg.pdf", "algebra_9"),
    ("Геометрия", 9, "s9/geomet.pdf", "geometriya_9"),
    ("Алгебра", 10, "s10/alg2.pdf", "algebra_10"),
    ("Геометрия", 10, "s10/geometry.pdf", "geometriya_10"),
    ("Алгебра", 11, "s11/algebra.pdf", "algebra_11"),
    ("Геометрия", 11, "s11/geometry.pdf", "geometriya_11"),
]

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)


def extract_with_pages(raw: bytes):
    from pypdf import PdfReader

    reader = PdfReader(__import__("io").BytesIO(raw))
    parts = []
    breakpoints = []
    pos = 0
    for page_num, page in enumerate(reader.pages):
        try:
            text = (page.extract_text() or "").strip()
        except Exception:
            text = ""
        breakpoints.append((pos, page_num))
        if text:
            parts.append(text)
            pos += len(text) + 2
    full_text = fix_legacy_tajik_glyphs("\n\n".join(parts))
    return full_text, breakpoints, reader


def extract_images(reader, out_dir: str) -> list[dict]:
    os.makedirs(out_dir, exist_ok=True)
    found = []
    for page_num, page in enumerate(reader.pages):
        for i, img in enumerate(page.images):
            try:
                from PIL import Image
                import io as _io
                with Image.open(_io.BytesIO(img.data)) as im:
                    w, h = im.size
            except Exception:
                continue
            if min(w, h) < MIN_IMAGE_DIMENSION:
                continue
            filename = f"p{page_num}_{i}.png"
            path = os.path.join(out_dir, filename)
            with Image.open(_io.BytesIO(img.data)) as im:
                im.convert("RGB").save(path, "PNG")
            found.append({"page": page_num, "path": filename, "w": w, "h": h})
    return found


_existing_manifest_path = os.path.join(CACHE_DIR, "_manifest.json")
try:
    with open(_existing_manifest_path, encoding="utf-8") as f:
        _existing_manifest = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    _existing_manifest = {}

manifest_out = {}
for subject, grade, rel_path, name in MANIFEST:
    cache_path = os.path.join(CACHE_DIR, f"{name}.txt")
    pages_path = os.path.join(CACHE_DIR, f"{name}.pages.json")
    images_dir = os.path.join(CACHE_DIR, f"{name}_images")
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 500:
        print(f"skip (cached): {name}")
    else:
        url = BASE + urllib.request.quote(rel_path)
        pdf_path = os.path.join(PDF_DIR, f"{name}.pdf")
        print(f"downloading {subject} grade {grade}: {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
            print(f"  {len(raw)} bytes")
            with open(pdf_path, "wb") as f:
                f.write(raw)
            text, breakpoints, reader = extract_with_pages(raw)
            print(f"  extracted {len(text)} chars, {len(breakpoints)} pages")
            if len(text) < 5000:
                print(f"  WARNING: no real text layer for {name} (likely a scanned PDF) — skipping cache write")
                continue
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(text)
            with open(pages_path, "w", encoding="utf-8") as f:
                json.dump(breakpoints, f)
            images = extract_images(reader, images_dir)
            def _bucket(im, step=40):
                return (round(im["w"] / step), round(im["h"] / step))
            import collections
            size_counts = collections.Counter(_bucket(im) for im in images)
            images = [im for im in images if size_counts[_bucket(im)] <= 8]
            for im in list(images):
                if not os.path.exists(os.path.join(images_dir, im["path"])):
                    images.remove(im)
            print(f"  {len(images)} real images kept (>= {MIN_IMAGE_DIMENSION}px, not a repeated page template)")
            if images:
                with open(os.path.join(images_dir, "images.json"), "w", encoding="utf-8") as f:
                    json.dump(images, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  FAILED: {e}")
            continue
    prior = _existing_manifest.get(subject, {}).get(str(grade))
    prior_images_ok = prior.get("images_ok", False) if isinstance(prior, dict) else False
    manifest_out.setdefault(subject, {})[str(grade)] = {"name": name, "images_ok": prior_images_ok}

with open(os.path.join(CACHE_DIR, "_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest_out, f, ensure_ascii=False, indent=2)
print("done, manifest:", manifest_out)
