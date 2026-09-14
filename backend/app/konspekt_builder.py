# -*- coding: utf-8 -*-
"""The конспект as a finished lesson plan — not a template PDF.

A konspekt used to be rendered by the same body function every document
used before the лекция got its own build this session: a numbered list
of sections, filled cards, no cover a teacher would actually recognise as
"this lesson". lecture_builder.py replaced that for the лекция; this
module gives the конспект the same treatment, reusing that module's
whole design system (five templates, covers, headings, callouts,
definitions, tables) rather than duplicating it — a konspekt and a
lecture are the same kind of object (a plan for one lesson) with a
different field list, not two different kinds of document.

What is deliberately UNCHANGED: the "nakscha" template. It renders the
official Tajik school lesson-plan FORM ("Нақшаи тавзеҳотӣ") — centred
caps title, date/class line, ruled blanks — a document a teacher hands
in, not a design choice. That path (konspekt_templates.plan_layout) still
goes through export_builder.py's _pdf_plan_body, untouched. This module
only handles every other template.
"""
import io
import os

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Frame, KeepTogether, NextPageTemplate, PageBreak, PageTemplate, Spacer, Table, TableStyle
from PIL import Image as PILImage

from app.export_builder import (
    FONT_NAME, FONT_NAME_BOLD, Paragraph, _pdf_illustration_image, _math_inline,
    _pdf_concept_card_grid, _pdf_code_card,
)
from app.lecture_builder import (
    INK, RULE, _Design, _LectureDoc, _COVERS, _HEADINGS, _heading_ghost,
    _CALLOUTS, _callout_card, _DEFINITIONS, _definitions_cards, _uid,
    _tag_for_toc, _split_main_content, _subheading, _plan_block,
    _objective_block, _selfcheck_block, _summary_block, _figure, _visual,
    _pdf_formula_flowable, _plain_to_latex,
)
from app.lecture_templates import get_lecture_template
from app.subject_theme import get_subject_accent_hex
from app.cover_builder import _SUBJECT_ILLUSTRATIONS
from app.logger import get_logger

logger = get_logger(__name__)


# ── words ───────────────────────────────────────────────────────────────
# Matches the vocabulary export_builder.py's _PDF_KONSPEKT_LABELS already
# uses — same words, same document family, no reason for a konspekt built
# by this renderer to name its own sections differently.
L10N = {
    'Русский': {
        'tag': 'КОНСПЕКТ', 'contents': 'Содержание', 'objectives': 'Цели урока',
        'competencies': 'Компетенции', 'concepts': 'Ключевые понятия',
        'terms': 'Словарь урока', 'lesson_program': 'План урока',
        'tools': 'Материалы', 'body': 'Основное содержание',
        'activities': 'Работа на уроке', 'pair_work': 'Работа в парах',
        'group_work': 'Групповая работа', 'consolidation': 'Закрепление',
        'selfcheck': 'Быстрая проверка', 'homework': 'Домашнее задание',
        'assessment': 'Оценивание', 'summary': 'Итоги урока',
        'answer': 'Ответ', 'grade_suffix': 'класс', 'subject': 'Предмет',
        'duration': 'Продолжительность', 'year': 'Учебный год',
        'teacher': 'Преподаватель', 'date': 'Дата', 'name': 'Ф.И.О.',
        'duration_value': '1 урок', 'plan': 'Цели урока', 'objective': 'Цель урока',
        'formulas': 'Формулы', 'scheme': 'Схема / Рисунок',
        'examples': 'Примеры', 'notes': 'Важно',
        'worked_examples': 'Решённые примеры', 'solution': 'Решение',
        'practice_problems': 'Практические задачи', 'answers': 'Ответы', 'code': 'Код',
    },
    'Таджикский': {
        'tag': 'КОНСПЕКТ', 'contents': 'Мундариҷа', 'objectives': 'Мақсадҳои дарс',
        'competencies': 'Салоҳиятҳо', 'concepts': 'Мафҳумҳои асосӣ',
        'terms': 'Луғати дарс', 'lesson_program': 'Барномаи дарс',
        'tools': 'Воситаҳои аёнӣ', 'body': 'Мазмуни асосӣ',
        'activities': 'Кор дар дарс', 'pair_work': 'Кори дунафара',
        'group_work': 'Кори гурӯҳӣ', 'consolidation': 'Мустаҳкамкунӣ',
        'selfcheck': 'Санҷиши зуд', 'homework': 'Супориши хонагӣ',
        'assessment': 'Арзёбӣ', 'summary': 'Хулосаи дарс',
        'answer': 'Ҷавоб', 'grade_suffix': 'синф', 'subject': 'Фан',
        'duration': 'Давомнокӣ', 'year': 'Соли таҳсил',
        'teacher': 'Омӯзгор', 'date': 'Сана', 'name': 'Ном ва насаб',
        'duration_value': '1 дарс', 'plan': 'Мақсадҳои дарс', 'objective': 'Мақсади дарс',
        'formulas': 'Формулаҳо', 'scheme': 'Схема / Расм',
        'examples': 'Мисолҳо', 'notes': 'Муҳим',
        'worked_examples': 'Мисолҳои ҳалшуда', 'solution': 'Ҳал',
        'practice_problems': 'Машқҳои мустақил', 'answers': 'Ҷавобҳо', 'code': 'Код',
    },
    'English': {
        'tag': 'KONSPEKT', 'contents': 'Contents', 'objectives': 'Lesson objectives',
        'competencies': 'Competencies', 'concepts': 'Key concepts',
        'terms': 'Glossary', 'lesson_program': 'Lesson plan',
        'tools': 'Materials', 'body': 'Main content',
        'activities': 'Classroom activities', 'pair_work': 'Pair work',
        'group_work': 'Group work', 'consolidation': 'Consolidation',
        'selfcheck': 'Quick check', 'homework': 'Homework',
        'assessment': 'Assessment', 'summary': 'Summary',
        'answer': 'Answer', 'grade_suffix': 'grade', 'subject': 'Subject',
        'duration': 'Duration', 'year': 'Academic year',
        'teacher': 'Teacher', 'date': 'Date', 'name': 'Name',
        'duration_value': '1 lesson', 'plan': 'Lesson objectives', 'objective': 'Lesson objective',
        'formulas': 'Formulas', 'scheme': 'Diagram / Image',
        'examples': 'Examples', 'notes': 'Important',
        'worked_examples': 'Worked Examples', 'solution': 'Solution',
        'practice_problems': 'Practice Problems', 'answers': 'Answers', 'code': 'Code',
    },
}
L10N['Английский'] = L10N['English']


