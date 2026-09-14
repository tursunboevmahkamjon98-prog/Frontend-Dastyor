"""Generates a decorative cover page for konspekt PDF exports — a purely
graphic/typographic design (no emoji, no photo — teacher explicitly asked
for the cover to stay abstract rather than an emoji/picture, after trying
both), the lesson title, a grade badge, and fill-in-the-blank fields
(name/class/school), matching the look of a professionally printed
methodological guide. Rendered once as a PNG (via PIL) and dropped in as a
genuine full-bleed first page — PDF only, by design (see export_builder.py's
build_konspekt_pdf); the docx export does not get one.

Which of the 5 designs below gets used is picked per-konspekt via
`template_id` (see app/konspekt_templates.py) — a teacher-facing wizard
choice, a DIFFERENT axis from subject. This is deliberately NOT
per-subject variation (that was tried before and reverted — the teacher
asked for one uniform look per document, matching a fixed reference —
each of these 5 designs stays that same "one fixed look", just 5 different
fixed looks to choose from instead of 1)."""

import io
import os
import re
from datetime import date
from PIL import Image, ImageDraw, ImageFont

_FONT_DIR = r"C:\Windows\Fonts"
_FONT_REGULAR = os.path.join(_FONT_DIR, "segoeui.ttf")
_FONT_BOLD = os.path.join(_FONT_DIR, "segoeuib.ttf")
# Serif alternative for "minimal"/"rasmiy" — Times New Roman ships with
# every Windows install, same reasoning as export_builder.py reusing
# Cambria for its own serif needs (a real font file, not a new
# dependency). Georgia was tried here first but is missing glyphs for
# Tajik-specific Cyrillic letters (ӯ/ҳ/ҷ/ӣ) — confirmed live: renders
# tofu boxes for e.g. "Омӯзгор"/"Соли таҳсилӣ", silently breaking any
# Tajik-language rasmiy/minimal cover. Times New Roman has full coverage.
_FONT_SERIF = os.path.join(_FONT_DIR, "times.ttf")
_FONT_SERIF_BOLD = os.path.join(_FONT_DIR, "timesbd.ttf")

_DARK = (0x11, 0x2A, 0x5E)
_LIGHT = (0x2E, 0x63, 0xC7)

# Per-subject cover illustration — deliberately a small, explicit dict
# rather than a generic "any subject" mechanism: only add a subject here
# once an actual image has been sourced/cleaned for it, not as a
# placeholder. Two modes:
#  - "cutout": background already removed (real transparency) — pasted
#    directly, floating on the white cover, no border.
#  - "framed": a real photo that keeps its own background (a lab photo,
#    an old map, a bokeh library shot) — these look wrong cut out (messy
#    edges, or the background IS the point, e.g. the dark studio shot for
#    Физика/Биология), so they're drawn inside a bordered rounded-rect
#    card instead, like a framed photograph on the page.
_ILLUS_DIR = os.path.join(os.path.dirname(__file__), "static", "subject_illustrations")
_SUBJECT_ILLUSTRATIONS = {
    "Информатика": ("cutout", os.path.join(_ILLUS_DIR, "informatika_pc.png")),
    "Технология": ("cutout", os.path.join(_ILLUS_DIR, "informatika_pc.png")),
    "Математика": ("cutout", os.path.join(_ILLUS_DIR, "math_calculator.png")),
    "Алгебра": ("cutout", os.path.join(_ILLUS_DIR, "algebra_glyph.png")),
    "Геометрия": ("cutout", os.path.join(_ILLUS_DIR, "geometry_star.png")),
    "География": ("cutout", os.path.join(_ILLUS_DIR, "geography_earth.png")),
    "Физика": ("cutout", os.path.join(_ILLUS_DIR, "physics_atom.png")),
    "Химия": ("cutout", os.path.join(_ILLUS_DIR, "chemistry_beaker.png")),
    "Биология": ("cutout", os.path.join(_ILLUS_DIR, "biology_microscope.png")),
    "Русский язык": ("cutout", os.path.join(_ILLUS_DIR, "russian_owl.png")),
    "Английский язык": ("cutout", os.path.join(_ILLUS_DIR, "english_books.png")),
    "Таджикский язык": ("cutout", os.path.join(_ILLUS_DIR, "tajik_flag.png")),
    "Таджикская литература": ("cutout", os.path.join(_ILLUS_DIR, "tajik_lit_book.png")),
    "История Таджикистана": ("cutout", os.path.join(_ILLUS_DIR, "tajik_history_map.png")),
    "Всемирная история": ("cutout", os.path.join(_ILLUS_DIR, "history_world_map.png")),
}

_LABELS = {
    "Русский": {"name": "Имя ученика", "class": "Класс", "school": "Школа", "subject": "Предмет", "year_prefix": "Учебный год", "teacher": "Учитель", "tag": "КОНСПЕКТ УРОКА"},
    "Таджикский": {"name": "Номи хонанда", "class": "Синф", "school": "Мактаб", "subject": "Фан", "year_prefix": "Соли таҳсилӣ", "teacher": "Омӯзгор", "tag": "НАҚШАИ ТАВЗЕҲОТӢ"},
    "English": {"name": "Student Name", "class": "Grade", "school": "School", "subject": "Subject", "year_prefix": "Academic Year", "teacher": "Teacher", "tag": "LESSON PLAN"},
}
# Wording specific to the "nakscha" cover — it is not a title plus fields
# like the other five, it is three running sentences ("for grade 10",
# "in the subject X", "for academic year Y"), so it needs the connecting
# words too, not just nouns.
_NAKSCHA_LABELS = {
    "Таджикский": {"grade": "барои синфи", "duration": "Давомнокии дарс: 1 соат",
                   "subject": "аз фанни", "year": "барои соли таҳсили",
                   "teacher": "Омӯзгор", "topic": "Мавзӯи дарс"},
    "Русский": {"grade": "для", "duration": "Длительность урока: 1 час",
                "subject": "по предмету", "year": "на учебный год",
                "teacher": "Учитель", "topic": "Тема урока"},
    "English": {"grade": "for grade", "duration": "Lesson duration: 1 hour",
                "subject": "in", "year": "for the academic year",
                "teacher": "Teacher", "topic": "Lesson topic"},
}
_NAKSCHA_LABELS["Английский"] = _NAKSCHA_LABELS["English"]

