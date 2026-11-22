"""Test and practical-task PDFs in the formal design shared with the konspekt.

Both are pupil handouts, so after the common header comes a shaded row for
the pupil's name, class, date and mark. A test then lists its questions
(short options side by side, open questions with answer lines) and ends
with the teacher's answer key on its own page. Practical tasks are cards:
individual tasks first, then group tasks with group size and roles.
"""

from __future__ import annotations

import io

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, KeepTogether, PageBreak, Spacer, Table, TableStyle

from app.export_builder import (CODE_FONT, FONT_NAME, FONT_NAME_BOLD, Paragraph, _PRACTICAL_UI,
                                _format_grade, _math_inline, _pdf_illustration_image, _test_ui)
from app.konspekt_design import (INK, LINE, MUTED, WIDTH, _box, _grid, _section, _Style, header,
                                 new_doc)
from app.lecture_builder import _words

LETTERS = 'ABCDEF'

# A worksheet is a handout for a child, not an exam — each block gets its own
# colour from this wheel (cycling by block index) instead of one muted
# subject accent, so the page reads as playful cards rather than a form.
_VARAQ_PALETTE = [
    ('#2563EB', '#DBEAFE'), ('#EA580C', '#FFEDD5'), ('#059669', '#D1FAE5'),
    ('#9333EA', '#F3E8FF'), ('#DB2777', '#FCE7F3'), ('#0891B2', '#CFFAFE'),
]


class _Badge(Flowable):
    """A small filled circle with a centered number/letter."""

    def __init__(self, text: str, fill: str, text_color: str, font: str, d: float = 20):
        super().__init__()
        self.text, self.fill, self.text_color, self.font, self.d = str(text), fill, text_color, font, d
        self.width = self.height = d

    def draw(self):
        c = self.canv
        c.setFillColor(HexColor(self.fill))
        c.circle(self.d / 2, self.d / 2, self.d / 2, stroke=0, fill=1)
        c.setFillColor(HexColor(self.text_color))
        c.setFont(self.font, self.d * 0.46)
        c.drawCentredString(self.d / 2, self.d / 2 - self.d * 0.17, self.text)

_TAGS = {
    'Русский': dict(test='ТЕСТ', practical='ПРАКТИЧЕСКИЕ ЗАДАНИЯ', questions='Вопросов',
                    tasks='Заданий', varaq='РАБОЧИЙ ЛИСТ', blocks='Заданий'),
    'Таджикский': dict(test='ТЕСТ', practical='АМАЛӢ СУПОРИШҲО', questions='Саволҳо',
                       tasks='Супоришҳо', varaq='ВАРАҚИ КОРӢ', blocks='Супоришҳо'),
    'English': dict(test='TEST', practical='PRACTICAL TASKS', questions='Questions',
                    tasks='Tasks', varaq='WORKSHEET', blocks='Tasks'),
}
_TAGS['Английский'] = _TAGS['English']

_VARAQ_UI = {
    'Русский': dict(instructions='Задание', word_bank='Банк слов', key_title='Ключ ответов',
                    key_hint='Правильные ответы для учителя.', correct='Правильно', block='Задание'),
    'Таджикский': dict(instructions='Супориш', word_bank='Бонки калимаҳо', key_title='Калиди ҷавобҳо',
                       key_hint='Ҷавобҳои дуруст барои омӯзгор.', correct='Дуруст', block='Супориш'),
    'English': dict(instructions='Task', word_bank='Word bank', key_title='Answer key',
                    key_hint='Correct answers for the teacher.', correct='Correct', block='Task'),
}
_VARAQ_UI['Английский'] = _VARAQ_UI['English']

# Difficulty as filled dots instead of green/amber/red badges.
_DOTS = {'easy': '●○○', 'medium': '●●○', 'hard': '●●●'}


def _language(content: dict) -> str:
    return str(content.get('language') or 'Русский')


