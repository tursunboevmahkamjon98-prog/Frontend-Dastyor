# -*- coding: utf-8 -*-
"""Slide compositions — the part that stops every slide being the same slide.

The problem this solves
-----------------------
Before this module a deck was: header, a grid of bullet cards, a grey
paragraph. Ten times. The subject changed the palette, the motif and the
card silhouette, but the SKELETON was identical, and that is what makes
two decks read as one template in two colours no matter how different the
decoration is.

Here a slide picks a composition from its own content. A slide naming
four parts of something becomes a central object with the parts around
it. A slide describing a sequence becomes a flow with arrows. A slide
whose point is one number sets that number huge. A slide with a picture
lets the picture own half the slide, bled to the edge, instead of sitting
in a box beside a list.

Contract
--------
A layout owns the area BELOW the header: x 0.9"–12.4", y 1.55"–6.95" on
a 13.333×7.5" slide. It draws everything it needs and returns True. The
header, footer, progress bar, speaker notes and transition are the
caller's (build_presentation_pptx) — a layout never touches those.

Returning False means "not for this slide after all", and the caller
falls through to its own long-standing bullets/picture/formula path,
which stays the safety net for anything unusual.

Imports of export_builder are deliberately late (inside functions):
export_builder imports this module, so a module-level import would be a
cycle. By the time any layout runs, export_builder is fully loaded.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from app import pptx_shapes, slide_characters


# The box a layout may draw in. Anything outside belongs to the header,
# the footer rule or the margins the whole deck shares.
TOP_IN = 1.55
BOTTOM_IN = 6.95
LEFT_IN = 0.9
RIGHT_IN = 12.4
WIDTH_IN = RIGHT_IN - LEFT_IN
SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5


@dataclass
class Ctx:
    """Everything a layout needs to draw itself, resolved once per slide by
    build_presentation_pptx so no layout has to re-derive a colour or a
    font and get it subtly different."""
    slide: object
    accent: RGBColor
    accent_dark: RGBColor
    accent_soft: RGBColor
    support: RGBColor
    ink: RGBColor
    muted: RGBColor
    bg: tuple
    title_font: str
    body_font: str
    template_id: str
    grade_tier: str            # "junior" | "middle" | "senior"
    language: str
    index: int
    total: int
    image_path: str | None = None
    image_credit: str = ""
    character_prop: str = "pointer"
    # The figure is drawn in `accent`; its prop needs a colour that
    # actually reads against that. See SubjectTemplate.prop_color.
    prop_color: RGBColor | None = None
    # The deck's own topic — the hub label for the central layout. The
    # first cut used the SLIDE title there and got "Растительна я и
    # животная к…" wrapped inside a circle, directly under a header that
    # already said the same words.
    topic: str = ""


# ── small shared pieces ──────────────────────────────────────────────────


def _text(ctx, x, y, w, h, s, size, bold=False, color=None, align=PP_ALIGN.LEFT,
          font=None):
    from app.export_builder import _add_text
    return _add_text(ctx.slide, Inches(x), Inches(y), Inches(w), Inches(h),
                     s, size, bold, color if color is not None else ctx.ink,
                     align, font_name=font or ctx.body_font)


def _shape(ctx, shape_type, x, y, w, h, fill=None, line=None, line_pt=1.0,
           rotation=None, adjust=None):
    shp = ctx.slide.shapes.add_shape(shape_type, Inches(x), Inches(y),
                                     Inches(max(w, 0.01)), Inches(max(h, 0.01)))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.fill.solid()
        shp.line.fill.fore_color.rgb = line
        shp.line.width = Pt(line_pt)
    if rotation is not None:
        shp.rotation = rotation
    if adjust is not None:
        try:
            shp.adjustments[0] = adjust
        except Exception:
            pass
    return pptx_shapes.flatten(shp)


def _lines(s, width_in, pt):
    from app.export_builder import _estimate_pptx_lines
    return _estimate_pptx_lines(s, width_in, pt)


def _fit(s, width_in, sizes, max_h_in):
    """The largest size in `sizes` at which `s` fits `max_h_in`. Shrinking
    beats truncating — a sentence that stops mid-thought is a worse slide
    than the same sentence a point smaller."""
    for pt in sizes:
        h = _lines(s, width_in, pt) * pt * 1.34 / 72.0
        if h <= max_h_in:
            return pt, h
    pt = sizes[-1]
    return pt, _lines(s, width_in, pt) * pt * 1.34 / 72.0


def _character(ctx, x, y, h, pose):
    """Place a figure, if this deck's audience wants one there.

    Age decides: the youngest classes get a figure on most slides because
    a person pointing at the thing IS the explanation at that age; the
    oldest get them rarely, because at that age the same device reads as
    talking down. Everyone in between gets them on roughly half."""
    if ctx.grade_tier == "senior" and ctx.index % 4 != 1:
        return
    if ctx.grade_tier == "middle" and ctx.index % 2 == 1:
        return
    slide_characters.draw(ctx.slide, x, y, h, ctx.accent,
                          ctx.prop_color or ctx.support,
                          pose=pose, prop=ctx.character_prop)


# ── callouts ─────────────────────────────────────────────────────────────
#
# Each kind has its own silhouette, not just its own word: a rule the
# brief is explicit about. "Важно" is a solid bar you cannot skim past,
# "Формула" is a panel, "Факт" is a soft aside.

_CALLOUT_LABEL = {
    "important": {"Русский": "ВАЖНО", "Таджикский": "МУҲИМ", "English": "IMPORTANT",
                  "Английский": "IMPORTANT"},
    "remember": {"Русский": "ЗАПОМНИ", "Таджикский": "ДАР ХОТИР ДОР",
                 "English": "REMEMBER", "Английский": "REMEMBER"},
    "fact": {"Русский": "ИНТЕРЕСНЫЙ ФАКТ", "Таджикский": "ДАЛЕЛИ ҶОЛИБ",
             "English": "DID YOU KNOW", "Английский": "DID YOU KNOW"},
    "why": {"Русский": "ПОЧЕМУ?", "Таджикский": "ЧАРО?", "English": "WHY?",
            "Английский": "WHY?"},
    "example": {"Русский": "ПРИМЕР", "Таджикский": "МИСОЛ", "English": "EXAMPLE",
                "Английский": "EXAMPLE"},
}


def draw_callout(ctx, kind, text, x, y, w) -> float:
    """One callout. Returns the height it used."""
    kind = str(kind or "important").lower()
    label = _CALLOUT_LABEL.get(kind, _CALLOUT_LABEL["important"]).get(
        ctx.language, _CALLOUT_LABEL.get(kind, _CALLOUT_LABEL["important"])["Русский"])
    pt, text_h = _fit(text, w - 0.7, (14, 13, 12, 11), 1.5)
    h = max(0.78, text_h + 0.62)

    if kind == "important":
        _shape(ctx, MSO_SHAPE.RECTANGLE, x, y, w, h, ctx.accent_soft)
        _shape(ctx, MSO_SHAPE.RECTANGLE, x, y, Inches(0.06).inches, h, ctx.accent)
    elif kind == "remember":
        _shape(ctx, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, None,
               line=ctx.accent, line_pt=1.5, adjust=0.12)
    elif kind == "fact":
        _shape(ctx, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, ctx.accent_soft, adjust=0.2)
        _shape(ctx, MSO_SHAPE.OVAL, x + w - 0.42, y - 0.14, 0.32, 0.32, ctx.accent)
    elif kind == "why":
        _shape(ctx, MSO_SHAPE.ROUND_2_SAME_RECTANGLE, x, y, w, h, None,
               line=ctx.support, line_pt=1.5)
        _shape(ctx, MSO_SHAPE.RECTANGLE, x, y + h - 0.035, w, 0.035, ctx.accent)
    else:
        _shape(ctx, MSO_SHAPE.SNIP_2_DIAG_RECTANGLE, x, y, w, h, ctx.accent_soft)

    _text(ctx, x + 0.26, y + 0.13, w - 0.5, 0.26, label, 10, True, ctx.accent)
    _text(ctx, x + 0.26, y + 0.4, w - 0.5, text_h + 0.2, text, pt, False, ctx.ink)
    return h


def _callout_of(sd):
    """The slide's callout, if the model wrote one: {"kind": ..., "text":
    ...}. Optional everywhere — a deck generated before this field
    existed, or a slide that simply didn't need one, renders unchanged."""
    c = sd.get("callout")
    if not isinstance(c, dict):
        return None
    text = _clean(c.get("text"))
    if not text:
        return None
    kind = str(c.get("kind") or "important").strip().lower()
    return (kind if kind in _CALLOUT_LABEL else "important"), text


