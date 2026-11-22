"""Test and practical-task .docx — Word twins of assessment_design (the PDF)."""

from __future__ import annotations

import io

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from app.assessment_design import _DOTS, _TAGS, _VARAQ_PALETTE, _VARAQ_UI, LETTERS, _key_answer, _language
from app.docx_builder import (_add_illustration, _add_lesson_image_block, _clear_cell, _set_cell_shading,
                              _typeset_math_runs)
from app.export_builder import CODE_FONT, _PRACTICAL_UI, _format_grade, _test_ui
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


def _varaq_block_body(doc, block: dict, s: _Style, answer: bool, accent: str, tint: str) -> None:
    btype = block.get('type')
    if btype == 'word_bank':
        bank = [str(w) for w in (block.get('word_bank') or [])]
        correct = [str(w) for w in (block.get('correct') or [])]
        if answer:
            _run(_para(doc, after=6), ', '.join(correct) or '—', s, s.size, False, accent)
            return
        if not bank:
            return
        cells, _ = _grid(doc, len(bank), min(4, len(bank)), 0.2)
        for cell, word in zip(cells, bank):
            _clear_cell(cell)
            _margins(cell, 70, 100)
            _set_cell_shading(cell, tint)
            _borders(cell, accent, '6')
            _run(_cell_para(cell, 0), word, s, s.size, False, INK)
        return
    if btype == 'cloze':
        text = str(block.get('text') or '')
        blanks = [str(b) for b in (block.get('blanks') or [])]
        p = _para(doc, after=6)
        if not answer:
            _run(p, text, s)
            return
        rest = text
        for i, b in enumerate(blanks, 1):
            marker = f'___({i})___'
            before_part, _, rest = rest.partition(marker)
            _run(p, before_part, s)
            _run(p, b, s, s.size, True, accent)
        _run(p, rest, s)
        return
    if btype == 'matching':
        left = [str(x) for x in (block.get('left') or [])]
        right = [str(x) for x in (block.get('right') or [])]
        pairs = {int(pr[0]): int(pr[1]) for pr in (block.get('correct_pairs') or [])
                 if isinstance(pr, (list, tuple)) and len(pr) == 2}
        for i, item in enumerate(left):
            p = _para(doc, after=3)
            _run(p, f'{i + 1}.  ', s, s.size, True, accent)
            if answer and i in pairs:
                _run(p, f'{LETTERS[pairs[i]]}  ', s, s.size, True, accent)
            else:
                _run(p, '[   ]  ', s, s.size, False, MUTED)
            _run(p, item, s)
        for j, item in enumerate(right):
            p = _para(doc, after=3)
            p.paragraph_format.left_indent = Cm(0.6)
            _run(p, f'{LETTERS[j]})  ', s, s.size, True, accent)
            _run(p, item, s)
        return
    if btype == 'table_fill':
        headers = [str(h) for h in (block.get('headers') or [])]
        rows = block.get('answer_rows') if answer else block.get('rows')
        rows = [[str(c) if str(c).strip() else '' for c in r] for r in (rows or []) if isinstance(r, (list, tuple))]
        if not headers or not rows:
            return
        t = doc.add_table(rows=len(rows) + 1, cols=len(headers))
        t.autofit = False
        _fix_widths(t, [WIDTH_CM / len(headers)] * len(headers))
        for c, label in enumerate(headers):
            cell = t.cell(0, c)
            _clear_cell(cell)
            _set_cell_shading(cell, accent)
            _run(_cell_para(cell, 0), label, s, s.size - 1, True, 'FFFFFF')
        for r, row in enumerate(rows, 1):
            for c, val in enumerate(row):
                cell = t.cell(r, c)
                _clear_cell(cell)
                _borders(cell, 'D5DCE5', '4')
                if r % 2 == 1:
                    _set_cell_shading(cell, tint)
                _run(_cell_para(cell, 0), val, s, s.size - 1, False, INK)
        _para(doc, after=6)
        return
    if btype == 'code_trace':
        code = str(block.get('code') or '')
        question = str(block.get('question') or '')
        if code:
            cells, _ = _grid(doc, 1, 1, 0.2)
            cell = cells[0]
            _clear_cell(cell)
            _margins(cell, 120, 140)
            _set_cell_shading(cell, '1E293B')
            lines = code.split('\n')
            p = _cell_para(cell, 0)
            for i, line in enumerate(lines):
                r = p.add_run(line if i == 0 else '\n' + line)
                r.font.name = CODE_FONT
                r.font.size = Pt(9)
                r.font.color.rgb = _rgb('E2E8F0')
            _para(doc, after=4)
        p = _para(doc, after=6)
        _run(p, question, s)
        if answer:
            _run(p, f'  {block.get("answer") or ""}', s, s.size, True, accent)
        else:
            _run(p, '  ______________', s, s.size, False, MUTED)
        return
    if btype == 'diagram_label':
        labels = [str(x) for x in (block.get('labels') or [])]
        img_path = block.get('image')
        if img_path:
            _add_illustration(doc, img_path, '', '', width_inches=2.6)
        p = _para(doc, after=6)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for i, d in enumerate(('N', 'E', 'S', 'W')):
            _run(p, f'{d}: ', s, s.size, True, INK)
            if answer and i < len(labels):
                _run(p, f'{labels[i]}   ', s, s.size, True, accent)
            else:
                _run(p, '______   ', s, s.size, False, MUTED)
        return
    if btype == 'picture_order':
        items = [it for it in (block.get('items') or []) if isinstance(it, dict)]
        correct_order = block.get('correct_order') or []
        for i, item in enumerate(items):
            img_path = (item.get('image') or {}).get('path')
            if img_path:
                _add_illustration(doc, img_path, '', '', width_inches=1.8)
            p = _para(doc, after=8)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            num = str(correct_order[i]) if (answer and i < len(correct_order)) else '[   ]'
            _run(p, num, s, s.size, True, accent if answer else MUTED)
        return