def _words(language: str) -> dict:
    return L10N.get(str(language or 'Русский'), L10N['Русский'])


def _short_list(items: list) -> list:
    return [str(x).strip() for x in (items or []) if str(x).strip()]


def _trim_chars(text: str, max_chars: int) -> str:
    """Cuts at the last whole word under max_chars, with an ellipsis —
    used for the notebook grid's narrower boxes (see _build_notebook_grid),
    where a full-length key_terms/key_concepts sentence can make a
    two-column box too tall to fit any single page."""
    text = str(text or '').strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(' ', 1)[0]
    return (cut or text[:max_chars]).rstrip('.,;:') + '…'


# ══════════════════════════════════════════════════════════════════════
# NOTEBOOK GRID — the "playful" template's own body, entirely separate
# from the linear section-by-section flow every other template shares.
# Built directly from a real reference photo a teacher sent: a hand-drawn
# Canva-style "КОНСПЕКТ" sheet with colour-labelled ribbon boxes (Цель /
# Ключевые слова / Основная часть / Схема / Формулы / Вывод / Вопросы) on
# ruled notebook paper. True hand-drawn illustration art (the reference's
# globe/books/backpack doodles) is out of reach here — no image-
# generation capability, and fetching a matching public clipart image
# proved too unreliable over this environment's network to depend on
# (confirmed live — see app/image_builder.py's _curl_bytes docstring).
# What's built instead: the real STRUCTURE — coloured ribbon labels,
# ruled-paper background, spiral-notebook margin — from ReportLab
# primitives, plus the app's own existing subject illustration (see
# cover_builder._SUBJECT_ILLUSTRATIONS) standing in for a hand-drawn icon
# where one exists for that subject.
# ══════════════════════════════════════════════════════════════════════

_GRID_W, _GRID_H = A4[0], A4[1]
_GRID_MARGIN = 1.5 * cm
# Same soft pastel/dark pairs as the presentation deck's own "playful"
# theme (see export_builder.py's _PLAYFUL_PALETTE) and the cover's own
# _NOTEBOOK_PALETTE — one consistent colour family across every document
# a teacher generates for the same lesson.
_GRID_COLORS = [
    ('#BFDBFE', '#1D4ED8'), ('#BBF7D0', '#15803D'), ('#DDD6FE', '#6D28D9'),
    ('#FBCFE8', '#BE185D'), ('#FDE68A', '#926B00'),
]
_GRID_PAPER = HexColor('#FFFDF7')


def _paint_notebook_chrome(canvas_obj, doc_obj, content: dict, accent: str) -> None:
    """Ruled paper + spiral-hole margin, drawn on the raw canvas so it
    sits BEHIND every flowable — the reportlab equivalent of
    export_builder.py's _pptx_notebook_lines/_pptx_spiral_margin, same
    visual identity carried into the PDF world's own coordinate system
    (points, y-up from the bottom, instead of pptx's inches/y-down)."""
    canvas_obj.saveState()
    canvas_obj.setStrokeColor(HexColor('#EEE4C8'))
    canvas_obj.setLineWidth(0.6)
    y = 1.6 * cm
    while y < _GRID_H - 1.2 * cm:
        canvas_obj.line(0, y, _GRID_W, y)
        y += 0.85 * cm
    canvas_obj.setStrokeColor(HexColor('#F3C6C6'))
    canvas_obj.setLineWidth(1.1)
    canvas_obj.line(2.1 * cm, 0.5 * cm, 2.1 * cm, _GRID_H - 0.5 * cm)
    canvas_obj.setStrokeColor(HexColor('#D8D2C4'))
    canvas_obj.setLineWidth(0.8)
    y = 1.0 * cm
    while y < _GRID_H - 0.6 * cm:
        canvas_obj.circle(1.0 * cm, y, 0.22 * cm, stroke=1, fill=0)
        y += 2.1 * cm
    canvas_obj.setFont(FONT_NAME, 8)
    canvas_obj.setFillColor(HexColor('#A8B0BB'))
    canvas_obj.drawString(2.4 * cm, 0.7 * cm, 'Dastyor')
    canvas_obj.setFillColor(HexColor(accent))
    canvas_obj.setFont(FONT_NAME_BOLD, 8.5)
    canvas_obj.drawRightString(_GRID_W - _GRID_MARGIN, 0.7 * cm, str(doc_obj.page))
    # Page 1 only — this template has no separate cover, so the icon sits
    # in the header block beside the title on page 1 by design. On any
    # later page there is no header there to sit beside, only the box
    # grid's own top row starting right at the margin: confirmed live
    # (a real multi-page generation) that the icon, drawn at this same
    # fixed position regardless of page, ends up directly behind that
    # row's boxes, with a sliver of it poking out past their rounded top
    # corner as a stray mark — not a box-rendering bug at all.
    illus = _SUBJECT_ILLUSTRATIONS.get(str(content.get('subject') or '')) if doc_obj.page == 1 else None
    if illus:
        _mode, path = illus
        if os.path.exists(path):
            try:
                with PILImage.open(path) as im:
                    iw, ih = im.size
                box = 2.0 * cm
                scale = min(box / iw, box / ih)
                w, h = iw * scale, ih * scale
                canvas_obj.drawImage(path, _GRID_W - _GRID_MARGIN - w, _GRID_H - 1.9 * cm - h,
                                     width=w, height=h, mask='auto')
            except Exception:
                pass
    canvas_obj.restoreState()


