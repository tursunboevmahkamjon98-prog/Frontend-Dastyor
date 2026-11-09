"""Konspekt PDF in the formal design.

One look for every subject: white paper, serif headings, a navy accent for
section numbers and markers, light blue-grey shaded cells, thin rules.
Layout: a header with shaded meta cells, numbered sections, goals and
competencies side by side, concept cards, a timed lesson flow, paired
callouts, group cards, check/homework columns and a 5/4/3 rubric.
new_doc, header and side_by_side are shared with lecture_design.
"""

from __future__ import annotations

import io
import re

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, KeepTogether, PageTemplate,
                                Spacer, Table, TableStyle)

from app.export_builder import (CODE_FONT, FONT_NAME, FONT_NAME_BOLD, MATH_FONT, MATH_FONT_BOLD,
                                Paragraph, _math_inline, _pdf_code_card, _pdf_concept_card_grid)
from app.lecture_builder import (_Design, _formula_block, _split_definition,
                                 _split_main_content, _uid, _visual)
from app.lecture_templates import get_lecture_template

INK = '#1A1D24'
MUTED = '#5B6170'
FAINT = '#8A909C'
LINE = '#E4E6EB'
WARN_BG, WARN_INK = '#F2F2F2', '#1A1D24'

# Formal school-document look for every subject: black ink, one light grey
# for shaded cells, serif headings, no motif. The family keys stay so the
# callers (and the docx twin) can still pass a subject family.
_FORMAL = dict(accent='#1F3A5F', tint='#F1F4F8', head='serif')
_FAMILIES = {k: dict(_FORMAL) for k in (
    'math', 'physics', 'chemistry', 'biology', 'geography', 'history',
    'literature', 'code', 'primary', 'general')}

_LABELS = {
    'Русский': dict(tag='КОНСПЕКТ УРОКА', stages='Ход урока', group='Группа', important='ВАЖНО',
                    example='ПРИМЕР ИЗ ЖИЗНИ', min='мин', grade='Класс'),
    'Таджикский': dict(tag='КОНСПЕКТИ ДАРС', stages='Раванди дарс', group='Гурӯҳи', important='МУҲИМ',
                       example='МИСОЛ АЗ ҲАЁТ', min='дақ', grade='Синф'),
    'English': dict(tag='LESSON PLAN', stages='Lesson flow', group='Group', important='IMPORTANT',
                    example='REAL-LIFE EXAMPLE', min='min', grade='Grade'),
}
_LABELS['Английский'] = _LABELS['English']


class _Style:
    def __init__(self, family: str):
        f = _FAMILIES.get(family, _FAMILIES['general'])
        self.family = family
        self.accent = f['accent']
        self.tint = f['tint']
        self.body = FONT_NAME
        self.bold = FONT_NAME_BOLD
        if f['head'] == 'serif':
            self.head = MATH_FONT_BOLD
            self.head_regular = MATH_FONT
        elif f['head'] == 'mono':
            self.head = CODE_FONT
            self.head_regular = CODE_FONT
        else:
            self.head = FONT_NAME_BOLD
            self.head_regular = FONT_NAME
        self.size = 11.5 if family == 'primary' else 10.5
        self.leading = self.size * 1.45

    def p(self, size=None, font=None, color=INK, leading=None, align=TA_LEFT, after=0, before=0):
        size = size or self.size
        return ParagraphStyle(name=_uid('KD'), fontName=font or self.body, fontSize=size,
                              leading=leading or size * 1.45, textColor=HexColor(color),
                              alignment=align, spaceAfter=after, spaceBefore=before)


class _Dot(Flowable):
    """Plain section number, e.g. "3."."""

    def __init__(self, n: int, s: _Style, d: float = 17):
        super().__init__()
        self.n, self.s, self.d = n, s, d
        self.width = self.height = d

    def draw(self):
        c = self.canv
        c.setFillColor(HexColor(self.s.accent))
        c.setFont(self.s.head, 13)
        c.drawString(0, self.d / 2 - 6, f"{self.n}.")


