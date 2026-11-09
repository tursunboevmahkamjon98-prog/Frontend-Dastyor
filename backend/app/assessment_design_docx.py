"""Test and practical-task .docx — Word twins of assessment_design (the PDF)."""

from __future__ import annotations

import io

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm

from app.assessment_design import _DOTS, _TAGS, LETTERS, _key_answer, _language
from app.docx_builder import (_add_lesson_image_block, _clear_cell, _set_cell_shading,
                              _typeset_math_runs)
from app.export_builder import _PRACTICAL_UI, _format_grade, _test_ui
from app.konspekt_design_docx import (INK, MUTED, WIDTH_CM, _borders, _cell_para, _fix_widths, _grid,
                                      _heading, _margins, _para, _rgb, _run, _Style, header,
                                      new_doc)
from app.lecture_builder import _words


def _answer_lines(doc, count: int = 3) -> None:
    """Writing lines as table rows: Word merges the borders of identical
    consecutive paragraphs into one, so paragraph rules would show a single line."""
    t = doc.add_table(rows=count, cols=2)
    t.autofit = False
    _fix_widths(t, [0.8, WIDTH_CM - 0.8])
    for r in range(count):
        t.rows[r].height = Cm(0.85)
        line = t.cell(r, 1)
        tcPr = line._element.get_or_add_tcPr()
        b = OxmlElement('w:tcBorders')
        e = OxmlElement('w:bottom')
        for k, v in (('w:val', 'single'), ('w:sz', '4'), ('w:space', '0'), ('w:color', 'C9D2DE')):
            e.set(qn(k), v)
        b.append(e)
        tcPr.append(b)
    _para(doc, after=2)


def _start(content: dict, tag: str, count_label: str, count: int, s: _Style):
    language = _language(content)
    w = _words(language)
    ui = _test_ui(language)
    doc = new_doc(content, s)
    grade = str(content.get('grade') or '')
    header(doc, tag, {'title': content.get('title'), 'subtitle': content.get('description')}, [
        (w['subject'], str(content.get('subject') or '')),
        (w['grade_suffix'].capitalize(), _format_grade(grade, w['grade_suffix']) if grade else ''),
        (count_label, str(count)),
        (w['date'], '____________')], s)
    cells, _ = _grid(doc, 1, 1, 0.2)
    cell = cells[0]
    _clear_cell(cell)
    _margins(cell, 120, 180)
    _set_cell_shading(cell, s.tint)
    p = _cell_para(cell, 0)
    _run(p, f"{ui['name']}  ______________________      {ui['klass']}  ________      "
            f"{ui['mark']}  ________", s, s.size - 1, False, MUTED)
    return doc, ui