def _grid_bullets(items: list, d: '_Design', numbered: bool = False) -> list:
    out = []
    for i, item in enumerate(items, 1):
        marker = f'{i}.' if numbered else '•'
        # _math_inline turns every "$...$" span the model wrote (any
        # field can carry one, worked_examples/main_content most often)
        # into a real typeset inline formula image instead of printing
        # raw LaTeX source ("$x = \frac{21}{3}$" verbatim) — see its own
        # docstring in export_builder.py. A no-op on text with no "$".
        out.append(Paragraph(f'{marker}&nbsp;&nbsp;{_math_inline(item, size=d.t.body_size)}', ParagraphStyle(
            name=_uid('GridB'), fontName=d.body_font, fontSize=d.t.body_size,
            leading=d.t.body_leading, textColor=HexColor(INK), spaceAfter=3)))
    return out


def _grid_formulas(formulas: list, d: '_Design') -> list:
    """Empty list (not a "—" placeholder) when there's nothing real to
    show — the caller (_build_notebook_grid) now OMITS the whole box in
    that case rather than printing an empty-looking ribbon, per direct
    feedback that a "Формулаҳо" box with nothing under it read as
    broken/unfinished for a subject (e.g. Информатика/language lessons)
    that genuinely has none."""
    out = []
    for item in formulas[:3]:
        if not isinstance(item, dict):
            continue
        formula = str(item.get('formula') or '').strip()
        if not formula:
            continue
        flow = _pdf_formula_flowable(_plain_to_latex(formula), minimal=False, accent=d.accent)
        if flow:
            out.append(flow)
        explanation = str(item.get('explanation') or '').strip()
        if explanation:
            exp_size = d.t.body_size - 1
            out.append(Paragraph(_math_inline(explanation, size=exp_size), ParagraphStyle(
                name=_uid('GridFExp'), fontName=d.body_font, fontSize=exp_size,
                leading=d.t.body_leading - 1.5, textColor=HexColor(INK), spaceAfter=6)))
    return out


def _worked_example_cards(items: list, d: '_Design', accent_hex: str, solution_label: str,
                          max_items: int = 20) -> list:
    """Numbered problem+solution cards — the 'мисол' exercises AI generates
    in bulk for math/exercise subjects (12-20 of them, a "hard floor" per
    ai_service.py's _WORKED_EXAMPLE_SUBJECTS/_EXERCISE_SUBJECTS prompt
    rules, explicitly "one of the most important fields" per direct
    teacher feedback) — a real, sizeable gap: this module rendered every
    OTHER konspekt field but silently dropped worked_examples entirely,
    on both the linear body and the notebook grid.

    Each example is its own small KeepTogether card, not one shared box —
    the list can run to 20 items, long enough that it MUST be free to
    flow across as many pages as it needs. A single big box (or one
    KeepTogether wrapping the whole list) can't do that without either an
    ugly mid-example split or the same LayoutError this module hit
    earlier from an oversized KeepTogether (see _ribbon_box's docstring)."""
    out = []
    n = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        problem = str(item.get('problem') or '').strip()
        if not problem:
            continue
        n += 1
        if n > max_items:
            break
        solution = str(item.get('solution') or '').strip()
        p_size = d.t.body_size
        s_size = max(d.t.body_size - 0.4, 8)
        p_style = ParagraphStyle(
            name=_uid('WEP'), fontName=d.body_font, fontSize=p_size,
            leading=d.t.body_leading, textColor=HexColor(INK))
        # _math_inline: the model writes these in LaTeX-with-$-delimiters
        # ("$x = \frac{21}{3}$", per ai_service.py's rule that worked_
        # examples solutions follow the same fraction/exponent notation as
        # the "formulas" field) — without this, that arrived on the page
        # as the literal LaTeX source, dollar signs and backslashes and
        # all, which is worse than plain "21/3" would have been. Renders
        # each "$...$" span as a real typeset inline formula image instead.
        body = [Paragraph(f'<b>{n}.</b>&nbsp;&nbsp;{_math_inline(problem, size=p_size)}', p_style)]
        if solution:
            s_style = ParagraphStyle(
                name=_uid('WES'), fontName=d.body_font, fontSize=s_size,
                leading=max(d.t.body_leading - 0.5, 11), textColor=HexColor('#334155'), spaceBefore=3)
            body.append(Paragraph(
                f'<font color="{accent_hex}"><b>{solution_label}:</b></font> {_math_inline(solution, size=s_size)}',
                s_style))
        box = Table([[body]], colWidths=[d.width])
        box.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.9, HexColor(accent_hex)),
            ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ]))
        out.append(KeepTogether([box]))
        out.append(Spacer(1, 6))
    return out


def _grid_image(image: dict, max_w: float) -> list:
    """One real, topic-relevant illustration for the "Схема/Расм" box —
    whatever real_world image this konspekt already fetched (see
    ai_service.py's _fetch_real_world_image/_render_lesson_images; a
    Wikimedia Commons photo/diagram picked for THIS specific topic, never
    a generic subject icon). A flat list of flowables, NOT wrapped in
    KeepTogether (unlike lecture_builder._figure, which this deliberately
    doesn't reuse) — see _ribbon_box's docstring for why a KeepTogether
    can never sit inside a Table cell, which is exactly where this box
    goes when paired with Мафҳумҳои асосӣ in a two-column row."""
    if not image:
        return []
    body = _pdf_illustration_image(image.get('path', ''), '', image.get('credit', ''),
                                   max_w=max_w, max_h=170)
    if not body:
        return []
    out = list(body)
    caption = str(image.get('caption') or image.get('explanation') or '').strip()
    if caption:
        out.append(Paragraph(caption, ParagraphStyle(
            name=_uid('GridImgCap'), fontName=FONT_NAME, fontSize=8.5,
            leading=11, alignment=TA_CENTER, textColor=HexColor(INK), spaceBefore=3)))
    return out


