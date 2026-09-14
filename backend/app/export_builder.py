import hashlib
import io
import math
import os
import re
import platform as _platform
from PIL import Image as PILImage
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.text import PP_ALIGN
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (SimpleDocTemplate, Paragraph as _RLParagraph,
                                Spacer, Table, TableStyle, KeepTogether)
from reportlab.platypus.flowables import Flowable as _RLFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader


# ── powers in every PDF, not just the plan sheet ─────────────────────────
# _math_inline below sets a formula as a drawn image, and only the nakscha
# plan layout calls it. The other five templates build their paragraphs
# straight from the model's text, so "S = a^2" printed with the 2 on the
# baseline and the dollar signs still in the sentence.
#
# ReportLab can set a real superscript in flowing text (<super>), and the
# great majority of school formulas are exactly that — a power or an index
# on plain text. So Paragraph is wrapped once here, and every paragraph in
# every export gets its powers typeset, whatever template built it. A
# formula that needs more than a raised digit — a stacked fraction, a
# radical — still becomes a drawn image, the same one the plan sheet uses.


def _xml_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


_RL_IMG_TAG = re.compile(r"<img\b[^>]*/?>", re.IGNORECASE)
_RL_STYLE_TAG = re.compile(r"</?(?:b|i|super|sub|font|para)\b[^>]*>", re.IGNORECASE)


def _strip_reportlab_markup(text: str) -> str:
    """The worst-case safety net under Paragraph's exception fallback
    below: even when the CALLER already baked ReportLab markup into the
    text it hands to Paragraph (several sites pre-run _math_inline before
    ever constructing one — the "important_notes"/plan-sheet panels, for
    two), a parse failure must never show that markup as literal text.
    Confirmed live: a teacher saw a whole paragraph print as
    "<b><i>...</i></b>" and "<img src="C:\\Users\\...\\uploads\\math\\
    ...png".../>" — a local server filesystem path, visible on the page.
    An <img> tag has no plain-text form worth keeping (there is no way to
    "un-render" a formula image back to readable text), so it is dropped
    outright; a <b>/<i>/<super> tag's own text is real content and is
    kept, just unstyled."""
    text = _RL_IMG_TAG.sub("", str(text or ""))
    text = _RL_STYLE_TAG.sub("", text)
    return text


def _math_markup(text, size: float = 11, bg: str | None = None) -> str:
    """Every $...$ span replaced by ReportLab markup: a raised <super> for
    a power or index, a drawn formula image for anything larger.

    bg defaults to None — a transparent plate. The wrapper below is
    applied to every paragraph in the document and cannot know what
    colour the cell behind it is painted, so an opaque white background
    showed up as a white patch around every fraction that landed inside a
    tinted card."""
    raw = _normalize_math(text)
    if "$" not in raw:
        return raw

    def repl(m):
        from app.math_render import script_segments, is_literal_operator
        latex = m.group(1)
        # "$**$" is Python's power operator being named, not a formula —
        # typesetting it turns it into "··" and the line loses its point.
        if is_literal_operator(latex):
            return _xml_escape(latex)
        try:
            segments = script_segments(latex)
        except Exception:
            segments = None
        if segments:
            out = []
            for seg_text, kind in segments:
                esc = _xml_escape(seg_text)
                if kind == "sup":
                    out.append(f"<super>{esc}</super>")
                elif kind == "sub":
                    out.append(f"<sub>{esc}</sub>")
                else:
                    out.append(esc)
            return "".join(out)
        got = _math_png(latex, size, bg)
        if not got:
            # Unrenderable: the expression without its dollars beats
            # "$x^2$" printed on the page.
            return _xml_escape(latex)
        path, w, asc, desc = got
        return (f'<img src="{path}" width="{w + 2 * _MATH_PAD:.1f}" '
                f'height="{asc + desc + 2 * _MATH_PAD:.1f}" '
                f'valign="{-(desc + _MATH_PAD):.1f}"/>')
    return _MATH_SPAN.sub(repl, raw)


class Paragraph(_RLParagraph):
    """ReportLab's Paragraph with the mathematics typeset first.

    Wrapping the class rather than editing four dozen call sites is
    deliberate: the konspekt PDF, the lecture, the test and the curriculum
    all build paragraphs from the same name, and a power must print as a
    power in all of them. Text with no mathematics in it is returned
    untouched, and a paragraph whose markup the rewrite would break still
    renders — the wrapper falls back to the original text."""

    def __init__(self, text, style=None, *args, **kwargs):
        size = 11
        try:
            size = float(getattr(style, "fontSize", 11) or 11)
        except Exception:
            pass
        # A code card is printed verbatim in the monospaced face: "^" is
        # xor there, not a power, and "a ^ 2" must stay exactly as the
        # pupil would type it.
        is_code = getattr(style, "fontName", None) == CODE_FONT
        # Kept separate from the markup below on purpose: when ReportLab's
        # own XML parser rejects the markup (confirmed live — a teacher
        # saw a whole paragraph print as literal "<b><i>...</b></i>" and
        # "<img src="C:\...\uploads\math\...png".../>" text, local
        # filesystem path and all), the fallback must never escape the
        # markup-laden version — that IS what leaked those raw tags and
        # disk paths onto the page. `original_text` can still carry markup
        # of its own though: several call sites run _math_inline on a
        # value before ever handing it to Paragraph (the "important_notes"
        # panel, the plan-sheet "runin" sections), so the fallback below
        # also runs it through _strip_reportlab_markup rather than trusting
        # "original" to mean "plain".
        original_text = text
        marked_up = text
        try:
            if not is_code:
                marked_up = _math_markup(text, size)
        except Exception:
            marked_up = text
        try:
            super().__init__(marked_up, style, *args, **kwargs)
        except Exception as e:
            # Logged rather than swallowed — this exception is the only
            # signal that a specific piece of AI-generated math broke
            # ReportLab's parser; silently recovering hid every past
            # occurrence of the bug above.
            logger.warning(f"Paragraph markup failed to parse (falling back to plain text): {e}")
            super().__init__(_xml_escape(_strip_reportlab_markup(original_text)), style, *args, **kwargs)

from app.logger import get_logger
from app.subject_theme import get_subject_accent_hex, get_subject_accent_rgb, get_subject_illustration_path
from app import slide_decor, pptx_shapes, slide_layouts, slide_characters
from app.konspekt_templates import get_template

logger = get_logger(__name__)

# See docx_builder.py's identical helper for why this exists: the model
# sometimes prefixes its own "Group N:"/"Гурӯҳи N:" label onto a group_work
# task despite being told not to, which would otherwise duplicate/collide
# with this section's own numbered bullet.
_GROUP_LABEL_RE = re.compile(
    r"^\s*(?:Группа|Гурӯҳи?|Group|Guruh)\s*\d+\s*[:.\-—]\s*", re.IGNORECASE
)


def _strip_group_label(task: str) -> str:
    return _GROUP_LABEL_RE.sub("", str(task), count=1)


def _register_unicode_font():
    font_name = 'Arial'
    font_name_bold = 'Arial-Bold'
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name, font_name_bold
    try:
        font_paths = []
        font_bold_paths = []
        if _platform.system() == 'Windows':
            windir = os.environ.get('WINDIR', r'C:\Windows')
            font_paths = [os.path.join(windir, 'Fonts', 'arial.ttf')]
            font_bold_paths = [os.path.join(windir, 'Fonts', 'arialbd.ttf')]
        elif _platform.system() == 'Darwin':
            font_paths = ['/Library/Fonts/Arial.ttf']
            font_bold_paths = ['/Library/Fonts/Arial Bold.ttf']
        else:
            font_paths = ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/TTF/DejaVuSans.ttf']
            font_bold_paths = ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf']

        for path in font_paths:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(font_name, path))
                break

        bold_registered = False
        for path in font_bold_paths:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(font_name_bold, path))
                bold_registered = True
                break

        if not bold_registered:
            font_name_bold = font_name

        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        registerFontFamily(font_name, normal=font_name, bold=font_name_bold)

        return font_name, font_name_bold
    except Exception:
        return 'Helvetica', 'Helvetica-Bold'


FONT_NAME, FONT_NAME_BOLD = _register_unicode_font()


def _register_math_font():
    """Arial (the default PDF font above) is missing glyphs for ∧/∨ (logical
    AND/OR) on this system — they render as tofu boxes even though Word's
    Cambria Math renders them fine. Cambria's regular weight (cambria.ttc)
    does have them — but oddly its own bold file (cambriab.ttf) does not
    (the glyph silently vanishes instead of even showing tofu), confirmed by
    direct testing, so both weights are mapped to the same regular face
    rather than risk that per-font gap. Losing true bold here is a fair
    trade for the symbols actually being correct."""
    name = 'CambriaMath'
    if name in pdfmetrics.getRegisteredFontNames():
        return name, name
    try:
        windir = os.environ.get('WINDIR', r'C:\Windows') if _platform.system() == 'Windows' else None
        if windir:
            regular_path = os.path.join(windir, 'Fonts', 'cambria.ttc')
            if os.path.exists(regular_path):
                pdfmetrics.registerFont(TTFont(name, regular_path))
                return name, name
    except Exception:
        pass
    return FONT_NAME, FONT_NAME_BOLD


MATH_FONT, MATH_FONT_BOLD = _register_math_font()


def _register_code_font():
    """Consolas for code_blocks (see _pdf_code_card) — a real monospaced
    face instead of falling back to the proportional FONT_NAME, which
    would misalign indentation/columns in any multi-line snippet. Same
    registration pattern as _register_math_font: best-effort, silent
    fallback to the main font if Consolas isn't on this machine."""
    name = 'Consolas'
    if name in pdfmetrics.getRegisteredFontNames():
        return name
    try:
        windir = os.environ.get('WINDIR', r'C:\Windows') if _platform.system() == 'Windows' else None
        if windir:
            path = os.path.join(windir, 'Fonts', 'consola.ttf')
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(name, path))
                return name
    except Exception:
        pass
    return FONT_NAME


CODE_FONT = _register_code_font()


# The six letters that separate "works on the developer's Windows laptop"
# from "works on the Ubuntu box it was sold from": Tajik's
# ғ қ ҳ ҷ ӣ ӯ. Cyrillic, but outside the basic range a font can
# cover while still looking complete in Russian.
_TAJIK_PROBE = "ғқҳҷӣӯ"


def verify_pdf_fonts() -> list[str]:
    """Reports what the PDF font cannot draw. Empty list means fine.

    Called at startup (see main.py's lifespan) because the failure it
    catches is invisible from the server's side: on Linux
    _register_unicode_font looks for DejaVuSans.ttf at two absolute
    paths and, finding neither, silently leaves Helvetica in place.
    Helvetica has no Cyrillic at all, so every generated PDF comes out
    as rows of empty boxes — with a 200 response, a plausible file size
    and nothing in the log. A teacher opens it and sees a broken
    product; the server thinks it succeeded.

    Returns strings rather than raising: a missing font must not stop
    the app from booting. It must only stop being silent.
    """
    problems: list[str] = []
    try:
        registered = pdfmetrics.getRegisteredFontNames()
        if FONT_NAME not in registered:
            return [
                f"the PDF font '{FONT_NAME}' was never registered — falling back "
                f"to a built-in face with no Cyrillic. On Linux install "
                f"fonts-dejavu-core."
            ]
        face = pdfmetrics.getFont(FONT_NAME).face
        # charToGlyph maps codepoint -> glyph id; absent, or mapped to 0
        # (.notdef), is the tofu box.
        missing = [c for c in _TAJIK_PROBE
                   if getattr(face, "charToGlyph", {}).get(ord(c), 0) == 0]
        if missing:
            problems.append(
                f"the PDF font '{FONT_NAME}' cannot draw {''.join(missing)} — "
                f"Tajik PDFs will contain empty boxes. Install fonts-dejavu-core."
            )
    except Exception as e:  # noqa: BLE001
        problems.append(f"could not verify the PDF fonts: {e}")
    return problems


def verify_pptx_renderer() -> str | None:
    """None if LibreOffice is present, otherwise why it matters.

    Separate from the font check because this one degrades rather than
    breaks: without soffice the presentation preview falls back to
    build_presentation_pdf, which works but is not the teacher's actual
    deck. Worth one clear line at startup instead of being discovered
    from a screenshot.
    """
    try:
        from app import pptx_pdf
        if pptx_pdf.find_binary() is None:
            return ("LibreOffice was not found — presentation previews will fall "
                    "back to the A4 rendering instead of the real slides. "
                    "Install libreoffice-impress.")
    except Exception as e:  # noqa: BLE001
        return f"could not check for LibreOffice: {e}"
    return None


from pptx.enum.shapes import MSO_SHAPE


# ── PPTX Builder ────────────────────────────────────────────────────────────

# Fallback brand blue (matches the konspekt/curriculum exports' default
# accent, #3B82F6) — used only when a deck has no subject (old data from
# before subject-theming existed, or a custom/unrecognized subject).
# build_presentation_pptx computes its own per-subject accent/dark/soft
# trio via _pptx_accent_shades(get_subject_accent_rgb(...)) instead of
# these constants directly, so a Biology deck and a Physics deck are
# visually distinguishable the same way konspekt exports already are —
# these three stay only as the _add_icon_badge default parameter below.
_ACCENT = RGBColor(0x3B, 0x82, 0xF6)
_ACCENT_DARK = RGBColor(0x1E, 0x3A, 0x8A)
_ACCENT_SOFT = RGBColor(0xDB, 0xEA, 0xFE)
_INK = RGBColor(0x1E, 0x29, 0x37)


def _pptx_accent_shades(rgb: tuple[int, int, int]) -> tuple[RGBColor, RGBColor, RGBColor]:
    """Derives (accent, accent_dark, accent_soft) RGBColor triples from one
    base (r, g, b) — the same darken/lighten math export_builder.py already
    uses for PDF (_pdf_light_tint_hex) and docx_builder.py
    (_light_tint_hex), just producing pptx's RGBColor instead of a hex
    string, so the gradient/badge/chip vocabulary already built for the
    fixed blue works unchanged for any subject's color."""
    r, g, b = rgb
    dark = RGBColor(int(r * 0.55), int(g * 0.55), int(b * 0.55))
    soft = RGBColor(int(r + (255 - r) * 0.88), int(g + (255 - g) * 0.88), int(b + (255 - b) * 0.88))
    return RGBColor(r, g, b), dark, soft
_MUTED = RGBColor(0x6B, 0x72, 0x80)
_HAIRLINE = RGBColor(0xE2, 0xE8, 0xF0)
_TEXT_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_TEXT_SOFT = RGBColor(0xDB, 0xEA, 0xFE)  # near-white with a hint of accent, for text sitting on the gradient

# Rotated per content slide for visual variety — professional-reading marks
# (energy/insight, highlight, structure, precision, direction), deliberately
# avoiding cutesy shapes like hearts/smileys/clouds.
_ICON_SHAPES = [MSO_SHAPE.LIGHTNING_BOLT, MSO_SHAPE.STAR_5_POINT, MSO_SHAPE.HEXAGON, MSO_SHAPE.DIAMOND, MSO_SHAPE.CHEVRON]
# The "playful" theme's own rotation instead — a teacher who picked THAT
# theme explicitly wants the cute-notebook look (a real reference photo of
# a hand-drawn Canva-style "КОНСПЕКТ" sheet — globe, books, backpack,
# stars, hearts, a lightbulb — was the ask), so cute is the point here,
# not the exception _ICON_SHAPES above deliberately avoids.
_PLAYFUL_ICON_SHAPES = [MSO_SHAPE.STAR_5_POINT, MSO_SHAPE.HEART, MSO_SHAPE.CLOUD, MSO_SHAPE.SUN, MSO_SHAPE.SMILEY_FACE]

# Five friendly pastel tints (light blue/green/lavender/pink/yellow) — the
# reference photo's boxes are each a DIFFERENT colour, not one accent
# repeated, which is what actually reads as "colourful notebook" rather
# than "one more monochrome deck". Independent of the subject accent
# rather than derived from it: a Math deck's blue accent alone can't
# produce this rainbow, and the reference doesn't tie its box colours to
# subject either.
_PLAYFUL_PALETTE = [
    RGBColor(0xBF, 0xDB, 0xFE),  # soft blue
    RGBColor(0xBB, 0xF7, 0xD0),  # soft green
    RGBColor(0xDD, 0xD6, 0xFE),  # soft lavender
    RGBColor(0xFB, 0xCF, 0xE8),  # soft pink
    RGBColor(0xFD, 0xE6, 0x8A),  # soft yellow
]
_PLAYFUL_PALETTE_DARK = [
    RGBColor(0x1D, 0x4E, 0xD8),
    RGBColor(0x15, 0x80, 0x3D),
    RGBColor(0x6D, 0x28, 0xD9),
    RGBColor(0xBE, 0x18, 0x5D),
    RGBColor(0x92, 0x6B, 0x00),
]


# ── deck themes ─────────────────────────────────────────────────────────
# The teacher picks one of these before generating (the "template" step in
# the create wizard), and the picker shows a real miniature of each, so
# the choice is made on what the slides will look like rather than on a
# name in a list.
#
# History worth knowing: this file used to offer five konspekt templates
# here too, and they were removed on direct feedback that five choices
# when only one looked good was friction. These four are a different
# proposition — each is a genuinely different deck design (background,
# title treatment, how a slide's content sits on it), not five variations
# of one, and the wizard now previews them instead of naming them.

_DECK_THEMES = {
    # The newest default, and the most literal one: direct feedback showed
    # a real reference photo (a hand-drawn, Canva-style "КОНСПЕКТ" notebook
    # sheet — globe/books/backpack doodles, colourful ribbon-labelled
    # boxes, pastel palette, spiral-bound left margin) and asked for that
    # look on the presentation. True hand-drawn illustration art is out of
    # reach here (no image-generation capability, no doodle asset library
    # in this repo) — what IS built from real pptx primitives: bullets as
    # ROTATING PASTEL cards (not one repeated colour — see
    # _PLAYFUL_PALETTE), a cute icon set instead of the professional-
    # reading one every other theme uses (_PLAYFUL_ICON_SHAPES), and a
    # spiral-bound-notebook left margin on every slide (see
    # _pptx_spiral_margin). Same warm spirit, honest about not being
    # pixel-identical to a hand-illustrated reference.
    "playful": {
        "bg": (0xFF, 0xFD, 0xF7),                # warm, slightly cream paper — not stark white
        "ink": RGBColor(0x2D, 0x2A, 0x4A),       # warm navy-purple, softer than pure black
        "muted": RGBColor(0x6B, 0x63, 0x8C),
        "title_font": "Comic Sans MS",           # the one deliberately playful/handwritten choice in this file
        "body_font": "Arial",                    # kept readable for the actual explanatory text
        "title_caps": False,
        "header": "rule",
        "cards": True,
        "badge": True,
        "pastel": True,                          # _pptx_bullet_grid: rotate _PLAYFUL_PALETTE fills instead of white+outline
        "spiral": True,                          # build_presentation_pptx: draw the notebook-hole margin
    },
    # Direct feedback ("shablонlar hunuk", every existing template
    # disliked at once) named Google Slides/Docs as the wanted look —
    # plain white, a simple thin rule under the title, plain bullet LINES
    # (not tinted rounded cards), no icon badge, no accent band, no
    # decorative shapes. Every visual flourish the other themes carry is
    # deliberately absent here: the content is what's supposed to read,
    # not the chrome around it.
    "google": {
        "bg": (0xFF, 0xFF, 0xFF),
        "ink": RGBColor(0x20, 0x21, 0x24),      # Google Docs' body text grey-black
        "muted": RGBColor(0x5F, 0x63, 0x68),    # Google's secondary-text grey
        "title_font": "Arial",
        "body_font": "Arial",
        "title_caps": False,
        "header": "underline",      # thin full-width hairline under the title
        "cards": False,             # plain bullet lines, no tinted boxes
        "badge": False,             # no icon disc
    },
    "zamonaviy": {
        "bg": (0xFF, 0xFF, 0xFF),
        "ink": RGBColor(0x1E, 0x29, 0x37),
        "muted": RGBColor(0x6B, 0x72, 0x80),
        "title_font": "Arial",
        "body_font": "Arial",
        "title_caps": False,
        "header": "rule",          # thin accent rule under the title
        "cards": True,             # bullets as rounded accent-tinted cards
        "badge": True,             # icon disc in the corner
    },
    # A printed-textbook feel: warm paper, serif headings, rules instead
    # of tinted cards. Reads calmer on a projector in a bright room.
    "klassik": {
        "bg": (0xFC, 0xFA, 0xF5),
        "ink": RGBColor(0x1F, 0x1B, 0x16),
        "muted": RGBColor(0x7A, 0x6E, 0x60),
        "title_font": "Georgia",
        "body_font": "Georgia",
        "title_caps": False,
        "header": "underline",     # full-width hairline under the title
        "cards": False,
        "badge": False,
    },
    # The loudest of the four: a solid accent band across the top of every
    # slide with the title reversed out of it, for younger classes.
    "rangli": {
        "bg": (0xFF, 0xFF, 0xFF),
        "ink": RGBColor(0x11, 0x18, 0x27),
        "muted": RGBColor(0x64, 0x74, 0x8B),
        "title_font": "Arial",
        "body_font": "Arial",
        "title_caps": False,
        "header": "band",          # filled accent band, white title
        "cards": True,
        "badge": True,
    },
    # Nothing but type and space — no chips, no badges, no rules. For a
    # teacher who wants the content to carry the slide by itself.
    "minimal": {
        "bg": (0xFF, 0xFF, 0xFF),
        "ink": RGBColor(0x0F, 0x17, 0x2A),
        "muted": RGBColor(0x94, 0xA3, 0xB8),
        "title_font": "Arial",
        "body_font": "Arial",
        "title_caps": True,        # small-caps-ish: set in caps, tracked
        "header": "plain",
        "cards": False,
        "badge": False,
    },
}
# The default has moved twice on direct feedback: "rangli" (loud, full
# accent bands + decorative blobs) was rejected as generic/ugly, "google"
# (plain white, no color, no cards) was then rejected as "juda minimal" —
# too plain, no color at all. "zamonaviy" (subtle accent-colored cards)
# was then tried as the deliberately-designed middle-ground default — and
# STILL called "hunuk" (ugly). That run of one-accent-color guesses ended
# when a real reference photo finally arrived: a hand-drawn, colourful
# notebook-style "КОНСПЕКТ" sheet. "playful" (see above) is the deck built
# to match that reference's actual spirit — pastel multi-colour cards, a
# spiral-notebook margin, a handwritten-style title font — and is now the
# default precisely because it's the one theme built FROM a concrete
# reference instead of another guess.
_DECK_THEME_DEFAULT = "playful"


def deck_theme(template_id) -> dict:
    """The deck design for a stored `template` value, falling back to the
    default for anything unrecognised (including the konspekt-only ids an
    older saved deck may still carry)."""
    return _DECK_THEMES.get(str(template_id or "").strip().lower(), _DECK_THEMES[_DECK_THEME_DEFAULT])


def _hex_rgb(value) -> RGBColor:
    """RGBColor from "#RRGGBB" — and a pass-through for a value that is
    already one, so the two theme sources can be normalised by the same
    code path."""
    if isinstance(value, RGBColor):
        return value
    h = str(value).lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _hex_tuple(value) -> tuple[int, int, int]:
    """The (r, g, b) int triple _set_slide_bg wants."""
    if isinstance(value, (tuple, list)):
        return (int(value[0]), int(value[1]), int(value[2]))
    h = str(value).lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _normalise_theme(theme: dict) -> dict:
    """Bring either theme source to the exact types build_presentation_pptx
    reads: bg as an (r, g, b) triple, every other colour as an RGBColor.

    _DECK_THEMES stores those types directly; subject_templates stores hex
    strings so it can stay importable without python-pptx. Normalising here
    means the renderer never has to know which source it got."""
    out = dict(theme)
    out["bg"] = _hex_tuple(theme["bg"])
    out["ink"] = _hex_rgb(theme["ink"])
    out["muted"] = _hex_rgb(theme["muted"])
    return out


def resolve_deck_theme(content: dict) -> dict:
    """Which design this deck is built with.

    The subject decides, unless the teacher explicitly asked for one of
    the six generic templates — an explicit choice in the wizard has to
    actually take effect, so a stored legacy id always wins over the
    automatic pick. Everything else (no template stored at all, "auto",
    or a subject-template id) resolves through subject_templates.

    Why the subject leads: a Biology deck and a History deck used to be
    the same deck in two accent colours, because the only thing the
    subject contributed was that colour. Now it picks the palette, the
    typography, the header treatment, the card silhouette, the marker,
    the decorative motif and the cover composition."""
    from app import subject_templates

    stored = str(content.get("template") or "").strip().lower()
    if stored in _DECK_THEMES:
        theme = dict(_DECK_THEMES[stored])
        # A legacy theme has no palette of its own — it always drew in
        # whatever accent the subject carried, and it still does.
        theme.setdefault("subject_template", "")
        theme["accent"] = None
        return _normalise_theme(theme)

    if stored in subject_templates.TEMPLATES:
        tpl = subject_templates.TEMPLATES[stored]
        theme = tpl.as_deck_theme()
        language = content.get("language")
        theme["title_font"] = subject_templates.safe_font(theme["title_font"], language)
        theme["body_font"] = subject_templates.safe_font(theme["body_font"], language)
        return _normalise_theme(theme)

    return _normalise_theme(subject_templates.deck_theme_for(
        content.get("subject"), content.get("grade"), content.get("language")))


# Keyword → icon for _pick_content_icon (bullet-grid cards / process steps):
# substring-matched against a card's own title+description (lowercased),
# covering common lesson vocabulary across the app's languages (Tajik,
# Russian, English) — so a card's icon reflects what THAT card is
# actually about instead of being an arbitrary rotating shape or a bare
# number, per direct teacher feedback ("har bir lista grafichiskiy
# materials bo'lsin va u o'sha slaydagi ma'lumotlarga asoslanib qo'yilsin").
# Order matters — first match wins — so more specific keywords are listed
# before generic ones they'd otherwise be shadowed by.
_CONTENT_ICON_KEYWORDS: list[tuple[tuple[str, ...], "MSO_SHAPE"]] = [
    (("ғоя", "идея", "g'oya", "goya", "idea", "мисол"), MSO_SHAPE.SUN),
    (("таърих", "тарих", "история", "tarix", "history", "созанда", "эҷод", "yaratil", "создан"), MSO_SHAPE.FLOWCHART_DOCUMENT),
    (("оянда", "будущ", "kelajak", "future", "рушд", "развит", "rivojlan", "growth", "ўсиш", "усиш"), MSO_SHAPE.UP_ARROW),
    (("савол", "вопрос", "savol", "question", "муаммо", "проблем", "muammo", "problem", "чаро", "почему", "nima uchun", "why"), MSO_SHAPE.ACTION_BUTTON_HELP),
    (("маълумот", "информ", "ma'lumot", "malumot", "information", "факт", "fact", "статистик"), MSO_SHAPE.ACTION_BUTTON_INFORMATION),
    (("раванд", "процесс", "jarayon", "process", "механизм", "mexanizm", "mechanism", "алгоритм", "algorithm", "кор мекунад", "ишлайди", "работает", "works"), MSO_SHAPE.GEAR_9),
    (("суръат", "скорост", "tezlik", "speed", "қувва", "энерги", "kuch", "energy", "quvvat"), MSO_SHAPE.LIGHTNING_BOLT),
    (("хатар", "опасн", "xavf", "danger", "risk", "амният", "безопасност", "xavfsizlik", "security"), MSO_SHAPE.NO_SYMBOL),
    (("шабака", "интернет", "сеть", "tarmoq", "internet", "network", "онлайн", "online", "abr", "cloud", "облак"), MSO_SHAPE.CLOUD),
    (("китобхона", "библиотек", "kutubxona", "library", "асбоб", "инструмент", "vosita", "tool"), MSO_SHAPE.FLOWCHART_PREDEFINED_PROCESS),
    (("сохт", "структур", "tuzilish", "structure", "модел", "model", "куб", "cube"), MSO_SHAPE.CUBE),
    (("бозӣ", "игра", "o'yin", "oyin", "game", "fun", "фан", "лаззат"), MSO_SHAPE.SMILEY_FACE),
    (("муҳаббат", "любов", "sevgi", "love", "care", "ғамхорӣ", "забота"), MSO_SHAPE.HEART),
    (("дастовард", "достижен", "yutuq", "achievement", "муваффақ", "успех", "muvaffaqiyat", "success", "беҳтарин", "лучш", "eng yaxshi", "best"), MSO_SHAPE.STAR_5_POINT),
    (("интишор", "выпуск", "release", "e'lon", "launch", "оғоз", "начал", "boshlash", "start"), MSO_SHAPE.RIGHT_ARROW),
]
def _pick_content_icon(*texts: str):
    """One MSO_SHAPE matching what the card actually says, or None.

    There used to be a fallback pool of neutral polygons, picked by
    hashing the text. It made unmatched cards look different from each
    other, which was the goal — but a hexagon beside "Связь растений и
    животных" and a chevron beside "Источник жизни" say nothing, and a
    reader looks for the meaning that is not there. None now means "this
    card has no icon worth showing", and the caller numbers it instead:
    a number is honest, and reads as a deliberate list."""
    joined = " ".join(t for t in texts if t).lower()
    for keywords, shape in _CONTENT_ICON_KEYWORDS:
        if any(kw in joined for kw in keywords):
            return shape
    return None


# The cover's agenda heading, in the deck's own language.
_DECK_AGENDA_LABEL = {
    "Русский": "В ЭТОМ УРОКЕ", "Таджикский": "ДАР ИН ДАРС",
    "English": "IN THIS LESSON",
    "Английский": "IN THIS LESSON",
}

# "+5" alone says nothing; the line has to say what the five are.
# Russian and English both inflect this count; Tajik does not
# (a Tajik noun after a numeral stays singular). The Russian form was a
# flat "ещё {n} слайдов", which is simply wrong for 2-4 — a real cover
# read "ещё 3 слайдов" — and English "{n} more slides" is wrong for 1.
_DECK_AGENDA_MORE = {
    "Русский": "ещё {n} {word}", "Таджикский": "боз {n} слайд",
    "English": "{n} more {word}",
    "Английский": "{n} more {word}",
}


def _agenda_more_word(language: str, n: int) -> str:
    """The noun that follows the count, inflected for `n`."""
    lang = str(language or "Русский")
    if lang == "Русский":
        # 1, 21, 31 -> слайд; 2-4, 22-24 -> слайда; everything else
        # (0, 5-20, 25-30, ...) -> слайдов.
        if n % 100 in (11, 12, 13, 14):
            return "слайдов"
        last = n % 10
        if last == 1:
            return "слайд"
        if last in (2, 3, 4):
            return "слайда"
        return "слайдов"
    if lang in ("English", "Английский"):
        return "slide" if n == 1 else "slides"
    return ""

# What KIND of moment a slide is, printed small in its top-right corner.
#
# The model already tags every slide (see _presentation_prompt's "kind"),
# and until now the renderer read exactly one of those tags ("formula")
# and threw the rest away — so a deck of ten slides was ten copies of one
# layout. Naming the kind on the slide, and giving three of them their own
# panel treatment below, is what turns that existing data into the varied
# composition the deck is supposed to have.
_SLIDE_KIND_LABEL = {
    "intro": {"Русский": "ВВЕДЕНИЕ", "Таджикский": "МУҚАДДИМА",
              "English": "INTRODUCTION",
              "Английский": "INTRODUCTION"},
    "concepts": {"Русский": "КЛЮЧЕВЫЕ ПОНЯТИЯ", "Таджикский": "МАФҲУМҲОИ АСОСӢ",
                 "English": "KEY CONCEPTS",
                 "Английский": "KEY CONCEPTS"},
    "example": {"Русский": "ПРИМЕР", "Таджикский": "МИСОЛ",
                "English": "EXAMPLE",
                "Английский": "EXAMPLE"},
    "task": {"Русский": "ЗАДАНИЕ", "Таджикский": "ВАЗИФА",
             "English": "TASK",
             "Английский": "TASK"},
    "summary": {"Русский": "ИТОГ", "Таджикский": "ХУЛОСА",
                "English": "SUMMARY",
                "Английский": "SUMMARY"},
}

# Which kinds get a panel drawn behind their bullets, and how it reads.
# Deliberately only three: a tag on every slide plus a panel on every
# slide would be the same repetition in a new costume.
_KIND_PANEL = {
    "example": "tinted",   # a worked example is set apart from the lesson
    "task": "dashed",      # something to DO — a worksheet box
    "summary": "banded",   # the takeaway, with a heavy rule beside it
}


def _kind_label(kind: str, language) -> str:
    table = _SLIDE_KIND_LABEL.get(kind)
    if not table:
        return ""
    return table.get(str(language or "Русский"), table.get("Русский", ""))


def _draw_kind_panel(slide, style: str, top_in: float, height_in: float,
                     accent: RGBColor, accent_soft: RGBColor) -> None:
    """The backdrop for an example/task/summary slide's bullet block.

    Drawn before the cards so it sits behind them, and given the same
    footprint the cards already occupy plus a little padding — it changes
    how the block READS without moving anything, so none of the layout
    maths above it has to know this exists."""
    x_in, w_in = 0.66, 11.98
    pad = 0.28
    y_in = max(1.45, top_in - pad)
    h_in = min(6.98 - y_in, height_in + pad * 2)
    if h_in <= 0.3:
        return
    if style == "tinted":
        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x_in), Inches(y_in),
                   Inches(w_in), Inches(h_in), accent_soft)
    elif style == "dashed":
        shp = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x_in), Inches(y_in),
                         Inches(w_in), Inches(h_in), _TEXT_WHITE,
                         line_rgb=accent, line_width=Pt(1.25))
        try:
            shp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        except Exception:
            pass
    elif style == "banded":
        _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(x_in), Inches(y_in),
                   Inches(w_in), Inches(h_in), accent_soft)
        _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(x_in), Inches(y_in),
                   Pt(5), Inches(h_in), accent)


_LOGO_PATH = os.path.join(os.path.dirname(__file__), "static", "logo.png")

_SLIDE_W = Inches(13.333)
_SLIDE_H = Inches(7.5)


def _set_slide_bg(slide, r, g, b):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(r, g, b)


