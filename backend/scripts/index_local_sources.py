"""Build a local textbook index for the Dastyor material generator.

The source folder contains a mixture of textbooks, curricula and teacher
lesson plans. We extract readable PDF/DOCX files once, keep a compact manifest,
and let the generator retrieve only the best subject/grade sources.
Legacy .DOC files are reported as skipped because the runtime has no safe
cross-platform .DOC extractor installed.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from docx import Document
import pypdfium2 as pdfium


SUBJECTS = {
    "Адабиёт": "Таджикская литература",
    "Алгебра": "Алгебра",
    "Биология": "Биология",
    "География": "География",
    "Геометрия": "Геометрия",
    "Забони англисӣ": "Английский язык",
    "Забони арабӣ": "Арабский язык",
    "Забони русӣ": "Русский язык",
    "Забони тоҷикӣ": "Таджикский язык",
    "Информатика": "Информатика",
    "Математика": "Математика",
    "Таърих": "История Таджикистана",
    "Технология": "Технология",
    "Физика": "Физика",
    "Химия": "Химия",
    "Ҷомеашиносӣ": "Обществознание",
    "Табиатшиносӣ": "Естествознание",
    "Санъат": "Искусство",
    "Тарбияи ҷисмонӣ": "Физическая культура",
}


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\x00", "").replace("\u00ad", "").replace("\ufffe", "")
    lines = []
    previous = ""
    for raw in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw).strip()
        if line:
            # PDF table extraction often repeats the same cell several times.
            if line == previous and len(line) > 1:
                continue
            lines.append(line)
            previous = line
    # Normalize the legacy Tajik glyphs found in older school books.
    return "\n".join(lines).translate(str.maketrans({"њ": "ҳ", "Њ": "Ҳ", "ќ": "қ", "Ќ": "Қ", "ѓ": "ғ", "Ѓ": "Ғ", "љ": "ҷ", "Љ": "Ҷ", "ї": "ӣ", "Ї": "Ӣ"}))


def extract_pdf(path: Path) -> str:
    # Pdfium is dramatically faster than pure-Python pypdf for the large
    # school books in this folder, while preserving the embedded Tajik text.
    document = pdfium.PdfDocument(str(path))
    return "\n\n".join(document[index].get_textpage().get_text_range() for index in range(len(document)))


def extract_docx(path: Path) -> str:
    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text)
    return "\n".join(parts)


def grade_for(path: Path) -> str:
    text = path.stem.lower().replace("ё", "е")
    patterns = (
        r"(?:синфи|синф|класс|class|grade|с)\s*[-_. ]*([5-9]|10|11)(?:\D|$)",
        r"(?:^|\D)(10|11|[5-9])(?:\D|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    if re.search(r"(?:5|v)[-_ ]*11|v[_ -]+xi|5[_ -]+11", text):
        return "all"
    return "all"


def source_kind(path: Path) -> str:
    name = path.stem.lower()
    if any(x in name for x in ("китоб", "китоби", "учебник", "дарсӣ")):
        return "textbook"
    if any(x in name for x in ("барнома", "стандарт", "роҳнамо", "программа")):
        return "curriculum"
    if any(x in name for x in ("конспект", "дарс", "нақша", "накша")):
        return "lesson_plan"
    return "reference"


def source_priority(kind: str) -> int:
    return {"textbook": 0, "curriculum": 1, "reference": 2, "lesson_plan": 3}.get(kind, 4)


def extract_item(item):
    path, relative, subject = item
    try:
        raw_text = extract_pdf(path) if path.suffix.lower() == ".pdf" else extract_docx(path)
        return item, clean_text(raw_text), None
    except Exception as exc:  # one bad book must not stop the full index
        return item, "", f"extract_error:{type(exc).__name__}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    source_root = args.source.resolve()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Keep the manifest deterministic while preserving already generated
    # files that may be useful to the image pipeline.
    for old in out_dir.glob("src_*.txt"):
        old.unlink()

    manifest = {
        "version": 1,
        "source_root": str(source_root),
        "sources": [],
        "by_subject_grade": {},
        "skipped": [],
    }
    seen_hashes: set[str] = set()

    candidates = []
    for path in sorted(source_root.rglob("*"), key=lambda p: str(p).lower()):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".docx", ".doc"}:
            continue
        relative = path.relative_to(source_root)
        subject_folder = relative.parts[0] if relative.parts else ""
        subject = SUBJECTS.get(subject_folder)
        if not subject:
            manifest["skipped"].append({"path": str(relative), "reason": "unknown_subject"})
        elif path.suffix.lower() == ".doc":
            manifest["skipped"].append({"path": str(relative), "reason": "legacy_doc"})
        else:
            candidates.append((path, relative, subject))

    # PDF parsing is slow; parallel extraction makes the one-time indexing
    # practical on a desktop while all manifest writes remain single-threaded.
    workers = min(8, max(2, (len(candidates) // 20) + 1))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for number, (item, text, error) in enumerate(pool.map(extract_item, candidates), 1):
            path, relative, subject = item
            if number % 25 == 0:
                print(f"processed {number}/{len(candidates)}", flush=True)
            if error:
                manifest["skipped"].append({"path": str(relative), "reason": error})
                continue
            if len(text) < 300:
                manifest["skipped"].append({"path": str(relative), "reason": "too_little_text"})
                continue

            digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
            if digest in seen_hashes:
                manifest["skipped"].append({"path": str(relative), "reason": "duplicate_text"})
                continue
            seen_hashes.add(digest)

            source_id = f"src_{digest[:16]}"
            text_file = out_dir / f"{source_id}.txt"
            text_file.write_text(text, encoding="utf-8")
            kind = source_kind(path)
            grade = grade_for(path)
            record = {
                "id": source_id,
                "file": text_file.name,
                "title": path.stem,
                "original_path": str(relative),
                "subject": subject,
                "grade": grade,
                "kind": kind,
                "chars": len(text),
            }
            manifest["sources"].append(record)
            by_grade = manifest["by_subject_grade"].setdefault(subject, {})
            by_grade.setdefault(grade, []).append(source_id)

    for subject, grades in manifest["by_subject_grade"].items():
        by_id = {s["id"]: s for s in manifest["sources"]}
        for grade, ids in grades.items():
            ids.sort(key=lambda sid: (source_priority(by_id[sid]["kind"]), by_id[sid]["title"].lower()))

    manifest["sources_count"] = len(manifest["sources"])
    manifest["skipped_count"] = len(manifest["skipped"])
    (out_dir / "_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps({
        "sources": manifest["sources_count"],
        "skipped": manifest["skipped_count"],
        "subjects": sorted(manifest["by_subject_grade"]),
        "legacy_doc_skipped": sum(1 for x in manifest["skipped"] if x["reason"] == "legacy_doc"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