def _ribbon_box(title: str, flowables: list, color_idx: int, width: float) -> Table:
    """One colour-labelled box: a tinted "ribbon" title strip over a
    white body, both inside one bordered frame — the reference photo's
    "Цель:", "Ключевые понятия:" boxes. A single Table (not a label
    Table nested inside a border Table) because a ReportLab Table cell
    already accepts a LIST of flowables and stacks them, so the title
    Paragraph and the body flowables can just be two rows of one table
    without any nesting.

    Returns the plain Table — NOT wrapped in KeepTogether here. Confirmed
    live: a KeepTogether wrapping a Table breaks (raises a hard
    LayoutError, not even a bad-looking page) the moment it sits INSIDE
    ANOTHER Table's cell, which is exactly how row1/row2 below use two of
    these side by side — ReportLab's KeepTogether.wrap() needs a live
    canvas reference that a nested-in-a-cell flowable never receives.
    Callers that place a box directly on the story (not nested in a row)
    wrap it in KeepTogether themselves at the call site instead, where
    that reference IS available."""
    fill, dark = _GRID_COLORS[color_idx % len(_GRID_COLORS)]
    if not flowables:
        flowables = [Paragraph('—', ParagraphStyle(name=_uid('GridEmpty'), fontName=FONT_NAME, fontSize=9,
                                                    textColor=HexColor(INK)))]
    label = Paragraph(title, ParagraphStyle(
        name=_uid('RibbonLbl'), fontName=FONT_NAME_BOLD, fontSize=11.5,
        leading=14, textColor=HexColor(dark)))
    # The label/body divider is a FILLED hairline row, not a LINEBELOW
    # stroke — confirmed live (real generated PDF, a teacher's own
    # download) that a stroked line spanning the full cell width lands
    # exactly on top of the rounded-corner BOX border's curve, and at
    # least one PDF renderer draws the stroke join there as a small stray
    # dash poking past the border. A filled rectangle has no stroke join
    # to glitch — same look (a solid ruled line under the ribbon title),
    # no corner artifact in any renderer.
    divider = Table([['']], colWidths=[width], rowHeights=[1.1])
    divider.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), HexColor(dark)),
        ('LEFTPADDING', (0, 0), (0, 0), 0), ('RIGHTPADDING', (0, 0), (0, 0), 0),
        ('TOPPADDING', (0, 0), (0, 0), 0), ('BOTTOMPADDING', (0, 0), (0, 0), 0),
    ]))
    t = Table([[label], [divider], [flowables]], colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), HexColor(fill)),
        ('BACKGROUND', (0, 1), (0, 1), HexColor(fill)),
        ('BACKGROUND', (0, 2), (0, 2), HexColor('#FFFFFF')),
        ('BOX', (0, 0), (-1, -1), 1.1, HexColor(dark)),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (0, 0), 5), ('BOTTOMPADDING', (0, 0), (0, 0), 5),
        ('TOPPADDING', (0, 1), (0, 1), 0), ('BOTTOMPADDING', (0, 1), (0, 1), 0),
        ('LEFTPADDING', (0, 1), (0, 1), 0), ('RIGHTPADDING', (0, 1), (0, 1), 0),
        ('TOPPADDING', (0, 2), (0, 2), 8), ('BOTTOMPADDING', (0, 2), (0, 2), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    return t


def _grid_header(content: dict, w: dict, d: '_Design') -> list:
    """The reference photo's top block: "КОНСПЕКТ" kicker + big title,
    then a bordered 2x2 field grid (Фан/Синф, Мавзуъ/Сана) — a flowable
    (not drawn on the canvas) so it participates in normal page flow like
    everything below it."""
    accent = d.accent
    out = [
        Paragraph(w['tag'], ParagraphStyle(
            name=_uid('GridTag'), fontName=FONT_NAME_BOLD, fontSize=12,
            textColor=HexColor(accent), spaceAfter=2)),
        Paragraph(str(content.get('title') or ''), ParagraphStyle(
            name=_uid('GridTitle'), fontName=FONT_NAME_BOLD, fontSize=22,
            leading=26, textColor=HexColor(INK), spaceAfter=10)),
    ]
    label_style = ParagraphStyle(name=_uid('GridFieldLbl'), fontName=FONT_NAME_BOLD, fontSize=10,
                                  textColor=HexColor(INK))
    value_style = ParagraphStyle(name=_uid('GridFieldVal'), fontName=FONT_NAME, fontSize=10,
                                  textColor=HexColor(INK))

    def field(label, value):
        return [Paragraph(f'{label}:', label_style), Paragraph(str(value or '—'), value_style)]

    grid = Table([
        [field(w['subject'], content.get('subject')), field(w['grade_suffix'].capitalize(), content.get('grade'))],
        [field(w['date'], ''), field(w['duration'], w['duration_value'])],
    ], colWidths=[d.width / 2, d.width / 2])
    grid.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.1, HexColor(accent)),
        ('INNERGRID', (0, 0), (-1, -1), 0.6, HexColor(RULE)),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    out.append(grid)
    out.append(Spacer(1, 14))
    return out