def _callout(ctx, sd, x, y, w) -> float:
    """Draw the slide's callout at (x, y) if there is one AND it fits.
    Returns the height used, 0 if nothing was drawn — a callout is the
    first thing to give way when a slide is full."""
    found = _callout_of(sd)
    if not found:
        return 0.0
    if y + 0.85 > BOTTOM_IN:
        return 0.0
    return draw_callout(ctx, found[0], found[1], x, y, w)


# ── layouts ──────────────────────────────────────────────────────────────


def _hero(ctx, sd) -> bool:
    """Giant typography. One idea, set as large as it will go, with the
    supporting sentence under it and a figure presenting it.

    For the slides that carry a single thought — an opening, a closing —
    where a grid of cards would be four boxes of nothing."""
    body = _clean(sd.get("body"))
    bullets = _strings(sd.get("bullet_points"))
    lead = bullets[0] if bullets else body
    if not lead:
        return False
    rest = body if (bullets and body) else ""

    text_w = 8.2
    pt, h = _fit(lead, text_w, (54, 46, 40, 34, 30), 3.0)
    top = TOP_IN + max(0.2, (BOTTOM_IN - TOP_IN - h - (1.0 if rest else 0)) / 2)

    _shape(ctx, MSO_SHAPE.RECTANGLE, LEFT_IN, top - 0.28, 1.3, 0.05, ctx.accent)
    _text(ctx, LEFT_IN, top, text_w, h + 0.3, lead, pt, True, ctx.ink,
          font=ctx.title_font)
    y = top + h + 0.3
    if rest:
        rpt, rh = _fit(rest, text_w, (17, 16, 15, 14), 1.5)
        _text(ctx, LEFT_IN, y, text_w, rh + 0.25, rest, rpt, False, ctx.muted)
        y += rh + 0.2

    _callout(ctx, sd, LEFT_IN, y + 0.25, 7.0)
    _character(ctx, 10.9, BOTTOM_IN - 2.6, 2.4, "present")
    return True


