
from __future__ import annotations

from dataclasses import dataclass, field, replace


_TAJIK_SAFE = {"Arial", "Times New Roman", "Tahoma", "Segoe UI"}
_TAJIK_FALLBACK = {
    "Comic Sans MS": "Segoe UI",
    "Georgia": "Times New Roman",
    "Cambria": "Times New Roman",
    "Consolas": "Arial",
}


def safe_font(font_name: str, language: str | None) -> str:
    if str(language or "").strip().lower() not in ("таджикский", "tajik", "tg", "тоҷикӣ"):
        return font_name
    if font_name in _TAJIK_SAFE:
        return font_name
    return _TAJIK_FALLBACK.get(font_name, "Arial")




@dataclass(frozen=True)
class SubjectTemplate:

    id: str
    label_ru: str

    accent: str
    support: str
    bg: str = "#FFFFFF"
    ink: str = "#1E2937"
    muted: str = "#5B6472"

    title_font: str = "Arial"
    body_font: str = "Arial"
    title_caps: bool = False
    title_pt: int = 27
    cover_title_pt: int = 46

    header: str = "rule"
    card: str = "rounded"
    marker: str = "number"
    decor: str = "none"
    cover: str = "standard"

    prop_color: str = "#F59E0B"

    image_style: str = "diagram"
    image_qualifiers: tuple[str, ...] = ("educational diagram",)
    topic_categories: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = ()

    pastel: bool = False
    spiral: bool = False
    badge: bool = True

    def as_deck_theme(self) -> dict:
        return {
            "bg": self.bg,
            "ink": self.ink,
            "muted": self.muted,
            "title_font": self.title_font,
            "body_font": self.body_font,
            "title_caps": self.title_caps,
            "header": self.header,
            "cards": self.card != "none",
            "badge": self.badge,
            "pastel": self.pastel,
            "spiral": self.spiral,
            "subject_template": self.id,
            "accent": self.accent,
            "support": self.support,
            "card": self.card,
            "marker": self.marker,
            "decor": self.decor,
            "cover": self.cover,
            "title_pt": self.title_pt,
            "cover_title_pt": self.cover_title_pt,
            "prop_color": self.prop_color,
            "image_style": self.image_style,
            "image_qualifiers": self.image_qualifiers,
        }



MATHEMATICS = SubjectTemplate(
    id="mathematics",
    label_ru="Математика",
    accent="#4A3AA7",
    support="#C7D2FE",
    bg="#FFFFFF",
    ink="#16192B",
    muted="#5A6178",
    title_font="Arial",
    body_font="Arial",
    header="index",
    card="sharp",
    marker="square",
    decor="grid",
    cover="axis",
    image_style="diagram",
    image_qualifiers=("labeled mathematical diagram", "educational"),
    topic_categories=(
        (("уравнен", "equation", "квадратн", "корн"), ("graph of the equation", "plotted")),
        (("функц", "график", "function", "graph"), ("function graph plotted axes",)),
        (("процент", "дроб", "fraction", "percent"), ("fraction percentage visual model",)),
        (("статистик", "вероятн", "probability"), ("statistics chart diagram",)),
    ),
)

ALGEBRA = replace(
    MATHEMATICS,
    id="algebra",
    label_ru="Алгебра",
    accent="#7C3AED",
    support="#DDD6FE",
    decor="symbols",
    cover="axis",
)

GEOMETRY = replace(
    MATHEMATICS,
    id="geometry",
    label_ru="Геометрия",
    accent="#0F9B6E",
    support="#A7F3D0",
    decor="construction",
    cover="construction",
    marker="triangle",
    image_qualifiers=("labeled geometric figure", "geometry diagram"),
)

PHYSICS = SubjectTemplate(
    id="physics",
    prop_color="#1D4ED8",
    label_ru="Физика",
    accent="#EB6834",
    support="#FED7AA",
    bg="#FCFCFD",
    ink="#1B2029",
    muted="#5C6570",
    title_font="Arial",
    body_font="Arial",
    header="measure",
    card="tab",
    marker="chevron",
    decor="wave",
    cover="trajectory",
    image_style="diagram",
    image_qualifiers=("labeled physics diagram", "schematic"),
    topic_categories=(
        (("ток", "цеп", "электр", "circuit", "ohm", "ом"), ("circuit diagram labeled",)),
        (("волн", "звук", "свет", "wave", "optic"), ("wave diagram wavelength",)),
        (("сил", "движен", "механик", "force", "motion"), ("force vector diagram",)),
        (("энерг", "тепл", "energy", "thermo"), ("energy transfer diagram",)),
    ),
)

