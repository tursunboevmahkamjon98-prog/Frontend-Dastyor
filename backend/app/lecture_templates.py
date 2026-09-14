"""The four designs a лекция can be printed in.

Not a palette. Each entry here changes the DOCUMENT, not its colour: a
different title page, a different way section headings are set, a
different shape for the "Важно"/"Пример" callouts, a different table, a
different treatment for definitions. Two lectures printed in two of these
templates should not look like the same file with the accent swapped —
that was the whole complaint about the konspekt templates this replaces
(see konspekt_templates.KonspektTemplate, which really is a knob registry
over one fixed layout).

The renderer reads these names and dispatches to a function per name
(lecture_builder._COVERS / _HEADINGS / _CALLOUTS / _TABLES /
_DEFINITIONS), so adding a design means writing those five functions —
not another copy of the whole builder.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LectureTemplate:
    id: str
    name: str
    description: str

    # ── the five things that actually differ ────────────────────────────
    cover: str        # "none" | "classic" | "split" | "banner" | "worksheet"
    heading: str      # "runin" | "smallcaps" | "ghost" | "band" | "boxed"
    callout: str      # "inline" | "rule" | "card" | "outline" | "dashed"
    table: str        # "ruled" | "filled" | "editorial" | "grid"
    definition: str   # "runin" | "cards" | "quote" | "framed"

    # ── typography ──────────────────────────────────────────────────────
    # "serif" sets the body in Cambria, "sans" in Arial. The heading font
    # is chosen separately: a serif heading over sans body is the
    # magazine convention, and it is what makes "jurnal" read differently
    # from "zamonaviy" even before any colour is involved.
    body_font: str    # "serif" | "sans"
    head_font: str    # "serif" | "sans"

    # Body size/leading in points. A worksheet is set larger and looser
    # (it is written on), an academic handout tighter.
    body_size: float
    body_leading: float

    # Page margins in cm: left/right, top, bottom.
    margin_x: float
    margin_top: float

    # How much colour the design carries. "full" uses the subject accent
    # for headings, rules and fills; "quiet" keeps the page black-on-white
    # and spends the accent only on thin rules and labels.
    colour: str       # "full" | "quiet"

    # Whether the contents page is printed. A short worksheet does not
    # want one; a 6-page academic handout is unusable without it.
    contents: bool = True

    # "playful" only — replaces the entire linear section-by-section body
    # with a single-page GRID of colour-labelled boxes (see
    # konspekt_builder.py's _build_notebook_grid), built directly from a
    # real reference photo a teacher sent (a hand-drawn notebook-style
    # "КОНСПЕКТ" sheet: Цель/Ключевые слова/Основная часть/Формулы/Вывод/
    # Вопросы boxes on ruled notebook paper). Every other template still
    # goes through the normal heading/callout/definition renderers above;
    # this is the one template that changes the DOCUMENT'S SHAPE, not
    # just its decoration — same reasoning konspekt_templates.py's
    # plan_layout flag already documents for "nakscha".
    notebook_grid: bool = False


TEMPLATES: dict[str, LectureTemplate] = {
    # The working format, and the default: what a teacher writes into a
    # lesson journal rather than what a publisher prints. No cover page at
    # all — the document opens on a form-like header block (topic,
    # subject, class, date, duration, aim) and goes straight into the
    # content, sections run in at the head of their own paragraph, notes
    # set as one-line margin remarks. Everything is tuned for the fewest
    # possible pages: a план-конспект that runs to seven pages is not one.
    "planspekt": LectureTemplate(
        id="planspekt",
        name="План-конспект",
        description="Лаконичный рабочий формат: шапка-бланк вместо обложки, "
                    "разделы в строку, компактные пометки на полях.",
        cover="none", heading="runin", callout="inline",
        table="ruled", definition="runin",
        body_font="sans", head_font="sans",
        body_size=9.8, body_leading=13.6,
        margin_x=1.9, margin_top=1.5,
        colour="quiet",
        contents=False,
    ),
    # The hand-drawn notebook look — see notebook_grid's own docstring.
    # cover="none" and contents=False on purpose: the grid page itself
    # opens the document (a header box, then the colour boxes), there is
    # no separate glossy title page in front of it, matching the
    # reference photo exactly (one sheet, not a cover plus a body).
    "playful": LectureTemplate(
        id="playful",
        name="Яркий блокнот",
        description="Разноцветные карточки-ленты на бумаге в линейку: цель, слова, "
                    "формулы, вывод — всё на одном листе, как в тетради.",
        cover="none", heading="runin", callout="card",
        table="filled", definition="cards",
        body_font="sans", head_font="sans",
        body_size=9.6, body_leading=13.2,
        margin_x=1.6, margin_top=1.3,
        colour="full",
        contents=False,
        notebook_grid=True,
    ),
    # A university handout: centred title page, roman-numeral small-caps
    # headings, ruled tables, definitions run into the paragraph. Nothing
    # is filled — the structure is carried entirely by typography, which
    # is why it prints well in black and white.
    "akademik": LectureTemplate(
        id="akademik",
        name="Академический",
        description="Классическая печатная лекция: титульный лист, засечный шрифт, "
                    "разделы римскими цифрами, тонкие линии вместо заливок.",
        cover="classic", heading="smallcaps", callout="rule",
        table="ruled", definition="runin",
        body_font="serif", head_font="serif",
        body_size=10.6, body_leading=15.4,
        margin_x=2.3, margin_top=2.0,
        colour="quiet",
    ),
    # The one that looks like a modern textbook spread: the cover is split
    # by a full-height accent panel, every section opens with an oversized
    # ghost numeral, and the callouts are filled cards.
    "kitob": LectureTemplate(
        id="kitob",
        name="Современный",
        description="Обложка с цветной панелью, крупные номера разделов, "
                    "определения карточками, заметные блоки «Важно» и «Пример».",
        cover="split", heading="ghost", callout="card",
        table="filled", definition="cards",
        body_font="sans", head_font="sans",
        body_size=10.2, body_leading=15.0,
        margin_x=2.0, margin_top=1.7,
        colour="full",
    ),
    # Editorial: a banner cover, reversed-out section bands, key ideas set
    # as pull quotes. Serif headings over a sans body.
    "jurnal": LectureTemplate(
        id="jurnal",
        name="Журнальный",
        description="Редакционный стиль: широкий баннер на обложке, разделы на "
                    "цветной плашке, ключевые мысли — крупными цитатами.",
        cover="banner", heading="band", callout="outline",
        table="editorial", definition="quote",
        body_font="sans", head_font="serif",
        body_size=10.4, body_leading=15.6,
        margin_x=2.1, margin_top=1.8,
        colour="full",
    ),
    # A sheet to work on: a framed cover with fields to fill in, numbered
    # square headings, dashed callouts, ruled answer space in the
    # self-check. Set larger, because it is read and written on at a desk.
    "praktikum": LectureTemplate(
        id="praktikum",
        name="Практикум",
        description="Рабочий лист: рамка и поля для имени на обложке, "
                    "нумерованные квадраты разделов, место для записей в самопроверке.",
        cover="worksheet", heading="boxed", callout="dashed",
        table="grid", definition="framed",
        body_font="sans", head_font="sans",
        body_size=11.0, body_leading=16.4,
        margin_x=2.2, margin_top=1.9,
        colour="full",
        contents=False,
    ),
}

DEFAULT_TEMPLATE_ID = "planspekt"


def get_lecture_template(template_id: str | None) -> LectureTemplate:
    """The template for `template_id`, falling back to the default.

    Lectures made before this registry existed carry a konspekt template
    id — almost always "zamonaviy", which both clients hardcoded because
    a лекция had no picker at all. None of those ids name a design here
    (the modern-textbook one is "kitob" precisely so that "zamonaviy"
    stays free), so every one of them lands on the default: the concise
    план-конспект. That is the format that was asked for, and it is what
    a teacher opening an old lecture should get."""
    return TEMPLATES.get(str(template_id or ""), TEMPLATES[DEFAULT_TEMPLATE_ID])
