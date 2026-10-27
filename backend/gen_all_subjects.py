import asyncio
import io
import logging
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from app.ai_service import generate_material
from app.export_builder import build_konspekt_pdf

DESKTOP = r"C:\Users\user\Desktop\Konspektlar"
os.makedirs(DESKTOP, exist_ok=True)

SUBJECTS = [
    ("Таджикский язык", "Ҷумлаҳои содда ва мураккаб"),
    ("Таджикская литература", "Рӯдакӣ — асосгузори адабиёти форсу тоҷик"),
    ("Русский язык", "Имя существительное"),
    ("Английский язык", "Present Simple Tense"),
    ("Математика", "Амалҳо бо касрҳо"),
    ("Алгебра", "Муодилаҳои хаттӣ бо як номаълум"),
    ("Геометрия", "Теоремаи Пифагор"),
    ("Информатика", "Алгоритмҳо ва блок-схемаҳо"),
    ("Физика", "Қонунҳои ҳаракати Нютон"),
    ("Химия", "Реаксияҳои кимиёвӣ"),
    ("Биология", "Фотосинтез"),
    ("География", "Иқлими Тоҷикистон"),
    ("История Таджикистана", "Давлати Сомониён"),
    ("Всемирная история", "Ҷанги якуми ҷаҳонӣ"),
]

_usage_lines: list[str] = []


class _Catcher(logging.Handler):
    def emit(self, record):
        msg = record.getMessage()
        if "AI SUCCESS" in msg:
            _usage_lines.append(msg)


logging.getLogger("app").addHandler(_Catcher())
logging.getLogger("app.ai_service").addHandler(_Catcher())
logging.getLogger().addHandler(_Catcher())


def _safe_filename(subject: str) -> str:
    return re.sub(r"[^\w\- ]", "", subject).strip().replace(" ", "_")


async def main():
    results = []
    for i, (subject, topic) in enumerate(SUBJECTS):
        fname = f"{_safe_filename(subject)}.pdf"
        path = os.path.join(DESKTOP, fname)
        if os.path.exists(path):
            print(f"\n=== {subject}: already saved, skipping ===")
            results.append((subject, topic, path, "(previous run — see earlier log)"))
            continue
        if i > 0:
            print("  (waiting 60s for the per-minute token quota to clear...)")
            await asyncio.sleep(60)
        print(f"\n=== {subject}: {topic} ===")
        before = len(_usage_lines)
        t0 = time.time()
        try:
            content = await generate_material(
                material_type="konspekt",
                topic=topic,
                subject=subject,
                language="Таджикский",
                level="Средний",
                grade="8",
                template="nakscha",
            )
        except Exception as e:
            print(f"  FAILED: {e}")
            results.append((subject, topic, None, None))
            continue
        elapsed = time.time() - t0
        buf = build_konspekt_pdf(content, "Таджикский")
        fname = f"{_safe_filename(subject)}.pdf"
        path = os.path.join(DESKTOP, fname)
        with open(path, "wb") as f:
            f.write(buf.getvalue())
        new_lines = _usage_lines[before:]
        usage_str = new_lines[-1] if new_lines else "(no usage line captured)"
        print(f"  saved: {path}  ({elapsed:.1f}s)")
        print(f"  {usage_str}")
        results.append((subject, topic, path, usage_str))

    print("\n\n===== SUMMARY =====")
    total_in = total_out = total_calls = 0
    for subject, topic, path, usage_str in results:
        status = "OK" if path else "FAILED"
        print(f"{subject:28s} {status:7s} {usage_str}")
        if usage_str:
            m_in = re.search(r"tokens_in=(\d+)", usage_str)
            m_out = re.search(r"tokens_out=(\d+)", usage_str)
            if m_in and m_out:
                total_in += int(m_in.group(1))
                total_out += int(m_out.group(1))
                total_calls += 1
    print(f"\nTotal successful generations: {total_calls}/{len(SUBJECTS)}")
    print(f"Total tokens_in:  {total_in}")
    print(f"Total tokens_out: {total_out}")
    print(f"Total tokens:     {total_in + total_out}")


if __name__ == "__main__":
    asyncio.run(main())