class _Mark(Flowable):
    """Small square bullet or an empty checkbox for homework."""

    def __init__(self, s: _Style, box: bool = False):
        super().__init__()
        self.s, self.box = s, box
        self.width = 10
        self.height = 10

    def draw(self):
        c = self.canv
        if self.box:
            c.setStrokeColor(HexColor(self.s.accent))
            c.setLineWidth(1.1)
            c.roundRect(0, 0, 9, 9, 2, stroke=1, fill=0)
        else:
            c.setFillColor(HexColor(self.s.accent))
            c.roundRect(2, 3, 4.5, 4.5, 1, stroke=0, fill=1)


def _box(content, bg=None, border=None, pad=8, radius=0):
    t = Table([[content]], colWidths=None)
    style = [('LEFTPADDING', (0, 0), (-1, -1), pad + 2), ('RIGHTPADDING', (0, 0), (-1, -1), pad + 2),
             ('TOPPADDING', (0, 0), (-1, -1), pad), ('BOTTOMPADDING', (0, 0), (-1, -1), pad),
             ('VALIGN', (0, 0), (-1, -1), 'TOP')]
    if radius:
        style.append(('ROUNDEDCORNERS', [radius] * 4))
    if bg:
        style.append(('BACKGROUND', (0, 0), (-1, -1), HexColor(bg)))
    if border:
        style.append(('BOX', (0, 0), (-1, -1), 0.8, HexColor(border)))
    t.setStyle(TableStyle(style))
    return t


def _grid(cells: list, cols: int, width: float, gap: float = 7) -> Table:
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    if rows and len(rows[-1]) < cols:
        rows[-1] = rows[-1] + [''] * (cols - len(rows[-1]))
    t = Table(rows, colWidths=[width / cols] * cols)
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), gap / 2), ('RIGHTPADDING', (0, 0), (-1, -1), gap / 2),
        ('TOPPADDING', (0, 0), (-1, -1), gap / 2), ('BOTTOMPADDING', (0, 0), (-1, -1), gap / 2),
    ]))
    return t


def _grid_rows(cells: list, cols: int, width: float, gap: float = 7) -> list:
    """The grid as one table per row, so a section heading glued to it pulls
    only the first row onto a new page, not the whole grid (which left half
    a page blank)."""
    return [_grid(cells[i:i + cols], cols, width, gap) for i in range(0, len(cells), cols)]


def _section(n: int, label: str, s: _Style, width: float) -> Table:
    t = Table([[_Dot(n, s), Paragraph(label, s.p(13, s.head, INK, 17))]],
              colWidths=[24, width - 24])
    # The gap below the heading lives inside it: keepWithNext only binds the
    # next flowable, and a separate Spacer there let the heading strand
    # alone at the foot of a page.
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                           ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                           ('LINEBELOW', (0, 0), (-1, -1), 0.6, HexColor('#C9D2DE'))]))
    t.keepWithNext = 1
    return t


def _bullets(items: list, s: _Style, box: bool = False) -> Table:
    rows = [[_Mark(s, box), Paragraph(_math_inline(str(it), size=s.size), s.p())] for it in items]
    t = Table(rows, colWidths=[16, None])
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                           ('TOPPADDING', (0, 0), (0, -1), 4), ('TOPPADDING', (1, 0), (1, -1), 0),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return t


def _cap(text: str) -> str:
    text = str(text).strip()
    return text[:1].upper() + text[1:]


def _short(items) -> list[str]:
    return [str(x).strip() for x in (items or []) if str(x).strip()]


def _rubric(text: str, s: _Style, width: float):
    parts = re.split(r'[«"]?([2-5])[»"]?\s*[—–-]\s*', text)
    marks = [(parts[i], parts[i + 1].strip().rstrip('.')) for i in range(1, len(parts) - 1, 2)]
    if len(marks) < 2:
        return None
    cells = []
    for mark, desc in marks[:4]:
        body = [Paragraph(mark, s.p(20, s.head, s.accent, 22)),
                Paragraph(_cap(desc), s.p(s.size - 0.5))]
        cells.append(_box(body, bg='#F5F6F8'))
    return [_grid(cells, len(cells), width)]


