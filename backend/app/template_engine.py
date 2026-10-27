"""Composable konspekt templates: structure x palette x tone.

Seven hand-written templates existed, and every new one meant another literal
in konspekt_templates.TEMPLATES. That does not reach a few hundred designs,
and writing a few hundred literals by hand would not produce a few hundred
*good* designs - it would produce a few hundred near-duplicates nobody can
choose between.

So the three things that actually vary are separated into independent axes:

  structure  the page skeleton: heading treatment, sidebar, chrome, density
  palette    the colour, which until now was always derived from the subject
  tone       how it is pitched: primary / middle / senior grades

Each axis is curated on its own, so every combination is coherent by
construction rather than by luck. 12 x 14 x 3 = 504 templates today, and one
new structure adds 42 more.

Nothing here changes an existing template. A composed template is still a
plain KonspektTemplate, so all four builders (export_builder, docx_builder,
konspekt_builder, pptx) keep reading the same six fields they always read;
the added fields carry defaults that reproduce today's behaviour exactly.

Composed ids look like "akademik.indigo.senior" and are resolved by
konspekt_templates.get_template, which still falls back to the default for
anything it does not recognise - so a material saved with an id that later
disappears keeps rendering.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.konspekt_templates import KonspektTemplate

ID_SEPARATOR = "."


@dataclass(frozen=True)
class Structure:
    """The page skeleton. Font family belongs here, not to the palette: a
    registry blank is serif because of what it is, not because of its colour."""

    id: str
    name: str
    description: str
    header_style: str
    font_family: str
    sidebar_sections: tuple[str, ...] = ()
    alt_row_tint: bool = False
    minimal_chrome: bool = False
    plan_layout: bool = False


@dataclass(frozen=True)
class Palette:
    """accent=None keeps the long-standing behaviour: the colour follows the
    subject via subject_theme. Every other palette overrides it, which is what
    makes colour a design choice instead of a lookup."""

    id: str
    name: str
    accent: str | None
    tint: str


@dataclass(frozen=True)
class Tone:
    """Grade band. Younger pages want air and larger type, senior pages want
    density; the same structure should not be set identically for a 2nd-grade
    reading sheet and an 11th-grade exam revision."""

    id: str
    name: str
    density: str
    allow_tint: bool


STRUCTURES: dict[str, Structure] = {
    "klassik": Structure(
        id="klassik", name="Классический",
        description="Пронумерованные разделы, цветные карточки.",
        header_style="numbered", font_family="sans",
    ),
    "zamonaviy": Structure(
        id="zamonaviy", name="Современный",
        description="Понятия и термины — в боковой панели, подчёркнутые заголовки.",
        header_style="underline", font_family="sans",
        sidebar_sections=("key_concepts", "key_terms", "tools"),
    ),
    "minimal": Structure(
        id="minimal", name="Минимализм",
        description="Чистая типографика, тонкие линии, без заливки.",
        header_style="smallcaps", font_family="sans", minimal_chrome=True,
    ),
    "akademik": Structure(
        id="akademik", name="Академический",
        description="Засечный шрифт, сдержанные тона, строгие заголовки.",
        header_style="serif", font_family="serif",
    ),
    "rangli": Structure(
        id="rangli", name="Яркий",
        description="Разделы на цветных плашках, чередующиеся фоны.",
        header_style="bar", font_family="sans", alt_row_tint=True,
    ),
    "blanka": Structure(
        id="blanka", name="Нақшаи тавзеҳотӣ",
        description="Официальный школьный бланк: без цвета, разделы в строку.",
        header_style="smallcaps", font_family="serif",
        minimal_chrome=True, plan_layout=True,
    ),
    "daftar": Structure(
        id="daftar", name="Тетрадь",
        description="Боковая панель с понятиями, мягкие полосы — для младших классов.",
        header_style="underline", font_family="sans",
        sidebar_sections=("key_concepts", "key_terms", "tools"), alt_row_tint=True,
    ),
    "jurnal": Structure(
        id="jurnal", name="Журнальный",
        description="Крупные засечные заголовки на плашке, широкие поля.",
        header_style="bar", font_family="serif",
    ),
    "spravochnik": Structure(
        id="spravochnik", name="Справочник",
        description="Нумерованные разделы и боковая панель терминов — для повторения.",
        header_style="numbered", font_family="serif",
        sidebar_sections=("key_terms",),
    ),
    "konspekt_lite": Structure(
        id="konspekt_lite", name="Краткий",
        description="Только заголовки и суть, минимум оформления.",
        header_style="smallcaps", font_family="sans",
        minimal_chrome=True, sidebar_sections=("key_concepts",),
    ),
    "praktikum": Structure(
        id="praktikum", name="Практикум",
        description="Рабочий лист: разделы в строку, место для записей.",
        header_style="numbered", font_family="sans", plan_layout=True,
    ),
    "tahlil": Structure(
        id="tahlil", name="Разбор",
        description="Подчёркнутые заголовки, панель понятий, засечный текст.",
        header_style="underline", font_family="serif",
        sidebar_sections=("key_concepts", "key_terms"),
    ),
}

# accent=None is the subject-driven default the app has always used, kept as a
# first-class palette so "follow the subject" stays available and is the one
# composed templates fall back to.
PALETTES: dict[str, Palette] = {
    "fan": Palette("fan", "По предмету", None, "#F3F4F6"),
    "indigo": Palette("indigo", "Индиго", "#4338CA", "#EEF0FD"),
    "koʻk": Palette("koʻk", "Синий", "#1D5FC2", "#E7EFFB"),
    "teal": Palette("teal", "Бирюзовый", "#0F766E", "#E3F5F2"),
    "yashil": Palette("yashil", "Зелёный", "#0F7B43", "#E4F3EA"),
    "zaytun": Palette("zaytun", "Оливковый", "#4D7C0F", "#EEF4E2"),
    "amber": Palette("amber", "Янтарный", "#B45309", "#FBF0DF"),
    "terrakota": Palette("terrakota", "Терракота", "#C2410C", "#FBEBE2"),
    "qizil": Palette("qizil", "Красный", "#B91C1C", "#FBE9E9"),
    "pushti": Palette("pushti", "Розовый", "#A83F6C", "#F9E8EF"),
    "siyoh": Palette("siyoh", "Чернильный", "#3730A3", "#EAEAF7"),
    "binafsha": Palette("binafsha", "Фиолетовый", "#6B3FA0", "#F0E9F7"),
    "grafit": Palette("grafit", "Графит", "#374151", "#EEF0F2"),
    "jigarrang": Palette("jigarrang", "Коричневый", "#8A5A2B", "#F5EDE3"),
}

TONES: dict[str, Tone] = {
    # Younger pages keep the tint a structure asks for; senior pages drop it,
    # which is why the same structure reads differently across the bands.
    "boshlangich": Tone("boshlangich", "1–4 класс", "airy", True),
    "orta": Tone("orta", "5–9 класс", "normal", True),
    "yuqori": Tone("yuqori", "10–11 класс", "compact", False),
}

DEFAULT_TONE = "orta"


def compose_id(structure: str, palette: str, tone: str = DEFAULT_TONE) -> str:
    return ID_SEPARATOR.join((structure, palette, tone))


def parse_id(template_id: str) -> tuple[str, str, str] | None:
    parts = template_id.split(ID_SEPARATOR)
    if len(parts) != 3:
        return None
    structure, palette, tone = parts
    if structure not in STRUCTURES or palette not in PALETTES or tone not in TONES:
        return None
    return structure, palette, tone


def compose(template_id: str) -> KonspektTemplate | None:
    """Build a KonspektTemplate from a composed id, or None if it is not one."""
    parsed = parse_id(template_id)
    if parsed is None:
        return None
    structure_id, palette_id, tone_id = parsed
    structure = STRUCTURES[structure_id]
    palette = PALETTES[palette_id]
    tone = TONES[tone_id]

    return KonspektTemplate(
        id=template_id,
        name=f"{structure.name} · {palette.name}",
        description=structure.description,
        header_style=structure.header_style,
        font_family=structure.font_family,
        sidebar_sections=structure.sidebar_sections,
        # A senior page drops the alternating tint even when its structure
        # asks for one: banded rows read as a worksheet, not as revision.
        alt_row_tint=structure.alt_row_tint and tone.allow_tint,
        minimal_chrome=structure.minimal_chrome,
        plan_layout=structure.plan_layout,
        accent=palette.accent,
        tint=palette.tint,
        density=tone.density,
        structure=structure_id,
        palette=palette_id,
        tone=tone_id,
    )


def catalog(tone: str | None = None) -> list[KonspektTemplate]:
    """Every composed template, optionally for one tone only."""
    tones = [tone] if tone in TONES else list(TONES)
    return [
        composed
        for s in STRUCTURES
        for p in PALETTES
        for t in tones
        if (composed := compose(compose_id(s, p, t))) is not None
    ]


def tone_for_grade(grade: str | None) -> str:
    """"7 класс" -> "orta". Unparseable grades fall to the middle band."""
    digits = "".join(c for c in (grade or "") if c.isdigit())
    if not digits:
        return DEFAULT_TONE
    number = int(digits[:2])
    if number <= 4:
        return "boshlangich"
    if number <= 9:
        return "orta"
    return "yuqori"
