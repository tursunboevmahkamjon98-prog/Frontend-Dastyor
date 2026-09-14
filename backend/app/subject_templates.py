# -*- coding: utf-8 -*-
"""Per-subject presentation design system.

Why this exists
---------------
Until now a deck's look came from ONE of six generic themes the teacher
picked in the wizard (export_builder._DECK_THEMES), and the only thing
the subject contributed was an accent colour and a clipart on the cover
(subject_theme.py). The result: a Biology deck and a History deck were
the same deck in two colours.

This module makes the SUBJECT the primary design decision. Each subject
gets its own palette, typography, header treatment, card silhouette,
bullet marker, decorative motif, cover composition and image-search
character — the axes that actually make two decks look like different
products rather than the same template recoloured.

Contract with the renderer
--------------------------
`as_deck_theme()` returns a dict that is a strict SUPERSET of an
export_builder._DECK_THEMES entry. Every key the existing renderer reads
("bg", "ink", "muted", "title_font", "body_font", "title_caps", "header",
"cards", "badge", "pastel", "spiral") is present with the same meaning
and the same types, so every code path in build_presentation_pptx keeps
working unchanged. The new keys are additive and read with .get() on the
renderer side, which is what lets the six legacy themes keep working
side by side with these.

Colours are plain hex strings here on purpose: this module must stay
importable without python-pptx so the query builder, the tests and any
future preview generator can use it. export_builder converts to
RGBColor at the boundary.

Subject keys
------------
The keys are the same fixed RUSSIAN subject names every other lookup in
this project uses (frontend/src/lib/material-types.ts's SUBJECTS,
ai_service._SUBJECT_KONSPEKT_PROMPTS, subject_theme._SUBJECT_ACCENTS).
`resolve()` maps each of them onto a template, including the several
subjects that legitimately share a family (the three maths courses, the
two history courses) while still differing in accent and motif.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


# ── Fonts ────────────────────────────────────────────────────────────────
#
# Tajik is a first-class language for this product and it needs Cyrillic
# Extended letters that decorative fonts routinely omit:
#
#     ӣ U+04E3   ҷ U+04B7   ҳ U+04B3   қ U+049B   ӯ U+04EF   ғ U+0493
#
# A missing glyph does not fall back gracefully in PowerPoint — it shows
# a box, or silently substitutes a different face mid-word. Arial and
# Times New Roman ship those ranges on every Windows/Office install this
# product targets; Comic Sans MS and Georgia do NOT reliably.
#
# So decorative faces are allowed, but only through safe_font(), which
# swaps them out when the deck is actually in Tajik. A Russian or English
# deck keeps the designed face.
_TAJIK_SAFE = {"Arial", "Times New Roman", "Tahoma", "Segoe UI"}
_TAJIK_FALLBACK = {
    "Comic Sans MS": "Segoe UI",
    "Georgia": "Times New Roman",
    "Cambria": "Times New Roman",
    "Consolas": "Arial",
}


def safe_font(font_name: str, language: str | None) -> str:
    """The font to actually write into the PPTX for this deck's language.

    Only Tajik is restricted — it is the language whose letters the
    decorative faces miss. Everything else keeps the designed font."""
    if str(language or "").strip().lower() not in ("таджикский", "tajik", "tg", "тоҷикӣ"):
        return font_name
    if font_name in _TAJIK_SAFE:
        return font_name
    return _TAJIK_FALLBACK.get(font_name, "Arial")


# ── The token set ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SubjectTemplate:
    """Everything that makes one subject's deck look like that subject.

    Grouped the way a designer would hand it over: colour, type, the
    structural choices, then how pictures should behave."""

    id: str
    label_ru: str

    # ── colour ──
    # accent drives every structural element (rules, markers, header);
    # support is a SECOND hue used only by the decorative motif, so the
    # decoration reads as part of the design rather than more of the same
    # accent. Two hues is the cap on purpose — the brief explicitly
    # rejects "слишком большое количество цветов".
    accent: str
    support: str
    bg: str = "#FFFFFF"
    ink: str = "#1E2937"
    muted: str = "#5B6472"

    # ── typography ──
    title_font: str = "Arial"
    body_font: str = "Arial"
    title_caps: bool = False
    # Content-slide title size. The renderer's own 24/27 default is fine
    # for most, but a serif face at the same pt reads smaller and a
    # condensed subject line wants more room.
    title_pt: int = 27
    cover_title_pt: int = 46

    # ── structure ──
    # header: how a content slide announces itself. Values the renderer
    # already understands ("rule", "underline", "band", "smallcaps",
    # "plain") plus the ones added for this system.
    header: str = "rule"
    # card: the silhouette of a bullet card. "none" keeps the legacy
    # plain typographic lines (klassik/minimal's restraint).
    card: str = "rounded"
    # marker: what sits beside/above a bullet.
    marker: str = "number"
    # decor: which motif slide_decor draws. "none" = a clean deck.
    decor: str = "none"
    # cover: which cover composition build_presentation_pptx uses.
    cover: str = "standard"

    # The colour the character's prop is drawn in. It must CONTRAST with
    # `accent`, which is what the figure itself is drawn in — the first
    # cut reused `support`, and a pale-green magnifier held by a green
    # figure on a white slide was invisible. A second hue, chosen per
    # subject so it never clashes with the accent it sits next to.
    prop_color: str = "#F59E0B"

    # ── imagery ──
    # What KIND of picture suits this subject, and the words appended to
    # every image search so Commons returns a teaching figure rather than
    # a decorative photo. See image_query.build_query.
    image_style: str = "diagram"
    image_qualifiers: tuple[str, ...] = ("educational diagram",)
    # Topic-level adaptation (the brief's SUBJECT -> TOPIC CATEGORY ->
    # SLIDE TYPE -> DESIGN layer). Each entry maps trigger words found in
    # the lesson topic to extra search qualifiers for that branch of the
    # subject — a Biology deck about the cell and one about ecosystems
    # should not fetch the same character of picture.
    topic_categories: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = ()

    # ── legacy renderer switches ──
    # Kept so as_deck_theme() can express the two existing special looks
    # (the notebook/spiral paper and the rotating pastel cards) without
    # the renderer needing to know about subject templates at all.
    pastel: bool = False
    spiral: bool = False
    badge: bool = True

    def as_deck_theme(self) -> dict:
        """A dict shaped exactly like an export_builder._DECK_THEMES entry
        (plus the new keys), with colours still as hex — the renderer
        converts. Keeping the legacy key names and meanings is what makes
        this drop into build_presentation_pptx without touching the parts
        of it that already work."""
        return {
            # legacy contract
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
            # subject-design additions
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


# ── The fourteen templates ───────────────────────────────────────────────
#
# Each one differs on SEVERAL axes, not just colour: a different header
# treatment, a different card silhouette, a different marker, a different
# motif and a different cover composition. That is what stops them from
# being one template in fourteen colours.

MATHEMATICS = SubjectTemplate(
    id="mathematics",
    label_ru="Математика",
    # Indigo — the accent subject_theme already assigns to Математика, so
    # a maths konspekt and a maths deck stay the same colour.
    accent="#4A3AA7",
    support="#C7D2FE",
    bg="#FFFFFF",
    ink="#16192B",
    muted="#5A6178",
    title_font="Arial",
    body_font="Arial",
    # Squared paper, a hard left rule, numerals in squares: the deck
    # should read as precise and constructed rather than friendly.
    header="index",          # "01 ―" index mark before the title
    card="sharp",            # square corners + a solid left rule
    marker="square",
    decor="grid",            # faint graph-paper field
    cover="axis",            # a quiet coordinate cross behind the title
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
    # Algebra is symbolic where geometry is constructed — the motif says
    # so: no construction lines, a field of faint operators instead.
    decor="symbols",
    cover="axis",
)

GEOMETRY = replace(
    MATHEMATICS,
    id="geometry",
    label_ru="Геометрия",
    accent="#0F9B6E",
    support="#A7F3D0",
    # Compass arcs and construction lines — the drawing-board look, which
    # is genuinely a different motif from algebra's symbol field rather
    # than the same grid in another colour.
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
    # A long measurement hairline under the title, tab-shaped cards and
    # chevron markers: direction and magnitude, the two things physics
    # notation is always about.
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
    # Hexagons everywhere a shape is needed — the one motif that reads as
    # "chemistry" without a single beaker clipart.
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
    # Nothing in biology is square. Fully rounded cards, a lozenge header
    # mark, soft organic shapes in the margin.
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
    # Map furniture: small-caps title like a chart label, a dashed legend
    # card, a pin marker and contour lines in the margin.
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
    # A serif masthead over a double rule, plaque-shaped cards, roman
    # numerals, and a dated timeline running along the foot of the slide.
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
    # Editor furniture rather than doodles: a prompt mark before the
    # title, window-chrome dots on the cover, a dotted field in the
    # margin, bracketed indices as markers.
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
    # The page, not the poster: a hanging initial before the title, ruled
    # writing lines in the margin, a quote bar instead of a badge.
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
    # A centred serif title with an ornamental rule under it, framed
    # page-like cards, diamond markers — the furniture of a printed book.
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
    # Conversation, not grammar tables: speech-bubble cards and a light
    # strip of letterforms.
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
    # A geometric ornamental band — the one motif in this file drawn from
    # the region's own visual tradition rather than a school-supply
    # cliché. Built from rotated squares and diamonds, no asset needed.
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
    # Society as a graph: connected nodes in the margin, a solid header
    # band, circular markers.
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
    # Everything in ecology is a loop, so the motif is one: a ring of
    # arrows in the margin, and rounded cards that echo it.
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
    title_font="Comic Sans MS",   # swapped by safe_font() for Tajik decks
    body_font="Arial",
    cover_title_pt=44,
    # The one place the existing notebook machinery genuinely belongs:
    # ruled paper, a spiral binding and rotating pastel cards. Reused
    # rather than rebuilt — see export_builder._pptx_notebook_lines.
    header="rule",
    card="pastel",
    marker="star",
    decor="none",       # the paper itself is the decoration here
    cover="notebook",
    pastel=True,
    spiral=True,
    image_style="illustration",
    image_qualifiers=("simple illustration for children", "educational"),
)


# ── Registry and resolution ──────────────────────────────────────────────

TEMPLATES: dict[str, SubjectTemplate] = {
    t.id: t
    for t in (
        MATHEMATICS, ALGEBRA, GEOMETRY, PHYSICS, CHEMISTRY, BIOLOGY,
        GEOGRAPHY, HISTORY, HISTORY_WORLD, INFORMATICS, RUSSIAN,
        LITERATURE, ENGLISH, TAJIK, SOCIAL_STUDIES, ECOLOGY,
        PRIMARY_SCHOOL,
    )
}

# The project's fixed Russian subject names -> template id. These are the
# exact strings frontend/src/lib/material-types.ts's SUBJECTS ships, so a
# subject chosen in the wizard always lands on a real template.
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

# A free-typed subject still deserves the right design, so the exact-name
# table above is backed by substring matching. Ordered longest/most
# specific first — "Таджикская литература" must not be caught by the
# "литератур" rule before the "таджикск" one, and "История" must not
# swallow "Всемирная история".
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

# What a deck gets when the subject is empty or matches nothing at all. A
# neutral, clean design rather than an arbitrary subject's look.
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
    """The template a deck should be built with.

    The SUBJECT decides — a biology lesson gets the biology design whether
    it is taught in grade 3 or grade 11. `grade` is only a fallback: a
    deck whose subject is blank or unrecognised, for grades 1-4, is a
    primary-school lesson and gets the friendly ruled paper instead of the
    neutral default.

    (An earlier cut of this had grade override the subject outright. That
    is wrong: it silently threw away the subject design a teacher had
    every reason to expect, which is exactly the "fake choice" the brief
    rules out.)"""
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
    """True for grades 1-4. `grade` arrives in several shapes ("3",
    "3 класс", "3-синф"), so the first run of digits is what decides."""
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
    """The renderer-facing entry point: resolve the subject, then apply
    the Tajik font guard so no deck is ever written with a face that
    cannot draw ӣ/ҷ/ҳ/қ/ӯ/ғ."""
    tpl = resolve(subject, grade)
    theme = tpl.as_deck_theme()
    theme["title_font"] = safe_font(theme["title_font"], language)
    theme["body_font"] = safe_font(theme["body_font"], language)
    return theme
