"""Lecture .docx — Word twin of lecture_design (the PDF), same order and look.

Built from the konspekt Word primitives (konspekt_design_docx) so the
lecture and the konspekt stay one design.
"""

from __future__ import annotations

import io

from app.docx_builder import (_DOCX_LABELS, _add_code_card, _add_concept_card_grid, _add_formula_card,
                              _add_visual_block, _clear_cell,
                              _set_cell_shading, _typeset_math_runs)
from app.export_builder import _format_grade
from app.konspekt_design_docx import (MUTED, _cards, _cell_para, _grid, _heading, _margins, _para,
                                      _rgb, _run, _short, _Style, header, new_doc, side_by_side)
from app.lecture_builder import _split_main_content, _words
from app.lecture_design import _CALLOUTS


def build(content: dict, language: str = 'Русский') -> io.BytesIO:
    w = _words(language)
    s = _Style('general', language)
    accent = _rgb(s.accent)
    labels = _DOCX_LABELS.get(language, _DOCX_LABELS['Русский'])
    doc = new_doc(content, s)

    grade = str(content.get('grade') or '')
    header(doc, w['tag'], content, [
        (w['subject'], str(content.get('subject') or '')),
        (w['grade_suffix'].capitalize(), _format_grade(grade, w['grade_suffix']) if grade else ''),
        (w['duration'], str(content.get('duration') or '').strip() or w['duration_value']),
        (w['date'], '____________')], s)

    n = [0]

    def head(label: str) -> None:
        n[0] += 1
        _heading(doc, n[0], label, s)

    def text(container, t: str, cell: bool = False) -> None:
        p = _cell_para(container, 5) if cell else _para(container, after=5)
        _run(p, t, s)

    def numbered(container, items: list) -> None:
        for i, it in enumerate(items, 1):
            p = _cell_para(container, 3)
            _run(p, f'{i:02d}  ', s, s.size, True, s.accent)
            _run(p, it, s)

    # goal | plan
    objective = str(content.get('objective') or '').strip()
    plan = _short(content.get('lecture_plan'))
    if objective and plan:
        n[0] = side_by_side(doc, [(w['objective'], lambda c: text(c, objective, cell=True)),
                                  (w['plan'], lambda c: numbered(c, plan))], n[0], s)
    elif objective:
        head(w['objective'])
        text(doc, objective)
    elif plan:
        head(w['plan'])
        numbered(doc, plan)

    # concepts and terms
    concepts = _short(content.get('key_concepts')) + _short(content.get('key_terms'))
    if concepts or content.get('concept_cards'):
        head(w['concepts'])
        if concepts:
            _cards(doc, concepts, s)
        if content.get('concept_cards'):
            _add_concept_card_grid(doc, content['concept_cards'], accent)

    # body
    parts = _split_main_content(content.get('main_content'))
    # No pictures in a lecture (see lecture_design).
    visuals = list(content.get('visual_blocks') or [])
    if parts:
        head(w['body'])
        for i, (sub, paragraphs) in enumerate(parts):
            if sub:
                _run(_para(doc, after=3, before=6), sub, s, s.size + 1.5, True, s.accent, s.head)
            for t in paragraphs:
                text(doc, t)
            if visuals and i % 2 == 1:
                _add_visual_block(doc, visuals.pop(0), accent, labels)
        for block in visuals:
            _add_visual_block(doc, block, accent, labels)
        for f in content.get('formulas') or []:
            if isinstance(f, dict) and (f.get('formula') or f.get('latex')):
                _add_formula_card(doc, str(f.get('formula') or f.get('latex')),
                                  str(f.get('explanation') or ''), accent)
        for cb in content.get('code_blocks') or []:
            if isinstance(cb, dict) and cb.get('code'):
                _add_code_card(doc, cb.get('code', ''), cb.get('language', ''),
                               cb.get('explanation', ''), accent)

    # main points
    callouts = [(w[kind], t) for field, kind, limit in _CALLOUTS
                for t in _short(content.get(field))[:limit]]
    if callouts:
        cells, spare = _grid(doc, len(callouts), 2)
        for cell, (label, body) in zip(cells, callouts):
            _clear_cell(cell)
            _margins(cell)
            _set_cell_shading(cell, s.tint)
            _run(_cell_para(cell), label, s, 7.5, True, s.accent)
            _run(_cell_para(cell), body, s, s.size - 0.5)
        for cell in spare:
            _clear_cell(cell)

    # self-check | conclusions
    checks = [q for q in (content.get('quick_check') or []) if isinstance(q, dict) and q.get('question')]
    summary = str(content.get('summary') or '').strip()

    def fill_checks(container):
        for k, q in enumerate(checks):
            _run(_cell_para(container, 0), f"{k + 1}. {q['question']}", s)
            if q.get('answer'):
                _run(_cell_para(container, 4), f"{w['answer']}: {q['answer']}", s, s.size - 1.5,
                     False, MUTED)

    def fill_summary(container):
        p = _cell_para(container, 2)
        _run(p, summary, s)

    if checks and summary:
        n[0] = side_by_side(doc, [(w['selfcheck'], fill_checks), (w['summary'], fill_summary)], n[0], s)
    elif checks:
        head(w['selfcheck'])
        fill_checks(doc)
    elif summary:
        head(w['summary'])
        cells, _ = _grid(doc, 1, 1)
        _clear_cell(cells[0])
        _margins(cells[0], 140, 200)
        _set_cell_shading(cells[0], s.tint)
        fill_summary(cells[0])

    references = _short(content.get('references'))
    if references:
        head(w['references'])
        for i, r in enumerate(references, 1):
            _run(_para(doc, after=2), f'{i}. {r}', s, s.size - 1, False, MUTED)

    _typeset_math_runs(doc)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