MARGIN = 1.75 * cm
WIDTH = A4[0] - 2 * MARGIN


def new_doc(buf, content: dict, s: _Style) -> BaseDocTemplate:
    """A4 page with the footer line, title · subject and page number."""
    title = str(content.get('title') or '')
    subject = str(content.get('subject') or '')
    grade = str(content.get('grade') or '')
    footer_text = ' · '.join(p for p in (title, ', '.join(q for q in (subject, grade) if q)) if p)
    mx = MARGIN

    def furniture(c, doc):
        c.saveState()
        c.setStrokeColor(HexColor('#EEF0F3'))
        c.setLineWidth(0.6)
        c.line(mx, 1.45 * cm, A4[0] - mx, 1.45 * cm)
        c.setFont(FONT_NAME, 8)
        c.setFillColor(HexColor(FAINT))
        c.drawString(mx, 1.0 * cm, footer_text[:95])
        c.setFont(FONT_NAME_BOLD, 9)
        c.setFillColor(HexColor(s.accent))
        c.drawRightString(A4[0] - mx, 1.0 * cm, str(doc.page))
        c.restoreState()

    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=mx, rightMargin=mx,
                          topMargin=1.5 * cm, bottomMargin=1.9 * cm,
                          title=title or 'Dastyor', author='Dastyor')
    doc.addPageTemplates([PageTemplate(id='p', frames=[Frame(
        mx, 1.9 * cm, WIDTH, A4[1] - 3.4 * cm, id='f', leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0)], onPage=furniture)])
    return doc


def header(tag: str, content: dict, meta: list[tuple[str, str]], s: _Style) -> list:
    """Tag, serif title, subtitle, short accent bar and the shaded meta cells."""
    out = [Paragraph(tag, s.p(8.5, s.head, s.accent, 11, after=6)),
           Paragraph(str(content.get('title') or ''), s.p(25, s.head, INK, 30, after=4))]
    if content.get('subtitle'):
        out.append(Paragraph(str(content['subtitle']), s.p(12, s.body, MUTED, 16, after=2)))
    bar = _box(Spacer(48, 0.1), bg=s.accent, pad=1.2, radius=0)
    bar.hAlign = 'LEFT'
    cells = [_box([Paragraph(k.upper(), s.p(7, s.bold, MUTED, 9)),
                   Paragraph(v or '—', s.p(10, s.bold, INK, 13))], bg=s.tint, pad=6)
             for k, v in meta]
    return out + [Spacer(1, 6), bar, Spacer(1, 10), _grid(cells, len(cells), WIDTH, gap=6),
                  Spacer(1, 14)]


def side_by_side(left: list, right: list) -> Table:
    t = Table([[left, right]], colWidths=[WIDTH / 2, WIDTH / 2])
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 0),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 8)]))
    return t


