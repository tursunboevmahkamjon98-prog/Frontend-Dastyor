# -*- coding: utf-8 -*-
"""The лекция as a finished teaching document.

A lecture used to be rendered by the konspekt's body renderer with a
different masthead bolted on: the same numbered sections, the same
bullets, the same wall of prose. It read as generated text, because
structurally it WAS the same document wearing another hat.

This module gives the лекция its own build:

    cover page  ->  contents  ->  numbered sections with sub-headings,
    definitions, worked callouts, figures and tables  ->  self-check
    ->  conclusions  ->  sources

and four genuinely different designs to print it in (see
lecture_templates.py). Everything visual is dispatched through the five
tables at the bottom of this file — _COVERS, _HEADINGS, _CALLOUTS,
_TABLES, _DEFINITIONS — so a design is a set of five small functions
rather than a copy of the builder.
"""
import io
import re

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, KeepTogether,
                                NextPageTemplate, PageBreak, PageTemplate, Spacer,
                                Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from app.export_builder import (CODE_FONT, FONT_NAME, FONT_NAME_BOLD, MATH_FONT,
                                MATH_FONT_BOLD, Paragraph, _bare_grade,
                                _format_grade, _pdf_formula_flowable,
                                _pdf_illustration_image, _pdf_light_tint_hex,
                                _pdf_visual_block, _plain_to_latex)
from app.lecture_templates import get_lecture_template
from app.subject_theme import get_subject_accent_hex
from app.cover_builder import _academic_year
from app.logger import get_logger

logger = get_logger(__name__)

INK = '#151A22'
INK_SOFT = '#4A5462'
RULE = '#D5DBE4'
PAPER_SOFT = '#F6F8FA'


# ── words ───────────────────────────────────────────────────────────────
# Everything the document says in its own voice. A lecture is handed to
# real students, so its furniture is written in the language the lecture
# is in — never Russian chrome around Tajik content.
L10N = {
    'Русский': {
        'tag': 'ЛЕКЦИЯ', 'contents': 'Содержание', 'objective': 'Цель лекции',
        'plan': 'План лекции', 'concepts': 'Ключевые понятия',
        'terms': 'Словарь урока', 'body': 'Содержание лекции',
        'formulas': 'Формулы и правила', 'selfcheck': 'Вопросы для самопроверки',
        'summary': 'Выводы', 'references': 'Литература',
        'important': 'ВАЖНО', 'remember': 'ЗАПОМНИ', 'example': 'ПРИМЕР',
        'tip': 'СОВЕТ', 'definition': 'ОПРЕДЕЛЕНИЕ',
        'answer': 'Ответ', 'grade_suffix': 'класс', 'subject': 'Предмет',
        'duration': 'Продолжительность', 'duration_value': '1 академический час',
        'year': 'Учебный год', 'teacher': 'Преподаватель', 'date': 'Дата',
        'name': 'Ф.И.О.', 'page': 'с.', 'figure': 'Рис.',
    },
    'Таджикский': {
        'tag': 'ЛЕКСИЯ', 'contents': 'Мундариҷа', 'objective': 'Мақсади лексия',
        'plan': 'Нақшаи лексия', 'concepts': 'Мафҳумҳои асосӣ',
        'terms': 'Луғати дарс', 'body': 'Мазмуни лексия',
        'formulas': 'Формулаҳо ва қоидаҳо', 'selfcheck': 'Саволҳо барои худсанҷӣ',
        'summary': 'Хулосаҳо', 'references': 'Адабиёт',
        'important': 'МУҲИМ', 'remember': 'ДАР ХОТИР ДОР', 'example': 'МИСОЛ',
        'tip': 'МАСЛИҲАТ', 'definition': 'ТАЪРИФ',
        'answer': 'Ҷавоб', 'grade_suffix': 'синф', 'subject': 'Фан',
        'duration': 'Давомнокӣ', 'duration_value': '1 соати академӣ',
        'year': 'Соли таҳсил', 'teacher': 'Муаллим', 'date': 'Сана',
        'name': 'Ном ва насаб', 'page': 'саҳ.', 'figure': 'Расми',
    },
    'English': {
        'tag': 'LECTURE', 'contents': 'Contents', 'objective': 'Objective',
        'plan': 'Lecture plan', 'concepts': 'Key concepts',
        'terms': 'Glossary', 'body': 'Lecture',
        'formulas': 'Formulas and rules', 'selfcheck': 'Self-check questions',
        'summary': 'Conclusions', 'references': 'References',
        'important': 'IMPORTANT', 'remember': 'REMEMBER', 'example': 'EXAMPLE',
        'tip': 'TIP', 'definition': 'DEFINITION',
        'answer': 'Answer', 'grade_suffix': 'grade', 'subject': 'Subject',
        'duration': 'Duration', 'duration_value': '1 academic hour',
        'year': 'Academic year', 'teacher': 'Teacher', 'date': 'Date',
        'name': 'Name', 'page': 'p.', 'figure': 'Fig.',
    },
}
L10N['Английский'] = L10N['English']


def _words(language: str) -> dict:
    return L10N.get(str(language or 'Русский'), L10N['Русский'])


# ── one place that knows the design ─────────────────────────────────────
class _Design:
    """The resolved look: template knobs + the accent + the fonts."""

    def __init__(self, template, accent_hex: str, words: dict):
        self.t = template
        self.words = words
        self.accent = accent_hex
        self.quiet = template.colour == 'quiet'
        # A quiet design still needs somewhere to spend the accent, or it
        # reads as a fax. It gets the rules and the labels; the fills stay
        # out of it.
        self.heading_ink = INK if self.quiet else accent_hex
        self.body_font = MATH_FONT if template.body_font == 'serif' else FONT_NAME
        self.body_bold = MATH_FONT_BOLD if template.body_font == 'serif' else FONT_NAME_BOLD
        self.head_font = MATH_FONT_BOLD if template.head_font == 'serif' else FONT_NAME_BOLD
        self.head_regular = MATH_FONT if template.head_font == 'serif' else FONT_NAME
        self.tint = _pdf_light_tint_hex(accent_hex, amount=0.93)
        self.tint_soft = _pdf_light_tint_hex(accent_hex, amount=0.965)
        self.width = A4[0] - 2 * template.margin_x * cm

    # styles used all over the body
    def body_style(self, name: str, **kw) -> ParagraphStyle:
        base = dict(fontName=self.body_font, fontSize=self.t.body_size,
                    leading=self.t.body_leading, textColor=HexColor(INK),
                    alignment=TA_JUSTIFY, spaceAfter=6)
        base.update(kw)
        return ParagraphStyle(name=name, **base)


_STYLE_SEQ = [0]


def _uid(prefix: str) -> str:
    _STYLE_SEQ[0] += 1
    return f'{prefix}{_STYLE_SEQ[0]}'


# ════════════════════════════════════════════════════════════════════════
# COVERS — drawn on the canvas, because a cover is composition, not flow
# ════════════════════════════════════════════════════════════════════════
def _cover_meta(content: dict, w: dict) -> list[tuple[str, str]]:
    rows = []
    if content.get('subject'):
        rows.append((w['subject'], str(content['subject'])))
    if content.get('grade'):
        grade = str(content['grade'])
        # _format_grade, not "leave it alone if it already has letters":
        # the create form ALWAYS sends the Russian "8 класс" whatever the
        # material's language is, so the old any(isalpha) test was true
        # every time and a Tajik lecture printed "8 класс" next to fully
        # translated labels. _format_grade strips whichever grade-word
        # arrived and re-suffixes with this document's own.
        rows.append((w['grade_suffix'].capitalize(),
                     _format_grade(grade, w['grade_suffix'])))
    duration_text = str(content.get('duration') or '').strip() or w.get('duration_value', '')
    rows.append((w['duration'], duration_text))
    rows.append((w['year'], _academic_year()))
    return rows