def _build_notebook_grid(content: dict, w: dict, d: '_Design') -> list:
    """The whole "playful" body: the header block, then a grid of
    ribbon-labelled boxes. Item counts are capped and long items trimmed
    (see _trim_chars) so a genuinely detailed generation still reads as
    the reference's one-page STUDY SHEET rather than spilling every
    field's full detail into boxes sized for a summary — the full text is
    never lost, it is still in the material's other exports (DOCX, the
    other PDF templates); this template's whole point is being the
    compact one. Two boxes are CONDITIONAL, not always drawn with a "—"
    placeholder when the material has nothing for them: "Формулаҳо" only
    for subjects that actually have formulas, "Схема/Расм" only when a
    real topic-relevant image was already fetched for this konspekt (see
    ai_service.py's _fetch_real_world_image/_render_lesson_images) — an
    empty ribboned box read as broken, not as "this subject has none".
    Two more boxes were added after a teacher flagged that the grid
    skipped straight from vocabulary to the summary with no room for
    actually EXPLAINING the topic, or for what happens after the lesson
    (в классе/дома): "Мазмуни асосӣ" (the real main_content explanation,
    not the 3-sentence stand-in the concepts box used as a fallback) and
    a combined кор/супориш row (pair/group work + consolidation on one
    side, homework on the other) — both conditional, same "omit rather
    than show empty" rule as formulas/image above."""
    col_w = d.width / 2 - 0.25 * cm
    full_w = d.width

    story = _grid_header(content, w, d)

    objectives = _short_list(content.get('objectives'))[:5]
    competencies = [_trim_chars(c, 200) for c in _short_list(content.get('competencies'))[:4]]
    terms = [_trim_chars(t, 170) for t in _short_list(content.get('key_terms'))[:5]]
    concepts = [_trim_chars(c, 200) for c in _short_list(content.get('key_concepts'))[:4]]
    formulas = list(content.get('formulas') or [])
    summary = str(content.get('summary') or '').strip()
    checks_raw = [q for q in (content.get('quick_check') or []) if q][:5]
    checks = []
    for item in checks_raw:
        checks.append(str(item.get('question')) if isinstance(item, dict) else str(item))
    images = [im for im in (content.get('lesson_images') or []) if isinstance(im, dict) and im.get('path')]
    image = images[0] if images else None

    # The topic explanation itself — every paragraph of main_content,
    # trimmed, not just the 3-sentence stand-in the concepts box falls
    # back to when key_concepts is empty (that fallback stays below for
    # the rare case key_concepts genuinely has nothing either).
    explanation = []
    for _, paragraphs in _split_main_content(content.get('main_content')):
        explanation.extend(paragraphs)
    explanation = [_trim_chars(p, 320) for p in explanation if str(p).strip()][:6]

    pair_work = str(content.get('pair_work') or '').strip()
    group_work = _short_list(content.get('group_work'))[:3]
    consolidation = str(content.get('consolidation') or '').strip()
    practice = []
    if pair_work:
        practice.append(f"{w['pair_work']}: {pair_work}")
    for g in group_work:
        practice.append(f"{w['group_work']}: {g}")
    if consolidation:
        practice.append(f"{w['consolidation']}: {consolidation}")
    practice = [_trim_chars(p, 220) for p in practice]

    homework = [_trim_chars(h, 220) for h in _short_list(content.get('homework'))[:5]]

    tools = [_trim_chars(t, 160) for t in _short_list(content.get('tools'))[:5]]
    lesson_program = str(content.get('lesson_program') or '').strip()
    examples = [_trim_chars(e, 220) for e in _short_list(content.get('real_life_examples'))[:4]]
    notes = [_trim_chars(n, 220) for n in _short_list(content.get('important_notes'))[:3]]
    assessment = str(content.get('assessment') or '').strip()
    worked = [it for it in (content.get('worked_examples') or []) if isinstance(it, dict) and it.get('problem')]
    # Deliberately separate from worked_examples: those are SOLVED (the
    # method demonstrated); these are for the pupil to solve themselves —
    # only "problem" goes on the page here, "answer" is held back for the
    # answers box placed at the very end of the document (see below),
    # not right next to the problem where it would just get glanced at
    # instead of worked out.
    drills = [it for it in (content.get('practice_problems') or []) if isinstance(it, dict) and it.get('problem')]

    _row_style = TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        # A real screenshot showed two boxes in a row (Мисолҳо/Мисоли гурӯҳӣ
        # then Муҳим) sitting close enough to nearly touch — 8pt of gap
        # (RIGHTPADDING alone) read as "no gap at all" once each box's own
        # border/rounded corner is in the picture. Split across both sides
        # of the seam (7pt + 7pt = 14pt total) so there's daylight between
        # the two borders instead of them nearly kissing.
        ('LEFTPADDING', (1, 0), (1, 0), 7),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ])

    def _two_col(left_box, right_box):
        t = Table([[left_box, right_box]], colWidths=[col_w, col_w])
        t.setStyle(_row_style)
        story.append(t)

    def _full(box):
        # KeepTogether at the CALL SITE, not inside _ribbon_box itself —
        # see that function's own docstring for why: this box sits
        # directly on the story (not nested in a row table's cell),
        # which is exactly where KeepTogether works as intended.
        story.append(KeepTogether([box]))
        story.append(Spacer(1, 10))

    # A running counter, not manually-picked indices — with two more
    # conditional boxes now in the mix (explanation, practice/homework)
    # keeping every box's colour hand-numbered was already error-prone
    # (two boxes silently shared index 2 before this pass); _GRID_COLORS
    # has 5 entries and cycles happily on its own.
    _c = [0]

    def _next_color() -> int:
        i = _c[0] % 5
        _c[0] += 1
        return i

    _two_col(
        _ribbon_box(w['objectives'], _grid_bullets(objectives, d), _next_color(), col_w),
        _ribbon_box(w['terms'], _grid_bullets(terms, d), _next_color(), col_w),
    )

    if competencies:
        _full(_ribbon_box(w['competencies'], _grid_bullets(competencies, d), _next_color(), full_w))

    tools_box = (
        _ribbon_box(w['tools'], _grid_bullets(tools, d), _next_color(), col_w if lesson_program else full_w)
        if tools else None
    )
    program_box = (
        _ribbon_box(w['lesson_program'], [Paragraph(_math_inline(lesson_program, size=d.t.body_size), ParagraphStyle(
            name=_uid('GridProg'), fontName=d.body_font, fontSize=d.t.body_size,
            leading=d.t.body_leading, textColor=HexColor(INK)))], _next_color(), col_w if tools else full_w)
        if lesson_program else None
    )
    if tools_box and program_box:
        _two_col(tools_box, program_box)
    elif tools_box:
        _full(tools_box)
    elif program_box:
        _full(program_box)

    if explanation:
        _full(_ribbon_box(w['body'], _grid_bullets(explanation, d, numbered=True), _next_color(), full_w))

    if worked:
        # Not a ribbon box — a list this long (up to 20 items) needs to
        # flow across as many pages as it takes, which one ribbon-box
        # Table (title+divider+body, whole thing colour-filled) can't do
        # safely; see _worked_example_cards' own docstring. A coloured
        # heading in the same visual language stands in for the ribbon.
        _, dark = _GRID_COLORS[_next_color() % len(_GRID_COLORS)]
        story.append(Paragraph(w['worked_examples'], ParagraphStyle(
            name=_uid('WEHead'), fontName=FONT_NAME_BOLD, fontSize=12.5,
            leading=15, textColor=HexColor(dark), spaceBefore=2, spaceAfter=6)))
        story.extend(_worked_example_cards(worked, d, dark, w['solution']))

    if drills:
        _full(_ribbon_box(w['practice_problems'],
                          _grid_bullets([it.get('problem', '') for it in drills], d, numbered=True),
                          _next_color(), full_w))

    # Callouts the linear body weaves into the main_content flow
    # (important_notes/real_life_examples) — given their own row here
    # since the grid has no inline-flow to weave them into, right after
    # the explanation they belong to.
    examples_box = (
        _ribbon_box(w['examples'], _grid_bullets(examples, d), _next_color(), col_w if notes else full_w)
        if examples else None
    )
    notes_box = (
        _ribbon_box(w['notes'], _grid_bullets(notes, d), _next_color(), col_w if examples else full_w)
        if notes else None
    )
    if examples_box and notes_box:
        _two_col(examples_box, notes_box)
    elif examples_box:
        _full(examples_box)
    elif notes_box:
        _full(notes_box)

    # No more main_content fallback here — the explanation box above now
    # covers that case directly; an empty key_concepts just omits this box.
    concept_flowables = _grid_bullets(concepts, d, numbered=True) if concepts else []
    concept_box = (
        _ribbon_box(w['concepts'], concept_flowables, _next_color(), col_w if image else full_w)
        if concept_flowables else None
    )
    if concept_box and image:
        # Paired side by side, matching the reference photo's layout
        # exactly (Асосий қисми on the left, Схема/Расм on the right, same
        # row) — a real image is worth the same visual weight as the
        # concepts box, not a small afterthought.
        img_box = _ribbon_box(w['scheme'], _grid_image(image, col_w - 24), _next_color(), col_w)
        _two_col(concept_box, img_box)
    elif concept_box:
        _full(concept_box)
    elif image:
        _full(_ribbon_box(w['scheme'], _grid_image(image, full_w - 24), _next_color(), full_w))

    practice_box = (
        _ribbon_box(w['activities'], _grid_bullets(practice, d), _next_color(), col_w if homework else full_w)
        if practice else None
    )
    homework_box = (
        _ribbon_box(w['homework'], _grid_bullets(homework, d), _next_color(), col_w if practice else full_w)
        if homework else None
    )
    if practice_box and homework_box:
        _two_col(practice_box, homework_box)
    elif practice_box:
        _full(practice_box)
    elif homework_box:
        _full(homework_box)

    formula_flowables = _grid_formulas(formulas, d) if formulas else []
    summary_width = col_w if formula_flowables else full_w
    summary_box = _ribbon_box(w['summary'], [Paragraph(_math_inline(summary, size=d.t.body_size) or '—', ParagraphStyle(
        name=_uid('GridSum'), fontName=d.body_font, fontSize=d.t.body_size,
        leading=d.t.body_leading, textColor=HexColor(INK)))], _next_color(), summary_width)
    if formula_flowables:
        _two_col(_ribbon_box(w['formulas'], formula_flowables, _next_color(), col_w), summary_box)
    else:
        _full(summary_box)

    checks_box = (
        _ribbon_box(w['selfcheck'], _grid_bullets(checks, d, numbered=True), _next_color(),
                    col_w if assessment else full_w)
        if checks else None
    )
    assessment_box = (
        _ribbon_box(w['assessment'], [Paragraph(_math_inline(assessment, size=d.t.body_size), ParagraphStyle(
            name=_uid('GridAssess'), fontName=d.body_font, fontSize=d.t.body_size,
            leading=d.t.body_leading, textColor=HexColor(INK)))], _next_color(),
                    col_w if checks else full_w)
        if assessment else None
    )
    if checks_box and assessment_box:
        _two_col(checks_box, assessment_box)
    elif checks_box:
        _full(checks_box)
    elif assessment_box:
        _full(assessment_box)

    # The practice_problems answer key — deliberately the LAST thing on
    # the page, well below the problems themselves (see the "drills"
    # extraction above), so a pupil working through them doesn't have the
    # answer sitting right next to the question.
    drill_answers = [it.get('answer', '') for it in drills if str(it.get('answer') or '').strip()]
    if drill_answers:
        _full(_ribbon_box(w['answers'], _grid_bullets(drill_answers, d, numbered=True), _next_color(), full_w))

    # _full() always trails its box with a Spacer for breathing room before
    # the next box - but for the LAST box on the page that trailing spacer
    # is pure dead weight, and on a page already filled close to the frame
    # bottom (the common case here - a one-page grid, deliberately kept
    # dense) it's exactly enough to overflow a blank second page. Drop it.
    if story and isinstance(story[-1], Spacer):
        story.pop()

    return story