def build(content: dict, words: dict, language: str, family: str) -> io.BytesIO:
    s = _Style(family)
    lab = _LABELS.get(language, _LABELS['Русский'])
    buf = io.BytesIO()
    width = WIDTH
    subject = str(content.get('subject') or '')
    grade = str(content.get('grade') or '')
    doc = new_doc(buf, content, s)
    helper = _Design(get_lecture_template('planspekt'), s.accent, words)

    duration = str(content.get('duration') or '').strip() or words.get('duration_value', '')
    story: list = header(lab['tag'], content, [
        (words['subject'], subject), (lab['grade'], grade), (words['duration'], duration),
        (words['date'], '____________')], s)

    n = [0]

    def sec(label):
        n[0] += 1
        return [_section(n[0], label, s, width)]

    def para(text):
        return Paragraph(_math_inline(str(text), size=s.size), s.p(after=5))

    objectives = _short(content.get('objectives'))
    competencies = _short(content.get('competencies'))
    if objectives and competencies:
        half = width / 2 - 8
        n[0] += 1
        left = [_section(n[0], words['objectives'], s, half), _bullets(objectives, s)]
        n[0] += 1
        right = [_section(n[0], words['competencies'], s, half), _bullets(competencies, s)]
        t = Table([[left, right]], colWidths=[width / 2, width / 2])
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 0),
                               ('RIGHTPADDING', (0, 0), (-1, -1), 8)]))
        story += [t, Spacer(1, 12)]
    else:
        for label, items in ((words['objectives'], objectives), (words['competencies'], competencies)):
            if items:
                story += sec(label) + [_bullets(items, s), Spacer(1, 12)]

    def cards(items):
        out = []
        for it in items:
            term, body = _split_definition(it)
            parts = []
            if term:
                parts.append(Paragraph(term, s.p(s.size, s.head, s.accent, s.size * 1.35)))
            parts.append(Paragraph(_math_inline(_cap(body), size=s.size - 0.5), s.p(s.size - 0.5)))
            out.append(_box(parts, border=LINE))
        return _grid_rows(out, 2, width)

    concepts = _short(content.get('key_concepts'))
    if concepts:
        story += sec(words['concepts']) + cards(concepts) + [Spacer(1, 10)]
    if content.get('concept_cards'):
        story += _pdf_concept_card_grid(content['concept_cards'], s.accent)
    terms = _short(content.get('key_terms'))
    if terms:
        story += sec(words['terms']) + cards(terms) + [Spacer(1, 10)]

    stages = [st for st in (content.get('lesson_stages') or []) if isinstance(st, dict) and st.get('stage')]
    if stages:
        story += sec(lab['stages'])
        rows = []
        for st in stages:
            minutes = str(st.get('minutes') or st.get('time') or '').strip()
            if minutes and minutes.isdigit():
                minutes = f"{minutes} {lab['min']}"
            pill = _box(Paragraph(minutes or '·', s.p(8.5, s.bold, s.accent, 11, align=TA_CENTER)),
                        bg=s.tint, pad=2, radius=4)
            rows.append([pill, Paragraph(str(st.get('stage')), s.p(s.size, s.bold)),
                         Paragraph(_math_inline(str(st.get('activity') or ''), size=s.size), s.p(color=MUTED))])
        t = Table(rows, colWidths=[56, 120, width - 176])
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('LINEBELOW', (0, 0), (-1, -2), 0.5, HexColor('#EEF0F3')),
                               ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                               ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
        story += [t, Spacer(1, 12)]
    elif str(content.get('lesson_program') or '').strip():
        story += sec(words['lesson_program']) + [para(content['lesson_program']), Spacer(1, 8)]

    tools = _short(content.get('tools'))
    if tools:
        story += sec(words['tools']) + [_bullets(tools, s), Spacer(1, 12)]

    # main content with its visuals and callouts
    parts = _split_main_content(content.get('main_content'))
    # No pictures (same as the lecture): Commons images were often off-topic
    # and left large blank gaps. Tables and diagrams (visual_blocks) stay.
    visuals = list(content.get('visual_blocks') or [])
    if parts:
        story += sec(words['body'])
        for head, paragraphs in parts:
            if head:
                story.append(Paragraph(head, s.p(s.size + 1, s.head, INK, before=4, after=3)))
            story += [para(t) for t in paragraphs]
        for block in visuals:
            story += _visual(block, helper)
        for f in content.get('formulas') or []:
            if isinstance(f, dict):
                story += _formula_block(f, helper)
    callouts = []
    for t in _short(content.get('important_notes'))[:2]:
        callouts.append(_box([Paragraph(lab['important'], s.p(7.5, s.bold, WARN_INK, 10, after=2)),
                              Paragraph(_math_inline(t, size=s.size - 0.5), s.p(s.size - 0.5))], bg=WARN_BG))
    from app.docx_builder import _strip_item_label
    for t in _short(content.get('real_life_examples'))[:4]:
        callouts.append(_box([Paragraph(lab['example'], s.p(7.5, s.bold, s.accent, 10, after=2)),
                              Paragraph(_math_inline(_strip_item_label(t), size=s.size - 0.5),
                                        s.p(s.size - 0.5))], bg=s.tint))
    if callouts:
        story += [Spacer(1, 4)] + _grid_rows(callouts, 2, width) + [Spacer(1, 10)]

    for cb in content.get('code_blocks') or []:
        if isinstance(cb, dict) and cb.get('code'):
            story += _pdf_code_card(cb.get('code', ''), cb.get('language', ''),
                                    cb.get('explanation', ''), s.accent)

    worked = [it for it in (content.get('worked_examples') or []) if isinstance(it, dict) and it.get('problem')]
    if worked:
        story += sec(words['worked_examples'])
        for it in worked:
            story.append(_box([Paragraph(_math_inline(str(it['problem']), size=s.size), s.p(after=4)),
                               Paragraph(words['solution'].upper(), s.p(7.5, s.bold, s.accent, 10)),
                               Paragraph(_math_inline(str(it.get('solution') or ''), size=s.size),
                                         s.p(color=MUTED))], border=LINE))
            story.append(Spacer(1, 6))
    drills = [it for it in (content.get('practice_problems') or []) if isinstance(it, dict) and it.get('problem')]
    if drills:
        story += sec(words['practice_problems']) + [_bullets([d['problem'] for d in drills], s), Spacer(1, 10)]

    # classroom work
    pair = str(content.get('pair_work') or '').strip()
    groups = [_strip_item_label(t) for t in _short(content.get('group_work'))]
    consolidation = str(content.get('consolidation') or '').strip()
    if pair or groups or consolidation:
        story += sec(words['activities'])
        if pair:
            story += [Paragraph(words['pair_work'], s.p(s.size, s.bold, after=2)), para(pair)]
        if groups:
            gcells = [_box([Paragraph(f"{lab['group'].upper()} {k + 1}", s.p(7.5, s.bold, MUTED, 10, after=2)),
                            Paragraph(_math_inline(g, size=s.size - 0.5), s.p(s.size - 0.5))], border=LINE)
                      for k, g in enumerate(groups)]
            story += [Spacer(1, 2), _grid(gcells, 3 if len(gcells) >= 3 else len(gcells), width), Spacer(1, 4)]
        if consolidation:
            story += [Paragraph(words['consolidation'], s.p(s.size, s.bold, after=2, before=4)),
                      para(consolidation)]
        story.append(Spacer(1, 8))

    checks = [q for q in (content.get('quick_check') or []) if isinstance(q, dict) and q.get('question')]
    homework = [_strip_item_label(t) for t in _short(content.get('homework'))]
    left, right = [], []
    if checks:
        rows = []
        for k, q in enumerate(checks):
            rows.append(Paragraph(f"{k + 1}. " + _math_inline(str(q['question']), size=s.size), s.p(after=0)))
            if q.get('answer'):
                rows.append(Paragraph(f"{words['answer']}: " + _math_inline(str(q['answer']), size=s.size - 1.5),
                                      s.p(s.size - 1.5, color=MUTED, after=4)))
        left = ['checks', rows]
    if homework:
        right = ['homework', _bullets(homework, s, box=True)]
    if left and right:
        n[0] += 1
        lcol = [_section(n[0], words['selfcheck'], s, width / 2 - 8)] + left[1]
        n[0] += 1
        rcol = [_section(n[0], words['homework'], s, width / 2 - 8), right[1]]
        t = Table([[lcol, rcol]], colWidths=[width / 2, width / 2])
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 8)]))
        story += [t, Spacer(1, 12)]
    else:
        if left:
            story += sec(words['selfcheck']) + left[1] + [Spacer(1, 10)]
        if right:
            story += sec(words['homework']) + [right[1], Spacer(1, 10)]

    assessment = str(content.get('assessment') or '').strip()
    if assessment:
        rubric = _rubric(assessment, s, width)
        story += sec(words['assessment']) + (rubric or [para(assessment)]) + [Spacer(1, 10)]

    answers = [str(it.get('answer')) for it in drills if str(it.get('answer') or '').strip()]
    if answers:
        story += sec(words['answers']) + [_bullets(answers, s), Spacer(1, 10)]

    summary = str(content.get('summary') or '').strip()
    if summary:
        story += sec(words['summary']) + [_box(Paragraph(_math_inline(summary, size=s.size), s.p()),
                                               bg=s.tint, pad=10)]

    doc.build(story)
    buf.seek(0)
    return buf