def _central(ctx, sd) -> bool:
    """One object in the middle, its parts named around it.

    This is the composition the brief asks for by name: blood in the
    centre, plasma/erythrocytes/leukocytes/platelets around it; the cell
    as a big central object with its structures labelled. Anything that
    is "X consists of A, B, C, D" is this shape, and a vertical list is
    the wrong shape for it."""
    bullets = _strings(sd.get("bullet_points"))
    if not (3 <= len(bullets) <= 6):
        return False

    cx, cy = 6.55, (TOP_IN + BOTTOM_IN) / 2
    core_d = 2.3
    # The hub names the THING the parts belong to. That is the deck's
    # topic, not the slide's title: the title is already set in the header
    # directly above, and repeating a full sentence inside a circle is how
    # "Растительна я и животная к…" happened.
    hub = _shorten(ctx.topic or sd.get("title") or "", 22)

    _shape(ctx, MSO_SHAPE.OVAL, cx - core_d / 2 - 0.22, cy - core_d / 2 - 0.22,
           core_d + 0.44, core_d + 0.44, ctx.accent_soft)
    _shape(ctx, MSO_SHAPE.OVAL, cx - core_d / 2, cy - core_d / 2, core_d, core_d,
           ctx.accent)
    hpt, hh = _fit(hub, core_d - 0.5, (18, 16, 14, 12), 1.4)
    from app.export_builder import _TEXT_WHITE
    _text(ctx, cx - core_d / 2 + 0.25, cy - hh / 2, core_d - 0.5, hh + 0.3,
          hub, hpt, True, _TEXT_WHITE, PP_ALIGN.CENTER, font=ctx.title_font)

    n = len(bullets)
    rx, ry = 4.35, 2.0
    node_w, node_h = 2.75, 0.86
    # An even number of nodes started at the top puts one straight down,
    # where it collided with the footer rule. Offsetting even counts by
    # half a step lands them on the diagonals instead, which also uses the
    # slide's width rather than its height — and the slide is wide.
    start = -math.pi / 2 + (math.pi / n if n % 2 == 0 else 0)
    for i, bp in enumerate(bullets):
        a = start + i * (2 * math.pi / n)
        px, py = cx + rx * math.cos(a), cy + ry * math.sin(a)
        # A connector from the hub edge to the node, drawn first.
        ex, ey = cx + (core_d / 2 + 0.1) * math.cos(a), cy + (core_d / 2 + 0.1) * math.sin(a)
        length = math.hypot(px - ex, py - ey)
        ang = math.degrees(math.atan2(py - ey, px - ex))
        _shape(ctx, MSO_SHAPE.RECTANGLE, (ex + px) / 2 - length / 2,
               (ey + py) / 2, length, 0.018, ctx.accent_soft, rotation=ang)
        bpt, bh = _fit(bp, node_w - 0.4, (13, 12, 11), node_h - 0.24)
        _shape(ctx, MSO_SHAPE.ROUNDED_RECTANGLE, px - node_w / 2, py - node_h / 2,
               node_w, max(node_h, bh + 0.24), None, line=ctx.accent, line_pt=1.25,
               adjust=0.2)
        _shape(ctx, MSO_SHAPE.OVAL, px - node_w / 2 - 0.11, py - 0.11, 0.22, 0.22,
               ctx.accent)
        _text(ctx, px - node_w / 2 + 0.2, py - bh / 2 - 0.02, node_w - 0.4,
              bh + 0.25, bp, bpt, False, ctx.ink, PP_ALIGN.CENTER)
    return True