def _wrap_canvas_text(c, text: str, font: str, size: float, max_w: float) -> list[str]:
    words, lines, line = str(text or '').split(), [], ''
    for word in words:
        trial = (line + ' ' + word).strip()
        if c.stringWidth(trial, font, size) <= max_w or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _cover_classic(c, content, d: _Design):
    """A university title page: everything centred between two rules, the
    metadata in a block at the foot. No colour blocks at all — this is
    the design that has to survive a black-and-white classroom printer."""
    w, W, H = d.words, A4[0], A4[1]
    mx = d.t.margin_x * cm
    c.setFillColor(HexColor(INK_SOFT))
    c.setFont(FONT_NAME_BOLD, 9)
    c.drawCentredString(W / 2, H - 3.2 * cm,
                        '   '.join(w['tag']))
    c.setStrokeColor(HexColor(d.accent))
    c.setLineWidth(1.2)
    c.line(mx, H - 3.8 * cm, W - mx, H - 3.8 * cm)
    c.setLineWidth(0.5)
    c.line(mx, H - 3.95 * cm, W - mx, H - 3.95 * cm)

    title_lines = _wrap_canvas_text(c, content.get('title', ''), MATH_FONT_BOLD, 27, W - 2 * mx - 20)
    y = H / 2 + 2.6 * cm + (len(title_lines) - 1) * 0.5 * cm
    c.setFillColor(HexColor(INK))
    for line in title_lines[:4]:
        c.setFont(MATH_FONT_BOLD, 27)
        c.drawCentredString(W / 2, y, line)
        y -= 1.05 * cm

    if content.get('subtitle'):
        c.setFillColor(HexColor(INK_SOFT))
        for line in _wrap_canvas_text(c, content['subtitle'], MATH_FONT, 12, W - 2 * mx - 80)[:3]:
            c.setFont(MATH_FONT, 12)
            c.drawCentredString(W / 2, y - 0.3 * cm, line)
            y -= 0.62 * cm

    c.setStrokeColor(HexColor(RULE))
    c.setLineWidth(0.7)
    c.line(W / 2 - 2.2 * cm, y - 1.1 * cm, W / 2 + 2.2 * cm, y - 1.1 * cm)

    _cover_plan(c, content, d, W / 2 - 6.0 * cm, y - 2.6 * cm, 12.0 * cm,
                rule=True, numbers='padded', max_items=5)

    ty = 6.4 * cm
    for label, value in _cover_meta(content, w):
        c.setFont(FONT_NAME, 9.5)
        c.setFillColor(HexColor(INK_SOFT))
        c.drawRightString(W / 2 - 0.4 * cm, ty, f'{label}:')
        c.setFont(FONT_NAME_BOLD, 9.5)
        c.setFillColor(HexColor(INK))
        c.drawString(W / 2 + 0.4 * cm, ty, value)
        ty -= 0.72 * cm

    c.setFont(FONT_NAME, 8.5)
    c.setFillColor(HexColor('#9AA3AF'))
    c.drawCentredString(W / 2, 2.2 * cm, 'Dastyor')