CHEMISTRY = SubjectTemplate(
    id="chemistry",
    label_ru="Химия",
    accent="#0891B2",
    support="#A5F3FC",
    bg="#FBFDFE",
    ink="#15242B",
    muted="#55666E",
    title_font="Arial",
    body_font="Arial",
    header="hexband",
    card="hex",
    marker="hexagon",
    decor="hexlattice",
    cover="molecule",
    image_style="diagram",
    image_qualifiers=("molecular structure diagram", "chemistry educational"),
    topic_categories=(
        (("реакц", "уравнен", "reaction"), ("chemical reaction equation diagram",)),
        (("таблиц", "менделе", "элемент", "periodic"), ("periodic table element",)),
        (("кислот", "щёлоч", "щелоч", "acid", "base"), ("acid base indicator diagram",)),
        (("органич", "углеводород", "organic"), ("organic molecule structural formula",)),
    ),
)

BIOLOGY = SubjectTemplate(
    id="biology",
    label_ru="Биология",
    accent="#008300",
    support="#BBF7D0",
    bg="#FCFEFC",
    ink="#16261A",
    muted="#55665A",
    title_font="Arial",
    body_font="Arial",
    header="lozenge",
    card="pill",
    marker="dot",
    decor="organic",
    cover="organic",
    image_style="diagram",
    image_qualifiers=("labeled biological diagram", "anatomy educational"),
    topic_categories=(
        (("клетк", "cell", "мембран", "ядро"), ("cell structure labeled organelles",)),
        (("человек", "орган", "сердц", "anatomy", "heart", "скелет"),
         ("human anatomy labeled diagram",)),
        (("растен", "фотосинтез", "plant", "лист"), ("plant structure labeled diagram",)),
        (("днк", "ген", "наследств", "dna", "genetic"), ("dna genetics diagram",)),
        (("животн", "animal", "птиц", "насеком"), ("animal anatomy labeled",)),
        (("экосистем", "среда", "ecosystem"), ("ecosystem food web diagram",)),
    ),
)

GEOGRAPHY = SubjectTemplate(
    id="geography",
    prop_color="#0F766E",
    label_ru="География",
    accent="#A3702D",
    support="#FDE68A",
    bg="#FDFCF9",
    ink="#26201A",
    muted="#6B5F50",
    title_font="Arial",
    body_font="Arial",
    header="smallcaps",
    card="legend",
    marker="pin",
    decor="contour",
    cover="globe",
    image_style="map",
    image_qualifiers=("map", "geographic educational map"),
    topic_categories=(
        (("климат", "пояс", "climate"), ("climate zones world map",)),
        (("рельеф", "гор", "равнин", "relief", "mountain"), ("relief topographic map",)),
        (("населен", "город", "population"), ("population density map",)),
        (("река", "озер", "океан", "river", "ocean"), ("hydrography river map",)),
        (("матери", "континент", "continent"), ("continent political map",)),
    ),
)

HISTORY = SubjectTemplate(
    id="history",
    prop_color="#0E7490",
    label_ru="История",
    accent="#8A2635",
    support="#E7D3B5",
    bg="#FDFBF6",
    ink="#241B17",
    muted="#6A5A50",
    title_font="Georgia",
    body_font="Georgia",
    title_pt=25,
    cover_title_pt=42,
    header="masthead",
    card="plaque",
    marker="roman",
    decor="timeline",
    cover="banner",
    image_style="photo",
    image_qualifiers=("historical", "museum artifact photograph"),
    topic_categories=(
        (("войн", "битв", "war", "battle"), ("historical map of the campaign",)),
        (("государств", "империи", "империя", "царств", "empire", "kingdom"),
         ("historical map empire borders",)),
        (("культур", "искусств", "архитект", "culture", "architecture"),
         ("historical architecture photograph",)),
        (("документ", "закон", "реформ", "document", "law"), ("historical document manuscript",)),
    ),
)

HISTORY_WORLD = replace(
    HISTORY,
    id="history_world",
    label_ru="Всемирная история",
    accent="#B5502E",
    support="#EED9BE",
)

INFORMATICS = SubjectTemplate(
    id="informatics",
    label_ru="Информатика",
    accent="#2A78D6",
    support="#BFDBFE",
    bg="#FBFCFE",
    ink="#151C26",
    muted="#56616F",
    title_font="Arial",
    body_font="Arial",
    header="prompt",
    card="window",
    marker="bracket",
    decor="dots",
    cover="terminal",
    image_style="diagram",
    image_qualifiers=("flowchart diagram", "computer science educational"),
    topic_categories=(
        (("алгоритм", "блок-схем", "algorithm", "flowchart"), ("algorithm flowchart",)),
        (("сет", "интернет", "network"), ("computer network topology diagram",)),
        (("баз", "данн", "database", "sql"), ("database schema diagram",)),
        (("программ", "код", "python", "код", "programming"), ("source code editor screenshot",)),
    ),
)