def _build_notebook_grid_pdf(content: dict, w: dict, d: '_Design', accent: str) -> io.BytesIO:
    """Its own small doc — one page template, background painted by
    _paint_notebook_chrome, body from _build_notebook_grid. Deliberately
    NOT threaded through the normal build_konspekt_pdf machinery below
    (cover pages, table of contents, the section-by-section loop): this
    template replaces the document's whole shape, not one knob in it, the
    same reasoning konspekt_templates.py's plan_layout already documents
    for "nakscha"."""
    buf = io.BytesIO()
    doc = _LectureDoc(buf, pagesize=A4, leftMargin=_GRID_MARGIN, rightMargin=_GRID_MARGIN,
                      topMargin=1.3 * cm, bottomMargin=1.6 * cm,
                      title=str(content.get('title') or 'Конспект'), author='Dastyor',
                      page_offset=0)

    def _on_page(canvas_obj, doc_obj):
        _paint_notebook_chrome(canvas_obj, doc_obj, content, accent)

    frame = Frame(_GRID_MARGIN, 1.6 * cm, _GRID_W - 2 * _GRID_MARGIN,
                  _GRID_H - 1.3 * cm - 1.6 * cm, id='grid')
    doc.addPageTemplates([PageTemplate(id='grid', frames=[frame], onPage=_on_page)])

    story = _build_notebook_grid(content, w, d)
    # build(), not multiBuild() — this template never sets tmpl.contents
    # (no table of contents), so the extra measure-then-render passes
    # multiBuild exists for buy nothing here. Confirmed live: they
    # actively broke a KeepTogether'd ribbon box that spilled onto a
    # second page — its second-pass height came back as ReportLab's
    # "couldn't measure" sentinel (16777225pt) instead of its real size,
    # raising a hard LayoutError. A single build() pass measures it once,
    # correctly, and never hits that state.
    doc.build(story)
    buf.seek(0)
    return buf