def _flow(ctx, sd) -> bool:
    """A → B → C. The composition for anything that happens in order:
    photosynthesis, a reaction, an algorithm, the steps of a solution.

    Chevrons rather than boxes, because the shape itself says "and then"."""
    bullets = _strings(sd.get("bullet_points"))
    if not (3 <= len(bullets) <= 5):
        return False

    n = len(bullets)
    gap = 0.22
    # Every chevron after the first is drawn 0.18" wider so its point
    # overlaps its neighbour. That overhang has to come OUT of the
    # available width, or the last chevron's point runs off the right
    # edge of the slide — which it did, by exactly 0.18".
    point = 0.18
    step_w = (WIDTH_IN - point - gap * (n - 1)) / n
    # 2.25" left most of the chevron empty under a two-word step. The
    # step is only as tall as it needs to be, and the block is centred in
    # the space instead of hugging the header.
    step_h = 1.7
    body_probe = _clean(sd.get("body"))
    # The steps and the paragraph under them are ONE block, and the block
    # is centred in the space below the header. Hanging it off the header
    # left three inches of nothing under the last chevron.
    body_h_probe = 0.0
    if body_probe:
        _, body_h_probe = _fit(body_probe, WIDTH_IN - 3.0, (15, 14, 13, 12), 2.0)
        body_h_probe += 0.42
    top = TOP_IN + max(0.2, (BOTTOM_IN - TOP_IN - step_h - body_h_probe) / 2)
    for i, bp in enumerate(bullets):
        x = LEFT_IN + i * (step_w + gap)
        shp = MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON
        _shape(ctx, shp, x, top, step_w + (point if i else 0), step_h,
               ctx.accent_soft if i % 2 == 0 else None,
               line=None if i % 2 == 0 else ctx.accent, line_pt=1.25)
        _shape(ctx, MSO_SHAPE.OVAL, x + step_w / 2 - 0.21, top + 0.2, 0.42, 0.42,
               ctx.accent)
        from app.export_builder import _TEXT_WHITE
        _text(ctx, x + step_w / 2 - 0.21, top + 0.26, 0.42, 0.32, str(i + 1), 13,
              True, _TEXT_WHITE, PP_ALIGN.CENTER)
        bpt, bh = _fit(bp, step_w - 0.6, (14, 13, 12, 11), 0.9)
        _text(ctx, x + 0.3, top + 0.78 + (0.62 - bh) / 2, step_w - 0.6, bh + 0.3,
              bp, bpt, True, ctx.ink, PP_ALIGN.CENTER)

    body = _clean(sd.get("body"))
    y = top + step_h + 0.42
    if body:
        bpt, bh = _fit(body, WIDTH_IN - 3.0, (15, 14, 13, 12), BOTTOM_IN - y - 0.1)
        _text(ctx, LEFT_IN, y, WIDTH_IN - 3.0, bh + 0.3, body, bpt, False, ctx.muted)
    _character(ctx, 11.15, BOTTOM_IN - 1.9, 1.75, "point_left")
    return True


def _bignumber(ctx, sd) -> bool:
    """One number, set enormous, with what it means beside it.

    Only when the slide really does turn on a figure — a date, a count, a
    percentage. Pulled from the bullets rather than invented."""
    bullets = _strings(sd.get("bullet_points"))
    num, rest = _extract_number(bullets)
    if not num:
        return False

    _text(ctx, LEFT_IN, TOP_IN + 0.5, 5.4, 2.8, num, 150 if len(num) <= 3 else 110,
          True, ctx.accent, PP_ALIGN.LEFT, font=ctx.title_font)
    _shape(ctx, MSO_SHAPE.RECTANGLE, 6.55, TOP_IN + 0.7, 0.045, 3.4, ctx.accent_soft)

    y = TOP_IN + 0.7
    for bp in rest[:4]:
        bpt, bh = _fit(bp, 5.1, (17, 16, 15, 14), 1.2)
        _text(ctx, 6.95, y, 5.1, bh + 0.3, bp, bpt, False, ctx.ink)
        y += bh + 0.42
    body = _clean(sd.get("body"))
    if body and y < BOTTOM_IN - 0.9:
        bpt, bh = _fit(body, 5.1, (14, 13, 12), BOTTOM_IN - y - 0.2)
        _text(ctx, 6.95, y + 0.1, 5.1, bh + 0.3, body, bpt, False, ctx.muted)
    _character(ctx, 2.6, BOTTOM_IN - 2.2, 2.1, "point_right")
    return True


def _split_image(ctx, sd) -> bool:
    """The picture owns half the slide, bled to the edge, with the text in
    the other half.

    The brief's complaint about "[текст] [обычная прямоугольная картинка]"
    is this layout's whole reason for existing: a picture that runs off
    the edge of the slide reads as a designed composition, one floating in
    a box reads as a 2010 school deck."""
    if not ctx.image_path:
        return False
    from PIL import Image as PILImage

    on_right = ctx.index % 2 == 0
    half_w = 5.6
    img_x = SLIDE_W_IN - half_w if on_right else 0.0
    band_top, band_h = 1.5, SLIDE_H_IN - 1.5 - 0.55

    # A tinted panel behind the picture, so a portrait image that cannot
    # fill the half still reads as a deliberate block rather than a gap.
    _shape(ctx, MSO_SHAPE.RECTANGLE, img_x, band_top, half_w, band_h, ctx.accent_soft)
    try:
        with PILImage.open(ctx.image_path) as im:
            iw, ih = im.size
        scale = max(half_w / iw, band_h / ih)      # cover, not contain
        tw, th = iw * scale, ih * scale
        # Centre the overflow, then let the panel clip it visually by
        # sitting flush to the slide edge.
        px = img_x + (half_w - tw) / 2
        py = band_top + (band_h - th) / 2
        if tw > half_w * 1.6 or th > band_h * 1.6:
            scale = min(half_w / iw, band_h / ih)   # too extreme a crop
            tw, th = iw * scale, ih * scale
            px, py = img_x + (half_w - tw) / 2, band_top + (band_h - th) / 2
        ctx.slide.shapes.add_picture(ctx.image_path, Inches(px), Inches(py),
                                     Inches(tw), Inches(th))
    except Exception:
        return False

    tx = LEFT_IN if on_right else half_w + 0.6
    tw_in = SLIDE_W_IN - half_w - LEFT_IN - 0.75

    y = TOP_IN + 0.35
    bullets = _strings(sd.get("bullet_points"))[:4]
    for i, bp in enumerate(bullets):
        bpt, bh = _fit(bp, tw_in - 0.45, (19, 18, 17, 16), 1.3)
        _shape(ctx, MSO_SHAPE.RECTANGLE, tx, y + 0.06, 0.045,
               max(0.22, bh - 0.04), ctx.accent)
        _text(ctx, tx + 0.26, y, tw_in - 0.45, bh + 0.3, bp, bpt, False, ctx.ink)
        y += bh + 0.34
    body = _clean(sd.get("body"))
    if body and y < BOTTOM_IN - 0.7:
        bpt, bh = _fit(body, tw_in, (15, 14, 13, 12), BOTTOM_IN - y - 0.35)
        _text(ctx, tx, y + 0.12, tw_in, bh + 0.3, body, bpt, False, ctx.muted)
        y += bh + 0.3
    _callout(ctx, sd, tx, y + 0.2, tw_in)
    if ctx.image_credit:
        _text(ctx, img_x + 0.12, SLIDE_H_IN - 0.62, half_w - 0.24, 0.28,
              ctx.image_credit, 8, False, ctx.muted,
              PP_ALIGN.RIGHT if on_right else PP_ALIGN.LEFT)
    return True


