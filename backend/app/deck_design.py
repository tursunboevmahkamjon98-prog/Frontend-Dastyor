"""Subject design families for presentation decks.

Each school subject gets its own look — palette, type, background texture,
cover composition — instead of one layout recoloured per subject. A
family is chosen from the subject template id; the slide body layouts in
slide_layouts.py stay shared and only take the family's colours.

Fonts are ones every Windows/Office install has (Segoe UI, Georgia,
Consolas), so a downloaded .pptx looks right on a teacher's computer.
subject_templates.safe_font still swaps them for Tajik decks where a
font lacks ӣ ӯ ҳ ҷ қ ғ.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from app import pptx_shapes

SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5


def _rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _tuple(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


@dataclass(frozen=True)
class Design:
    family: str
    bg: str
    ink: str
    muted: str
    accent: str
    accent_dark: str      # text drawn on accent_soft fills
    accent_soft: str      # card and panel fills
    on_accent: str        # text drawn on solid accent
    hairline: str
    title_font: str = "Segoe UI"
    body_font: str = "Segoe UI"
    label_font: str = "Segoe UI"
    pattern: str = "none"
    pattern_color: str = "#E3EAF8"
    dark: bool = False
    title_caps_label: bool = True


DESIGNS: dict[str, Design] = {
    "math": Design("math", bg="#FFFFFF", ink="#14213D", muted="#4A5878", accent="#2456C7",
                   accent_dark="#173A8A", accent_soft="#E4ECFB", on_accent="#FFFFFF",
                   hairline="#DCE4F4", pattern="grid", pattern_color="#E8EEF9"),
    "physics": Design("physics", bg="#0E1B2E", ink="#EAF0FA", muted="#B7C4DA", accent="#FF9B54",
                      accent_dark="#FFD2B3", accent_soft="#1B2C45", on_accent="#0E1B2E",
                      hairline="#2A4062", label_font="Consolas", pattern="grid",
                      pattern_color="#17283F", dark=True),
    "chemistry": Design("chemistry", bg="#F8F6FD", ink="#1E1633", muted="#574C70", accent="#6A2FC9",
                        accent_dark="#4A1F8F", accent_soft="#ECE5FA", on_accent="#FFFFFF",
                        hairline="#DED4F3", pattern="hex", pattern_color="#E6DDF7"),
    "biology": Design("biology", bg="#F1F7F1", ink="#14301F", muted="#3F5A49", accent="#1F7A55",
                      accent_dark="#14533A", accent_soft="#DCEEE1", on_accent="#FFFFFF",
                      hairline="#D2E4D6"),
    "geography": Design("geography", bg="#F6F1E6", ink="#1F2A2B", muted="#4E5A5B", accent="#0F6670",
                        accent_dark="#0A4A51", accent_soft="#E5EDE6", on_accent="#FFFFFF",
                        hairline="#E2D6BC", pattern="topo", pattern_color="#E8DDC6"),
    "history": Design("history", bg="#F4ECDD", ink="#2A1E14", muted="#6B5A48", accent="#7A1F2B",
                      accent_dark="#5A1520", accent_soft="#EADBC4", on_accent="#FFFFFF",
                      hairline="#CDBB9C", title_font="Georgia", body_font="Georgia",
                      label_font="Georgia"),
    "literature": Design("literature", bg="#241A2E", ink="#F5EEE3", muted="#BFB2C9", accent="#E2BE7E",
                         accent_dark="#F0D6A8", accent_soft="#33263F", on_accent="#241A2E",
                         hairline="#4A3B57", title_font="Georgia", label_font="Georgia", dark=True),
    "code": Design("code", bg="#15171C", ink="#E8EAF0", muted="#A9AEBC", accent="#5EE29A",
                   accent_dark="#9DF0C1", accent_soft="#1E2128", on_accent="#15171C",
                   hairline="#2E323C", title_font="Consolas", label_font="Consolas", dark=True),
    "primary": Design("primary", bg="#FFF5D6", ink="#2B2340", muted="#5A4E73", accent="#E8603C",
                      accent_dark="#A8380B", accent_soft="#FFE6C2", on_accent="#FFFFFF",
                      hairline="#F2DDA8", pattern="dots", title_caps_label=False),
    "general": Design("general", bg="#FFFFFF", ink="#1A1D24", muted="#5B6170", accent="#2456C7",
                      accent_dark="#173A8A", accent_soft="#E8EEFB", on_accent="#FFFFFF",
                      hairline="#E4E6EB"),
}

FAMILY_OF = {
    "mathematics": "math", "algebra": "math", "geometry": "math",
    "physics": "physics",
    "chemistry": "chemistry",
    "biology": "biology", "ecology": "biology",
    "geography": "geography",
    "history": "history", "history_world": "history", "social_studies": "history",
    "literature": "literature", "russian": "literature", "tajik": "literature", "english": "literature",
    "informatics": "code",
    "primary_school": "primary",
    "general": "general",
}


def for_theme(theme: dict, language: str | None) -> Design | None:
    family = FAMILY_OF.get(str(theme.get("subject_template") or ""))
    if not family:
        return None
    from dataclasses import replace
    from app.subject_templates import safe_font
    d = DESIGNS[family]
    return replace(d, title_font=safe_font(d.title_font, language),
                   body_font=safe_font(d.body_font, language),
                   label_font=safe_font(d.label_font, language))


# ---------------------------------------------------------------------
# drawing primitives
# ---------------------------------------------------------------------

def _shape(slide, kind, x, y, w, h, fill=None, line=None, lw=1.0, rotation=None):
    shp = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(max(w, 0.01)), Inches(max(h, 0.01)))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = _rgb(fill)
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.fill.solid()
        shp.line.fill.fore_color.rgb = _rgb(line)
        shp.line.width = Pt(lw)
    if rotation is not None:
        shp.rotation = rotation
    return pptx_shapes.flatten(shp)


def _text(slide, x, y, w, h, s, pt, color, font, bold=False, italic=False, align=PP_ALIGN.LEFT):
    from app.export_builder import _add_text
    tf = _add_text(slide, Inches(x), Inches(y), Inches(w), Inches(h), s, pt, bold,
                   _rgb(color), align, font_name=font)
    if italic:
        tf.paragraphs[0].font.italic = True
    return tf


def _poly(slide, pts, line=None, lw=1.0, fill=None, closed=False):
    ff = slide.shapes.build_freeform(Inches(pts[0][0]), Inches(pts[0][1]))
    ff.add_line_segments([(Inches(px), Inches(py)) for px, py in pts[1:]], close=closed)
    shp = ff.convert_to_shape()
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = _rgb(fill)
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.fill.solid()
        shp.line.fill.fore_color.rgb = _rgb(line)
        shp.line.width = Pt(lw)
    return shp


def _fit(s, width_in, sizes, max_h_in, leading=1.15):
    from app.export_builder import _estimate_pptx_lines
    for pt in sizes:
        h = _estimate_pptx_lines(s, width_in, pt) * pt * leading / 72.0
        if h <= max_h_in:
            return pt, h
    pt = sizes[-1]
    return pt, _estimate_pptx_lines(s, width_in, pt) * pt * leading / 72.0


def _chip_w(s, pt, pad=0.5):
    return len(s) * pt * 0.0078 + pad


# ---------------------------------------------------------------------
# backgrounds
# ---------------------------------------------------------------------

def paint_background(slide, d: Design, cover: bool = False) -> None:
    from app.export_builder import _set_slide_bg
    _set_slide_bg(slide, *_tuple(d.bg))
    if d.pattern == "grid":
        step = 0.42
        x = step
        while x < SLIDE_W_IN:
            _shape(slide, MSO_SHAPE.RECTANGLE, x, 0, 0.012, SLIDE_H_IN, d.pattern_color)
            x += step
        y = step
        while y < SLIDE_H_IN:
            _shape(slide, MSO_SHAPE.RECTANGLE, 0, y, SLIDE_W_IN, 0.012, d.pattern_color)
            y += step
    elif d.pattern == "hex":
        for cx, cy, s in ((12.4, 0.7, 0.9), (11.7, 1.45, 0.9), (0.6, 6.7, 0.8)):
            _shape(slide, MSO_SHAPE.HEXAGON, cx - s / 2, cy - s * 0.44, s, s * 0.88,
                   None, d.pattern_color, 1.5)
    elif d.pattern == "topo":
        for k in range(4):
            off = k * 0.45
            pts = [(x / 10.0, 7.6 - off - 0.9 * math.sin(x / 10.0 * 0.55 + k * 0.4)
                    - 0.5 * math.sin(x / 10.0 * 1.3)) for x in range(-5, 140, 5)]
            _poly(slide, pts, d.pattern_color, 1.5)
    elif d.pattern == "dots" and cover:
        _shape(slide, MSO_SHAPE.OVAL, 11.6, -1.2, 3.0, 3.0, "#FFE08A")
        _shape(slide, MSO_SHAPE.OVAL, -1.0, 6.3, 2.4, 2.4, "#BFE6FF")
        _shape(slide, MSO_SHAPE.STAR_5_POINT, 10.2, 0.9, 0.55, 0.55, "#FF8A65")
    elif d.pattern == "dots":
        _shape(slide, MSO_SHAPE.OVAL, 12.3, -0.6, 1.5, 1.5, "#FFE08A")
        _shape(slide, MSO_SHAPE.OVAL, -0.5, 6.9, 1.2, 1.2, "#BFE6FF")


# ---------------------------------------------------------------------
# content slide chrome
# ---------------------------------------------------------------------

def draw_header(slide, d: Design, index: int, kind_label: str, title: str) -> None:
    label = f"{index:02d}"
    if kind_label:
        label += f" · {kind_label.upper() if d.title_caps_label else kind_label}"
    if d.family == "code":
        label = f"> {label.lower()}"
    _text(slide, 0.9, 0.38, 9.5, 0.35, label, 12, d.accent, d.label_font, bold=True)
    pt, _ = _fit(title, 11.4, (32, 28, 25, 22), 0.75)
    _text(slide, 0.9, 0.66, 11.5, 0.8, title, pt, d.ink, d.title_font, bold=True)
    if d.family == "history":
        _shape(slide, MSO_SHAPE.RECTANGLE, 0.9, 1.42, 11.5, 0.02, d.ink)


def draw_footer(slide, d: Design, index: int, total: int) -> None:
    _shape(slide, MSO_SHAPE.RECTANGLE, 0.9, 7.08, 10.6, 0.04, d.hairline)
    frac = (index + 1) / max(total, 1)
    if frac > 0:
        _shape(slide, MSO_SHAPE.RECTANGLE, 0.9, 7.08, 10.6 * frac, 0.04, d.accent)
    _text(slide, 11.6, 6.9, 0.9, 0.35, f"{index + 1} / {total}", 11, d.muted, d.body_font,
          bold=True, align=PP_ALIGN.RIGHT)


# ---------------------------------------------------------------------
# covers
# ---------------------------------------------------------------------

def _meta(content: dict) -> tuple[str, str, str]:
    subject = str(content.get("subject") or "").strip()
    grade = str(content.get("grade") or "").strip()
    meta = " · ".join(p for p in (subject, grade) if p)
    return subject, grade, meta


def _title_block(slide, d, content, x, w, top, bottom, sizes=(60, 54, 48, 42, 36),
                 title_color=None, desc_color=None, desc_italic=False, desc_font=None):
    title = str(content.get("title") or "")
    desc = str(content.get("description") or "")
    # PowerPoint sets Segoe UI and Georgia at about 1.3x their size per line;
    # a tighter estimate let a three-line title run into the description.
    # Measured against 90% of the box: the estimator undercounts wide
    # glyphs (Tajik ҳ ҷ ӣ, bold caps), and an extra line here only costs
    # a little air, while one too few runs the title into the description.
    wide = {"Georgia": 0.78, "Times New Roman": 0.82, "Consolas": 0.8}.get(d.title_font, 0.9)
    tpt, th = _fit(title, w * wide, sizes, 3.0, 1.3)
    dpt, dh = (_fit(desc, w, (22, 20, 18), 1.4, 1.35) if desc else (0, 0.0))
    block = th + (0.3 + dh if desc else 0.0)
    y = top + max(0.0, (bottom - top - block) / 2)
    _text(slide, x, y, w, th + 0.3, title, tpt, title_color or d.ink, d.title_font, bold=True)
    if desc:
        _text(slide, x, y + th + 0.3, w, dh + 0.3, desc, dpt, desc_color or d.muted,
              desc_font or d.body_font, italic=desc_italic)
    return y + block


def _agenda_chips(slide, d, agenda, x, y, max_w, border, fill="#FFFFFF", pt=14, color=None):
    cx = x
    for item in agenda:
        s = item if len(item) <= 34 else item[:32].rstrip() + "…"
        w = _chip_w(s, pt, 0.45)
        if cx + w > x + max_w:
            break
        _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, cx, y, w, 0.46, fill, border, 1.25).adjustments[0] = 0.18
        _text(slide, cx + 0.05, y + 0.06, w - 0.1, 0.36, s, pt, color or d.muted, d.body_font,
              align=PP_ALIGN.CENTER)
        cx += w + 0.15


def _cover_math(slide, d, content, agenda):
    _, _, meta = _meta(content)
    label = meta.upper()
    w = _chip_w(label, 13, 0.6)
    _shape(slide, MSO_SHAPE.RECTANGLE, 0.95, 0.75, w, 0.44, d.accent)
    _text(slide, 0.95, 0.8, w, 0.36, label, 13, d.on_accent, d.label_font, bold=True, align=PP_ALIGN.CENTER)
    _title_block(slide, d, content, 0.95, 6.4, 1.5, 5.9)
    _agenda_chips(slide, d, agenda, 0.95, 6.35, 6.6, "#C9D6F2", "#FFFFFF")
    ox, oy = 10.25, 4.55
    _shape(slide, MSO_SHAPE.RECTANGLE, 7.9, oy - 0.02, 4.7, 0.04, d.ink)
    _shape(slide, MSO_SHAPE.RECTANGLE, ox - 0.02, 1.0, 0.04, 5.7, d.ink)
    k = 1.55
    pts = [(ox + dx / 20.0, 6.0 - k * (dx / 20.0) ** 2) for dx in range(-34, 35)]
    _poly(slide, pts, d.accent, 4.5)
    root = math.sqrt((6.0 - oy) / k)
    for rx in (ox - root, ox + root):
        _shape(slide, MSO_SHAPE.OVAL, rx - 0.13, oy - 0.13, 0.26, 0.26, "#F2A900", d.ink, 2)
    _text(slide, 12.35, oy + 0.05, 0.4, 0.4, "x", 22, d.ink, "Georgia", italic=True)
    _text(slide, ox + 0.12, 0.95, 0.4, 0.4, "y", 22, d.ink, "Georgia", italic=True)


def _cover_physics(slide, d, content, agenda):
    subject, grade, _ = _meta(content)
    label = " / ".join(p for p in (subject.upper(), grade.upper()) if p)
    _text(slide, 0.95, 0.75, 7, 0.4, label, 15, d.accent, d.label_font, bold=True)
    _title_block(slide, d, content, 0.95, 6.4, 1.4, 5.0)
    for j, item in enumerate(agenda[:3]):
        x = 0.95 + j * 2.2
        _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, 5.45, 2.05, 1.25, None, "#34507A", 1.5).adjustments[0] = 0.08
        _text(slide, x + 0.15, 5.52, 1.8, 0.45, f"{j + 1:02d}", 22, d.accent, d.label_font, bold=True)
        pt, _ = _fit(item, 1.8, (13, 12, 11), 0.6)
        _text(slide, x + 0.15, 5.98, 1.8, 0.65, item, pt, d.muted, d.body_font)
    cx, cy = 10.1, 3.75
    for rot in (0, 60, 120):
        _shape(slide, MSO_SHAPE.OVAL, cx - 2.0, cy - 0.72, 4.0, 1.44, None, d.ink, 2.25, rotation=rot)
    _shape(slide, MSO_SHAPE.OVAL, cx - 0.32, cy - 0.32, 0.64, 0.64, d.accent)
    for ex, ey in ((cx + 2.0, cy), (cx - 1.0, cy - 1.73 * 0.72 * 1.2), (cx - 1.0, cy + 1.25)):
        _shape(slide, MSO_SHAPE.OVAL, ex - 0.11, ey - 0.11, 0.22, 0.22, d.accent)


def _cover_chemistry(slide, d, content, agenda):
    subject, grade, _ = _meta(content)
    num = "".join(ch for ch in grade if ch.isdigit()) or "·"
    symbol = (subject[:2] or "Х").capitalize()
    _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, 0.95, 0.7, 0.95, 1.1, d.accent).adjustments[0] = 0.1
    _text(slide, 1.05, 0.74, 0.8, 0.3, num, 12, d.on_accent, d.body_font, bold=True)
    _text(slide, 0.95, 1.0, 0.95, 0.6, symbol, 28, d.on_accent, d.title_font, bold=True, align=PP_ALIGN.CENTER)
    _title_block(slide, d, content, 0.95, 6.6, 1.9, 6.0)
    _agenda_chips(slide, d, agenda, 0.95, 6.4, 6.8, "#D9CCF5", "#FFFFFF")
    cx, cy = 10.2, 3.6
    for ax, ay in ((cx - 1.45, cy + 1.3), (cx + 1.45, cy + 1.3)):
        _poly(slide, [(cx, cy), (ax, ay)], d.ink, 9)
    _shape(slide, MSO_SHAPE.OVAL, cx - 1.0, cy - 1.0, 2.0, 2.0, d.accent)
    _text(slide, cx - 1.0, cy - 0.45, 2.0, 0.9, "O", 48, d.on_accent, d.title_font, bold=True, align=PP_ALIGN.CENTER)
    for ax, ay in ((cx - 1.45, cy + 1.3), (cx + 1.45, cy + 1.3)):
        _shape(slide, MSO_SHAPE.OVAL, ax - 0.6, ay - 0.6, 1.2, 1.2, "#FFFFFF", d.ink, 4)
        _text(slide, ax - 0.6, ay - 0.32, 1.2, 0.7, "H", 34, d.ink, d.title_font, bold=True, align=PP_ALIGN.CENTER)


_IN_LESSON = {"Таджикский": "Дар дарс", "English": "In this lesson", "Английский": "In this lesson"}


def _cover_biology(slide, d, content, agenda):
    _, _, meta = _meta(content)
    w = _chip_w(meta, 16, 0.7)
    _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, 0.95, 0.75, w, 0.5, "#FFFFFF").adjustments[0] = 0.5
    _text(slide, 0.95, 0.82, w, 0.4, meta, 16, d.accent, d.body_font, bold=True, align=PP_ALIGN.CENTER)
    _title_block(slide, d, content, 0.95, 6.2, 1.5, 5.9)
    if agenda:
        label = _IN_LESSON.get(str(content.get("language") or ""), "В уроке")
        line = f"{label}: " + " · ".join(agenda[:3])
        pt, _ = _fit(line, 6.4, (15, 14, 13), 0.5)
        _text(slide, 0.95, 6.4, 6.4, 0.5, line, pt, d.muted, d.body_font)
    _shape(slide, MSO_SHAPE.OVAL, 7.7, 1.2, 4.9, 4.4, "#DDEFE2", d.accent, 4)
    _shape(slide, MSO_SHAPE.OVAL, 9.75, 2.35, 1.5, 1.4, "#B9DEC6", d.accent, 3)
    _shape(slide, MSO_SHAPE.OVAL, 10.4, 2.7, 0.5, 0.5, d.accent)
    _shape(slide, MSO_SHAPE.OVAL, 8.4, 4.0, 1.3, 0.6, "#F5C26B", "#8A5A00", 2, rotation=-25)
    for rx, ry in ((11.3, 4.2), (11.6, 4.5), (11.1, 4.6), (9.0, 2.0), (9.3, 1.8)):
        _shape(slide, MSO_SHAPE.OVAL, rx, ry, 0.15, 0.15, d.ink)


def _band(cx, cy, r, f1, f2, steps=24):
    y1, y2 = cy + f1 * r, cy + f2 * r
    right = [(cx + math.sqrt(max(r * r - (y - cy) ** 2, 0)), y)
             for y in (y1 + (y2 - y1) * s / steps for s in range(steps + 1))]
    left = [(2 * cx - px, py) for px, py in reversed(right)]
    return right + left


def _cover_geography(slide, d, content, agenda):
    _, _, meta = _meta(content)
    _text(slide, 0.95, 0.72, 7, 0.4, meta.upper(), 15, d.accent, d.label_font, bold=True)
    _shape(slide, MSO_SHAPE.RECTANGLE, 0.95, 1.14, _chip_w(meta.upper(), 15, 0.0), 0.03, d.accent)
    _title_block(slide, d, content, 0.95, 6.2, 1.5, 5.9)
    _agenda_chips(slide, d, agenda, 0.95, 6.35, 6.4, "#D8CBAE", "#FFFFFF")
    cx, cy, r = 10.15, 3.75, 2.55
    for f1, f2, col in ((-1, -0.55, "#CFE6F2"), (-0.55, -0.28, "#7FB77E"), (-0.28, 0.28, "#C2410C"),
                        (0.28, 0.55, "#7FB77E"), (0.55, 1, "#CFE6F2")):
        _poly(slide, _band(cx, cy, r, f1, f2), fill=col, closed=True)
    _shape(slide, MSO_SHAPE.OVAL, cx - 1.05, cy - r, 2.1, 2 * r, None, "#FFFFFF", 1.5)
    _shape(slide, MSO_SHAPE.OVAL, cx - r, cy - r, 2 * r, 2 * r, None, d.ink, 3)
    _shape(slide, MSO_SHAPE.RECTANGLE, cx - r - 0.3, cy - 0.01, 2 * r + 0.6, 0.025, d.ink)


def _cover_history(slide, d, content, agenda):
    subject, grade, _ = _meta(content)
    _text(slide, 0.95, 0.55, 8, 0.4, subject.upper(), 15, d.ink, d.label_font, bold=True)
    _text(slide, 8.4, 0.55, 4.0, 0.4, grade, 17, d.muted, d.label_font, italic=True, align=PP_ALIGN.RIGHT)
    _shape(slide, MSO_SHAPE.RECTANGLE, 0.95, 1.05, 11.45, 0.03, d.ink)
    _title_block(slide, d, content, 0.95, 9.5, 1.3, 4.6, sizes=(64, 56, 48, 42),
                 title_color=d.accent)
    items = agenda[:4]
    if items:
        _shape(slide, MSO_SHAPE.RECTANGLE, 0.95, 5.3, 11.45, 0.05, d.ink)
        col = 11.45 / len(items)
        numerals = ("I", "II", "III", "IV")
        for j, item in enumerate(items):
            x = 0.95 + j * col
            _shape(slide, MSO_SHAPE.OVAL, x, 5.18, 0.3, 0.3, d.accent, d.bg, 2.5)
            _text(slide, x, 5.5, col - 0.2, 0.55, numerals[j], 28, d.accent, d.title_font, bold=True)
            pt, _ = _fit(item, col - 0.3, (16, 15, 14), 0.8)
            _text(slide, x, 6.05, col - 0.3, 0.9, item, pt, d.ink, d.body_font)


def _cover_literature(slide, d, content, agenda):
    _, _, meta = _meta(content)
    _text(slide, 0.95, 0.7, 6.5, 0.5, meta, 22, d.accent, d.label_font, italic=True)
    _title_block(slide, d, content, 0.95, 6.4, 1.4, 6.0, sizes=(66, 58, 50, 44),
                 desc_color=d.accent, desc_italic=True, desc_font=d.title_font)
    _shape(slide, MSO_SHAPE.RECTANGLE, 0.95, 6.55, 0.6, 0.02, d.accent)
    y = 1.3
    for item in agenda[:4]:
        pt, h = _fit(item, 4.2, (20, 18, 16), 0.8, 1.2)
        box_h = max(0.95, h + 0.45)
        _shape(slide, MSO_SHAPE.RECTANGLE, 8.0, y, 4.6, box_h, None, "#5B4A69", 1)
        _text(slide, 8.2, y + (box_h - h) / 2 - 0.05, 4.2, h + 0.2, item, pt, d.ink, d.title_font)
        y += box_h + 0.2


def _cover_code(slide, d, content, agenda):
    subject, grade, _ = _meta(content)
    prompt = f"> {subject.lower()}" + (f" --{grade.lower().replace(' ', '-')}" if grade else "")
    _text(slide, 0.95, 0.75, 6.5, 0.4, prompt, 15, d.accent, d.label_font, bold=True)
    _title_block(slide, d, content, 0.95, 6.0, 1.4, 6.6, sizes=(50, 44, 38, 32))
    x, y, w = 7.4, 1.4, 5.25
    lines = agenda[:5] or ["…"]
    h = 0.62 + 0.5 * len(lines) + 0.3
    _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, "#1E2128", "#2E323C", 1).adjustments[0] = 0.04
    for k in range(3):
        _shape(slide, MSO_SHAPE.OVAL, x + 0.22 + k * 0.24, y + 0.2, 0.14, 0.14, "#3A3F4B")
    _text(slide, x + 1.05, y + 0.1, 3, 0.35, "урок.py", 12, d.muted, d.label_font)
    _shape(slide, MSO_SHAPE.RECTANGLE, x, y + 0.52, w, 0.015, "#2E323C")
    for j, item in enumerate(lines):
        ly = y + 0.7 + j * 0.5
        _text(slide, x + 0.2, ly, 0.4, 0.4, str(j + 1), 14, "#5B6170", d.label_font)
        s = item if len(item) <= 30 else item[:28].rstrip() + "…"
        _text(slide, x + 0.6, ly, w - 0.8, 0.4, "# " + s, 15, "#8FD3A9" if j % 2 == 0 else d.ink, d.label_font)


def _cover_primary(slide, d, content, agenda):
    subject, grade, _ = _meta(content)
    x = 0.95
    if subject:
        w = _chip_w(subject, 18, 0.8)
        _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, 0.7, w, 0.58, "#FF8A65").adjustments[0] = 0.5
        _text(slide, x, 0.78, w, 0.45, subject, 18, d.ink, d.title_font, bold=True, align=PP_ALIGN.CENTER)
        x += w + 0.2
    if grade:
        w = _chip_w(grade, 18, 0.8)
        _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, 0.7, w, 0.58, "#FFFFFF", d.ink, 2.5).adjustments[0] = 0.5
        _text(slide, x, 0.78, w, 0.45, grade, 18, d.ink, d.title_font, bold=True, align=PP_ALIGN.CENTER)
    _title_block(slide, d, content, 0.95, 9.0, 1.5, 5.8, sizes=(72, 64, 56, 48))
    cx = 0.95
    palette = ("#FF8A65", "#4FA8E0", "#7CCB7A")
    for j, item in enumerate(agenda[:3]):
        s = f"{j + 1}. " + (item if len(item) <= 26 else item[:24].rstrip() + "…")
        w = _chip_w(s, 17, 0.6)
        if cx + w > 12.4:
            break
        _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, cx, 6.25, w, 0.6, "#FFFFFF", palette[j], 3).adjustments[0] = 0.4
        _text(slide, cx, 6.33, w, 0.45, s, 17, d.ink, d.title_font, bold=True, align=PP_ALIGN.CENTER)
        cx += w + 0.2


def _cover_general(slide, d, content, agenda):
    _, _, meta = _meta(content)
    w = _chip_w(meta, 15, 0.7)
    _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, 0.95, 0.8, w, 0.48, d.accent_soft).adjustments[0] = 0.5
    _text(slide, 0.95, 0.86, w, 0.4, meta, 15, d.accent, d.body_font, bold=True, align=PP_ALIGN.CENTER)
    _title_block(slide, d, content, 0.95, 6.4, 1.5, 6.4)
    _shape(slide, MSO_SHAPE.RECTANGLE, 7.75, 0, SLIDE_W_IN - 7.75, SLIDE_H_IN, d.accent)
    y = 1.4
    for j, item in enumerate(agenda[:5]):
        _text(slide, 8.3, y, 0.7, 0.5, f"{j + 1:02d}", 20, d.accent_soft, d.title_font, bold=True)
        pt, h = _fit(item, 4.0, (20, 18, 16), 0.9, 1.2)
        _text(slide, 9.0, y, 4.0, h + 0.2, item, pt, d.on_accent, d.body_font)
        y += max(0.75, h + 0.35)


_COVERS = {
    "math": _cover_math, "physics": _cover_physics, "chemistry": _cover_chemistry,
    "biology": _cover_biology, "geography": _cover_geography, "history": _cover_history,
    "literature": _cover_literature, "code": _cover_code, "primary": _cover_primary,
    "general": _cover_general,
}


def draw_cover(slide, d: Design, content: dict, agenda: list[str]) -> None:
    paint_background(slide, d, cover=True)
    _COVERS.get(d.family, _cover_general)(slide, d, content, [a for a in agenda if a])
