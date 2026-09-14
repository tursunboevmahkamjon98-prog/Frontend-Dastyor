"""Registry of selectable konspekt export layouts — a teacher picks one of
these per konspekt (see the "template" wizard step), and the SAME choice
drives both the PDF (export_builder.py) and DOCX (docx_builder.py) exports
plus the PDF cover (cover_builder.py), so a teacher gets one consistent
document regardless of which format they download.

Deliberately a REGISTRY OF STYLE KNOBS, not 5 copy-pasted 300-line render
functions: every template still walks the exact same section data in the
exact same order (see docx_builder.py's _add_konspekt_body / export_builder
.py's _add_konspekt_body_pdf) — only the VISUAL TREATMENT (header style,
font family, card fill vs. border, cover decoration) changes per template.
This is also what makes new sections (like this session's code_blocks/
quick_check) automatically show up correctly-styled in every template
without each one needing its own update.

"klassik" is the pre-existing look, byte-for-byte — any konspekt saved
before this feature existed has no "template" key at all, and get_template
falls back to "klassik" for it, so old data renders exactly as it always
has (see get_template's docstring).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class KonspektTemplate:
    id: str
    # Wizard-facing name/description (Russian — matches the rest of the
    # app's UI chrome, which is Russian-only regardless of content language;
    # same convention as "Отменить"/"AI создаёт конспект…" elsewhere).
    name: str
    description: str
    # Section header treatment — matches a named renderer in both
    # docx_builder.py's _SECTION_RENDERERS and export_builder.py's
    # _PDF_SECTION_RENDERERS. See those for what each style actually draws.
    header_style: str  # "numbered" | "underline" | "smallcaps" | "serif" | "bar"
    # "sans" = Calibri (docx) / FONT_NAME=Arial (pdf), matching today's
    # look. "serif" = Cambria (docx) / MATH_FONT=Cambria (pdf, already
    # registered for math glyphs — reused here, not a new font file).
    font_family: str  # "sans" | "serif"
    # Reference-card sections (key_concepts/key_terms/tools) pulled into a
    # standalone tinted panel right after the title instead of appearing
    # inline in normal reading order — only "zamonaviy" uses this; empty
    # for every other template (those keep the sections inline, as today).
    sidebar_sections: tuple[str, ...]
    # Alternating light background tint behind each section's body text,
    # for a "rangli" liveliness — every other template leaves the body
    # background plain white, same as today.
    alt_row_tint: bool
    # Strips the filled decoration the renderers otherwise apply
    # everywhere — the dark title block, the solid table header row and
    # row tints, the grey formula panel, the filled number badge on worked
    # examples. Those are drawn by shared code, so before this knob
    # existed "Минимализм" promised "clean typography, thin lines, no
    # fills" in its own description while rendering exactly the same
    # heavy chrome as every other template. Only the section-header style
    # actually differed.
    #
    # Deliberately one flag rather than five: the point of the look is
    # that ALL the fills go away together. A half-minimal page (plain
    # table but a dark cover block) reads as an inconsistency, not a
    # style.
    minimal_chrome: bool = False
    # Renders the body as the official Tajik school lesson-plan document
    # ("Нақшаи тавзеҳотӣ") instead of the card/section layout every other
    # template shares: a centred all-caps title under a date/class line,
    # run-in bold-italic headings with the text continuing on the same
    # line, ruled blanks where a section has nothing to print, and a
    # centred page number. Black on white throughout.
    #
    # This is the one template that changes the STRUCTURE rather than the
    # decoration, so it gets its own body renderer (see export_builder's
    # _pdf_plan_body) rather than another set of style knobs.
    plan_layout: bool = False


TEMPLATES: dict[str, KonspektTemplate] = {
    "klassik": KonspektTemplate(
        id="klassik",
        name="Классический",
        description="Проверенный вид: пронумерованные разделы, цветные карточки.",
        header_style="numbered",
        font_family="sans",
        sidebar_sections=(),
        alt_row_tint=False,
    ),
    "zamonaviy": KonspektTemplate(
        id="zamonaviy",
        name="Современный",
        description="Ключевые понятия и термины — в боковой панели сверху, подчёркнутые заголовки.",
        header_style="underline",
        font_family="sans",
        sidebar_sections=("key_concepts", "key_terms", "tools"),
        alt_row_tint=False,
    ),
    "minimal": KonspektTemplate(
        id="minimal",
        name="Минимализм",
        description="Чистая типографика, тонкие линии, без заливки — для чёткой печати.",
        header_style="smallcaps",
        font_family="sans",
        sidebar_sections=(),
        alt_row_tint=False,
        minimal_chrome=True,
    ),
    "rasmiy": KonspektTemplate(
        id="rasmiy",
        name="Официальный",
        description="Академический стиль: засечный шрифт, сдержанные тона.",
        header_style="serif",
        font_family="serif",
        sidebar_sections=(),
        alt_row_tint=False,
    ),
    "rangli": KonspektTemplate(
        id="rangli",
        name="Яркий",
        description="Разделы на цветных плашках, чередующиеся фоны — живой вид для младших классов.",
        header_style="bar",
        font_family="sans",
        sidebar_sections=(),
        alt_row_tint=True,
    ),
    "playful": KonspektTemplate(
        id="playful",
        name="Яркий блокнот",
        description="Обложка в стиле тетради: пастельные стикеры, спиральные поля, рукописный заголовок.",
        header_style="underline",
        font_family="sans",
        sidebar_sections=("key_concepts", "key_terms", "tools"),
        alt_row_tint=True,
    ),
    "nakscha": KonspektTemplate(
        id="nakscha",
        name="Нақшаи тавзеҳотӣ",
        description="Официальный школьный бланк: заголовок по центру, строка даты и класса, разделы в строку, без цвета.",
        header_style="smallcaps",
        font_family="serif",
        sidebar_sections=(),
        alt_row_tint=False,
        minimal_chrome=True,
        plan_layout=True,
    ),
}

DEFAULT_TEMPLATE_ID = "klassik"


def get_template(template_id: str | None) -> KonspektTemplate:
    """Fail-soft lookup — an unrecognized or missing id (every konspekt
    saved before this feature existed) falls back to "klassik", same
    fallback pattern as app/subject_theme.py's get_subject_accent_hex."""
    if not template_id:
        return TEMPLATES[DEFAULT_TEMPLATE_ID]
    return TEMPLATES.get(template_id, TEMPLATES[DEFAULT_TEMPLATE_ID])