def _timeline(ctx, sd) -> bool:
    """Events on a spine. History's natural shape, and the right one for
    any "first… then… finally" slide."""
    bullets = _strings(sd.get("bullet_points"))
    if not (3 <= len(bullets) <= 5):
        return False

    y = (TOP_IN + BOTTOM_IN) / 2
    # The spine is the subject of this layout, so it is drawn in the
    # accent. In accent_soft it was a barely-there hairline and the cards
    # read as floating rather than as hung off a chronology.
    _shape(ctx, MSO_SHAPE.RECTANGLE, LEFT_IN, y, WIDTH_IN, 0.035, ctx.accent)
    n = len(bullets)
    step = WIDTH_IN / n
    for i, bp in enumerate(bullets):
        cx = LEFT_IN + step * (i + 0.5)
        above = i % 2 == 0
        _shape(ctx, MSO_SHAPE.OVAL, cx - 0.15, y - 0.15 + 0.017, 0.3, 0.3, ctx.accent)
        # Longer stems and taller cards: the first cut used barely half
        # the vertical space it had, which read as a small diagram
        # stranded in the middle of an empty slide.
        stem_h = 0.85
        _shape(ctx, MSO_SHAPE.RECTANGLE, cx - 0.016,
               y - stem_h if above else y + 0.035, 0.032, stem_h, ctx.accent)
        card_w = step - 0.3
        bpt, bh = _fit(bp, card_w - 0.5, (16, 15, 14, 13), 1.7)
        card_h = max(1.15, bh + 0.6)
        card_y = y - stem_h - card_h if above else y + 0.035 + stem_h
        _shape(ctx, MSO_SHAPE.RECTANGLE, cx - card_w / 2, card_y, card_w, card_h,
               None, line=ctx.accent_soft, line_pt=1.25)
        _shape(ctx, MSO_SHAPE.RECTANGLE, cx - card_w / 2, card_y, card_w, 0.045,
               ctx.accent)
        _text(ctx, cx - card_w / 2 + 0.25, card_y + (card_h - bh) / 2,
              card_w - 0.5, bh + 0.25, bp, bpt, False, ctx.ink, PP_ALIGN.CENTER)
    return True


def _comparison(ctx, sd) -> bool:
    """Two things side by side, with the divider doing the comparing."""
    bullets = _strings(sd.get("bullet_points"))
    if len(bullets) not in (2, 4):
        return False
    half = len(bullets) // 2
    left, right = bullets[:half], bullets[half:]

    col_w = (WIDTH_IN - 0.9) / 2
    # The two things being compared, taken from the title: "Растительная и
    # животная клетка" captions the columns "Растительная" / "животная".
    # Without them the reader has to infer which column is which from the
    # bullets, which is the one thing a comparison must not make them do.
    caps = _split_on_vs(sd.get("title"))

    # Height follows the content. A full-height column holding two short
    # bullets is two-thirds empty box, which reads as unfinished rather
    # than as roomy.
    measured = []
    for items in (left, right):
        h_items = 0.0
        for bp in items:
            _, bh = _fit(bp, col_w - 0.9, (18, 17, 16, 15), 1.6)
            h_items += bh + 0.42
        measured.append(h_items)
    head_h = 0.62 if caps else 0.0
    h = min(BOTTOM_IN - TOP_IN - 0.5,
            max(2.2, max(measured) + head_h + 0.8))
    top = TOP_IN + max(0.25, (BOTTOM_IN - TOP_IN - h) / 2)

    for col, (items, tint) in enumerate(((left, ctx.accent_soft), (right, None))):
        x = LEFT_IN + col * (col_w + 0.9)
        _shape(ctx, MSO_SHAPE.ROUNDED_RECTANGLE, x, top, col_w, h,
               tint, line=None if tint else ctx.accent, line_pt=1.4, adjust=0.06)
        y = top + 0.45
        if caps:
            cpt, chh = _fit(caps[col], col_w - 0.7, (19, 18, 17, 16), 0.5)
            _text(ctx, x + 0.35, y, col_w - 0.7, chh + 0.25, caps[col].capitalize(),
                  cpt, True, ctx.accent_dark, font=ctx.title_font)
            _shape(ctx, MSO_SHAPE.RECTANGLE, x + 0.35, y + chh + 0.14,
                   col_w - 0.7, 0.02, ctx.accent)
            y += chh + 0.42
        for bp in items:
            bpt, bh = _fit(bp, col_w - 0.9, (18, 17, 16, 15), 1.6)
            _shape(ctx, MSO_SHAPE.OVAL, x + 0.35, y + 0.06, 0.2, 0.2, ctx.accent)
            _text(ctx, x + 0.68, y, col_w - 0.9, bh + 0.3, bp, bpt, False, ctx.ink)
            y += bh + 0.42

    # The divider, with the comparison mark in it.
    mid = LEFT_IN + col_w + 0.45
    _shape(ctx, MSO_SHAPE.RECTANGLE, mid - 0.012, top + 0.2, 0.024, h - 0.4,
           ctx.accent_soft)
    _shape(ctx, MSO_SHAPE.OVAL, mid - 0.3, (top + h / 2) - 0.3, 0.6, 0.6, ctx.accent)
    from app.export_builder import _TEXT_WHITE
    _text(ctx, mid - 0.3, (top + h / 2) - 0.2, 0.6, 0.4, "VS", 13, True,
          _TEXT_WHITE, PP_ALIGN.CENTER)
    return True