def _start(content: dict, tag: str, count_label: str, count: int, s: _Style):
    """Header with meta cells, then the shaded pupil row."""
    language = _language(content)
    w = _words(language)
    ui = _test_ui(language)
    grade = str(content.get('grade') or '')
    head_content = {'title': content.get('title'), 'subtitle': content.get('description')}
    story = header(tag, head_content, [
        (w['subject'], str(content.get('subject') or '')),
        (w['grade_suffix'].capitalize(), _format_grade(grade, w['grade_suffix']) if grade else ''),
        (count_label, str(count)),
        (w['date'], '____________')], s)
    line = '<font color="#9AA6B6">' + '_' * 22 + '</font>'
    short = '<font color="#9AA6B6">' + '_' * 8 + '</font>'
    cells = [Paragraph(f"{ui['name']}&nbsp;&nbsp;{line}", s.p(9.5, color=MUTED)),
             Paragraph(f"{ui['klass']}&nbsp;&nbsp;{short}", s.p(9.5, color=MUTED)),
             Paragraph(f"{ui['mark']}&nbsp;&nbsp;{short}", s.p(9.5, color=MUTED))]
    row = Table([cells], colWidths=[WIDTH * 0.56, WIDTH * 0.22, WIDTH * 0.22])
    row.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), HexColor(s.tint)),
                             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                             ('LEFTPADDING', (0, 0), (-1, -1), 10),
                             ('TOPPADDING', (0, 0), (-1, -1), 9),
                             ('BOTTOMPADDING', (0, 0), (-1, -1), 9)]))
    return story + [row, Spacer(1, 10)], ui


def _answer_lines(count: int = 3) -> Table:
    t = Table([['']] * count, colWidths=[WIDTH - 22], rowHeights=[20] * count)
    t.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), 0.5, HexColor('#C9D2DE'))]))
    t.hAlign = 'RIGHT'
    return t


def _options(q: dict, s: _Style) -> list:
    options = [str(o) for o in (q.get('options') or [])]
    if not options:
        return []
    multi = q.get('type') == 'multiple_select'
    cells = []
    for j, opt in enumerate(options):
        letter = LETTERS[j] if j < len(LETTERS) else str(j + 1)
        mark = '<font color="#9AA6B6">[&nbsp;&nbsp;&nbsp;]</font>&nbsp;' if multi else ''
        cells.append(Paragraph(f'{mark}<font color="{s.accent}"><b>{letter})</b></font>&nbsp;&nbsp;'
                               + _math_inline(opt, size=s.size), s.p(after=0)))
    # short options sit two per row, long ones one per row
    cols = 2 if max(len(o) for o in options) <= 38 and len(options) > 2 else 1
    t = _grid(cells, cols, WIDTH - 22, gap=4)
    t.hAlign = 'RIGHT'
    return [t]


def _key_answer(q: dict, ui: dict) -> str:
    options = q.get('options') or []
    kind = q.get('type', 'multiple_choice')
    if kind == 'open_ended':
        return ui['open']
    if kind == 'multiple_select':
        idx = sorted(int(i) for i in (q.get('correct_indices') or [])
                     if isinstance(i, (int, float)) and 0 <= int(i) < len(options))
        return ', '.join(LETTERS[i] for i in idx) if idx else '—'
    i = q.get('correct_index')
    if not isinstance(i, int) or not (0 <= i < len(options)):
        return '—'
    return f'{LETTERS[i]} · {options[i]}' if kind == 'true_false' else LETTERS[i]