def build_varaq(content: dict) -> io.BytesIO:
    language = _language(content)
    s = _Style('general', language)
    tags = _TAGS.get(language, _TAGS['Русский'])
    vui = _VARAQ_UI.get(language, _VARAQ_UI['Русский'])
    blocks = [b for b in (content.get('blocks') or []) if isinstance(b, dict)]
    doc, _ = _start(content, tags['varaq'], tags['blocks'], len(blocks), s)

    for i, block in enumerate(blocks, 1):
        accent, tint = (c.lstrip('#') for c in _VARAQ_PALETTE[(i - 1) % len(_VARAQ_PALETTE)])
        p = _para(doc, after=4, before=10)
        p.paragraph_format.keep_with_next = True
        _run(p, f'{i}.  ', s, s.size + 0.5, True, accent, s.head)
        _run(p, str(block.get('instructions') or ''), s, s.size + 0.5, True, INK, s.head)
        if block.get('type') == 'word_bank':
            _run(_para(doc, after=4), vui['word_bank'].upper(), s, 7.5, True, accent)
        _varaq_block_body(doc, block, s, answer=False, accent=accent, tint=tint)

    key_blocks = [b for b in blocks if b.get('type') in (
        'word_bank', 'cloze', 'matching', 'table_fill', 'code_trace', 'diagram_label', 'picture_order')]
    if key_blocks:
        doc.add_page_break()
        _run(_para(doc, after=2), vui['key_title'].capitalize(), s, 18, False, INK, s.head)
        _run(_para(doc, after=8), vui['key_hint'], s, s.size - 1.5, False, MUTED)
        for i, block in enumerate(blocks, 1):
            accent, tint = (c.lstrip('#') for c in _VARAQ_PALETTE[(i - 1) % len(_VARAQ_PALETTE)])
            p = _para(doc, after=3, before=6)
            p.paragraph_format.keep_with_next = True
            _run(p, f'{i}. ', s, s.size, True, accent)
            _run(p, vui['block'], s, s.size, True, accent)
            _varaq_block_body(doc, block, s, answer=True, accent=accent, tint=tint)

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
