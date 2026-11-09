"""Konspekt .docx in the per-subject design.

Word counterpart of konspekt_design (the PDF): same palettes, labels and
section order, so a teacher who downloads both gets the same document.
Word has no drawn shapes in flowing text, so cards and pills are table



"""

from __future__ import annotations

import io
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from app.docx_builder import (_add_code_card, _add_formula_card, _add_lesson_image_block,
                              _add_visual_block, _add_worked_examples, _clear_cell,
                              _set_cell_shading, _strip_item_label, _typeset_math_runs)
from app.konspekt_design import _FAMILIES, _LABELS
from app.lecture_builder import _split_definition, _split_main_content
from app.subject_templates import safe_font

INK = '1A1D24'
MUTED = '5B6170'
FAINT = '8A909C'
LINE = 'E4E6EB'
WARN_BG, WARN_INK = 'F2F2F2', '1A1D24'
WIDTH_CM = 17.5


def _rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip('#')
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


class _Style:
    def __init__(self, family: str, language: str):
        f = _FAMILIES.get(family, _FAMILIES['general'])
        self.family = family
        self.accent = f['accent'].lstrip('#')
        self.tint = f['tint'].lstrip('#')
        # Formal school document: Times New Roman throughout (Tajik-safe).
        self.head = safe_font('Times New Roman', language)
        self.body = safe_font('Times New Roman', language)
        self.size = 11.5 if family == 'primary' else 10.5


def _run(p, text, s: _Style, size=None, bold=False, color=INK, font=None, italic=False):
    r = p.add_run(str(text))
    r.font.size = Pt(size or s.size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = _rgb(color)
    name = font or s.body
    r.font.name = name
    r._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), name)
    return r


def _para(container, after=4, before=0, align=None):
    p = container.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = 1.2
    if align is not None:
        p.alignment = align
    return p


def _cell_para(cell, after=2):
    p = cell.paragraphs[0] if (len(cell.paragraphs) == 1 and not cell.paragraphs[0].text) else cell.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    return p


def _borders(cell, color=LINE, size='6'):
    tcPr = cell._element.get_or_add_tcPr()
    b = OxmlElement('w:tcBorders')
    for side in ('top', 'left', 'bottom', 'right'):
        e = OxmlElement(f'w:{side}')
        e.set(qn('w:val'), 'single')
        e.set(qn('w:sz'), size)
        e.set(qn('w:space'), '0')
        e.set(qn('w:color'), color)
        b.append(e)
    tcPr.append(b)


def _margins(cell, top=90, side=140):
    tcPr = cell._element.get_or_add_tcPr()
    m = OxmlElement('w:tcMar')
    for name, val in (('top', top), ('bottom', top), ('left', side), ('right', side)):
        e = OxmlElement(f'w:{name}')
        e.set(qn('w:w'), str(val))
        e.set(qn('w:type'), 'dxa')
        m.append(e)
    tcPr.append(m)


def _fix_widths(table, widths_cm):
    """Word ignores cell widths unless the table is fixed-layout and its grid
    columns carry the same widths."""
    layout = OxmlElement('w:tblLayout')
    layout.set(qn('w:type'), 'fixed')
    table._tbl.tblPr.append(layout)
    for i, w in enumerate(widths_cm):
        table.columns[i].width = Cm(w)
        for cell in table.columns[i].cells:
            cell.width = Cm(w)