def _add_shape(slide, shape_type, left, top, width, height, fill_rgb, line_rgb=None, line_width=Pt(1)):
    shape = slide.shapes.add_shape(shape_type, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_rgb
    if line_rgb:
        shape.line.fill.solid()
        shape.line.fill.fore_color.rgb = line_rgb
        shape.line.width = line_width
    else:
        shape.line.fill.background()
    # python-pptx's default theme attaches a soft drop shadow to every new
    # autoshape (via <p:style>'s effectRef) — invisible in the object model
    # until rendered, but it's what made every card/chip/badge in this file
    # look like dated 2007-era PowerPoint clipart instead of a flat, modern
    # deck. `.inherit = False` writes an empty <a:effectLst/>, which is the
    # documented way to override that inherited effect with "none" rather
    # than fighting the theme with raw XML per shape.
    #
    # LibreOffice ignores that override and keeps drawing the themed
    # shadow from <p:style>'s effectRef — and LibreOffice is what renders
    # the in-app preview (app/pptx_pdf.py), so a teacher saw the shadows
    # this line was meant to remove. flatten() zeroes both.
    pptx_shapes.flatten(shape)
    return shape


def _set_shape_alpha(shape, alpha_pct: int):
    """Applies fill transparency (python-pptx has no high-level API for
    this) so decorative background shapes can sit behind content without
    competing with it — e.g. alpha_pct=12 for a barely-there tint."""
    from pptx.oxml.ns import qn
    sp_pr = shape.fill._xPr
    solid_fill = sp_pr.find(qn('a:solidFill'))
    if solid_fill is None:
        return
    color_el = solid_fill.find(qn('a:srgbClr'))
    if color_el is None:
        return
    alpha_el = color_el.makeelement(qn('a:alpha'), {'val': str(alpha_pct * 1000)})
    color_el.append(alpha_el)


def _add_gradient_fill(shape, rgb1, rgb2, angle=45):
    """Applies a genuine two-stop gradient (python-pptx exposes this at the
    object-model level, unlike transitions/alpha, so no raw XML needed).
    Used for full-bleed cover/closing backgrounds and content-slide header
    bands so the deck reads as designed rather than flat report pages."""
    fill = shape.fill
    fill.gradient()
    stops = fill.gradient_stops
    stops[0].color.rgb = rgb1
    stops[0].position = 0.0
    stops[-1].color.rgb = rgb2
    stops[-1].position = 1.0
    fill.gradient_angle = angle
    return shape


def _trim_text_to_lines(text: str, width_in: float, font_size: float, max_lines: int) -> str:
    """`text` cut back to the last whole word that still fits in
    `max_lines`, with an ellipsis.

    Cutting at a word rather than a character is the whole point: a slide
    that ends mid-word reads as a rendering bug, while one that ends on a
    clean "…" reads as a summary whose remainder is in the speaker
    notes — which is exactly where the rest of it is."""
    words = str(text or "").split()
    if not words or _estimate_pptx_lines(text, width_in, font_size) <= max_lines:
        return text
    kept: list[str] = []
    for word in words:
        trial = " ".join(kept + [word]) + "…"
        if _estimate_pptx_lines(trial, width_in, font_size) > max_lines:
            break
        kept.append(word)
    return (" ".join(kept) + "…") if kept else ""


_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


def _estimate_pptx_lines(text, width_in, font_size):
    """Rough character-count-based line-wrap estimate — python-pptx has no
    text-measurement API, so bullet rows used to be spaced a fixed 0.98in
    apart regardless of actual length, which overlapped the next bullet
    whenever the AI wrote a long, detailed sentence (routinely 3-4 lines
    of wrapped text). Good enough to space bullets apart without overlap —
    not pixel-perfect layout, since a true text measurement would need
    actually rendering the font.

    0.52 was calibrated on Latin text; Cyrillic runs wider in Arial (Ш,
    Ж, Ф, М and friends are noticeably broader than the Latin average),
    so a Tajik/Russian title this estimated as 1 line came out as 2 in
    real PowerPoint — confirmed live on a deck's cover-slide agenda,
    where the next item's number badge then overlapped the wrapped
    second line. Almost everything this app renders is Cyrillic, so the
    text is sniffed per-call rather than adding a separate "Cyrillic"
    variant everywhere this is called."""
    factor = 0.62 if _CYRILLIC_RE.search(str(text)) else 0.52
    avg_char_width_in = (font_size * factor) / 72.0
    chars_per_line = max(8, int(width_in / avg_char_width_in))
    return max(1, -(-len(text) // chars_per_line))  # ceil division


def _add_logo_badge(slide, on_dark_bg=False):
    """Small circular Dastyor mark in the bottom-right corner of every
    slide. Always sits inside an opaque white disc — regardless of whether
    the slide behind it is a white content area or a dark gradient — so the
    logo stays legible everywhere, plus a thin outline so it still reads as
    a deliberate badge on a plain white background."""
    if not os.path.exists(_LOGO_PATH):
        return
    diameter = Inches(0.62)
    left = _SLIDE_W - diameter - Inches(0.4)
    top = _SLIDE_H - diameter - Inches(0.35)
    line_rgb = _ACCENT_SOFT if not on_dark_bg else None
    _add_shape(slide, MSO_SHAPE.OVAL, left, top, diameter, diameter, _TEXT_WHITE, line_rgb=line_rgb, line_width=Pt(0.75))
    pad = Emu(int(diameter * 0.17))
    slide.shapes.add_picture(_LOGO_PATH, left + pad, top + pad, width=diameter - pad * 2, height=diameter - pad * 2)


def _pptx_sticker_decorations(slide) -> None:
    """"playful" theme only — a small hand-drawn-STICKER-style cluster
    (a tilted stack of books, a heart) on the cover, echoing the two
    reference photos of Canva sticker cutouts sent directly. Built from
    real pptx autoshapes with a rotation on each, not an image asset: no
    hand-drawn illustration library exists in this repo, and fetching a
    matching real clipart image from any public source (openclipart.org,
    etc.) proved too unreliable over this environment's network to depend
    on at generation time — confirmed live, the same connectivity issues
    already worked around elsewhere in this file (see _curl_bytes's
    docstring in image_builder.py). This is the honest middle ground:
    the STICKER idea, built from shapes that always render.

    Placed in the cover's one genuinely empty region — below the
    Синф:/Мактаб: fill-in lines, above the footer rule — confirmed empty
    by inspecting the real shape list built there (nothing between
    roughly y=5.0in and y=6.85in on the left half of the slide)."""
    book_colors = [RGBColor(0xF9, 0xA8, 0xD4), RGBColor(0x93, 0xC5, 0xFD), RGBColor(0x86, 0xEF, 0xAC)]
    x0, y0, w0 = 1.0, 5.35, 1.5
    y = y0
    for i, color in enumerate(book_colors):
        h = 0.22
        w = w0 - i * 0.12
        book = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x0), Inches(y), Inches(w), Inches(h),
                           color, line_rgb=RGBColor(0xFF, 0xFF, 0xFF), line_width=Pt(1.5))
        book.rotation = -4 + i * 3
        y += h - 0.03
    heart = _add_shape(slide, MSO_SHAPE.HEART, Inches(x0 + w0 + 0.25), Inches(y0 - 0.15), Inches(0.42), Inches(0.42),
                        RGBColor(0xFB, 0x71, 0x85))
    heart.rotation = -12

    # A pencil — a thin yellow body plus a small dark triangular tip,
    # rotated together — placed to the right of the heart in the same
    # empty strip.
    pencil_x, pencil_y = x0 + w0 + 0.95, y0 + 0.05
    body = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(pencil_x), Inches(pencil_y), Inches(0.85), Inches(0.16),
                       RGBColor(0xFD, 0xE0, 0x47), line_rgb=RGBColor(0xB4, 0x8A, 0x00), line_width=Pt(1.0))
    body.rotation = 35
    tip = _add_shape(slide, MSO_SHAPE.ISOSCELES_TRIANGLE, Inches(pencil_x + 0.62), Inches(pencil_y + 0.30),
                      Inches(0.18), Inches(0.16), RGBColor(0x8B, 0x5E, 0x34))
    tip.rotation = 125


def _pptx_washi_tape(slide, x_in: float, y_in: float, color: RGBColor, rotation: float = -6) -> None:
    """A small tilted, semi-transparent strip — the "washi tape" corner
    accent every content slide's header now carries in the "playful"
    theme, echoing the reference photos' Canva-sticker corners. Sized and
    positioned to sit in the header's own empty padding (above the slide
    number, below the top edge) — never near the title/bullet text, so it
    never has to compete with content of varying length."""
    tape = _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(x_in), Inches(y_in), Inches(0.85), Inches(0.24), color)
    tape.rotation = rotation
    _set_shape_alpha(tape, 60)


def _pptx_notebook_lines(slide) -> None:
    """Faint horizontal ruled lines across the whole slide — real
    notebook paper, not just a cream background colour. Drawn absolute
    FIRST (before the spiral margin, before any content), in a colour
    close enough to the cream background (_BG for "playful") that it
    reads as paper texture, not as a grid competing with the text
    sitting on top of it."""
    line_color = RGBColor(0xEE, 0xE4, 0xC8)
    y = 0.55
    while y < 7.3:
        _add_shape(slide, MSO_SHAPE.RECTANGLE, 0, Inches(y), _SLIDE_W, Pt(0.75), line_color)
        y += 0.32


def _pptx_spiral_margin(slide) -> None:
    """The "playful" theme's spiral-bound-notebook left margin — a column
    of small punched-hole circles plus a thin vertical rule, echoing the
    reference photo's spiral-notebook binding. Drawn FIRST (bottom of the
    z-order, before the theme's own background is even a factor) and
    confined to x < 0.55in — well clear of every content column, which
    all start at _CONTENT_X_IN (0.9in) or later — so it never competes
    with or gets covered by real content, on the cover or any content
    slide."""
    hole_d = Inches(0.14)
    hole_x = Inches(0.28) - hole_d / 2
    hole_line = RGBColor(0xD8, 0xD2, 0xC4)
    # Every 4th "hole" position is a tiny heart/star instead of a plain
    # punched circle — the one flourish direct feedback asked to see on
    # EVERY slide, not just the cover, placed in the only strip of the
    # slide that's structurally guaranteed empty regardless of how much
    # text a given slide happens to hold (unlike the cover's sticker
    # cluster, which only fits where the cover ITSELF has empty room —
    # see _pptx_sticker_decorations).
    sparkle_shapes = [MSO_SHAPE.HEART, MSO_SHAPE.STAR_5_POINT]
    sparkle_colors = [RGBColor(0xFB, 0x71, 0x85), RGBColor(0xFB, 0xBF, 0x24)]
    y = 0.35
    n = 0
    while y < 7.15:
        if n % 4 == 3:
            d = Inches(0.16)
            k = (n // 4) % len(sparkle_shapes)
            spark = _add_shape(slide, sparkle_shapes[k], Inches(0.28) - d / 2, Inches(y) - d / 2 + hole_d / 2,
                               d, d, sparkle_colors[k])
            spark.rotation = -10 if k == 0 else 0
        else:
            _add_shape(slide, MSO_SHAPE.OVAL, hole_x, Inches(y), hole_d, hole_d,
                       RGBColor(0xFF, 0xFD, 0xF7), line_rgb=hole_line, line_width=Pt(1.0))
        y += 0.55
        n += 1
    _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.58), Inches(0.15), Pt(1.25), Inches(7.2),
               RGBColor(0xF3, 0xC6, 0xC6))


# The badge's own silhouette, per subject template's `marker`. A circle
# everywhere used to be one of the reasons two decks looked identical: the
# badge repeats on every card of every slide, so its shape carries more of
# a deck's character than almost anything else on the slide.
_MARKER_BADGE_SHAPE = {
    "number": MSO_SHAPE.OVAL,
    "circle": MSO_SHAPE.OVAL,
    "dot": MSO_SHAPE.OVAL,
    "square": MSO_SHAPE.ROUNDED_RECTANGLE,
    "hexagon": MSO_SHAPE.HEXAGON,
    "diamond": MSO_SHAPE.DIAMOND,
    "chevron": MSO_SHAPE.PENTAGON,
    "pin": MSO_SHAPE.OVAL,
    "roman": MSO_SHAPE.RECTANGLE,
    "bracket": MSO_SHAPE.ROUNDED_RECTANGLE,
    "dash": MSO_SHAPE.OVAL,
    "star": MSO_SHAPE.OVAL,
    "leaf": MSO_SHAPE.OVAL,
    "triangle": MSO_SHAPE.ISOSCELES_TRIANGLE,
}

# What goes INSIDE the badge when the bullet's own text suggested no
# content icon (see _pick_content_icon) — the subject's own mark rather
# than a bare sequence number.
_MARKER_GLYPH_SHAPE = {
    "chevron": MSO_SHAPE.CHEVRON,
    "diamond": MSO_SHAPE.DIAMOND,
    "hexagon": MSO_SHAPE.HEXAGON,
    "star": MSO_SHAPE.STAR_5_POINT,
    "triangle": MSO_SHAPE.ISOSCELES_TRIANGLE,
    "leaf": MSO_SHAPE.DIAMOND,
    # A peak, not a map pin: an upward triangle is legible at badge size
    # where a teardrop is not, and it reads as terrain, which is the
    # subject.
    "pin": MSO_SHAPE.ISOSCELES_TRIANGLE,
    "square": MSO_SHAPE.RECTANGLE,
}

# Roman numerals for the history template's markers. Only ever asked for
# 1..12 (the grid caps well below that), so a table beats a converter.
_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")


def _marker_label(marker: str, n: int) -> str:
    """The text a numbered badge carries, in this template's own
    numbering: plain digits, roman numerals, or a bracketed index."""
    if marker == "roman":
        return _ROMAN[(n - 1) % len(_ROMAN)]
    if marker == "bracket":
        return f"[{n}]"
    if marker == "dash":
        return "—"
    return str(n)


def _add_icon_badge(slide, cx, cy, diameter, shape_type, bg_rgb=_ACCENT,
                    icon_rgb=_TEXT_WHITE, badge_shape=MSO_SHAPE.OVAL):
    """A colored badge with a smaller icon-shape centered inside — the
    closest thing to a real icon/illustration achievable without an image
    generation API or an SVG rendering library, but renders crisp and fully
    vector (scales perfectly, unlike a raster image would).

    `badge_shape` is the outer silhouette: a circle by default, a hexagon
    for chemistry, a diamond for literature, and so on."""
    _add_shape(slide, badge_shape, cx - diameter / 2, cy - diameter / 2, diameter, diameter, bg_rgb)
    inner = diameter * 0.42
    _add_shape(slide, shape_type, cx - inner / 2, cy - inner / 2, inner, inner, icon_rgb)


def _add_number_badge(slide, cx, cy, diameter, number: int, bg_rgb=_ACCENT,
                      text_rgb=_TEXT_WHITE, badge_shape=MSO_SHAPE.OVAL,
                      label: str | None = None):
    """The same badge, carrying a number — for a card whose content has no
    icon that would mean anything (see _pick_content_icon). `label` lets a
    template number its cards its own way (roman numerals, [n], ...)."""
    text = label if label is not None else str(number)
    _add_shape(slide, badge_shape, cx - diameter / 2, cy - diameter / 2,
               diameter, diameter, bg_rgb)
    # A 3-character label ("VIII", "[10]") does not fit at the size a
    # single digit does — shrink rather than let it spill out of the badge.
    size = 13 if len(text) <= 2 else (11 if len(text) == 3 else 9)
    _add_text(slide, cx - diameter / 2, cy - diameter / 2 + Emu(int(diameter * 0.12)),
              diameter, diameter, text, size, True, text_rgb, PP_ALIGN.CENTER)


def _add_transition(slide, duration_ms=600):
    """Injects a basic fade transition into the slide's own XML — python-pptx
    has no API for this (transitions/animations live outside its object
    model), but the underlying OOXML tag is simple enough to add directly.
    This is real PowerPoint "animation" (Transitions ▸ Fade), as opposed to
    per-element entrance effects, which need much more complex timing XML."""
    from pptx.oxml.ns import qn
    sld = slide._element
    existing = sld.find(qn('p:transition'))
    if existing is not None:
        sld.remove(existing)
    transition = sld.makeelement(qn('p:transition'), {'spd': 'med', 'dur': str(duration_ms)})
    fade = transition.makeelement(qn('p:fade'), {})
    transition.append(fade)
    # <p:transition> must come right after <p:timing> if present, but with
    # no timing element it's valid as the final child of <p:sld>.
    sld.append(transition)


def _add_text(slide, left, top, width, height, text, font_size=14, bold=False, color=_INK, align=PP_ALIGN.LEFT, wrap=True, font_name="Arial"):
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf = txb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.text = text
    p.font.name = font_name
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.alignment = align
    return tf


def _add_multiline(slide, left, top, width, height, lines, font_size=14, color=_INK, line_spacing=Pt(8)):
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf = txb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = line
        p.font.name = "Arial"
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.space_after = line_spacing
    return tf


# A plain bullet list rendered as one skinny left-aligned column used to
# leave the entire right half of a text-only content slide dead white
# space (a teacher literally circled it in a screenshot and asked for
# "grafichiskiy materials" there instead). _pptx_bullet_grid renders those
# same bullets as a 2-column grid of small icon+text cards instead — same
# information, but it fills the slide's actual width and gives every
# bullet its own graphical anchor instead of a plain text line. Only used
# when a slide has NO "visual" block and >=2 bullets (see call site) — a
# slide that already has a table/process/comparison graphic, or just one
# lone lead-in bullet, keeps the simpler single-line treatment instead.
_GRID_BADGE_D_IN = 0.56
_GRID_BADGE_PROTRUDE_IN = 0.18  # how far the badge pokes above the card's own top edge


# The column every slide is built in. The header rule, the footer bar and
# the cards used to end at three different x positions (12.4, 11.4 and
# 11.0), which is why the right-hand side of a slide looked ragged and
# emptier than the left. One number now, and the margins match: 0.9 left,
# 0.93 right on a 13.33in slide.
_CONTENT_X_IN = 0.9
_CONTENT_W_IN = 11.5


def _grid_columns(n: int, kind: str = "") -> int:
    """How many columns `n` cards want.

    Three bullets in a two-column grid leave a hole where the fourth card
    would be, and that hole is the single most "unfinished" thing on a
    slide. Three and six go in threes; everything else pairs, and an odd
    last card is stretched to the full width by the caller instead of
    sitting next to an empty half.

    A "concepts" slide is the exception: it names short terms, and three
    short terms to a row read as the glossary strip that slide actually
    is, rather than as two columns of half-empty cards. `kind` must be
    passed to BOTH the measuring pass and the drawing pass or they will
    lay the same bullets out differently and the cards will overlap."""
    if kind == "concepts" and n >= 3:
        return 3
    return 3 if n in (3, 6) else 2


def _pptx_bullet_grid_natural_heights(bullets: list[str], col_w_in: float, font_size: int = 14, kind: str = "") -> list[float]:
    """The height each grid row needs for its own text — the un-stretched
    minimum. See _pptx_bullet_grid for why the caller usually stretches
    these further to actually fill the slide."""
    pad_in = 0.22
    n = len(bullets)
    cols = _grid_columns(n, kind)
    # col_w_in arrives measured for two columns; three narrower ones fit
    # the same width, and their text has to be measured against THAT.
    if cols == 3:
        col_w_in = (col_w_in * 2 + 0.3 - 0.3 * 2) / 3
    text_w_in = col_w_in - pad_in * 2
    line_h_in = font_size * 1.3 / 72.0
    rows = -(-n // cols)  # ceil div
    row_heights = []
    for r in range(rows):
        pair = bullets[r * cols:r * cols + cols]
        max_lines = max(_estimate_pptx_lines(bp, text_w_in, font_size) for bp in pair)
        text_h_in = max_lines * line_h_in
        row_heights.append((_GRID_BADGE_D_IN - _GRID_BADGE_PROTRUDE_IN) + 0.16 + text_h_in + pad_in)
    return row_heights


def _draw_bullet_card(slide, card: str, x_in: float, y_in: float, w_in: float,
                      h_in: float, accent: RGBColor, border: RGBColor,
                      support: RGBColor) -> None:
    """One bullet card's silhouette, in this subject's own shape language.

    The card repeats several times per slide and on most slides of the
    deck, so its outline does more to make two subjects look different
    than the accent colour ever did: geometry's square corners with a hard
    left rule genuinely do not read as biology's pill, and neither reads
    as history's ruled plaque.

    Every variant keeps the SAME footprint (x/y/w/h) so the caller's
    layout maths — which is where all the overflow fixes live — is
    untouched by the choice."""
    L, T, W, H = Inches(x_in), Inches(y_in), Inches(w_in), Inches(h_in)

    if card == "sharp":
        _add_shape(slide, MSO_SHAPE.RECTANGLE, L, T, W, H, _TEXT_WHITE,
                   line_rgb=border, line_width=Pt(1.25))
        _add_shape(slide, MSO_SHAPE.RECTANGLE, L, T, Pt(3.5), H, accent)
    elif card == "tab":
        shp = _add_shape(slide, MSO_SHAPE.ROUND_2_SAME_RECTANGLE, L, T, W, H,
                         _TEXT_WHITE, line_rgb=border, line_width=Pt(1.25))
        _add_shape(slide, MSO_SHAPE.RECTANGLE, L, T + H - Pt(3), W, Pt(3), accent)
    elif card == "hex":
        # Corners cut on the diagonal — the flat-sided silhouette a
        # structural formula is drawn with, without being a literal
        # hexagon (which cannot hold a line of text).
        _add_shape(slide, MSO_SHAPE.SNIP_2_DIAG_RECTANGLE, L, T, W, H,
                   _TEXT_WHITE, line_rgb=border, line_width=Pt(1.25))
    elif card == "pill":
        shp = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, L, T, W, H,
                         _TEXT_WHITE, line_rgb=border, line_width=Pt(1.25))
        try:
            # Fully rounded ends. The default adjustment is a modest
            # corner radius; 0.5 takes it to a lozenge.
            shp.adjustments[0] = 0.5
        except Exception:
            pass
    elif card == "legend":
        shp = _add_shape(slide, MSO_SHAPE.RECTANGLE, L, T, W, H, _TEXT_WHITE,
                         line_rgb=accent, line_width=Pt(1.0))
        try:
            shp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        except Exception:
            pass
    elif card == "plaque":
        _add_shape(slide, MSO_SHAPE.RECTANGLE, L, T, W, H, _TEXT_WHITE,
                   line_rgb=border, line_width=Pt(1.0))
        _add_shape(slide, MSO_SHAPE.RECTANGLE, L, T, W, Pt(4), accent)
    elif card == "window":
        _add_shape(slide, MSO_SHAPE.ROUND_2_SAME_RECTANGLE, L, T, W, H,
                   _TEXT_WHITE, line_rgb=border, line_width=Pt(1.25))
        _add_shape(slide, MSO_SHAPE.RECTANGLE, L, T + Inches(0.26), W, Pt(1), border)
    elif card == "quote":
        _add_shape(slide, MSO_SHAPE.RECTANGLE, L, T, W, H, _TEXT_WHITE)
        _add_shape(slide, MSO_SHAPE.RECTANGLE, L, T, Pt(5), H, support)
    elif card == "framed":
        _add_shape(slide, MSO_SHAPE.RECTANGLE, L, T, W, H, _TEXT_WHITE,
                   line_rgb=border, line_width=Pt(1.5))
        inset = Inches(0.055)
        _add_shape(slide, MSO_SHAPE.RECTANGLE, L + inset, T + inset,
                   W - inset * 2, H - inset * 2, _TEXT_WHITE,
                   line_rgb=support, line_width=Pt(0.75))
    elif card == "bubble":
        shp = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, L, T, W, H,
                         _TEXT_WHITE, line_rgb=border, line_width=Pt(1.25))
        try:
            shp.adjustments[0] = 0.22
        except Exception:
            pass
        _add_shape(slide, MSO_SHAPE.ISOSCELES_TRIANGLE, L + Inches(0.45),
                   T + H - Inches(0.02), Inches(0.26), Inches(0.2), _TEXT_WHITE,
                   line_rgb=border, line_width=Pt(1.0))
    elif card == "ornate":
        _add_shape(slide, MSO_SHAPE.RECTANGLE, L, T, W, H, _TEXT_WHITE,
                   line_rgb=border, line_width=Pt(1.25))
        d = Inches(0.11)
        for cx, cy in ((L, T), (L + W - d, T), (L, T + H - d), (L + W - d, T + H - d)):
            _add_shape(slide, MSO_SHAPE.DIAMOND, cx, cy, d, d, support)
    else:  # "rounded" — the neutral default every legacy theme used
        _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, L, T, W, H, _TEXT_WHITE,
                   line_rgb=border, line_width=Pt(1.25))


def _pptx_bullet_grid(slide, top_in: float, bullets: list[str], row_heights: list[float], accent: RGBColor, accent_soft: RGBColor, ink: RGBColor, pastel: bool = False, card: str = "rounded", marker: str = "number", kind: str = "") -> None:
    """Draws bullets as a 2-column grid of icon+text cards. `row_heights`
    (one entry per row of up to 2 cards) is caller-supplied rather than
    recomputed here — see build_presentation_pptx, which stretches these
    past their natural minimum to actually fill the available vertical
    space instead of leaving a couple of small cards stranded at the top
    of an otherwise-empty slide when a slide only has 2-3 short bullets.

    Each card's badge is a CONTENT-relevant icon (see _pick_content_icon),
    not a bare sequence number, and it overlaps the card's own top edge
    instead of sitting fully inside the padding — direct teacher feedback
    was that plain numbered chips over a flat tinted box read as "text
    sitting in a block" rather than a designed card; a badge that pops out
    of the card plus an icon tied to that bullet's actual content is a
    real (if modest) step toward looking hand-designed instead of
    templated.

    `pastel=True` (the "playful" theme, see _DECK_THEMES) swaps the
    white-card-with-accent-outline look for a rotating pastel palette
    (_PLAYFUL_PALETTE) — a DIFFERENT fill colour per card, matching a
    hand-drawn notebook reference's colourful boxes rather than one
    accent colour repeated everywhere."""
    left_in = _CONTENT_X_IN
    total_w_in = _CONTENT_W_IN
    col_gap_in = 0.3
    cols = _grid_columns(len(bullets), kind)
    col_w_in = (total_w_in - col_gap_in * (cols - 1)) / cols
    pad_in = 0.22
    badge_d_in = _GRID_BADGE_D_IN
    protrude_in = _GRID_BADGE_PROTRUDE_IN
    font_size = 14
    row_gap_in = 0.35  # a bit more than the badge protrusion, so it never overlaps the row above
    text_w_in = col_w_in - pad_in * 2
    # accent_soft (the caller's usual pastel-fill color) mixes 88% toward
    # white — nearly invisible as a border against a white card on a white
    # slide. A ~55%-toward-white mix instead stays subtle but is actually
    # visible as an outline.
    _hex = str(accent)
    _r, _g, _b = int(_hex[0:2], 16), int(_hex[2:4], 16), int(_hex[4:6], 16)
    border_color = RGBColor(int(_r + (255 - _r) * 0.55), int(_g + (255 - _g) * 0.55), int(_b + (255 - _b) * 0.55))

    y_in = top_in
    for r, row_h_in in enumerate(row_heights):
        for c in range(cols):
            j = r * cols + c
            if j >= len(bullets):
                break
            bp = bullets[j]
            x_in = left_in + c * (col_w_in + col_gap_in)
            # A card alone on the last row takes the whole width rather
            # than leaving the rest of the row blank — five bullets read
            # as a finished 2+2+1 block instead of a grid with a bite out
            # of it.
            this_w_in = col_w_in
            if c == 0 and j == len(bullets) - 1 and len(bullets) % cols == 1:
                this_w_in = total_w_in
            text_w_in = this_w_in - pad_in * 2
            if pastel:
                # A different pastel fill per card (cycling _PLAYFUL_
                # PALETTE), its own matching dark shade for the border and
                # badge — the "colourful notebook boxes" look, not one
                # accent colour reused everywhere. A tiny alternating tilt
                # (well under the row/column gap, so it can never touch a
                # neighbour) plus a dashed border reads as hand-placed on
                # a page rather than machine-ruled — closer to the
                # reference photo's slightly-imperfect drawn boxes.
                card_fill = _PLAYFUL_PALETTE[j % len(_PLAYFUL_PALETTE)]
                card_badge_color = _PLAYFUL_PALETTE_DARK[j % len(_PLAYFUL_PALETTE_DARK)]
                card = _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x_in), Inches(y_in), Inches(this_w_in), Inches(row_h_in),
                                  card_fill, line_rgb=card_badge_color, line_width=Pt(1.25))
                card.rotation = 1.4 if j % 2 == 0 else -1.4
                card.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            else:
                # White fill + a thin accent-soft border instead of a solid
                # pastel fill — against an all-white deck (every header is
                # white now too, see build_presentation_pptx) a tinted block
                # read as heavier than intended; an outlined card keeps the
                # same "this is one grouped item" cue with much less weight.
                # Which SILHOUETTE that card has is the subject template's
                # (see _draw_bullet_card); the footprint is identical
                # either way, so none of the layout maths above changes.
                card_badge_color = accent
                _draw_bullet_card(slide, card, x_in, y_in, this_w_in, row_h_in,
                                  accent, border_color, accent_soft)

            badge_top_in = y_in - protrude_in
            icon = _pick_content_icon(bp)
            if pastel and icon is None:
                icon = _PLAYFUL_ICON_SHAPES[j % len(_PLAYFUL_ICON_SHAPES)]
            # No content icon, but the template has a mark of its own —
            # use it rather than a bare sequence number. A content-derived
            # icon still wins: it says something about THIS bullet, which
            # is worth more than another copy of the subject's symbol.
            if icon is None:
                icon = _MARKER_GLYPH_SHAPE.get(marker)
            badge_shape = _MARKER_BADGE_SHAPE.get(marker, MSO_SHAPE.OVAL)
            badge_cx = Inches(x_in + pad_in + badge_d_in / 2)
            badge_cy = Inches(badge_top_in + badge_d_in / 2)
            if icon is not None:
                _add_icon_badge(slide, badge_cx, badge_cy, Inches(badge_d_in),
                                icon, card_badge_color, _TEXT_WHITE,
                                badge_shape=badge_shape)
            else:
                _add_number_badge(slide, badge_cx, badge_cy, Inches(badge_d_in),
                                  j + 1, card_badge_color, _TEXT_WHITE,
                                  badge_shape=badge_shape,
                                  label=_marker_label(marker, j + 1))

            text_y_in = badge_top_in + badge_d_in + 0.16
            _add_text(slide, Inches(x_in + pad_in), Inches(text_y_in), Inches(text_w_in), Inches(row_h_in - (text_y_in - y_in)),
                      bp, font_size, False, ink)
        y_in += row_h_in + row_gap_in


def _estimate_pptx_visual_height(block: dict) -> float:
    """Mirrors _pptx_visual_block's own height math without drawing
    anything, so the content-slide layout can center the bullets+visual as
    one block *before* any shape gets placed (see build_presentation_pptx).
    Keep in sync with the row_h_in/card_h_in constants used there."""
    btype = block.get("type")
    data = block.get("data") or {}
    if btype in ("table", "comparison"):
        if btype == "table":
            headers = data.get("headers") or []
            rows = data.get("rows") or []
        else:
            headers = [""] + list(data.get("criteria") or [])
            rows = data.get("items") or []
        if not headers or not rows:
            return 0.0
        return 0.42 * (1 + min(5, len(rows)))
    elif btype == "process":
        steps = (data.get("steps") or [])[:6]
        if not steps:
            return 0.0
        return _pptx_process_layout(steps, 10.1)[1]
    elif btype == "chart":
        return 3.0 if data.get("categories") and data.get("series") else 0.0
    elif btype == "figure":
        # Was missing entirely — every OTHER visual type mirrors its own
        # drawing math here so the layout can budget space for it before
        # anything is placed, but "figure" fell through to the final
        # `return 0.0` below and was silently treated as taking NO room.
        # Confirmed live: a flowchart figure got centered as if the slide
        # were bullets-only, then drawn at its real (up to ~4in) height
        # starting from that too-low cursor — the bottom of the diagram
        # ran straight off the bottom edge of the slide, screenshotted by
        # a teacher mid-generation. Mirrors _pptx_visual_block's own
        # max_w_in/max_h_in=3.6 + caption-line math exactly.
        image_path = block.get("image")
        if not image_path:
            return 0.0
        full_path = os.path.join(os.path.dirname(__file__), "..", str(image_path).lstrip("/"))
        if not os.path.exists(full_path):
            return 0.0
        try:
            with PILImage.open(full_path) as im:
                iw, ih = im.size
            scale = min(10.1 / iw, 3.6 / ih)
            h_in = ih * scale
        except Exception:
            return 0.0
        if str(block.get("caption") or ""):
            h_in += 0.45
        return h_in
    return 0.0


_PROCESS_TITLE_PT = 15
_PROCESS_DESC_PT = 12
_PROCESS_ITEM_GAP_IN = 0.20
_PROCESS_NUM_COL_IN = 0.42


def _pptx_process_layout(steps: list, width_in: float) -> tuple[list[tuple[float, float]], float]:
    """Per-step (title height, description height) and the total, in
    inches, for a "process" block set as notes.

    One function so the height ESTIMATE and the actual drawing can never
    disagree — they used to be two separate pieces of pixel maths (the
    estimator mirrored an image generator's internal layout), and that is
    the kind of duplication that quietly slides out of sync and pushes
    the block off the slide."""
    text_w_in = width_in - _PROCESS_NUM_COL_IN
    rows: list[tuple[float, float]] = []
    total = 0.0
    for step in steps:
        title = str((step or {}).get("title", "")).strip()
        desc = str((step or {}).get("description", "")).strip()
        title_h = (_estimate_pptx_lines(title, text_w_in, _PROCESS_TITLE_PT)
                   * _PROCESS_TITLE_PT * 1.30 / 72.0) if title else 0.0
        desc_h = (_estimate_pptx_lines(desc, text_w_in, _PROCESS_DESC_PT)
                  * _PROCESS_DESC_PT * 1.34 / 72.0 + 0.04) if desc else 0.0
        rows.append((title_h, desc_h))
        total += title_h + desc_h
    total += _PROCESS_ITEM_GAP_IN * max(0, len(rows) - 1)
    return rows, total


def _chart_color_shades(accent: RGBColor, n: int) -> list[RGBColor]:
    """n distinguishable shades of one accent color for a chart's series/
    pie-wedges — reusing the deck's own subject accent instead of
    PowerPoint's default rainbow chart palette, so a chart reads as part of
    the same designed deck instead of a bolted-on Excel graph."""
    hex_str = str(accent)
    r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
    if n <= 1:
        return [accent]
    shades = []
    for i in range(n):
        t = i / (n - 1)
        factor = 0.62 + t * 0.7  # darkest ~0.62x, lightest ~1.32x (clamped below)
        shades.append(RGBColor(min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor))))
    return shades