_LABELS["Английский"] = _LABELS["English"]

_W, _H = 1240, 1754  # A4 at ~150dpi


def _academic_year() -> str:
    today = date.today()
    start = today.year if today.month >= 8 else today.year - 1
    return f"{start}-{start + 1}"


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for w in words:
        trial = f"{current} {w}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def _grade_number(grade: str) -> str:
    """"8 класс" -> "8" — the CIRCULAR grade badges (klassik, rangli) size
    their font for a short number; the full phrase overflowed the circle
    and got clipped at the edges. A round badge reads as a number icon
    anyway, not a sentence, so trimming to the leading digits (falling
    back to the original string if there aren't any) is the fix, not a
    bigger circle."""
    m = re.match(r'\s*(\d+)', str(grade))
    return m.group(1) if m else str(grade)


def _draw_ornamental_border(draw, W, H, margin=44, step=26,
                             colors=((0xC9, 0x9A, 0x2E), (0x1F, 0x29, 0x37))):
    """Repeating diamond motif band around the page edge, alternating two
    colors — the specific ornamental-border look a real official Tajik
    curriculum document ("Нақшаи тавзеҳотӣ") uses, which is what "rasmiy"
    (Official) is meant to evoke; a plain double-rule frame read as
    generic instead. Diamonds are drawn edge-to-edge so the 4 corners
    naturally line up without extra corner-piece logic."""
    size = step * 0.42

    def diamond(cx, cy, fill):
        draw.polygon([(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)], fill=fill)

    i = 0
    x = margin
    while x <= W - margin:
        color = colors[i % 2]
        diamond(x, margin, color)
        diamond(x, H - margin, color)
        x += step
        i += 1
    i = 0
    y = margin
    while y <= H - margin:
        color = colors[i % 2]
        diamond(margin, y, color)
        diamond(W - margin, y, color)
        y += step
        i += 1


def _watermark(draw, color=(255, 255, 255, 200)):
    wm_font = _font(_FONT_REGULAR, 20)
    draw.text((100, _H - 50), "Dastyor — AI-помощник для учителей", font=wm_font, fill=color)


# ── "klassik" — the original design, unchanged ──────────────────────────