def build_test(content: dict, include_key: bool = True, student_only: bool = False) -> io.BytesIO:
    s = _Style('general')
    tags = _TAGS.get(_language(content), _TAGS['Русский'])
    questions = [q for q in (content.get('questions') or []) if isinstance(q, dict)]
    buf = io.BytesIO()
    doc = new_doc(buf, content, s)
    story, ui = _start(content, tags['test'], tags['questions'], len(questions), s)
    story.append(Paragraph(ui['hint'], s.p(9, color=MUTED, after=8)))

    for i, q in enumerate(questions):
        hint = (f' <font color="{MUTED}" size="9">({ui["select_hint"]})</font>'
                if q.get('type') == 'multiple_select' else '')
        block = [Paragraph(f'<font color="{s.accent}"><b>{i + 1}.</b></font>&nbsp;&nbsp;'
                           + _math_inline(str(q.get('question') or ''), size=s.size + 0.5) + hint,
                           s.p(s.size + 0.5, s.bold, INK, leading=(s.size + 0.5) * 1.4, after=5))]
        img = q.get('image') if isinstance(q.get('image'), dict) else None
        if img and img.get('path'):
            block += _pdf_illustration_image(img['path'], '', img.get('credit', ''),
                                             max_w=200, max_h=140) or []
        if q.get('type') == 'open_ended':
            block.append(_answer_lines(3))
        else:
            block += _options(q, s)
        story += [KeepTogether(block), Spacer(1, 12)]

    story.append(Paragraph(f"{ui['total']}: {len(questions)}&nbsp;&nbsp;·&nbsp;&nbsp;"
                           f"{ui['max_score']}: {len(questions)}", s.p(9, color=MUTED)))

    if include_key and not student_only and questions:
        story += [PageBreak(), Paragraph(ui['key_title'].capitalize(), s.p(18, s.head, INK, 23, after=2)),
                  Paragraph(ui['key_hint'], s.p(9, color=MUTED, after=10))]
        head = s.p(9, s.bold, s.accent)
        rows = [[Paragraph(ui['col_no'], head), Paragraph(ui['col_answer'], head),
                 Paragraph(ui['col_why'], head)]]
        for i, q in enumerate(questions):
            note = _math_inline(str(q.get('explanation') or '').strip(), size=9)
            if q.get('type') == 'open_ended' and q.get('model_answer'):
                model = _math_inline(str(q['model_answer']).strip(), size=9)
                note = f"<b>{ui['model']}:</b> {model}" + (f'<br/>{note}' if note else '')
            rows.append([Paragraph(str(i + 1), s.p(10, s.bold)),
                         Paragraph(_key_answer(q, ui), s.p(10, s.bold, s.accent)),
                         Paragraph(note or '&nbsp;', s.p(9, color=MUTED))])
        key = Table(rows, colWidths=[30, 110, WIDTH - 140], repeatRows=1)
        key.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(s.tint)),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, HexColor('#D5DCE5')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(key)

    doc.build(story)
    buf.seek(0)
    return buf


def _task_card(n: int, task: dict, pui: dict, s: _Style, group: bool) -> Table:
    """One bordered task card."""
    level = str(task.get('difficulty') or '').lower()
    title = (f'<font color="{s.accent}">{n}.</font>&nbsp;&nbsp;'
             + _math_inline(str(task.get('title') or ''), size=s.size + 1.5))
    head_cells = [Paragraph(title, s.p(s.size + 1.5, s.head, INK, after=0))]
    widths = [WIDTH - 20]
    if level in _DOTS:
        label = pui['difficulty'].get(level, level)
        head_cells.append(Paragraph(f'<font color="{s.accent}">{_DOTS[level]}</font> {label}',
                                    s.p(8.5, color=MUTED)))
        widths = [WIDTH - 20 - 90, 90]
    top = Table([head_cells], colWidths=widths)
    top.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                             ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                             ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    body = [top]
    if group and task.get('group_size'):
        body.append(Paragraph(f"{pui['group_size']}: {task['group_size']}", s.p(9, s.bold, MUTED, after=3)))
    body.append(Paragraph(_math_inline(str(task.get('instructions') or ''), size=s.size), s.p(after=4)))
    roles = [str(r) for r in (task.get('roles') or []) if str(r).strip()]
    if group and roles:
        body.append(Paragraph(pui['roles'].upper(), s.p(7.5, s.bold, s.accent, 10, after=2)))
        body += [Paragraph(f'•&nbsp;&nbsp;{_math_inline(r, size=s.size - 0.5)}', s.p(s.size - 0.5, after=1))
                 for r in roles]
    if task.get('expected_outcome'):
        body.append(Spacer(1, 4))
        body.append(_box([Paragraph(pui['outcome'].upper(), s.p(7.5, s.bold, s.accent, 10, after=2)),
                          Paragraph(_math_inline(str(task['expected_outcome']), size=s.size - 0.5),
                                    s.p(s.size - 0.5))], bg=s.tint, pad=6))
    return _box(body, border=LINE, pad=10)