def _pptx_visual_block(slide, top_in: float, width_in: float, block: dict, accent: RGBColor, accent_soft: RGBColor, ink: RGBColor, pastel: bool = False) -> float:
    """Draws one AI-chosen visual (table/comparison/process/chart/figure —
    see ai_service.py's _presentation_prompt rule 9) directly onto a pptx
    content slide, using the same shape/text helpers as everything else in
    this file rather than an external charting library. PDF counterpart is
    _pdf_visual_block, sharing the exact same block["type"]/block["data"]
    shape so the model only ever has to learn one vocabulary — except
    "figure", whose "image"/"caption" sit on the block itself, stamped by
    _render_slide_figures after the model returns (a shape id, not a
    picture, is all the model ever writes into "data").

    Returns the height (inches) actually used so the caller can lay out
    speaker-notes/footer below it; returns 0 and draws nothing for an
    empty/malformed block — a cosmetic extra should never break the export.
    """
    btype = block.get("type")
    data = block.get("data") or {}
    left = Inches(0.9)

    try:
        if btype in ("table", "comparison"):
            if btype == "table":
                headers = data.get("headers") or []
                rows = data.get("rows") or []
            else:
                criteria = data.get("criteria") or []
                items = data.get("items") or []
                headers = [""] + list(criteria)
                rows = [[it.get("name", "")] + list(it.get("values") or []) for it in items]
            if not headers or not rows:
                return 0.0
            rows = rows[:5]  # keep the whole grid on one slide
            n_cols = len(headers)
            col_w_in = width_in / n_cols
            row_h_in = 0.42
            y = top_in
            for c, h in enumerate(headers):
                if pastel:
                    # A different pastel per COLUMN instead of one solid
                    # accent header row — same "colourful, not one accent
                    # repeated" idea as the pastel bullet cards.
                    head_fill = _PLAYFUL_PALETTE[c % len(_PLAYFUL_PALETTE)]
                    head_text_color = _PLAYFUL_PALETTE_DARK[c % len(_PLAYFUL_PALETTE_DARK)]
                else:
                    head_fill, head_text_color = accent, _TEXT_WHITE
                _add_shape(slide, MSO_SHAPE.RECTANGLE, left + Inches(c * col_w_in), Inches(y), Inches(col_w_in), Inches(row_h_in), head_fill)
                _add_text(slide, left + Inches(c * col_w_in) + Inches(0.05), Inches(y + 0.06), Inches(col_w_in - 0.1), Inches(row_h_in - 0.1),
                          str(h), 11, True, head_text_color, PP_ALIGN.CENTER)
            y += row_h_in
            for r_i, row in enumerate(rows):
                if r_i % 2 == 0:
                    stripe = _PLAYFUL_PALETTE[(r_i + 1) % len(_PLAYFUL_PALETTE)] if pastel else accent_soft
                    _add_shape(slide, MSO_SHAPE.RECTANGLE, left, Inches(y), Inches(width_in), Inches(row_h_in), stripe)
                for c, cell in enumerate(list(row)[:n_cols]):
                    _add_text(slide, left + Inches(c * col_w_in) + Inches(0.05), Inches(y + 0.06), Inches(col_w_in - 0.1), Inches(row_h_in - 0.1),
                              str(cell), 10, c == 0 and btype == "comparison", ink, PP_ALIGN.CENTER)
                y += row_h_in
            return y - top_in

        elif btype == "process":
            steps = (data.get("steps") or [])[:6]
            if not steps:
                return 0.0
            # Set as CONSPECT NOTES, not as an infographic: a numbered
            # heading with its explanation underneath, one per line down
            # the slide.
            #
            # What this replaced: a generated PNG of coloured cards with
            # circled numbers and arrows between them
            # (timeline_builder.build_process_image). Two problems with
            # it. The layout broke — the cards were sized for a wide
            # horizontal strip, so three steps with real Tajik sentences
            # in them overflowed their boxes and collided with the
            # arrows. And it was an image: a teacher could not fix a typo
            # in it, and it scaled to whatever the strip's aspect ratio
            # dictated rather than to the text it held. Plain text on a
            # single grid has neither problem, and reads as the lesson
            # notes it actually is.
            text_x = left + Inches(_PROCESS_NUM_COL_IN)
            text_w_in = width_in - _PROCESS_NUM_COL_IN
            rows, total_h = _pptx_process_layout(steps, width_in)
            y = top_in
            for i, (step, (title_h, desc_h)) in enumerate(zip(steps, rows)):
                title = str((step or {}).get("title", "")).strip()
                desc = str((step or {}).get("description", "")).strip()
                if title:
                    # The number sits in its own fixed-width column so
                    # every heading starts on the same vertical line, no
                    # matter whether the number is 1 or 10.
                    _add_text(slide, left, Inches(y), Inches(_PROCESS_NUM_COL_IN),
                              Inches(title_h), f"{i + 1}.", _PROCESS_TITLE_PT, True, accent)
                    _add_text(slide, text_x, Inches(y), Inches(text_w_in),
                              Inches(title_h), title, _PROCESS_TITLE_PT, True, ink)
                    y += title_h
                if desc:
                    _add_text(slide, text_x, Inches(y), Inches(text_w_in),
                              Inches(desc_h), desc, _PROCESS_DESC_PT, False, _MUTED)
                    y += desc_h
                if i < len(steps) - 1:
                    y += _PROCESS_ITEM_GAP_IN
            return total_h

        elif btype == "chart":
            # A REAL PowerPoint chart object (python-pptx's chart API, an
            # embedded chart part), not a shape drawn to look like one — a
            # teacher can double-click it in PowerPoint afterward and edit
            # the underlying numbers like any normal Excel-backed chart.
            categories = [str(c) for c in (data.get("categories") or [])][:8]
            series_in = (data.get("series") or [])[:4]
            if not categories or not series_in:
                return 0.0
            chart_data = CategoryChartData()
            chart_data.categories = categories
            for s in series_in:
                raw_vals = list(s.get("values") or [])[:len(categories)]
                vals = []
                for v in raw_vals:
                    try:
                        vals.append(float(v))
                    except (TypeError, ValueError):
                        vals.append(0)
                vals += [0] * (len(categories) - len(vals))
                chart_data.add_series(str(s.get("name", "")), vals)

            chart_kind = str(data.get("chart_type") or "bar").lower()
            xl_type = {
                "bar": XL_CHART_TYPE.COLUMN_CLUSTERED,
                "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
                "pie": XL_CHART_TYPE.PIE,
                "line": XL_CHART_TYPE.LINE_MARKERS,
            }.get(chart_kind, XL_CHART_TYPE.COLUMN_CLUSTERED)

            chart_h_in = 3.0
            graphic_frame = slide.shapes.add_chart(xl_type, left, Inches(top_in), Inches(width_in), Inches(chart_h_in), chart_data)
            chart = graphic_frame.chart
            chart.has_title = False

            is_pie = chart_kind == "pie"
            chart.has_legend = is_pie or len(series_in) > 1
            if chart.has_legend:
                chart.legend.position = XL_LEGEND_POSITION.BOTTOM
                chart.legend.include_in_layout = False
                chart.legend.font.size = Pt(10)

            plot = chart.plots[0]
            plot.has_data_labels = True
            plot.data_labels.font.size = Pt(9)
            plot.data_labels.font.color.rgb = _TEXT_WHITE if is_pie else ink

            if is_pie:
                wedge_colors = _chart_color_shades(accent, len(categories))
                for i, point in enumerate(plot.series[0].points):
                    point.format.fill.solid()
                    point.format.fill.fore_color.rgb = wedge_colors[i]
            else:
                series_colors = _chart_color_shades(accent, len(series_in))
                for i, s in enumerate(plot.series):
                    s.format.fill.solid()
                    s.format.fill.fore_color.rgb = series_colors[i]
                    if chart_kind == "line":
                        s.format.line.color.rgb = series_colors[i]
                        s.format.line.width = Pt(2.25)
                chart.category_axis.tick_labels.font.size = Pt(10)
                chart.value_axis.tick_labels.font.size = Pt(10)
                chart.value_axis.has_major_gridlines = False

            return chart_h_in

        elif btype == "figure":
            # A figure_builder line drawing (see ai_service.py's
            # _render_slide_figures) — same box-fit-by-aspect-ratio
            # placement as the Commons photo layout above, just centred
            # under the slide's own content column instead of beside it,
            # since a figure slide keeps at most 1-2 lead-in bullets above
            # it rather than a full text column next to it.
            image_path = block.get("image")
            if not image_path:
                return 0.0
            full_path = os.path.join(os.path.dirname(__file__), "..", image_path.lstrip("/"))
            if not os.path.exists(full_path):
                return 0.0
            max_w_in, max_h_in = width_in, 3.6
            try:
                with PILImage.open(full_path) as im:
                    iw, ih = im.size
                scale = min(max_w_in / iw, max_h_in / ih)
                w_in, h_in = iw * scale, ih * scale
            except Exception:
                return 0.0
            slide.shapes.add_picture(full_path, left + Inches((width_in - w_in) / 2), Inches(top_in), Inches(w_in), Inches(h_in))
            used_h = h_in
            caption = str(block.get("caption") or "")
            if caption:
                _add_text(slide, left, Inches(top_in + h_in + 0.08), Inches(width_in), Inches(0.35),
                          caption, 11, False, _MUTED, PP_ALIGN.CENTER)
                used_h += 0.45
            return used_h
    except Exception:
        return 0.0
    return 0.0


# ── powers on the slides ────────────────────────────────────────────────
# The same problem the docx and PDF exports had: slide text is written as
# plain runs, so "S = a^2" reached the projector with the 2 on the
# baseline. PowerPoint raises a run with the "baseline" attribute — 30% of
# the type size up for a power, 25% down for an index — which is exactly
# the school-textbook superscript, in the slide's own font.

_PPTX_BASELINE = {"sup": "30000", "sub": "-25000"}

_A14_NS = "http://schemas.microsoft.com/office/drawing/2010/main"
_MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def _pptx_math_element(latex: str, template_run, fallback_pieces):
    """One formula as a NATIVE PowerPoint equation, with a text fallback.

    This is the shape PowerPoint itself writes when a teacher inserts an
    equation on a slide: the equation lives in <a14:m> inside an
    <mc:AlternateContent> whose <mc:Fallback> holds ordinary runs. So
    PowerPoint shows a real, editable, vector equation — a stacked
    fraction is a stacked fraction, and it stays sharp on a projector at
    any size — while a reader that does not implement the 2010 math
    extension (LibreOffice Impress, Google Slides) still shows the
    formula as readable text instead of nothing at all.

    Returns None if the formula cannot be built, and the caller then
    keeps the plain runs it already had."""
    import copy
    from lxml import etree
    from pptx.oxml.ns import qn as _pqn
    from app.math_render import to_omml

    try:
        omml = to_omml(latex)
        if not omml:
            return None
        math_el = etree.fromstring(omml)
    except Exception:
        return None

    try:
        alt = etree.SubElement(etree.Element("root"), f"{{{_MC_NS}}}AlternateContent",
                               nsmap={"mc": _MC_NS})
        choice = etree.SubElement(alt, f"{{{_MC_NS}}}Choice", nsmap={"a14": _A14_NS})
        choice.set("Requires", "a14")
        holder = etree.SubElement(choice, f"{{{_A14_NS}}}m")
        holder.append(math_el)

        fallback = etree.SubElement(alt, f"{{{_MC_NS}}}Fallback")
        for piece_text, kind in (fallback_pieces or [(latex, "")]):
            if not piece_text:
                continue
            run = copy.deepcopy(template_run)
            text_el = run.find(_pqn('a:t'))
            if text_el is None:
                continue
            text_el.text = piece_text
            if kind:
                rPr = run.find(_pqn('a:rPr'))
                if rPr is None:
                    rPr = run.makeelement(_pqn('a:rPr'), {})
                    run.insert(0, rPr)
                rPr.set('baseline', _PPTX_BASELINE[kind])
            fallback.append(run)
        if len(fallback) == 0:
            return None
        return alt
    except Exception:
        return None


def _pptx_math_runs(paragraph) -> None:
    """Rewrites one paragraph so its formulas are typeset.

    Two levels, both vector and both crisp on a projector:

      * a power or an index is a run with a raised baseline — plain
        DrawingML that every viewer honours;
      * anything a run cannot express (a stacked fraction, a radical, a
        sum) becomes a real PowerPoint equation object, with those same
        runs kept as the fallback — see _pptx_math_element. It used to be
        flattened to "(a+b)/2" on one line, which is not what a fraction
        looks like in a textbook."""
    import copy
    from pptx.oxml.ns import qn as _pqn
    from app.math_render import script_segments, is_literal_operator

    for run in list(paragraph.runs):
        text = run.text or ""
        normalized = _normalize_math(text)
        if "$" not in normalized:
            continue
        # Each entry is either ("text", kind) for a plain/scripted run, or
        # ("equation", latex, fallback_pieces) for a real equation object.
        pieces: list[tuple] = []
        pos = 0
        for m in _MATH_SPAN.finditer(normalized):
            prose = normalized[pos:m.start()]
            if prose:
                pieces.append(("text", prose, ""))
            latex = m.group(1)
            if is_literal_operator(latex):
                pieces.append(("text", latex, ""))
                pos = m.end()
                continue
            segments = script_segments(latex)
            if segments is None:
                pieces.append(("equation", latex, [(latex, "")]))
            elif any(kind for _, kind in segments):
                pieces.append(("equation", latex, segments))
            else:
                # No scripts and no structure: ordinary text already says
                # everything the formula says.
                pieces.extend(("text", t, k) for t, k in segments)
            pos = m.end()
        rest = normalized[pos:]
        if rest:
            pieces.append(("text", rest, ""))
        if not pieces:
            continue

        r = run._r
        parent = r.getparent()
        index = list(parent).index(r)
        offset = 0
        for piece in pieces:
            if piece[0] == "equation":
                node = _pptx_math_element(piece[1], r, piece[2])
                if node is None:
                    node = copy.deepcopy(r)
                    t = node.find(_pqn('a:t'))
                    if t is not None:
                        t.text = piece[1]
            else:
                node = copy.deepcopy(r)
                t = node.find(_pqn('a:t'))
                if t is None:
                    continue
                t.text = piece[1]
                if piece[2]:
                    rPr = node.find(_pqn('a:rPr'))
                    if rPr is None:
                        # A run whose formatting came from the paragraph
                        # has no <a:rPr> of its own; the raised baseline
                        # needs one, and it must be the run's first child.
                        rPr = node.makeelement(_pqn('a:rPr'), {})
                        node.insert(0, rPr)
                    rPr.set('baseline', _PPTX_BASELINE[piece[2]])
            parent.insert(index + offset, node)
            offset += 1
        parent.remove(r)


def _typeset_math_pptx(prs) -> None:
    """Raises every power on every slide. Never raises: a formula must not
    be able to fail an export."""
    for slide in prs.slides:
        for shape in slide.shapes:
            try:
                if not shape.has_text_frame:
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    _pptx_math_runs(paragraph)
            except Exception:
                continue        # that shape keeps its plain text


def build_presentation_pptx(content: dict) -> io.BytesIO:
    prs = Presentation()
    prs.slide_width = _SLIDE_W
    prs.slide_height = _SLIDE_H

    slides_data = content.get("slides", [])
    title_text = content.get("title", "")
    desc = content.get("description", "")

    total_slides = len(slides_data)

    # The deck's design comes from the template the teacher picked in the
    # wizard (see _DECK_THEMES). This replaced a single hardcoded look:
    # the five-way konspekt chooser was dropped here because it offered
    # five variations of one design under five names, which was friction
    # with no payoff — these four are visibly different decks and the
    # wizard previews each one, so the choice is made on the design
    # itself. Per-subject accent colour still applies on top of whichever
    # theme is chosen, so a Biology deck and a Physics deck stay
    # distinguishable within the same template.
    theme = resolve_deck_theme(content)
    # A subject template carries its own palette. The six legacy templates
    # never had one — they always drew in whatever accent the subject
    # happened to have — so they keep borrowing it from subject_theme.
    _accent_rgb = (_hex_tuple(theme["accent"]) if theme.get("accent")
                   else get_subject_accent_rgb(content.get("subject")))
    _ACCENT, _ACCENT_DARK, _ACCENT_SOFT = _pptx_accent_shades(_accent_rgb)
    # The motif's hue. Deliberately a SECOND colour, not another shade of
    # the accent: decoration drawn in the same hue as every rule and
    # marker reads as more of the same element rather than as background.
    _SUPPORT = _hex_rgb(theme["support"]) if theme.get("support") else _ACCENT_SOFT
    _DECOR = str(theme.get("decor") or "none")
    _CARD = str(theme.get("card") or ("rounded" if theme.get("cards") else "none"))
    _MARKER = str(theme.get("marker") or "number")
    _COVER = str(theme.get("cover") or "standard")
    title_font = theme["title_font"]
    _INK = theme["ink"]
    _MUTED = theme["muted"]
    _BG = theme["bg"]

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 1 — COVER: white background, big bold dark title + italic
    # accent-colored subtitle line, thin rule, small accent corner badge —
    # replacing the old full-bleed gradient cover (teacher feedback: the
    # colored-band look read as a generic "AI slide generator" template).
    # ══════════════════════════════════════════════════════════════════════
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, *_BG)
    if theme.get("spiral"):
        _pptx_notebook_lines(slide)
        _pptx_spiral_margin(slide)

    # How tall the title block is, worked out BEFORE anything is drawn.
    # Decoration has to be placed first (so it sits behind the text), but
    # it can only decide whether it fits once it knows how far down a long
    # title pushes the description — so the metrics are computed here and
    # consumed twice.
    _cover_w_in = 6.7 if len([1 for sd in slides_data if sd.get("title")]) >= 4 else 10.8
    # The size the title is ACTUALLY set in — the box used to be measured
    # at a hardcoded 40pt whatever the real size was, and the rule under
    # the title is positioned from that box. A long title wrapping to one
    # more line than the estimate expected put the rule straight through
    # the last line of the title (seen on a 3-line maths cover). Measuring
    # at the real size, and allowing for one extra line, fixes the cause
    # rather than nudging the rule down.
    _cover_pt_full = int(theme.get("cover_title_pt") or 46)
    _cover_title_pt = int(_cover_pt_full * 0.87) if _cover_w_in < 10 else _cover_pt_full
    _cover_line_in = _cover_title_pt * 1.22 / 72.0
    _cover_lines = _estimate_pptx_lines(title_text, _cover_w_in, _cover_title_pt)
    # PowerPoint's own wrapping is not this estimator's, and it errs
    # toward MORE lines (a real deck wrapped 2 estimated lines into 3).
    # A long title reserves the extra line rather than being overdrawn.
    if _cover_lines >= 2:
        _cover_lines += 1
    _cover_title_h = min(3.3, max(0.95, _cover_lines * _cover_line_in + 0.15))
    _rule_y_in = max(4.35, 2.4 + _cover_title_h + 0.18)

    # The subject's motif, drawn before any content so it always sits
    # behind it. The cover gets the motif at slightly more strength — it
    # is the slide the class looks at longest, and the one that has to
    # land "this is a chemistry lesson" before a word is read.
    slide_decor.draw(slide, _DECOR, _SUPPORT, _BG, 0, on_cover=True)
    # The cover composition lives in the lower-left quadrant — which is
    # also where the description ends up once a long title has pushed it
    # down. When that happens the composition is DROPPED, not moved: a
    # window frame drawn through the sentence a teacher is reading is
    # worse than a plainer cover. Content outranks decoration.
    if not (desc and _rule_y_in + 0.25 > 5.05):
        slide_decor.draw_cover(slide, _COVER, _ACCENT, _SUPPORT, _BG)

    # A soft-tinted corner blob used to draw here on "rangli" — pulled
    # back out per direct feedback ("shablonlar hunuk", every template
    # disliked, Google Slides named as the wanted look): a plain, clean
    # deck reads calmer and more professional on a classroom projector
    # than one with decorative shapes bleeding off the edges, which is
    # exactly why Slides/Docs-style decks don't use them either.

    _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(0.85), Inches(0.5), Pt(2.5), _ACCENT)
    _add_text(slide, Inches(1.6), Inches(0.72), Inches(6), Inches(0.35),
              "ПРЕЗЕНТАЦИЯ", 12, True, _ACCENT)

    # Small accent badge in the top-right corner — a subject/slide-count
    # tag instead of a decorative blob, echoing the reference's "SESSION
    # 2026" corner card.
    badge_w, badge_h = Inches(1.7), Inches(1.05)
    badge_x, badge_y = _SLIDE_W - badge_w - Inches(0.8), Inches(0.6)
    _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, badge_x, badge_y, badge_w, badge_h, _ACCENT)
    # +1 for the cover this badge is printed ON. `total_slides` counts
    # CONTENT slides, which is the right number for the "3 / 8" page
    # counter and the progress bar further down (neither of which counts
    # the cover as a step) — but as a headline figure on the cover it
    # undercounts by one against what the teacher sees: a deck whose
    # badge said "8 СЛАЙДОВ" opens in PowerPoint showing 9.
    _add_text(slide, badge_x, badge_y + Inches(0.16), badge_w, Inches(0.35), f"{total_slides + 1} СЛАЙДОВ", 11, True, _TEXT_WHITE, PP_ALIGN.CENTER)
    _add_text(slide, badge_x, badge_y + Inches(0.55), badge_w, Inches(0.4), "Dastyor", 15, True, _TEXT_WHITE, PP_ALIGN.CENTER)

    # A small subject illustration (openclipart.org, public domain — see
    # subject_theme.get_subject_illustration_path) in the gap between the
    # badge and the agenda box below it. Subjects with no matching image
    # (a custom/free-typed subject) simply skip this — an unrelated
    # picture would be worse than none.
    # …but only for the six legacy templates. A subject template carries
    # its own drawn motif and cover composition, and the openclipart PNGs
    # (a black flask, a black scroll, a cartoon pi) read as exactly the
    # "cheap school clipart" a designed deck is supposed to replace — they
    # were acceptable when the accent colour was the ONLY thing the
    # subject contributed, and are not now.
    _illustration_path = (None if theme.get("subject_template")
                          else get_subject_illustration_path(content.get("subject")))
    if _illustration_path:
        try:
            with PILImage.open(_illustration_path) as _im:
                _iw, _ih = _im.size
            _icon_box_in = 0.65
            _scale = min(_icon_box_in / _iw, _icon_box_in / _ih)
            _icon_w_in, _icon_h_in = _iw * _scale, _ih * _scale
            _icon_x = badge_x + (badge_w - Inches(_icon_w_in)) / 2
            _icon_y = badge_y + badge_h + Inches(0.1)
            slide.shapes.add_picture(_illustration_path, _icon_x, _icon_y, Inches(_icon_w_in), Inches(_icon_h_in))
        except Exception:
            pass

    # The title box is sized to the title it actually holds — it used to
    # be a fixed 2.4in (room for three lines) and a one-line title left
    # 1.6in of empty box lying over the subtitle beneath it.
    # The cover title's size is the template's — a serif face at 46pt
    # reads considerably larger than Arial does, so History and Literature
    # ask for less. Measured above, before the box was sized.
    _add_text(slide, Inches(0.95), Inches(2.4), Inches(_cover_w_in), Inches(_cover_title_h),
              title_text, _cover_title_pt, True, _INK, font_name=title_font)

    _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(_rule_y_in),
               Inches(0.9), Pt(3), _ACCENT)

    if desc:
        _add_text(slide, Inches(1.0), Inches(_rule_y_in + 0.25), Inches(_cover_w_in),
                  Inches(1.4), desc, 15, False, _MUTED)

    # What the lesson will cover, down the right-hand side. The cover used
    # to be a title, a subtitle and about half a slide of white — the one
    # slide the class looks at longest while the teacher introduces the
    # lesson. An agenda is what belongs in that space: it is the first
    # thing a teacher writes on the board anyway, and it fills the cover
    # with content instead of decoration.
    agenda = [str(sd.get("title") or "").strip()
              for sd in slides_data if str(sd.get("title") or "").strip()]
    if len(agenda) >= 4:
        plan_x_in, plan_top_in = 8.05, 2.45
        _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(plan_x_in), Inches(plan_top_in),
                   Pt(2.5), Inches(3.5), _ACCENT_SOFT)
        _add_text(slide, Inches(plan_x_in + 0.3), Inches(plan_top_in), Inches(4.0),
                  Inches(0.3), _DECK_AGENDA_LABEL.get(
                      str(content.get("language") or "Русский"), "В ЭТОМ УРОКЕ"),
                  10, True, _ACCENT)
        # Five at most, and the rest counted rather than listed: a
        # fourteen-line agenda in 9pt type is not a plan, it is a wall.
        y_in = plan_top_in + 0.42
        for n, item in enumerate(agenda[:5], 1):
            lines = _estimate_pptx_lines(item, 3.5, 12)
            _add_text(slide, Inches(plan_x_in + 0.3), Inches(y_in), Inches(0.35),
                      Inches(0.3), f"{n}", 12, True, _ACCENT)
            _add_text(slide, Inches(plan_x_in + 0.72), Inches(y_in), Inches(3.6),
                      Inches(lines * 0.24), item, 12, False, _INK)
            y_in += max(0.34, lines * 0.24 + 0.12)
        if len(agenda) > 5:
            _lang = str(content.get("language") or "Русский")
            _more_n = len(agenda) - 5
            more = _DECK_AGENDA_MORE.get(_lang, "ещё {n} {word}")
            _add_text(slide, Inches(plan_x_in + 0.72), Inches(y_in), Inches(3.6),
                      Inches(0.3),
                      more.format(n=_more_n, word=_agenda_more_word(_lang, _more_n)).strip(),
                      11, False, _MUTED)

    if theme.get("pastel"):
        _pptx_sticker_decorations(slide)

    _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(6.85), Inches(11.5), Pt(0.75), _HAIRLINE)
    _add_text(slide, Inches(1.0), Inches(7.0), Inches(9.3), Inches(0.4),
              f"{content.get('subject', '')}  ·  {content.get('grade', '')}".strip(" ·"),
              11, False, _MUTED)

    _add_logo_badge(slide, on_dark_bg=False)
    _add_transition(slide)

    # ══════════════════════════════════════════════════════════════════════
    # CONTENT SLIDES — a full-width gradient header band (title + rotating
    # icon badge live inside it) instead of a plain white header, numbered
    # accent chips instead of plain bullet ticks, logo badge in the corner,
    # and a fade transition. Notes still go to the real PowerPoint notes pane.
    # ══════════════════════════════════════════════════════════════════════
    def _name_slide(slide, layout_name):
        """Record which composition drew this slide, in the slide's own
        OOXML name.

        Two reasons, both practical. PowerPoint shows it in the outline
        pane, so a teacher reporting "this slide looks wrong" can say
        which KIND of slide it was. And the test suite reads it back to
        check a deck actually varies its compositions — the requirement
        that a deck stop being ten copies of one layout is otherwise only
        checkable by eye, which means it would quietly regress."""
        try:
            slide._element.cSld.set("name", str(layout_name))
        except Exception:
            pass

    def _finish_slide(slide, i, notes):
        """Everything every content slide ends with, whichever composition
        drew its body. Factored out when the layout engine arrived: the
        engine returns having drawn only the body, and both paths have to
        close the slide identically or the progress bar starts skipping
        slides."""
        # Speaker notes live in the real PowerPoint notes pane (View ▸ Notes)
        # instead of a visible box, so the slide itself stays uncluttered.
        if notes:
            slide.notes_slide.notes_text_frame.text = notes

        # A slim reading-progress bar instead of a plain static hairline —
        # same footprint, but the filled portion (how far into the deck
        # this slide is) gives every slide a small, deliberate touch of
        # color instead of a flat gray line, and doubles as wayfinding.
        footer_w_in = _CONTENT_W_IN
        _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(7.1), Inches(footer_w_in), Pt(2.25), _HAIRLINE)
        progress_w_in = footer_w_in * (i + 1) / total_slides
        if progress_w_in > 0.05:
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(7.1), Inches(progress_w_in), Pt(2.25), _ACCENT)

        _add_logo_badge(slide, on_dark_bg=False)
        _add_transition(slide)

    _grade_tier = slide_layouts.grade_tier(content.get("grade"))
    _char_prop = slide_characters.prop_for(str(theme.get("subject_template") or ""))
    # The figure is drawn in the accent, so its prop needs a colour that
    # reads AGAINST the accent rather than another tint of it.
    _PROP_COLOR = (_hex_rgb(theme["prop_color"]) if theme.get("prop_color")
                   else _ACCENT_DARK)
    _last_layout: str | None = None

    for i, sd in enumerate(slides_data):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _set_slide_bg(slide, *_BG)
        if theme.get("spiral"):
            _pptx_notebook_lines(slide)
            _pptx_spiral_margin(slide)
            _pptx_washi_tape(slide, 0.75, 0.1, _PLAYFUL_PALETTE[i % len(_PLAYFUL_PALETTE)])
        slide_decor.draw(slide, _DECOR, _SUPPORT, _BG, i)

        title_str = sd.get("title", f"Слайд {i + 1}")

        # header_style drives how the header reads, not just its color —
        # "underline"/"smallcaps" (zamonaviy/minimal) deliberately drop the
        # full gradient band for a quieter, more modern/minimal header,
        # while "numbered"/"bar"/"serif" keep the original full-bleed band
        # (serif only swaps the title font). Scoped to what's cheap to
        # express with the shape helpers already in this file rather than
        # 5 bespoke layouts.
        # One fixed header for every content slide: white background,
        # big bold dark title, thin accent rule, small page counter, and a
        # small accent-tinted icon badge in the corner — no more full-
        # bleed colored band (see build_presentation_pptx's docstring-ish
        # comment above the cover slide for why: it read as generic "AI
        # slide generator" chrome once there was only ever one template).
        # The header is where the four templates differ most, so it is
        # built per theme rather than once: a rule under the title, a
        # full-width hairline, a filled accent band with the title
        # reversed out of it, or nothing but the type itself.
        band_h_in = 1.15
        header_style = theme["header"]
        title_ink = _TEXT_WHITE if header_style == "band" else _INK
        counter_ink = _TEXT_WHITE if header_style == "band" else _MUTED

        # Anything that has to sit BEHIND the title is drawn first.
        if header_style == "band":
            _add_shape(slide, MSO_SHAPE.RECTANGLE, 0, 0, _SLIDE_W, Inches(1.5), _ACCENT)
        elif header_style == "hexband":
            # A thin rule across the very top plus a hexagon standing in
            # for the bullet before the slide number — chemistry's shape,
            # used as furniture rather than as decoration.
            _add_shape(slide, MSO_SHAPE.RECTANGLE, 0, 0, _SLIDE_W, Inches(0.1), _ACCENT)
            _add_shape(slide, MSO_SHAPE.HEXAGON, Inches(0.62), Inches(0.37),
                       Inches(0.2), Inches(0.2), _ACCENT)
        elif header_style == "index":
            # A hard vertical rule to the left of the whole header block:
            # maths sets its headings against a margin, not on a band.
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.66), Inches(0.33),
                       Pt(3), Inches(0.95), _ACCENT)
        elif header_style == "lozenge":
            _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.72), Inches(0.33),
                       Inches(0.62), Inches(0.3), _ACCENT_SOFT)
        elif header_style == "initial":
            # The hanging bar a printed page uses to mark a new section.
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(0.58),
                       Pt(5), Inches(0.78), _ACCENT)

        _number_x = 0.9 if header_style not in ("prompt",) else 1.12
        if header_style == "prompt":
            # An editor's prompt mark. Informatics is the one subject
            # whose own visual language is literally typography.
            _add_text(slide, Inches(0.86), Inches(0.33), Inches(0.3), Inches(0.3),
                      ">", 14, True, _ACCENT, font_name="Consolas")
        _add_text(slide, Inches(_number_x), Inches(0.35), Inches(8.6), Inches(0.3),
                  f"{i + 1:02d}", 13, True,
                  _TEXT_WHITE if header_style == "band" else _ACCENT)
        # What kind of moment this slide is, in the teacher's language.
        # Small, beside the number — it costs nothing and it is the
        # cheapest possible signal that the deck has a structure.
        _kind_text = _kind_label(str(sd.get("kind") or "").strip().lower(),
                                 content.get("language"))
        if _kind_text:
            _add_text(slide, Inches(_number_x + 0.45), Inches(0.37), Inches(4.2), Inches(0.3),
                      f"· {_kind_text}", 10, True,
                      _TEXT_WHITE if header_style == "band" else _MUTED)
        _add_text(slide, Inches(0.9), Inches(0.62), Inches(9.6), Inches(0.7),
                  title_str.upper() if theme["title_caps"] else title_str,
                  int(theme.get("title_pt") or (24 if theme["title_caps"] else 27)),
                  True, title_ink, font_name=title_font)

        # …and everything that sits under it.
        if header_style == "rule":
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.32), Inches(1.1), Pt(3), _ACCENT)
        elif header_style == "underline":
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.36), Inches(11.5), Pt(1.25), _HAIRLINE)
        elif header_style == "index":
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.34), Inches(2.2), Pt(1.5), _ACCENT_SOFT)
        elif header_style == "measure":
            # A ruler: one hairline with graduations along it. Physics is
            # the subject where every quantity is a measurement.
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.36), Inches(11.5), Pt(1.25), _HAIRLINE)
            for _t in range(12):
                _tall = _t % 4 == 0
                _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9 + _t * (11.5 / 12)),
                           Inches(1.36 - (0.09 if _tall else 0.05)), Pt(1.25),
                           Inches(0.09 if _tall else 0.05),
                           _ACCENT if _tall else _HAIRLINE)
        elif header_style == "hexband":
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.34), Inches(1.6), Pt(2.5), _ACCENT)
        elif header_style == "lozenge":
            _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(1.3),
                       Inches(1.5), Pt(5), _ACCENT)
        elif header_style == "masthead":
            # Thick over thin — the double rule a printed masthead uses.
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.3), Inches(11.5), Pt(2.5), _ACCENT)
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.4), Inches(11.5), Pt(0.75), _ACCENT_SOFT)
        elif header_style == "prompt":
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.36), Inches(11.5), Pt(1.25), _HAIRLINE)
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.33), Inches(0.75), Pt(2.5), _ACCENT)
        elif header_style == "ornamental":
            # A printer's rule: a hairline with a diamond set into it.
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.37), Inches(4.6), Pt(1), _ACCENT_SOFT)
            for _d in range(3):
                _add_shape(slide, MSO_SHAPE.DIAMOND, Inches(4.75 + _d * 0.22), Inches(1.31),
                           Inches(0.11), Inches(0.11), _ACCENT if _d == 1 else _ACCENT_SOFT)
        _add_text(slide, Inches(9.9), Inches(0.35), Inches(1.7), Inches(0.3),
                  f"{i + 1} / {total_slides}", 10, False, counter_ink, PP_ALIGN.RIGHT)
        # A soft accent-tinted disc behind the icon — without it the icon
        # shape floats bare in the corner, reading as a stray/unfinished
        # graphic rather than a deliberate badge. Themes that are meant to
        # be quiet (klassik, minimal) drop it entirely.
        if theme["badge"] and header_style != "band":
            badge_d = Inches(0.6)
            badge_cx, badge_cy = Inches(12.15), Inches(0.65)
            _add_shape(slide, MSO_SHAPE.OVAL, badge_cx - badge_d / 2, badge_cy - badge_d / 2, badge_d, badge_d, _ACCENT_SOFT)
            icon_d = badge_d * 0.42
            _marker_glyph = _MARKER_GLYPH_SHAPE.get(_MARKER)
            if theme.get("pastel"):
                _corner_shape = _PLAYFUL_ICON_SHAPES[i % len(_PLAYFUL_ICON_SHAPES)]
            elif _marker_glyph is not None:
                # The subject's own mark rather than a rotating list of
                # generic ones — a lightning bolt in the corner of a
                # geography slide said nothing about geography.
                _corner_shape = _marker_glyph
            else:
                _corner_shape = _ICON_SHAPES[i % len(_ICON_SHAPES)]
            _add_shape(slide, _corner_shape, badge_cx - icon_d / 2, badge_cy - icon_d / 2, icon_d, icon_d, _ACCENT)

        bullets = sd.get("bullet_points", [])
        notes = sd.get("speaker_notes", "")
        visual = sd.get("visual")

        # ── which LAYOUT this slide gets ───────────────────────────────
        # A deck built from one repeated layout reads as a form someone
        # filled in. These three are chosen from the slide's own content,
        # so the shape of the slide tells the class what kind of moment it
        # is: a figure to look at, an equation to read, or a task to do.
        slide_kind = str(sd.get("kind") or "").strip().lower()
        slide_image = sd.get("image") if isinstance(sd.get("image"), dict) else None
        image_path = None
        if slide_image and slide_image.get("path"):
            candidate = os.path.join(os.path.dirname(__file__), "..",
                                     str(slide_image["path"]).lstrip("/"))
            if os.path.exists(candidate):
                image_path = candidate
        # ── the composition engine ─────────────────────────────────────
        # Before this, every content slide was the same skeleton: header,
        # a grid of bullet cards, a grey paragraph. The subject changed
        # the palette and the motif, but a deck of ten slides was ten
        # copies of one layout — which is what makes two subjects read as
        # one template recoloured however different the decoration is.
        #
        # slide_layouts picks a composition from the slide's own content:
        # a slide naming the parts of something becomes a central object
        # with the parts around it; a sequence becomes a flow; a picture
        # gets half the slide bled to the edge instead of a box beside a
        # list. See app/slide_layouts.py.
        #
        # Scoped to subject templates on purpose. The six legacy themes
        # are a teacher's explicit request for a plain deck — "google" in
        # particular exists BECAUSE someone asked for Google-Slides-plain
        # — and handing them varied compositions would override a choice
        # rather than serve it.
        #
        # Slides carrying a table/chart/process block, or an equation,
        # keep the paths built for them: those already are their own
        # composition and are tuned for overflow in ways this engine
        # would have to re-derive.
        _layout_used = None
        if (theme.get("subject_template") and not visual
                and (bullets or str(sd.get("body") or "").strip())
                and str(sd.get("kind") or "").strip().lower() != "formula"):
            _ctx = slide_layouts.Ctx(
                slide=slide, accent=_ACCENT, accent_dark=_ACCENT_DARK,
                accent_soft=_ACCENT_SOFT, support=_SUPPORT, ink=_INK,
                muted=_MUTED, bg=_BG, title_font=title_font,
                body_font=theme["body_font"],
                template_id=str(theme.get("subject_template") or ""),
                grade_tier=_grade_tier,
                language=str(content.get("language") or "Русский"),
                index=i, total=total_slides, image_path=image_path,
                image_credit=str((slide_image or {}).get("credit") or ""),
                character_prop=_char_prop, prop_color=_PROP_COLOR,
                topic=str(content.get("title") or ""),
            )
            _layout_used = slide_layouts.draw(_ctx, sd, _last_layout)
        if _layout_used:
            _last_layout = _layout_used
            _name_slide(slide, _layout_used)
            _finish_slide(slide, i, notes)
            continue

        # A picture always wins over the formula layout: the two used to
        # be able to claim the same slide at once (kind="formula" AND a
        # fetched image), and then the formula panel drew full width
        # while the paragraph was still positioned for the picture's
        # narrow column — the two texts landed on top of each other. The
        # equation still typesets properly inside the bullets of the
        # picture layout, so nothing is lost by letting the picture win.
        is_formula_slide = not image_path and (
            slide_kind == "formula" or (
                bool(bullets) and not visual
                and sum(1 for b in bullets if "$" in str(b)) >= max(1, len(bullets) - 1)))
        # Which side the picture sits on alternates down the deck, so two
        # picture slides in a row are not the same slide twice.
        image_on_right = (i % 2 == 0)

        bullet_width_in = 5.35 if image_path else _CONTENT_W_IN
        bullet_width = Inches(bullet_width_in)
        # Bumped from 18: the prompt now caps bullets at 2-5 word fragments
        # (was 4-9) precisely so the slide has room to set them bigger and
        # bolder instead of cramming more small text in — fewer words,
        # printed with more visual weight, is what "less text, still looks
        # premium" actually means on a slide.
        bullet_font = 20

        # A text-only slide (no "visual" block) renders its bullets as a
        # 2-column grid of icon+text cards instead of one skinny column of
        # lines — a plain left-aligned list used to leave the entire right
        # half of the slide dead white space (this is what a teacher
        # circled in feedback: "text-lar juda hunuk, grafichiskiy
        # materials qo'sh"). ANY bullets get the icon-card treatment now —
        # including the 1-2 short lead-in bullets on a slide that ALSO has
        # a table/process/comparison/chart "visual" below them — per
        # direct follow-up feedback ("har bir lista grafichiskiy material
        # yasab qoysin", repeated more than once): every single bullet
        # anywhere in the deck should carry a graphical anchor, not just
        # the bullets on visual-less slides. The old plain single-line
        # list (a bare outlined-ring number + text, no card) is now fully
        # retired — it used to be the fallback for <2 bullets or any
        # visual-slide lead-in, both of which read as "just text" next to
        # every other slide's cards.
        # Beside a picture the bullets are a single narrow column, not a
        # 2-across card grid — two cards in a 5-inch half come out as
        # slivers of text.
        # klassik/minimal set their bullets as plain typographic lines
        # rather than tinted cards — that restraint IS their design.
        use_grid = (theme["cards"] and len(bullets) >= 1
                    and not image_path and not is_formula_slide)
        available_top_in = band_h_in + 0.5
        available_h_in = 7.0 - available_top_in

        if use_grid:
            grid_row_gap_in = 0.35  # must match _pptx_bullet_grid's own row_gap_in
            natural_row_heights = _pptx_bullet_grid_natural_heights(bullets, (bullet_width_in - 0.3) / 2, kind=slide_kind)
            n_rows = len(natural_row_heights)
            # A modest, FIXED comfortable size per row — not stretched to
            # fill whatever vertical space happens to be available. That
            # was tried and made a 2-3-word bullet balloon into an
            # obviously-empty giant rounded box, which read as worse than
            # the original problem, not a fix — a teacher can immediately
            # tell a mostly-empty box was padded out. A modestly-sized
            # card plus the page's normal centering (below) reads as a
            # deliberate compact layout instead; any leftover space is
            # shared margin around the whole block, not stuffed into
            # individual cards.
            row_heights = [min(1.7, max(h, 1.15)) for h in natural_row_heights]
            grid_h = sum(row_heights) + grid_row_gap_in * max(0, n_rows - 1)
        else:
            # Row height is estimated per-bullet from its actual text length
            # instead of a fixed increment — a short bullet and a 4-line
            # detailed one no longer get the same spacing (which used to make
            # long bullets visually collide with the next chip/number).
            line_h_in = bullet_font * 1.32 / 72.0
            bullet_gap_in = 0.22  # breathing room between successive bullets
            chip = Inches(0.42)
            row_heights = [max(0.55, _estimate_pptx_lines(bp, bullet_width_in, bullet_font) * line_h_in + 0.24) for bp in bullets]
            grid_h = sum(row_heights) + bullet_gap_in * max(0, len(bullets) - 1)

        # The slide's explanatory paragraph (see the "body" prompt rule) —
        # what a pupil reads to actually learn the point, and what lets a
        # substitute teacher teach from the deck. Space for it is reserved
        # here so the block below still centres correctly.
        body_text = re.sub(r"\s+", " ", str(sd.get("body") or "")).strip()
        body_font = 15
        body_width_in = bullet_width_in
        # Set by whichever layout branch actually runs; None means "the
        # column this slide's bullets already use".
        body_x_override = None
        body_h_in = 0.0
        if body_text:
            body_h_in = (_estimate_pptx_lines(body_text, body_width_in - 0.2, body_font)
                         * body_font * 1.38 / 72.0) + 0.30

        content_h = grid_h + (body_h_in + 0.28 if body_h_in else 0.0)
        visual_gap_in = 0.35 if bullets and visual else 0.0
        if visual:
            content_h += visual_gap_in + _estimate_pptx_visual_height(visual)

        # The paragraph must never push a table, a chart or a picture off
        # the bottom of the slide: it is the flexible part of the layout,
        # so when the slide is full IT gives way. Only the BUDGET is
        # trimmed here, for the centring calculation below — what the
        # paragraph actually does (shrink, or step aside) is decided once
        # the layout branch has run and the real cursor is known, since
        # the picture and formula layouts move it themselves. Deciding it
        # twice is how a paragraph ended up cut on a slide that had room
        # for it.
        max_bottom_in = 6.9
        overflow_in = (available_top_in + content_h) - max_bottom_in
        if overflow_in > 0 and body_h_in:
            content_h -= min(overflow_in, body_h_in + 0.28)

        # A slide with only 1-2 short bullets (or a small table) used to
        # hug the header and leave the whole bottom half of the slide dead
        # white space — this centers the actual content block in the space
        # between the header and the footer hairline instead, capped so a
        # near-empty slide doesn't push its one bullet awkwardly far down.
        # The cap was 1.4in until a real deck showed what that looks like
        # on a genuinely light slide (3 short cards + a 2-line paragraph):
        # nearly 1.4in of dead air above AND below the content block, on
        # a slide that otherwise looks unfinished rather than "centered".
        # 0.85 still lifts a lonely bullet off the header without
        # recreating that half-empty look.
        # ...but that 0.85 was tuned for a slide whose content IS bullet
        # cards. A slide carrying a paragraph and a visual and NO bullets
        # (which is what a "visual" slide became once bullets that merely
        # repeated the visual started being dropped — see ai_service's
        # _drop_bullets_duplicating_visual) has a taller, denser block, so
        # capping it at 0.85 leaves the bottom third of the slide empty
        # instead of reading as centred. Those get the full centring.
        _offset_cap = 0.85 if bullets else 1.8
        offset_in = min(_offset_cap, max(0.0, (available_h_in - content_h) / 2))
        cursor = available_top_in + offset_in

        # ── layout: the opening slide reads as prose, not as a list ────
        # An "intro" slide's job is to say what the lesson is about, so
        # its paragraph LEADS — set larger, full width, above the bullets
        # — instead of being the small grey footnote under them that every
        # other slide's paragraph is. Same two elements, opposite
        # emphasis, and that is what makes slide 2 of a deck not look like
        # slide 5.
        #
        # Only when the slide is otherwise plain: a picture, an equation
        # or a table already gives that slide its own shape, and stacking
        # a lead paragraph on top of one of those is how the bottom of a
        # slide gets pushed off the edge.
        if (slide_kind == "intro" and body_text and bullets
                and not image_path and not is_formula_slide and not visual):
            lead_pt = 17
            lead_h_in = (_estimate_pptx_lines(body_text, _CONTENT_W_IN - 0.4, lead_pt)
                         * lead_pt * 1.42 / 72.0) + 0.12
            # Only if the bullets still fit underneath it afterwards.
            if cursor + lead_h_in + 0.34 + grid_h <= 6.9:
                _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(_CONTENT_X_IN),
                           Inches(cursor + 0.04), Pt(4), Inches(max(0.3, lead_h_in - 0.1)),
                           _ACCENT)
                _add_text(slide, Inches(_CONTENT_X_IN + 0.24), Inches(cursor),
                          Inches(_CONTENT_W_IN - 0.4), Inches(lead_h_in),
                          body_text, lead_pt, False, _INK,
                          font_name=theme["body_font"])
                cursor += lead_h_in + 0.34
                # Consumed here — the paragraph must not also print in its
                # usual place under the bullets further down.
                body_text, body_h_in = "", 0.0

        # ── layout: the equation is the slide ──────────────────────────
        # Its own layout rather than a bullet card: the class is meant to
        # read one expression, so it is set large, centred and alone, with
        # any remaining bullet under it as the reading of it. The $...$
        # becomes a real PowerPoint equation in _typeset_math_pptx.
        if is_formula_slide and bullets:
            formula_text = next((str(b) for b in bullets if "$" in str(b)), str(bullets[0]))
            rest = [str(b) for b in bullets if str(b) != formula_text]
            # The panel used to be a fixed 1.9" holding fixed 32pt type,
            # so a long equation — a chemical reaction with its conditions
            # is the usual one — wrapped onto three lines and spilled out
            # of the bottom of its own card. The equation is measured
            # first: it is set smaller when it is long, and the card is
            # grown to whatever the wrapped result actually needs.
            from app.math_render import measure as _measure
            latex_src = formula_text.strip().strip("$").strip()
            avail_pt = 9.5 * 72
            f_size = 32
            width_pt = _measure(latex_src, f_size)[0]
            if width_pt > avail_pt:
                f_size = max(18, int(f_size * avail_pt / width_pt))
                width_pt = _measure(latex_src, f_size)[0]
            f_lines = max(1, math.ceil(width_pt / avail_pt)) if width_pt else 1
            text_h_in = f_lines * (f_size * 1.5 / 72)
            panel_h_in = max(1.6, text_h_in + 0.7)
            panel_top = Inches(available_top_in + 0.35)
            _add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.6), panel_top,
                       Inches(10.1), Inches(panel_h_in), _ACCENT_SOFT)
            _add_text(slide, Inches(1.9),
                      panel_top + Inches((panel_h_in - text_h_in) / 2),
                      Inches(9.5), Inches(text_h_in),
                      formula_text, f_size, True, _ACCENT_DARK, PP_ALIGN.CENTER)
            below = available_top_in + 0.35 + panel_h_in + 0.45
            for line in rest[:2]:
                _add_text(slide, Inches(1.9), Inches(below), Inches(9.5), Inches(0.5),
                          line, 18, False, _MUTED, PP_ALIGN.CENTER)
                below += 0.55
            # The cursor has to follow the panel down, or whatever is
            # drawn next (the paragraph) starts back up at the block's
            # centred position and lands on top of the equation.
            cursor = below
            # This layout owns the full width, so the paragraph below it
            # must not stay in the narrow column another layout set.
            body_width_in = 9.5
            body_x_override = 1.9

        # ── layout: a figure beside the text ───────────────────────────
        elif image_path:
            img_w_in, img_area_h_in = 5.9, 4.4
            text_x_in = 0.9 if image_on_right else 7.05
            img_x_in = 6.75 if image_on_right else 0.75
            try:
                with PILImage.open(image_path) as im:
                    iw, ih = im.size
                scale = min(img_w_in / iw, img_area_h_in / ih)
                tw, th = iw * scale, ih * scale
            except Exception:
                tw, th = img_w_in, img_area_h_in * 0.7
            img_top_in = available_top_in + max(0.0, (img_area_h_in - th) / 2)
            slide.shapes.add_picture(image_path, Inches(img_x_in + (img_w_in - tw) / 2),
                                     Inches(img_top_in), Inches(tw), Inches(th))
            # Commons licences require the author and licence to travel
            # with the picture — printed small, under it.
            credit = str(slide_image.get("credit") or "")
            if credit:
                _add_text(slide, Inches(img_x_in), Inches(img_top_in + th + 0.12),
                          Inches(img_w_in), Inches(0.3), credit, 9, False, _MUTED, PP_ALIGN.CENTER)
            # Each bullet's box is exactly as tall as its own wrapped
            # text, and the next one starts below THAT. The box used to
            # be a fixed 0.9in while the cursor advanced by ~0.64in, so
            # consecutive bullets overlapped by a quarter inch — invisible
            # for one-line bullets, a collision the moment one wrapped.
            bullet_pt, bullet_gap_in = 19, 0.18
            by = available_top_in + 0.15
            for bp in bullets[:4]:
                lines = _estimate_pptx_lines(str(bp), bullet_width_in - 0.3, bullet_pt)
                row_h_in = lines * bullet_pt * 1.32 / 72.0 + 0.14
                _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(text_x_in), Inches(by + 0.08),
                           Pt(3), Inches(max(0.22, row_h_in - 0.16)), _ACCENT)
                _add_text(slide, Inches(text_x_in + 0.22), Inches(by), Inches(bullet_width_in - 0.3),
                          Inches(row_h_in), str(bp), bullet_pt, False, _INK)
                by += row_h_in + bullet_gap_in
            # The paragraph continues down the TEXT column, beside the
            # picture — not below it. Anchoring to the picture's bottom
            # left barely a third of an inch of slide, so the paragraph
            # was dropped entirely and the slide lost its explanation.
            cursor = by - bullet_gap_in

        elif use_grid:
            # example/task/summary slides get a backdrop behind the whole
            # block — drawn first so the cards sit on top of it. Same
            # footprint, so the centring and overflow maths above is
            # unaffected; only how the slide READS changes.
            _panel_style = _KIND_PANEL.get(slide_kind)
            if _panel_style:
                _draw_kind_panel(slide, _panel_style, cursor, grid_h, _ACCENT, _ACCENT_SOFT)
            _pptx_bullet_grid(slide, cursor, bullets, row_heights, _ACCENT, _ACCENT_SOFT, _INK, pastel=bool(theme.get("pastel")), card=_CARD, marker=_MARKER, kind=slide_kind)
            cursor += grid_h  # grid_h already excludes any trailing gap — see the (n_rows-1) factor above
        else:
            for j, bp in enumerate(bullets):
                by = cursor
                row_h = row_heights[j]

                # A thin outlined ring with the accent-colored number inside,
                # instead of a solid filled square — a filled block of color
                # next to every single line reads as a corporate-template
                # "checkbox list" at a glance; an outline badge is the same
                # wayfinding cue with far less visual weight, closer to what an
                # actual designer would ship for a body slide read line by line.
                _marker_text = _marker_label(_MARKER, j + 1)
                _add_shape(slide, _MARKER_BADGE_SHAPE.get(_MARKER, MSO_SHAPE.OVAL),
                           Inches(0.9), Inches(by), chip, chip, _TEXT_WHITE,
                           line_rgb=_ACCENT, line_width=Pt(1.5))
                _add_text(slide, Inches(0.9), Inches(by) + Emu(int(chip * 0.14)), chip, chip,
                          _marker_text, 13 if len(_marker_text) <= 2 else 10, True,
                          _ACCENT, PP_ALIGN.CENTER)

                # Box height = the row's own height, not row_h + 0.3: the
                # cursor advances by row_h + the gap, so an over-tall box
                # reached into the next bullet's line. Invisible while
                # every bullet was one line, a collision as soon as one
                # wrapped — which is exactly what klassik/minimal do,
                # since they set bullets as plain lines rather than cards.
                _add_text(slide, Inches(1.55), Inches(by - 0.07), bullet_width, Inches(row_h),
                          bp, bullet_font, False, _INK)
                cursor += row_h + bullet_gap_in
            # The loop above adds one trailing bullet_gap_in that grid_h's
            # formula doesn't have (grid_h uses n-1 gaps, not n) — cancel it
            # back out so both branches leave `cursor` at the same place:
            # exactly grid_h past their own start, regardless of which
            # branch ran. Only matters when there IS a next block (the
            # visual) to position from here.
            if bullets:
                cursor -= bullet_gap_in

        # The explanatory paragraph, under the bullets it belongs to. Set
        # smaller and in the muted ink so the slide still reads as
        # headline-then-detail rather than a page of prose, with a short
        # accent rule marking where the explanation starts.
        # The authoritative fit check, made against the cursor the layout
        # actually reached — the estimate above centres the block, but the
        # picture and formula layouts move the cursor themselves, so only
        # here is the real remaining room known.
        if body_text:
            reserved_in = (visual_gap_in + _estimate_pptx_visual_height(visual)) if visual else 0.0
            room_in = 6.9 - (cursor + 0.28) - reserved_in
            # Shrink the type before cutting the sentence. A paragraph
            # that stops mid-thought on "…" is a worse slide than the
            # same paragraph a point or two smaller, and the sizes below
            # are all still readable from the back of a classroom.
            for candidate_pt in (15, 14, 13, 12, 11):
                line_in = candidate_pt * 1.38 / 72.0
                needed = (_estimate_pptx_lines(body_text, body_width_in - 0.2, candidate_pt)
                          * line_in) + 0.30
                if needed <= room_in:
                    body_font, body_h_in = candidate_pt, needed
                    break
            else:
                if visual:
                    # The slide already carries a table/chart/notes block,
                    # so its content is not lost: drop the paragraph
                    # rather than print a sentence that stops mid-thought.
                    # The full text is in the speaker notes either way.
                    body_text, body_h_in = "", 0.0
                else:
                    # Nothing else on the slide carries this content, so a
                    # trimmed paragraph beats no paragraph — cut at a
                    # whole word, and only if two lines survive.
                    body_font = 11
                    line_in = body_font * 1.38 / 72.0
                    fit_lines = int((room_in - 0.30) / line_in) if room_in > 0 else 0
                    if fit_lines < 2:
                        body_text, body_h_in = "", 0.0
                    else:
                        body_text = _trim_text_to_lines(body_text, body_width_in - 0.2,
                                                        body_font, fit_lines)
                        body_h_in = fit_lines * line_in + 0.30

        _name_slide(slide, "formula" if is_formula_slide
                    else "picture" if image_path
                    else "visual" if visual
                    else "cards")

        if body_text:
            body_x_in = (body_x_override if body_x_override is not None
                         else (0.9 if (not image_path or image_on_right) else 7.05))
            cursor += 0.28
            _add_shape(slide, MSO_SHAPE.RECTANGLE, Inches(body_x_in), Inches(cursor + 0.06),
                       Pt(2.5), Inches(max(0.3, body_h_in - 0.24)), _ACCENT_SOFT)
            _add_text(slide, Inches(body_x_in + 0.18), Inches(cursor), Inches(body_width_in - 0.2),
                      Inches(body_h_in), body_text, body_font, False, _MUTED,
                      font_name=theme["body_font"])
            cursor += body_h_in

        # Optional per-slide graphic — see _pptx_visual_block; drawn below
        # whatever short lead-in bullets this slide has.
        if visual:
            if bullets:
                cursor += visual_gap_in
            # Pulled back up when tall bullets have pushed it too low:
            # a chart or table whose own height runs past the slide edge
            # is simply cut off in PowerPoint. Predates the body
            # paragraph — measured on a deck built without one.
            visual_h_in = _estimate_pptx_visual_height(visual)
            cursor = max(available_top_in, min(cursor, 6.95 - visual_h_in))
            _pptx_visual_block(slide, cursor, bullet_width_in, visual, _ACCENT, _ACCENT_SOFT, _INK, pastel=bool(theme.get("pastel")))

        _finish_slide(slide, i, notes)

    # No trailing "Спасибо!" slide — a teacher presenting to a class ends on
    # their own last content slide (or their own wrap-up), not a generic
    # branded thank-you card tacked on by the export tool.

    buf = io.BytesIO()
    _typeset_math_pptx(prs)
    prs.save(buf)
    buf.seek(0)
    return buf