def _magazine(ctx, sd) -> bool:
    """An editorial spread: a drop cap, the paragraph set in two columns,
    a pull quote. For the senior classes, where a grid of cards reads as
    a worksheet rather than as a text worth reading."""
    body = _clean(sd.get("body"))
    if len(body) < 180:
        return False
    bullets = _strings(sd.get("bullet_points"))

    col_w = (WIDTH_IN - 0.7) / 2
    top = TOP_IN + 0.35
    # Split the paragraph at a sentence boundary near the middle.
    cut = _split_sentences(body)
    first, second = cut

    _text(ctx, LEFT_IN, top - 0.16, 0.7, 1.0, first[:1], 58, True, ctx.accent,
          font=ctx.title_font)
    pt, h1 = _fit(first[1:], col_w - 0.62, (15, 14, 13), BOTTOM_IN - top)
    _text(ctx, LEFT_IN + 0.62, top, col_w - 0.62, h1 + 0.3, first[1:], pt, False,
          ctx.ink)
    if second:
        _, h2 = _fit(second, col_w, (pt,), BOTTOM_IN - top)
        _text(ctx, LEFT_IN + col_w + 0.7, top, col_w, h2 + 0.3, second, pt, False,
              ctx.ink)

    if _callout_of(sd):
        _callout(ctx, sd, LEFT_IN, max(top + max(h1, 1.6) + 0.45, BOTTOM_IN - 1.35),
                 WIDTH_IN)
    elif bullets:
        q = bullets[0]
        qy = max(top + max(h1, 1.6) + 0.45, BOTTOM_IN - 1.5)
        if qy + 1.1 <= BOTTOM_IN:
            _shape(ctx, MSO_SHAPE.RECTANGLE, LEFT_IN, qy, WIDTH_IN, 0.035,
                   ctx.accent_soft)
            qpt, qh = _fit(q, WIDTH_IN - 1.6, (22, 20, 18, 16), 1.0)
            _text(ctx, LEFT_IN + 0.1, qy + 0.22, WIDTH_IN - 1.6, qh + 0.3, q, qpt,
                  True, ctx.accent_dark, font=ctx.title_font)
    return True