def _task_section(n: int, label: str, tasks: list, pui: dict, s: _Style, group: bool) -> list:
    cards = [_task_card(i, t, pui, s, group) for i, t in enumerate(tasks, 1)]
    # the heading travels with its first card, never alone at the foot of a page
    out = [KeepTogether([_section(n, label, s, WIDTH), cards[0], Spacer(1, 9)])]
    for card in cards[1:]:
        out += [KeepTogether([card, Spacer(1, 9)])]
    return out + [Spacer(1, 6)]


def _varaq_code_card(code: str, language: str, accent_hex: str, width: float) -> list:
    escaped = (
        str(code).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')
    )
    badge_style = ParagraphStyle(name=f'VBadge_{abs(hash(code)) % 100000}', fontName=FONT_NAME_BOLD,
                                 fontSize=8, textColor=HexColor('#FFFFFF'))
    code_style = ParagraphStyle(name=f'VCode_{abs(hash(code)) % 100000}', fontName=CODE_FONT,
                                fontSize=9, leading=13, textColor=HexColor('#E2E8F0'))
    t = Table([[Paragraph((language or 'code').upper(), badge_style)], [Paragraph(escaped, code_style)]],
              colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), HexColor(accent_hex)),
        ('BACKGROUND', (0, 1), (0, 1), HexColor('#1E293B')),
        ('TOPPADDING', (0, 0), (0, 0), 3), ('BOTTOMPADDING', (0, 0), (0, 0), 3),
        ('LEFTPADDING', (0, 0), (0, 0), 10), ('RIGHTPADDING', (0, 0), (0, 0), 8),
        ('TOPPADDING', (0, 1), (0, 1), 8), ('BOTTOMPADDING', (0, 1), (0, 1), 8),
        ('LEFTPADDING', (0, 1), (0, 1), 10), ('RIGHTPADDING', (0, 1), (0, 1), 8),
    ]))
    return [t]


