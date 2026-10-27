
from dataclasses import dataclass


@dataclass(frozen=True)
class KonspektTemplate:
    id: str
    name: str
    description: str
    header_style: str
    font_family: str
    sidebar_sections: tuple[str, ...]
    alt_row_tint: bool
    minimal_chrome: bool = False
    plan_layout: bool = False

    # Added for template_engine. Every default reproduces the behaviour that
    # existed before them, so the seven literals below are untouched by this:
    #   accent=None  -> the colour keeps coming from subject_theme
    #   tint=None    -> builders keep their own tint
    #   density      -> the spacing builders already used
    accent: str | None = None
    tint: str | None = None
    density: str = "normal"
    structure: str | None = None
    palette: str | None = None
    tone: str | None = None


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

# Kept in sync with template_engine.ID_SEPARATOR without importing it.
ID_SEPARATOR = "."


def get_template(template_id: str | None) -> KonspektTemplate:
    if not template_id:
        return TEMPLATES[DEFAULT_TEMPLATE_ID]
    if template_id in TEMPLATES:
        return TEMPLATES[template_id]

    # Composed ids ("akademik.indigo.senior") are built on demand. Imported
    # here rather than at module scope because template_engine imports this
    # module for KonspektTemplate.
    if ID_SEPARATOR in template_id:
        from app.template_engine import compose

        composed = compose(template_id)
        if composed is not None:
            return composed

    # Unknown id - a material saved against a template that no longer exists
    # still has to render.
    return TEMPLATES[DEFAULT_TEMPLATE_ID]