def build_konspekt_pdf(content: dict, language: str = 'Русский') -> io.BytesIO:
    """The whole конспект: cover, contents, plan, body, activities, checks.

    Follows the same shape build_lecture_pdf does — same fonts, same
    section-heading styles, same callouts — because the two are read the
    same way. What differs is only the field list: a konspekt carries
    objectives/competencies as short phrase lists rather than one
    paragraph goal, a lesson_program and tools list a лекция has no use
    for, and classroom activities (pair/group work, consolidation)."""
    w = _words(language)
    tmpl = get_lecture_template(content.get('template'))
    accent = get_subject_accent_hex(content.get('subject'))
    d = _Design(tmpl, accent, w)

    if tmpl.notebook_grid:
        return _build_notebook_grid_pdf(content, w, d, accent)

    buf = io.BytesIO()
    mx = tmpl.margin_x * cm
    doc = _LectureDoc(buf, pagesize=A4, leftMargin=mx, rightMargin=mx,
                      topMargin=tmpl.margin_top * cm, bottomMargin=2.0 * cm,
                      title=str(content.get('title') or 'Конспект'), author='Dastyor',
                      page_offset=0 if tmpl.cover == 'none' else 1)

    def _furniture(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setFont(FONT_NAME, 8)
        canvas_obj.setFillColor(HexColor('#A8B0BB'))
        canvas_obj.drawString(mx, A4[1] - 1.15 * cm, str(content.get('title') or '')[:70])
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

    # The cover functions are shared with build_lecture_pdf and read
    # `objective` (one string) and `lecture_plan` (a list) — a лекция's
    # fields. A konspekt's nearest equivalents are `objectives` (already a
    # short-phrase list — used as the plan preview) and the first
    # objective (used as the one-line aim). A copy, not a mutation of
    # `content`: nothing past the cover should see these synthetic keys.
    cover_content = dict(content)
    _obj_list = _short_list(content.get('objectives'))
    cover_content.setdefault('lecture_plan', _obj_list)
    if _obj_list:
        cover_content.setdefault('objective', _obj_list[0])

    def _paint_cover(canvas_obj, doc_obj):
        canvas_obj.saveState()
        try:
            _COVERS.get(tmpl.cover, _COVERS['split'])(canvas_obj, cover_content, d)
        except Exception as e:
            logger.warning(f'konspekt cover failed ({tmpl.cover}): {e}')
        canvas_obj.restoreState()

    frame = Frame(mx, 2.0 * cm, A4[0] - 2 * mx,
                  A4[1] - tmpl.margin_top * cm - 2.0 * cm, id='body')
    cover_frame = Frame(mx, 2 * cm, A4[0] - 2 * mx, A4[1] - 4 * cm, id='cover')
    page_templates = [PageTemplate(id='body', frames=[frame], onPage=_furniture)]
    if tmpl.cover != 'none':
        page_templates.insert(0, PageTemplate(id='cover', frames=[cover_frame],
                                              onPage=_paint_cover))
    doc.addPageTemplates(page_templates)

    story: list = [NextPageTemplate('body')]
    if tmpl.cover == 'none':
        from app.lecture_builder import _form_header
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
        from reportlab.platypus.tableofcontents import TableOfContents
        from reportlab.platypus import HRFlowable
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
        story.append(Spacer(1, 18))

    # ── objectives + competencies: short phrase lists, plan-style ───────
    objectives = _short_list(content.get('objectives'))
    if objectives:
        story.extend(section(w['objectives']))
        story.extend(_plan_block(objectives, d))
    competencies = _short_list(content.get('competencies'))
    if competencies:
        story.extend(section(w['competencies']))
        story.extend(_plan_block(competencies, d))

    # ── concepts and glossary ────────────────────────────────────────────
    definer = _DEFINITIONS.get(tmpl.definition, _definitions_cards)
    concepts = _short_list(content.get('key_concepts'))
    if concepts:
        story.extend(section(w['concepts']))
        story.extend(definer(concepts, d))
    # concept_cards: a structured visual extra (logic truth tables,
    # language declension/conjugation grids — see ai_service.py's
    # _CONCEPT_CARD_SUBJECTS) that export_builder.py's "nakscha" template
    # has always rendered right after key_concepts, no heading of its
    # own — this builder never ported it over, so every OTHER template
    # (every one this session touched) silently dropped it even though
    # the AI generates it. No new heading here either, same reasoning:
    # it belongs to the concepts section above, not a chapter of its own.
    concept_cards = content.get('concept_cards') or []
    if concept_cards:
        story.extend(_pdf_concept_card_grid(concept_cards, d.accent))
    terms = _short_list(content.get('key_terms'))
    if terms:
        story.extend(section(w['terms']))
        story.extend(definer(terms, d))
    # Same gap, same fix, for code_blocks (Информатика/programming only —
    # _CODE_SUBJECTS): real syntax-styled code the model already writes,
    # silently dropped by every template but "nakscha".
    for cb in (content.get('code_blocks') or []):
        if isinstance(cb, dict) and cb.get('code'):
            story.extend(_pdf_code_card(cb.get('code', ''), cb.get('language', ''),
                                        cb.get('explanation', ''), d.accent))

    # ── lesson flow and materials ────────────────────────────────────────
    lesson_program = str(content.get('lesson_program') or '').strip()
    if lesson_program:
        story.extend(section(w['lesson_program']))
        story.append(Paragraph(_math_inline(lesson_program, size=d.t.body_size), d.body_style(_uid('Prog'))))
    tools = _short_list(content.get('tools'))
    if tools:
        story.extend(section(w['tools']))
        story.extend(_plan_block(tools, d))

    # ── the lesson itself ────────────────────────────────────────────────
    parts = _split_main_content(content.get('main_content'))
    images = list(content.get('lesson_images') or [])
    visuals = list(content.get('visual_blocks') or [])
    if parts:
        story.extend(section(w['body']))
        # A konspekt's callouts are important_notes (warnings) and
        # real_life_examples — the лекция's key_ideas/teacher_tips have
        # no konspekt equivalent, so the queue is built directly rather
        # than through _queue_callouts (which expects those fields).
        callouts = []
        for text in (content.get('important_notes') or [])[:3]:
            if str(text).strip():
                callouts.append(('important', 'ВАЖНО', str(text).strip()))
        for text in (content.get('real_life_examples') or [])[:4]:
            if str(text).strip():
                callouts.append(('example', 'ПРИМЕР', str(text).strip()))
        callout_render = _CALLOUTS.get(tmpl.callout, _callout_card)
        body_style = d.body_style(_uid('Body'))
        for i, (head, paragraphs) in enumerate(parts):
            if head:
                story.extend(_subheading(head, d))
            for para in paragraphs:
                story.append(Paragraph(_math_inline(para, size=d.t.body_size), body_style))
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

    # ── worked examples ────────────────────────────────────────────────
    # Same gap this template's notebook grid had (see _worked_example_
    # cards' docstring): a real, sizeable field — 12-20 solved 'мисол'
    # problems for math/exercise subjects — that this builder silently
    # dropped entirely. Its own section like every other field above, not
    # folded into "the lesson itself" above: worked_examples is often
    # LONGER than main_content for these subjects, so it earns its own
    # heading rather than being buried as one more callout in the body.
    worked = [it for it in (content.get('worked_examples') or []) if isinstance(it, dict) and it.get('problem')]
    if worked:
        story.extend(section(w['worked_examples']))
        story.extend(_worked_example_cards(worked, d, d.accent, w['solution']))

    # ── practice problems (unsolved — for the pupil, not worked_examples'
    # "solved for the pupil to study") ───────────────────────────────────
    # "answer" is deliberately held back here and printed near the very
    # end of the document instead (see summary section below) — right
    # next to the problem it would just be glanced at instead of worked
    # out.
    drills = [it for it in (content.get('practice_problems') or []) if isinstance(it, dict) and it.get('problem')]
    if drills:
        story.extend(section(w['practice_problems']))
        story.extend(_grid_bullets([it.get('problem', '') for it in drills], d, numbered=True))

    # ── classroom activities ─────────────────────────────────────────────
    pair_work = str(content.get('pair_work') or '').strip()
    group_work = _short_list(content.get('group_work'))
    consolidation = str(content.get('consolidation') or '').strip()
    if pair_work or group_work or consolidation:
        story.extend(section(w['activities']))
        if pair_work:
            story.extend(_subheading(w['pair_work'], d))
            story.append(Paragraph(_math_inline(pair_work, size=d.t.body_size), d.body_style(_uid('Pair'))))
        if group_work:
            story.extend(_subheading(w['group_work'], d))
            story.extend(_plan_block(group_work, d))
        if consolidation:
            story.extend(_subheading(w['consolidation'], d))
            story.append(Paragraph(_math_inline(consolidation, size=d.t.body_size), d.body_style(_uid('Cons'))))

    # ── self-check ────────────────────────────────────────────────────────
    checks = [q for q in (content.get('quick_check') or []) if q]
    if checks:
        story.extend(section(w['selfcheck']))
        story.extend(_selfcheck_block(checks, d))

    # ── homework and assessment ──────────────────────────────────────────
    homework = _short_list(content.get('homework'))
    if homework:
        story.extend(section(w['homework']))
        story.extend(_plan_block(homework, d))
    assessment = str(content.get('assessment') or '').strip()
    if assessment:
        story.extend(section(w['assessment']))
        story.append(Paragraph(_math_inline(assessment, size=d.t.body_size), d.body_style(_uid('Assess'))))

    # ── practice problems answer key ─────────────────────────────────────
    # The very last section before the summary — see the "drills" block
    # above for why the answers are held back this far from the problems.
    drill_answers = [it.get('answer', '') for it in drills if str(it.get('answer') or '').strip()]
    if drill_answers:
        story.extend(section(w['answers']))
        story.extend(_grid_bullets(drill_answers, d, numbered=True))

    # ── summary ───────────────────────────────────────────────────────────
    summary = str(content.get('summary') or '').strip()
    if summary:
        story.extend(section(w['summary']))
        story.append(_summary_block(summary, d))

    doc.multiBuild(story)
    buf.seek(0)
    return buf