# ── PDF Builder ─────────────────────────────────────────────────────────────

from reportlab.platypus import HRFlowable, Image as _PdfFlowableImage
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Image as _PdfImage
from reportlab.graphics import renderPDF


_PDF_ACCENT = '#3B82F6'
_PDF_DARK = '#1E293B'
_PDF_LIGHT = '#F1F5F9'
_PDF_GREEN = '#10B981'
_PDF_ORANGE = '#F59E0B'
_PDF_RED = '#EF4444'
_PDF_PURPLE = '#8B5CF6'

# _PDF_BRAND stays red — it's what marks an exam/test day's heading bar in
# the combined curriculum PDF (build_curriculum_pdf), deliberately
# contrasting against the blue lesson-day headings. The presentation deck
# itself now uses the same blue family as every other export instead (see
# _PDF_ACCENT_DARK/_PDF_ACCENT_SOFT below) — it used to be its own red
# brand, which made decks look like a different app from the rest of the
# site's exports.
_PDF_BRAND = '#DC2626'
_PDF_BRAND_DARK = '#7F1D1D'
_PDF_BRAND_SOFT = '#FEE2E2'
_PDF_ACCENT_DARK = '#1E3A8A'
_PDF_ACCENT_SOFT = '#DBEAFE'

# reportlab.graphics.shapes.Image ignores PNG alpha (it rendered the
# transparent-background logo as a solid red square in testing), so PDF
# export uses a pre-flattened white-background copy instead of the
# transparent one the pptx builder and website use.
_LOGO_PATH_PDF = os.path.join(os.path.dirname(__file__), "static", "logo_pdf.png")


def _wrap_pdf_title(text, font_name, font_size, max_width):
    """Greedy word-wrap into as many lines as needed so a long title is
    never cut off with an ellipsis — splits at word boundaries, only
    breaking a single overlong word (no spaces to break at) by character
    as a last resort. Returns a list of lines, each fitting max_width."""
    words = text.split()
    if not words:
        return [text]
    lines, current = [], ""
    for w in words:
        trial = f"{current} {w}".strip()
        if pdfmetrics.stringWidth(trial, font_name, font_size) <= max_width:
            current = trial
            continue
        if current:
            lines.append(current)
        if pdfmetrics.stringWidth(w, font_name, font_size) <= max_width:
            current = w
        else:
            # A single word wider than the whole box (rare) — break it
            # by character instead of leaving it to overflow.
            chunk = ""
            for ch in w:
                if pdfmetrics.stringWidth(chunk + ch, font_name, font_size) <= max_width:
                    chunk += ch
                else:
                    lines.append(chunk)
                    chunk = ch
            current = chunk
    if current:
        lines.append(current)
    return lines


# How much page a fetched Wikipedia image is allowed, by what kind of
# image it is (real_image["style"], set in ai_service.py). One flat 190pt
# box for all three made a square brand logo fill roughly a third of the
# page height — a lot of paper for a mark that reads fine small, and the
# main source of the "half the page is empty" look around it. A labelled
# anatomy diagram is the opposite case: shrink it and the labels stop
# being readable, which defeats the point of including it.
_REAL_IMAGE_BOX = {
    "logo": 110,      # a brand/software mark — recognisable at a glance
    "cutout": 155,    # an organism/object photo — wants some size
    "diagram": 210,   # labelled anatomy/structure — text must stay legible
}
_REAL_IMAGE_BOX_DEFAULT = 155


# Every language's word for "grade/class" as it can appear inside the
# `grade` string. The create form always sends the RUSSIAN form ("10 класс",
# see frontend/src/lib/material-types.ts's CLASSES) no matter what language
# the material itself is in, so checking only the current language's suffix
# left a Tajik konspekt reading "10 класс синф" — the word twice, in two
# languages. Checked against all of them instead.
_GRADE_WORDS = ("класс", "синф", "grade", "sinf")


def _bare_grade(grade: str) -> str:
    """"10 класс"/"10 синф"/"10" -> "10" — strips whichever language's
    grade-word the create form sent (see _GRADE_WORDS), for call sites that
    put their OWN label in front (e.g. "Синф 10") rather than appending a
    suffix after the number (see _format_grade, the other convention used
    elsewhere in these templates)."""
    lowered = grade.lower()
    for word in _GRADE_WORDS:
        idx = lowered.find(word)
        if idx != -1:
            return grade[:idx].strip()
    return grade


def _format_grade(grade: str, suffix: str) -> str:
    """"10" -> "10 синф"; "10 класс" -> "10 синф" too — the create form
    always sends the Russian "N класс" (see _GRADE_WORDS's comment above)
    regardless of the material's language, so a Tajik/English document
    used to print "10 класс" verbatim right next to labels that were
    otherwise fully translated. Strip whichever grade-word the form sent
    and re-suffix with the one this document's own language wants,
    instead of leaving a foreign word alone just because *some* suffix
    was already present."""
    stripped = grade
    lowered = grade.lower()
    for word in _GRADE_WORDS:
        idx = lowered.find(word)
        if idx != -1:
            stripped = grade[:idx].strip()
            break
    return f"{stripped} {suffix}" if stripped else grade


# `content["subject"]` is always one of frontend/src/lib/material-types.ts's
# fixed RUSSIAN subject names (it's the internal key every other lookup in
# this codebase — accent colour, illustration, AI prompt tuning — keys off
# of), regardless of which language the material itself was generated in.
# Most of those names are identical loanwords in Tajik (Математика,
# Физика, Химия...) so printing them as-is went unnoticed, but a few are
# not real Tajik/English words at all — "Информатика" printed on a Tajik
# konspekt next to otherwise fully-translated labels reads as a mistake,
# not a loanword. Only a display-time override for the header text; every
# other lookup in the app keeps using the Russian key untouched.
_SUBJECT_DISPLAY_NAMES: dict[str, dict[str, str]] = {
    "Информатика": {"Таджикский": "Технологияи иттилоотӣ", "Английский": "Computer Science"},
    "Русский язык": {"Таджикский": "Забони русӣ", "Английский": "Russian Language"},
    "Английский язык": {"Таджикский": "Забони англисӣ", "Английский": "English Language"},
    "Таджикский язык": {"Таджикский": "Забони тоҷикӣ", "Английский": "Tajik Language"},
    "Таджикская литература": {"Таджикский": "Адабиёти тоҷик", "Английский": "Tajik Literature"},
    "История Таджикистана": {"Таджикский": "Таърихи Тоҷикистон", "Английский": "History of Tajikistan"},
    "Всемирная история": {"Таджикский": "Таърихи умумиҷаҳонӣ", "Английский": "World History"},
    "Математика": {"Английский": "Mathematics"},
    "Алгебра": {"Английский": "Algebra"},
    "Геометрия": {"Английский": "Geometry"},
    "Физика": {"Английский": "Physics"},
    "Химия": {"Английский": "Chemistry"},
    "Биология": {"Английский": "Biology"},
    "География": {"Английский": "Geography"},
}


def _display_subject(subject: str, language: str) -> str:
    """The subject name as it should be PRINTED for this document's
    language — see _SUBJECT_DISPLAY_NAMES above. Falls back to the stored
    Russian name for Russian docs and for any subject/language pair with
    no override (i.e. the many subjects that are the same word in Tajik)."""
    return _SUBJECT_DISPLAY_NAMES.get(subject, {}).get(language, subject)


# ── the лекция's own look ────────────────────────────────────────────────
# A лекция used to be rendered in the konspekt's clothes — the same dark
# masthead block, the same accent plaques, the same sans body — so the two
# documents were indistinguishable at a glance even after the лекция grew
# its own standard structure (aim, plan, conclusions, sources). This is
# the lecture's own design: a printed academic handout.
#
#   * a typographic masthead — subject and grade as small spaced caps, the
#     title in serif below it, one hairline, the subtitle in italics;
#   * numbered section headings in serif caps over a hairline, no colour
#     plaques and no filled bands;
#   * a serif body set justified, the way lecture material is printed.
#
# Deliberately ONE fixed look with no picker: unlike a presentation, where
# the design is a matter of taste and gets previewed, a lecture handout has
# a conventional form and offering five variants of it is the friction the
# konspekt template chooser was removed for.

_LECTURE_INK = "#141821"
_LECTURE_RULE = "#C9CFDA"
_LECTURE_MUTED = "#5A6472"


def _pdf_lecture_masthead(title, subtitle, subject, grade, language, grade_suffix,
                          accent=None):
    """The lecture's title block: what subject and class it is for, the
    title itself, and its one-line description.

    Restrained, but not colourless: the subject line and the rule under
    the title carry the subject's own accent. Set entirely in greys the
    page read as unfinished rather than austere — a printed handout still
    has one colour in it."""
    accent = accent or get_subject_accent_hex(subject)
    display_subject = _display_subject(str(subject or ""), language)
    meta_bits = [b for b in (display_subject.upper(),
                             _format_grade(grade, grade_suffix).upper() if grade else "") if b]
    elements = [Spacer(1, 10)]
    if meta_bits:
        elements.append(Paragraph(
            "&nbsp;&nbsp;·&nbsp;&nbsp;".join("&nbsp;".join(part) for part in meta_bits),
            ParagraphStyle(name="LecMeta", fontName=FONT_NAME_BOLD, fontSize=8.5,
                           leading=11, alignment=TA_CENTER,
                           textColor=HexColor(accent), spaceAfter=10)))
    elements.append(Paragraph(
        str(title or ""),
        ParagraphStyle(name="LecTitle", fontName=MATH_FONT_BOLD, fontSize=23, leading=28,
                       alignment=TA_CENTER, textColor=HexColor(_LECTURE_INK), spaceAfter=8)))
    rule = Table([[""]], colWidths=[110], rowHeights=[2.2])
    rule.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(accent)),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(Table([[rule]], colWidths=[500], style=TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ])))
    if subtitle:
        elements.append(Paragraph(
            f"<i>{subtitle}</i>",
            ParagraphStyle(name="LecSub", fontName=MATH_FONT, fontSize=11, leading=15,
                           alignment=TA_CENTER, textColor=HexColor(_LECTURE_MUTED),
                           spaceAfter=16)))
    return elements


def _pdf_lecture_section_header(label, color, number, font_name=None):
    """"3. ПЛАН ЛЕКЦИИ" in serif caps over a hairline — the heading style
    of a printed handout, with no plaque and no colour behind it."""
    accent = color or _PDF_ACCENT
    number_bit = (f'<font color="{accent}">{number}.</font>&nbsp;&nbsp;' if number else "")
    head = Paragraph(
        f"{number_bit}{str(label).upper()}",
        ParagraphStyle(name=f"LecHead{abs(hash(label)) % 99999}", fontName=MATH_FONT_BOLD,
                       fontSize=12, leading=15, textColor=HexColor(_LECTURE_INK),
                       spaceBefore=12, spaceAfter=2))
    t = Table([[head]], colWidths=[500])
    t.setStyle(TableStyle([
        # One rule in the subject's accent under the heading — enough
        # colour to structure the page, no filled plaque.
        ("LINEBELOW", (0, 0), (-1, -1), 1.1, HexColor(accent)),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [t, Spacer(1, 5)]


def _pdf_header(title, subtitle=None, tag=None, accent=_PDF_ACCENT, minimal=False):
    elements = []
    elements.append(Spacer(1, 6))

    if minimal:
        # Typographic masthead instead of the filled dark block: the tag
        # line as small spaced caps, the title as plain large type, and a
        # single short accent rule doing all the decorating. See
        # KonspektTemplate.minimal_chrome for why this is a template knob
        # rather than a separate renderer.
        if tag:
            elements.append(Paragraph(
                f'<font color="{accent}" size="8"><b>{"&nbsp;".join(tag.upper())}</b></font>',
                ParagraphStyle(name='MinTag', fontName=FONT_NAME_BOLD, fontSize=8,
                               leading=11, textColor=HexColor(accent), spaceAfter=6),
            ))
        elements.append(Paragraph(
            title,
            ParagraphStyle(name='MinTitle', fontName=FONT_NAME_BOLD, fontSize=21,
                           leading=25, textColor=HexColor(_PDF_DARK), spaceAfter=6),
        ))
        rule = Table([[""]], colWidths=[54], rowHeights=[2.2])
        rule.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor(accent)),
            ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(rule)
        if subtitle:
            elements.append(Spacer(1, 8))
            elements.append(Paragraph(f'<font color="#64748B">{subtitle}</font>', _styles()['DocSubtitle']))
        elements.append(Spacer(1, 14))
        return elements

    # Long titles wrap onto extra lines instead of being cut off with an
    # ellipsis — the header box grows taller to fit however many lines it
    # takes (this used to shrink the font down to a floor and then
    # truncate, silently losing the end of the title).
    max_title_width = 465
    title_font_size = 18
    while title_font_size > 13 and pdfmetrics.stringWidth(title, FONT_NAME_BOLD, title_font_size) > max_title_width:
        title_font_size -= 1
    title_lines = _wrap_pdf_title(title, FONT_NAME_BOLD, title_font_size, max_title_width)
    line_h = title_font_size + 7
    extra_height = line_h * (len(title_lines) - 1)

    # Taller drawing when there's a tag pill — title sits above it instead of
    # on top of it (the two used to overlap: a fixed 55pt-tall box put the
    # title's baseline inside the tag pill's own vertical span).
    height = (66 if tag else 55) + extra_height
    d = Drawing(500, height)
    d.add(Rect(0, 0, 500, height, fillColor=HexColor(_PDF_DARK), strokeColor=None))
    d.add(Rect(0, height - 3, 500, 3, fillColor=HexColor(accent), strokeColor=None))
    if tag:
        d.add(Rect(10, 10, len(tag) * 7 + 20, 22, fillColor=HexColor(accent), strokeColor=None, rx=11, ry=11))
        d.add(String(20, 16, tag, fontName=FONT_NAME_BOLD, fontSize=9, fillColor=HexColor('#FFFFFF')))
        y_title = 40
    else:
        y_title = 22
    # Lines stack downward from the top of the box — the first line of the
    # title sits highest, reading top-to-bottom in natural order, down to
    # y_title (right above the tag pill, or the box bottom without one).
    for i, line in enumerate(title_lines):
        y = y_title + line_h * (len(title_lines) - 1 - i)
        d.add(String(15, y, line, fontName=FONT_NAME_BOLD, fontSize=title_font_size, fillColor=HexColor('#FFFFFF')))
    elements.append(d)
    if subtitle:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f'<font color="#64748B">{subtitle}</font>', _styles()['DocSubtitle']))
    elements.append(Spacer(1, 6))
    return elements


def _pdf_section_header(label, color=_PDF_ACCENT, number=None):
    """"klassik" template — bold colored number + label, nothing else.
    Used to also draw a leading colored bullet square and a full-width
    rule underneath; both removed (teacher feedback: too heavy/bureaucratic
    for a document meant to read as clean and simple, not an official
    form)."""
    elements = []
    elements.append(Spacer(1, 8))
    prefix = f'{number}. ' if number else ''
    elements.append(Paragraph(f'<font color="{color}"><b>{prefix}{label}</b></font>', _styles()['SlideTitle']))
    elements.append(Spacer(1, 3))
    return elements


def _pdf_section_header_underline(label, color, number, font_name):
    """"zamonaviy" — bold caps over a short colored rule, no number badge
    (docx counterpart: _header_underline)."""
    style = ParagraphStyle(
        name=f'HdrUL_{abs(hash(label)) % 100000}', fontName=FONT_NAME_BOLD, fontSize=12.5,
        textColor=HexColor(_PDF_DARK), spaceAfter=3,
    )
    return [
        Spacer(1, 5),
        Paragraph(label.upper(), style),
        HRFlowable(width=70, thickness=2.4, color=HexColor(color), spaceAfter=3, hAlign='LEFT'),
    ]


def _pdf_section_header_smallcaps(label, color, number, font_name):
    """"minimal" — small muted-accent label over a thin full-width gray
    rule, no fill (docx counterpart: _header_smallcaps)."""
    style = ParagraphStyle(
        name=f'HdrSC_{abs(hash(label)) % 100000}', fontName=FONT_NAME_BOLD, fontSize=8.5,
        textColor=HexColor(color), spaceAfter=2,
    )
    return [
        Spacer(1, 9),
        Paragraph(label.upper(), style),
        HRFlowable(width='100%', thickness=0.6, color=HexColor('#E2E8F0'), spaceAfter=4),
    ]


