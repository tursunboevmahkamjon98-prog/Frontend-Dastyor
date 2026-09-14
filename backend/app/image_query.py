# -*- coding: utf-8 -*-
"""Turning a slide into an image search that returns the RIGHT picture.

The problem
-----------
A slide about "Строение клетки" must not get a photograph of a laboratory
or a nice picture of nature. It must get a labelled cell diagram showing
the membrane, the nucleus, the mitochondria — the structures the slide is
actually about. A beautiful but wrong picture is worse than a plain
correct one, and that ordering is the whole point of this module.

The model already writes a short English `image_query` on every slide
(see ai_service._presentation_prompt), and that phrase is the best signal
available: it is the only thing in the pipeline that has read the slide's
own content. So it is kept as the semantic core and this module does the
two things the model reliably does NOT do:

1. **Qualifies it for the subject.** "right triangle labeled" is a better
   search with "labeled mathematical diagram" appended, because Commons
   is full of photographs and the qualifier is what pushes the result
   toward a teaching figure.

2. **Qualifies it for the branch of the subject.** A biology deck about
   the cell and one about ecosystems want a different CHARACTER of
   picture, so the lesson topic selects extra qualifiers (see
   SubjectTemplate.topic_categories).

Fallback chain, not one query
-----------------------------
build_queries returns queries ordered most-specific-first, and
image_builder.fetch_lesson_images walks that list until it finds a usable
file. The LAST entry is always the model's own untouched phrase, so this
module can only ever improve the result: if every enrichment misses, the
search lands exactly where it lands today.
"""

from __future__ import annotations

import re

from app.subject_templates import SubjectTemplate, resolve


# Phrases that come back with a generic, useless picture. A query that is
# only one of these (or only the subject's own name) has told the search
# nothing about the slide, and gets rebuilt from the topic instead.
_TOO_GENERIC = {
    "biology", "mathematics", "math", "maths", "physics", "chemistry",
    "geography", "history", "informatics", "computer science", "literature",
    "language", "english", "russian", "tajik", "science", "school",
    "education", "educational", "lesson", "classroom", "students",
    "биология", "математика", "физика", "химия", "география", "история",
    "информатика", "литература", "язык", "урок", "школа",
}

# Words that describe the MEDIUM rather than the subject — they crowd out
# real search terms without narrowing anything, because every Commons file
# is already an image.
_NOISE = {"image", "images", "picture", "pictures", "photo", "photos",
          "photograph", "jpg", "png", "wikipedia", "wikimedia"}

# A query longer than this stops narrowing and starts missing: Commons
# matches on file titles and categories, and every extra term is another
# thing that has to appear.
_MAX_WORDS = 9


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[^\wЀ-ӿ-]+", str(text or "")) if w]


def _clean(text: str) -> str:
    """Lowercased, de-noised, de-duplicated — so appending a qualifier
    that repeats a word the core already has doesn't waste one of the
    nine slots."""
    seen: list[str] = []
    for w in _words(text):
        lw = w.lower()
        if lw in _NOISE or lw in seen:
            continue
        seen.append(lw)
    return " ".join(seen)


def _join(*parts: str) -> str:
    """Concatenate query fragments, dropping repeats and capping length."""
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
    # One bare word is almost never specific enough to find the right
    # teaching figure — "cell" returns a prison cell as readily as a
    # biological one.
    return len(cleaned.split()) < 2


def _topic_qualifiers(template: SubjectTemplate, topic: str, slide_text: str) -> tuple[str, ...]:
    """The extra qualifiers for THIS branch of the subject.

    Both the lesson topic and the slide's own text are searched, so a
    genetics slide inside a general biology lesson still gets the
    genetics treatment."""
    haystack = f"{topic} {slide_text}".lower()
    for needles, qualifiers in template.topic_categories:
        if any(n in haystack for n in needles):
            return qualifiers
    return ()


def _slide_text(slide: dict) -> str:
    """Everything on the slide that could name a key concept, as one
    string — the title first, since it is the most on-point."""
    bits = [str(slide.get("title") or "")]
    bits.extend(str(b) for b in (slide.get("bullet_points") or [])[:4])
    bits.append(str(slide.get("body") or "")[:200])
    return " ".join(b for b in bits if b)


def build_queries(slide: dict, topic: str, subject: str | None,
                  grade: str | None = None) -> list[str]:
    """Search phrases for one slide, most specific first.

    The caller hands the whole list to fetch_lesson_images, which walks
    it until something usable turns up."""
    template = resolve(subject, grade)
    core = _clean(slide.get("image_query") or "")
    text = _slide_text(slide)
    topic_quals = _topic_qualifiers(template, topic, text)
    subject_quals = template.image_qualifiers

    # A query the model left generic ("biology") is rebuilt around the
    # lesson topic instead, which at least names what the deck is about.
    if _is_generic(core, subject):
        core = _clean(topic)

    queries: list[str] = []

    def _add(q: str) -> None:
        q = q.strip()
        if q and q not in queries:
            queries.append(q)

    # 1. The full picture: slide concept + branch of the subject + the
    #    kind of figure this subject teaches with.
    if topic_quals:
        _add(_join(core, " ".join(topic_quals), subject_quals[0] if subject_quals else ""))
    # 2. Slide concept + subject character.
    _add(_join(core, " ".join(subject_quals)))
    # 3. Slide concept inside the lesson's topic — catches the case where
    #    the slide phrase alone is ambiguous ("structure" in a cell
    #    lesson) but the topic disambiguates it.
    topic_clean = _clean(topic)
    if topic_clean and topic_clean != core:
        _add(_join(core, topic_clean))
    # 4. Exactly what the model asked for. Always last, always present:
    #    this is today's behaviour, so enrichment can only add options,
    #    never remove the one that already works.
    original = _clean(slide.get("image_query") or "")
    if original:
        _add(original)
    elif topic_clean:
        _add(topic_clean)

    return queries


def describe(slide: dict, topic: str, subject: str | None,
             grade: str | None = None) -> str:
    """One-line explanation of how a slide's search was built — for logs
    and for the test script, so a wrong picture can be traced to the
    phrase that fetched it rather than guessed at."""
    qs = build_queries(slide, topic, subject, grade)
    tpl = resolve(subject, grade)
    return f"[{tpl.id}] {slide.get('title', '')!r} -> " + " | ".join(qs)