def _cover_split(c, content, d: _Design):
    """A modern textbook cover: a full-height accent panel down the left
    third carrying the subject and the class, the title set large on the
    white right-hand side."""
    w, W, H = d.words, A4[0], A4[1]
    panel_w = 6.6 * cm
    c.setFillColor(HexColor(d.accent))
    c.rect(0, 0, panel_w, H, stroke=0, fill=1)
    c.setFillColor(HexColor(_pdf_light_tint_hex(d.accent, amount=0.55)))
    c.rect(panel_w - 0.35 * cm, 0, 0.35 * cm, H, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont(FONT_NAME_BOLD, 10)
    c.drawString(1.3 * cm, H - 3.0 * cm, '  '.join(w['tag']))
    c.setFont(MATH_FONT_BOLD, 46)
    # The bare number — this draws it at 46pt with the grade WORD printed
    # separately just below, so slicing the raw string ("8 класс"[:3] ->
    # "8 к") put a stray Russian letter inside the big numeral.
    c.drawString(1.3 * cm, H - 6.4 * cm, _bare_grade(str(content.get('grade') or ''))[:3])
    c.setFont(FONT_NAME, 10.5)
    for i, line in enumerate(_wrap_canvas_text(c, w['grade_suffix'], FONT_NAME, 10.5, panel_w - 2.6 * cm)):
        c.drawString(1.3 * cm, H - 7.1 * cm - i * 0.5 * cm, line)

    c.setFont(FONT_NAME_BOLD, 11)
    for i, line in enumerate(_wrap_canvas_text(c, str(content.get('subject') or ''),
                                               FONT_NAME_BOLD, 11, panel_w - 2.6 * cm)[:3]):
        c.drawString(1.3 * cm, 4.6 * cm - i * 0.55 * cm, line)
    c.setFont(FONT_NAME, 9)
    c.drawString(1.3 * cm, 3.2 * cm, _academic_year())
    c.drawString(1.3 * cm, 2.4 * cm, 'Dastyor')

    tx = panel_w + 1.5 * cm
    tw = W - tx - 1.8 * cm
    title_lines = _wrap_canvas_text(c, content.get('title', ''), FONT_NAME_BOLD, 30, tw)
    y = H / 2 + 3.4 * cm
    c.setFillColor(HexColor(INK))
    for line in title_lines[:5]:
        c.setFont(FONT_NAME_BOLD, 30)
        c.drawString(tx, y, line)
        y -= 1.15 * cm

    c.setFillColor(HexColor(d.accent))
    c.rect(tx, y - 0.2 * cm, 2.4 * cm, 3.2, stroke=0, fill=1)
    y -= 1.3 * cm
    if content.get('subtitle'):
        c.setFillColor(HexColor(INK_SOFT))
        for line in _wrap_canvas_text(c, content['subtitle'], FONT_NAME, 12, tw)[:5]:
            c.setFont(FONT_NAME, 12)
            c.drawString(tx, y, line)
            y -= 0.62 * cm

    # The plan, previewed on the cover — the teacher sees the shape of the
    # lesson before opening it. Starts just under the standfirst rather
    # than at a fixed height, so a short subtitle does not leave a band of
    # white across the middle of the page.
    _cover_plan(c, content, d, tx, min(y - 1.6 * cm, 11.0 * cm), tw, max_items=5)
    _cover_facts(c, content, d, tx, 3.4 * cm, tw,
                 str(content.get('language') or 'Русский'))


def _cover_banner(c, content, d: _Design):
    """Editorial: a deep accent banner across the top third with the title
    reversed out of it, the standfirst and the metadata below on white."""
    w, W, H = d.words, A4[0], A4[1]
    mx = d.t.margin_x * cm
    # The band is as deep as its own title needs. Fixed at 11.4cm it left
    # a slab of flat colour under a one-line title.
    _n_title = len(_wrap_canvas_text(c, content.get('title', ''), MATH_FONT_BOLD, 29, W - 2 * mx)[:4])
    band_h = 6.4 * cm + _n_title * 1.15 * cm
    c.setFillColor(HexColor(d.accent))
    c.rect(0, H - band_h, W, band_h, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont(FONT_NAME_BOLD, 9.5)
    c.drawString(mx, H - 2.2 * cm, '   '.join(w['tag']))
    c.setLineWidth(2)
    c.setStrokeColor(colors.white)
    c.line(mx, H - 2.6 * cm, mx + 1.8 * cm, H - 2.6 * cm)

    title_lines = _wrap_canvas_text(c, content.get('title', ''), MATH_FONT_BOLD, 29, W - 2 * mx)
    y = H - 4.3 * cm
    for line in title_lines[:4]:
        c.setFont(MATH_FONT_BOLD, 29)
        c.drawString(mx, y, line)
        y -= 1.15 * cm

    c.setFont(FONT_NAME, 10)
    meta = '   ·   '.join(f'{v}' for _, v in _cover_meta(content, w)[:2])
    c.drawString(mx, H - band_h + 1.0 * cm, meta)

    if content.get('subtitle'):
        c.setFillColor(HexColor(INK))
        y = H - band_h - 1.9 * cm
        for line in _wrap_canvas_text(c, content['subtitle'], MATH_FONT, 14, W - 2 * mx - 3 * cm)[:4]:
            c.setFont(MATH_FONT, 14)
            c.drawString(mx, y, line)
            y -= 0.75 * cm

    py = _cover_plan(c, content, d, mx, H - band_h - 4.2 * cm, W - 2 * mx,
                     rule=True, numbers='padded', max_items=6)

    # The aim, set as a standfirst under the plan — an editorial cover
    # carries a paragraph, and this is the paragraph the document is for.
    objective = str(content.get('objective') or '').strip()
    if objective:
        c.setFillColor(HexColor(d.accent))
        c.rect(mx, py - 1.5 * cm, 2.2 * cm, 2.5, stroke=0, fill=1)
        c.setFillColor(HexColor(INK_SOFT))
        oy = py - 2.4 * cm
        for line in _wrap_canvas_text(c, objective, MATH_FONT, 11, W - 2 * mx)[:5]:
            c.setFont(MATH_FONT, 11)
            c.drawString(mx, oy, line)
            oy -= 0.62 * cm

    _cover_facts(c, content, d, mx, 3.6 * cm, W - 2 * mx,
                 str(content.get('language') or 'Русский'))

    c.setFillColor(HexColor('#9AA3AF'))
    c.setFont(FONT_NAME, 8.5)
    c.drawString(mx, 1.9 * cm, 'Dastyor')
    c.drawRightString(W - mx, 1.9 * cm, _academic_year())


def _cover_worksheet(c, content, d: _Design):
    """A sheet to be worked on: a ruled frame, the title inside it, and
    real fields for a name, a class and a date at the foot."""
    w, W, H = d.words, A4[0], A4[1]
    mx = 1.7 * cm
    c.setStrokeColor(HexColor(d.accent))
    c.setLineWidth(2.2)
    c.rect(mx, 1.7 * cm, W - 2 * mx, H - 3.4 * cm, stroke=1, fill=0)
    c.setStrokeColor(HexColor(RULE))
    c.setLineWidth(0.7)
    c.rect(mx + 0.28 * cm, 1.98 * cm, W - 2 * mx - 0.56 * cm, H - 3.96 * cm, stroke=1, fill=0)

    # The band sits ON the inner frame's top edge, not floating below it —
    # the gap between the two read as a printing error.
    band_h = 1.15 * cm
    band_y = H - 1.98 * cm - band_h
    c.setFillColor(HexColor(d.accent))
    c.rect(mx + 0.28 * cm, band_y, W - 2 * mx - 0.56 * cm, band_h, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont(FONT_NAME_BOLD, 11)
    c.drawCentredString(W / 2, band_y + 0.38 * cm,
                        f"{'  '.join(w['tag'])}   ·   {content.get('subject', '')}")

    title_lines = _wrap_canvas_text(c, content.get('title', ''), FONT_NAME_BOLD, 26, W - 2 * mx - 2.4 * cm)
    y = H / 2 + 4.4 * cm
    c.setFillColor(HexColor(INK))
    for line in title_lines[:4]:
        c.setFont(FONT_NAME_BOLD, 26)
        c.drawCentredString(W / 2, y, line)
        y -= 1.05 * cm
    if content.get('subtitle'):
        c.setFillColor(HexColor(INK_SOFT))
        for line in _wrap_canvas_text(c, content['subtitle'], FONT_NAME, 11.5, W - 2 * mx - 4 * cm)[:3]:
            c.setFont(FONT_NAME, 11.5)
            c.drawCentredString(W / 2, y - 0.2 * cm, line)
            y -= 0.6 * cm

    _cover_plan(c, content, d, mx + 1.6 * cm, y - 1.6 * cm, W - 2 * mx - 3.2 * cm,
                max_items=5)

    objective = str(content.get('objective') or '').strip()
    if objective:
        c.setFillColor(HexColor(d.tint))
        box_y = 7.4 * cm
        lines = _wrap_canvas_text(c, objective, FONT_NAME, 10, W - 2 * mx - 3.2 * cm)[:4]
        box_h = 1.2 * cm + len(lines) * 0.5 * cm
        c.rect(mx + 1.2 * cm, box_y, W - 2 * mx - 2.4 * cm, box_h, stroke=0, fill=1)
        c.setFillColor(HexColor(d.accent))
        c.setFont(FONT_NAME_BOLD, 8.5)
        c.drawString(mx + 1.6 * cm, box_y + box_h - 0.75 * cm, '  '.join(w['objective'].upper()))
        c.setFillColor(HexColor(INK))
        c.setFont(FONT_NAME, 10)
        ly = box_y + box_h - 1.35 * cm
        for line in lines:
            c.drawString(mx + 1.6 * cm, ly, line)
            ly -= 0.5 * cm

    # The fields are laid out against the space that actually exists
    # between the frame's sides — hard-coded widths ran the date's rule
    # off the edge of the page.
    c.setStrokeColor(HexColor(RULE))
    c.setFillColor(HexColor(INK_SOFT))
    fy = 4.8 * cm
    fx0 = mx + 1.2 * cm
    avail = W - 2 * (mx + 1.2 * cm)
    fields = [(w['name'], 0.5), (w['grade_suffix'].capitalize(), 0.22), (w['date'], 0.28)]
    gap = 0.5 * cm
    fx = fx0
    for label, share in fields:
        c.setFont(FONT_NAME, 9.5)
        c.drawString(fx, fy, label)
        lw = c.stringWidth(label, FONT_NAME, 9.5)
        rule_w = max(1.6 * cm, avail * share - lw - gap)
        c.line(fx + lw + 0.2 * cm, fy - 0.1 * cm, fx + lw + 0.2 * cm + rule_w, fy - 0.1 * cm)
        fx += lw + rule_w + gap

    c.setFont(FONT_NAME, 8.5)
    c.setFillColor(HexColor('#9AA3AF'))
    c.drawCentredString(W / 2, 2.55 * cm, f"Dastyor   ·   {_academic_year()}")


def _cover_plan(c, content, d: _Design, x, y, width, *, rule=False, numbers='plain',
               max_items=5, ink=INK, label_ink=None):
    """The lecture's plan, printed on the cover.

    Every cover has empty middle ground once the title is set, and the
    plan is the one thing a teacher wants to see before opening the
    document — it is what tells them whether this lecture is the one they
    need. Wrapped to two lines rather than clipped: a plan item cut off
    mid-word ("...основания на") reads as a bug, not as a summary."""
    plan = [str(p).strip() for p in (content.get('lecture_plan') or []) if str(p).strip()]
    if not plan:
        return y
    c.setFillColor(HexColor(label_ink or INK_SOFT))
    c.setFont(FONT_NAME_BOLD, 8.5)
    c.drawString(x, y, '   '.join(d.words['plan'].upper()))
    y -= 0.75 * cm
    for i, item in enumerate(plan[:max_items], 1):
        if rule:
            c.setStrokeColor(HexColor(RULE))
            c.setLineWidth(0.6)
            c.line(x, y + 0.42 * cm, x + width, y + 0.42 * cm)
        c.setFillColor(HexColor(d.accent))
        c.setFont(FONT_NAME_BOLD, 9.5 if numbers == 'plain' else 11)
        c.drawString(x, y, f'{i}' if numbers == 'plain' else f'{i:02d}')
        c.setFillColor(HexColor(ink))
        c.setFont(FONT_NAME, 9.5)
        indent = 0.55 * cm if numbers == 'plain' else 1.05 * cm
        lines = _wrap_canvas_text(c, item, FONT_NAME, 9.5, width - indent)[:2]
        for j, line in enumerate(lines):
            c.drawString(x + indent, y - j * 0.45 * cm, line)
        y -= 0.62 * cm + (len(lines) - 1) * 0.45 * cm
    return y


# Nouns for the counts on the cover strip, in the three grammatical
# numbers Russian and Tajik need. English uses one plural form.
_COUNT_WORDS = {
    'Русский': {'sections': ('раздел', 'раздела', 'разделов'),
                'terms': ('термин', 'термина', 'терминов'),
                'examples': ('пример', 'примера', 'примеров'),
                'questions': ('вопрос', 'вопроса', 'вопросов')},
    'Таджикский': {'sections': ('бахш', 'бахш', 'бахш'),
                   'terms': ('истилоҳ', 'истилоҳ', 'истилоҳ'),
                   'examples': ('мисол', 'мисол', 'мисол'),
                   'questions': ('савол', 'савол', 'савол')},
    'English': {'sections': ('section', 'sections', 'sections'),
                'terms': ('term', 'terms', 'terms'),
                'examples': ('example', 'examples', 'examples'),
                'questions': ('question', 'questions', 'questions')},
}
_COUNT_WORDS['Английский'] = _COUNT_WORDS['English']


def _plural(n: int, forms: tuple) -> str:
    """Russian needs three forms and gets them wrong-looking otherwise:
    1 раздел, 2 раздела, 5 разделов."""
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return forms[1]
    return forms[2]


def _cover_facts(c, content, d: _Design, x, y, width, language: str,
                 ink=INK, muted=INK_SOFT):
    """What is actually inside this lecture, as four counts.

    The bottom of a cover is where a designer puts the "what you get"
    line. It is also the honest answer to why the page was empty: there
    was nothing there to read."""
    words = _COUNT_WORDS.get(str(language or 'Русский'), _COUNT_WORDS['Русский'])
    plan = len(content.get('lecture_plan') or [])
    terms = len(content.get('key_terms') or []) + len(content.get('key_concepts') or [])
    examples = len(content.get('real_life_examples') or [])
    questions = len(content.get('quick_check') or [])
    facts = [(plan, 'sections'), (terms, 'terms'),
             (examples, 'examples'), (questions, 'questions')]
    facts = [(n, key) for n, key in facts if n]
    if not facts:
        return
    c.setStrokeColor(HexColor(RULE))
    c.setLineWidth(0.7)
    c.line(x, y + 1.15 * cm, x + width, y + 1.15 * cm)
    step = width / len(facts)
    for i, (n, key) in enumerate(facts):
        c.setFillColor(HexColor(d.accent))
        c.setFont(FONT_NAME_BOLD, 17)
        c.drawString(x + i * step, y + 0.42 * cm, str(n))
        c.setFillColor(HexColor(muted))
        c.setFont(FONT_NAME, 8.5)
        c.drawString(x + i * step, y - 0.1 * cm, _plural(n, words[key]))


_COVERS = {
    'classic': _cover_classic, 'split': _cover_split,
    'banner': _cover_banner, 'worksheet': _cover_worksheet,
}


# ════════════════════════════════════════════════════════════════════════
# SECTION HEADINGS
# ════════════════════════════════════════════════════════════════════════
_ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']


def _heading_smallcaps(label: str, number: int, d: _Design) -> list:
    """"III.  КЛЮЧЕВЫЕ ПОНЯТИЯ" over a hairline — a printed handout's own
    heading, carried by letterspacing rather than by any fill."""
    text = f"{_ROMAN[number] if number < len(_ROMAN) else number}.&nbsp;&nbsp;&nbsp;{label.upper()}"
    head = Paragraph(text, ParagraphStyle(
        name=_uid('HeadSC'), fontName=d.head_font, fontSize=11.5, leading=15,
        textColor=HexColor(INK), spaceBefore=2, spaceAfter=1))
    t = Table([[head]], colWidths=[d.width])
    t.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.9, HexColor(d.accent)),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return [Spacer(1, 14), t, Spacer(1, 7)]


def _heading_ghost(label: str, number: int, d: _Design) -> list:
    """An oversized pale numeral with the heading set against it — the
    section number becomes the page's landmark instead of a bullet."""
    num = Paragraph(f'{number:02d}', ParagraphStyle(
        name=_uid('HeadGhostN'), fontName=FONT_NAME_BOLD, fontSize=30, leading=30,
        textColor=HexColor(_pdf_light_tint_hex(d.accent, amount=0.62)), alignment=TA_LEFT))
    text = Paragraph(label.upper(), ParagraphStyle(
        name=_uid('HeadGhostT'), fontName=FONT_NAME_BOLD, fontSize=13, leading=16,
        textColor=HexColor(INK), spaceBefore=8))
    t = Table([[num, text]], colWidths=[1.5 * cm, d.width - 1.5 * cm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (1, 0), (1, 0), 2.2, HexColor(d.accent)),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return [Spacer(1, 15), t, Spacer(1, 8)]


def _heading_band(label: str, number: int, d: _Design) -> list:
    """The heading reversed out of a solid accent band — the editorial
    look, where a new section is a visible break in the page."""
    head = Paragraph(f'{number:02d}&nbsp;&nbsp;&nbsp;{label.upper()}', ParagraphStyle(
        name=_uid('HeadBand'), fontName=d.head_font, fontSize=12.5, leading=16,
        textColor=colors.white))
    t = Table([[head]], colWidths=[d.width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor(d.accent)),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    return [Spacer(1, 15), t, Spacer(1, 9)]


def _heading_boxed(label: str, number: int, d: _Design) -> list:
    """A numbered square beside the heading — the worksheet's own marker,
    the same shape as the tick boxes further down the page."""
    num = Paragraph(str(number), ParagraphStyle(
        name=_uid('HeadBoxN'), fontName=FONT_NAME_BOLD, fontSize=13, leading=16,
        textColor=colors.white, alignment=TA_CENTER))
    text = Paragraph(label.upper(), ParagraphStyle(
        name=_uid('HeadBoxT'), fontName=FONT_NAME_BOLD, fontSize=12.5, leading=16,
        textColor=HexColor(INK)))
    t = Table([[num, text]], colWidths=[0.85 * cm, d.width - 0.85 * cm], rowHeights=[0.85 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), HexColor(d.accent)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 0), ('RIGHTPADDING', (0, 0), (0, 0), 0),
        ('LEFTPADDING', (1, 0), (1, 0), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LINEBELOW', (1, 0), (1, 0), 1.2, HexColor(RULE)),
    ]))
    return [Spacer(1, 15), t, Spacer(1, 8)]


def _heading_runin(label: str, number: int, d: _Design) -> list:
    """"3. КЛЮЧЕВЫЕ ПОНЯТИЯ" set small over a hairline.

    The plan-konspekt's heading: it marks the section and takes as little
    vertical space as a heading can while still being one. No numeral
    block, no band, no colour behind it — those are for a document meant
    to be looked at, and this one is meant to be worked from."""
    head = Paragraph(
        f'{number}.&nbsp;&nbsp;{label.upper()}',
        ParagraphStyle(name=_uid('HeadRunIn'), fontName=FONT_NAME_BOLD, fontSize=10,
                       leading=13, textColor=HexColor(INK), spaceBefore=0, spaceAfter=1))
    t = Table([[head]], colWidths=[d.width])
    t.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.8, HexColor(d.accent)),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    return [Spacer(1, 9), t, Spacer(1, 4)]


_HEADINGS = {
    'runin': _heading_runin,
    'smallcaps': _heading_smallcaps, 'ghost': _heading_ghost,
    'band': _heading_band, 'boxed': _heading_boxed,
}


def _subheading(text: str, d: _Design) -> list:
    """A sub-topic inside the lecture body. Same in every template — it is
    the level BELOW the one the templates differentiate, and giving it a
    second personality per design made the page noisy."""
    return [Spacer(1, 8), Paragraph(text, ParagraphStyle(
        name=_uid('SubHead'), fontName=d.body_bold, fontSize=d.t.body_size + 1.4,
        leading=d.t.body_leading + 1, textColor=HexColor(d.heading_ink),
        spaceBefore=2, spaceAfter=4))]


# ════════════════════════════════════════════════════════════════════════
# CALLOUTS — «Важно», «Запомни», «Пример», «Совет»
# ════════════════════════════════════════════════════════════════════════
def _callout_colour(kind: str, d: _Design) -> str:
    """Each kind keeps its own hue so a reader learns them by colour:
    warnings warm, examples in the subject's accent, tips green."""
    return {
        'important': '#B4232A', 'remember': d.accent,
        'example': d.accent, 'tip': '#1F7A4D',
    }.get(kind, d.accent)


def _callout_rule(kind: str, label: str, text: str, d: _Design):
    colour = _callout_colour(kind, d)
    body = Paragraph(text, ParagraphStyle(
        name=_uid('CalloutR'), fontName=d.body_font, fontSize=d.t.body_size - 0.3,
        leading=d.t.body_leading - 0.6, textColor=HexColor(INK), alignment=TA_JUSTIFY))
    tag = Paragraph('&nbsp;'.join(label), ParagraphStyle(
        name=_uid('CalloutRL'), fontName=FONT_NAME_BOLD, fontSize=7.6, leading=10,
        textColor=HexColor(colour), spaceAfter=3))
    t = Table([[tag], [body]], colWidths=[d.width - 0.9 * cm])
    t.setStyle(TableStyle([
        ('LINEBEFORE', (0, 0), (0, -1), 2.2, HexColor(colour)),
        ('LEFTPADDING', (0, 0), (-1, -1), 11), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (0, 0), 2), ('BOTTOMPADDING', (0, 0), (0, 0), 0),
        ('TOPPADDING', (0, 1), (0, 1), 0), ('BOTTOMPADDING', (0, 1), (0, 1), 2),
    ]))
    return [Spacer(1, 7), t, Spacer(1, 7)]