def _pdf_section_header_serif(label, color, number, font_name):
    """"rasmiy" — serif numbered heading over a muted rule, no colored
    fill (docx counterpart: _header_serif)."""
    style = ParagraphStyle(
        name=f'HdrSerif_{abs(hash(label)) % 100000}', fontName=font_name, fontSize=13,
        textColor=HexColor('#334155'), spaceAfter=3,
    )
    prefix = f'{number}. ' if number else ''
    return [
        Spacer(1, 9),
        Paragraph(f'<b>{prefix}{label}</b>', style),
        HRFlowable(width='100%', thickness=0.75, color=HexColor('#CBD5E1'), spaceAfter=4),
    ]


def _pdf_section_header_bar(label, color, number, font_name):
    """"rangli" — a full-width colored bar with white text, instead of a
    left-accent line (docx counterpart: _header_bar)."""
    style = ParagraphStyle(
        name=f'HdrBar_{abs(hash(label)) % 100000}', fontName=FONT_NAME_BOLD, fontSize=11.5,
        textColor=HexColor('#FFFFFF'),
    )
    prefix = f'{number}.  ' if number else ''
    t = Table([[Paragraph(f'{prefix}{label}', style)]], colWidths=[470])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor(color)),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return [Spacer(1, 8), t, Spacer(1, 3)]


_PDF_SECTION_RENDERERS = {
    "underline": _pdf_section_header_underline,
    "smallcaps": _pdf_section_header_smallcaps,
    "serif": _pdf_section_header_serif,
    "bar": _pdf_section_header_bar,
}


def _pdf_light_tint_hex(hex_color: str, amount: float = 0.88) -> str:
    """Same idea as docx_builder.py's _light_tint_hex, for a hex string
    input instead of an RGBColor — "rangli"'s soft-tinted bullets."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    tr = int(r + (255 - r) * amount)
    tg = int(g + (255 - g) * amount)
    tb = int(b + (255 - b) * amount)
    return f'#{tr:02X}{tg:02X}{tb:02X}'


def _pdf_dark_shade_hex(hex_color: str, amount: float = 0.55) -> str:
    """Darken a hex color — same math as _pptx_accent_shades' `dark` output,
    for the presentation PDF's gradient deck header (the konspekt PDF has
    no gradient, so this wasn't needed until now)."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'#{int(r * amount):02X}{int(g * amount):02X}{int(b * amount):02X}'


def _pdf_bullet(text, color=_PDF_ACCENT, indent=16, serif: bool = False):
    style = ParagraphStyle(
        name=f'Bullet_{color}' + ('S' if serif else ''),
        fontName=MATH_FONT if serif else FONT_NAME,
        fontSize=11 if serif else 10.5,
        leading=15 if serif else 13,
        textColor=HexColor(_LECTURE_INK if serif else _PDF_DARK),
        leftIndent=indent,
        spaceAfter=2,
    )
    colored_dot = f'<font color="{color}"><b>●</b></font>'
    return Paragraph(f'{colored_dot}&nbsp;&nbsp;{text}', style)


def _pdf_prose_paragraph(text, serif: bool = False):
    """Plain flowing-paragraph rendering for "main_content" specifically —
    every other string section (pair_work/consolidation/assessment/...)
    is one short blurb where _pdf_bullet's colored-dot + 25pt indent
    treatment reads fine, but main_content is genuine multi-paragraph
    prose (see _konspekt_prompt's own rule that it must be real flowing
    sentences); forcing a bullet indent onto that wasted a quarter-inch
    of line width for no reason and read as odd (a "bullet" spanning 4
    paragraphs). Splits on the model's own blank-line paragraph breaks
    into separate justified, full-width Paragraph flowables — dense like
    a real printed page instead of one indented block (direct teacher
    feedback: konspekt read as too spread-out/empty next to a reference
    printed booklet)."""
    style = ParagraphStyle(
        name='ProseBody' + ('Serif' if serif else ''),
        fontName=MATH_FONT if serif else FONT_NAME,
        fontSize=11 if serif else 10.5, leading=15 if serif else 13.5,
        textColor=HexColor(_LECTURE_INK if serif else _PDF_DARK),
        alignment=TA_JUSTIFY, spaceAfter=6 if serif else 5,
    )
    return [Paragraph(p.strip(), style) for p in text.split('\n\n') if p.strip()]


def _pdf_numbered_bullet(num, text, color=_PDF_ACCENT, serif: bool = False):
    style = ParagraphStyle(
        name=f'NumBullet_{num}' + ('S' if serif else ''),
        fontName=MATH_FONT if serif else FONT_NAME,
        fontSize=11 if serif else 10.5,
        leading=15 if serif else 13,
        textColor=HexColor(_LECTURE_INK if serif else _PDF_DARK),
        # Hanging indent: the number sits in the gutter and wrapped lines
        # line up under the TEXT, not under the number. Without the
        # negative first-line indent (which is how this used to be) a
        # two-line item's second line ran back under "1.", so a list of
        # long items read as a wall with numbers floating inside it.
        leftIndent=30,
        firstLineIndent=-14,
        spaceAfter=2,
    )
    return Paragraph(f'<font color="{color}"><b>{num}.</b></font>&nbsp;&nbsp;{text}', style)


def _pdf_numbered_bullet_tinted(num, text, color):
    """"rangli" counterpart to _pdf_numbered_bullet — a soft accent-tinted
    background behind each item instead of plain white (docx counterpart:
    _add_konspekt_body's _bullet)."""
    style = ParagraphStyle(
        name=f'NumBulletTint_{num}_{abs(hash(text)) % 100000}', fontName=FONT_NAME, fontSize=10.5,
        leading=13, textColor=HexColor(_PDF_DARK),
    )
    t = Table([[Paragraph(f'<font color="{color}"><b>{num}.</b></font>&nbsp;&nbsp;{text}', style)]], colWidths=[460])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor(_pdf_light_tint_hex(color))),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return [t, Spacer(1, 2)]


def _pdf_formula_flowable(latex: str, minimal: bool = False, accent: str | None = None):
    """The formula itself, drawn as vector art on the card's own tinted
    strip, or None if there is nothing typesettable to draw."""
    latex = str(latex or "").strip()
    if not latex:
        return None
    try:
        # The tint is painted by the flowable itself across the full
        # column, not by a fixed-width table around it: a table sized to
        # some guessed number of points left white gutters down both
        # sides of every card, so the panel came out striped.
        return MathFlowable(latex, 15, colour=HexColor(accent or _PDF_ACCENT),
                            back_colour=None if minimal else HexColor('#F8FAFC'),
                            pad_top=7, pad_bottom=4)
    except Exception:
        return None


def _pdf_formula_card(formula: str, explanation: str, minimal: bool = False,
                      latex: str | None = None, accent: str | None = None) -> list:
    """Same visual idea as the docx formula card — a shaded, centered block
    that reads as reference material rather than another paragraph of
    prose. Returns a list of flowables (formula + optional explanation),
    meant to be `story.extend()`-ed rather than appended as one item.

    Set as REAL typeset mathematics whenever a LaTeX form is available:
    this card used to print the "formula" field verbatim, so a fraction
    arrived as "1/2" on one line and a root as the bare "√" character
    with brackets after it — the panel that a teacher looks at first was
    the one place in the document with no typesetting at all. The plain
    string is still the fallback for an entry with no usable LaTeX."""
    typeset = _pdf_formula_flowable(latex or _plain_to_latex(formula), minimal, accent)
    if typeset is not None:
        elements = [typeset]
        if explanation:
            elements.append(Paragraph(
                f'<i>{explanation}</i>',
                ParagraphStyle(name=f'FormulaExplV_{abs(hash(explanation)) % 100000}',
                               fontName=FONT_NAME, fontSize=9.5, leading=12,
                               textColor=HexColor('#64748B'),
                               backColor=None if minimal else HexColor('#F8FAFC'),
                               alignment=TA_CENTER, borderPadding=(1, 10, 5, 10),
                               spaceAfter=8 if minimal else 4)))
        return elements

    formula_style = ParagraphStyle(
        name=f'Formula_{abs(hash(formula)) % 100000}',
        fontName=MATH_FONT_BOLD,
        fontSize=15,
        leading=20,
        textColor=HexColor(_PDF_ACCENT),
        # No panel fill in the minimal look — the formula is set apart by
        # size and whitespace alone (see KonspektTemplate.minimal_chrome).
        backColor=None if minimal else HexColor('#F8FAFC'),
        alignment=TA_CENTER,
        borderPadding=(6, 10, 4 if explanation else 6, 10),
        spaceBefore=2,
        spaceAfter=0 if explanation else 4,
    )
    elements = [Paragraph(formula, formula_style)]
    if explanation:
        expl_style = ParagraphStyle(
            name=f'FormulaExpl_{abs(hash(explanation)) % 100000}',
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=12,
            textColor=HexColor('#64748B'),
            # Matches the formula above: with the panel gone, a fill behind
            # only the caption would leave a stray grey band under an
            # otherwise unfilled formula.
            backColor=None if minimal else HexColor('#F8FAFC'),
            alignment=TA_CENTER,
            borderPadding=(1, 10, 5, 10),
            spaceAfter=8 if minimal else 4,
        )
        elements.append(Paragraph(f'<i>{explanation}</i>', expl_style))
    return elements


def _pdf_concept_card(card: dict, accent_hex: str) -> Table:
    """One reference card — colored header (title + optional tag) over a
    light body holding a small truth-table and/or a formula and a short
    note. Returns a single flowable (a 2-row Table) so it can be dropped
    straight into a grid Table cell."""
    title = card.get('title', '')
    tag = card.get('tag', '')

    # White header + colored bold text + a heavy colored top border,
    # instead of a solid accent-fill header with white text — a page with
    # several of these printed on a black-and-white printer turned into
    # a wall of dark ink blocks; a teacher pointed this out directly. The
    # thick top rule still reads as "this card belongs to this subject's
    # color" even with zero fill.
    header_style = ParagraphStyle(
        name=f'CardHeader_{abs(hash(title)) % 100000}', fontName=FONT_NAME_BOLD, fontSize=11,
        textColor=HexColor(accent_hex), alignment=TA_CENTER, spaceAfter=0,
    )
    header_content = [Paragraph(title, header_style)]
    if tag:
        tag_style = ParagraphStyle(
            name=f'CardTag_{abs(hash(tag)) % 100000}', fontName=FONT_NAME, fontSize=8,
            textColor=HexColor('#64748B'), alignment=TA_CENTER, spaceBefore=1,
        )
        header_content.append(Paragraph(f'<i>{tag}</i>', tag_style))

    body_content = []
    table_rows = card.get('table')
    if table_rows:
        t = Table(table_rows, hAlign='CENTER')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E2E8F0')),
            ('FONTNAME', (0, 0), (-1, 0), MATH_FONT_BOLD),
            ('FONTNAME', (0, 1), (-1, -1), MATH_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        body_content.append(t)
    formula = card.get('formula')
    if formula:
        f_style = ParagraphStyle(
            name=f'CardFormula_{abs(hash(formula)) % 100000}', fontName=MATH_FONT_BOLD, fontSize=12,
            textColor=HexColor(accent_hex), alignment=TA_CENTER, spaceBefore=3, spaceAfter=1,
        )
        body_content.append(Paragraph(formula, f_style))
    note = card.get('note')
    if note:
        n_style = ParagraphStyle(
            name=f'CardNote_{abs(hash(note)) % 100000}', fontName=FONT_NAME, fontSize=7.5,
            textColor=HexColor('#64748B'), alignment=TA_CENTER, spaceBefore=2,
        )
        body_content.append(Paragraph(f'<i>{note}</i>', n_style))
    if not body_content:
        body_content = [Spacer(1, 4)]

    card_table = Table([[header_content], [body_content]], colWidths=[228], hAlign='CENTER')
    card_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), HexColor('#FFFFFF')),
        ('BACKGROUND', (0, 1), (0, 1), HexColor('#F8FAFC')),
        ('LINEABOVE', (0, 0), (0, 0), 2.5, HexColor(accent_hex)),
        ('LINEBELOW', (0, 0), (0, 0), 0.75, HexColor(accent_hex)),
        ('BOX', (0, 0), (-1, -1), 0.75, HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (0, 0), 4), ('BOTTOMPADDING', (0, 0), (0, 0), 4),
        ('TOPPADDING', (0, 1), (0, 1), 5), ('BOTTOMPADDING', (0, 1), (0, 1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return card_table


def _card_weight(card: dict) -> int:
    """Rough estimate of how tall a card will render, used only to pair
    similarly-sized cards into the same grid row (see below) — reportlab's
    Table stretches every cell in a row to match the tallest one, so pairing
    a short card next to a tall one used to leave a visible empty gap at
    the bottom of the short one."""
    w = 0
    table = card.get('table')
    if table:
        w += len(table) * 2
    if card.get('formula'):
        w += 3
    note = card.get('note')
    if note:
        w += 1 + len(note) // 60
    return w


def _pdf_concept_card_grid(cards: list, accent_hex: str, cols: int = 2) -> list:
    """Lays cards out 2-per-row in a grid Table, matching the reference
    methodological guide's card-grid layout instead of one long column.
    Cards are reordered (grouped by similar estimated height) before
    pairing into rows, so each row pairs cards of comparable size instead
    of a short one next to a tall one."""
    if not cards:
        return []
    ordered = sorted(cards, key=_card_weight)
    flowables = [_pdf_concept_card(c, accent_hex) for c in ordered]
    # An odd card count leaves one lone card in the last row with a blank
    # gap next to it — span that row's cells into one wide cell instead
    # (the card itself stays its normal fixed width, just centered in the
    # now-wide cell — see _pdf_concept_card's hAlign='CENTER') so it never
    # reads as a half-finished row.
    odd_last_row = len(flowables) % cols == 1
    while len(flowables) % cols:
        flowables.append('')
    rows = [flowables[i:i + cols] for i in range(0, len(flowables), cols)]
    grid = Table(rows, colWidths=[232] * cols, hAlign='CENTER')
    style = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]
    if odd_last_row:
        last_row = len(rows) - 1
        style.append(('SPAN', (0, last_row), (cols - 1, last_row)))
        style.append(('ALIGN', (0, last_row), (cols - 1, last_row), 'CENTER'))
    grid.setStyle(TableStyle(style))
    return [Spacer(1, 4), grid, Spacer(1, 6)]


_SUBSCRIPT_DIGITS = {chr(0x2080 + d): str(d) for d in range(10)}


_MATH_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "math")
_MATH_SPAN = re.compile(r"\$([^$\n]{1,400}?)\$")
# render_png pads by this much on every side; the caller needs it to place
# the image on the text baseline.
_MATH_PAD = 4
# Device pixels per point for the ONE case that still has to rasterise (a
# fraction or a radical sitting inside a line of prose — ReportLab takes
# no vector flowable inline). 6 puts ~430 dpi on the page, which holds up
# well past the 400% zoom the brief asks about. Everything on its own
# line is drawn as vector and ignores this entirely.
_MATH_OVERSAMPLE = 6
# Bumped whenever the typesetting itself changes (a glyph placed
# differently, a new rule about degree signs). The rendered formulas are
# cached on disk by content hash, so without this a fix to the layout
# would keep serving the images drawn by the old one.
_MATH_CACHE_VERSION = 2


# ── formulas as vector art, not pictures of formulas ────────────────────
# math_render lays a formula out on real baselines and then hands the
# result to a painter (see its PilPainter). This is the other painter: it
# turns the same two primitives into PDF drawing operators, so a fraction
# in an exported konspekt is the embedded font's outlines plus a drawn
# rule — sharp at 100%, at 400%, and on a printer's imagesetter, exactly
# like the surrounding body text.
#
# What it replaced: the layout was rasterised at 3x and then resized back
# down to one pixel per point before being placed in the page. That is a
# 72 dpi bitmap, and no amount of zooming recovers what it threw away —
# which is what "the formulas look blurry" was.

_MATH_PDF_FONTS: dict = {}


def _math_pdf_font(path: str) -> str:
    """The registered PDF font name for one of math_render's font FILES.

    math_render addresses fonts by path because PIL does; ReportLab needs
    them registered under a name first. Registration is cached and
    fail-soft — a missing italic face falls back to the document's own
    text font rather than losing the formula."""
    if path in _MATH_PDF_FONTS:
        return _MATH_PDF_FONTS[path]
    name = FONT_NAME
    try:
        if os.path.exists(path):
            candidate = "MathFace" + str(abs(hash(path)) % 100000)
            if candidate not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(candidate, path))
            name = candidate
    except Exception:
        name = MATH_FONT or FONT_NAME
    _MATH_PDF_FONTS[path] = name
    return name


class _PdfMathPainter:
    """math_render's painter protocol, drawing onto a ReportLab canvas.

    math_render works in supersampled units with y growing DOWNWARD from
    the formula's baseline; PDF space has y growing UP. `scale` converts
    the first to points and `baseline_y` is where that baseline sits on
    the page, so the whole transform is one multiply and one subtract."""

    def __init__(self, canvas, origin_x: float, baseline_y: float,
                 scale: float, colour):
        self.c = canvas
        self.x0 = origin_x
        self.y0 = baseline_y
        self.k = scale
        self.colour = colour

    def text(self, x, y, s, font_path, size_px):
        self.c.setFont(_math_pdf_font(font_path), size_px * self.k)
        self.c.setFillColor(self.colour)
        self.c.drawString(self.x0 + x * self.k, self.y0 - y * self.k, s)

    def line(self, x1, y1, x2, y2, width):
        self.c.setStrokeColor(self.colour)
        self.c.setLineWidth(max(0.35, width * self.k))
        self.c.line(self.x0 + x1 * self.k, self.y0 - y1 * self.k,
                    self.x0 + x2 * self.k, self.y0 - y2 * self.k)


class MathFlowable(_RLFlowable):
    """One formula drawn as vector art, as a flowable of its own.

    Used for every formula that gets a line to itself — the formulas
    panel, a displayed equation — which is where the fractions, radicals
    and sums live, i.e. everything the inline text runs cannot express."""

    def __init__(self, latex: str, size: float = 14, align: str = "CENTER",
                 colour=None, avail_width: float | None = None,
                 back_colour=None, pad_top: float = 0, pad_bottom: float = 0,
                 pad_x: float = 10):
        super().__init__()
        from app.math_render import parse, _layout, SS
        self._ss = SS
        self._box = _layout(parse(latex), size)
        self._colour = colour or HexColor("#111111")
        self.align = align
        self.width = self._box.w / SS
        self.height = (self._box.asc + self._box.desc) / SS
        self._avail = avail_width
        # The tint behind a formula card is painted here rather than by a
        # table around the flowable, so it spans the whole column exactly
        # like the paragraph it replaced.
        self.back_colour = back_colour
        self.pad_top = pad_top
        self.pad_bottom = pad_bottom
        self.pad_x = pad_x

    def wrap(self, avail_w, avail_h):
        self._avail = avail_w
        # A formula wider than the column is scaled down to fit rather
        # than running off the page — rare, but a long worked line does
        # it, and clipping mathematics is never acceptable.
        usable = max(1.0, avail_w - 2 * self.pad_x)
        self._shrink = min(1.0, (usable / self.width) if self.width else 1.0)
        return (avail_w, self.height * self._shrink + self.pad_top + self.pad_bottom)

    def draw(self):
        shrink = getattr(self, "_shrink", 1.0)
        width = self.width * shrink
        avail = self._avail if self._avail is not None else width
        if self.back_colour is not None:
            self.canv.setFillColor(self.back_colour)
            self.canv.rect(0, 0, avail,
                           self.height * shrink + self.pad_top + self.pad_bottom,
                           stroke=0, fill=1)
        if self.align == "CENTER":
            x = max(0.0, (avail - width) / 2)
        elif self.align == "RIGHT":
            x = max(self.pad_x, avail - width - self.pad_x)
        else:
            x = self.pad_x
        baseline = self.pad_bottom + (self._box.desc / self._ss) * shrink
        self._box.paint(_PdfMathPainter(self.canv, x, baseline,
                                        shrink / self._ss, self._colour), 0, 0)


def _plain_to_latex(text) -> str:
    """The "formula" field's plain notation (a^2, sqrt, x1 as an index)
    read as LaTeX, for entries where the model gave no "latex"."""
    try:
        from app.math_render import plain_to_latex
        return plain_to_latex(text)
    except Exception:
        return ""


def _normalize_math(text) -> str:
    """A power the model wrote outside the dollars ("S = a^2") or as the
    character itself ("x²") rewritten into a $...$ span, so the code below
    typesets it as a raised exponent instead of printing it flat.

    ai_service does this when the konspekt is generated; it is repeated
    here because a konspekt saved BEFORE that pass existed is still in the
    database and still gets exported. The rewrite is idempotent, so text
    that has already been through it is unchanged."""
    try:
        from app.math_render import normalize_math
        return normalize_math(text)
    except Exception:
        return str(text or "")


def _math_png(latex: str, size: float, bg: str = "white"):
    """Renders one formula to a cached PNG and returns
    (path, width, ascent, descent) in points, or None.

    Cached on the formula text and size: a konspekt repeats the same
    expression across twenty worked examples, and re-rasterising it each
    time made the export noticeably slower for no gain.

    Only used for a formula that has to sit INSIDE a line of prose, where
    ReportLab accepts an image and nothing else. Everything set on its
    own line goes through MathFlowable and is true vector. The image is
    rendered at _MATH_OVERSAMPLE pixels per point (~430 dpi) and placed
    at its point size, so even this path holds up under magnification —
    it used to be written out at 72 dpi, which is what made zoomed
    formulas look soft."""
    from app.math_render import render_png, measure
    try:
        key = hashlib.sha1(
            f"{latex}|{size:.2f}|{bg}|x{_MATH_OVERSAMPLE}|{_MATH_CACHE_VERSION}".encode("utf-8")).hexdigest()
        path = os.path.join(_MATH_DIR, key + ".png")
        if not os.path.exists(path):
            png = render_png(latex, size, _MATH_PAD, bg, oversample=_MATH_OVERSAMPLE)
            if not png:
                return None
            os.makedirs(_MATH_DIR, exist_ok=True)
            with open(path, "wb") as f:
                f.write(png)
        w, asc, desc = measure(latex, size)
        if w <= 0:
            return None
        return path, w, asc, desc
    except Exception:
        return None


def _math_inline(text, size: float = 11, bg: str = "white"):
    """Replaces every $...$ span with an inline formula image.

    The image is placed by its own baseline (valign is the descent below
    it), so a fraction inside a sentence sits on the line of text rather
    than floating above or below it."""
    raw = _normalize_math(text)
    if "$" not in raw:
        return raw

    def repl(m):
        got = _math_png(m.group(1), size, bg)
        if not got:
            # Unrenderable: show the expression without the dollars rather
            # than leaving "$x^2$" on the page.
            return m.group(1)
        path, w, asc, desc = got
        return (f'<img src="{path}" width="{w + 2 * _MATH_PAD:.1f}" '
                f'height="{asc + desc + 2 * _MATH_PAD:.1f}" '
                f'valign="{-(desc + _MATH_PAD):.1f}"/>')
    return _MATH_SPAN.sub(repl, raw)


def _pdf_math_display(latex: str, size: float = 15, width: float = 430, bg: str = "white"):
    """A formula set on its own, centred — the display form.

    Drawn as vector art (MathFlowable): the glyph outlines and the
    fraction rules go into the PDF as drawing operators, so the equation
    stays sharp at any magnification instead of being a picture of an
    equation. `bg` is kept in the signature because callers pass the
    panel colour, but a vector formula needs no background of its own —
    it simply draws over whatever the panel painted."""
    try:
        formula = MathFlowable(latex, size)
        if formula.width <= 0:
            return None
    except Exception:
        return None
    # Wrapped in a full-width table rather than trusting hAlign: inside the
    # panel's own table cell hAlign was ignored and every equation sat
    # hard against the left edge with its explanation stranded beside it.
    t = Table([[formula]], colWidths=[width])
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return t


def _sub_digits(text) -> str:
    """Rewrites Unicode subscript digits as ReportLab <sub> markup.

    The embedded font has no glyph for U+2081 and friends, so a caption
    naming a solid the way a textbook does — "ABCDA₁B₁C₁D₁" — printed as a row
    of empty boxes. The model writes those characters unprompted, so
    stripping them at render time is more reliable than asking it not to."""
    out = str(text or "")
    for ch, digit in _SUBSCRIPT_DIGITS.items():
        if ch in out:
            out = out.replace(ch, f"<sub>{digit}</sub>")
    return out


def _pdf_subject_figure(fig: dict, minimal: bool = False, max_w: float = 300,
                        max_h: float = 230) -> list:
    """One figure_builder drawing plus the caption printed under it.

    Deliberately narrower than a photo (max_w 300pt against the photo
    helper's 460): these are line drawings on white with no border, so at
    full text width a cube reads as a page of empty space with a few
    strokes in it. The caption is not optional decoration — a drawing with
    no reading underneath leaves the pupil to guess what it shows, the same
    reason visual_blocks carries a "description"."""
    path = fig.get("image")
    if not path:
        return []
    full = os.path.join(os.path.dirname(__file__), "..", path.lstrip("/"))
    if not os.path.exists(full):
        return []
    try:
        with PILImage.open(full) as im:
            iw, ih = im.size
    except Exception:
        return []
    # Fitted to a BOX, not just a width: the drawings are cropped to their
    # own ink (see figure_builder.Canvas.finish), so a cone comes out tall
    # and narrow while a parabola comes out wide and short. Scaling on
    # width alone let the tall ones run most of a page high.
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    body = [_PdfFlowableImage(full, width=w, height=h, hAlign="CENTER")]
    caption = _sub_digits(fig.get("caption"))
    if caption:
        body.append(Paragraph(
            f"<i>{caption}</i>",
            ParagraphStyle(
                name=f"FigCap_{abs(hash(str(caption))) % 100000}",
                fontName=FONT_NAME, fontSize=9.5, leading=12.5, alignment=TA_CENTER,
                textColor=HexColor("#000000" if minimal else "#64748B"),
                spaceBefore=3, spaceAfter=8,
            ),
        ))
    # A drawing stranded at the foot of one page with its caption at the
    # top of the next is worse than either alone — they are one unit.
    return [Spacer(1, 6), KeepTogether(body), Spacer(1, 6)]


class _PdfContentAnchor(Spacer):
    """A zero-height marker a body renderer drops where its own header
    ends, so a caller can splice something in after it without having to
    count that renderer's flowables."""

    def __init__(self):
        super().__init__(1, 0)


def _pdf_body_splice_index(body: list, nth_section: int = 2) -> int:
    """Where a teaching illustration goes into the body: at the start of
    the `nth_section`-th section.

    Every section in both body renderers opens with a KeepTogether (its
    heading bound to its first item, so a heading is never stranded at
    the foot of a page), which makes those the section boundaries. nth=1
    is "after the masthead, before the first section" — where the plan
    sheet's first picture belongs, since that template prints its own
    date/class/school form and title before any content. nth=2 is the end
    of section one: early enough for the picture to still be on the
    second page, late enough that the first page keeps its text."""
    if nth_section == 1:
        for i, flowable in enumerate(body):
            if isinstance(flowable, _PdfContentAnchor):
                return i + 1
    seen = 0
    for i, flowable in enumerate(body):
        if isinstance(flowable, KeepTogether):
            seen += 1
            if seen == nth_section:
                return i
    # Not that many sections (a very short konspekt): a fraction of the
    # way in still beats dropping the picture at the very end.
    return min(len(body), max(1, len(body) * (nth_section - 1) // 3))


class _PdfPageGate(_RLFlowable):
    """Zero-height spacer that refuses to fit until the document has
    reached `target_page`, pushing whatever follows onto a later page.

    This is how the second teaching illustration is guaranteed to land on
    the SECOND content page rather than sharing the first one with the
    first illustration. ReportLab decides pagination while it lays the
    story out, so the page number cannot be known in advance — but a
    flowable can read the page it is currently being laid out on
    (`_doctemplateAttr('page')`, available because the frame assigns
    `canv` before calling wrap) and ask for more room than any page has,
    which makes the frame break and try again on the next one.

    The retry counter is a hard stop: a gate that could never be
    satisfied would otherwise loop forever instead of printing the
    picture."""

    def __init__(self, target_page: int, max_defers: int = 4):
        super().__init__()
        self.target_page = target_page
        self._defers_left = max_defers

    def wrap(self, avail_w, avail_h):
        current = self._doctemplateAttr("page") or 1
        if current < self.target_page and self._defers_left > 0:
            self._defers_left -= 1
            return (avail_w, avail_h + 1)      # too tall to fit → next page
        return (0, 0)

    def draw(self):
        pass


def _pdf_lesson_image_block(image: dict, label: str, accent_hex: str) -> list:
    """One Commons teaching illustration set into the running text, under
    the section it explains (image["position_after"], chosen by the model
    while it was writing that section).

    Deliberately NOT a page of its own and NOT parked at the top of a
    page: a diagram belongs in the middle of the explanation it
    illustrates, the way a textbook sets one — the paragraph, then the
    figure, then the sentence telling the pupil what to look at, then the
    explanation continues. At 300x215pt it takes about a third of the
    page height, so the text it belongs to stays visible around it.

    The whole block is one KeepTogether: a figure separated from its
    reading instruction by a page break teaches nothing."""
    body = _pdf_illustration_image(
        image.get("path", ""), image.get("caption", ""),
        image.get("credit", ""), max_w=300, max_h=215,
    )
    if not body:
        return []
    key = abs(hash(image.get("path", ""))) % 100000
    tag = Paragraph(
        label.upper(),
        ParagraphStyle(name=f'LessonImgTag_{key}', fontName=FONT_NAME_BOLD, fontSize=8.5,
                       textColor=HexColor(accent_hex), alignment=TA_CENTER,
                       spaceBefore=8, spaceAfter=2),
    )
    parts = [tag] + body
    # What the pupil is supposed to get out of the picture, printed under
    # it — the difference between an illustration that is part of the
    # explanation and one that is decoration.
    explanation = str(image.get("explanation") or "").strip()
    if explanation:
        parts.append(Paragraph(
            explanation,
            ParagraphStyle(name=f'LessonImgNote_{key}', fontName=FONT_NAME, fontSize=9.5,
                           leading=13, alignment=TA_CENTER, textColor=HexColor('#334155'),
                           leftIndent=40, rightIndent=40, spaceBefore=2, spaceAfter=2),
        ))
    return [KeepTogether(parts), Spacer(1, 8)]


def _pdf_illustration_image(image_path: str, caption: str, attribution: str, max_w: float = 460, max_h: float = 320) -> list | None:
    """Embeds a real photo (Wikipedia topic image) or map (OpenStreetMap)
    into the PDF flow, with a caption and a small attribution line
    underneath. Reads the file's actual dimensions via PIL so Wikipedia's
    variable-aspect-ratio photos aren't stretched — the OSM map's fixed
    640x420 ratio is just a special case of the same math."""
    full_path = os.path.join(os.path.dirname(__file__), "..", image_path.lstrip("/"))
    if not os.path.exists(full_path):
        return None
    try:
        with PILImage.open(full_path) as img:
            iw, ih = img.size
    except Exception:
        return None
    w, h = max_w, max_w * ih / iw
    if h > max_h:
        h = max_h
        w = max_h * iw / ih
    elements = [
        Spacer(1, 4),
        _PdfFlowableImage(full_path, width=w, height=h, hAlign='CENTER'),
    ]
    if caption:
        cap_style = ParagraphStyle(
            name=f'ImgCaption_{abs(hash(caption)) % 100000}', fontName=FONT_NAME_BOLD, fontSize=9.5,
            alignment=TA_CENTER, textColor=HexColor('#334155'), spaceBefore=5, spaceAfter=1,
        )
        # Plain data, never markup: a Wikimedia caption/credit can contain
        # a raw "&" (an author name like "Kaiser&Augstus&Imperator" is
        # real, seen live) which ReportLab's XML parser reads as the start
        # of an entity reference — "&Augstus;" printed literally on the
        # page instead of "&Augstus". _math_markup (what Paragraph runs
        # text through) only escapes text that contains "$" math, so a
        # plain caption/credit with no math in it needs its own escaping
        # here rather than relying on that.
        elements.append(Paragraph(_xml_escape(caption), cap_style))
    if attribution:
        attr_style = ParagraphStyle(
            name=f'ImgAttribution_{abs(hash(attribution)) % 100000}', fontName=FONT_NAME, fontSize=7.5,
            alignment=TA_CENTER, textColor=HexColor('#94A3B8'), spaceAfter=4,
        )
        elements.append(Paragraph(_xml_escape(attribution), attr_style))
    return elements


def _pdf_answer_box(text, accent: str | None = None):
    style = ParagraphStyle(
        name='AnswerBox',
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        textColor=HexColor('#475569'),
        backColor=HexColor(_PDF_LIGHT),
        borderPadding=(6, 8, 6, 8),
        leftIndent=25,
        rightIndent=15,
        spaceAfter=8,
    )
    # No emoji: the embedded font subset has no glyph for 💡 and it
    # printed as an empty box at the head of every explanation. A bar in
    # the accent colour down the left edge carries the same "this is a
    # note" cue and survives black-and-white printing.
    note = Table([[Paragraph(str(text), style)]], colWidths=[470])
    note.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(_PDF_LIGHT)),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, HexColor(accent or _PDF_ACCENT)),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return note


def _pdf_footer():
    elements = []
    elements.append(Spacer(1, 20))
    d = Drawing(500, 20)
    d.add(Rect(0, 0, 500, 20, fillColor=HexColor(_PDF_DARK), strokeColor=None))
    d.add(String(150, 6, 'Dastyor — AI-помощник для учителей', fontName=FONT_NAME, fontSize=8, fillColor=HexColor('#94A3B8')))
    elements.append(d)
    return elements


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='SlideTitle',
        fontName=FONT_NAME_BOLD,
        fontSize=13,
        leading=16,
        textColor=HexColor(_PDF_DARK),
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name='SlideBody',
        fontName=FONT_NAME,
        fontSize=11,
        leading=15,
        textColor=HexColor('#374151'),
        leftIndent=20,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='DocTitle',
        fontName=FONT_NAME_BOLD,
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        textColor=HexColor(_PDF_DARK),
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name='DocSubtitle',
        fontName=FONT_NAME,
        fontSize=12,
        leading=15,
        alignment=TA_CENTER,
        textColor=HexColor('#6B7280'),
        spaceAfter=8,
    ))
    return styles


_COLORS = [_PDF_ACCENT, _PDF_GREEN, _PDF_ORANGE, _PDF_RED, _PDF_PURPLE, '#06B6D4', '#EC4899', '#14B8A6']