def _build_cover_klassik(subject: str, title: str, grade: str, language: str) -> bytes:
    W, H = _W, _H
    dark, light = _DARK, _LIGHT
    L = _LABELS.get(language, _LABELS["Русский"])

    img = Image.new("RGB", (W, H), dark)
    draw = ImageDraw.Draw(img)

    # Diagonal gradient background (top-left dark -> bottom-right light).
    for y in range(H):
        t = y / H
        r = int(dark[0] + (light[0] - dark[0]) * t)
        g = int(dark[1] + (light[1] - dark[1]) * t)
        b = int(dark[2] + (light[2] - dark[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Purely abstract/geometric decoration — a cluster of large, layered
    # translucent rings (not filled disks) anchored top-right, plus a thin
    # diagonal line accent bottom-left.
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    ring_cx, ring_cy = W - 120, 260
    for i, (radius, width, alpha) in enumerate([(560, 3, 30), (430, 3, 40), (300, 4, 55), (180, 5, 70)]):
        odraw.ellipse(
            [ring_cx - radius, ring_cy - radius, ring_cx + radius, ring_cy + radius],
            outline=(255, 255, 255, alpha), width=width,
        )
    odraw.ellipse([-260, H - 360, 220, H + 220], fill=(255, 255, 255, 14))
    for i in range(6):
        x = -40 + i * 70
        odraw.line([(x, H - 40), (x + 160, H - 200)], fill=(255, 255, 255, 22), width=2)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    year_font = _font(_FONT_BOLD, 22)
    year_text = f"{L['year_prefix'].upper()}  {_academic_year()}"
    tw = draw.textlength(year_text, font=year_font)
    draw.text((W - 70 - tw, 60), year_text, font=year_font, fill=(255, 255, 255))

    top_y = 220
    subj_font = _font(_FONT_BOLD, 26)
    subj_text = subject.upper()
    stw = draw.textlength(subj_text, font=subj_font)
    pill_pad = 22
    draw.rounded_rectangle([100, top_y, 100 + stw + pill_pad * 2, top_y + 56], radius=28, fill=(255, 255, 255))
    draw.text((100 + pill_pad, top_y + 12), subj_text, font=subj_font, fill=dark)

    title_font = _font(_FONT_BOLD, 64)
    lines = _wrap_text(draw, title, title_font, W - 220)[:5]
    ty = top_y + 96
    for line in lines:
        draw.text((100, ty), line, font=title_font, fill=(255, 255, 255))
        ty += 78

    ty += 18
    draw.line([(100, ty), (260, ty)], fill=(255, 255, 255, 220), width=6)

    field_font = _font(_FONT_REGULAR, 28)
    fy = H - 400
    for label in (L["name"], L["class"], L["school"]):
        draw.text((100, fy), f"{label}:", font=field_font, fill=(255, 255, 255))
        line_x0 = 100 + draw.textlength(f"{label}:  ", font=field_font)
        draw.line([(line_x0, fy + 34), (W - 340, fy + 34)], fill=(255, 255, 255, 180), width=2)
        fy += 70

    if grade:
        gb_cx, gb_cy, gb_r = W - 190, H - 200, 95
        draw.ellipse([gb_cx - gb_r - 14, gb_cy - gb_r - 14, gb_cx + gb_r + 14, gb_cy + gb_r + 14], outline=(255, 255, 255, 130), width=3)
        draw.ellipse([gb_cx - gb_r, gb_cy - gb_r, gb_cx + gb_r, gb_cy + gb_r], fill=(255, 255, 255))
        grade_font = _font(_FONT_BOLD, 64)
        gtext = _grade_number(grade)
        gbbox = draw.textbbox((0, 0), gtext, font=grade_font)
        gw, gh = gbbox[2] - gbbox[0], gbbox[3] - gbbox[1]
        draw.text((gb_cx - gw / 2 - gbbox[0], gb_cy - gh / 2 - gbbox[1]), gtext, font=grade_font, fill=dark)

    _watermark(draw)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ── "zamonaviy" (Modern) — off-center title, bold flat shapes ───────────

_MODERN_INK = (0x1E, 0x29, 0x37)
_MODERN_ACCENT = (0x3B, 0x82, 0xF6)  # same blue family as the presentation redesign
_MODERN_MUTED = (0x64, 0x74, 0x8B)
_MODERN_HAIRLINE = (0xE2, 0xE8, 0xF0)


def _tint(color: tuple, amount: float = 0.9) -> tuple:
    """Blend `color` toward white by `amount` (0 = unchanged, 1 = white) —
    used for the cover's soft background blobs below."""
    r, g, b = color
    return (int(r + (255 - r) * amount), int(g + (255 - g) * amount), int(b + (255 - b) * amount))


def _build_cover_zamonaviy(subject: str, title: str, grade: str, language: str, doc_type_label: str | None = None) -> bytes:
    """White background, bold dark title, thin blue rule, small accent
    corner badge — the konspekt cover redone to match the presentation
    export's redesigned look (see build_presentation_pptx's cover slide),
    after direct feedback that a konspekt exported next to a presentation
    on the same topic should read as the same product. Was a dark-navy +
    coral/teal design before; every other one of the 5 covers is
    untouched, still available for curriculum's own separate template
    picker.

    Two soft accent-tinted circles (top-right, bottom-left) were added
    later — a teacher found the plain white page "too empty"/plain, but
    an earlier attempt at fixing that with an ornamental pattern border
    was rejected outright as too busy/heavy ("juda hunuk"). Soft flat-
    tinted blobs are the middle ground: they fill the dead space and add
    depth without any hard edges/pattern repetition to read as "busy" —
    the same "gradient hero + soft shapes" language the mobile app's own
    login screen already uses, so the cover reads as the same product."""
    W, H = _W, _H
    L = _LABELS.get(language, _LABELS["Русский"])
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.ellipse([W - 520, -260, W + 260, 480], fill=_tint(_MODERN_ACCENT, 0.90))
    draw.ellipse([-320, H - 640, 340, H + 260], fill=_tint(_MODERN_ACCENT, 0.94))

    # Thin rule + small-caps label, top-left — same "ПРЕЗЕНТАЦИЯ" kicker
    # idiom the pptx cover uses, just labeled for a konspekt instead.
    label_font = _font(_FONT_BOLD, 20)
    draw.rectangle([100, 118, 160, 122], fill=_MODERN_ACCENT)
    label_text = doc_type_label or {"Русский": "КОНСПЕКТ", "Таджикский": "КОНСПЕКТ", "English": "LESSON NOTES"}.get(language, "КОНСПЕКТ")
    draw.text((180, 104), label_text, font=label_font, fill=_MODERN_ACCENT)

    # Small accent badge, top-right — grade number + academic year,
    # mirroring the pptx cover's "N СЛАЙДОВ / Dastyor" corner card.
    badge_w, badge_h = 230, 150
    badge_x0, badge_y0 = W - badge_w - 100, 80
    draw.rounded_rectangle([badge_x0, badge_y0, badge_x0 + badge_w, badge_y0 + badge_h], radius=18, fill=_MODERN_ACCENT)
    if grade:
        grade_font = _font(_FONT_BOLD, 44)
        gtext = f"{_grade_number(grade)} {L['class'].upper()}"
        gbbox = draw.textbbox((0, 0), gtext, font=grade_font)
        gw = gbbox[2] - gbbox[0]
        draw.text((badge_x0 + (badge_w - gw) / 2 - gbbox[0], badge_y0 + 22), gtext, font=grade_font, fill=(255, 255, 255))
    year_font = _font(_FONT_REGULAR, 18)
    year_text = _academic_year()
    ybbox = draw.textbbox((0, 0), year_text, font=year_font)
    yw = ybbox[2] - ybbox[0]
    draw.text((badge_x0 + (badge_w - yw) / 2 - ybbox[0], badge_y0 + 92), year_text, font=year_font, fill=(255, 255, 255))

    subj_font = _font(_FONT_BOLD, 26)
    draw.text((100, 340), subject.upper(), font=subj_font, fill=_MODERN_ACCENT)

    title_font = _font(_FONT_BOLD, 62)
    lines = _wrap_text(draw, title, title_font, W - 260)[:5]
    ty = 420
    for line in lines:
        draw.text((100, ty), line, font=title_font, fill=_MODERN_INK)
        ty += 78
    ty += 16
    draw.rectangle([100, ty, 190, ty + 8], fill=_MODERN_ACCENT)

    # Subject illustration, centered in the empty space between the title
    # rule and the name/class/school fields — only for subjects with an
    # actual supplied image (see _SUBJECT_ILLUSTRATIONS); every other
    # subject's cover is unchanged.
    entry = _SUBJECT_ILLUSTRATIONS.get(subject)
    if entry and os.path.exists(entry[1]):
        mode, illus_path = entry
        try:
            illus = Image.open(illus_path).convert("RGBA")
            area_top, area_bottom = ty + 50, H - 500
            pad = 36
            max_w, max_h = W - 240 - pad * 2, max(0, area_bottom - area_top) - pad * 2
            iw, ih = illus.size
            scale = min(max_w / iw, max_h / ih, 1.0)
            tw, th = int(iw * scale), int(ih * scale)
            if tw > 0 and th > 0:
                illus = illus.resize((tw, th), Image.LANCZOS)
                px = (W - tw) // 2
                py = area_top + pad + (max_h - th) // 2
                # A white card behind the illustration, always (used to be
                # "framed" photos only) — now that the page has soft
                # colored background blobs, an image floating directly on
                # top of the tint read as messy; a plain white card
                # underneath keeps it crisp either way, cutout or framed.
                draw.rounded_rectangle(
                    [px - pad, py - pad, px + tw + pad, py + th + pad],
                    radius=20, fill=(255, 255, 255), outline=_MODERN_HAIRLINE, width=2,
                )
                img.paste(illus, (px, py), illus)
        except Exception:
            pass  # a missing/corrupt illustration file should never break the cover

    # No "student name" fill-in line — this cover is one printed sheet a
    # teacher photocopies for a whole class, not a per-student handout, so
    # a blank name field on it never made sense (direct feedback: "Номи
    # хонанда... buni olib tashla").
    field_font = _font(_FONT_REGULAR, 26)
    fy = H - 460
    for label in (L["class"], L["school"]):
        draw.text((100, fy), f"{label}:", font=field_font, fill=_MODERN_INK)
        line_x0 = 100 + draw.textlength(f"{label}:  ", font=field_font)
        draw.line([(line_x0, fy + 32), (W - 340, fy + 32)], fill=_MODERN_HAIRLINE, width=2)
        fy += 62

    draw.line([(100, H - 130), (W - 100, H - 130)], fill=_MODERN_HAIRLINE, width=2)
    _watermark(draw, color=_MODERN_MUTED)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ── "minimal" — plain background, centered serif title, one thin rule ───

_MINIMAL_BG = (0xFA, 0xFA, 0xF9)
_MINIMAL_INK = (0x1F, 0x29, 0x37)
_MINIMAL_MUTED = (0x6B, 0x72, 0x80)


def _build_cover_minimal(subject: str, title: str, grade: str, language: str) -> bytes:
    W, H = _W, _H
    L = _LABELS.get(language, _LABELS["Русский"])
    img = Image.new("RGB", (W, H), _MINIMAL_BG)
    draw = ImageDraw.Draw(img)

    subj_font = _font(_FONT_REGULAR, 24)
    subj_text = subject.upper()
    stw = draw.textlength(subj_text, font=subj_font)
    draw.text(((W - stw) / 2, 220), subj_text, font=subj_font, fill=_MINIMAL_MUTED)

    title_font = _font(_FONT_SERIF_BOLD, 58)
    lines = _wrap_text(draw, title, title_font, W - 320)[:5]
    ty = 300
    for line in lines:
        lw = draw.textlength(line, font=title_font)
        draw.text(((W - lw) / 2, ty), line, font=title_font, fill=_MINIMAL_INK)
        ty += 76

    ty += 24
    draw.line([(W / 2 - 60, ty), (W / 2 + 60, ty)], fill=_MINIMAL_INK, width=2)

    field_font = _font(_FONT_SERIF, 26)
    fy = H - 420
    for label in (L["name"], L["class"], L["school"]):
        draw.text((W / 2 - 260, fy), f"{label}:", font=field_font, fill=_MINIMAL_INK)
        line_x0 = W / 2 - 260 + draw.textlength(f"{label}:  ", font=field_font)
        draw.line([(line_x0, fy + 32), (W / 2 + 260, fy + 32)], fill=(0xCB, 0xD5, 0xE1), width=2)
        fy += 66

    if grade:
        gtext = f"{grade}"
        grade_font = _font(_FONT_SERIF_BOLD, 30)
        gw = draw.textlength(gtext, font=grade_font)
        gy = H - 160
        draw.text(((W - gw) / 2, gy), gtext, font=grade_font, fill=_MINIMAL_INK)

    year_font = _font(_FONT_REGULAR, 18)
    year_text = f"{L['year_prefix']}  {_academic_year()}"
    ytw = draw.textlength(year_text, font=year_font)
    draw.text(((W - ytw) / 2, H - 90), year_text, font=year_font, fill=_MINIMAL_MUTED)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ── "rasmiy" (Formal/Academic) — centered, institutional, thin frame ────

_FORMAL_BG = (0xFF, 0xFF, 0xFF)
_FORMAL_INK = (0x1F, 0x29, 0x37)
_FORMAL_MUTED = (0x47, 0x55, 0x69)
_FORMAL_ACCENT = (0x8A, 0x26, 0x35)  # muted maroon


def _build_cover_rasmiy(subject: str, title: str, grade: str, language: str) -> bytes:
    W, H = _W, _H
    L = _LABELS.get(language, _LABELS["Русский"])
    img = Image.new("RGB", (W, H), _FORMAL_BG)
    draw = ImageDraw.Draw(img)

    # Ornamental diamond-motif border (see _draw_ornamental_border) — real
    # official Tajik curriculum documents ("Нақшаи тавзеҳотӣ") use exactly
    # this kind of repeating pattern band; a plain double-rule frame read
    # as generic rather than "official" (confirmed against a real printed
    # reference). A thin plain rule just inside it keeps the page content
    # visually separated from the pattern itself.
    margin = 60
    _draw_ornamental_border(draw, W, H, margin=margin)
    inner = margin + 22
    draw.rectangle([inner, inner, W - inner, H - inner], outline=(0xCB, 0xD5, 0xE1), width=1)

    tag_font = _font(_FONT_SERIF_BOLD, 26)
    tag_text = L["tag"]
    ttw = draw.textlength(tag_text, font=tag_font)
    draw.text(((W - ttw) / 2, 220), tag_text, font=tag_font, fill=_FORMAL_ACCENT)

    subj_font = _font(_FONT_SERIF_BOLD, 24)
    subj_text = subject.upper()
    stw = draw.textlength(subj_text, font=subj_font)
    draw.text(((W - stw) / 2, 270), subj_text, font=subj_font, fill=_FORMAL_MUTED)

    title_font = _font(_FONT_SERIF_BOLD, 52)
    lines = _wrap_text(draw, title, title_font, W - 400)[:5]
    ty = 400
    for line in lines:
        lw = draw.textlength(line, font=title_font)
        draw.text(((W - lw) / 2, ty), line, font=title_font, fill=_FORMAL_INK)
        ty += 68

    ty += 20
    draw.line([(W / 2 - 90, ty), (W / 2 + 90, ty)], fill=_FORMAL_ACCENT, width=2)

    # Subject illustration, centered in the empty space between the title
    # rule and the teacher/class/school fields — same asset/scaling logic
    # as _build_cover_zamonaviy (see that function's matching comment);
    # a teacher directly asked for this template to include a picture too,
    # matching a real official document's own cover having one.
    entry = _SUBJECT_ILLUSTRATIONS.get(subject)
    if entry and os.path.exists(entry[1]):
        mode, illus_path = entry
        try:
            illus = Image.open(illus_path).convert("RGBA")
            area_top, area_bottom = ty + 40, H - 500
            pad = 28 if mode == "framed" else 0
            max_w, max_h = W - 400 - pad * 2, max(0, area_bottom - area_top) - pad * 2
            iw, ih = illus.size
            scale = min(max_w / iw, max_h / ih, 1.0)
            tw, th = int(iw * scale), int(ih * scale)
            if tw > 0 and th > 0:
                illus = illus.resize((tw, th), Image.LANCZOS)
                px = (W - tw) // 2
                py = area_top + pad + (max_h - th) // 2
                if mode == "framed":
                    draw.rounded_rectangle(
                        [px - pad, py - pad, px + tw + pad, py + th + pad],
                        radius=14, fill=(255, 255, 255), outline=(0xCB, 0xD5, 0xE1), width=2,
                    )
                img.paste(illus, (px, py), illus)
        except Exception:
            pass  # a missing/corrupt illustration file should never break the cover

    # "Teacher" first and most prominent — matches the real reference
    # document's own sole blank field (this is the teacher's own lesson
    # plan, not a student handout); class/school kept below it since
    # they're still genuinely useful on a printed cover.
    field_font = _font(_FONT_SERIF, 26)
    fy = H - 460
    for label in (L["teacher"], L["class"], L["school"]):
        draw.text((W / 2 - 260, fy), f"{label}:", font=field_font, fill=_FORMAL_INK)
        line_x0 = W / 2 - 260 + draw.textlength(f"{label}:  ", font=field_font)
        draw.line([(line_x0, fy + 32), (W / 2 + 260, fy + 32)], fill=(0xCB, 0xD5, 0xE1), width=2)
        fy += 66

    if grade:
        gtext = f"{L['class']}: {grade}"
        grade_font = _font(_FONT_SERIF_BOLD, 24)
        gw = draw.textlength(gtext, font=grade_font)
        draw.text(((W - gw) / 2, H - 200), gtext, font=grade_font, fill=_FORMAL_ACCENT)

    year_font = _font(_FONT_SERIF, 18)
    year_text = f"{L['year_prefix']}  {_academic_year()}"
    ytw = draw.textlength(year_text, font=year_font)
    draw.text(((W - ytw) / 2, H - 100), year_text, font=year_font, fill=_FORMAL_MUTED)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ── "nakscha" — 1:1 with the printed Нақшаи тавзеҳотӣ binder cover ─────
#
# Rebuilt from a photograph of the real document a teacher supplied. Every
# choice here is copied from that sheet rather than designed: the red/blue
# split (heading red, the "which subject, which year, which teacher" block
# blue), the two-line heading, the bracketed term line, the handwriting
# rule after "Омӯзгор", and the subject picture sitting in the lower third.
# It is deliberately NOT consistent with the other five covers — matching
# the original is the whole point.

_NAK_RED = (0xC4, 0x1E, 0x1E)
_NAK_BLUE = (0x1C, 0x3F, 0x94)
_NAK_GOLD = (0xC9, 0x8A, 0x2E)


# A few faint marks in the outer margins, chosen per subject. The brief
# asked for decoration that belongs in a school textbook rather than
# ornament for its own sake: these are the symbols the subject itself
# uses, set very light and kept out in the margins where no text runs, so
# they read as a watermark of what the folder is about.
# Every glyph here is checked against the cover's own font (Times New
# Roman Bold) — the obvious picks for several subjects (△ ∠ ≅ for
# geometry, ✿ for biology, ★ ❖ for history) are simply not in it and drew
# as empty boxes, which is worse than no decoration at all.
_COVER_MOTIFS = {
    "Математика": "+−×÷=",
    "Алгебра": "xy√π=",
    "Геометрия": "○□·∙°",
    "Физика": "F=ma·v",
    "Химия": "H₂O+=",
    "Биология": "○·∙~°",
    "География": "○·~≈°",
    "Информатика": "01{}<>",
    "История Таджикистана": "§¶·◦",
    "Всемирная история": "§¶·◦",
    "Русский язык": "Аа·Бб",
    "Английский язык": "Aa·Bb",
    "Таджикский язык": "Аа·Ҳҳ",
    "Таджикская литература": "«»·§",
}
_NAK_MOTIF_INK = (0xE8, 0xD6, 0xB0)      # pale gold, barely there


def _nakscha_motifs(draw, W, H, subject: str):
    """Scatters the subject's own symbols down both margins, faintly."""
    glyphs = _COVER_MOTIFS.get(subject) or "•◦·"
    font = _font(_FONT_SERIF_BOLD, 44)
    spots = [(78, 470), (W - 116, 620), (78, 900), (W - 116, 1050),
             (78, 1290), (W - 116, 1400)]
    for i, (x, y) in enumerate(spots):
        draw.text((x, y), glyphs[i % len(glyphs)], font=font, fill=_NAK_MOTIF_INK)


def _build_cover_nakscha(subject: str, title: str, grade: str, language: str) -> bytes:
    """The Нақшаи тавзеҳотӣ cover, redrawn as a modern textbook title page.

    What changed from the 1:1 copy of the photographed original, and why:

      * the double gold ornamental border is gone. It was the loudest
        thing on the page and dated the sheet by about forty years; a
        teacher asked for the page to read as a current textbook instead.
        Two hairlines — one under the top meta row, one above the foot —
        do the framing job without boxing the page in;
      * the text block starts lower. With the border removed the old
        y=330 heading left the top looking unfinished; the block now sits
        in the upper-middle of the page with air above it;
      * the bracketed term line ("нимсолаи 1") is replaced by the lesson
        duration in the top meta row. One konspekt is one lesson of one
        hour, so a half-year marker was simply the wrong unit;
      * the decoration is a short accent rule under the heading, three
        dots under the class line, and the subject's own symbols set very
        pale in the margins.
    """
    W, H = _W, _H
    L = _LABELS.get(language, _LABELS["Таджикский"])
    N = _NAKSCHA_LABELS.get(language, _NAKSCHA_LABELS["Таджикский"])
    img = Image.new("RGB", (W, H), (0xFF, 0xFF, 0xFF))
    draw = ImageDraw.Draw(img)

    margin = 150
    hair = (0xD9, 0xC9, 0xA6)

    def centered(text, font, y, fill):
        draw.text(((W - draw.textlength(text, font=font)) / 2, y), text, font=font, fill=fill)

    # ── top meta row: what year, and how long the lesson runs ──────────
    meta_font = _font(_FONT_SERIF_BOLD, 34)
    meta_ink = (0x6B, 0x72, 0x80)
    draw.text((margin, 120), f'{L["year_prefix"]} {_academic_year()}', font=meta_font, fill=meta_ink)
    duration = N["duration"]
    draw.text((W - margin - draw.textlength(duration, font=meta_font), 120),
              duration, font=meta_font, fill=_NAK_BLUE)
    draw.line([(margin, 182), (W - margin, 182)], fill=hair, width=2)

    # No scattered subject glyphs. Set faintly down both margins they did
    # not read as decoration — "0", "1", "{", "}" adrift near the edges of
    # an official form look like a rendering fault, and a teacher handing
    # the sheet in cannot tell the difference.

    # ── heading, one word per line, sitting lower than it used to ──────
    head_font = _font(_FONT_SERIF_BOLD, 96)
    y = 430
    for word in L["tag"].split():
        centered(word, head_font, y, _NAK_RED)
        y += 108

    # Short accent rule under the heading — the one piece of ornament the
    # page keeps, and it earns its place by anchoring the title block.
    y += 22
    draw.line([((W - 240) / 2, y), ((W + 240) / 2, y)], fill=_NAK_GOLD, width=5)
    y += 46

    centered(f'{N["grade"]} {_grade_number(grade)}', _font(_FONT_SERIF_BOLD, 62), y, _NAK_RED)
    y += 92

    # Three dots instead of the old bracketed term line: it separates the
    # red title block from the blue detail block without adding a word.
    dot_r, gap = 5, 26
    cx = W / 2
    for k in (-1, 0, 1):
        draw.ellipse([cx + k * gap - dot_r, y - dot_r, cx + k * gap + dot_r, y + dot_r],
                     fill=_NAK_GOLD)
    y += 56

    # `subject` is always the Russian internal key (see
    # export_builder._display_subject's doc comment for why) — most
    # subjects are the same loanword in Tajik, but a few (Информатика,
    # the language/literature/history names) are not, and printing them
    # untranslated on an otherwise fully-Tajik/English cover reads as a
    # mistake. Local import: cover_builder has no other dependency on
    # export_builder, and export_builder already imports the other
    # direction (see _academic_year usages above), so importing back here
    # at module scope would be circular.
    from app.export_builder import _display_subject
    subj_font = _font(_FONT_SERIF_BOLD, 44)
    for line in _wrap_text(draw, f'{N["subject"]} {_display_subject(subject, language).lower()}', subj_font, W - 400)[:2]:
        centered(line, subj_font, y, _NAK_BLUE)
        y += 60
    centered(f'{N["year"]} {_academic_year()}', subj_font, y, _NAK_BLUE)
    y += 78

    # The lesson's own topic. It was missing entirely: the cover said
    # which class and which subject, and never which LESSON — a plan
    # sheet handed in without its topic is not a plan sheet, and it is
    # the first thing anyone reads.
    topic = str(title or "").strip()
    if topic:
        draw.line([((W - 300) / 2, y - 22), ((W + 300) / 2, y - 22)],
                  fill=hair, width=2)
        y += 16
        centered(N["topic"], _font(_FONT_SERIF, 34), y, meta_ink)
        y += 48
        topic_font = _font(_FONT_SERIF_BOLD, 56)
        for line in _wrap_text(draw, topic, topic_font, W - 320)[:3]:
            centered(line, topic_font, y, _NAK_INK if "_NAK_INK" in globals() else (0x15, 0x1A, 0x22))
            y += 68
        y += 26

    # "Омӯзгор ______" — a rule to write on, exactly as the teacher on the
    # original filled it in by hand.
    teach_font = _font(_FONT_SERIF_BOLD, 44)
    label = N["teacher"]
    lw = draw.textlength(label + " ", font=teach_font)
    rule_w = 420
    x0 = (W - (lw + rule_w)) / 2
    draw.text((x0, y), label, font=teach_font, fill=_NAK_BLUE)
    draw.line([(x0 + lw, y + 54), (x0 + lw + rule_w, y + 54)], fill=_NAK_BLUE, width=3)
    y += 96

    # ── foot hairline, closing the page without enclosing it ───────────
    foot_y = H - 150
    draw.line([(margin, foot_y), (W - margin, foot_y)], fill=hair, width=2)
    diamond = 9
    draw.polygon([(W / 2, foot_y - diamond), (W / 2 + diamond, foot_y),
                  (W / 2, foot_y + diamond), (W / 2 - diamond, foot_y)], fill=_NAK_GOLD)

    # Subject picture between the teacher rule and the foot line — same
    # asset set and fit logic as the other covers use.
    entry = _SUBJECT_ILLUSTRATIONS.get(subject)
    if entry and os.path.exists(entry[1]):
        try:
            illus = Image.open(entry[1]).convert("RGBA")
            top = y + 70
            max_w, max_h = W - 430, max(0, (foot_y - 90) - top)
            iw, ih = illus.size
            scale = min(max_w / iw, max_h / ih, 1.0)
            tw, th = int(iw * scale), int(ih * scale)
            if tw > 0 and th > 0:
                illus = illus.resize((tw, th), Image.LANCZOS)
                img.paste(illus, ((W - tw) // 2, top), illus)
        except Exception:
            pass  # a missing/corrupt illustration must never break the cover

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ── "rangli" (Colorful/Playful) — bold color blocks, big grade numeral ──

_PLAYFUL_BLOCKS = [(0xF5, 0x9E, 0x0B), (0x10, 0xB9, 0x81), (0xEC, 0x48, 0x99)]  # amber, green, pink
_PLAYFUL_INK = (0x1F, 0x29, 0x37)


def _build_cover_rangli(subject: str, title: str, grade: str, language: str) -> bytes:
    W, H = _W, _H
    L = _LABELS.get(language, _LABELS["Русский"])
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Three bold flat color blocks — a thick top bar split into three
    # equal color segments, plus one corner triangle bottom-left — the
    # liveliest of the 5 covers, aimed at younger grades.
    bar_h = 90
    seg_w = W / 3
    for i, color in enumerate(_PLAYFUL_BLOCKS):
        draw.rectangle([i * seg_w, 0, (i + 1) * seg_w, bar_h], fill=color)
    draw.polygon([(0, H), (0, H - 340), (340, H)], fill=_PLAYFUL_BLOCKS[1])

    subj_font = _font(_FONT_BOLD, 26)
    subj_text = subject.upper()
    pill_w = draw.textlength(subj_text, font=subj_font) + 44
    draw.rounded_rectangle([100, bar_h + 60, 100 + pill_w, bar_h + 116], radius=28, fill=_PLAYFUL_BLOCKS[0])
    draw.text((122, bar_h + 76), subj_text, font=subj_font, fill=(255, 255, 255))

    title_font = _font(_FONT_BOLD, 62)
    lines = _wrap_text(draw, title, title_font, W - 220)[:5]
    ty = bar_h + 200
    for line in lines:
        draw.text((100, ty), line, font=title_font, fill=_PLAYFUL_INK)
        ty += 78

    field_font = _font(_FONT_REGULAR, 27)
    fy = H - 380
    for i, label in enumerate((L["name"], L["class"], L["school"])):
        draw.ellipse([100, fy + 6, 116, fy + 22], fill=_PLAYFUL_BLOCKS[i % len(_PLAYFUL_BLOCKS)])
        draw.text((132, fy), f"{label}:", font=field_font, fill=_PLAYFUL_INK)
        line_x0 = 132 + draw.textlength(f"{label}:  ", font=field_font)
        draw.line([(line_x0, fy + 32), (W - 380, fy + 32)], fill=(0xCB, 0xD5, 0xE1), width=2)
        fy += 66

    if grade:
        gb_cx, gb_cy, gb_r = W - 220, H - 220, 110
        draw.ellipse([gb_cx - gb_r, gb_cy - gb_r, gb_cx + gb_r, gb_cy + gb_r], fill=_PLAYFUL_BLOCKS[2])
        grade_font = _font(_FONT_BOLD, 72)
        gtext = _grade_number(grade)
        gbbox = draw.textbbox((0, 0), gtext, font=grade_font)
        gw, gh = gbbox[2] - gbbox[0], gbbox[3] - gbbox[1]
        draw.text((gb_cx - gw / 2 - gbbox[0], gb_cy - gh / 2 - gbbox[1]), gtext, font=grade_font, fill=(255, 255, 255))

    year_font = _font(_FONT_BOLD, 18)
    year_text = f"{L['year_prefix'].upper()}  {_academic_year()}"
    draw.text((100, H - 60), year_text, font=year_font, fill=_PLAYFUL_INK)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# The "playful" cover's own pastel set — a different palette from
# _PLAYFUL_BLOCKS' vivid amber/green/pink (that one is "rangli"'s loud
# flat-color-block look), matching instead the soft blue/green/lavender/
# pink/yellow rotation the presentation's own "playful" pptx theme uses
# (see export_builder.py's _PLAYFUL_PALETTE) — the same deck built from
# the same reference photo, so a teacher's konspekt and presentation on
# the same lesson read as one visual family.
_NOTEBOOK_PALETTE = [(0xBF, 0xDB, 0xFE), (0xBB, 0xF7, 0xD0), (0xDD, 0xD6, 0xFE),
                     (0xFB, 0xCF, 0xE8), (0xFD, 0xE6, 0x8A)]
_NOTEBOOK_DARK = [(0x1D, 0x4E, 0xD8), (0x15, 0x80, 0x3D), (0x6D, 0x28, 0xD9),
                  (0xBE, 0x18, 0x5D), (0x92, 0x6B, 0x00)]
_NOTEBOOK_PAPER = (0xFF, 0xFD, 0xF7)


def _notebook_background(draw, W, H) -> None:
    """Faint ruled lines + a spiral-hole left margin — the same "real
    notebook paper" texture as the presentation's pptx cover/slides (see
    export_builder.py's _pptx_notebook_lines/_pptx_spiral_margin),
    reimplemented here in PIL's coordinate system (pixels, not inches) so
    the konspekt cover carries the identical visual identity."""
    for y in range(70, H - 40, 46):
        draw.line([(0, y), (W, y)], fill=(0xEE, 0xE4, 0xC8), width=2)
    hole_x = 38
    for y in range(48, H - 20, 78):
        draw.ellipse([hole_x - 12, y - 12, hole_x + 12, y + 12], fill=_NOTEBOOK_PAPER, outline=(0xD8, 0xD2, 0xC4), width=2)
    draw.line([(78, 20), (78, H - 20)], fill=(0xF3, 0xC6, 0xC6), width=3)


def _sticker_cluster(img, x: int, y: int) -> None:
    """A small tilted "sticker" cluster — a stack of books and a heart —
    built from plain PIL polygons/ellipses at a slight, alternating skew,
    echoing the two Canva-sticker reference photos sent directly (a real
    hand-drawn illustration asset isn't achievable here — no image-
    generation capability, and fetching a matching public clipart image
    proved too unreliable over this environment's network to depend on;
    see export_builder.py's _pptx_sticker_decorations, which documents
    the same tradeoff for the presentation's own cover). Takes the real
    Image (not just its Draw wrapper) since each tilted book is composed
    on its own small canvas and pasted in, which needs the Image itself."""
    book_w, book_h = 210, 46
    for i, color in enumerate(_NOTEBOOK_PALETTE[:3]):
        skew = (-6, 3, -3)[i]
        by = y + i * (book_h - 6)
        bw = book_w - i * 18
        book_img = Image.new("RGBA", (bw, book_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(book_img)
        d.rounded_rectangle([0, 0, bw - 1, book_h - 1], radius=10, fill=color, outline=(255, 255, 255), width=3)
        rotated = book_img.rotate(skew, expand=True, resample=Image.BICUBIC)
        img.paste(rotated, (x, int(by)), rotated)
    draw = ImageDraw.Draw(img)
    heart_cx, heart_cy = x + book_w + 60, y - 10
    r = 26
    draw.polygon([
        (heart_cx, heart_cy + r * 0.9),
        (heart_cx - r, heart_cy - r * 0.2),
        (heart_cx - r * 0.5, heart_cy - r * 0.9),
        (heart_cx, heart_cy - r * 0.35),
        (heart_cx + r * 0.5, heart_cy - r * 0.9),
        (heart_cx + r, heart_cy - r * 0.2),
    ], fill=(0xFB, 0x71, 0x85))


def _build_cover_playful(subject: str, title: str, grade: str, language: str) -> bytes:
    W, H = _W, _H
    L = _LABELS.get(language, _LABELS["Русский"])
    img = Image.new("RGB", (W, H), _NOTEBOOK_PAPER)
    draw = ImageDraw.Draw(img)
    _notebook_background(draw, W, H)

    left_x = 150
    subj_font = _font(_FONT_BOLD, 24)
    subj_text = subject.upper()
    pill_w = draw.textlength(subj_text, font=subj_font) + 48
    draw.rounded_rectangle([left_x, 130, left_x + pill_w, 186], radius=28,
                            fill=_NOTEBOOK_PALETTE[0], outline=_NOTEBOOK_DARK[0], width=2)
    draw.text((left_x + 24, 148), subj_text, font=subj_font, fill=_NOTEBOOK_DARK[0])

    # Deliberately _FONT_BOLD (Segoe UI), not Comic Sans MS Bold as first
    # tried here — confirmed live: Comic Sans has no glyphs for Tajik-
    # specific Cyrillic letters (ҳ/ӯ/ҷ/ӣ), rendering them as tofu boxes in
    # the title. Same failure mode already documented above for Georgia
    # (see _FONT_SERIF's comment) — Segoe UI Bold is the one proven-safe
    # bold face for Tajik in this whole file, so the "playful" title stays
    # legible over being maximally handwritten.
    title_font = _font(_FONT_BOLD, 56)
    lines = _wrap_text(draw, title, title_font, W - left_x - 220)[:5]
    ty = 260
    for line in lines:
        draw.text((left_x, ty), line, font=title_font, fill=_PLAYFUL_INK)
        ty += 74
    draw.line([(left_x, ty + 8), (left_x + 130, ty + 8)], fill=_NOTEBOOK_DARK[3], width=5)

    _sticker_cluster(img, left_x, ty + 90)

    field_font = _font(_FONT_REGULAR, 27)
    fy = H - 380
    for i, label in enumerate((L["name"], L["class"], L["school"])):
        draw.ellipse([left_x, fy + 6, left_x + 16, fy + 22], fill=_NOTEBOOK_PALETTE[i % len(_NOTEBOOK_PALETTE)],
                     outline=_NOTEBOOK_DARK[i % len(_NOTEBOOK_DARK)], width=2)
        draw.text((left_x + 32, fy), f"{label}:", font=field_font, fill=_PLAYFUL_INK)
        line_x0 = left_x + 32 + draw.textlength(f"{label}:  ", font=field_font)
        draw.line([(line_x0, fy + 32), (W - 340, fy + 32)], fill=(0xCB, 0xD5, 0xE1), width=2)
        fy += 66

    if grade:
        gb_cx, gb_cy, gb_r = W - 220, H - 220, 105
        draw.ellipse([gb_cx - gb_r, gb_cy - gb_r, gb_cx + gb_r, gb_cy + gb_r],
                     fill=_NOTEBOOK_PALETTE[2], outline=_NOTEBOOK_DARK[2], width=4)
        grade_font = _font(_FONT_BOLD, 68)
        gtext = _grade_number(grade)
        gbbox = draw.textbbox((0, 0), gtext, font=grade_font)
        gw, gh = gbbox[2] - gbbox[0], gbbox[3] - gbbox[1]
        draw.text((gb_cx - gw / 2 - gbbox[0], gb_cy - gh / 2 - gbbox[1]), gtext, font=grade_font, fill=_NOTEBOOK_DARK[2])

    year_font = _font(_FONT_BOLD, 18)
    year_text = f"{L['year_prefix'].upper()}  {_academic_year()}"
    draw.text((left_x, H - 60), year_text, font=year_font, fill=_PLAYFUL_INK)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


_COVER_BUILDERS = {
    "klassik": _build_cover_klassik,
    "zamonaviy": _build_cover_zamonaviy,
    "minimal": _build_cover_minimal,
    "rasmiy": _build_cover_rasmiy,
    "nakscha": _build_cover_nakscha,
    "rangli": _build_cover_rangli,
    "playful": _build_cover_playful,
}


def build_cover_image(
    subject: str, title: str, grade: str, language: str = "Русский",
    image_path: str | None = None, show_subject_icon: bool = False,
    template_id: str | None = None, doc_type_label: str | None = None,
) -> bytes:
    """image_path/show_subject_icon are accepted-but-unused — kept so
    existing call sites don't need to change; every one of the 5 designs
    below is deliberately abstract/typographic only, no photo and no
    emoji icon (same constraint that applied to the original single
    design). `template_id` picks which of the 5 (see
    app/konspekt_templates.py) — an unrecognized/missing id falls back to
    "klassik", the original design, so old call sites/data are unaffected.
    `doc_type_label` overrides the "КОНСПЕКТ" kicker text — only
    "zamonaviy" (the one template konspekt/lecture actually use now)
    accepts it, so build_lecture_pdf can get a "ЛЕКЦИЯ" cover from this
    exact same cover without touching the other 4 (still curriculum's)."""
    builder = _COVER_BUILDERS.get(template_id, _build_cover_klassik)
    if builder is _build_cover_zamonaviy:
        return builder(subject, title, grade, language, doc_type_label=doc_type_label)
    return builder(subject, title, grade, language)