def _code(ctx, sd) -> bool:
    """A real terminal-style code panel — dark background, monospace,
    line numbers, traffic-light dots — with the explanation and a
    figure beside it.

    Only runs when the model actually wrote a `code` field (see
    _presentation_prompt's rule): this composition exists because
    Informatics/Python decks had NOTHING code-specific before it —
    every "for loop" or "if/else" slide got the same generic bullets
    every other subject's slide would, which is exactly the "AI took
    one template and put text in it" the brief calls out by name."""
    code = sd.get("code")
    if not isinstance(code, dict):
        return False
    snippet = str(code.get("snippet") or "").strip()
    if not snippet:
        return False
    from app.export_builder import _TEXT_WHITE

    lines = snippet.replace("\r\n", "\n").split("\n")[:10]
    lang = str(code.get("language") or "").strip() or "code"

    panel_w = 7.4
    line_h = 0.32
    pad = 0.35
    header_h = 0.5
    panel_h = min(BOTTOM_IN - TOP_IN - 0.3, header_h + len(lines) * line_h + pad * 1.6)
    top = TOP_IN + max(0.1, (BOTTOM_IN - TOP_IN - panel_h) / 2)

    dark = RGBColor(0x1E, 0x1E, 0x2E)
    _shape(ctx, MSO_SHAPE.ROUNDED_RECTANGLE, LEFT_IN, top, panel_w, panel_h, dark, adjust=0.04)

    # Traffic-light dots + language tag, same furniture the informatics
    # template's cover terminal window already uses (slide_decor's
    # "terminal" composition) — the code panel and the cover now read as
    # the same object.
    for n, c in enumerate((RGBColor(0xEF, 0x44, 0x44), RGBColor(0xEA, 0xB3, 0x08),
                           RGBColor(0x22, 0xC5, 0x5E))):
        _shape(ctx, MSO_SHAPE.OVAL, LEFT_IN + pad + n * 0.22, top + 0.17, 0.11, 0.11, c)
    _text(ctx, LEFT_IN + panel_w - 1.5, top + 0.1, 1.15, 0.3, lang, 10, True,
          ctx.accent, PP_ALIGN.RIGHT, font="Consolas")

    y = top + header_h
    gutter_w = 0.4
    for i, line in enumerate(lines):
        _text(ctx, LEFT_IN + pad - 0.08, y, gutter_w, line_h,
              str(i + 1), 11, False, RGBColor(0x6B, 0x72, 0x80), font="Consolas")
        _text(ctx, LEFT_IN + pad + gutter_w, y, panel_w - pad * 2 - gutter_w, line_h,
              line if line.strip() else " ", 12, False, _TEXT_WHITE, font="Consolas")
        y += line_h

    tx = LEFT_IN + panel_w + 0.45
    tw = RIGHT_IN - tx
    explanation = _clean(code.get("explanation")) or _clean(sd.get("body"))
    bullets = _strings(sd.get("bullet_points"))
    by = top + 0.1
    for bp in bullets[:3]:
        bpt, bh = _fit(bp, tw - 0.3, (15, 14, 13), 1.3)
        _shape(ctx, MSO_SHAPE.OVAL, tx, by + 0.08, 0.14, 0.14, ctx.accent)
        _text(ctx, tx + 0.28, by, tw - 0.28, bh + 0.25, bp, bpt, False, ctx.ink)
        by += bh + 0.32
    if explanation:
        bpt, bh = _fit(explanation, tw, (14, 13, 12), max(0.8, top + panel_h - by))
        _text(ctx, tx, by + 0.15, tw, bh + 0.3, explanation, bpt, False, ctx.muted)

    _callout(ctx, sd, LEFT_IN, top + panel_h + 0.3, panel_w)
    return True


def _cards(ctx, sd) -> bool:
    """Not implemented here on purpose — the caller's existing bullet grid
    IS this layout, and it is the one piece of the old renderer worth
    keeping exactly as it is. Returning False hands the slide back."""
    return False


# ── helpers ──────────────────────────────────────────────────────────────


def _strings(value) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out = []
    for v in value:
        s = re.sub(r"\s+", " ", str(v or "")).strip()
        if s:
            out.append(s)
    return out


def _clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _shorten(s, n):
    """Trim to `n` characters at a WORD boundary. Cutting mid-word puts a
    broken syllable in the middle of a design element."""
    s = _clean(s)
    if len(s) <= n:
        return s
    cut = s[:n]
    space = cut.rfind(" ")
    if space >= n * 0.5:
        cut = cut[:space]
    return cut.rstrip(" ,.;:—-") + "…"


def _split_sentences(body):
    """Two roughly equal halves, cut at a sentence end."""
    parts = re.split(r"(?<=[.!?])\s+", body)
    if len(parts) < 2:
        return body, ""
    half = len(body) / 2
    acc, i = 0, 0
    for i, p in enumerate(parts):
        acc += len(p)
        if acc >= half:
            break
    return " ".join(parts[: i + 1]), " ".join(parts[i + 1:])


# Titles that name two things being set against each other. Deliberately
# conservative: "и" joins far more than it contrasts, so it only counts
# when the bullets ALSO split evenly in two.
_VS_WORDS = (" vs ", " и ", " или ", " ва ", " ё ", " versus ")


def _split_on_vs(title):
    """The two sides of a contrasting title, or None.

    "Растительная и животная клетка" -> ("Растительная", "животная"): the
    shared noun after the second side is dropped, because it is the thing
    BOTH columns are, not what tells them apart."""
    t = _clean(title)
    if not t:
        return None
    low = " " + t.lower() + " "
    for w in _VS_WORDS:
        i = low.find(w)
        if i <= 0:
            continue
        left = t[: i - 1].strip(" ,")
        right = t[i - 1 + len(w):].strip(" ,")
        if not left or not right:
            continue
        # Drop the trailing shared noun from the right-hand side, and any
        # leading article-ish word from the left.
        rw = right.split()
        if len(rw) > 1:
            right = " ".join(rw[:-1])
        if len(left) > 26 or len(right) > 26:
            return None
        return left, right
    return None


def _looks_like_comparison(sd) -> bool:
    bullets = _strings(sd.get("bullet_points"))
    if len(bullets) not in (2, 4):
        return False
    title = " " + _clean(sd.get("title")).lower() + " "
    return any(w in title for w in _VS_WORDS)


_NUM_RE = re.compile(r"^[^\d]{0,12}?(\d[\d\s.,]{0,9}\s*%?)\s*(.*)$")


def _extract_number(bullets):
    """A bullet that is essentially one figure, split into the figure and
    what it means. Returns ("", []) when no bullet qualifies — a slide
    without a real number must not get the big-number layout."""
    for i, bp in enumerate(bullets):
        m = _NUM_RE.match(bp)
        if not m:
            continue
        num = m.group(1).strip()
        # Guard against grabbing a year out of the middle of a sentence,
        # or a bullet that merely starts with a digit.
        if len(bp) > 42 or not num or len(num) > 7:
            continue
        rest = [b for j, b in enumerate(bullets) if j != i]
        if m.group(2).strip():
            rest = [m.group(2).strip()] + rest
        if not rest:
            continue
        return num, rest
    return "", []


