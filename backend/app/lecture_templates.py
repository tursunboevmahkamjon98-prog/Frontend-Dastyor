
from dataclasses import dataclass


@dataclass(frozen=True)
class LectureTemplate:
    id: str
    name: str
    description: str

    cover: str
    heading: str
    callout: str
    table: str
    definition: str

    body_font: str
    head_font: str

    body_size: float
    body_leading: float

    margin_x: float
    margin_top: float

    colour: str

    contents: bool = True

    notebook_grid: bool = False


TEMPLATES: dict[str, LectureTemplate] = {
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
    return TEMPLATES.get(str(template_id or ""), TEMPLATES[DEFAULT_TEMPLATE_ID])
