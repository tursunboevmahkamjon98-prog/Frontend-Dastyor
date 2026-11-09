"""Konspekt PDF entry point and its section labels.

Every konspekt prints in the formal design (konspekt_design); this module
keeps the per-language words that design reads.
"""

import io


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
        'examples': 'Примеры', 'example': 'Пример', 'notes': 'Важно',
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
        'examples': 'Мисолҳо', 'example': 'Мисол', 'notes': 'Муҳим',
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
        'examples': 'Examples', 'example': 'Example', 'notes': 'Important',
        'worked_examples': 'Worked Examples', 'solution': 'Solution',
        'practice_problems': 'Practice Problems', 'answers': 'Answers', 'code': 'Code',
    },
}
L10N['Английский'] = L10N['English']


def _words(language: str) -> dict:
    return L10N.get(str(language or 'Русский'), L10N['Русский'])


def build_konspekt_pdf(content: dict, language: str = 'Русский') -> io.BytesIO:
    """Every konspekt prints in the formal design, whatever template was picked."""
    from app import konspekt_design, subject_templates
    from app.deck_design import FAMILY_OF
    family = FAMILY_OF.get(subject_templates.resolve(content.get('subject'),
                                                     content.get('grade')).id, 'general')
    return konspekt_design.build(content, _words(language), language, family)