_PDF_KONSPEKT_LABELS = {
    'Русский': {
        'objective': 'Цель лекции', 'lecture_plan': 'План лекции', 'references': 'Литература',
        'competencies': 'Компетенции', 'objectives': 'Цели урока', 'key_concepts': 'Ключевые понятия',
        'key_terms': 'Словарь урока', 'fun_facts': 'Интересные факты', 'formulas': 'Формулы',
        'lesson_program': 'План урока', 'tools': 'Материалы', 'warmup': 'Разминка',
        'main_content': 'Основное содержание', 'real_life_examples': 'Примеры из жизни', 'map': 'Карта', 'illustration': 'Иллюстрация', 'diagrams': 'Схемы',
        'pair_work': 'Работа в парах', 'consolidation': 'Закрепление', 'common_mistakes': 'Частые ошибки',
        'group_work': 'Групповая работа', 'group': 'Группа',
        'homework': 'Домашнее задание', 'summary': 'Итоги урока', 'assessment': 'Оценивание',
        'code_blocks': 'Код', 'quick_check': 'Быстрая проверка', 'answer': 'Ответ',
        'worked_examples': 'Решённые примеры', 'solution': 'Решение',
        'practice_problems': 'Практические задачи', 'answers': 'Ответы',
        'plan_note': 'Внимание', 'plan_date': 'Дата', 'plan_class': 'Класс', 'plan_school': 'Школа', 'example': 'Пример', 'warmup': 'Проверка знаний', 'plan_year': 'Учебный год',
        'tag': 'КОНСПЕКТ', 'grade_suffix': 'класс',
    },
    'Таджикский': {
        'objective': 'Мақсади лексия', 'lecture_plan': 'Нақшаи лексия', 'references': 'Адабиёт',
        'competencies': 'Салоҳиятҳо', 'objectives': 'Мақсадҳои дарс', 'key_concepts': 'Мафҳумҳои асосӣ',
        'key_terms': 'Луғати дарс', 'fun_facts': 'Фактҳои ҷолиб', 'formulas': 'Формулаҳо',
        'lesson_program': 'Барномаи дарс', 'tools': 'Воситаҳои аёнӣ', 'warmup': 'Санҷиши дониш',
        'main_content': 'Шиносоӣ бо мазмуни мавзӯъ', 'real_life_examples': 'Дар ҳаёти воқеӣ', 'map': 'Харита', 'illustration': 'Тасвир', 'diagrams': 'Расмҳо',
        'pair_work': 'Кори дунафара', 'consolidation': 'Мустаҳкамкунии дарс', 'common_mistakes': 'Хатогиҳои маъмул',
        'group_work': 'Кори гурӯҳӣ', 'group': 'Гурӯҳи',
        'homework': 'Супориши хонагӣ', 'summary': 'Хулосаи дарс', 'assessment': 'Арзёбӣ',
        'code_blocks': 'Код', 'quick_check': 'Санҷиши зуд', 'answer': 'Ҷавоб',
        'worked_examples': 'Мисолҳои ҳалшуда', 'solution': 'Ҳал',
        'practice_problems': 'Машқҳои мустақил', 'answers': 'Ҷавобҳо',
        'plan_note': 'Диққат', 'plan_date': 'Сана', 'plan_class': 'Синф', 'plan_school': 'Мактаб', 'example': 'Мисоли', 'warmup': 'Санҷиши дониш', 'plan_year': 'Соли таҳсили',
        'tag': 'КОНСПЕКТ', 'grade_suffix': 'синф',
    },
    'English': {
        'objective': 'Objective', 'lecture_plan': 'Lecture plan', 'references': 'References',
        'competencies': 'Competencies', 'objectives': 'Objectives', 'key_concepts': 'Key Concepts',
        'key_terms': 'Lesson Glossary', 'fun_facts': 'Fun Facts', 'formulas': 'Formulas',
        'lesson_program': 'Lesson Program', 'tools': 'Tools', 'warmup': 'Warm-up',
        'main_content': 'Main Content', 'real_life_examples': 'Real Life Examples', 'map': 'Map', 'illustration': 'Illustration', 'diagrams': 'Diagrams',
        'pair_work': 'Pair Work', 'consolidation': 'Consolidation', 'common_mistakes': 'Common Mistakes',
        'group_work': 'Group Work', 'group': 'Group',
        'homework': 'Homework', 'summary': 'Summary', 'assessment': 'Assessment',
        'code_blocks': 'Code', 'quick_check': 'Quick Check', 'answer': 'Answer',
        'worked_examples': 'Worked Examples', 'solution': 'Solution',
        'practice_problems': 'Practice Problems', 'answers': 'Answers',
        'plan_note': 'Note', 'plan_date': 'Date', 'plan_class': 'Class', 'plan_school': 'School', 'example': 'Example', 'warmup': 'Knowledge check', 'plan_year': 'Academic year',
        'tag': 'KONSPEKT', 'grade_suffix': 'grade',
    },
}
_PDF_KONSPEKT_LABELS['Английский'] = _PDF_KONSPEKT_LABELS['English']


def build_konspekt_pdf(content: dict, language: str = 'Русский', doc_type_label: str | None = None, skip_cover: bool = False) -> io.BytesIO:
    """The old body renderer — kept alive for two callers only, both
    below. Everything that generates a real konspekt PDF for a teacher no
    longer reaches this far; see the delegation at the top of the
    function body.

    doc_type_label overrides the "КОНСПЕКТ" tag shown on the cover badge
    and the running-page tag line — used as-is by build_lecture_pdf's
    fallback path to get "ЛЕКЦИЯ" instead, reusing this whole renderer
    rather than a parallel copy: a лекция's content dict simply omits the
    lesson-management fields (competencies/objectives/lesson_program/
    pair_work/consolidation/homework/assessment/tools), which every
    section below is already individually guarded on
    (`if content.get(...)`), so they silently don't render.

    skip_cover=True (build_lecture_pdf's own default) drops the full-bleed
    illustrated cover page entirely."""
    if doc_type_label is None and not skip_cover:
        # A real konspekt download — the only way routers/materials.py
        # calls this — goes to konspekt_builder.py's own renderer
        # instead, UNLESS the template is "nakscha": that one is the
        # official Tajik lesson-plan FORM, not a design choice, and its
        # plan_layout keeps it on the path below, untouched.
        _tmpl_check = get_template(content.get('template') or 'zamonaviy')
        if not _tmpl_check.plan_layout:
            try:
                from app.konspekt_builder import build_konspekt_pdf as _build_modern
                return _build_modern(content, language)
            except Exception as e:
                logger.exception(f"modern konspekt renderer failed, falling back: {e}")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.9 * cm, bottomMargin=1.3 * cm,
                            leftMargin=1.4 * cm, rightMargin=1.4 * cm)
    story = []

    L = dict(_PDF_KONSPEKT_LABELS.get(language, _PDF_KONSPEKT_LABELS['Русский']))
    if doc_type_label:
        L['tag'] = doc_type_label

    title = content.get("title", "Конспект урока")
    subtitle = content.get("subtitle", "")
    subject = content.get("subject", "")
    grade = content.get("grade", "")

    # Full-bleed cover page (drawn directly on page 1's raw canvas via
    # onFirstPage, since it needs to ignore the doc's normal margins
    # entirely) — best-effort like the map/image illustrations, a failed
    # cover should never block the konspekt content itself. Purely
    # graphic/typographic design (gradient + geometric accents), no photo
    # or emoji — see cover_builder.py.
    from app.cover_builder import _academic_year

    cover_png = None
    # The plan sheet DOES get a cover — but its own, not the glossy
    # full-bleed one. The real printed Нақшаи тавзеҳотӣ is a bound folder
    # whose first page is an ornamented title sheet (red heading, blue
    # subject/year/teacher block, subject picture), so cover_builder has a
    # "nakscha" design rebuilt 1:1 from that page. What must not appear in
    # front of a black-and-white school form is the MODERN cover, which is
    # why this used to skip the cover entirely.
    if not skip_cover:
        try:
            from app.cover_builder import build_cover_image
            # "zamonaviy" when content carries no template at all (e.g. a
            # konspekt/лекция generated straight from the wizard, which no
            # longer offers a template choice at all and always means this
            # one) — curriculum's per-day konspekts still set a real explicit
            # value from its own 5-template wizard, so `or` only ever kicks in
            # here, never overriding a real curriculum choice.
            cover_png = build_cover_image(subject, title, grade, language, template_id=content.get("template") or "zamonaviy", doc_type_label=doc_type_label)
        except Exception as e:
            logger.warning(f"Cover generation failed for '{title[:50]}': {e}")

    _plan_sheet = get_template(content.get("template") or "zamonaviy").plan_layout

    # A running footer (title on the left, page number on the right, above
    # a thin rule) on every content page — reads as an actual printed
    # document rather than an export dump. Skipped on the cover itself
    # (page 1, when the cover renders) since that page has its own footer
    # baked into the artwork.
    def _draw_running_footer(canvas_obj, doc_obj):
        # The official plan sheet is dated and numbered the way a school
        # form is: a bare centred page number, nothing else. No rule, no
        # product name, no corner year mark — the year already appears in
        # the sheet's own top matter (see _pdf_plan_body).
        if _plan_sheet:
            canvas_obj.saveState()
            canvas_obj.setFont(MATH_FONT, 10)
            canvas_obj.setFillColor(HexColor('#000000'))
            canvas_obj.drawCentredString(A4[0] / 2, 1.0 * cm, str(doc_obj.page))
            canvas_obj.restoreState()
            return
        canvas_obj.saveState()
        canvas_obj.setStrokeColor(HexColor('#E2E8F0'))
        canvas_obj.setLineWidth(0.6)
        canvas_obj.line(1.6 * cm, 1.0 * cm, A4[0] - 1.6 * cm, 1.0 * cm)
        canvas_obj.setFont(FONT_NAME, 8)
        canvas_obj.setFillColor(HexColor('#94A3B8'))
        canvas_obj.drawString(1.6 * cm, 0.65 * cm, title[:70])
        canvas_obj.drawRightString(A4[0] - 1.6 * cm, 0.65 * cm, f'Dastyor  •  Страница {doc_obj.page}')
        # Faint academic-year mark, top-right corner of every page — the
        # same value the cover's own badge shows, computed fresh on every
        # render (see cover_builder._academic_year: Aug-Dec -> current/
        # next year, Jan-Jul -> previous/current year), so it rolls over
        # to "2027-2028" etc. on its own each school year — never
        # hardcoded, never needs updating by hand.
        canvas_obj.setFont(FONT_NAME, 7.5)
        canvas_obj.setFillColor(HexColor('#CBD5E1'))
        canvas_obj.drawRightString(A4[0] - 1.6 * cm, A4[1] - 0.7 * cm, _academic_year())
        canvas_obj.restoreState()

    def _draw_cover(canvas_obj, doc_obj):
        if not cover_png:
            _draw_running_footer(canvas_obj, doc_obj)
            return
        canvas_obj.drawImage(ImageReader(io.BytesIO(cover_png)), 0, 0, width=A4[0], height=A4[1])

    if cover_png:
        from reportlab.platypus import PageBreak
        story.append(PageBreak())

    tag_line = L['tag']
    if subject:
        tag_line += f"  •  {subject}"
    if grade:
        tag_line += f"  •  {_format_grade(grade, L['grade_suffix'])}"

    _tmpl = get_template(content.get("template") or "zamonaviy")
    accent_hex = get_subject_accent_hex(subject)

    # The two Wikimedia Commons teaching illustrations are NOT placed
    # here. Each one carries the section it explains
    # (image["position_after"], see ai_service._place_lesson_images) and
    # the body renderers below print it under that section's own text —
    # a diagram belongs in the middle of the explanation it illustrates,
    # not parked at the top of the first page that had room for it.
    if _tmpl.plan_layout:
        # The plan sheet carries its own top matter and centred title — the
        # standard masthead would duplicate both.
        body = _pdf_plan_body(content, L)
    elif content.get("lecture_plan") or content.get("objective"):
        # A лекция gets its own masthead — see _pdf_lecture_masthead. It
        # used to borrow the konspekt's filled dark block, which made the
        # two documents look like the same thing.
        story.extend(_pdf_lecture_masthead(
            title, subtitle, subject, grade, language, L['grade_suffix']))
        body = _add_konspekt_body_pdf(content, L)
    else:
        story.extend(_pdf_header(
            title, subtitle, tag_line,
            accent=accent_hex,
            minimal=_tmpl.minimal_chrome,
        ))
        body = _add_konspekt_body_pdf(content, L)

    story.extend(body)

    doc.build(story, onFirstPage=_draw_cover, onLaterPages=_draw_running_footer)
    buf.seek(0)
    return buf


# tag shown on a lecture's cover badge / running-page line, per language —
# same role as _PDF_KONSPEKT_LABELS['tag'] but this is the one word a
# лекция's own vocabulary differs from a конспект's.
_LECTURE_TAG = {
    'Русский': 'ЛЕКЦИЯ', 'Таджикский': 'ЛЕКСИЯ', 'English': 'LECTURE',
    'Английский': 'LECTURE',
}


def build_lecture_pdf(content: dict, language: str = 'Русский') -> io.BytesIO:
    """The лекция, built by its own renderer (app/lecture_builder.py).

    It used to be build_konspekt_pdf with a different masthead: same
    numbered sections, same bullets, same undivided prose. That is why a
    lecture read as generated text — structurally it WAS a konspekt. The
    lecture now has a cover page, a contents page, sub-headings inside
    the body, definition blocks, "Важно"/"Пример" callouts placed where
    they belong, a self-check and conclusions — and four designs to print
    it in.

    Imported here rather than at module scope because lecture_builder
    imports this module's fonts and flowables."""
    from app.lecture_builder import build_lecture_pdf as _build
    try:
        return _build(content, language)
    except Exception as e:
        # A lecture that fails to render must still download: the old
        # konspekt-shaped path stays as the fallback rather than handing
        # the teacher an error.
        logger.exception(f"lecture renderer failed, falling back: {e}")
        tag = _LECTURE_TAG.get(language, _LECTURE_TAG['Русский'])
        return build_konspekt_pdf(content, language, doc_type_label=tag, skip_cover=True)


def _pdf_important_note(text: str, accent_hex: str) -> Table:
    """A single 'pay attention' callout — a left-accent-bar + tinted-box
    Table (reportlab has no native bordered-callout flowable), matching the
    docx export's _add_important_note look. Uses a plain "!" rather than an
    emoji glyph (e.g. ☝) — Arial (this PDF's registered font) is missing
    most emoji codepoints and silently renders them as a tofu box, the
    same class of issue already worked around elsewhere in this file."""
    style = ParagraphStyle(
        name=f'ImportantNote_{abs(hash(text)) % 100000}', fontName=FONT_NAME, fontSize=9.5,
        leading=13, textColor=HexColor('#7F1D1D'),
    )
    t = Table([[Paragraph(f'<b>!</b> <i>{text}</i>', style)]], colWidths=[470])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor(_PDF_BRAND_SOFT)),
        ('LINEBEFORE', (0, 0), (0, -1), 3, HexColor(accent_hex)),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def _pdf_code_card(code: str, language: str, explanation: str, accent_hex: str) -> list:
    """PDF counterpart to docx_builder._add_code_card — a dark 'code
    editor' Table (accent-colored language badge row on top of a dark
    monospaced body), matching the docx export's look. XML-escapes the
    code first since reportlab's Paragraph markup treats <, >, & as
    markup — real code (e.g. "#include <iostream>") would otherwise
    silently break the layout or drop characters."""
    escaped = (
        code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')
    )
    badge_style = ParagraphStyle(
        name=f'CodeBadge_{abs(hash(code)) % 100000}', fontName=FONT_NAME_BOLD, fontSize=8,
        textColor=HexColor('#FFFFFF'),
    )
    code_style = ParagraphStyle(
        name=f'Code_{abs(hash(code)) % 100000}', fontName=CODE_FONT, fontSize=9, leading=13,
        textColor=HexColor('#E2E8F0'),
    )
    t = Table(
        [[Paragraph((language or 'code').upper(), badge_style)], [Paragraph(escaped, code_style)]],
        colWidths=[470],
    )
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), HexColor(accent_hex)),
        ('BACKGROUND', (0, 1), (0, 1), HexColor('#1E293B')),
        ('TOPPADDING', (0, 0), (0, 0), 3), ('BOTTOMPADDING', (0, 0), (0, 0), 3),
        ('LEFTPADDING', (0, 0), (0, 0), 10), ('RIGHTPADDING', (0, 0), (0, 0), 8),
        ('TOPPADDING', (0, 1), (0, 1), 8), ('BOTTOMPADDING', (0, 1), (0, 1), 8),
        ('LEFTPADDING', (0, 1), (0, 1), 10), ('RIGHTPADDING', (0, 1), (0, 1), 8),
    ]))
    elements = [t]
    if explanation:
        expl_style = ParagraphStyle(
            name=f'CodeExpl_{abs(hash(explanation)) % 100000}', fontName=FONT_NAME, fontSize=9.5,
            leading=12, textColor=HexColor('#64748B'), spaceBefore=4, spaceAfter=6,
        )
        elements.append(Paragraph(f'<i>{explanation}</i>', expl_style))
    else:
        elements.append(Spacer(1, 6))
    return [KeepTogether(elements)]


def _pdf_quick_check(items: list, accent_hex: str, answer_label: str) -> list:
    """PDF counterpart to docx_builder._add_quick_check — one soft-green
    left-accent-bar Table per Q&A pair, same visual family as
    _pdf_important_note (a callout box, not another bullet)."""
    elements = []
    for item in items:
        if not isinstance(item, dict):
            continue
        question = item.get('question', '')
        answer = item.get('answer', '')
        if not question:
            continue
        q_style = ParagraphStyle(
            name=f'QCQ_{abs(hash(question)) % 100000}', fontName=FONT_NAME, fontSize=9.5,
            leading=13, textColor=HexColor('#1F2937'),
        )
        rows = [[Paragraph(f'<b>?</b>&nbsp;&nbsp;{question}', q_style)]]
        if answer:
            a_style = ParagraphStyle(
                name=f'QCA_{abs(hash(answer)) % 100000}', fontName=FONT_NAME, fontSize=9,
                leading=12, textColor=HexColor('#166534'),
            )
            rows.append([Paragraph(f'<b>{answer_label}:</b> <i>{answer}</i>', a_style)])
        t = Table(rows, colWidths=[470])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F0FDF4')),
            ('LINEBEFORE', (0, 0), (0, -1), 3, HexColor(accent_hex)),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 4))
    return elements


def _pdf_worked_examples(items: list, accent_hex: str, solution_label: str, minimal: bool = False) -> list:
    """PDF counterpart to docx_builder._add_worked_examples — solved 'misol'
    problems (Математика/Алгебра/Геометрия only — see ai_service.py's
    _WORKED_EXAMPLE_SUBJECTS), each as its own card: a solid accent-colored
    square carrying the problem number, and beside it the problem statement
    over its step-by-step solution on a light tint.

    Same reasoning as the docx side for the badge column over a plain
    left-bar callout: at 8-12 examples the flat tinted boxes ran together
    into one slab, and the number gives each example an anchor to scan by.
    Each card is wrapped in KeepTogether so a problem is never split from
    its own solution across a page break. The number lives only in the
    badge — an inline "Пример N." label beside it just restated it, and the
    section heading above already names these as examples."""
    elements = []
    tint = _pdf_light_tint_hex(accent_hex, amount=0.93)
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        problem = item.get('problem', '')
        solution = item.get('solution', '')
        if not problem:
            continue
        n_style = ParagraphStyle(
            name=f'WEN_{i}_{abs(hash(problem)) % 100000}', fontName=FONT_NAME_BOLD, fontSize=13,
            leading=16,
            # White on the filled badge; the accent colour directly on the
            # page when there is no badge to sit on.
            textColor=HexColor(accent_hex if minimal else '#FFFFFF'),
            alignment=1,
        )
        p_style = ParagraphStyle(
            name=f'WEP_{abs(hash(problem)) % 100000}', fontName=FONT_NAME, fontSize=9.5,
            leading=13, textColor=HexColor('#1F2937'),
        )
        body = [Paragraph(f'<b>{problem}</b>', p_style)]
        if solution:
            s_style = ParagraphStyle(
                name=f'WES_{abs(hash(solution)) % 100000}', fontName=FONT_NAME, fontSize=9,
                leading=12.5, textColor=HexColor('#334155'), spaceBefore=3,
            )
            body.append(Paragraph(
                f'<font color="#1D4ED8"><b>{solution_label}:</b></font> {solution}', s_style,
            ))
        t = Table([[Paragraph(str(i + 1), n_style), body]], colWidths=[26, 444])
        if minimal:
            # Number in the accent colour on the page itself, and a single
            # hairline rule under each example instead of a filled badge
            # and tinted panel.
            style = [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, HexColor('#E2E8F0')),
                ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (0, 0), 0), ('RIGHTPADDING', (0, 0), (0, 0), 6),
                ('LEFTPADDING', (1, 0), (1, 0), 0), ('RIGHTPADDING', (1, 0), (1, 0), 0),
            ]
        else:
            style = [
                ('BACKGROUND', (0, 0), (0, 0), HexColor(accent_hex)),
                ('BACKGROUND', (1, 0), (1, 0), HexColor(tint)),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (0, 0), 2), ('RIGHTPADDING', (0, 0), (0, 0), 2),
                ('LEFTPADDING', (1, 0), (1, 0), 10), ('RIGHTPADDING', (1, 0), (1, 0), 10),
            ]
        t.setStyle(TableStyle(style))
        elements.append(KeepTogether([t, Spacer(1, 5)]))
    return elements


def _pdf_sidebar_panel(content: dict, sections: tuple, accent_hex: str, L: dict) -> list:
    """"zamonaviy" template only — PDF counterpart to docx_builder.py's
    _add_sidebar_panel: a single tinted Table cell holding the given
    section keys (e.g. key_concepts/key_terms/tools) as a standalone
    reference panel, rendered once right after the header instead of
    those sections appearing inline later."""
    rows_present = [(key, content.get(key)) for key in sections if content.get(key)]
    if not rows_present:
        return []
    tint = _pdf_light_tint_hex(accent_hex, amount=0.92)
    cell_elements = []
    for key, items in rows_present:
        header_style = ParagraphStyle(
            name=f'SidebarHdr_{key}', fontName=FONT_NAME_BOLD, fontSize=8.5,
            textColor=HexColor(accent_hex), spaceBefore=6, spaceAfter=2,
        )
        cell_elements.append(Paragraph(L.get(key, key).upper(), header_style))
        item_style = ParagraphStyle(
            name=f'SidebarItem_{key}', fontName=FONT_NAME, fontSize=9.5,
            leading=12, textColor=HexColor(_PDF_DARK), leftIndent=8, spaceAfter=3,
        )
        for item in items:
            cell_elements.append(Paragraph(f'•&nbsp;&nbsp;{item}', item_style))
    t = Table([[cell_elements]], colWidths=[470])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor(tint)),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    return [Spacer(1, 4), t, Spacer(1, 8)]


# The usable text width of a konspekt/lecture page: A4 less the 1.4cm
# margins build_konspekt_pdf sets, with a little slack so a table's own
# border never touches the margin.
_VISUAL_TABLE_WIDTH = 500.0


_LECTURE_SUMMARY_LABEL = {
    'Русский': 'Выводы', 'Таджикский': 'Хулосаҳо',
    'English': 'Conclusions',
}
_LECTURE_SUMMARY_LABEL['Английский'] = _LECTURE_SUMMARY_LABEL['English']


def _pdf_visual_block(block: dict, accent_hex: str, minimal: bool = False,
                      serif: bool = False) -> list:
    """PDF counterpart to docx_builder._add_visual_block — renders one
    AI-chosen structured visual (table/timeline/flowchart/process/
    comparison/concept_map). Returns a list of flowables; an unrecognized
    or malformed block is skipped (returns []) rather than raising, since a
    cosmetic extra shouldn't be able to break the whole export."""
    btype = block.get('type')
    data = block.get('data') or {}
    elements = []
    # A small italic caption, not a bold numbered section heading — this
    # block sits right inside the section it illustrates (see
    # position_after), so it should read as part of that explanation, not
    # as its own separate titled chapter.
    title = block.get('title')
    if title:
        cap_style = ParagraphStyle(
            name=f'VisualBlockCaption_{abs(hash(title)) % 100000}', fontName=FONT_NAME, fontSize=9.5,
            # A coloured caption is the odd one out on an otherwise black
            # and white sheet.
            textColor=HexColor('#000000' if minimal else '#64748B'), spaceBefore=6, spaceAfter=3,
        )
        elements.append(Paragraph(f'<i>{title}</i>', cap_style))

    try:
        if btype in ('table', 'comparison'):
            if btype == 'table':
                headers = data.get('headers') or []
                rows = data.get('rows') or []
            else:
                criteria = data.get('criteria') or []
                items = data.get('items') or []
                headers = [''] + criteria
                rows = [[it.get('name', '')] + list(it.get('values') or []) for it in items]
            if not headers or not rows:
                return []
            # On the plan sheet the cells are Paragraphs, not raw strings,
            # so a cell holding "$2x + 5$" is typeset like the rest of the
            # document instead of printing its dollar signs. Only the
            # minimal branch does this: the other templates size their
            # tables around plain strings and Paragraph cells would change
            # their column widths.
            # Every cell is a Paragraph and every column has an explicit
            # width. Without colWidths ReportLab sizes the columns to
            # whatever the longest string needs, and a four-column
            # comparison of full phrases came out wider than the page —
            # centred, so it bled off BOTH edges and the first column's
            # text was cut in half. Widths are shared out in proportion to
            # how much text each column actually holds, with a floor so a
            # short column stays readable.
            col_count = max(1, len(headers))
            weights = []
            for c in range(col_count):
                longest = max([len(str(headers[c]))] +
                              [len(str(r[c])) for r in rows if c < len(r)] or [1])
                weights.append(max(6, longest))
            total_w = _VISUAL_TABLE_WIDTH
            min_w = min(52.0, total_w / col_count)
            free = total_w - min_w * col_count
            weight_sum = sum(weights) or 1
            col_widths = [min_w + free * (w / weight_sum) for w in weights]

            cell_style = ParagraphStyle(
                name='VisCell', fontName=FONT_NAME, fontSize=9, leading=12,
                alignment=TA_CENTER,
                textColor=HexColor('#000000' if minimal else '#1F2937'))
            head_style = ParagraphStyle(
                name='VisCellHead', parent=cell_style, fontName=FONT_NAME_BOLD,
                textColor=HexColor(accent_hex if minimal else '#FFFFFF'))
            headers = [Paragraph(_math_inline(str(h), 9), head_style) for h in headers]
            rows = [[Paragraph(_math_inline(str(c), 9), cell_style) for c in row]
                    for row in rows]
            t = Table([headers] + rows, colWidths=col_widths, hAlign='CENTER')
            t.setStyle(TableStyle([
            ] + ([] if minimal else [
                ('BACKGROUND', (0, 0), (-1, 0), HexColor(accent_hex)),
            ]) + [
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor(accent_hex if minimal else '#FFFFFF')),
                ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
                ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ] + ([
                # Ruled, not boxed: a hairline under the header and between
                # rows carries the structure without any fill.
                ('LINEBELOW', (0, 0), (-1, 0), 0.8, HexColor(accent_hex)),
                ('LINEBELOW', (0, 1), (-1, -2), 0.4, HexColor('#E2E8F0')),
            ] if minimal else [
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#FEF2F2')]),
            ])))
            elements.extend([Spacer(1, 2), t, Spacer(1, 4)])

        elif btype == 'timeline':
            # Dated notes, for the same reasons the process strip became
            # notes: the generated card-and-node infographic could not be
            # edited, clipped its own labels once the events had real
            # wording, and looked like nothing else in the document. The
            # saved `image` is ignored so konspekts made before this
            # change print as notes too.
            events = data.get('events') or []
            if events:
                elements.append(Spacer(1, 2))
                for ev in events:
                    date = str(ev.get('date', '')).strip()
                    label = str(ev.get('label', '')).strip()
                    head = (f'<font color="{accent_hex}"><b>{date}</b></font>&nbsp;&nbsp;' if date else '')
                    elements.append(Paragraph(
                        f'{head}<b>{label}</b>',
                        ParagraphStyle(
                            name=f'TlT{abs(hash(label + date)) % 99999}',
                            fontName=MATH_FONT_BOLD if serif else FONT_NAME_BOLD,
                            fontSize=11 if serif else 10.5, leading=15 if serif else 14,
                            textColor=HexColor(_LECTURE_INK if serif else _PDF_DARK),
                            leftIndent=22, firstLineIndent=-22, spaceBefore=5, spaceAfter=1)))
                    if ev.get('description'):
                        elements.append(Paragraph(
                            str(ev['description']),
                            ParagraphStyle(
                                name=f'TlD{abs(hash(str(ev["description"]))) % 99999}',
                                fontName=MATH_FONT if serif else FONT_NAME,
                                fontSize=10 if serif else 9.5, leading=14 if serif else 13,
                                textColor=HexColor(_LECTURE_MUTED if serif else '#475569'),
                                leftIndent=22, spaceAfter=2)))
                elements.append(Spacer(1, 4))

        elif btype in ('flowchart', 'process'):
            # Conspect notes: a numbered heading with its explanation
            # under it, down the page.
            #
            # This replaced a generated PNG of coloured cards joined by
            # arrows (timeline_builder.build_process_image), the same
            # thing already taken out of the slides. The strip was sized
            # for four short cards, so real sentences overflowed their
            # boxes; it was a picture, so a teacher could not correct a
            # typo in it; and its palette had nothing to do with the
            # document around it. Plain text on one grid has none of
            # those problems and IS what a lesson note looks like.
            steps = data.get('steps') or []
            if steps:
                elements.append(Spacer(1, 2))
                for i, step in enumerate(steps):
                    title = str(step.get('title', '')).strip()
                    desc = str(step.get('description', '')).strip()
                    if title:
                        elements.append(Paragraph(
                            f'<font color="{accent_hex}"><b>{i + 1}.</b></font>'
                            f'&nbsp;&nbsp;<b>{title}</b>',
                            ParagraphStyle(
                                name=f'StepT{abs(hash(title)) % 99999}',
                                fontName=MATH_FONT_BOLD if serif else FONT_NAME_BOLD,
                                fontSize=11 if serif else 10.5, leading=15 if serif else 14,
                                textColor=HexColor(_LECTURE_INK if serif else _PDF_DARK),
                                leftIndent=22, firstLineIndent=-22, spaceBefore=5, spaceAfter=1)))
                    if desc:
                        elements.append(Paragraph(
                            desc,
                            ParagraphStyle(
                                name=f'StepD{abs(hash(desc)) % 99999}',
                                fontName=MATH_FONT if serif else FONT_NAME,
                                fontSize=10 if serif else 9.5, leading=14 if serif else 13,
                                textColor=HexColor(_LECTURE_MUTED if serif else '#475569'),
                                leftIndent=22, spaceAfter=2)))
                elements.append(Spacer(1, 4))

        elif btype == 'figure':
            # A figure_builder line drawing (see ai_service.py's
            # _render_slide_figures) — same {"image", "caption"} shape as
            # a konspekt's subject figure, so the existing helper draws it
            # identically rather than duplicating its box-fit math here.
            elements.extend(_pdf_subject_figure(block, minimal=minimal, max_w=340, max_h=260))

        elif btype == 'chart':
            # No reportlab chart primitive wired up here (yet) — falls back
            # to a plain data table instead of the real bar/pie/line chart
            # the PPTX export draws (see _pptx_visual_block), which would
            # otherwise silently render NOTHING for this slide's whole
            # visual in the PDF (btype not matching any branch above just
            # returns [] from the try/except). A table is a legitimate way
            # to read the same numbers, if not as pretty as a chart.
            categories = [str(c) for c in (data.get('categories') or [])]
            series = data.get('series') or []
            if categories and series:
                headers = [''] + categories
                rows = [[str(s.get('name', ''))] + [str(v) for v in (s.get('values') or [])] for s in series]
                t = Table([headers] + rows, hAlign='CENTER')
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor(accent_hex)),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
                    ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
                    ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#E2E8F0')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#FEF2F2')]),
                    ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                elements.extend([Spacer(1, 2), t, Spacer(1, 4)])

        elif btype == 'concept_map':
            # A real generated network diagram (nodes in a circle, labeled
            # edges — see timeline_builder.py) instead of a bullet list.
            # Falls back to the list below only for older konspekts saved
            # before this existed, or if the image failed to render.
            # Written out as relations rather than drawn as a ring of
            # nodes — same decision as the timeline and the process strip:
            # the generated diagram was an uneditable picture whose labels
            # collided as soon as the concepts had real names.
            nodes = {n.get('id'): n.get('label', n.get('id', '')) for n in (data.get('nodes') or [])}
            for edge in (data.get('edges') or []):
                frm = nodes.get(edge.get('from'), edge.get('from', ''))
                to = nodes.get(edge.get('to'), edge.get('to', ''))
                text = f'<b>{frm}</b> &nbsp;→&nbsp; <b>{to}</b>'
                if edge.get('label'):
                    text += f" — {edge['label']}"
                elements.append(_pdf_bullet(text, accent_hex, serif=serif))
    except Exception:
        return []
    if not elements:
        return elements
    # Small blocks (a short bullet fallback, or a capped-size infographic
    # image — max_h 120-220pt, a fraction of a page) get KeepTogether: a
    # caption like "Сохти асосии Python" ending up alone at the bottom of
    # a page with its diagram pushed to the next one is a real, visible
    # orphaning bug worth this. table/comparison/chart are the opposite
    # case — potentially many rows, so forcing the WHOLE table onto a
    # fresh page when it doesn't fit the remainder of the current one
    # left a much bigger blank gap behind than the orphaning problem this
    # was meant to solve (this got noticeably worse once visual_blocks
    # started spreading across the whole document instead of clustering
    # in one spot — see the position_after fix above). Table already
    # splits across pages at row boundaries on its own without this
    # wrapper, so it's left to flow naturally instead.
    if btype in ('table', 'comparison', 'chart'):
        return elements
    return [KeepTogether(elements)]


# ── "Нақшаи тавзеҳотӣ" plan layout ───────────────────────────────────────────
# Reproduces the official Tajik school lesson-plan sheet a teacher actually
# hands in: no colour, no cards, no numbered chapter blocks. A run-in
# heading (bold italic, text continuing on the SAME line) is the whole
# structure, exactly as in the printed original.

# Sections that read as one flowing paragraph after their heading, in the
# order the real document uses them.
_PLAN_RUN_IN = [
    ("tools", "prose"),
    ("main_content", "prose"),
    ("lesson_program", "prose"),
    ("pair_work", "prose"),
    ("consolidation", "prose"),
    ("summary", "prose"),
    ("assessment", "prose"),
]

# Sections printed as a bulleted list under their own heading line.
_PLAN_BULLETS = ["objectives", "key_concepts", "key_terms", "real_life_examples", "group_work", "homework"]

# Sections the teacher fills in by hand on the printed sheet — ruled blanks
# when we have nothing for them, rather than the heading silently vanishing.
_PLAN_FILL_IN = ["competencies", "warmup"]


# Soft blue accents for the nakscha sheet. Deliberately a narrow set: one
# panel fill, one bar/rule colour, one ink, one stronger tint for the
# inline marker. The sheet is otherwise black on white and the whole point
# of the highlight is that the eye lands on four or five places per page —
# a second and third accent colour would undo that.
_PLAN_BG = "#EAF3FB"      # panel fill
_PLAN_BAR = "#8FBEDC"      # left bar and heading rule
_PLAN_INK = "#1B4460"      # heading text
_PLAN_MARK = "#D3E7F6"     # inline marker, a shade stronger than the panel
# Worked examples get their OWN, lighter tint rather than the panel fill.
# There can be twenty of them on a page; at panel strength the section
# would outweigh the key concepts and formulas it is meant to support, and
# the page would read as one solid blue block. Lighter keeps the hierarchy:
# panels first, examples second, prose plain.
_PLAN_EX_BG = "#F4F9FD"