def build_test(content: dict) -> io.BytesIO:
    s = _Style('general', _language(content))
    tags = _TAGS.get(_language(content), _TAGS['Русский'])
    questions = [q for q in (content.get('questions') or []) if isinstance(q, dict)]
    doc, ui = _start(content, tags['test'], tags['questions'], len(questions), s)
    accent = _rgb(s.accent)
    _run(_para(doc, after=8, before=4), ui['hint'], s, s.size - 1.5, False, MUTED)

    for i, q in enumerate(questions):
        p = _para(doc, after=4, before=8)
        p.paragraph_format.keep_with_next = True
        _run(p, f'{i + 1}.  ', s, s.size + 0.5, True, s.accent)
        _run(p, str(q.get('question') or ''), s, s.size + 0.5, True, INK)
        if q.get('type') == 'multiple_select':
            _run(p, f"  ({ui['select_hint']})", s, s.size - 1.5, False, MUTED)
        img = q.get('image') if isinstance(q.get('image'), dict) else None
        if img and img.get('path'):
            _add_lesson_image_block(doc, img, '', accent)
        if q.get('type') == 'open_ended':
            _answer_lines(doc)
            continue
        options = [str(o) for o in (q.get('options') or [])]
        mark = '[   ] ' if q.get('type') == 'multiple_select' else ''
        for j, opt in enumerate(options):
            op = _para(doc, after=2)
            op.paragraph_format.left_indent = Cm(0.8)
            op.paragraph_format.keep_with_next = j < len(options) - 1
            _run(op, mark, s, s.size, False, MUTED)
            _run(op, f'{LETTERS[j] if j < len(LETTERS) else j + 1})  ', s, s.size, True, s.accent)
            _run(op, opt, s)

    _run(_para(doc, before=12), f"{ui['total']}: {len(questions)}  ·  {ui['max_score']}: {len(questions)}",
         s, s.size - 1.5, False, MUTED)

    if questions:
        doc.add_page_break()
        _run(_para(doc, after=2), ui['key_title'].capitalize(), s, 18, False, INK, s.head)
        _run(_para(doc, after=8), ui['key_hint'], s, s.size - 1.5, False, MUTED)
        t = doc.add_table(rows=len(questions) + 1, cols=3)
        t.autofit = False
        widths = [1.1, 3.8, WIDTH_CM - 4.9]
        _fix_widths(t, widths)
        for c, label in enumerate((ui['col_no'], ui['col_answer'], ui['col_why'])):
            cell = t.cell(0, c)
            _clear_cell(cell)
            _set_cell_shading(cell, s.tint)
            _run(_cell_para(cell, 0), label, s, s.size - 1.5, True, s.accent)
        for r, q in enumerate(questions, 1):
            note = str(q.get('explanation') or '').strip()
            if q.get('type') == 'open_ended' and q.get('model_answer'):
                note = f"{ui['model']}: {q['model_answer']}" + (f'\n{note}' if note else '')
            values = ((str(r), True, INK), (_key_answer(q, ui), True, s.accent), (note, False, MUTED))
            for c, (val, bold, color) in enumerate(values):
                cell = t.cell(r, c)
                _clear_cell(cell)
                _borders(cell, 'D5DCE5', '4')
                _run(_cell_para(cell, 0), val, s, s.size - 1, bold, color)

    _typeset_math_runs(doc)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def build_practical(content: dict) -> io.BytesIO:
    language = _language(content)
    s = _Style('general', language)
    tags = _TAGS.get(language, _TAGS['Русский'])
    pui = _PRACTICAL_UI.get(language, _PRACTICAL_UI['Русский'])
    individual = [t for t in (content.get('individual_tasks') or []) if isinstance(t, dict)]
    group = [t for t in (content.get('group_tasks') or []) if isinstance(t, dict)]
    doc, _ = _start(content, tags['practical'], tags['tasks'], len(individual) + len(group), s)

    def card(n: int, task: dict, is_group: bool) -> None:
        cells, _ = _grid(doc, 1, 1, 0.2)
        cell = cells[0]
        _clear_cell(cell)
        _margins(cell, 140, 200)
        _borders(cell, 'E4E6EB', '6')
        p = _cell_para(cell, 4)
        _run(p, f'{n}.  ', s, s.size + 1.5, False, s.accent, s.head)
        _run(p, str(task.get('title') or ''), s, s.size + 1.5, False, INK, s.head)
        level = str(task.get('difficulty') or '').lower()
        if level in _DOTS:
            _run(p, f"     {_DOTS[level]} {pui['difficulty'].get(level, level)}", s, s.size - 2, False, MUTED)
        if is_group and task.get('group_size'):
            _run(_cell_para(cell, 3), f"{pui['group_size']}: {task['group_size']}", s, s.size - 1.5, True, MUTED)
        _run(_cell_para(cell, 4), str(task.get('instructions') or ''), s)
        roles = [str(r) for r in (task.get('roles') or []) if str(r).strip()]
        if is_group and roles:
            _run(_cell_para(cell, 2), pui['roles'].upper(), s, 7.5, True, s.accent)
            for role in roles:
                _run(_cell_para(cell, 1), f'•  {role}', s, s.size - 0.5)
        if task.get('expected_outcome'):
            _run(_cell_para(cell, 1), pui['outcome'].upper(), s, 7.5, True, s.accent)
            _run(_cell_para(cell, 2), str(task['expected_outcome']), s, s.size - 0.5, False, MUTED)

    n = 0
    for label, tasks, is_group in ((pui['individual'], individual, False), (pui['group'], group, True)):
        if not tasks:
            continue
        n += 1
        _heading(doc, n, label, s)
        for i, task in enumerate(tasks, 1):
            card(i, task, is_group)

    _typeset_math_runs(doc)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