def _callout_card(kind: str, label: str, text: str, d: _Design):
    colour = _callout_colour(kind, d)
    tag = Paragraph('&nbsp;'.join(label), ParagraphStyle(
        name=_uid('CalloutCL'), fontName=FONT_NAME_BOLD, fontSize=7.6, leading=10,
        textColor=colors.white, alignment=TA_CENTER))
    chip = Table([[tag]], colWidths=[max(2.0 * cm, 0.32 * cm * len(label))], rowHeights=[0.46 * cm])
    chip.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor(colour)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    body = Paragraph(text, ParagraphStyle(
        name=_uid('CalloutC'), fontName=d.body_font, fontSize=d.t.body_size - 0.3,
        leading=d.t.body_leading - 0.6, textColor=HexColor(INK), alignment=TA_JUSTIFY))
    t = Table([[chip], [body]], colWidths=[d.width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor(_pdf_light_tint_hex(colour, amount=0.94))),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (0, 0), 9), ('BOTTOMPADDING', (0, 0), (0, 0), 5),
        ('TOPPADDING', (0, 1), (0, 1), 0), ('BOTTOMPADDING', (0, 1), (0, 1), 10),
    ]))
    return [Spacer(1, 8), t, Spacer(1, 8)]


def _callout_outline(kind: str, label: str, text: str, d: _Design):
    colour = _callout_colour(kind, d)
    tag = Paragraph('&nbsp;'.join(label), ParagraphStyle(
        name=_uid('CalloutOL'), fontName=FONT_NAME_BOLD, fontSize=7.6, leading=10,
        textColor=HexColor(colour), spaceAfter=4))
    body = Paragraph(text, ParagraphStyle(
        name=_uid('CalloutO'), fontName=d.body_font, fontSize=d.t.body_size - 0.3,
        leading=d.t.body_leading - 0.6, textColor=HexColor(INK), alignment=TA_JUSTIFY))
    t = Table([[tag], [body]], colWidths=[d.width])
    t.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.9, HexColor(colour)),
        ('LINEBEFORE', (0, 0), (0, -1), 4, HexColor(colour)),
        ('LEFTPADDING', (0, 0), (-1, -1), 13), ('RIGHTPADDING', (0, 0), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (0, 0), 8), ('BOTTOMPADDING', (0, 0), (0, 0), 0),
        ('TOPPADDING', (0, 1), (0, 1), 0), ('BOTTOMPADDING', (0, 1), (0, 1), 9),
    ]))
    return [Spacer(1, 8), t, Spacer(1, 8)]