def _varaq_block_body(block: dict, s: _Style, vui: dict, answer: bool, accent: str, tint: str) -> list:
    """Render one worksheet block — student version by default, answer-key
    version (answer=True) shows the correct answer inline instead of blanks."""
    btype = block.get('type')
    out = []
    if btype == 'word_bank':
        bank = [str(w) for w in (block.get('word_bank') or [])]
        correct = [str(w) for w in (block.get('correct') or [])]
        if answer:
            out.append(Paragraph(', '.join(correct) or '&nbsp;', s.p(after=0, color=accent)))
            return out
        cells = [_box(Paragraph(_math_inline(w, size=s.size), s.p(after=0)), bg=tint, border=accent, pad=6, radius=8)
                 for w in bank]
        if cells:
            out.append(_grid(cells, min(4, max(1, len(cells))), WIDTH - 22, gap=6))
        return out
    if btype == 'cloze':
        text = str(block.get('text') or '')
        blanks = [str(b) for b in (block.get('blanks') or [])]
        if answer:
            for i, b in enumerate(blanks, 1):
                text = text.replace(f'___({i})___', f'<b><font color="{accent}">{b}</font></b>', 1)
        out.append(Paragraph(_math_inline(text, size=s.size), s.p(leading=s.size * 1.6)))
        return out
    if btype == 'matching':
        left = [str(x) for x in (block.get('left') or [])]
        right = [str(x) for x in (block.get('right') or [])]
        pairs = {int(p[0]): int(p[1]) for p in (block.get('correct_pairs') or [])
                 if isinstance(p, (list, tuple)) and len(p) == 2}
        left_cells, right_cells = [], []
        for i, item in enumerate(left):
            ans = f'<font color="{accent}"><b>{LETTERS[pairs[i]]}</b></font>&nbsp;&nbsp;' if (answer and i in pairs) else '[&nbsp;&nbsp;&nbsp;]&nbsp;&nbsp;'
            left_cells.append(Paragraph(f'<font color="{accent}"><b>{i + 1}.</b></font>&nbsp;{ans}' + _math_inline(item, size=s.size), s.p(after=4)))
        for j, item in enumerate(right):
            right_cells.append(Paragraph(f'<font color="{accent}"><b>{LETTERS[j]})</b></font>&nbsp;&nbsp;' + _math_inline(item, size=s.size),
                                         s.p(after=4)))
        t = Table([[left_cells, right_cells]], colWidths=[(WIDTH - 22) * 0.52, (WIDTH - 22) * 0.48])
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        out.append(t)
        return out
    if btype == 'table_fill':
        headers = [str(h) for h in (block.get('headers') or [])]
        rows = block.get('answer_rows') if answer else block.get('rows')
        rows = [[str(c) if str(c).strip() else '&nbsp;' for c in r] for r in (rows or []) if isinstance(r, (list, tuple))]
        if not headers or not rows:
            return out
        head = s.p(9, s.bold, '#FFFFFF')
        data = [[Paragraph(h, head) for h in headers]] + \
               [[Paragraph(c, s.p(9.5)) for c in r] for r in rows]
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(accent)),
            ('BOX', (0, 0), (-1, -1), 0.6, HexColor(accent)),
            ('INNERGRID', (0, 0), (-1, -1), 0.6, HexColor(LINE)),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]
        for r in range(1, len(rows) + 1, 2):
            style.append(('BACKGROUND', (0, r), (-1, r), HexColor(tint)))
        t = Table(data, colWidths=[(WIDTH - 22) / len(headers)] * len(headers), repeatRows=1)
        t.setStyle(TableStyle(style))
        out.append(t)
        return out
    if btype == 'code_trace':
        code = str(block.get('code') or '')
        question = str(block.get('question') or '')
        if code:
            out += _varaq_code_card(code, str(block.get('language') or ''), accent, WIDTH - 22)
            out.append(Spacer(1, 6))
        if answer:
            out.append(Paragraph(f'{question}&nbsp;&nbsp;<font color="{accent}"><b>{block.get("answer") or ""}</b></font>',
                                 s.p(after=0)))
        else:
            out.append(Paragraph(f'{question}&nbsp;&nbsp;<font color="{MUTED}">______________</font>', s.p(after=0)))
        return out
    if btype == 'diagram_label':
        labels = [str(x) for x in (block.get('labels') or [])]
        img_path = block.get('image')
        if img_path:
            img = _pdf_illustration_image(img_path, '', '', max_w=220, max_h=220)
            if img:
                out += img
        lines = []
        for i, d in enumerate(('N', 'E', 'S', 'W')):
            ans = (f'<font color="{accent}"><b>{labels[i]}</b></font>' if (answer and i < len(labels))
                   else f'<font color="{MUTED}">______</font>')
            lines.append(f'{d}: {ans}')
        out.append(Paragraph('&nbsp;&nbsp;&nbsp;'.join(lines), s.p(after=0, align=TA_CENTER)))
        return out
    if btype == 'picture_order':
        items = [it for it in (block.get('items') or []) if isinstance(it, dict)]
        correct_order = block.get('correct_order') or []
        cells = []
        for i, item in enumerate(items):
            img_path = (item.get('image') or {}).get('path')
            cell = []
            if img_path:
                img = _pdf_illustration_image(img_path, '', '', max_w=110, max_h=90)
                if img:
                    cell += img
            num = str(correct_order[i]) if (answer and i < len(correct_order)) else ''
            order_text = (f'<font color="{accent}"><b>{num}</b></font>' if answer
                          else f'<font color="{MUTED}">[&nbsp;&nbsp;]</font>')
            cell.append(Paragraph(order_text, s.p(after=0, align=TA_CENTER)))
            cells.append(_box(cell, border=accent, pad=6, radius=6))
        if cells:
            out.append(_grid(cells, min(4, max(1, len(cells))), WIDTH - 22, gap=8))
        return out
    return out


