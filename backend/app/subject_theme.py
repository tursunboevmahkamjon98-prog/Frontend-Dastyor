"""Per-subject accent color for konspekt document BODIES (docx + PDF) —
one fixed, deliberately chosen color per subject so a Biology konspekt
and a Physics konspekt read as visually distinct from each other at a
glance, without introducing more than one color WITHIN a single document
(every section of one konspekt still uses its subject's one color
throughout — see export_builder.py's _add_konspekt_body_pdf docstring for
why multiple colors in the same document was explicitly rejected before
as "rainbow/childish").

Deliberately scoped to the body only — the PDF cover page
(cover_builder.py) stays the single uniform blue it already is; that was
a separate, explicit teacher decision ("previously varied per subject...
teacher asked for a single uniform look instead") and this module does
not touch it.
"""

import os

# Hex per subject — one deliberate, readable-on-white color each. Related
# subjects (the three math branches, the two history courses, the four
# language/literature courses) get related-but-distinguishable hues from
# the same family, rather than a single indistinguishable “language
# blue”/“math violet” repeated three times over.
_SUBJECT_ACCENTS: dict[str, str] = {
    "Таджикский язык": "#0e7c86",
    "Таджикская литература": "#6b3fa0",
    "Русский язык": "#c62839",
    "Английский язык": "#1d5fc2",
    "Математика": "#4a3aa7",
    "Алгебра": "#7c3aed",
    "Геометрия": "#0f9b6e",
    "Информатика": "#2a78d6",
    "Физика": "#eb6834",
    "Химия": "#0891b2",
    "Биология": "#008300",
    "География": "#a3702d",
    "История Таджикистана": "#8a2635",
    "Всемирная история": "#b5502e",
}

# Falls back to the app's original default blue for any subject not in
# the table above (a custom/free-typed subject, or a future one not yet
# added here) — keeps today's look rather than an undefined color.
_DEFAULT_ACCENT = "#3B82F6"


def get_subject_accent_hex(subject: str | None) -> str:
    """Returns e.g. "#008300" for "Биология", or the default blue if
    `subject` is empty/unrecognized."""
    if not subject:
        return _DEFAULT_ACCENT
    return _SUBJECT_ACCENTS.get(subject, _DEFAULT_ACCENT)


def get_subject_accent_rgb(subject: str | None) -> tuple[int, int, int]:
    """Same lookup as get_subject_accent_hex, as an (r, g, b) int tuple —
    convenience for callers building a docx RGBColor(*rgb)."""
    hex_str = get_subject_accent_hex(subject).lstrip("#")
    return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)


# Small decorative subject illustration for a presentation's cover slide
# (see export_builder.py's build_presentation_pptx) — public-domain/CC0
# clipart from openclipart.org (chosen for licensing, not to match 5-rka's
# custom character art: see the "ready-made clipart" product decision).
# Deliberately NOT the same grouping as _SUBJECT_ACCENTS above: the three
# language courses share one generic "speech bubble" image (no distinct
# per-language clipart exists, and forcing one would be worse than a
# shared but honest generic icon), while the two history courses get
# different images (Tajik history: a scroll; world history: an artefact)
# since suitable art existed for both.
_SUBJECT_ILLUSTRATIONS: dict[str, str] = {
    "Математика": "matematika.png",
    "Алгебра": "algebra.png",
    "Геометрия": "geometriya.png",
    "Информатика": "informatika.png",
    "Физика": "fizika.png",
    "Химия": "himiya.png",
    "Биология": "biologiya.png",
    "География": "geografiya.png",
    "Русский язык": "til.png",
    "Английский язык": "til.png",
    "Таджикский язык": "til.png",
    "Таджикская литература": "adabiyot.png",
    "История Таджикистана": "tarix_tj.png",
    "Всемирная история": "tarix_dunyo.png",
}

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "subjects")


def get_subject_illustration_path(subject: str | None) -> str | None:
    """Absolute path to the subject's cover-slide illustration PNG, or
    None if this subject has no matching image (a custom/free-typed
    subject, or one of the few not covered by the clipart search) — the
    caller skips drawing it entirely rather than falling back to a
    generic image, since an unrelated picture is worse than none."""
    if not subject:
        return None
    fname = _SUBJECT_ILLUSTRATIONS.get(subject)
    if not fname:
        return None
    path = os.path.join(_ASSETS_DIR, fname)
    return path if os.path.exists(path) else None
