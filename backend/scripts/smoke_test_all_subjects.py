"""Generate one unsaved hard-topic konspekt per indexed subject and report metrics."""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai_service import _load_cached_textbook, generate_material


CASES = [
    ("Таджикская литература", "Таҳлили ғазалиёти Ҳофиз", "11 класс"),
    ("Алгебра", "Ҳосила ва истифодаи он барои таҳлили функсия", "11 класс"),
    ("Биология", "Митоз ва мейоз ва аҳамияти онҳо", "10 класс"),
    ("География", "Тағйирёбии иқлим ва гардиши атмосфера", "10 класс"),
    ("Геометрия", "Масъалаҳои мураккаби стереометрӣ ва ҳаҷми ҷисмҳо", "11 класс"),
    ("Английский язык", "Шартҳои омехта дар забони англисӣ", "11 класс"),
    ("Арабский язык", "Ҷумлаи шартӣ ва сарфи феъл", "10 класс"),
    ("Русский язык", "Ҷумлаҳои мураккаби тобеъ ва аломатҳои китобат", "11 класс"),
    ("Таджикский язык", "Ҷумлаи мураккаб ва аъзои пайрави он", "10 класс"),
    ("Информатика", "Алгоритмҳои рекурсивӣ ва мураккабии вақт", "11 класс"),
    ("Математика", "Эҳтимолият ва комбинаторика", "11 класс"),
    ("История Таджикистана", "Истиқлолияти Тоҷикистон ва ташаккули давлатдории муосир", "11 класс"),
    ("Технология", "Амнияти шабака ва рамзгузории маълумот", "10 класс"),
    ("Физика", "Индуксияи электромагнитӣ ва қонуни Фарадей", "11 класс"),
    ("Химия", "Реаксияҳои оксидшавӣ ва барқароршавӣ ва ҳуҷайраи галванӣ", "11 класс"),
    ("Естествознание", "Гардиши моддаҳо дар табиат ва таъсири инсон", "6 класс"),
    ("Искусство", "Перспектива ва таркиби тасвир", "8 класс"),
    ("Физическая культура", "Энергетикаи аэробӣ ва анаэробӣ дар машқҳои варзишӣ", "10 класс"),
    ("Обществознание", "Ҳуқуқи инсон ва сохтори давлати ҳуқуқбунёд", "10 класс"),
]

BAD_TERMS = (
    "условие", "пример", "вопрос", "ответ", "системасининг", "бир нечта",
    "запутанлик", "entangled", "волновӣ", "мӯйбанд", "мусоидат мекунад",
)


def flatten(value, out: list[str]) -> None:
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, list):
        for item in value:
            flatten(item, out)
    elif isinstance(value, dict):
        for item in value.values():
            flatten(item, out)


async def run_case(subject: str, topic: str, grade: str) -> dict:
    source = _load_cached_textbook(subject, grade, topic) or ""
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    started = time.perf_counter()
    try:
        with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
            content = await generate_material(
                material_type="konspekt",
                topic=topic,
                subject=subject,
                language="Таджикский",
                level="Сложный",
                grade=grade,
                include_homework=False,
                include_fun_facts=False,
                include_assessment=False,
                include_examples=True,
            )
        status = "ok"
        error = None
    except Exception as exc:
        content = {}
        status = "error"
        error = str(exc)[:180]

    logs = captured_out.getvalue() + captured_err.getvalue()
    calls = [
        tuple(map(int, match))
        for match in re.findall(r"tokens_in=(\d+) tokens_out=(\d+) tokens_total=(\d+)", logs)
    ]
    text_parts: list[str] = []
    flatten(content, text_parts)
    all_text = " ".join(text_parts).lower()
    return {
        "subject": subject,
        "topic": topic,
        "grade": grade,
        "status": status,
        "error": error,
        "seconds": round(time.perf_counter() - started, 2),
        "source_chars": len(source),
        "calls": len(calls),
        "tokens_in": sum(item[0] for item in calls),
        "tokens_out": sum(item[1] for item in calls),
        "tokens_total": sum(item[2] for item in calls),
        "bad_terms": {term: all_text.count(term) for term in BAD_TERMS if term in all_text},
        "main_content_chars": len(str(content.get("main_content") or "")),
        "key_concepts": len(content.get("key_concepts") or []),
        "title": content.get("title"),
    }


async def main() -> None:
    results = []
    for index, case in enumerate(CASES, 1):
        result = await run_case(*case)
        results.append(result)
        print(json.dumps({"progress": f"{index}/{len(CASES)}", **result}, ensure_ascii=False), flush=True)
    print(json.dumps({
        "summary": {
            "subjects": len(results),
            "ok": sum(item["status"] == "ok" for item in results),
            "errors": sum(item["status"] == "error" for item in results),
            "total_tokens": sum(item["tokens_total"] for item in results),
            "total_seconds": round(sum(item["seconds"] for item in results), 2),
            "source_backed": sum(item["source_chars"] > 0 for item in results),
            "with_bad_terms": sum(bool(item["bad_terms"]) for item in results),
        }
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
