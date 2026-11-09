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
from reportlab.platypus import KeepTogether, PageBreak, Spacer, Table, TableStyle

from app.export_builder import (Paragraph, _PRACTICAL_UI, _format_grade, _math_inline,
                                _pdf_illustration_image, _test_ui)
from app.konspekt_design import (INK, LINE, MUTED, WIDTH, _box, _grid, _section, _Style, header,
                                 new_doc)
from app.lecture_builder import _words

LETTERS = 'ABCDEF'

_TAGS = {
    'Русский': dict(test='ТЕСТ', practical='ПРАКТИЧЕСКИЕ ЗАДАНИЯ', questions='Вопросов',
                    tasks='Заданий'),
    'Таджикский': dict(test='ТЕСТ', practical='АМАЛӢ СУПОРИШҲО', questions='Саволҳо',
                       tasks='Супоришҳо'),
    'English': dict(test='TEST', practical='PRACTICAL TASKS', questions='Questions',
                    tasks='Tasks'),
}
_TAGS['Английский'] = _TAGS['English']

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