# ── choosing ─────────────────────────────────────────────────────────────

# What each slide KIND naturally wants, best first. The model already
# tags every slide (see ai_service._presentation_prompt's "kind"), and
# until now the renderer used exactly one of those tags.
_BY_KIND = {
    "intro":       ("split_image", "hero", "magazine"),
    "concepts":    ("central", "split_image", "comparison"),
    "explanation": ("split_image", "magazine", "flow", "central"),
    "example":     ("flow", "bignumber", "split_image"),
    "task":        ("flow", "comparison"),
    "summary":     ("timeline", "central", "hero"),
}

# Some subjects lean on a composition harder than the kind alone implies:
# history teaches in periods, geography in maps, maths in worked steps.
_BY_SUBJECT = {
    "history":       ("timeline",),
    "history_world": ("timeline",),
    "geography":     ("split_image",),
    "mathematics":   ("flow", "bignumber"),
    "algebra":       ("flow",),
    "geometry":      ("split_image",),
    "informatics":   ("flow",),
    "social_studies": ("comparison", "bignumber"),
    "ecology":       ("central", "flow"),
}

_LAYOUTS = {
    "hero": _hero,
    "central": _central,
    "flow": _flow,
    "bignumber": _bignumber,
    "split_image": _split_image,
    "timeline": _timeline,
    "comparison": _comparison,
    "magazine": _magazine,
    "code": _code,
    "cards": _cards,
}


def draw(ctx: Ctx, sd: dict, last_layout: str | None) -> str | None:
    """Pick a composition for this slide and draw it.

    Returns the name of the layout that drew, or None if none applied and
    the caller should fall back to its own bullets path.

    `last_layout` is what the previous slide used. Two identical
    compositions in a row is the single most template-looking thing a
    deck can do, so a candidate that just ran is tried last rather than
    first — it can still win if it is the only one that fits."""
    kind = str(sd.get("kind") or "").strip().lower()

    order: list[str] = []
    for name in _BY_SUBJECT.get(ctx.template_id, ()):
        if name not in order:
            order.append(name)
    for name in _BY_KIND.get(kind, ()):
        if name not in order:
            order.append(name)
    # Everything else, so an untagged slide still gets a real composition.
    for name in ("split_image", "central", "flow", "comparison", "timeline",
                 "bignumber", "magazine", "hero"):
        if name not in order:
            order.append(name)

    # A slide whose point IS a figure belongs in the big-number layout
    # whatever its kind says — "13 климатических поясов" came out as step
    # one of a three-step flow, which says nothing. _extract_number is
    # strict, so this only fires when a bullet really is one number.
    if _extract_number(_strings(sd.get("bullet_points")))[0] and "bignumber" in order:
        order.remove("bignumber")
        order.insert(0, "bignumber")

    # A slide that is literally about two things belongs in the two-column
    # layout whatever its kind says. Without this the anti-repeat rule
    # below could bump comparison down and a "Растительная и животная
    # клетка" slide came out as a radial diagram, which is the wrong
    # shape for a contrast.
    if _looks_like_comparison(sd) and "comparison" in order:
        order.remove("comparison")
        order.insert(0, "comparison")

    # A picture is a strong enough signal to lead with, whatever the kind.
    if ctx.image_path and "split_image" in order:
        order.remove("split_image")
        order.insert(0, "split_image")

    # A slide carrying real code outranks everything — a "for loop" slide
    # with an actual runnable snippet on it is a completely different
    # (and far better) slide than the same content squeezed into a
    # generic bullet grid.
    if isinstance(sd.get("code"), dict) and str(sd["code"].get("snippet") or "").strip():
        order = ["code"] + [n for n in order if n != "code"]

    if last_layout and last_layout in order and len(order) > 1:
        order.remove(last_layout)
        order.append(last_layout)

    # Senior classes get the editorial treatment ahead of the diagrammatic
    # ones; juniors the opposite. Same catalogue, different priorities —
    # which is what "design adapts to the age" has to mean in practice.
    if ctx.grade_tier == "senior" and "magazine" in order:
        order.remove("magazine")
        order.insert(1 if ctx.image_path else 0, "magazine")
    elif ctx.grade_tier == "junior":
        for name in ("magazine",):
            if name in order:
                order.remove(name)

    for name in order:
        fn = _LAYOUTS.get(name)
        if fn is None:
            continue
        try:
            if fn(ctx, sd):
                return name
        except Exception:
            # A layout that fails mid-draw may have left partial shapes;
            # the caller still has its own path, and a slide with one
            # stray rule on it beats a failed export.
            continue
    return None


def grade_tier(grade) -> str:
    """1-4 junior, 5-9 middle, 10-11 senior. `grade` arrives as "8",
    "8 класс", "8-синф" — the first run of digits decides."""
    m = re.search(r"\d+", str(grade or ""))
    if not m:
        return "middle"
    try:
        n = int(m.group())
    except ValueError:
        return "middle"
    if n <= 4:
        return "junior"
    return "senior" if n >= 10 else "middle"