def _grid(doc, n: int, cols: int, gap_cm: float = 0.25):
    """A borderless table of `n` card cells; gutters are empty columns and rows."""
    rows = (n + cols - 1) // cols
    t = doc.add_table(rows=rows * 2 - 1, cols=cols * 2 - 1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    card_w = (WIDTH_CM - gap_cm * (cols - 1)) / cols
    _fix_widths(t, [gap_cm if c % 2 else card_w for c in range(cols * 2 - 1)])
    cells = []
    for r in range(rows * 2 - 1):
        t.rows[r]._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        if r % 2:
            t.rows[r].height = Cm(gap_cm)
            for c in range(cols * 2 - 1):
                gap_p = t.cell(r, c).paragraphs[0]
                gap_p.paragraph_format.space_after = Pt(0)
                gap_p.paragraph_format.line_spacing = Pt(1)
            continue
        for c in range(0, cols * 2 - 1, 2):
            cells.append(t.cell(r, c))
    _para(doc, after=2)
    return cells[:n], cells[n:]


def _heading(doc, n: int, label: str, s: _Style):
    p = _para(doc, after=5, before=10)
    p.paragraph_format.keep_with_next = True
    _run(p, f'{n}. ', s, 13, True, s.accent, s.head)
    _run(p, label, s, 13, True, INK, s.head)
    _rule_below(p)
    return p


def _rule_below(p, color='C9D2DE', size='6'):
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    for k, v in (('w:val', 'single'), ('w:sz', size), ('w:space', '2'), ('w:color', color)):
        bottom.set(qn(k), v)
    bdr.append(bottom)
    pPr.append(bdr)


def _bullets(container, items, s: _Style, box=False, in_cell=False):
    for it in items:
        p = _cell_para(container, 3) if in_cell else _para(container, 3)
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.first_line_indent = Cm(-0.5)
        _run(p, '☐  ' if box else '•  ', s, s.size, False, s.accent)
        _run(p, it, s)


def _short(items) -> list[str]:
    return [str(x).strip() for x in (items or []) if str(x).strip()]


def _cap(text: str) -> str:
    text = str(text).strip()
    return text[:1].upper() + text[1:]


def _cards(doc, items, s: _Style, cols=2, fill=None, border=True, label=None, label_color=None):
    cells, spare = _grid(doc, len(items), cols)
    for cell, item in zip(cells, items):
        _clear_cell(cell)
        _margins(cell)
        if fill:
            _set_cell_shading(cell, fill)
        if border:
            _borders(cell)
        if isinstance(item, tuple):
            head, body = item
        else:
            head, body = _split_definition(item)
        if label:
            _run(_cell_para(cell), label, s, 7.5, True, label_color or MUTED)
        if head:
            _run(_cell_para(cell), head, s, s.size, s.family not in ('history', 'literature'),
                 s.accent, s.head)
        _run(_cell_para(cell), _cap(body), s, s.size - 0.5)
    for cell in spare:
        _clear_cell(cell)


def _footer(doc, text: str, s: _Style):
    footer = doc.sections[0].footer
    p = footer.paragraphs[0]
    # The Footer style already carries a centre and a right tab stop.
    _run(p, text[:95], s, 8, False, FAINT)
    _run(p, '\t\t', s, 8)
    r = _run(p, '', s, 9, True, s.accent)
    for kind, val in (('begin', None), ('instr', ' PAGE '), ('end', None)):
        if kind == 'instr':
            e = OxmlElement('w:instrText')
            e.set(qn('xml:space'), 'preserve')
            e.text = val
        else:
            e = OxmlElement('w:fldChar')
            e.set(qn('w:fldCharType'), kind)
        r._element.append(e)


def new_doc(content: dict, s: _Style) -> Document:
    """A4 document with margins, base font and the title · subject footer."""
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(1.75)
    sec.top_margin, sec.bottom_margin = Cm(1.5), Cm(1.6)
    normal = doc.styles['Normal']
    normal.font.name = s.body
    normal.font.size = Pt(s.size)
    normal._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), s.body)
    title = str(content.get('title') or '')
    subject = str(content.get('subject') or '')
    grade = str(content.get('grade') or '')
    _footer(doc, ' · '.join(p for p in (title, ', '.join(q for q in (subject, grade) if q)) if p), s)
    return doc


def header(doc, tag: str, content: dict, meta: list[tuple[str, str]], s: _Style) -> None:
    """Tag, title, subtitle, short accent rule and the shaded meta cells."""
    _run(_para(doc, after=4), tag, s, 8.5, True, s.accent, s.head)
    _run(_para(doc, after=3), str(content.get('title') or ''), s, 24, False, INK, s.head)
    if content.get('subtitle'):
        _run(_para(doc, after=8), content['subtitle'], s, 12, False, MUTED)
    _rule_below(_para(doc, after=8), s.accent, '18')
    cells, _ = _grid(doc, len(meta), len(meta), 0.2)
    for cell, (k, v) in zip(cells, meta):
        _clear_cell(cell)
        _margins(cell, 70, 120)
        _set_cell_shading(cell, s.tint)
        _run(_cell_para(cell, 0), k.upper(), s, 7, True, MUTED)
        _run(_cell_para(cell, 0), v or '—', s, 10, True, INK)


def side_by_side(doc, blocks: list[tuple[str, callable]], start: int, s: _Style) -> int:
    """Two numbered sections in one row; each block fills its cell. Returns the last number."""
    t = doc.add_table(rows=1, cols=2)
    t.autofit = False
    _fix_widths(t, [WIDTH_CM / 2, WIDTH_CM / 2])
    n = start
    for cell, (label, fill) in zip((t.cell(0, 0), t.cell(0, 1)), blocks):
        cell.width = Cm(WIDTH_CM / 2)
        _clear_cell(cell)
        n += 1
        hp = _cell_para(cell, 5)
        _run(hp, f'{n}. ', s, 13, True, s.accent, s.head)
        _run(hp, label, s, 13, True, INK, s.head)
        _rule_below(hp)
        fill(cell)
    _para(doc, after=2)
    return n