def _callout_dashed(kind: str, label: str, text: str, d: _Design):
    colour = _callout_colour(kind, d)
    tag = Paragraph('&nbsp;'.join(label), ParagraphStyle(
        name=_uid('CalloutDL'), fontName=FONT_NAME_BOLD, fontSize=7.6, leading=10,
        textColor=HexColor(colour), spaceAfter=4))
    body = Paragraph(text, ParagraphStyle(
        name=_uid('CalloutD'), fontName=d.body_font, fontSize=d.t.body_size - 0.4,
        leading=d.t.body_leading - 0.4, textColor=HexColor(INK)))
    t = Table([[tag], [body]], colWidths=[d.width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor(PAPER_SOFT)),
        # A dashed border reads as "cut here / write here", which is
        # exactly the register of a worksheet.
        ('BOX', (0, 0), (-1, -1), 0.9, HexColor(colour), None, (2.5, 2.5)),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (0, 0), 8), ('BOTTOMPADDING', (0, 0), (0, 0), 0),
        ('TOPPADDING', (0, 1), (0, 1), 0), ('BOTTOMPADDING', (0, 1), (0, 1), 9),
    ]))
    return [Spacer(1, 8), t, Spacer(1, 8)]


def _callout_inline(kind: str, label: str, text: str, d: _Design):
    """A margin remark: the label and the note on the same line.

    A filled card costs four lines of height for one sentence. In a
    working document that sentence is a remark, and it is set as one."""
    colour = _callout_colour(kind, d)
    body = Paragraph(
        f'<font color="{colour}"><b>{label}.</b></font>&nbsp;&nbsp;{text}',
        ParagraphStyle(name=_uid('CalloutIn'), fontName=d.body_font,
                       fontSize=d.t.body_size - 0.4, leading=d.t.body_leading - 0.8,
                       textColor=HexColor(INK), alignment=TA_JUSTIFY))
    t = Table([[body]], colWidths=[d.width - 0.55 * cm])
    t.setStyle(TableStyle([
        ('LINEBEFORE', (0, 0), (0, -1), 1.6, HexColor(colour)),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    return [Spacer(1, 4), t, Spacer(1, 5)]


_CALLOUTS = {
    'inline': _callout_inline,
    'rule': _callout_rule, 'card': _callout_card,
    'outline': _callout_outline, 'dashed': _callout_dashed,
}


# ════════════════════════════════════════════════════════════════════════
# DEFINITIONS
# ════════════════════════════════════════════════════════════════════════
def _split_definition(item) -> tuple[str, str]:
    """"Хлоропласт: органоид…" -> ("Хлоропласт", "органоид…")."""
    text = str(item or '').strip()
    for sep in (' — ', ': ', ' – ', ' - '):
        if sep in text:
            head, tail = text.split(sep, 1)
            if len(head) <= 60:
                return head.strip(), tail.strip()
    return '', text


def _definitions_runin(items: list, d: _Design) -> list:
    """Term in bold, definition running on from it — the way a printed
    glossary sets one, with a hanging indent so the terms line up."""
    out = []
    for item in items:
        term, body = _split_definition(item)
        text = f'<b>{term}</b> — {body}' if term else body
        out.append(Paragraph(text, ParagraphStyle(
            name=_uid('DefRunIn'), fontName=d.body_font, fontSize=d.t.body_size,
            leading=d.t.body_leading, textColor=HexColor(INK), alignment=TA_JUSTIFY,
            leftIndent=14, firstLineIndent=-14, spaceAfter=5)))
    return out


def _definitions_cards(items: list, d: _Design) -> list:
    """Two per row, each in its own tinted card with the term as a
    heading — the textbook's "new words" spread."""
    cards = []
    for item in items:
        term, body = _split_definition(item)
        inner = [Paragraph(term or d.words['definition'], ParagraphStyle(
            name=_uid('DefCardT'), fontName=FONT_NAME_BOLD, fontSize=d.t.body_size,
            leading=d.t.body_leading - 1, textColor=HexColor(d.accent), spaceAfter=3))]
        inner.append(Paragraph(body, ParagraphStyle(
            name=_uid('DefCardB'), fontName=d.body_font, fontSize=d.t.body_size - 0.8,
            leading=d.t.body_leading - 1.6, textColor=HexColor(INK))))
        cards.append(inner)

    col_w = (d.width - 0.4 * cm) / 2
    rows = []
    for i in range(0, len(cards), 2):
        pair = cards[i:i + 2]
        if len(pair) == 1:
            pair.append([])
        rows.append(pair)
    out = []
    for left, right in rows:
        t = Table([[left, right]], colWidths=[col_w, col_w])
        style = [
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 9), ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (0, 0), HexColor(d.tint_soft)),
            ('LINEBEFORE', (0, 0), (0, 0), 2.2, HexColor(d.accent)),
        ]
        if right:
            style += [('BACKGROUND', (1, 0), (1, 0), HexColor(d.tint_soft)),
                      ('LINEBEFORE', (1, 0), (1, 0), 2.2, HexColor(d.accent))]
        t.setStyle(TableStyle(style))
        out.extend([t, Spacer(1, 7)])
    return out


def _definitions_quote(items: list, d: _Design) -> list:
    """The term set large in the heading face with the definition beneath
    it and a rule between entries — an editorial glossary."""
    out = []
    for i, item in enumerate(items):
        term, body = _split_definition(item)
        if i:
            out.append(HRFlowable(width='100%', thickness=0.6, color=HexColor(RULE),
                                  spaceBefore=6, spaceAfter=6))
        out.append(Paragraph(term or d.words['definition'], ParagraphStyle(
            name=_uid('DefQT'), fontName=d.head_font, fontSize=d.t.body_size + 2.2,
            leading=d.t.body_leading + 2, textColor=HexColor(INK), spaceAfter=2)))
        out.append(Paragraph(body, ParagraphStyle(
            name=_uid('DefQB'), fontName=d.body_font, fontSize=d.t.body_size,
            leading=d.t.body_leading, textColor=HexColor(INK_SOFT), alignment=TA_JUSTIFY)))
    return out


def _definitions_framed(items: list, d: _Design) -> list:
    """One framed box per term, stacked — a worksheet's "write it here"
    register, with the term on a tinted strip at the top of each box."""
    out = []
    for item in items:
        term, body = _split_definition(item)
        head = Paragraph(term or d.words['definition'], ParagraphStyle(
            name=_uid('DefFT'), fontName=FONT_NAME_BOLD, fontSize=d.t.body_size - 0.2,
            leading=d.t.body_leading - 1, textColor=HexColor(INK)))
        body_p = Paragraph(body, ParagraphStyle(
            name=_uid('DefFB'), fontName=d.body_font, fontSize=d.t.body_size - 0.4,
            leading=d.t.body_leading - 0.8, textColor=HexColor(INK), alignment=TA_JUSTIFY))
        t = Table([[head], [body_p]], colWidths=[d.width])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), HexColor(d.tint)),
            ('BOX', (0, 0), (-1, -1), 0.8, HexColor(RULE)),
            ('LINEBELOW', (0, 0), (0, 0), 0.8, HexColor(RULE)),
            ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        out.extend([t, Spacer(1, 6)])
    return out