def _plan_panel(flowables, width=470, bar=True):
    """Wraps content in a soft blue panel with a left accent bar.

    A Table is the only flowable that can carry a background behind other
    flowables, so the panel is a one-cell table rather than a drawing —
    which also means it splits across a page break instead of being pushed
    whole onto the next page and leaving a gap."""
    t = Table([[flowables]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(_PLAN_BG)),
    ] + ([("LINEBEFORE", (0, 0), (0, -1), 2.5, HexColor(_PLAN_BAR))] if bar else []) + [
        ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return [Spacer(1, 4), t, Spacer(1, 8)]


def _plan_feature_head(text, S, badge=None):
    """A filled heading for the one section a teacher flips straight to.

    The ordinary heading() is ink over a hairline — right for fifteen
    sections in a row, but it makes the examples section look like just
    another paragraph title when it is the longest and most used part of
    the sheet. Filled, with the count on the right, it is findable by
    thumbing through the pages."""
    cells = [Paragraph(f"<b>{text}</b>", S["head"])]
    widths = [470]
    if badge:
        cells.append(Paragraph(
            f'<para alignment="right">{badge}</para>',
            ParagraphStyle(name="PlanBadge", parent=S["head"], fontSize=9.5),
        ))
        widths = [370, 100]
    t = Table([cells], colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(_PLAN_BG)),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, HexColor(_PLAN_BAR)),
        ("LEFTPADDING", (0, 0), (0, -1), 11), ("RIGHTPADDING", (-1, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return [Spacer(1, 6), t, Spacer(1, 6)]


def _plan_example_card(label, problem, solution, S):
    """One example as its own tinted card with a blue edge.

    A card each — rather than one long bullet list — is what separates the
    twenty of them from the prose around them, and it also means a page
    break falls BETWEEN two examples instead of between a problem and its
    own solution."""
    inner = [Paragraph(f'<b>{label}</b> {problem}', S["ex"])]
    if solution:
        inner.append(Paragraph(solution, S["exsol"]))
    t = Table([[inner]], colWidths=[470])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(_PLAN_EX_BG)),
        ("LINEBEFORE", (0, 0), (0, -1), 2, HexColor(_PLAN_BAR)),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return [t, Spacer(1, 5)]


# "Натиҷа" (result) turns up as often as "Ҷавоб" (answer) in the model's
# solutions, and a whole document's answers went unmarked because only the
# latter was listed. Same for the Russian and English pairs.
_ANSWER_WORDS = ("ҷавоб", "җавоб", "жавоб", "javob", "ответ", "answer",
                 "натиҷа", "натича", "натижа", "natija", "результат", "result")


def _plan_mark_answer(text: str) -> str:
    """Marks the final answer of a worked example with an inline tint.

    Twenty examples each in their own panel would turn the page into a
    stack of boxes, so the answer alone is marked instead — the way a
    teacher runs a highlighter over the result and nothing else. Matching
    on the answer WORD rather than on punctuation because the solutions are
    written in four languages and end in no consistent shape."""
    body = str(text or "")
    low = body.lower()
    cut = max((low.rfind(w) for w in _ANSWER_WORDS), default=-1)
    if cut < 0:
        return body
    head, tail = body[:cut], body[cut:]
    # The tail cannot simply be wrapped: ReportLab draws the backColor
    # rectangle but DROPS any inline image inside it, so an answer like
    # "Ҷавоб: $x_1 = -2$" came out as a blue box with nothing in it.
    # Text runs get the highlight; formulas are rendered onto the same
    # colour instead, which looks identical and actually appears.
    out = []
    pos = 0
    for m in _MATH_SPAN.finditer(tail):
        text = tail[pos:m.start()]
        if text:
            # The space that separates the label from the formula has to
            # sit OUTSIDE the closing tag. ReportLab extends a backColor
            # rectangle over an inline image that follows it immediately,
            # hiding it completely — one ordinary character in between is
            # enough to stop that, and a trailing space is one we already
            # have.
            body, sep = text.rstrip(), text[len(text.rstrip()):] or " "
            if body:
                out.append(f'<font backColor="{_PLAN_MARK}"><b>{body}</b></font>')
            out.append(sep)
        got = _math_png(m.group(1), 10.5, _PLAN_MARK)
        if got:
            path, w, asc, desc = got
            out.append(f'<img src="{path}" width="{w + 2 * _MATH_PAD:.1f}" '
                       f'height="{asc + desc + 2 * _MATH_PAD:.1f}" '
                       f'valign="{-(desc + _MATH_PAD):.1f}"/>')
        else:
            out.append(f'<font backColor="{_PLAN_MARK}"><b>{m.group(1)}</b></font>')
        pos = m.end()
    rest = tail[pos:]
    if rest:
        out.append(f'<font backColor="{_PLAN_MARK}"><b>{rest}</b></font>')
    return head + "".join(out)


def _plan_styles():
    body = ParagraphStyle(
        name="PlanBody", fontName=MATH_FONT, fontSize=11, leading=15,
        alignment=TA_JUSTIFY, textColor=HexColor("#000000"), spaceAfter=6,
    )
    return {
        "body": body,
        "bullet": ParagraphStyle(
            name="PlanBullet", parent=body, alignment=TA_LEFT,
            leftIndent=22, firstLineIndent=-11, spaceAfter=2,
        ),
        "head": ParagraphStyle(
            name="PlanHead", fontName=MATH_FONT_BOLD, fontSize=11, leading=14,
            textColor=HexColor(_PLAN_INK), spaceBefore=0, spaceAfter=0,
        ),
        "title": ParagraphStyle(
            name="PlanTitle", fontName=MATH_FONT_BOLD, fontSize=16, leading=20,
            alignment=TA_CENTER, textColor=HexColor("#000000"),
            spaceBefore=0, spaceAfter=8,
        ),
        # Inside an example card the hanging-indent bullet style is wrong —
        # the card's own padding already sets the text in, and the bullet
        # indent on top of it pushed every line off-centre in the card.
        # Leading is generous because these lines carry inline formula
        # images: a stacked fraction is roughly half again the height of a
        # line of text, and at the text leading consecutive lines clipped
        # into each other.
        "ex": ParagraphStyle(
            name="PlanEx", parent=body, alignment=TA_LEFT, leading=22, spaceAfter=2,
        ),
        "exsol": ParagraphStyle(
            name="PlanExSol", parent=body, alignment=TA_LEFT,
            leftIndent=13, fontSize=10.5, leading=21, spaceAfter=0,
        ),
        "meta": ParagraphStyle(
            name="PlanMeta", fontName=MATH_FONT, fontSize=10.5, leading=14,
            textColor=HexColor("#000000"),
        ),
    }


def _plan_rule(width=470, count=2):
    """The ruled blanks the printed sheet leaves for handwriting."""
    out = []
    for _ in range(count):
        t = Table([[""]], colWidths=[width], rowHeights=[15])
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.6, HexColor("#000000")),
            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        out.append(t)
    out.append(Spacer(1, 4))
    return out


def _plan_flatten(value):
    """A section is a string or a list of strings — both end up as prose.

    List items are separated by "; " rather than a bare space: run together
    with nothing between them, a tools list read as one collapsed sentence
    ("Интерактивная доска: ... Карточки-подсказки: ...") with no visible
    boundary between the entries."""
    if isinstance(value, list):
        parts = [str(v).strip().rstrip(".") for v in value if v]
        return "; ".join(parts) + ("." if parts else "")
    return str(value or "")


def _pdf_plan_body(content: dict, L: dict) -> list:
    """Full body for the nakscha template — see KonspektTemplate.plan_layout.

    Heavy items (tables, code, formulas, worked examples) are DEALT OUT one
    per section boundary rather than placed at the anchor the model chose.
    Honouring "position_after" sounded right and was tried first, but the
    model reliably anchors several blocks to the same one or two sections
    (usually main_content), so every table and code block still landed
    together on one page while the next page stayed an unbroken wall of
    text. Dealing them round-robin is what actually spreads them."""
    S = _plan_styles()
    story = []

    # ── masthead ────────────────────────────────────────────────────────
    # The date/class/school line is laid out as a real 3-column row rather
    # than one string padded with &nbsp;: the padded version drifted out of
    # alignment as soon as the grade string changed length, and the sheet's
    # whole credibility rests on looking like a printed form.
    from app.cover_builder import _academic_year
    grade = str(content.get("grade") or "")
    subject = str(content.get("subject") or "")
    language = str(content.get("language") or "Русский")

    story.append(Paragraph(
        f'<para alignment="right">{L.get("plan_year", "Соли таҳсили")} {_academic_year()}</para>',
        ParagraphStyle(name="PlanYear", parent=S["meta"], alignment=TA_RIGHT),
    ))
    fill = Table(
        [[Paragraph(f'{L.get("plan_date", "Сана")} ____________', S["meta"]),
          # Always the bare number behind THIS document's own "Синф"/
          # "Class" label (L is already keyed to `language`) — the create
          # form sends "N класс" in Russian no matter what language was
          # picked (see _GRADE_WORDS), so using the grade string as-is
          # whenever it happened to already contain *a* grade-word used to
          # print the Russian word right next to an otherwise fully
          # translated label.
          Paragraph(
              f'{L.get("plan_class", "Синф")} {_bare_grade(grade) or grade or "________"}',
              S["meta"],
          ),
          Paragraph(f'{L.get("plan_school", "Мактаб")} ____________', S["meta"])]],
        colWidths=[160, 150, 160],
    )
    fill.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    story.append(fill)
    story.append(Spacer(1, 14))

    # Subject sits above the title as spaced small caps — the one piece of
    # information the plain masthead was missing, and it gives the title
    # something to sit under instead of floating alone.
    if subject:
        story.append(Paragraph(
            "&nbsp;".join(_display_subject(subject, language).upper()),
            ParagraphStyle(name="PlanSubject", parent=S["meta"], fontName=MATH_FONT_BOLD,
                           fontSize=8.5, alignment=TA_CENTER, spaceAfter=4),
        ))
    story.append(Paragraph(str(content.get("title") or "").upper(), S["title"]))
    # Short centred rule under the title, the way the printed form breaks
    # its header off from the body.
    rule = Table([[""]], colWidths=[120], rowHeights=[1.6])
    rule.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(_PLAN_BAR)),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(Table([[rule]], colWidths=[470], style=TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ])))
    # End of the printed form's own header — everything above is the
    # date/class/school line and the sheet's title, which nothing may be
    # inserted in front of. See _pdf_body_splice_index.
    story.append(_PdfContentAnchor())

    def heading(text):
        """Blue ink over a hairline blue rule.

        A filled band behind every heading was the first attempt and the
        sheet came out striped — fifteen sections meant fifteen bands, and
        the panels that are meant to stand out stopped standing out. The
        rule organises without competing."""
        t = Table([[Paragraph(f"<b>{text}</b>", S["head"])]], colWidths=[470])
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.7, HexColor(_PLAN_BAR)),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    def bullets(value, bg="white"):
        # Mathematics is typeset here too. The model writes $...$ wherever
        # it needs a formula — in the key concepts, in the lesson steps, in
        # a real-life example — not only inside the worked examples, and
        # anything not passed through here printed the dollar signs as
        # literal text on the page.
        out = []
        for item in (value if isinstance(value, list) else [value]):
            out.append(Paragraph(
                f"&nbsp;&nbsp;•&nbsp;&nbsp;{_math_inline(item, 11, bg)}", S["bullet"]))
        out.append(Spacer(1, 4))
        return out

    # ── the heavy items, each as a ready list of flowables ──────────────
    heavy: list[list] = []

    formulas = content.get("formulas") or []
    if formulas:
        head = heading(L.get("formulas", "Формулаҳо"))
        blk = [head]
        for f in formulas:
            latex = f.get("latex") if isinstance(f, dict) else None
            plain = (f.get("formula", "") if isinstance(f, dict) else str(f))
            # No "latex" from the model: read the plain field as
            # mathematics rather than dropping to the bulleted fallback,
            # where "S = a^2" prints with the 2 on the baseline.
            if not latex and plain:
                latex = _plain_to_latex(plain)
            # Drawn ON the panel colour, not on white: a formula image
            # with a white background sits on the blue panel as a
            # visible pale rectangle around every equation.
            drawn = _pdf_math_display(latex, 14, bg=_PLAN_BG) if latex else None
            if drawn is not None:
                # Set as a real equation on its own line. The explanation
                # goes under it in smaller type, the way a textbook prints
                # a formula and then says what it is for.
                blk.append(drawn)
                if isinstance(f, dict) and f.get("explanation"):
                    blk.append(Paragraph(
                        f'<para alignment="center">{f["explanation"]}</para>',
                        ParagraphStyle(name=f"Fx{abs(hash(plain)) % 99999}",
                                       parent=S["body"], fontSize=9.5, leading=12.5,
                                       spaceBefore=1, spaceAfter=7),
                    ))
            else:
                line = f"<b>{plain}</b>"
                if isinstance(f, dict) and f.get("explanation"):
                    line += f" — {f['explanation']}"
                blk.append(Paragraph(f"&nbsp;&nbsp;•&nbsp;&nbsp;{line}", S["bullet"]))
        heavy.append([head] + _plan_panel(blk[1:]))

    examples = [e for e in (content.get("worked_examples") or [])
                if isinstance(e, dict) and e.get("problem")]
    if examples:
        blk = list(_plan_feature_head(
            L.get("worked_examples", "Мисолҳо"), S,
            # Just the count. "20 \u00d7" read as an equation fragment, and the
            # word for "example" carries an izofat ending in Tajik, so
            # "20 \u041c\u0438\u0441\u043e\u043b\u0438" would be ungrammatical.
            badge=str(len(examples)),
        ))
        for i, ex in enumerate(examples, 1):
            solution = ""
            if ex.get("solution"):
                # ORDER MATTERS. _plan_mark_answer must see the raw $...$
                # in the answer tail, because it renders those itself onto
                # the highlight colour. Running the inline pass first left
                # it an <img> to wrap in <font backColor>, which is the one
                # combination ReportLab silently drops.
                solution = (f'<i>{L.get("solution", "Ҳал")}:</i> '
                            f'{_math_inline(_plan_mark_answer(ex["solution"]), 10.5, _PLAN_EX_BG)}')
            blk.extend(_plan_example_card(
                f'{L.get("example", "Мисол")} {i}.',
                _math_inline(ex["problem"], 11, _PLAN_EX_BG), solution, S
            ))
        blk.append(Spacer(1, 4))
        heavy.append(blk)

    # Unsolved practice problems — deliberately separate from
    # worked_examples above (those are SOLVED, for the pupil to study;
    # these are for the pupil to solve themselves). No "solution" is ever
    # passed to the card here, on purpose — only the answer key appended
    # at the very end of the sheet (see below) carries the answers, kept
    # as far from the problems as this template's own structure allows.
    drills = [d for d in (content.get("practice_problems") or [])
              if isinstance(d, dict) and d.get("problem")]
    if drills:
        blk = list(_plan_feature_head(
            L.get("practice_problems", "Машқҳои мустақил"), S, badge=str(len(drills)),
        ))
        for i, d in enumerate(drills, 1):
            blk.extend(_plan_example_card(
                f'{L.get("example", "Мисол")} {i}.',
                _math_inline(d["problem"], 11, _PLAN_EX_BG), "", S
            ))
        blk.append(Spacer(1, 4))
        heavy.append(blk)

    # "quick_check" — a real, valuable AI-generated field (short Q&A a
    # teacher fires off right after teaching a section) that this
    # renderer silently dropped entirely: PLAN_ORDER above never named
    # it, so a teacher's konspekt could carry real questions+answers in
    # its stored content that never printed anywhere on the sheet. Same
    # gap this template had for practice_problems before that was fixed.
    quick_check = [q for q in (content.get("quick_check") or []) if isinstance(q, dict) and q.get("question")]
    if quick_check:
        blk = list(_plan_feature_head(L.get("quick_check", "Санҷиши зуд"), S, badge=str(len(quick_check))))
        blk.extend(_pdf_quick_check(quick_check, _PLAN_BAR, L.get("answer", "Ҷавоб")))
        heavy.append(blk)

    for block in (content.get("visual_blocks") or []):
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        data = block.get("data") or {}
        if btype in ("table", "comparison"):
            # _PLAN_INK, not black: in minimal mode this colours both the
            # header text and the rule under it, so the table joins the
            # sheet's palette instead of sitting in it as a separate style.
            blk = list(_pdf_visual_block(block, _PLAN_INK, minimal=True))
        elif btype in ("process", "flowchart", "timeline"):
            # Rendered as a plain numbered/dated list rather than the
            # colour-boxed picture the image builders draw. The drawn
            # version is what the teacher rejected for this sheet, but the
            # CONTENT — ordered steps, dated events — is worth keeping, and
            # dropping these types outright silently discarded most of what
            # the model produced.
            blk = []
            if block.get("title"):
                # Through heading(), not the raw style — a visual's title is
                # a section heading like any other, and using the style
                # directly skipped both the accent rule and the spacing that
                # heading() carries, leaving it jammed against the paragraph
                # above it.
                blk.append(heading(block["title"]))
            if btype == "timeline":
                for ev in (data.get("events") or []):
                    bits = [b for b in [ev.get("date"), ev.get("label")] if b]
                    line = f"<b>{' — '.join(bits)}</b>"
                    if ev.get("description"):
                        line += f" — {ev['description']}"
                    blk.append(Paragraph(
                        f"&nbsp;&nbsp;•&nbsp;&nbsp;{_math_inline(line, 11)}", S["bullet"]))
            else:
                for i, st in enumerate(data.get("steps") or [], 1):
                    line = f"<b>{st.get('title', '')}</b>"
                    if st.get("description"):
                        line += f" — {st['description']}"
                    blk.append(Paragraph(
                        f"&nbsp;&nbsp;{i}.&nbsp;&nbsp;{_math_inline(line, 11)}", S["bullet"]))
            if len(blk) <= (1 if block.get("title") else 0):
                continue
            blk.append(Spacer(1, 4))
        else:
            continue
        # A table on its own leaves the reader to work out what it shows —
        # the note underneath is what makes it teach something.
        note = block.get("description") or block.get("note")
        if note:
            blk.append(Paragraph(
                f"<i>{_math_inline(note, 10)}</i>",
                ParagraphStyle(name=f"PlanVisNote_{abs(hash(str(note))) % 100000}",
                               parent=S["body"], fontSize=10, leading=13,
                               alignment=TA_LEFT, spaceBefore=1, spaceAfter=8),
            ))
        if blk:
            heavy.append(blk)

    for cb in (content.get("code_blocks") or []):
        if isinstance(cb, dict) and cb.get("code"):
            heavy.append(list(_pdf_code_card(
                cb["code"], cb.get("language", ""), cb.get("explanation", ""), _PLAN_INK)))

    # Subject figures are heavy items too, so they get dealt out across the
    # page boundaries by the same rule as everything else rather than all
    # landing together — the specific complaint that produced this layout.
    for fig in (content.get("figures") or []):
        if isinstance(fig, dict):
            blk = _pdf_subject_figure(fig, minimal=True, max_w=270, max_h=205)
            if blk:
                heavy.append(blk)

    # ── sections, in lesson order ───────────────────────────────────────
    # Same anchoring as the ordinary templates: each picture waits for the
    # section whose text it explains.
    lesson_by_anchor: dict[str, list] = {}
    for image in (content.get("lesson_images") or []):
        if isinstance(image, dict) and image.get("path"):
            lesson_by_anchor.setdefault(image.get("position_after") or "main_content", []).append(image)

    PLAN_ORDER = [
        ("competencies", "fill"),
        ("warmup", "fill"),
        ("objectives", "bullets"),
        ("key_concepts", "bullets"),
        ("key_terms", "bullets"),
        ("tools", "runin"),
        ("main_content", "runin"),
        ("important_notes", "notes"),
        ("real_life_examples", "bullets"),
        ("lesson_program", "runin"),
        ("pair_work", "runin"),
        ("group_work", "bullets"),
        ("consolidation", "runin"),
        ("homework", "bullets"),
        ("summary", "runin"),
        ("assessment", "runin"),
    ]

    # Only sections that actually print can carry a heavy item after them,
    # so count those first and spread the items across that many slots.
    printable = [
        key for key, kind in PLAN_ORDER
        if kind == "fill" or content.get(key)
    ]
    # Never attach one to the very first section — the sheet should open
    # with its own front matter, not a table.
    slots = printable[1:]
    drop_after: dict[str, list] = {}
    if slots and heavy:
        # Even fractional spacing across the WHOLE run of sections:
        # item i of n goes at (i+1)/(n+1) of the way through. Two earlier
        # attempts got this wrong — stepping from position 0 by
        # len(slots)//len(heavy) crowded everything into the first half and
        # left the tail bare, and clamping with min(..., len(slots)-1)
        # piled every surplus item onto the very last section, which is the
        # bunching this was supposed to fix in the first place.
        for i, blk in enumerate(heavy):
            pos = round((i + 1) * len(slots) / (len(heavy) + 1))
            pos = max(0, min(pos, len(slots) - 1))
            drop_after.setdefault(slots[pos], []).append(blk)

    # The two sections a pupil looks back at while working — the concepts
    # and the terms — are the ones that get the tint, so the eye finds them
    # on a page of running prose without hunting.
    PANELLED = {"key_concepts", "key_terms"}

    for key, kind in PLAN_ORDER:
        value = content.get(key)
        label = L.get(key, key)
        if kind == "fill":
            story.append(heading(f"{label}:"))
            story.extend(bullets(value) if value else _plan_rule())
        elif value and kind == "notes":
            # "important_notes" had no entry in PLAN_ORDER at all, so every
            # caveat and misconception warning the model produced was
            # silently dropped from this template — the one layout where a
            # teacher most wants them. They print here, in the panel.
            for note in (value if isinstance(value, list) else [value]):
                if not str(note).strip():
                    continue
                story.extend(_plan_panel([Paragraph(
                    f'<b>{L.get("plan_note", "Диққат")}.</b> '
                    f'{_math_inline(note, 11, _PLAN_BG)}', S["body"]
                )]))
        elif value and kind == "bullets":
            story.append(heading(label))
            if key in PANELLED:
                story.extend(_plan_panel(bullets(value, _PLAN_BG)[:-1]))
            else:
                story.extend(bullets(value))
        elif value and kind == "runin":
            story.append(Paragraph(
                f"<b><i>{label}.</i></b> {_math_inline(_plan_flatten(value), 11)}",
                S["body"]))
        # The Commons illustration for this section prints right under the
        # section it explains, before the dealt-out heavy items — same
        # anchoring the ordinary templates use (see _add_konspekt_body_pdf).
        for image in lesson_by_anchor.pop(key, []):
            story.extend(_pdf_lesson_image_block(
                image, L.get("illustration", "Тасвир"), _PLAN_INK))
        for blk in drop_after.pop(key, []):
            story.extend(blk)

    # Anything that didn't get a slot (more items than printable sections)
    # still renders rather than vanishing.
    for images in lesson_by_anchor.values():
        for image in images:
            story.extend(_pdf_lesson_image_block(
                image, L.get("illustration", "Тасвир"), _PLAN_INK))
    for leftover in drop_after.values():
        for blk in leftover:
            story.extend(blk)

    # Answer key for the practice problems above — appended directly to
    # the story rather than dealt out with the other heavy items, so it
    # always lands at the very end of the sheet, as far from the problems
    # themselves as this template's structure allows (unlike the
    # worked_examples above, which show their solution right inline).
    drill_answers = [d.get("answer", "") for d in drills if str(d.get("answer") or "").strip()]
    if drill_answers:
        story.extend(_plan_feature_head(L.get("answers", "Ҷавобҳо"), S))
        for i, ans in enumerate(drill_answers, 1):
            story.append(Paragraph(
                f'<b>{i}.</b>&nbsp;&nbsp;{_math_inline(ans, 11, _PLAN_BG)}', S["bullet"]))
        story.append(Spacer(1, 4))

    return story


def _add_konspekt_body_pdf(content: dict, L: dict, academic: bool = False,
                           numbered: bool = True) -> list:
    """Builds the full section-by-section flowable list for a konspekt body
    (everything after the title/subtitle) — shared by build_konspekt_pdf (a
    lone document) and build_curriculum_pdf (many of these appended into one
    combined multi-day PDF), so a curriculum download gets the exact same
    numbered/formula-card/concept-card styling as a single konspekt
    download instead of the old flat monochrome look.

    One consistent color throughout — previously a different color per
    SECTION was tried and reverted as "rainbow/childish" per teacher
    feedback (a serious methodological guide reads as one deliberate
    palette, not confetti). That still holds: this is one color for the
    whole document. What varies now is which color, by SUBJECT (see
    app/subject_theme.py) — so a Biology konspekt and a Physics konspekt
    are distinguishable from each other, without introducing more than
    one color within either one. fun_facts / warmup / common_mistakes
    deliberately excluded — the teacher asked for these to never appear
    in the konspekt at all.

    The document's overall LAYOUT is picked per-konspekt via "template"
    (see app/konspekt_templates.py) — content placement/order (this
    function's sections_map) is identical across every template; only the
    header style / font / sidebar panel / bullet tint change."""
    ACCENT = get_subject_accent_hex(content.get("subject"))
    # Strip a redundant self-labeled "Group N:"/"Гурӯҳи N:" prefix the model
    # sometimes adds despite being told not to (see _GROUP_LABEL_RE) —
    # group_work then flows through sections_map below like any other list
    # field, its numbered bullet alone conveying which group it is.
    if content.get("group_work"):
        content = {
            **content,
            "group_work": [_strip_group_label(t) for t in content["group_work"]],
        }
    # Same "zamonaviy" fallback as build_konspekt_pdf's cover — see that
    # comment for why `or` is safe here too (curriculum always sets a real
    # value; only wizard-generated konspekt/лекция ever hits this default).
    tmpl = get_template(content.get("template") or "zamonaviy")
    header_font = MATH_FONT if tmpl.font_family == 'serif' else FONT_NAME

    def _header(label, color, number):
        if is_lecture:
            # Inside a majmua the day itself is the numbered unit, so the
            # sections within a day are not numbered again — two counters
            # running at the same level ("2. РӮЗ 1" over "1. ЦЕЛИ") read
            # as a mistake.
            return _pdf_lecture_section_header(label, color, number if numbered else None)
        if tmpl.header_style == "numbered":
            return _pdf_section_header(label, color, number)
        renderer = _PDF_SECTION_RENDERERS.get(tmpl.header_style, _pdf_section_header)
        return renderer(label, color, number, header_font)

    def _num_bullet(j, item, color):
        if tmpl.alt_row_tint:
            return _pdf_numbered_bullet_tinted(j, item, color)
        return [_pdf_numbered_bullet(j, item, color, serif=is_lecture)]

    # Group visual_blocks by their own "position_after" (see ai_service.py's
    # _konspekt_prompt) so each renders right after the section it's
    # actually anchored to, spread through the document the way the AI
    # intended — same fix as docx_builder.py's _add_konspekt_body (this PDF
    # export used to dump every block in one spot after main_content
    # regardless of what it was about).
    _visuals_by_position: dict[str, list] = {}
    for _block in (content.get("visual_blocks") or []):
        if isinstance(_block, dict):
            _visuals_by_position.setdefault(_block.get("position_after") or "", []).append(_block)

    # Figures are spread over the section anchors rather than dumped in one
    # place, same reasoning as the plan sheet's "heavy" dealing.
    _figures = [f for f in (content.get("figures") or [])
                if isinstance(f, dict) and f.get("image")]
    _figure_anchors = ["key_concepts", "main_content", "real_life_examples", "consolidation"]
    _figures_by_anchor: dict[str, list] = {}
    for _i, _fig in enumerate(_figures):
        _figures_by_anchor.setdefault(_figure_anchors[_i % len(_figure_anchors)], []).append(_fig)

    def _render_figures(position_key):
        out = []
        for fig in _figures_by_anchor.pop(position_key, []):
            out.extend(_pdf_subject_figure(fig, tmpl.minimal_chrome))
        return out

    def _render_visuals(position_key):
        rendered = []
        for block in _visuals_by_position.pop(position_key, []):
            rendered.extend(_pdf_visual_block(block, ACCENT, tmpl.minimal_chrome,
                                              serif=is_lecture))
        return rendered

    # The Commons teaching illustrations, each filed under the section it
    # explains (see ai_service._place_lesson_images). Anchored rather than
    # placed at the top of the document: a diagram of a right triangle
    # belongs under the paragraph about right triangles, not on whatever
    # page happens to come first.
    _lesson_by_anchor: dict[str, list] = {}
    for _img in (content.get("lesson_images") or []):
        if isinstance(_img, dict) and _img.get("path"):
            _lesson_by_anchor.setdefault(_img.get("position_after") or "main_content", []).append(_img)

    def _render_lesson_images(position_key):
        out = []
        for image in _lesson_by_anchor.pop(position_key, []):
            out.extend(_pdf_lesson_image_block(image, L.get('illustration', 'Illustration'), ACCENT))
        return out

    story = []
    # A лекция follows the standard lecture form — aim, plan, body,
    # conclusion, sources — and that order is the document's whole point.
    # The template's sidebar panel would lift key_concepts/key_terms above
    # all of it, so a reader met six paragraphs of terminology before
    # learning what the lecture is even for. Lectures therefore render
    # every section inline, in order; konspekts keep their sidebar.
    is_lecture = academic or bool(content.get("lecture_plan") or content.get("objective"))
    sidebar_sections = () if is_lecture else tmpl.sidebar_sections
    if is_lecture:
        # "Итоги урока" is the wrong noun in a document that is not a
        # lesson: a лекция ends on its conclusions.
        L = dict(L)
        L['summary'] = _LECTURE_SUMMARY_LABEL.get(
            str(content.get('language') or 'Русский'), L['summary'])
    if sidebar_sections:
        story.extend(_pdf_sidebar_panel(content, sidebar_sections, ACCENT, L))
    # Order matches how a teacher actually walks through a real lesson
    # plan (goal first, then what the class needs to know, then the
    # explanation itself, then practice, then wrap-up) — was ordered by
    # roughly how the JSON schema happened to list the fields instead,
    # which read fine section-by-section but not as one coherent flow
    # top to bottom (direct feedback, referencing a real "Нақшаи
    # тавзеҳотӣ" curriculum document's own ordering).
    sections_map = [
        # A лекция opens on the standard lecture form: what it is for, then
        # the plan it will follow. Both keys are absent from a konspekt, so
        # the per-field guard below simply skips them there — same
        # mechanism the лекция already relies on to drop the
        # lesson-management sections.
        ("objective", L.get('objective', 'Цель'), ACCENT),
        ("lecture_plan", L.get('lecture_plan', 'План'), ACCENT),
        ("objectives", L['objectives'], ACCENT),
        ("competencies", L['competencies'], ACCENT),
        ("key_concepts", L['key_concepts'], ACCENT),
        ("key_terms", L['key_terms'], ACCENT),
        ("tools", L['tools'], ACCENT),
        ("lesson_program", L['lesson_program'], ACCENT),
        ("main_content", L['main_content'], ACCENT),
        ("real_life_examples", L['real_life_examples'], ACCENT),
        ("pair_work", L['pair_work'], ACCENT),
        ("group_work", L['group_work'], ACCENT),
        ("consolidation", L['consolidation'], ACCENT),
    ]

    num = 0
    for key, label, color in sections_map:
        val = content.get(key)
        if val is None:
            continue
        # The section's own content (its bullet list or paragraph) always
        # renders first — the formula/card/image extras below are meant to
        # follow it, not precede it. Skipped entirely when this key is
        # already covered by the sidebar panel above (zamonaviy only).
        if key not in sidebar_sections:
            if isinstance(val, list):
                if val:
                    num += 1
                    # KeepTogether around the header + its first item only
                    # (not the whole section — a long list should still be
                    # free to split page-to-page) — a header stranded
                    # alone at the bottom of a page with its content
                    # starting fresh on the next one read as a mistake,
                    # not a real page break (direct feedback: "yetim
                    # sarlavha").
                    header_flowables = _header(label, color, num)
                    first_item = _num_bullet(1, val[0], color)
                    story.append(KeepTogether(header_flowables + first_item))
                    for j, item in enumerate(val[1:], start=2):
                        story.extend(_num_bullet(j, item, color))
            elif isinstance(val, str) and val.strip():
                num += 1
                header_flowables = _header(label, color, num)
                if key == "main_content":
                    paragraphs = _pdf_prose_paragraph(val, serif=is_lecture)
                    if paragraphs:
                        story.append(KeepTogether(header_flowables + [paragraphs[0]]))
                        story.extend(paragraphs[1:])
                    else:
                        story.extend(header_flowables)
                else:
                    story.append(KeepTogether(header_flowables + [_pdf_bullet(val, color, serif=is_lecture)]))
        # Any block anchored to this section (by "position_after") renders
        # right after it, whether or not this key had its own content above
        # — a block can be relevant to a sidebar-only section too.
        story.extend(_render_lesson_images(key))
        story.extend(_render_figures(key))
        story.extend(_render_visuals(key))

        # formulas/concept_cards/map render right where they're most
        # relevant (next to key_concepts / real_life_examples) with NO
        # numbered section heading of their own — a heading like "4.
        # Расмхо" made them read as their own separate chapter instead of
        # an illustration embedded in the surrounding explanation, which is
        # what the teacher actually wants.
        if key == "key_concepts":
            formulas = content.get("formulas")
            if formulas:
                story.append(Spacer(1, 4))
                for f in formulas:
                    if isinstance(f, dict):
                        story.extend(_pdf_formula_card(
                            f.get('formula', ''), f.get('explanation', ''),
                            tmpl.minimal_chrome or is_lecture, f.get('latex'), ACCENT))
                    else:
                        story.extend(_pdf_formula_card(str(f), '', tmpl.minimal_chrome or is_lecture, accent=ACCENT))
            concept_cards = content.get("concept_cards")
            if concept_cards:
                story.extend(_pdf_concept_card_grid(concept_cards, ACCENT))
        if key == "key_terms":
            # Real, syntax-styled code (Информатика/programming topics
            # only — see ai_service.py's _CODE_SUBJECTS), same "no numbered
            # heading of its own" reasoning as formulas/concept_cards above.
            for cb in (content.get("code_blocks") or []):
                if isinstance(cb, dict) and cb.get("code"):
                    story.extend(_pdf_code_card(cb["code"], cb.get("language", ""), cb.get("explanation", ""), ACCENT))
        if key == "main_content":
            # Solved "misol" practice problems (Математика/Алгебра/
            # Геометрия only — see ai_service.py's _WORKED_EXAMPLE_SUBJECTS)
            # right after main_content, the "now apply what was just
            # explained" spot — unlike formulas/concept_cards above, this
            # gets its own numbered section heading since it's substantial
            # enough content to read as its own part of the lesson, not a
            # small illustration embedded in the surrounding explanation.
            worked_examples = content.get("worked_examples")
            if worked_examples:
                num += 1
                story.extend(_header(L['worked_examples'], ACCENT, num))
                story.extend(_pdf_worked_examples(worked_examples, ACCENT, L['solution'], tmpl.minimal_chrome))
                # "worked_examples" is a valid anchor for a lesson image
                # but not one of sections_map's own keys, so it needs
                # catching here — after the examples, never inside them:
                # a figure dropped between a problem and its solution
                # breaks the one thing a pupil has to read straight
                # through.
                story.extend(_render_lesson_images("worked_examples"))
        if key == "real_life_examples":
            map_image = content.get("map_image")
            if map_image:
                locations = content.get("map_locations", [])
                caption = ', '.join(locations) if locations else ''
                img = _pdf_illustration_image(map_image, caption, '© OpenStreetMap contributors', max_w=400, max_h=262)
                if img:
                    story.extend(img)
            # Real Wikipedia photo/logo for a concrete real-world subject
            # the AI named (real_image_query) — a background-removed
            # animal/plant cutout or a brand/software logo, already
            # trimmed to its own content (see image_builder.py's
            # _trim_transparent), so a modest box is enough here.
            real_image = content.get("real_image")
            if isinstance(real_image, dict) and real_image.get("path"):
                box = _REAL_IMAGE_BOX.get(real_image.get("style"), _REAL_IMAGE_BOX_DEFAULT)
                img = _pdf_illustration_image(real_image["path"], real_image.get("caption", ""), "Wikipedia", max_w=box, max_h=box)
                if img:
                    story.extend(img)
    # "visual_aid" is a valid position_after value (see ai_service.py) but
    # isn't one of sections_map's own keys above — this export doesn't
    # render a dedicated "visual_aid" section — so it needs its own catch
    # here. Anything else left over (a malformed/legacy position_after)
    # still renders instead of silently vanishing, same "end of the lesson
    # body" spot this always used before this fix.
    for _left in list(_lesson_by_anchor):
        story.extend(_render_lesson_images(_left))
    for _left in list(_figures_by_anchor):
        story.extend(_render_figures(_left))
    story.extend(_render_visuals("visual_aid"))
    for _leftover_key in list(_visuals_by_position):
        story.extend(_render_visuals(_leftover_key))

    important_notes = content.get("important_notes") or []
    for note in important_notes:
        num += 1
        story.append(Spacer(1, 4))
        story.append(_pdf_important_note(str(note), ACCENT))

    quick_check = content.get("quick_check") or []
    if quick_check:
        num += 1
        story.extend(_header(L['quick_check'], ACCENT, num))
        story.extend(_pdf_quick_check(quick_check, ACCENT, L['answer']))

    homework = content.get("homework")
    if homework:
        num += 1
        story.extend(_header(L['homework'], ACCENT, num))
        if isinstance(homework, list):
            for i, h in enumerate(homework):
                story.extend(_num_bullet(i + 1, h, ACCENT))
        else:
            story.append(_pdf_bullet(str(homework), ACCENT, serif=is_lecture))

    summary = content.get("summary", "")
    if summary:
        num += 1
        story.extend(_header(L['summary'], ACCENT, num))
        story.append(_pdf_bullet(summary, ACCENT, serif=is_lecture))

    assessment = content.get("assessment", "")
    if assessment:
        num += 1
        story.extend(_header(L['assessment'], ACCENT, num))
        story.append(_pdf_bullet(assessment, ACCENT, serif=is_lecture))

    # The sources, last — where a lecture's bibliography belongs. Absent
    # from a konspekt, so nothing changes there.
    references = [r for r in (content.get("references") or []) if str(r).strip()]
    if references:
        num += 1
        story.extend(_header(L.get('references', 'Литература'), ACCENT, num))
        for i, ref in enumerate(references, start=1):
            story.extend(_num_bullet(i, str(ref), ACCENT))

    return story


