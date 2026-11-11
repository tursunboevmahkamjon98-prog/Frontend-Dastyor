"""Lecture PDF in the formal design shared with the konspekt.

Reading order, built for a lecture rather than a lesson plan:

    header (title, subject, grade, duration, date)
    goal | plan                      side by side
    1. key concepts and terms        two-column cards (+ concept cards)
    2. lecture body                  subheads, tables/diagrams, formulas, code (no pictures)
    3. the main points               remember / important / example / tip, in a grid
    4. self-check | 5. conclusions   side by side
    6. references                    small print

Page, header and two-column helpers come from konspekt_design so both
documents stay one design.
"""

from __future__ import annotations

import io

from reportlab.platypus import Spacer

from app.export_builder import (Paragraph, _format_grade, _math_inline, _pdf_code_card,
                                _pdf_concept_card_grid)
from app.konspekt_design import (LINE, MUTED, WIDTH, _box, _cap, _grid_rows, _section, _short,
                                 _Style, header, new_doc, side_by_side)
from app.lecture_builder import (_Design, _formula_block, _split_definition,
                                 _split_main_content, _visual, _words)
from app.lecture_templates import get_lecture_template

_CALLOUTS = (('key_ideas', 'remember', 4), ('important_notes', 'important', 3),
             ('real_life_examples', 'example', 3), ('teacher_tips', 'tip', 3))


def _cards(items: list, s: _Style) -> list:
    out = []
    for it in items:
        term, body = _split_definition(it)
        parts = []
        if term:
            parts.append(Paragraph(term, s.p(s.size, s.head, s.accent, s.size * 1.35)))
        parts.append(Paragraph(_math_inline(_cap(body), size=s.size - 0.5), s.p(s.size - 0.5)))
        out.append(_box(parts, border=LINE))
    return _grid_rows(out, 2, WIDTH) + [Spacer(1, 10)]


def _numbered(items: list, s: _Style) -> list:
    return [Paragraph(f'<font color="{s.accent}"><b>{i:02d}</b></font>&nbsp;&nbsp;'
                      + _math_inline(str(it), size=s.size), s.p(after=3))
            for i, it in enumerate(items, 1)]


def build(content: dict, language: str = 'Русский') -> io.BytesIO:
    w = _words(language)
    s = _Style('general')
    buf = io.BytesIO()
    doc = new_doc(buf, content, s, language)
    helper = _Design(get_lecture_template('planspekt'), s.accent, w)

    grade = str(content.get('grade') or '')
    if grade:
        grade = _format_grade(grade, w['grade_suffix'])
    duration = str(content.get('duration') or '').strip() or w['duration_value']
    story = header(w['tag'], content, [
        (w['subject'], str(content.get('subject') or '')),
        (w['grade_suffix'].capitalize(), grade), (w['duration'], duration),
        (w['date'], '____________')], s)

    n = [0]

    def sec(label: str, width: float = WIDTH) -> list:
        n[0] += 1
        return [_section(n[0], label, s, width)]

    def para(text: str):
        return Paragraph(_math_inline(str(text), size=s.size), s.p(after=5))

    half = WIDTH / 2 - 8

    # goal | plan
    objective = str(content.get('objective') or '').strip()
    plan = _short(content.get('lecture_plan'))
    if objective and plan:
        left = sec(w['objective'], half) + [para(objective)]
        right = sec(w['plan'], half) + _numbered(plan, s)
        story += [side_by_side(left, right), Spacer(1, 12)]
    elif objective:
        story += sec(w['objective']) + [para(objective), Spacer(1, 8)]
    elif plan:
        story += sec(w['plan']) + _numbered(plan, s) + [Spacer(1, 10)]

    # concepts and terms
    concepts = _short(content.get('key_concepts')) + _short(content.get('key_terms'))
    if concepts or content.get('concept_cards'):
        story += sec(w['concepts'])
        if concepts:
            story += _cards(concepts, s)
        if content.get('concept_cards'):
            story += _pdf_concept_card_grid(content['concept_cards'], s.accent)

    # body
    parts = _split_main_content(content.get('main_content'))
    # No pictures in a lecture: Commons images were often off-topic and their
    # odd sizes left large blank gaps. Tables/diagrams (visual_blocks) stay.
    visuals = list(content.get('visual_blocks') or [])
    if parts:
        story += sec(w['body'])
        for i, (head, paragraphs) in enumerate(parts):
            if head:
                story.append(Paragraph(head, s.p(s.size + 1.5, s.head, s.accent, before=6, after=3)))
            story += [para(t) for t in paragraphs]
            # spread the visuals through the text instead of piling them at the end
            if visuals and i % 2 == 1:
                story += _visual(visuals.pop(0), helper)
        for block in visuals:
            story += _visual(block, helper)
        for f in content.get('formulas') or []:
            if isinstance(f, dict):
                story += _formula_block(f, helper)
        for cb in content.get('code_blocks') or []:
            if isinstance(cb, dict) and cb.get('code'):
                story += _pdf_code_card(cb.get('code', ''), cb.get('language', ''),
                                        cb.get('explanation', ''), s.accent)

    # main points
    callouts = []
    for field, kind, limit in _CALLOUTS:
        for text in _short(content.get(field))[:limit]:
            callouts.append(_box([Paragraph(w[kind], s.p(7.5, s.bold, s.accent, 10, after=2)),
                                  Paragraph(_math_inline(text, size=s.size - 0.5), s.p(s.size - 0.5))],
                                 bg=s.tint))
    if callouts:
        story += [Spacer(1, 4)] + _grid_rows(callouts, 2, WIDTH) + [Spacer(1, 10)]

    # self-check | conclusions
    checks = [q for q in (content.get('quick_check') or []) if isinstance(q, dict) and q.get('question')]
    check_rows = []
    for k, q in enumerate(checks):
        check_rows.append(Paragraph(f'{k + 1}. ' + _math_inline(str(q['question']), size=s.size),
                                    s.p(after=0)))
        if q.get('answer'):
            check_rows.append(Paragraph(f"{w['answer']}: " + _math_inline(str(q['answer']),
                                                                            size=s.size - 1.5),
                                        s.p(s.size - 1.5, color=MUTED, after=4)))
    summary = str(content.get('summary') or '').strip()
    summary_box = _box(Paragraph(_math_inline(summary, size=s.size), s.p()), bg=s.tint, pad=10)
    if check_rows and summary:
        left = sec(w['selfcheck'], half) + check_rows
        right = sec(w['summary'], half) + [summary_box]
        story += [side_by_side(left, right), Spacer(1, 12)]
    elif check_rows:
        story += sec(w['selfcheck']) + check_rows + [Spacer(1, 10)]
    elif summary:
        story += sec(w['summary']) + [summary_box, Spacer(1, 10)]

    references = _short(content.get('references'))
    if references:
        story += sec(w['references']) + [Paragraph(f'{i}. {r}', s.p(s.size - 1, color=MUTED, after=2))
                                         for i, r in enumerate(references, 1)]

    doc.build(story)
    buf.seek(0)
    return buf