RUSSIAN = SubjectTemplate(
    id="russian",
    prop_color="#1D4ED8",
    label_ru="Русский язык",
    accent="#C62839",
    support="#FBCFD3",
    bg="#FFFDFD",
    ink="#231619",
    muted="#655257",
    title_font="Georgia",
    body_font="Arial",
    title_pt=26,
    header="initial",
    card="quote",
    marker="dash",
    decor="ruled",
    cover="page",
    image_style="illustration",
    image_qualifiers=("grammar chart", "language education illustration"),
    topic_categories=(
        (("орфограф", "правопис", "spelling"), ("spelling rule chart",)),
        (("часть реч", "существит", "глагол", "прилагат"), ("parts of speech chart",)),
        (("синтакс", "предложен", "syntax", "sentence"), ("sentence diagram syntax",)),
        (("лексик", "словар", "vocabulary"), ("vocabulary chart illustrated",)),
    ),
)

LITERATURE = SubjectTemplate(
    id="literature",
    label_ru="Литература",
    accent="#6B3FA0",
    support="#E9D5FF",
    bg="#FCFAFF",
    ink="#20182B",
    muted="#5E5470",
    title_font="Georgia",
    body_font="Georgia",
    title_pt=25,
    cover_title_pt=42,
    header="ornamental",
    card="framed",
    marker="diamond",
    decor="ornament",
    cover="frontispiece",
    image_style="portrait",
    image_qualifiers=("portrait", "literary illustration"),
    topic_categories=(
        (("поэз", "стих", "газал", "poetry", "poem"), ("illuminated manuscript poetry",)),
        (("роман", "повест", "проза", "novel"), ("book illustration novel scene",)),
        (("биограф", "жизн", "biography"), ("author portrait",)),
    ),
)

ENGLISH = SubjectTemplate(
    id="english",
    label_ru="Английский язык",
    accent="#1D5FC2",
    support="#BFDBFE",
    bg="#FCFDFF",
    ink="#161E2B",
    muted="#556376",
    title_font="Arial",
    body_font="Arial",
    header="rule",
    card="bubble",
    marker="dot",
    decor="letters",
    cover="bubble",
    image_style="illustration",
    image_qualifiers=("english language learning illustration", "educational"),
    topic_categories=(
        (("tense", "время", "grammar", "граммат"), ("english grammar tense chart",)),
        (("vocabulary", "словар", "лексик"), ("illustrated vocabulary flashcards",)),
        (("dialogue", "диалог", "speaking"), ("conversation dialogue illustration",)),
    ),
)

TAJIK = SubjectTemplate(
    id="tajik",
    label_ru="Таджикский язык",
    accent="#0E7C86",
    support="#99F6E4",
    bg="#FCFEFE",
    ink="#132326",
    muted="#4F6467",
    title_font="Arial",
    body_font="Arial",
    header="smallcaps",
    card="ornate",
    marker="star",
    decor="girih",
    cover="ornament",
    image_style="illustration",
    image_qualifiers=("Tajik", "educational illustration"),
    topic_categories=(
        (("грамматик", "grammar", "сарф", "наҳв"), ("grammar chart",)),
        (("адабиёт", "литератур", "шеър"), ("manuscript illustration",)),
        (("таърих", "фарҳанг", "культур"), ("Tajikistan culture photograph",)),
    ),
)

SOCIAL_STUDIES = SubjectTemplate(
    id="social_studies",
    label_ru="Обществознание",
    accent="#4338CA",
    support="#C7D2FE",
    bg="#FCFCFE",
    ink="#181B2A",
    muted="#575E75",
    title_font="Arial",
    body_font="Arial",
    header="band",
    card="rounded",
    marker="circle",
    decor="network",
    cover="nodes",
    image_style="infographic",
    image_qualifiers=("infographic chart", "social studies educational"),
    topic_categories=(
        (("прав", "закон", "конституц", "law", "right"), ("legal document infographic",)),
        (("эконом", "рынок", "economy", "market"), ("economics chart infographic",)),
        (("общест", "социал", "society", "social"), ("society structure diagram",)),
    ),
)