_DEFINITIONS = {
    'runin': _definitions_runin, 'cards': _definitions_cards,
    'quote': _definitions_quote, 'framed': _definitions_framed,
}


# ════════════════════════════════════════════════════════════════════════
# TABLES
# ════════════════════════════════════════════════════════════════════════
def _table_styles(kind: str, d: _Design, n_rows: int) -> TableStyle:
    common = [
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]
    if kind == 'ruled':
        return TableStyle(common + [
            ('LINEABOVE', (0, 0), (-1, 0), 1.1, HexColor(INK)),
            ('LINEBELOW', (0, 0), (-1, 0), 0.7, HexColor(INK)),
            ('LINEBELOW', (0, -1), (-1, -1), 1.1, HexColor(INK)),
            ('LINEBELOW', (0, 1), (-1, -2), 0.4, HexColor(RULE)),
        ])
    if kind == 'filled':
        return TableStyle(common + [
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(d.accent)),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, HexColor(d.tint_soft)]),
            ('LINEBELOW', (0, 0), (-1, -1), 0.4, HexColor(RULE)),
        ])
    if kind == 'editorial':
        return TableStyle(common + [
            ('LINEBELOW', (0, 0), (-1, 0), 2.0, HexColor(d.accent)),
            ('LINEBELOW', (0, 1), (-1, -1), 0.5, HexColor(RULE)),
        ])
    return TableStyle(common + [                      # grid
        ('GRID', (0, 0), (-1, -1), 0.7, HexColor(RULE)),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor(d.tint)),
    ])


def _header_text_colour(kind: str, d: _Design) -> str:
    return '#FFFFFF' if kind == 'filled' else INK


def _lecture_table(headers: list, rows: list, d: _Design, title: str = '') -> list:
    if not headers or not rows:
        return []
    kind = d.t.table
    head_style = ParagraphStyle(
        name=_uid('TblH'), fontName=FONT_NAME_BOLD, fontSize=d.t.body_size - 1.2,
        leading=d.t.body_leading - 2, textColor=HexColor(_header_text_colour(kind, d)))
    cell_style = ParagraphStyle(
        name=_uid('TblC'), fontName=d.body_font, fontSize=d.t.body_size - 1.2,
        leading=d.t.body_leading - 2, textColor=HexColor(INK))
    data = [[Paragraph(str(h), head_style) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), cell_style) for c in row])
    n_cols = max(1, len(headers))
    # Widths follow what each column actually holds. Splitting the page
    # evenly broke short cells onto two lines while a one-word column sat
    # half empty ("Вкус/Свойст во" next to "Кислый"), and letting
    # reportlab size them automatically pushes the table past the margin.
    weights = []
    for col in range(n_cols):
        longest = len(str(headers[col]))
        for row in rows:
            if col < len(row):
                longest = max(longest, len(str(row[col])))
        # Square-rooted: a cell with a sentence in it needs more room than
        # a one-word cell, but not five times more.
        weights.append(max(1.0, longest) ** 0.5)
    total = sum(weights)
    widths = [d.width * wgt / total for wgt in weights]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(_table_styles(kind, d, len(data)))
    out = []
    if title:
        out.append(Paragraph(title, ParagraphStyle(
            name=_uid('TblT'), fontName=FONT_NAME_BOLD, fontSize=d.t.body_size - 1,
            leading=d.t.body_leading - 2, textColor=HexColor(INK_SOFT), spaceAfter=4)))
    out.extend([t, Spacer(1, 10)])
    return out


def _form_header(content: dict, d: _Design) -> list:
    """The plan-konspekt's opening block, in place of a cover page.

    A lesson plan starts with the facts of the lesson — topic, subject,
    class, date, duration — laid out like the form a teacher fills in,
    then the aim, then straight into the content. Spending a whole sheet
    of paper on a title is exactly what this format exists not to do."""
    w = d.words
    title = Paragraph(str(content.get('title') or ''), ParagraphStyle(
        name=_uid('FormTitle'), fontName=FONT_NAME_BOLD, fontSize=15, leading=19,
        textColor=HexColor(INK), alignment=TA_CENTER, spaceAfter=2))
    tag = Paragraph('&nbsp;'.join(w['tag']), ParagraphStyle(
        name=_uid('FormTag'), fontName=FONT_NAME_BOLD, fontSize=8,
        leading=11, textColor=HexColor(d.accent), alignment=TA_CENTER, spaceAfter=3))
    out = [tag, title]
    subtitle = str(content.get('subtitle') or '').strip()
    if subtitle:
        out.append(Paragraph(subtitle, ParagraphStyle(
            name=_uid('FormSub'), fontName=d.body_font, fontSize=d.t.body_size - 0.4,
            leading=d.t.body_leading - 1, textColor=HexColor(INK_SOFT),
            alignment=TA_CENTER, spaceAfter=6)))

    grade = str(content.get('grade') or '')
    if grade:
        grade = _format_grade(grade, w['grade_suffix'])
    # A konspekt carries a real duration ("45 минут"); a lecture does not
    # and gets the fixed one-hour placeholder from its own word table.
    duration_text = str(content.get('duration') or '').strip() or w.get('duration_value', '')
    cells = [(w['subject'], str(content.get('subject') or '—')),
             (w['grade_suffix'].capitalize(), grade or '—'),
             (w['duration'], duration_text),
             (w['date'], '________')]
    lbl = ParagraphStyle(name=_uid('FormLbl'), fontName=FONT_NAME, fontSize=7.5,
                         leading=10, textColor=HexColor(INK_SOFT))
    val = ParagraphStyle(name=_uid('FormVal'), fontName=FONT_NAME_BOLD, fontSize=9.5,
                         leading=12, textColor=HexColor(INK))
    row_l = [Paragraph(a, lbl) for a, _ in cells]
    row_v = [Paragraph(b, val) for _, b in cells]
    col = d.width / len(cells)
    t = Table([row_l, row_v], colWidths=[col] * len(cells))
    t.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1.0, HexColor(d.accent)),
        ('LINEBELOW', (0, -1), (-1, -1), 0.7, HexColor(RULE)),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 5), ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
        ('TOPPADDING', (0, 1), (-1, 1), 1), ('BOTTOMPADDING', (0, 1), (-1, 1), 6),
    ]))
    out.extend([t, Spacer(1, 8)])
    return out