# ── Curriculum PDF Builder ───────────────────────────────────────────────
# Same blue-accent styling as the per-material PDFs above (via
# _add_konspekt_body_pdf) — one combined file: a roadmap overview table,
# then every day's full content in order. Exam-day questions still use a
# plain ink/gray palette below (a test isn't a methodological document),
# but get a red heading bar so they still stand out from lesson days.

_MONO_INK = '#111111'
_MONO_TEXT = '#222222'

_CURRICULUM_LABELS = {
    'Русский': {
        'duration': 'Время урока', 'competencies': 'Компетенции', 'objectives': 'Цели урока',
        'key_concepts': 'Ключевые понятия', 'key_terms': 'Словарь урока', 'lesson_program': 'Программа урока',
        'tools': 'Инструменты', 'warmup': 'Разминка', 'main_content': 'Основное содержание',
        'real_life_examples': 'Примеры из жизни', 'visual_aid': 'Наглядное пособие',
        'pair_work': 'Парная работа', 'consolidation': 'Закрепление', 'fun_facts': 'Интересные факты',
        'common_mistakes': 'Частые ошибки', 'summary': 'Итоги урока', 'homework': 'Домашнее задание',
        'assessment': 'Оценка', 'group_work': 'Групповая работа', 'group': 'Группа',
        'day': 'День', 'date': 'Дата', 'topic': 'Тема', 'type': 'Тип', 'lesson': 'Урок', 'exam': 'Экзамен',
        'roadmap': 'Дорожная карта курса', 'answer': 'Примерный ответ', 'explanation': 'Объяснение',
    },
    'Таджикский': {
        'duration': 'Вақти дарс', 'competencies': 'Салоҳиятҳо', 'objectives': 'Мақсадҳои дарс',
        'key_concepts': 'Мафҳумҳои асосӣ', 'key_terms': 'Луғати дарс', 'lesson_program': 'Барномаи дарс',
        'tools': 'Воситаҳои аёнӣ', 'warmup': 'Санҷиши дониш', 'main_content': 'Шиносоӣ бо мазмуни мавзӯъ',
        'real_life_examples': 'Дар ҳаёти воқеӣ', 'visual_aid': 'Ёрии визуалӣ',
        'pair_work': 'Кори дунафара', 'consolidation': 'Мустаҳкамкунии дарс', 'fun_facts': 'Фактҳои ҷолиб',
        'common_mistakes': 'Хатогиҳои маъмул', 'summary': 'Хулосаи дарс', 'homework': 'Супориши хонагӣ',
        'assessment': 'Арзёбӣ', 'group_work': 'Кори гурӯҳӣ', 'group': 'Гурӯҳи',
        'day': 'Рӯз', 'date': 'Сана', 'topic': 'Мавзӯъ', 'type': 'Навъ', 'lesson': 'Дарс', 'exam': 'Имтиҳон',
        'roadmap': 'Харитаи курс', 'answer': 'Ҷавоби намунавӣ', 'explanation': 'Шарҳ',
    },
    'English': {
        'duration': 'Duration', 'competencies': 'Competencies', 'objectives': 'Objectives',
        'key_concepts': 'Key Concepts', 'key_terms': 'Lesson Glossary', 'lesson_program': 'Lesson Program',
        'tools': 'Teaching Tools', 'warmup': 'Warm-up', 'main_content': 'Main Content',
        'real_life_examples': 'Real Life', 'visual_aid': 'Visual Aid',
        'pair_work': 'Pair Work', 'consolidation': 'Consolidation', 'fun_facts': 'Fun Facts',
        'common_mistakes': 'Common Mistakes', 'summary': 'Summary', 'homework': 'Homework',
        'assessment': 'Assessment', 'group_work': 'Group Work', 'group': 'Group',
        'day': 'Day', 'date': 'Date', 'topic': 'Topic', 'type': 'Type', 'lesson': 'Lesson', 'exam': 'Exam',
        'roadmap': 'Course Roadmap', 'answer': 'Model Answer', 'explanation': 'Explanation',
    },
}
_CURRICULUM_LABELS['Английский'] = _CURRICULUM_LABELS['English']


def _pdf_mono_para(text, size=10.5, italic=False):
    tag = 'i' if italic else 'span'
    style = ParagraphStyle(
        name=f'MonoPara_{hash(text) % 10000}', fontName=FONT_NAME, fontSize=size,
        leading=size + 4, textColor=HexColor(_MONO_TEXT), spaceAfter=5,
    )
    return Paragraph(f'<{tag}>{text}</{tag}>' if italic else text, style)


def _pdf_curriculum_exam_content(content: dict, R: dict, accent: str | None = None) -> list:
    """An exam day's questions, set exactly like the standalone test sheet
    (see build_test_pdf) so a majmua reads as one document — this used to
    be the odd page out, in sans with green answers, while everything
    around it had moved to the serif handout style."""
    accent = accent or _PDF_ACCENT
    elements = []
    description = content.get('description', '')
    if description:
        elements.append(Paragraph(
            str(description),
            ParagraphStyle(name='ExamDesc', fontName=MATH_FONT, fontSize=10, leading=14,
                           textColor=HexColor(_LECTURE_MUTED), spaceAfter=6)))
    for i, q in enumerate(content.get('questions', [])):
        q_type = q.get('type', 'multiple_choice')
        q_style = ParagraphStyle(
            name=f'ExamQ_{i}', fontName=MATH_FONT_BOLD, fontSize=11.5, leading=16,
            textColor=HexColor(_LECTURE_INK), leftIndent=20, firstLineIndent=-20,
            spaceBefore=9, spaceAfter=4,
        )
        elements.append(Paragraph(
            f'<font color="{accent}"><b>{i + 1}.</b></font>&nbsp;&nbsp;{q.get("question", "")}',
            q_style))
        if q_type == 'open_ended':
            if q.get('model_answer'):
                elements.append(_pdf_answer_box(f'{R["answer"]}: {q["model_answer"]}', accent))
        else:
            options = q.get('options', [])
            correct_indices = set(q.get('correct_indices') or [])
            correct = q.get('correct_index', 0)
            for j, opt in enumerate(options):
                is_correct = (j in correct_indices) if q_type == 'multiple_select' else (j == correct)
                letter = chr(65 + j)
                # The right answer is marked by weight, an underline and a
                # faint tint rather than by colour alone — it survives a
                # black-and-white printout, which an exam sheet often is.
                opt_style = ParagraphStyle(
                    name=f'ExamOpt_{i}_{j}',
                    fontName=MATH_FONT_BOLD if is_correct else MATH_FONT,
                    fontSize=10.5, leading=15, textColor=HexColor(_LECTURE_INK),
                    backColor=HexColor(_pdf_light_tint_hex(accent, amount=0.90)) if is_correct else None,
                    borderPadding=(2, 5, 2, 5) if is_correct else 0,
                    leftIndent=36 if is_correct else 40, spaceAfter=2,
                )
                text = f'<b><u>{letter}) {opt}</u></b>' if is_correct else f'{letter}) {opt}'
                elements.append(Paragraph(text, opt_style))
        if q.get('explanation'):
            elements.append(_pdf_answer_box(f'{R["explanation"]}: {q["explanation"]}', accent))
    return elements


# "10 · вопросов" under the test's title, in the sheet's own language.
_TEST_COUNT_LABEL = {
    'Русский': 'вопросов', 'Таджикский': 'савол',
    'English': 'questions',
}
_TEST_COUNT_LABEL['Английский'] = _TEST_COUNT_LABEL['English']


# Everything the sheet says in its own voice, per language. A test is
# handed to a class, so its furniture — the name line, the instructions,
# the answer key's heading — has to be in the language the test is in.
_TEST_UI = {
    'Русский': {
        'name': 'Ф.И.О.', 'klass': 'Класс', 'date': 'Дата', 'mark': 'Оценка',
        'hint': 'Внимательно прочитайте каждый вопрос. В заданиях с одним ответом '
                'обведите букву верного варианта, в заданиях с несколькими ответами — '
                'отметьте все верные, на открытый вопрос ответьте письменно.',
        'key_title': 'КЛЮЧ К ТЕСТУ', 'key_hint': 'Лист для учителя — не выдавайте ученикам.',
        'col_no': '№', 'col_answer': 'Ответ', 'col_why': 'Пояснение',
        'open': 'развёрнутый ответ', 'model': 'Примерный ответ',
        'total': 'Всего вопросов', 'max_score': 'Максимальный балл',
        'types': {'true_false': 'верно / неверно', 'multiple_select': 'несколько ответов',
                  'open_ended': 'открытый вопрос'},
        'select_hint': 'выберите все верные', 'tf': ('Верно', 'Неверно'),
    },
    'Таджикский': {
        'name': 'Ном ва насаб', 'klass': 'Синф', 'date': 'Сана', 'mark': 'Баҳо',
        'hint': 'Ҳар саволро бодиққат хонед. Дар саволҳои якҷавоба ҳарфи ҷавоби дурустро '
                'давра кунед, дар саволҳои бисёрҷавоба ҳамаи ҷавобҳои дурустро қайд кунед, '
                'ба саволи кушод хаттӣ ҷавоб диҳед.',
        'key_title': 'КАЛИДИ ТЕСТ', 'key_hint': 'Варақаи муаллим — ба хонандагон надиҳед.',
        'col_no': '№', 'col_answer': 'Ҷавоб', 'col_why': 'Шарҳ',
        'open': 'ҷавоби муфассал', 'model': 'Ҷавоби намунавӣ',
        'total': 'Ҳамагӣ саволҳо', 'max_score': 'Холи ниҳоӣ',
        'types': {'true_false': 'дуруст / нодуруст', 'multiple_select': 'якчанд ҷавоб',
                  'open_ended': 'саволи кушод'},
        'select_hint': 'ҳамаи ҷавобҳои дурустро интихоб кунед', 'tf': ('Дуруст', 'Нодуруст'),
    },
    'English': {
        'name': 'Name', 'klass': 'Class', 'date': 'Date', 'mark': 'Mark',
        'hint': 'Read each question carefully. For single-answer questions circle the letter '
                'of the correct option, for multiple-answer questions mark every correct '
                'option, and answer the open question in writing.',
        'key_title': 'ANSWER KEY', 'key_hint': 'Teacher\'s sheet — do not hand out to students.',
        'col_no': '#', 'col_answer': 'Answer', 'col_why': 'Explanation',
        'open': 'written answer', 'model': 'Model answer',
        'total': 'Questions', 'max_score': 'Maximum score',
        'types': {'true_false': 'true / false', 'multiple_select': 'multiple answers',
                  'open_ended': 'open question'},
        'select_hint': 'choose all that apply', 'tf': ('True', 'False'),
    },
}
_TEST_UI['Английский'] = _TEST_UI['English']


def _test_ui(language: str) -> dict:
    return _TEST_UI.get(str(language or 'Русский'), _TEST_UI['Русский'])


def _pdf_student_header(ui: dict, accent: str):
    """The line a student fills in before answering.

    A printed test without somewhere to write a name and a mark is not a
    test yet — it is a draft of one, and every teacher would have to add
    this by hand."""
    cell = ParagraphStyle(name='TestFieldLbl', fontName=FONT_NAME, fontSize=9,
                          leading=13, textColor=HexColor(_LECTURE_MUTED))
    def field(label, width):
        return Paragraph(f'{label}&nbsp;<font color="{_LECTURE_RULE}">'
                         f'{"_" * width}</font>', cell)
    row = [[field(ui['name'], 26), field(ui['klass'], 7),
            field(ui['date'], 9), field(ui['mark'], 7)]]
    # The name column is the widest because its label is: "Ном ва насаб"
    # wrapped onto a second line at the Russian column widths, dragging
    # the writing line down with it.
    t = Table(row, colWidths=[228, 74, 86, 72])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, -1), 0.7, HexColor(_LECTURE_RULE)),
    ]))
    return [t, Spacer(1, 8)]


def _pdf_answer_lines(count: int = 3, width: str = '100%'):
    """Ruled lines for a written answer — the space to actually answer in."""
    out = []
    for _ in range(count):
        out.append(Spacer(1, 15))
        out.append(HRFlowable(width=width, thickness=0.5,
                              color=HexColor(_LECTURE_RULE), hAlign='RIGHT'))
    out.append(Spacer(1, 6))
    return out


def build_test_pdf(content: dict, include_key: bool = True,
                   student_only: bool = False) -> io.BytesIO:
    """The test as a teacher uses it: a clean student sheet, then the key.

    It used to be one document that printed the correct option highlighted
    and its explanation under every question — a teacher's crib that could
    not be given to a class at all. The answers now live on their own page
    after a page break, so the same file both hands out and marks.

    `student_only` drops the key entirely, for a teacher who wants only
    the sheet to photocopy.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm)
    story = []

    title = content.get("title", "Тест")
    desc = content.get("description", "")
    subject = content.get("subject", "")
    grade = content.get("grade", "")
    language = str(content.get("language") or "Русский")
    ui = _test_ui(language)
    questions = content.get("questions", [])
    accent = get_subject_accent_hex(subject)

    story.extend(_pdf_lecture_masthead(
        title, desc, subject, grade, language,
        _PDF_KONSPEKT_LABELS.get(language,
                                 _PDF_KONSPEKT_LABELS['Русский']).get('grade_suffix', 'класс'),
        accent=accent))
    story.extend(_pdf_student_header(ui, accent))
    # No "10 · вопросов" line: the description above already says how many
    # there are, and the sheet's own footer states the total and the
    # maximum score — three copies of one number is clutter on a page a
    # student has to read under time pressure.
    story.append(Paragraph(
        ui['hint'],
        ParagraphStyle(name="TestHint", fontName=FONT_NAME, fontSize=8.5, leading=12,
                       alignment=TA_JUSTIFY, textColor=HexColor(_LECTURE_MUTED),
                       spaceAfter=2)))

    _LETTERS = ['A', 'B', 'C', 'D', 'E', 'F']

    def letters_for(q):
        """The key's answer for one question, as the student would write it."""
        q_type = q.get('type', 'multiple_choice')
        options = q.get('options') or []
        if q_type == 'open_ended':
            return ui['open']
        if q_type == 'multiple_select':
            idx = sorted(int(i) for i in (q.get('correct_indices') or [])
                         if isinstance(i, (int, float)) and 0 <= int(i) < len(options))
            return ', '.join(_LETTERS[i] for i in idx) if idx else '—'
        i = q.get('correct_index')
        if not isinstance(i, int) or not (0 <= i < len(options)):
            return '—'
        # "B) Верно" reads better than a bare letter on a true/false row,
        # where the letter alone says nothing.
        return (f'{_LETTERS[i]} · {options[i]}' if q_type == 'true_false'
                else _LETTERS[i])

    # ── the student sheet ───────────────────────────────────────────────
    for i, q in enumerate(questions):
        q_type = q.get('type', 'multiple_choice')
        question_style = ParagraphStyle(
            name=f'Q_{i}', fontName=MATH_FONT_BOLD, fontSize=12.5, leading=17,
            textColor=HexColor(_LECTURE_INK), leftIndent=22, firstLineIndent=-22,
            spaceAfter=7)
        opt_style = ParagraphStyle(
            name=f'Opt_{i}', fontName=MATH_FONT, fontSize=11, leading=15.5,
            textColor=HexColor(_LECTURE_INK), leftIndent=40, spaceAfter=3)

        story.append(Spacer(1, 12))
        story.append(HRFlowable(width="100%", thickness=0.7, color=HexColor(_LECTURE_RULE)))
        story.append(Spacer(1, 7))

        # Only the instruction a student needs to answer correctly — the
        # type of a question is the teacher's vocabulary, not theirs, so
        # "multiple answers" became "choose all that apply" and the rest
        # of the labels went away.
        hint = (f' <font color="{_LECTURE_MUTED}" size="9">({ui["select_hint"]})</font>'
                if q_type == 'multiple_select' else '')
        story.append(Paragraph(
            f'<font color="{accent}"><b>{i + 1}.</b></font>&nbsp;&nbsp;'
            f'{_math_inline(q.get("question", ""), 12.5)}{hint}', question_style))

        # Only the minority of questions the model marked as genuinely
        # needing one (_TEST_IMAGE_RULE) carry an "image" at all — most
        # questions are answered from their own text and print none.
        img = q.get("image") if isinstance(q.get("image"), dict) else None
        if img and img.get("path"):
            body = _pdf_illustration_image(img.get("path", ""), "", img.get("credit", ""),
                                           max_w=220, max_h=160)
            if body:
                story.append(KeepTogether([Spacer(1, 4)] + body))

        if q_type == 'open_ended':
            story.extend(_pdf_answer_lines(3))
        else:
            for j, opt in enumerate(q.get("options", [])):
                letter = _LETTERS[j] if j < len(_LETTERS) else str(j)
                # A box to tick on a multi-answer question, a plain letter
                # otherwise. Written with characters this font really has:
                # a ☐ silently prints as a tofu box.
                box = '<font color="%s">[&nbsp;&nbsp;]</font>&nbsp;' % _LECTURE_RULE \
                    if q_type == 'multiple_select' else ''
                story.append(Paragraph(f'{box}{letter})&nbsp;{_math_inline(opt, 11)}', opt_style))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.7, color=HexColor(_LECTURE_RULE)))
    story.append(Paragraph(
        f"{ui['total']}: {len(questions)}&nbsp;&nbsp;·&nbsp;&nbsp;"
        f"{ui['max_score']}: {len(questions)}",
        ParagraphStyle(name="TestFoot", fontName=FONT_NAME, fontSize=8.5, leading=12,
                       alignment=TA_CENTER, textColor=HexColor(_LECTURE_MUTED),
                       spaceBefore=5)))

    # ── the key, on its own page ────────────────────────────────────────
    if include_key and not student_only and questions:
        from reportlab.platypus import PageBreak
        story.append(PageBreak())
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            ui['key_title'],
            ParagraphStyle(name="KeyTitle", fontName=MATH_FONT_BOLD, fontSize=15, leading=19,
                           alignment=TA_CENTER, textColor=HexColor(_LECTURE_INK))))
        story.append(Paragraph(
            ui['key_hint'],
            ParagraphStyle(name="KeyHint", fontName=FONT_NAME, fontSize=8.5, leading=12,
                           alignment=TA_CENTER, textColor=HexColor(_LECTURE_MUTED),
                           spaceAfter=12)))

        head = ParagraphStyle(name="KeyHead", fontName=FONT_NAME_BOLD, fontSize=9, leading=12,
                              textColor=HexColor("#FFFFFF"))
        num = ParagraphStyle(name="KeyNum", fontName=FONT_NAME_BOLD, fontSize=10, leading=14,
                             alignment=TA_CENTER, textColor=HexColor(_LECTURE_INK))
        ans = ParagraphStyle(name="KeyAns", fontName=FONT_NAME_BOLD, fontSize=10, leading=14,
                             textColor=HexColor(accent))
        why = ParagraphStyle(name="KeyWhy", fontName=FONT_NAME, fontSize=9, leading=12.5,
                             textColor=HexColor(_LECTURE_MUTED))

        rows = [[Paragraph(ui['col_no'], head), Paragraph(ui['col_answer'], head),
                 Paragraph(ui['col_why'], head)]]
        for i, q in enumerate(questions):
            note = _math_inline(str(q.get('explanation') or '').strip(), 9)
            if q.get('type') == 'open_ended' and q.get('model_answer'):
                model = _math_inline(str(q['model_answer']).strip(), 9)
                note = (f'<b>{ui["model"]}:</b> {model}<br/>{note}' if note
                        else f'<b>{ui["model"]}:</b> {model}')
            rows.append([Paragraph(str(i + 1), num),
                         Paragraph(letters_for(q), ans),
                         Paragraph(note or '&nbsp;', why)])

        # Proportional widths, not automatic ones: an explanation column
        # sized by its longest sentence pushes the table off the margin.
        table = Table(rows, colWidths=[30, 95, 345], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(accent)),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [HexColor("#FFFFFF"), HexColor(_pdf_light_tint_hex(accent, amount=0.955))]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(_LECTURE_RULE)),
            ('LEFTPADDING', (0, 0), (-1, -1), 7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 7),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table)

    doc.build(story)
    buf.seek(0)
    return buf


# ── Practical tasks ("💡 Амалӣ супоришҳо") ────────────────────────────────────

_PRACTICAL_UI = {
    'Русский': {'individual': 'Индивидуальные задания', 'group': 'Групповые задания',
               'difficulty': {'easy': 'лёгкое', 'medium': 'среднее', 'hard': 'сложное'},
               'roles': 'Роли в группе', 'outcome': 'Результат', 'group_size': 'Состав группы'},
    'Таджикский': {'individual': 'Супоришҳои инфиродӣ', 'group': 'Супоришҳои гурӯҳӣ',
                  'difficulty': {'easy': 'сабук', 'medium': 'миёна', 'hard': 'душвор'},
                  'roles': 'Нақшҳо дар гурӯҳ', 'outcome': 'Натиҷа', 'group_size': 'Таркиби гурӯҳ'},
    'English': {'individual': 'Individual tasks', 'group': 'Group tasks',
               'difficulty': {'easy': 'easy', 'medium': 'medium', 'hard': 'hard'},
               'roles': 'Roles in the group', 'outcome': 'Expected outcome', 'group_size': 'Group size'},
}


def build_practical_pdf(content: dict) -> io.BytesIO:
    """A hands-on worksheet: individual tasks by difficulty, then group
    tasks with named roles — same masthead/student-header furniture as
    build_test_pdf, but no answer key (there is no single correct option
    to key against; grading is against "expected_outcome" in the
    teacher's own copy of this same sheet)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm)
    story = []

    title = content.get("title", "Амалӣ супоришҳо")
    desc = content.get("description", "")
    subject = content.get("subject", "")
    grade = content.get("grade", "")
    language = str(content.get("language") or "Русский")
    ui = _test_ui(language)
    pui = _PRACTICAL_UI.get(language, _PRACTICAL_UI['Русский'])
    accent = get_subject_accent_hex(subject)

    story.extend(_pdf_lecture_masthead(
        title, desc, subject, grade, language,
        _PDF_KONSPEKT_LABELS.get(language,
                                 _PDF_KONSPEKT_LABELS['Русский']).get('grade_suffix', 'класс'),
        accent=accent))
    story.extend(_pdf_student_header(ui, accent))

    section_style = ParagraphStyle(name="PracticalSection", fontName=FONT_NAME_BOLD, fontSize=13.5,
                                   leading=17, textColor=HexColor(accent), spaceBefore=16, spaceAfter=8)
    task_title_style = ParagraphStyle(name="PracticalTaskTitle", fontName=MATH_FONT_BOLD, fontSize=12,
                                      leading=16, textColor=HexColor(_LECTURE_INK), spaceAfter=3)
    body_style = ParagraphStyle(name="PracticalBody", fontName=FONT_NAME, fontSize=10.5, leading=15,
                                alignment=TA_JUSTIFY, textColor=HexColor(_LECTURE_INK), spaceAfter=4)
    label_style = ParagraphStyle(name="PracticalLabel", fontName=FONT_NAME_BOLD, fontSize=9,
                                 leading=13, textColor=HexColor(_LECTURE_MUTED))
    diff_style = ParagraphStyle(name="PracticalDiff", fontName=FONT_NAME_BOLD, fontSize=9,
                                leading=13, textColor=HexColor("#FFFFFF"))

    def diff_badge(level: str):
        label = pui['difficulty'].get(str(level or 'medium').lower(), level or '')
        badge_color = {'easy': '#16A34A', 'medium': '#D97706', 'hard': '#DC2626'}.get(
            str(level or 'medium').lower(), '#6B7280')
        t = Table([[Paragraph(label.upper(), diff_style)]], colWidths=[60])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor(badge_color)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return t

    individual = content.get("individual_tasks") or []
    if individual:
        story.append(Paragraph(pui['individual'], section_style))
        for i, task in enumerate(individual):
            if not isinstance(task, dict):
                continue
            head = Table([[Paragraph(f"{i + 1}. {task.get('title', '')}", task_title_style),
                          diff_badge(task.get('difficulty'))]], colWidths=[400, 65])
            head.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                      ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                      ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
            body = [head, Spacer(1, 3), Paragraph(task.get("instructions", ""), body_style)]
            if task.get("expected_outcome"):
                body.append(Paragraph(f"{pui['outcome']}: {task['expected_outcome']}", label_style))
            story.append(KeepTogether(body))
            story.append(Spacer(1, 10))

    group = content.get("group_tasks") or []
    if group:
        story.append(Paragraph(pui['group'], section_style))
        for i, task in enumerate(group):
            if not isinstance(task, dict):
                continue
            body = [Paragraph(f"{i + 1}. {task.get('title', '')}", task_title_style)]
            if task.get("group_size"):
                body.append(Paragraph(f"{pui['group_size']}: {task['group_size']}", label_style))
            body.append(Spacer(1, 3))
            body.append(Paragraph(task.get("instructions", ""), body_style))
            roles = task.get("roles") or []
            if roles:
                body.append(Paragraph(pui['roles'], label_style))
                for role in roles:
                    body.append(Paragraph(f"• {role}", body_style))
            if task.get("expected_outcome"):
                body.append(Paragraph(f"{pui['outcome']}: {task['expected_outcome']}", label_style))
            story.append(KeepTogether(body))
            story.append(Spacer(1, 10))

    doc.build(story)
    buf.seek(0)
    return buf


def _pdf_notebook_page(canvas_obj, doc_obj):
    """Draw ruled notebook paper across a whole PDF page.

    The "playful" deck is notebook-themed on every .pptx slide
    (_pptx_notebook_lines + _pptx_spiral_margin) and on its cover
    (cover_builder._build_cover_playful), but the PDF export only had the
    themed cover — pages 2..n came out plain white, so the preview a
    teacher actually reads in the app stopped looking like the deck after
    the first page.

    Same three elements and the same colours as the other two
    implementations, in reportlab's points-from-bottom-left coordinates:
    cream paper, faint horizontal rules, a punched-hole margin with a pink
    vertical rule. Drawn as an onPage callback so it lands UNDER every
    flowable without the body layout having to know about it.
    """
    w, h = A4
    canvas_obj.saveState()

    # Paper.
    canvas_obj.setFillColor(HexColor('#FFFDF7'))
    canvas_obj.rect(0, 0, w, h, stroke=0, fill=1)

    # Ruled lines. 23pt apart, matching the pptx's 0.32in spacing.
    canvas_obj.setStrokeColor(HexColor('#EEE4C8'))
    canvas_obj.setLineWidth(0.9)
    y = 40
    while y < h - 30:
        canvas_obj.line(0, y, w, y)
        y += 23

    # Margin rule, then the punched holes on top of it.
    canvas_obj.setStrokeColor(HexColor('#F3C6C6'))
    canvas_obj.setLineWidth(1.4)
    canvas_obj.line(38, 20, 38, h - 20)

    canvas_obj.setStrokeColor(HexColor('#D8D2C4'))
    canvas_obj.setFillColor(HexColor('#FFFDF7'))
    canvas_obj.setLineWidth(1.1)
    y = h - 44
    while y > 30:
        canvas_obj.circle(19, y, 6, stroke=1, fill=1)
        y -= 39

    canvas_obj.restoreState()


def build_presentation_pdf(content: dict) -> io.BytesIO:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm)
    story = []

    title = content.get("title", "Презентация")
    desc = content.get("description", "")
    subject = content.get("subject", "")
    grade = content.get("grade", "")
    language = content.get("language", "Русский")

    slides = content.get("slides", [])

    # Same per-subject accent + per-template header/font language as the
    # konspekt PDF (see _add_konspekt_body_pdf) and the pptx builder above
    # — reused rather than reinvented so all three exports of the same
    # deck (web preview, pptx, pdf) look like one coherent product.
    tmpl = get_template(content.get("template"))
    ACCENT = get_subject_accent_hex(content.get("subject"))
    ACCENT_DARK = _pdf_dark_shade_hex(ACCENT)
    ACCENT_SOFT = _pdf_light_tint_hex(ACCENT)
    title_font = MATH_FONT_BOLD if tmpl.font_family == 'serif' else FONT_NAME_BOLD
    body_font = MATH_FONT if tmpl.font_family == 'serif' else FONT_NAME

    # Full-bleed cover page — the SAME templated cover_builder.build_cover_image
    # the konspekt/lecture PDF uses (see build_konspekt_pdf), instead of this
    # deck's own bespoke full-width blue gradient band (_pdf_deck_header,
    # removed — it was a leftover from before the pptx cover was redesigned
    # away from that exact look on direct teacher feedback; the PDF export
    # never got the matching update, so it kept reading as a different,
    # generic-feeling document from the konspekt/lecture PDFs).
    cover_png = None
    try:
        from app.cover_builder import build_cover_image
        cover_png = build_cover_image(
            subject, title, grade, language,
            template_id=content.get("template") or "zamonaviy",
            doc_type_label="ПРЕЗЕНТАЦИЯ",
        )
    except Exception as e:
        logger.warning(f"Presentation cover generation failed for '{title[:50]}': {e}")

    def _draw_cover(canvas_obj, doc_obj):
        if cover_png:
            canvas_obj.drawImage(ImageReader(io.BytesIO(cover_png)), 0, 0, width=A4[0], height=A4[1])

    if cover_png:
        from reportlab.platypus import PageBreak
        story.append(PageBreak())
    elif desc:
        # No cover (best-effort generation failed) — at least keep the
        # description visible instead of silently dropping it.
        story.append(Paragraph(f'<font color="#64748B">{desc}</font>', _styles()['DocSubtitle']))
        story.append(Spacer(1, 14))

    minimal_header = tmpl.header_style in ("underline", "smallcaps")

    for i, s in enumerate(slides):
        slide_title = s.get("title", f"Слайд {i + 1}")
        bullets = s.get("bullet_points", [])
        notes = s.get("speaker_notes", "")

        story.append(Spacer(1, 8))

        # "underline"/"smallcaps" (zamonaviy/minimal) get a quieter, card-
        # free header — a numbered eyebrow line + thin rule — matching the
        # same "drop the filled card" restraint the pptx version uses for
        # these two templates; the other three keep the filled number card.
        if minimal_header:
            d = Drawing(460, 22)
            num_str = f'{i + 1:02d}'
            d.add(String(0, 4, num_str, fontName=title_font, fontSize=11, fillColor=HexColor(ACCENT)))
            d.add(String(24, 4, slide_title.upper() if tmpl.header_style == "smallcaps" else slide_title,
                          fontName=title_font, fontSize=13, fillColor=HexColor(_PDF_DARK)))
            story.append(d)
            story.append(HRFlowable(width="18%", thickness=1.5, color=HexColor(ACCENT), spaceAfter=6))
        elif tmpl.header_style == "bar":
            # "rangli" — a bold FLAT full-width colored band with white
            # text, matching TemplateCard's mockup and the pptx "bar"
            # branch, instead of the same soft rounded number-card every
            # other template used to share.
            d = Drawing(460, 30)
            d.add(Rect(0, 0, 460, 30, fillColor=HexColor(ACCENT), strokeColor=None))
            d.add(String(10, 10, f'{i + 1}. {slide_title}', fontName=title_font, fontSize=13, fillColor=HexColor('#FFFFFF')))
            story.append(d)
        else:
            # One consistent brand-color slide-number card instead of a
            # different rainbow color per slide/bullet — reads as a single
            # designed deck rather than a randomly tinted list.
            d = Drawing(460, 32)
            d.add(Rect(0, 0, 460, 30, fillColor=HexColor(ACCENT_SOFT), strokeColor=None, rx=7, ry=7))
            d.add(Rect(0, 0, 5, 30, fillColor=HexColor(ACCENT), strokeColor=None))
            d.add(Circle(27, 15, 11, fillColor=HexColor(ACCENT), strokeColor=None))
            num_str = str(i + 1)
            d.add(String(27 - (3.5 * len(num_str)), 11, num_str, fontName=FONT_NAME_BOLD, fontSize=11, fillColor=HexColor('#FFFFFF')))
            d.add(String(48, 10, slide_title, fontName=title_font, fontSize=13, fillColor=HexColor(_PDF_DARK)))
            story.append(d)

        for j, bp in enumerate(bullets):
            story.append(_pdf_numbered_bullet(j + 1, bp, ACCENT))

        # The slide's explanatory paragraph. It is what the teacher says
        # while the bullets are on screen, and it was silently dropped
        # here while the .pptx printed it.
        body_text = str(s.get("body") or "").strip()
        if body_text:
            story.append(Paragraph(body_text, ParagraphStyle(
                name=f'DeckBody_{i}', fontName=body_font, fontSize=10,
                leading=14.5, textColor=HexColor('#334155'),
                alignment=TA_JUSTIFY, leftIndent=20, rightIndent=6,
                spaceBefore=3, spaceAfter=6)))

        # And the slide's illustration, with the credit its licence
        # requires — also dropped before.
        image = s.get("image")
        if isinstance(image, dict) and image.get("path"):
            figure = _pdf_illustration_image(
                image.get("path", ""), "", image.get("credit", ""),
                max_w=300, max_h=200)
            if figure:
                story.append(Spacer(1, 4))
                story.extend(figure)

        # Optional per-slide graphic — table/comparison/process, the same
        # AI-chosen visual_blocks vocabulary + renderer a konspekt already
        # uses (see _pdf_visual_block), so a slide with genuinely tabular/
        # comparative/sequential content gets a real diagram instead of
        # forcing everything through bullet_points.
        visual = s.get("visual")
        if visual:
            story.extend(_pdf_visual_block(visual, ACCENT))

        if notes:
            notes_style = ParagraphStyle(
                name=f'Notes_{i}',
                fontName=body_font,
                fontSize=9,
                leading=13,
                textColor=HexColor('#64748B'),
                backColor=HexColor('#F8FAFC'),
                borderPadding=(4, 6, 4, 6),
                leftIndent=20,
                rightIndent=10,
                spaceAfter=8,
            )
            story.append(Spacer(1, 4))
            story.append(Paragraph(f'<font color="{ACCENT}"><b>Заметки:</b></font> {notes}', notes_style))

        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#E2E8F0')))

    story.extend(_pdf_footer())
    # "playful" is the notebook theme: its inner pages get the same paper
    # the cover and every .pptx slide already have. Other templates keep
    # plain pages — a ruled background under, say, the academic layout
    # would just be noise.
    notebook = (content.get("template") or "") == "playful"
    doc.build(
        story,
        onFirstPage=_draw_cover,
        onLaterPages=_pdf_notebook_page if notebook else (lambda c, d: None),
    )
    buf.seek(0)
    return buf
