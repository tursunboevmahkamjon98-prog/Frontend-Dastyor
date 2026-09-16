
from __future__ import annotations

import re

from app.subject_templates import SubjectTemplate, resolve


_TOO_GENERIC = {
    "biology", "mathematics", "math", "maths", "physics", "chemistry",
    "geography", "history", "informatics", "computer science", "literature",
    "language", "english", "russian", "tajik", "science", "school",
    "education", "educational", "lesson", "classroom", "students",
    "биология", "математика", "физика", "химия", "география", "история",
    "информатика", "литература", "язык", "урок", "школа",
}

_NOISE = {"image", "images", "picture", "pictures", "photo", "photos",
          "photograph", "jpg", "png", "wikipedia", "wikimedia"}

_MAX_WORDS = 9


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[^\wЀ-ӿ-]+", str(text or "")) if w]


def _clean(text: str) -> str:
    seen: list[str] = []
    for w in _words(text):
        lw = w.lower()
        if lw in _NOISE or lw in seen:
            continue
        seen.append(lw)
    return " ".join(seen)


def _join(*parts: str) -> str:
    out: list[str] = []
    for part in parts:
        for w in _words(part):
            lw = w.lower()
            if lw in _NOISE or lw in out:
                continue
            out.append(lw)
            if len(out) >= _MAX_WORDS:
                return " ".join(out)
    return " ".join(out)


def _is_generic(core: str, subject: str | None) -> bool:
    cleaned = _clean(core)
    if not cleaned:
        return True
    if cleaned in _TOO_GENERIC:
        return True
    if subject and cleaned == _clean(subject):
        return True
    return len(cleaned.split()) < 2


def _topic_qualifiers(template: SubjectTemplate, topic: str, slide_text: str) -> tuple[str, ...]:
    haystack = f"{topic} {slide_text}".lower()
    for needles, qualifiers in template.topic_categories:
        if any(n in haystack for n in needles):
            return qualifiers
    return ()


def _slide_text(slide: dict) -> str:
    bits = [str(slide.get("title") or "")]
    bits.extend(str(b) for b in (slide.get("bullet_points") or [])[:4])
    bits.append(str(slide.get("body") or "")[:200])
    return " ".join(b for b in bits if b)


def build_queries(slide: dict, topic: str, subject: str | None,
                  grade: str | None = None) -> list[str]:
    template = resolve(subject, grade)
    core = _clean(slide.get("image_query") or "")
    text = _slide_text(slide)
    topic_quals = _topic_qualifiers(template, topic, text)
    subject_quals = template.image_qualifiers

    if _is_generic(core, subject):
        core = _clean(topic)

    queries: list[str] = []

    def _add(q: str) -> None:
        q = q.strip()
        if q and q not in queries:
            queries.append(q)

    if topic_quals:
        _add(_join(core, " ".join(topic_quals), subject_quals[0] if subject_quals else ""))
    _add(_join(core, " ".join(subject_quals)))
    topic_clean = _clean(topic)
    if topic_clean and topic_clean != core:
        _add(_join(core, topic_clean))
    original = _clean(slide.get("image_query") or "")
    if original:
        _add(original)
    elif topic_clean:
        _add(topic_clean)

    return queries


def describe(slide: dict, topic: str, subject: str | None,
             grade: str | None = None) -> str:
    qs = build_queries(slide, topic, subject, grade)
    tpl = resolve(subject, grade)
    return f"[{tpl.id}] {slide.get('title', '')!r} -> " + " | ".join(qs)