# ════════════════════════════════════════════════════════════════════════
# THE DOCUMENT
# ════════════════════════════════════════════════════════════════════════
class _LectureDoc(BaseDocTemplate):
    """Carries the contents page's entries.

    ReportLab can only number a table of contents on a second pass — the
    page a section lands on is not known until the first pass has laid it
    out. multiBuild runs both; this class is what reports each heading's
    final page number into the TOC between them."""

    def __init__(self, *args, page_offset: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self._toc_entries = []
        # A cover page is page 1 of the PDF but page 0 of the document —
        # the numbering a reader sees starts after it. A design with no
        # cover has no offset, and printing "0" in its footer was the
        # visible half of the same bug.
        self.page_offset = page_offset

    def afterFlowable(self, flowable):
        key = getattr(flowable, '_toc_label', None)
        if key:
            self.notify('TOCEntry', (0, key, self.page - self.page_offset))


def _tag_for_toc(flowables: list, label: str):
    """Marks the first flowable of a heading so afterFlowable sees it."""
    for f in flowables:
        if isinstance(f, Table):
            f._toc_label = label
            return
    if flowables:
        flowables[0]._toc_label = label


def _split_main_content(text: str) -> list[tuple[str, list[str]]]:
    """The lecture body split into its sub-topics.

    The model writes the body as "1. Question heading" followed by the
    prose that answers it. Kept as (heading, paragraphs) pairs so the
    renderer can put a real sub-heading on each one and drop a callout
    between them — instead of printing eight paragraphs in a row, which
    is the "wall of text" a teacher sees and closes."""
    raw = str(text or '').strip()
    if not raw:
        return []
    parts: list[tuple[str, list[str]]] = []
    current_head = ''
    current: list[str] = []
    for block in re.split(r'\n\s*\n|\n', raw):
        line = block.strip()
        if not line:
            continue
        m = re.match(r'^(\d{1,2})[.)]\s+(.{4,120})$', line)
        if m and not line.rstrip().endswith(('.', ':', ';')) or (m and line.rstrip().endswith('?')):
            if current_head or current:
                parts.append((current_head, current))
            current_head, current = m.group(2).strip(), []
        else:
            current.append(line)
    if current_head or current:
        parts.append((current_head, current))
    return parts


def _queue_callouts(content: dict, w: dict) -> list[tuple[str, str, str]]:
    """(kind, label, text) for every callout the lecture has to place.

    Ordered so the strongest ones land earliest in the body: a lesson
    that opens with its warning and its first worked example reads as
    taught, not as dumped."""
    queue = []
    for text in (content.get('key_ideas') or [])[:4]:
        if str(text).strip():
            queue.append(('remember', w['remember'], str(text).strip()))
    for text in (content.get('important_notes') or [])[:3]:
        if str(text).strip():
            queue.append(('important', w['important'], str(text).strip()))
    for text in (content.get('real_life_examples') or [])[:4]:
        if str(text).strip():
            queue.append(('example', w['example'], str(text).strip()))
    for text in (content.get('teacher_tips') or [])[:3]:
        if str(text).strip():
            queue.append(('tip', w['tip'], str(text).strip()))
    # Interleave the kinds instead of printing four warnings in a row.
    by_kind: dict[str, list] = {}
    for item in queue:
        by_kind.setdefault(item[0], []).append(item)
    mixed, order = [], ['remember', 'important', 'example', 'tip']
    while any(by_kind.get(k) for k in order):
        for k in order:
            if by_kind.get(k):
                mixed.append(by_kind[k].pop(0))
    return mixed


def build_lecture_pdf(content: dict, language: str = 'Русский') -> io.BytesIO:
    """The whole лекция: cover, contents, body, self-check, conclusions."""
    w = _words(language)
    tmpl = get_lecture_template(content.get('template'))
    accent = get_subject_accent_hex(content.get('subject'))
    d = _Design(tmpl, accent, w)

    buf = io.BytesIO()
    mx = tmpl.margin_x * cm
    doc = _LectureDoc(buf, pagesize=A4, leftMargin=mx, rightMargin=mx,
                      topMargin=tmpl.margin_top * cm, bottomMargin=2.0 * cm,
                      title=str(content.get('title') or 'Лекция'), author='Dastyor',
                      page_offset=0 if tmpl.cover == 'none' else 1)

    def _furniture(canvas_obj, doc_obj):
        """The running head and foot on every page after the cover."""
        canvas_obj.saveState()
        canvas_obj.setFont(FONT_NAME, 8)
        canvas_obj.setFillColor(HexColor('#A8B0BB'))
        head = str(content.get('title') or '')[:70]
        canvas_obj.drawString(mx, A4[1] - 1.15 * cm, head)
        canvas_obj.drawRightString(A4[0] - mx, A4[1] - 1.15 * cm,
                                   f"{content.get('subject', '')}")
        canvas_obj.setStrokeColor(HexColor(RULE))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(mx, A4[1] - 1.35 * cm, A4[0] - mx, A4[1] - 1.35 * cm)
        canvas_obj.line(mx, 1.5 * cm, A4[0] - mx, 1.5 * cm)
        canvas_obj.setFillColor(HexColor(d.accent))
        canvas_obj.setFont(FONT_NAME_BOLD, 8.5)
        canvas_obj.drawRightString(A4[0] - mx, 1.05 * cm,
                                   str(doc_obj.page - getattr(doc_obj, 'page_offset', 1)))
        canvas_obj.setFillColor(HexColor('#A8B0BB'))
        canvas_obj.setFont(FONT_NAME, 8)
        canvas_obj.drawString(mx, 1.05 * cm, 'Dastyor')
        canvas_obj.restoreState()

    def _paint_cover(canvas_obj, doc_obj):
        canvas_obj.saveState()
        try:
            _COVERS.get(tmpl.cover, _cover_split)(canvas_obj, content, d)
        except Exception as e:                        # a cover must never cost the document
            logger.warning(f'lecture cover failed ({tmpl.cover}): {e}')
        canvas_obj.restoreState()

    frame = Frame(mx, 2.0 * cm, A4[0] - 2 * mx,
                  A4[1] - tmpl.margin_top * cm - 2.0 * cm, id='body')
    cover_frame = Frame(mx, 2 * cm, A4[0] - 2 * mx, A4[1] - 4 * cm, id='cover')
    page_templates = [PageTemplate(id='body', frames=[frame], onPage=_furniture)]
    if tmpl.cover != 'none':
        # First in the list is what page 1 uses, so a design without a
        # cover simply never registers one.
        page_templates.insert(0, PageTemplate(id='cover', frames=[cover_frame],
                                              onPage=_paint_cover))
    doc.addPageTemplates(page_templates)

    story: list = [NextPageTemplate('body')]
    if tmpl.cover == 'none':
        # The document starts on page 1 with its own header block: this
        # format does not spend a sheet on a title.
        story.extend(_form_header(content, d))
    else:
        story.extend([Spacer(1, 1), PageBreak()])
    section_no = [0]

    def section(label: str) -> list:
        section_no[0] += 1
        flowables = _HEADINGS.get(tmpl.heading, _heading_ghost)(label, section_no[0], d)
        _tag_for_toc(flowables, f'{section_no[0]}.  {label}')
        return flowables

    # ── contents ────────────────────────────────────────────────────────
    if tmpl.contents:
        story.append(Paragraph(w['contents'].upper(), ParagraphStyle(
            name=_uid('TocTitle'), fontName=d.head_font, fontSize=14, leading=18,
            textColor=HexColor(INK), spaceAfter=4)))
        story.append(HRFlowable(width='100%', thickness=1.2, color=HexColor(d.accent),
                                spaceAfter=10))
        toc = TableOfContents()
        toc.levelStyles = [ParagraphStyle(
            name=_uid('TocL0'), fontName=d.body_font, fontSize=d.t.body_size,
            leading=d.t.body_leading + 3, textColor=HexColor(INK),
            firstLineIndent=0, leftIndent=0, rightIndent=6)]
        toc.dotsMinLevel = 0
        story.append(toc)
        # No page break: a nine-line contents list followed by two thirds
        # of an empty page is the single most "generated" thing a document
        # can do. The first section starts right under it.
        story.append(Spacer(1, 18))

    # ── objective ───────────────────────────────────────────────────────
    objective = str(content.get('objective') or '').strip()
    if objective:
        story.extend(section(w['objective']))
        story.append(_objective_block(objective, d))

    # ── plan ────────────────────────────────────────────────────────────
    plan = [str(p).strip() for p in (content.get('lecture_plan') or []) if str(p).strip()]
    if plan:
        story.extend(section(w['plan']))
        story.extend(_plan_block(plan, d))

    # ── concepts and glossary ───────────────────────────────────────────
    definer = _DEFINITIONS.get(tmpl.definition, _definitions_cards)
    concepts = [c for c in (content.get('key_concepts') or []) if str(c).strip()]
    if concepts:
        story.extend(section(w['concepts']))
        story.extend(definer(concepts, d))
    terms = [t for t in (content.get('key_terms') or []) if str(t).strip()]
    if terms:
        story.extend(section(w['terms']))
        story.extend(definer(terms, d))

    # ── the lecture itself ──────────────────────────────────────────────
    parts = _split_main_content(content.get('main_content'))
    images = list(content.get('lesson_images') or [])
    visuals = list(content.get('visual_blocks') or [])
    if parts:
        story.extend(section(w['body']))
        callouts = _queue_callouts(content, w)
        callout_render = _CALLOUTS.get(tmpl.callout, _callout_card)
        body_style = d.body_style(_uid('Body'))
        for i, (head, paragraphs) in enumerate(parts):
            if head:
                story.extend(_subheading(head, d))
            for para in paragraphs:
                story.append(Paragraph(para, body_style))
            # One callout after each sub-topic, so the reader never gets
            # more than a few paragraphs without a visual break — and the
            # callouts land where they are relevant rather than in a heap
            # at the end of the lecture.
            if callouts and i < len(parts) - 1:
                kind, label, text = callouts.pop(0)
                story.extend(callout_render(kind, label, text, d))
            if images and i in (0, len(parts) // 2):
                story.extend(_figure(images.pop(0), d))
            if visuals and i == max(0, len(parts) - 2):
                story.extend(_visual(visuals.pop(0), d))
        for kind, label, text in callouts:
            story.extend(callout_render(kind, label, text, d))
    for image in images:
        story.extend(_figure(image, d))
    for block in visuals:
        story.extend(_visual(block, d))

    # ── formulas ────────────────────────────────────────────────────────
    formulas = [f for f in (content.get('formulas') or []) if isinstance(f, dict)]
    if formulas:
        story.extend(section(w['formulas']))
        for item in formulas:
            story.extend(_formula_block(item, d))

    # ── self-check ──────────────────────────────────────────────────────
    checks = [q for q in (content.get('quick_check') or []) if q]
    if checks:
        story.extend(section(w['selfcheck']))
        story.extend(_selfcheck_block(checks, d))

    # ── conclusions ─────────────────────────────────────────────────────
    summary = str(content.get('summary') or '').strip()
    if summary:
        story.extend(section(w['summary']))
        story.append(_summary_block(summary, d))

    refs = [str(r).strip() for r in (content.get('references') or []) if str(r).strip()]
    if refs:
        story.extend(section(w['references']))
        for i, ref in enumerate(refs, 1):
            story.append(Paragraph(f'{i}.&nbsp;&nbsp;{ref}', ParagraphStyle(
                name=_uid('Ref'), fontName=d.body_font, fontSize=d.t.body_size - 0.6,
                leading=d.t.body_leading - 1, textColor=HexColor(INK_SOFT),
                leftIndent=16, firstLineIndent=-16, spaceAfter=3)))

    doc.multiBuild(story)
    buf.seek(0)
    return buf


# ── the blocks the body is made of ──────────────────────────────────────
def _objective_block(text: str, d: _Design):
    """The aim, set apart — it is the one sentence a teacher reads first."""
    body = Paragraph(text, ParagraphStyle(
        name=_uid('Obj'), fontName=d.body_font, fontSize=d.t.body_size + 0.6,
        leading=d.t.body_leading + 1.4, textColor=HexColor(INK), alignment=TA_JUSTIFY))
    t = Table([[body]], colWidths=[d.width])
    if d.quiet:
        t.setStyle(TableStyle([
            ('LINEBEFORE', (0, 0), (0, -1), 2.5, HexColor(d.accent)),
            ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
    else:
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor(d.tint)),
            ('LEFTPADDING', (0, 0), (-1, -1), 14), ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 11), ('BOTTOMPADDING', (0, 0), (-1, -1), 11),
        ]))
    return t