def _varaq_block_card(n: int, block: dict, s: _Style, vui: dict) -> Table:
    """A card with a SOLID colour header bar (badge + instructions in white)
    over a white body — the look from the reference worksheets, not just a
    coloured outline."""
    accent, tint = _VARAQ_PALETTE[(n - 1) % len(_VARAQ_PALETTE)]
    instructions = _math_inline(str(block.get('instructions') or ''), size=s.size + 0.5)
    badge = _Badge(str(n), '#FFFFFF', accent, s.bold, d=22)
    header = Table([[badge, Paragraph(instructions, s.p(s.size + 0.5, s.bold, '#FFFFFF', leading=(s.size + 0.5) * 1.4))]],
                   colWidths=[30, WIDTH - 24 - 30])
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    body = []
    if block.get('type') == 'word_bank':
        body.append(Paragraph(vui['word_bank'].upper(), s.p(7.5, s.bold, accent, 10, after=4)))
    body += _varaq_block_body(block, s, vui, answer=False, accent=accent, tint=tint)

    card = Table([[header], [body]], colWidths=[WIDTH - 24])
    card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), HexColor(accent)),
        ('BACKGROUND', (0, 1), (0, 1), HexColor('#FFFFFF')),
        ('BOX', (0, 0), (-1, -1), 1.1, HexColor(accent)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 12), ('RIGHTPADDING', (0, 0), (0, 0), 12),
        ('TOPPADDING', (0, 0), (0, 0), 9), ('BOTTOMPADDING', (0, 0), (0, 0), 9),
        ('LEFTPADDING', (0, 1), (0, 1), 12), ('RIGHTPADDING', (0, 1), (0, 1), 12),
        ('TOPPADDING', (0, 1), (0, 1), 11), ('BOTTOMPADDING', (0, 1), (0, 1), 11),
    ]))
    return card


def build_varaq(content: dict) -> io.BytesIO:
    s = _Style('general')
    language = _language(content)
    tags = _TAGS.get(language, _TAGS['Русский'])
    vui = _VARAQ_UI.get(language, _VARAQ_UI['Русский'])
    blocks = [b for b in (content.get('blocks') or []) if isinstance(b, dict)]
    buf = io.BytesIO()
    doc = new_doc(buf, content, s)
    story, _ = _start(content, tags['varaq'], tags['blocks'], len(blocks), s)

    cards = [_varaq_block_card(i, b, s, vui) for i, b in enumerate(blocks, 1)]
    for card in cards:
        story += [KeepTogether([card, Spacer(1, 9)])]

    key_blocks = [b for b in blocks if b.get('type') in (
        'word_bank', 'cloze', 'matching', 'table_fill', 'code_trace', 'diagram_label', 'picture_order')]
    if key_blocks:
        story += [PageBreak(), Paragraph(vui['key_title'].capitalize(), s.p(18, s.head, INK, 23, after=2)),
                  Paragraph(vui['key_hint'], s.p(9, color=MUTED, after=10))]
        for i, b in enumerate(blocks, 1):
            accent, tint = _VARAQ_PALETTE[(i - 1) % len(_VARAQ_PALETTE)]
            label = f"<b>{i}.</b> {vui['block']}"
            entry = [Paragraph(label, s.p(10, s.bold, accent, after=3))]
            entry += _varaq_block_body(b, s, vui, answer=True, accent=accent, tint=tint)
            story += [KeepTogether(entry + [Spacer(1, 8)])]

    doc.build(story)
    buf.seek(0)
    return buf


def build_practical(content: dict) -> io.BytesIO:
    s = _Style('general')
    language = _language(content)
    tags = _TAGS.get(language, _TAGS['Русский'])
    pui = _PRACTICAL_UI.get(language, _PRACTICAL_UI['Русский'])
    individual = [t for t in (content.get('individual_tasks') or []) if isinstance(t, dict)]
    group = [t for t in (content.get('group_tasks') or []) if isinstance(t, dict)]
    buf = io.BytesIO()
    doc = new_doc(buf, content, s)
    story, _ = _start(content, tags['practical'], tags['tasks'], len(individual) + len(group), s)

    n = 0
    if individual:
        n += 1
        story += _task_section(n, pui['individual'], individual, pui, s, group=False)
    if group:
        n += 1
        story += _task_section(n, pui['group'], group, pui, s, group=True)

    doc.build(story)
    buf.seek(0)
    return buf