def build(content: dict, L: dict, language: str, family: str) -> io.BytesIO:
    s = _Style(family, language)
    lab = _LABELS.get(language, _LABELS['Русский'])
    accent_rgb = _rgb(s.accent)
    doc = new_doc(content, s)
    en = language in ('English', 'Английский')
    header(doc, lab['tag'], content, [
        ('Subject' if en else 'Фан' if language == 'Таджикский' else 'Предмет',
         str(content.get('subject') or '')),
        (lab['grade'], str(content.get('grade') or '')),
        (L.get('duration', 'Время урока'), str(content.get('duration') or '').strip() or '—'),
        ('Date' if en else 'Сана' if language == 'Таджикский' else 'Дата', '____________')], s)

    n = [0]

    def head(label):
        n[0] += 1
        _heading(doc, n[0], label, s)

    def text(t):
        _run(_para(doc, after=5), t, s)

    objectives = _short(content.get('objectives'))
    competencies = _short(content.get('competencies'))
    if objectives and competencies:
        n[0] = side_by_side(doc, [
            (L.get('objectives', 'Цели урока'), lambda c: _bullets(c, objectives, s, in_cell=True)),
            (L.get('competencies', 'Компетенции'), lambda c: _bullets(c, competencies, s, in_cell=True)),
        ], n[0], s)
    else:
        for label, items in ((L.get('objectives', 'Цели урока'), objectives),
                             (L.get('competencies', 'Компетенции'), competencies)):
            if items:
                head(label)
                _bullets(doc, items, s)

    concepts = _short(content.get('key_concepts'))
    if concepts:
        head(L.get('key_concepts', 'Ключевые понятия'))
        _cards(doc, concepts, s)
    terms = _short(content.get('key_terms'))
    if terms:
        head(L.get('key_terms', 'Словарь урока'))
        _cards(doc, terms, s)

    stages = [st for st in (content.get('lesson_stages') or []) if isinstance(st, dict) and st.get('stage')]
    if stages:
        head(lab['stages'])
        t = doc.add_table(rows=len(stages), cols=3)
        t.autofit = False
        _fix_widths(t, [2.0, 4.3, WIDTH_CM - 6.3])
        for r, st in enumerate(stages):
            minutes = str(st.get('minutes') or st.get('time') or '').strip()
            if minutes.isdigit():
                minutes = f"{minutes} {lab['min']}"
            widths = (2.0, 4.3, WIDTH_CM - 6.3)
            for c, w in enumerate(widths):
                t.cell(r, c).width = Cm(w)
                _clear_cell(t.cell(r, c))
            _run(_cell_para(t.cell(r, 0), 0), minutes or '·', s, 8.5, True, s.accent)
            _cell_para(t.cell(r, 0), 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
            _run(_cell_para(t.cell(r, 1), 0), st.get('stage'), s, s.size, True)
            _run(_cell_para(t.cell(r, 2), 0), st.get('activity') or '', s, s.size, False, MUTED)
        _para(doc, after=2)
    elif str(content.get('lesson_program') or '').strip():
        head(L.get('lesson_program', 'План урока'))
        text(content['lesson_program'])

    tools = _short(content.get('tools'))
    if tools:
        head(L.get('tools', 'Материалы'))
        _bullets(doc, tools, s)

    parts = _split_main_content(content.get('main_content'))
    images = list(content.get('lesson_images') or [])
    if parts:
        head(L.get('main_content', 'Основное содержание'))
        for i, (sub, paragraphs) in enumerate(parts):
            if sub:
                _run(_para(doc, after=3, before=4), sub, s, s.size + 1, True, INK, s.head)
            for t in paragraphs:
                text(t)
            if images and i in (0, len(parts) // 2):
                _add_lesson_image_block(doc, images.pop(0), L.get('illustration', ''), accent_rgb)
    for img in images:
        _add_lesson_image_block(doc, img, L.get('illustration', ''), accent_rgb)
    for block in content.get('visual_blocks') or []:
        _add_visual_block(doc, block, accent_rgb, L)
    for f in content.get('formulas') or []:
        if isinstance(f, dict) and (f.get('formula') or f.get('latex')):
            _add_formula_card(doc, str(f.get('formula') or f.get('latex')), str(f.get('explanation') or ''),
                              accent_rgb)

    callouts = [(lab['important'], WARN_BG, WARN_INK, t) for t in _short(content.get('important_notes'))[:2]]
    callouts += [(lab['example'], s.tint, s.accent, _strip_item_label(t))
                 for t in _short(content.get('real_life_examples'))[:4]]
    if callouts:
        cells, spare = _grid(doc, len(callouts), 2)
        for cell, (label, fill, ink, body) in zip(cells, callouts):
            _clear_cell(cell)
            _margins(cell)
            _set_cell_shading(cell, fill)
            _run(_cell_para(cell), label, s, 7.5, True, ink)
            _run(_cell_para(cell), body, s, s.size - 0.5)
        for cell in spare:
            _clear_cell(cell)

    for cb in content.get('code_blocks') or []:
        if isinstance(cb, dict) and cb.get('code'):
            _add_code_card(doc, cb.get('code', ''), cb.get('language', ''), cb.get('explanation', ''), accent_rgb)

    worked = [it for it in (content.get('worked_examples') or []) if isinstance(it, dict) and it.get('problem')]
    if worked:
        head(L.get('worked_examples', 'Решённые примеры'))
        _add_worked_examples(doc, worked, accent_rgb, L.get('solution', 'Решение'))
    drills = [it for it in (content.get('practice_problems') or []) if isinstance(it, dict) and it.get('problem')]
    if drills:
        head({'Таджикский': 'Машқҳои мустақил', 'English': 'Practice problems',
              'Английский': 'Practice problems'}.get(language, 'Практические задачи'))
        _bullets(doc, [d['problem'] for d in drills], s)

    pair = str(content.get('pair_work') or '').strip()
    groups = [_strip_item_label(t) for t in _short(content.get('group_work'))]
    consolidation = str(content.get('consolidation') or '').strip()
    if pair or groups or consolidation:
        head({'Таджикский': 'Кор дар дарс', 'English': 'Classroom activities',
              'Английский': 'Classroom activities'}.get(language, 'Работа на уроке'))
        if pair:
            _run(_para(doc, after=2), L.get('pair_work', 'Работа в парах'), s, s.size, True)
            text(pair)
        if groups:
            cells, spare = _grid(doc, len(groups), min(3, len(groups)))
            for k, (cell, g) in enumerate(zip(cells, groups)):
                _clear_cell(cell)
                _margins(cell)
                _borders(cell)
                _run(_cell_para(cell), f"{lab['group'].upper()} {k + 1}", s, 7.5, True, MUTED)
                _run(_cell_para(cell), g, s, s.size - 0.5)
            for cell in spare:
                _clear_cell(cell)
        if consolidation:
            _run(_para(doc, after=2, before=4), L.get('consolidation', 'Закрепление'), s, s.size, True)
            text(consolidation)

    checks = [q for q in (content.get('quick_check') or []) if isinstance(q, dict) and q.get('question')]
    homework = [_strip_item_label(t) for t in _short(content.get('homework'))]
    if checks:
        head(L.get('quick_check', 'Быстрая проверка'))
        for k, q in enumerate(checks):
            _run(_para(doc, after=0), f"{k + 1}. {q['question']}", s)
            if q.get('answer'):
                _run(_para(doc, after=4), f"{L.get('answer', 'Ответ')}: {q['answer']}", s, s.size - 1.5, False, MUTED)
    if homework:
        head(L.get('homework', 'Домашнее задание'))
        _bullets(doc, homework, s, box=True)

    assessment = str(content.get('assessment') or '').strip()
    if assessment:
        head(L.get('assessment', 'Оценивание'))
        parts_r = re.split(r'[«"]?([2-5])[»"]?\s*[—–-]\s*', assessment)
        marks = [(parts_r[i], parts_r[i + 1].strip().rstrip('.')) for i in range(1, len(parts_r) - 1, 2)]
        if len(marks) >= 2:
            _cards(doc, [(m, d) for m, d in marks[:4]], s, cols=len(marks[:4]), fill='F5F6F8', border=False)
        else:
            text(assessment)

    answers = [str(it.get('answer')) for it in drills if str(it.get('answer') or '').strip()]
    if answers:
        head({'Таджикский': 'Ҷавобҳо', 'English': 'Answers', 'Английский': 'Answers'}.get(language, 'Ответы'))
        _bullets(doc, answers, s)

    summary = str(content.get('summary') or '').strip()
    if summary:
        head(L.get('summary', 'Итоги урока'))
        cells, _ = _grid(doc, 1, 1)
        _clear_cell(cells[0])
        _margins(cells[0], 140, 200)
        _set_cell_shading(cells[0], s.tint)
        _run(_cell_para(cells[0]), summary, s)

    _typeset_math_runs(doc)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