ECOLOGY = SubjectTemplate(
    id="ecology",
    label_ru="Экология",
    accent="#0E9F6E",
    support="#A7F3D0",
    bg="#FBFEFB",
    ink="#132520",
    muted="#4F6660",
    title_font="Arial",
    body_font="Arial",
    header="lozenge",
    card="pill",
    marker="leaf",
    decor="cycle",
    cover="cycle",
    image_style="diagram",
    image_qualifiers=("ecosystem diagram", "environmental educational"),
    topic_categories=(
        (("загрязн", "отход", "pollution", "waste"), ("pollution environmental photograph",)),
        (("climate", "климат", "потеплен"), ("climate change infographic",)),
        (("вид", "заповед", "species", "biodiversity"), ("biodiversity species illustration",)),
    ),
)

PRIMARY_SCHOOL = SubjectTemplate(
    id="primary_school",
    prop_color="#2563EB",
    label_ru="Начальные классы",
    accent="#E4572E",
    support="#FFD166",
    bg="#FFFDF7",
    ink="#2D2A4A",
    muted="#6B638C",
    title_font="Comic Sans MS",
    body_font="Arial",
    cover_title_pt=44,
    header="rule",
    card="pastel",
    marker="star",
    decor="none",
    cover="notebook",
    pastel=True,
    spiral=True,
    image_style="illustration",
    image_qualifiers=("simple illustration for children", "educational"),
)



TEMPLATES: dict[str, SubjectTemplate] = {
    t.id: t
    for t in (
        MATHEMATICS, ALGEBRA, GEOMETRY, PHYSICS, CHEMISTRY, BIOLOGY,
        GEOGRAPHY, HISTORY, HISTORY_WORLD, INFORMATICS, RUSSIAN,
        LITERATURE, ENGLISH, TAJIK, SOCIAL_STUDIES, ECOLOGY,
        PRIMARY_SCHOOL,
    )
}

SUBJECT_TO_TEMPLATE: dict[str, str] = {
    "Математика": "mathematics",
    "Алгебра": "algebra",
    "Геометрия": "geometry",
    "Физика": "physics",
    "Химия": "chemistry",
    "Биология": "biology",
    "География": "geography",
    "История Таджикистана": "history",
    "Всемирная история": "history_world",
    "Информатика": "informatics",
    "Русский язык": "russian",
    "Таджикская литература": "literature",
    "Английский язык": "english",
    "Таджикский язык": "tajik",
    "Обществознание": "social_studies",
    "Экология": "ecology",
    "Начальные классы": "primary_school",
}

_FUZZY: tuple[tuple[tuple[str, ...], str], ...] = (
    (("всемирн", "world history", "жаҳон"), "history_world"),
    (("тадж", "тоҷик", "tajik"), "tajik"),
    (("литератур", "адабиёт", "literature"), "literature"),
    (("англ", "english", "инглис"), "english"),
    (("русск", "russian"), "russian"),
    (("геометр", "geometry"), "geometry"),
    (("алгебр", "algebra"), "algebra"),
    (("математ", "math", "риёз"), "mathematics"),
    (("физик", "physic"), "physics"),
    (("хими", "chemist", "кимиё"), "chemistry"),
    (("биолог", "biolog"), "biology"),
    (("эколог", "ecolog", "окружающ"), "ecology"),
    (("географ", "geograph", "ҷуғроф"), "geography"),
    (("истори", "histor", "таърих"), "history"),
    (("информат", "computer", "икт"), "informatics"),
    (("общество", "социал", "social"), "social_studies"),
    (("начальн", "primary", "ибтидо"), "primary_school"),
)

DEFAULT = SubjectTemplate(
    id="general",
    label_ru="Общий",
    accent="#3B82F6",
    support="#DBEAFE",
    header="rule",
    card="rounded",
    marker="number",
    decor="none",
    cover="standard",
    image_style="diagram",
    image_qualifiers=("educational diagram",),
)
TEMPLATES[DEFAULT.id] = DEFAULT


def resolve(subject: str | None, grade: str | None = None) -> SubjectTemplate:
    name = str(subject or "").strip()

    if name:
        exact = SUBJECT_TO_TEMPLATE.get(name)
        if exact:
            return TEMPLATES[exact]

        low = name.lower()
        for needles, template_id in _FUZZY:
            if any(n in low for n in needles):
                return TEMPLATES[template_id]

    return PRIMARY_SCHOOL if _is_primary(grade) else DEFAULT


def _is_primary(grade: str | None) -> bool:
    import re

    m = re.search(r"\d+", str(grade or ""))
    if not m:
        return False
    try:
        return 1 <= int(m.group()) <= 4
    except ValueError:
        return False


def deck_theme_for(subject: str | None, grade: str | None = None,
                   language: str | None = None) -> dict:
    tpl = resolve(subject, grade)
    theme = tpl.as_deck_theme()
    theme["title_font"] = safe_font(theme["title_font"], language)
    theme["body_font"] = safe_font(theme["body_font"], language)
    return theme