def _plan_block(plan: list, d: _Design) -> list:
    """The plan as a numbered list with the numbers in the accent — this
    is the document's own table of contents for the body below."""
    out = []
    for i, item in enumerate(plan, 1):
        num = Paragraph(f'{i:02d}', ParagraphStyle(
            name=_uid('PlanN'), fontName=FONT_NAME_BOLD, fontSize=d.t.body_size,
            leading=d.t.body_leading, textColor=HexColor(d.accent), alignment=TA_RIGHT))
        text = Paragraph(item, ParagraphStyle(
            name=_uid('PlanT'), fontName=d.body_font, fontSize=d.t.body_size,
            leading=d.t.body_leading, textColor=HexColor(INK)))
        t = Table([[num, text]], colWidths=[1.0 * cm, d.width - 1.0 * cm])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (0, 0), 0), ('RIGHTPADDING', (0, 0), (0, 0), 10),
            ('LEFTPADDING', (1, 0), (1, 0), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, HexColor(RULE)),
        ]))
        out.append(t)
    out.append(Spacer(1, 6))
    return out


def _formula_block(item: dict, d: _Design) -> list:
    """The formula as vector art on its own line, with its reading under
    it — the same treatment a textbook gives a boxed rule."""
    formula = str(item.get('formula') or '').strip()
    if not formula:
        return []
    flow = _pdf_formula_flowable(_plain_to_latex(formula), minimal=d.quiet, accent=d.accent)
    out = [Spacer(1, 4)]
    if flow:
        out.append(flow)
    else:
        out.append(Paragraph(formula, ParagraphStyle(
            name=_uid('FormulaTxt'), fontName=d.body_bold, fontSize=d.t.body_size + 2,
            leading=d.t.body_leading + 3, alignment=TA_CENTER, textColor=HexColor(INK))))
    explanation = str(item.get('explanation') or '').strip()
    if explanation:
        out.append(Paragraph(explanation, ParagraphStyle(
            name=_uid('FormulaExp'), fontName=d.body_font, fontSize=d.t.body_size - 1,
            leading=d.t.body_leading - 1.5, alignment=TA_CENTER,
            textColor=HexColor(INK_SOFT), spaceBefore=2, spaceAfter=8)))
    return out


def _selfcheck_block(checks: list, d: _Design) -> list:
    """The questions a student answers to know whether they followed.

    On a worksheet the answer space is ruled and the answer itself is
    dropped — a sheet that prints the answers under the questions is not
    a self-check. Every other design keeps the answer, small and muted,
    because those are read by the teacher."""
    worksheet = d.t.callout == 'dashed'
    out = []
    for i, item in enumerate(checks, 1):
        if isinstance(item, dict):
            question = str(item.get('question') or '').strip()
            answer = str(item.get('answer') or '').strip()
        else:
            question, answer = str(item).strip(), ''
        if not question:
            continue
        out.append(Paragraph(f'<b>{i}.</b>&nbsp;&nbsp;{question}', ParagraphStyle(
            name=_uid('QcQ'), fontName=d.body_font, fontSize=d.t.body_size,
            leading=d.t.body_leading, textColor=HexColor(INK),
            leftIndent=16, firstLineIndent=-16, spaceBefore=5, spaceAfter=3)))
        if worksheet:
            for _ in range(2):
                out.append(Spacer(1, 11))
                out.append(HRFlowable(width='94%', thickness=0.5, color=HexColor(RULE),
                                      hAlign='RIGHT'))
            out.append(Spacer(1, 5))
        elif answer:
            out.append(Paragraph(f"<b>{d.words['answer']}:</b> {answer}", ParagraphStyle(
                name=_uid('QcA'), fontName=d.body_font, fontSize=d.t.body_size - 1,
                leading=d.t.body_leading - 1.5, textColor=HexColor(INK_SOFT),
                leftIndent=16, spaceAfter=4)))
    return out


def _summary_block(text: str, d: _Design):
    body = Paragraph(text, ParagraphStyle(
        name=_uid('Sum'), fontName=d.body_font, fontSize=d.t.body_size,
        leading=d.t.body_leading, textColor=HexColor(INK), alignment=TA_JUSTIFY))
    t = Table([[body]], colWidths=[d.width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1),
         HexColor('#FFFFFF') if d.quiet else HexColor(d.tint_soft)),
        ('BOX', (0, 0), (-1, -1), 0.8, HexColor(d.accent)),
        ('LEFTPADDING', (0, 0), (-1, -1), 13), ('RIGHTPADDING', (0, 0), (-1, -1), 13),
        ('TOPPADDING', (0, 0), (-1, -1), 11), ('BOTTOMPADDING', (0, 0), (-1, -1), 11),
    ]))
    return t


def _figure(image: dict, d: _Design) -> list:
    """One Commons illustration, with its reading instruction under it."""
    body = _pdf_illustration_image(
        image.get('path', ''), '', image.get('credit', ''), max_w=330, max_h=225)
    if not body:
        return []
    parts = list(body)
    note = str(image.get('explanation') or '').strip()
    if note:
        parts.append(Paragraph(note, ParagraphStyle(
            name=_uid('FigNote'), fontName=d.body_font, fontSize=d.t.body_size - 1,
            leading=d.t.body_leading - 1.5, alignment=TA_CENTER,
            textColor=HexColor(INK_SOFT), leftIndent=30, rightIndent=30, spaceBefore=3)))
    return [Spacer(1, 6), KeepTogether(parts), Spacer(1, 10)]


def _visual(block: dict, d: _Design) -> list:
    """A comparison/table block, drawn in this template's table style."""
    btype = str(block.get('type') or '')
    data = block.get('data') or {}
    title = str(block.get('title') or '')
    if btype == 'comparison':
        criteria = [str(c) for c in (data.get('criteria') or [])]
        items = data.get('items') or []
        if criteria and items:
            headers = [''] + criteria
            rows = [[str(it.get('name') or '')] + [str(v) for v in (it.get('values') or [])]
                    for it in items]
            return _lecture_table(headers, rows, d, title)
    if btype == 'table':
        headers = [str(h) for h in (data.get('headers') or [])]
        rows = [[str(c) for c in row] for row in (data.get('rows') or [])]
        if headers and rows:
            return _lecture_table(headers, rows, d, title)
    # Anything else keeps the shared renderer — charts and timelines are
    # drawn the same way in every document in this app.
    try:
        return _pdf_visual_block(block, d.accent, d.quiet)
    except Exception as e:
        logger.warning(f'lecture visual block failed: {e}')
        return []
