import asyncio
import copy
import json
import os
import random
import re
import httpx
import time
from datetime import datetime, timezone
from app.config import get_settings
from app.security import ai_slot
from app.logger import get_logger
from app.http_client import SSL_CONTEXT

settings = get_settings()
logger = get_logger(__name__)

_api_call_count = 0
_daily_reset_time = datetime.now(timezone.utc).date()

LANGUAGE_NAMES = {
    "Таджикский": "Tajik",
    "Русский": "Russian",
    "English": "English",
    "Английский": "English",
}



_STEM_ACCURACY = (
    " ACCURACY RULE: Only state facts, numbers, dates, and named "
    "scientists/discoveries you are confident are correct — never invent a "
    "precise figure, statistic, or attribution. If unsure of an exact "
    "number or date, describe it qualitatively (e.g. 'roughly', 'in the "
    "early 1900s') instead of a fabricated precise value."
)

_SUBJECT_KONSPEKT_PROMPTS = {
    "Таджикский язык": "Focus on Tajik grammar, morphology, phonetics with real sentence examples. Include word formation, vowel harmony, consonant clusters. Use Tajik linguistic terminology: фонетика, морфология, синтаксис, лексика. MANDATORY vocabulary when writing in Tajik: дарс (not урок), мактаб (not школа), синф (not класс), хонанда (not ученик), омӯзгор (not учитель), китоб (not книга), савол (not вопрос), ҷавоб (not ответ), намуна (not пример), хулоса (not вывод), таҳлил (not анализ). "
    "GRAMMATICAL TERMINOLOGY — this is the single highest-risk area for this subject (verified by direct review: generated content has used invented or wrong words here before), so use ONLY these standard Tajik school-grammar terms, spelled exactly as shown, and NEVER invent a substitute or approximate one: "
    "мубтадо (grammatical subject/подлежащее — NEVER 'кешанда' or any other invented word), "
    "хабар (grammatical predicate/сказуемое — NEVER 'нагзор'/'нагзори' or any other invented word), "
    "феъли ёридиҳанда (auxiliary verb — 'ёвар' is an acceptable shorter synonym; NEVER 'ёроғ', which is a real Tajik word but means WEAPON/ARMS, not an auxiliary — a clear and embarrassing error if it slips through), "
    "калима (word — spelled with 'а', NEVER the Turkish spelling 'келима' with 'е'), "
    "пасванд (suffix), реша (root), аломат/нишона (marker/sign). "
    "TENSE NAMES specifically (a second confirmed recurring error): замони ҳозира (present tense — NEVER 'ҳозирон', which is a real Tajik word but means 'those present/attendees', not a tense), замони гузашта (past tense), замони оянда (future tense). "
    "Also: use 'ва' for 'and', NEVER the Russian 'и' — a stray Russian conjunction has slipped into otherwise-correct Tajik text before. "
    "If you are not certain a specialized grammatical term is a real, standard word actually used in Tajik school textbooks, do NOT use it — rephrase the sentence in plain descriptive Tajik instead of risking an invented or wrong technical term. A teacher will read this term aloud to a class of native Tajik speakers, so an invented or foreign-language word here is immediately obvious and undermines trust in the whole material.",

    "Таджикская литература": "Start with a poem or excerpt from a Tajik classic. CRITICAL RULES for academic accuracy: 1) For Rudakiy: He made significant CONTRIBUTIONS to qasida and ghazal development, but did NOT create or standardize them. Use 'contributed to development' NOT 'created' or 'standardized'. 2) Avoid claiming he 'organized language and rhythm' - instead say 'enriched the literary language and demonstrated its artistic possibilities'. 3) Birthplace: use 'traditionally attributed to' when discussing birthplace, as exact location is debated. 4) For literary influence: use 'influenced' or 'was part of the tradition of' NOT direct borrowing claims. 5) Distinguish between well-established facts and scholarly debates. 6) Use 'approximately' for uncertain dates. 7) Present Persian-Tajik civilizational heritage, not just Tajik-only claims. IMPORTANT: When writing in Tajik, MANDATORY vocabulary: шеър (not стихотворение), байт (not куплет), ғазал (not газель), қасида (not касыда), адабиёт (not литература), муаллиф (not автор), асар (not произведение), достон (not поэма), ҳикоя (not рассказ), китоб (not книга), дарс (not урок), мактаб (not школа), синф (not класс), хонанда (not ученик), омӯзгор (not учитель), донишҷӯй (not студент), таҳлил (not анализ), муқоиса (not сравнение), хулоса (not вывод), намуна (not пример), савол (not вопрос), ҷавоб (not ответ), ҳақиқат (not правда), муҳаббат (not любовь), озодӣ (not свобода), адолат (not справедливость), меҳнат (not труд), дониш (not знание), шуҷоат (not храбрость), некӣ (not доброта), зебоӣ (not красота). Never use Russian words when Tajik equivalents exist.",

    "Русский язык": "Use word detective style. Include tongue twisters, grammar puzzles, common mistakes as detective cases.",

    "Английский язык": "Use movie quotes, song lyrics, pop culture. Compare formal vs slang English.",

    "Математика": "Use fun real-life examples: shopping discounts, sports scores, cooking. Include brain teasers and puzzles. NO dry formulas without explanation." + _STEM_ACCURACY,

    "Алгебра": "Use mystery/detective style. Show algebra as solving real puzzles: phone bills, pizza splitting, game scores." + _STEM_ACCURACY,

    "Геометрия": "Use famous buildings, nature patterns (flowers, snowflakes), origami. Make it visual and artistic." + _STEM_ACCURACY,

    "Информатика": "Use video game and social media analogies. If programming → show cool things code can do (games, apps). If hardware → compare to phone/computer parts students know. If algorithms → use treasure hunt or recipe analogies. Make it feel like learning a superpower, NOT a boring class. Keep it SHORT and EXCITING." + _STEM_ACCURACY,

    "Физика": "Start with a WOW fact or home experiment. Use car speed, roller coasters, sports. Tell scientist stories." + _STEM_ACCURACY,

    "Химия": "Use cooking analogies: atoms=ingredients, reactions=recipes. Include kitchen chemistry experiments." + _STEM_ACCURACY,

    "Биология": "Use nature documentary style. Include animal facts, body science, ecosystems. Make it feel like a zoo adventure." + _STEM_ACCURACY,

    "География": "Use travel blog style. Include country comparisons, culture, food, wildlife descriptions." + _STEM_ACCURACY,

    "История Таджикистана": "Use time-travel storytelling about Tajik history. CRITICAL RULES: 1) Distinguish FACTS from LEGENDS - label them clearly. 2) Use 'approximately' for uncertain dates. 3) Avoid nationalistic exaggeration - present balanced, scholarly views. 4) When discussing figures like Ferdowsi or Samanids, present their contribution to Persian-Tajik civilizational heritage, not just 'Tajik' heritage. 5) Use precise academic language, avoid emotional claims. 6) Include sources or scholarly consensus where possible. MANDATORY VOCABULARY when writing in Tajik (use these exact words, NOT Russian equivalents): давра (not период), сарвар (not лидер), давлат (not государство), халқ (not народ), забон (not язык), фарҳанг (not культура), таърих (not история), санъат (not искусство), илм (not наука), маориф (not образование), иқтисодиёт (not экономика), ҷамъият (not общество), давраи (not период), асри (not век), тоҷик (not таджик), форс (not перс), Сомониён (not Саманиды), Бухоро (not Бухара), Хуҷанд (not Худжанд), Душанбе (not Душанбе), кӯҳҳо (not горы), дарёҳо (not реки), водӣ (not долина), сарзамин (not территория), истиқлолият (not независимость), озодӣ (not свобода), бародарӣ (not братство), якҷоя (not вместе), авлод (not поколение), фарзанд (not потомок), аҷдод (not предки), бобо (not дед), таърихи (not исторический), муқаддас (not священный), арҷгузорӣ (not уважение), қадрдонӣ (not признательность).",

    "Всемирная история": "Use time-travel storytelling about world history. CRITICAL RULES: 1) Distinguish FACTS from LEGENDS. 2) Use precise dates with 'approximately' when uncertain. 3) Present balanced scholarly perspectives. 4) Connect world events to Central Asian/Tajik context where relevant. 5) Avoid oversimplification of complex historical processes.",

}

_FORMULA_SUBJECTS = {"Математика", "Алгебра", "Геометрия", "Физика", "Химия"}

_EXERCISE_SUBJECTS = {
    "Информатика",
    "Таджикский язык",
    "Русский язык",
    "Английский язык",
    "Таджикская литература",
}

_EXERCISE_KIND = {
    "Информатика": (
        "a concrete task on this exact topic: classify a component or process, trace a data flow, "
        "interpret a diagram/table, or solve a number-system or logic question — NEVER a program to write, "
        "trace, or debug, since this topic is not about programming"
    ),
    "Информатика_code": (
        "a concrete programming task on this exact topic: a short program to write, a snippet to trace or "
        "debug, or a number-system/logic question"
    ),
    "Таджикский язык": (
        "a concrete language exercise on this exact rule: a sentence to analyse, words to sort "
        "into their parts of speech, a word to change form, a sentence to build from given words, "
        "a mistake to correct"
    ),
    "Таджикский язык_primary": (
        "a concrete comprehension task on this exact story/topic: a question about what happened or why, "
        "a new word to use in the student's own simple sentence, a moral/lesson to state in one sentence, "
        "or a real-life situation to connect to the topic — NEVER a grammatical-structure task (no subject/"
        "predicate/parts-of-speech/suffix-root analysis, and never invent a grammatical category that is not "
        "real Tajik grammar)"
    ),
    "Таджикская литература_primary": (
        "a concrete comprehension task on this exact proverb/tale: what it means in plain words, a real-life "
        "situation where it applies, or retelling part of the story in the student's own words — NEVER a "
        "literary-analysis or grammatical-structure task"
    ),
    "Русский язык": (
        "a concrete language exercise on this exact rule: a sentence to analyse, words to sort "
        "into their parts of speech, a word to change form, a sentence to build from given words, "
        "a mistake to correct"
    ),
    "Английский язык": (
        "a concrete language exercise on this exact rule: a sentence to complete, a verb to put in "
        "the right tense, words to order into a sentence, a translation, a mistake to correct"
    ),
    "Таджикская литература": (
        "a concrete text task on this exact work/author: a line to explain in your own words, an "
        "image or figure of speech to identify and interpret, a character's motive to justify from "
        "the text, a passage to compare with another"
    ),
}

_WORKED_EXAMPLE_SUBJECTS = {"Математика", "Алгебра", "Геометрия", "Физика", "Химия"}

_CONCEPT_CARD_SUBJECTS = {"Информатика"}

_CODE_SUBJECTS = {"Информатика"}

# Programming is a branch of Informatics, not a default section of every
# Informatics lesson.  Keep this router deliberately conservative: a code
# block is allowed only when the requested topic itself names programming,
# code, an algorithm, or a programming data structure.  Hardware, networking,
# history, digital literacy, cybersecurity and the social role of technology
# should stay conceptual unless the teacher explicitly asks for code.
_CODE_TOPIC_TERMS = (
    "python", "c++", "c#", "java", "javascript", "программа", "барномасоз",
    "код", "синтаксис", "тағйирёбанда", "тағирёбанда", "переменн", "function",
    "функсия", "рекурс", "массив", "array", "list", "рӯйхат", "сикл", "давр",
    "loop", "алгоритм", "algorithm", "ҷустуҷӯ", "поиск", "sorting", "сортиров",
    "мураттабсоз", "структураи маълумот", "структура данных", "мураккабии вақт",
    "сложность алгоритм",
)


def _code_relevance(subject: str, topic: str) -> str:
    """Return ``needed`` only for a topic that genuinely calls for code.

    This is intentionally local and cheap.  The model still sees the RAG
    excerpt and is told to make the pedagogical decision, but this guard keeps
    a bad source excerpt or the old Informatics template from re-introducing
    Python/C++ into a non-programming lesson.
    """
    if subject not in _CODE_SUBJECTS:
        return "none"
    haystack = str(topic or "").casefold()
    return "needed" if any(term in haystack for term in _CODE_TOPIC_TERMS) else "none"


def _code_relevance_rule(subject: str, code_policy: str) -> str:
    """CODE IS/IS NOT RELEVANT guard. Previously wired only into konspekt/lektsiya/
    prezentatsiya, which is why test/amaliy/igra defaulted to Python/C++ on any
    Informatics topic regardless of relevance — this makes it available to every
    material type."""
    if subject not in _CODE_SUBJECTS:
        return ""
    if code_policy == "needed":
        return (
            "- CODE IS RELEVANT TO THIS TOPIC. Include a short, valid code example only when it directly "
            "teaches the requested programming concept, in the language the topic names. Never add Python "
            "and C++ together just because the subject is Informatics."
        )
    return (
        "- CODE IS NOT RELEVANT TO THIS TOPIC. Do not write Python/C++ examples, compiler/API material, "
        "or programming exercises. Cover the requested Informatics topic with its own concepts, diagrams, "
        "processes, devices, standards, or real-life examples instead."
    )


def _exercise_kind(subject: str, code_policy: str, grade: str | None = None) -> str:
    """Pick the Информатика exercise wording by code relevance — the generic
    dict entry used to say "or write a short program only when..." which the
    model treated as permission rather than a condition, leaking code/compiler
    exercises into non-programming Informatics lessons.

    A primary-grade "Таджикский язык"/"Таджикская литература" reading/moral-
    story/proverb topic needs comprehension exercises, not the grammar-rule
    exercises this dict otherwise describes (see _PRIMARY_GRADE_SUBJECT_HINT
    — without this, exercises kept drifting into grammatical analysis even
    once the main lesson body stopped)."""
    if subject == "Информатика" and code_policy == "needed":
        return _EXERCISE_KIND["Информатика_code"]
    if _is_primary_grade(subject, grade) and f"{subject}_primary" in _EXERCISE_KIND:
        return _EXERCISE_KIND[f"{subject}_primary"]
    return _EXERCISE_KIND.get(subject, "a concrete task on this exact topic")


def _is_variable_topic(subject: str, topic: str) -> bool:
    if subject != "Информатика":
        return False
    haystack = str(topic or "").casefold()
    variable_terms = (
        "переменн", "тағйирёбанда", "тағирёбанда", "variable", "навъи маълумот",
        "типы данных", "data type", "int", "float", "str", "bool", "input", "type",
    )
    return any(term in haystack for term in variable_terms)


def _topic_scope_rule(subject: str, topic: str) -> str:
    """Keep focused Informatics lessons from drifting into nearby chapters."""
    if subject != "Информатика":
        return ""

    if _is_variable_topic(subject, topic):
        return (
            f'- EXACT TOPIC LOCK for this Informatics lesson: the topic is only "{topic}". '
            "Teach variables, assignment, and the named data types/functions using only the smallest examples. "
            "For a basic variables-and-types lesson, the core types are int, float, str, and bool; use input(), "
            "type(), and int()/float()/str() only when the topic or teacher request names them. Do NOT add "
            "discounts, finance, rounding, memory "
            "internals, swapping two variables, lists/dictionaries, functions/def, imports/modules, APIs, "
            "algorithms, or programming history unless the topic explicitly names them. Do not turn a simple "
            "variable example into a real-life business problem. For tools, use only a generic Python "
            "interpreter/console when necessary; never add IDLE, Jupyter, Colab, VS Code, or other tools by default. "
            "Every group task, visual block, homework task, and example must test one of the named concepts."
        )
    return (
        f'- EXACT TOPIC LOCK: teach only the concepts explicitly named in "{topic}" and the minimum prerequisite '
        "needed to understand them. Do not add adjacent chapters, unrelated applications, named software tools, "
        "or extra programming examples just to make the material look richer."
    )


_MATH_NOTATION_RULE = (
    "- MATH NOTATION: wrap every mathematical expression — a formula, a single variable, a unit with an "
    "exponent — in dollar signs: \"$x^{2} + 5x + 6 = 0$\", \"$-100$\", a lone variable \"$x$\". Use "
    "\\frac{a}{b} for every fraction (never a slash, except in units like м/с), ^{} for powers, _{} for "
    "indices. The ^{} braces hold ONLY the exponent itself, never a variable multiplied after it "
    "(\"3a^{2}b\", never \"3a^{2b}\"). When two separately-indexed variables are multiplied, like "
    "P₁ times V₁, give each its own subscript and never stack a second _{} right after the first: "
    "\"$P_{1}V_{1}=P_{2}V_{2}$\" is correct, \"$P_{1V}_{1}=P_{2V}_{2}$\" is invalid and will break the "
    "formula display entirely."
)

_TEACHER_SIMPLICITY_RULE = (
    "- STRICT TOPIC BOUNDARY: every sentence, fact, example, task, question, and explanation must directly "
    "teach the exact topic written by the teacher. Do not expand it into a related chapter, nearby concept, "
    "general history, broad subject overview, or an unrelated real-life story. If a detail does not help explain "
    "this exact topic, leave it out. When unsure whether something belongs, omit it.\n"
    "- VERY SIMPLE LANGUAGE: write for the stated grade using the shortest, clearest everyday words. Do not use "
    "difficult academic, bureaucratic, poetic, or foreign words when a simple word works. Use a subject-specific "
    "term only when it is truly necessary, and explain it immediately in plain words the first time. No unexplained "
    "abbreviations, inflated phrasing, filler, or complicated sentence structure. A teacher and pupil should "
    "understand every sentence on the first read.\n"
    "- DIFFICULTY LIMIT FOR EVERY SUBJECT: for a basic topic in any subject, use only concepts, words, formulas, "
    "tools, code, and examples that are necessary for the exact topic and grade. Do not add advanced concepts from "
    "another chapter just to make the lesson look richer. Teach one new idea at a time, use the simplest possible "
    "example, and explain necessary terms immediately. If a method is not named by the topic and is not required to "
    "solve it, leave it out. For example, in a basic Python lesson do not add def, import, classes, or unrelated "
    "libraries; in mathematics do not add advanced formulas; in science do not add unrelated terminology. Use "
    "advanced material only when the exact topic asks for it.\n"
    "- COMPOUND TOPIC: if the teacher's topic names SEVERAL distinct things separated by periods or semicolons "
    "(e.g. \"Пешвои миллат. Дӯстӣ. Шарҳи маънои зарбулмасалҳо\" — three unrelated themes, not one idea said "
    "twice), do NOT blend them into one continuous narrative — that is what produces off-topic tasks and shaky "
    "examples, because material meant for one part leaks into another. Instead give each part its own clearly "
    "separated piece of the lesson (its own lesson_stage(s), its own key_concepts entries, its own examples/"
    "tasks) so every fact and exercise stays inside the ONE part it belongs to. Keep the parts in the order the "
    "teacher wrote them and size each part's share of the lesson roughly evenly unless one part is obviously "
    "bigger. A single sentence with commas describing one idea is NOT a compound topic — only split when the "
    "parts are genuinely different subjects of study."
)

_LEVEL_MAP_DETAILED = {
    "Лёгкий": "Beginner. Very simple language, like talking to a friend. Avoid academic/technical jargon "
              "entirely — if a term is truly unavoidable, define it in plain words the moment it's used.",
    "Средний": "Intermediate. Clear with real examples. Subject-specific terminology is fine but always "
               "explained in context, never assumed.",
    "Сложный": "Advanced. Deeper but still practical and engaging. Technical vocabulary is fine, but still "
               "explained — this is still the hardest version of what THIS grade can absorb, not "
               "university-level material (see the grade rule below).",
}


def _level_text(level: str) -> str:
    return _LEVEL_MAP_DETAILED.get(level, _LEVEL_MAP_DETAILED["Средний"])


_PRIMARY_GRADE_SUBJECT_HINT = {
    "Таджикский язык": (
        "PRIMARY-GRADE READING LESSON for a young child (not a grammar lesson): this topic is a short story, "
        "poem, or everyday-life text, not a grammar rule. Do NOT analyse grammatical structure (subject/"
        "predicate, tense, parts of speech, suffixes) unless the topic itself explicitly names a grammar rule — "
        "focus instead on understanding the text, 3-5 new words explained in one simple sentence each, the "
        "moral or lesson it teaches, and warm, concrete real-life connections (family, friends, school, nature, "
        "animals) a 6-10-year-old recognises. Short sentences, friendly tone, no literary or linguistic "
        "terminology."
    ),
    "Таджикская литература": (
        "EARLY-GRADE READING LESSON for a young child, not academic literary criticism: this topic is a "
        "proverb, folk saying, or short tale, not a classical author's biography or literary movement. Do NOT "
        "discuss literary history, named classical poets, or scholarly debate unless the topic itself names a "
        "specific author/work. ACCURACY: only use REAL, well-known Tajik/Persian proverbs and sayings you are "
        "genuinely confident exist — never invent a proverb-sounding sentence and present it as a real one. If "
        "unsure whether a specific proverb is real, use a different well-known one instead. Use a DIFFERENT real "
        "proverb/example in each section — never repeat the exact same line across key_concepts, "
        "real_life_examples, and lesson_stages. Explain its everyday meaning in simple words, give 2-3 real-life situations a "
        "child would recognise where it applies, and state the moral plainly and warmly."
    ),
}


_PRIMARY_GRADE_MAX = {
    "Таджикский язык": 4,   # confirmed via real topics, e.g. "Дӯстӣ" filed at grade 2
    "Таджикская литература": 5,  # confirmed via "Зарбулмасалу мақолҳо" filed at grade 5
}


def _is_primary_grade(subject: str, grade: str | None) -> bool:
    max_grade = _PRIMARY_GRADE_MAX.get(subject)
    if max_grade is None:
        return False
    # The frontend always sends grade as "3 класс", never a bare "3" -- a
    # plain int(str(grade)) silently raised ValueError on that and always
    # fell back to False, so this primary-grade hint never actually fired
    # for a real request (only for a bare-number grade nothing ever sends).
    match = re.search(r"\d+", str(grade or ""))
    if not match:
        return False
    return int(match.group()) <= max_grade


def _subject_hint(
    subject: str,
    language: str = "English",
    grade: str | None = None,
    topic: str | None = None,
) -> str:
    """Per-subject tone/style hint, plus the Tajik Informatics/Physics term fixes
    that used to live only inside _konspekt_prompt — every material type gets
    them now, not just konspekt.

    Grades 1-4 file reading/moral-story and proverb topics under the SAME
    subject keys ("Таджикский язык", "Таджикская литература") as grammar and
    literary-history lessons for older grades — confirmed against real topics
    like "Дӯстӣ" (grade 2) and "Зарбулмасалу мақолҳо" (grade 5). Without this,
    the grammar/literary-history hint below got force-applied to a 7-year-old's
    friendship story, producing irrelevant grammatical analysis.
    """
    if _is_primary_grade(subject, grade) and subject in _PRIMARY_GRADE_SUBJECT_HINT:
        return _PRIMARY_GRADE_SUBJECT_HINT[subject]
    if subject == "Информатика" and _is_variable_topic(subject, topic or ""):
        # Focused Python lessons should not inherit the broad Informatics
        # hype about games, social media, or "superpowers".
        hint = (
            "Use a neutral, textbook-style explanation focused only on Python variables and the named data types. "
            "Do not use hype, marketing, games, social media, or unrelated real-life framing."
        )
    else:
        hint = _SUBJECT_KONSPEKT_PROMPTS.get(subject, "")
    if language == "Таджикский" and subject == "Информатика":
        if _is_variable_topic(subject, topic or ""):
            hint += (
                " Use only these school terms for this lesson: тағйирёбанда (variable), навъи маълумот "
                "(data type), адади бутун (integer), адади ҳақиқӣ (float), сатр (string), қимат (value), "
                "таъйин кардан (assignment), табдил додан (conversion), ворид кардан (input), нишон додан "
                "(output). Never use the invented form Интизор for integer and never introduce рӯйхат (list) "
                "unless the topic explicitly names it."
            )
        else:
            hint += (
                " For Tajik programming lessons use school-standard terms: тағйирёбанда (variable), "
                "навъи маълумот (data type), адади бутун (integer), адади ҳақиқӣ (float), сатр (string), "
                "рӯйхат (list), қимат (value), нигоҳ медорад (stores). Never use the invented form "
                "Интизор for integer and never translate programming terms word-for-word from Russian or Uzbek."
            )
    elif language == "Таджикский" and subject == "Физика":
        hint += (
            " For Tajik physics use standard school vocabulary: ҳолат, эҳтимол, ченкунӣ, зарра, фотон, "
            "электрон, мавҷ, энергия, баробарӣ, таҷриба, назария. For quantum entanglement, prefer the "
            "plain phrase 'алоқаи квантӣ байни ду зарра' if a shorter technical term is uncertain. Never use "
            "Uzbek syntax or words such as системасининг, имконияти, бир нечта, бўлиш, шаклида, қўшилган, "
            "or запутанлик; rewrite them in natural literary Tajik."
        )
    return hint

_SUBJECT_VISUAL_PREFERENCE: dict[str, list[str]] = {
    "Информатика": ["process", "flowchart", "comparison"],
    "Математика": ["table", "process"],
    "Алгебра": ["table", "process"],
    "Геометрия": ["table", "comparison"],
    "Физика": ["process", "comparison", "table"],
    "Химия": ["process", "table"],
    "Биология": ["comparison", "process"],
    "География": ["comparison", "table"],
    "История Таджикистана": ["timeline", "comparison"],
    "Всемирная история": ["timeline", "comparison"],
    "Таджикская литература": ["timeline", "comparison"],
}

_FIGURE_SHAPES: dict[str, list[tuple[str, str]]] = {
    "Геометрия": [
        ("cube", "[qirra]"), ("cuboid", "[a, b, balandlik]"),
        ("pyramid", "[asos qirrasi, balandlik]"), ("prism", "[asos qirrasi, balandlik]"),
        ("cylinder", "[radius, balandlik]"), ("cone", "[radius, balandlik]"),
        ("sphere", "[radius]"), ("square", "[tomon]"), ("rectangle", "[a, b]"),
        ("parallelogram", "[a, b]"), ("trapezoid", "[asos a, yon tomon]"),
        ("rhombus", "[tomon]"), ("triangle", "[a, b, c]"),
        ("right_triangle", "[katet a, katet b, gipotenuza]"),
        ("circle", "[radius]"), ("angle", "[burchak nomi, masalan 45°]"),
    ],
    "Математика": [
        ("square", "[tomon]"), ("rectangle", "[a, b]"), ("triangle", "[a, b, c]"),
        ("right_triangle", "[katet a, katet b, gipotenuza]"), ("circle", "[radius]"),
        ("cube", "[qirra]"), ("cuboid", "[a, b, balandlik]"), ("cylinder", "[radius, balandlik]"),
        ("angle", "[burchak nomi]"), ("coordinate_plane", "[]"),
        ("plot_linear", "[k, b]"), ("plot_parabola", "[a, b, c]"),
        ("plot_exponential", "[asos a (y = a^x), koeffitsient]"),
    ],
    "Алгебра": [
        ("coordinate_plane", "[]"), ("plot_linear", "[k, b]"),
        ("plot_parabola", "[a, b, c]"), ("plot_hyperbola", "[k]"),
        ("plot_sine", "[amplituda, chastota]"),
        ("plot_exponential", "[asos a (y = a^x), koeffitsient]"),
    ],
    "Физика": [
        ("force_diagram", "[F, mg, N, ishqalanish]"),
        ("inclined_plane", "[mg, burchak]"), ("pendulum", "[uzunlik, burchak]"),
        ("circuit", "[manba, qarshilik, lampa, kalit]"),
        ("plot_linear", "[k, b]"), ("plot_parabola", "[a, b, c]"),
    ],
    "Информатика": [
        ("blok_sxema", "[har bir qadam \"tur:matn\" ko'rinishida, algoritm tartibida; "
                        "turlar: start, in (kiritish), do (amal), if (shart), "
                        "yes/no (shartning ikki javobi, faqat if dan keyin), out (chiqarish), end]"),
        ("computer_arch", "[kirish, protsessor, chiqish, xotira, ALU, boshqaruv qurilmasi]"),
        ("network_star", "[markaz/kommutator nomi, keyin kompyuter nomlari]"),
        ("network_bus", "[shina nomi, keyin kompyuter nomlari]"),
        ("network_ring", "[halqa nomi, keyin kompyuter nomlari]"),
        ("logic_gate", "[and|or|not|xor, 1-kirish, 2-kirish, chiqish]"),
        ("binary_table", "[0-255 orasidagi butun son]"),
        ("array_cells", "[massiv elementlari, 8 tagacha]"),
        ("folder_tree", "[ildiz papka, keyin ichki papkalar]"),
        ("client_server", "[mijoz, server, so'rov, javob]"),
    ],
    "Химия": [
        ("atom_model", "[element belgisi, qobiqlar masalan \"2,8,1\", izoh]"),
        ("molecule", "[formula: h2o, co2, ch4, nh3, h2, o2, n2, hcl]"),
    ],
}

_VISUAL_BLOCK_TYPES = ["table", "timeline", "flowchart", "process", "comparison"]

_KONSPEKT_ANGLES = [
    "Lead with a concrete everyday scenario a student has personally run into, then connect it to the concept.",
    "Frame it around a historical origin story — who first figured this out or needed it, and why.",
    "Build it as a mini problem-to-solve: pose a question first, then unfold the concept as the answer.",
    "Lean on a comparison/analogy to something students already know well from daily life.",
    "Center it on a real profession/industry that uses this concept day-to-day, with concrete work examples.",
    "Frame it around a common misconception students have, correcting it step by step.",
    "Build it as a cause-and-effect chain — what happens if this concept is ignored or misapplied.",
    "Center it on a local/regional example (Tajikistan-relevant where plausible) rather than a generic global one.",
]



_KONSPEKT_SHAPES = [
    "STEP-BY-STEP PROCEDURE: teach it as an explicit algorithm — name each step, show it applied to one "
    "worked example, then let the exercises repeat the steps on new numbers.",
    "PROBLEM-FIRST DISCOVERY: open with a problem the pupils cannot yet solve, let the rule emerge as the "
    "answer to it, and only name/formalise the rule after they have seen why it is needed.",
    "ERROR HUNT: build the lesson around wrong solutions — present worked examples containing deliberate "
    "mistakes for the class to find and correct, with the correct method emerging from the corrections.",
    "VISUAL MODEL: teach the whole topic through one concrete visual model (balance scales, area rectangles, "
    "a number line, a diagram) and keep returning to that model for every example and exercise.",
    "REAL-WORLD TASKS: every example and exercise is a practical situation with real quantities (money, "
    "distances, time, materials); the abstract notation is introduced as shorthand for those situations.",
    "COMPARE AND CONTRAST: teach by putting cases side by side — what changes and what stays the same "
    "between two related types of problem — so the boundary of the rule is what the pupils learn.",
    "GROUP INVESTIGATION: the class works in groups on different pieces of the topic and reports back; the "
    "lesson content is organised as the material each group needs and what the whole class assembles from it.",
    "FROM SIMPLE TO GENERAL: start from the most stripped-down special case, then add one complication at a "
    "time, each with its own short example, until the general case is reached.",
]


def _content_of(previous: dict) -> dict:
    if isinstance(previous, dict):
        return previous
    try:
        return json.loads(previous)
    except Exception:
        return {}


def _first_texts(value, limit: int, chars: int = 90) -> list[str]:
    out = []
    items = value if isinstance(value, list) else ([value] if value else [])
    for item in items[:limit]:
        if isinstance(item, dict):
            text = " / ".join(str(item.get(k, "")) for k in ("problem", "question", "term", "title")
                              if item.get(k))
            text = text or str(next(iter(item.values()), ""))
        else:
            text = str(item)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append(text[:chars])
    return out


def summarize_previous_konspekt(previous) -> dict:
    content = _content_of(previous)
    if not content:
        return {}
    variant = content.get("variant") or {}
    return {
        "subtitle": str(content.get("subtitle") or "")[:120],
        "shape": str(variant.get("shape") or "")[:80],
        "angle": str(variant.get("angle") or "")[:80],
        "examples": _first_texts(content.get("worked_examples"), 14, chars=70),
        "real_life": _first_texts(content.get("real_life_examples"), 3),
        "quick_check": _first_texts(content.get("quick_check"), 3),
        "group_work": _first_texts(content.get("group_work"), 3),
        "homework": _first_texts(content.get("homework"), 3),
        "sections": [k for k in ("key_concepts", "main_content", "worked_examples",
                                 "real_life_examples", "group_work", "consolidation")
                     if content.get(k)],
    }


def summarize_previous_presentation(previous) -> dict:
    content = _content_of(previous)
    if not content:
        return {}
    slides = content.get("slides") or []
    titles, bullets = [], []
    for slide in slides[:12]:
        if not isinstance(slide, dict):
            continue
        title = re.sub(r"\s+", " ", str(slide.get("title") or "")).strip()
        if title:
            titles.append(title[:60])
        for point in (slide.get("bullet_points") or [])[:2]:
            text = re.sub(r"\s+", " ", str(point or "")).strip()
            if text:
                bullets.append(text[:60])
    variant = content.get("variant") or {}
    return {
        "kind": "presentation",
        "subtitle": str(content.get("description") or "")[:120],
        "shape": str(variant.get("shape") or "")[:80],
        "angle": str(variant.get("angle") or "")[:80],
        "sections": titles[:10],
        "examples": bullets[:10],
    }


def _variation_rule(previous_digests: list[dict], angle: str, shape: str) -> str:
    if not previous_digests:
        return ""
    lines = [
        f"- THIS TOPIC HAS BEEN TAUGHT BEFORE. {len(previous_digests)} konspekt(s) already exist for it, "
        "and this new one must read as a DIFFERENT LESSON on the same topic — not a reworded copy. What the "
        "earlier ones used is listed below; none of it may come back:"
    ]
    for i, digest in enumerate(previous_digests, start=1):
        parts = []
        if digest.get("shape"):
            parts.append(f"taught as: {digest['shape']}")
        if digest.get("kind") == "presentation" and digest.get("sections"):
            parts.append("slide titles: " + " | ".join(digest["sections"]))
        if digest.get("examples"):
            label = ("slide bullets: " if digest.get("kind") == "presentation"
                     else "worked examples: ")
            parts.append(label + " | ".join(digest["examples"]))
        if digest.get("real_life"):
            parts.append("real-life: " + " | ".join(digest["real_life"]))
        if digest.get("quick_check"):
            parts.append("quick check: " + " | ".join(digest["quick_check"]))
        if digest.get("group_work"):
            parts.append("group work: " + " | ".join(digest["group_work"]))
        if digest.get("homework"):
            parts.append("homework: " + " | ".join(digest["homework"]))
        if parts:
            lines.append(f"  PREVIOUS VERSION {i}: " + "; ".join(parts))
    lines.append(
        "  Rules for THIS generation, all of them hard requirements:\n"
        "  * Do NOT reuse any worked example, practice task, quick-check question, group/pair task, "
        "real-life example or homework listed above — not the same wording, and not the same numbers with "
        "the wording changed. Every number in every problem must be different from the ones above.\n"
        "  * Do NOT reuse the way the topic was explained above; teach it through the different LESSON SHAPE "
        "given in the rule above instead.\n"
        "  * Change the ORDER in which the material unfolds, and which idea the lesson opens with.\n"
        "  * What must NOT change: the topic itself, the language, the grade, the difficulty level, and the "
        "mathematical/scientific correctness. A different lesson, not a different subject — and never a wrong "
        "one for the sake of being different."
    )
    return "\n".join(lines)


def _pick_variant(previous_digests: list[dict]) -> tuple[str, str]:
    used_angles = {d.get("angle") for d in previous_digests if d.get("angle")}
    used_shapes = {d.get("shape") for d in previous_digests if d.get("shape")}
    free_angles = [a for a in _KONSPEKT_ANGLES if a[:80] not in used_angles]
    free_shapes = [s for s in _KONSPEKT_SHAPES if s[:80] not in used_shapes]
    angle = random.choice(free_angles or _KONSPEKT_ANGLES)
    shape = random.choice(free_shapes or _KONSPEKT_SHAPES)
    return angle, shape



def _konspekt_prompt(
    topic: str,
    subject: str,
    level: str,
    grade: str,
    language: str = "English",
    include_homework: bool = True,
    include_fun_facts: bool = True,
    include_assessment: bool = True,
    include_examples: bool = True,
    source_text: str | None = None,
    previous_digests: list[dict] | None = None,
    variant_out: dict | None = None,
    code_policy: str | None = None,
) -> str:
    level_text = _level_text(level)
    subject_hint = _subject_hint(subject, language, grade, topic)
    lang_name = LANGUAGE_NAMES.get(language, "English")
    code_policy = code_policy or _code_relevance(subject, topic)

    optional_fields = []
    if subject in _FORMULA_SUBJECTS:
        optional_fields.append(
            '  "formulas": [{"formula": "compact formula in plain-text/unicode math notation, '
            'e.g. x^2, √(x), Δ, π, 45°, a/b", '
            '"latex": "the SAME formula written in LaTeX, e.g. x = \\\\frac{-b \\\\pm \\\\sqrt{D}}{2a}", '
            '"explanation": "1-2 sentence plain-language '
            'explanation of what it means and when to use it"}],'
        )
    if subject in _WORKED_EXAMPLE_SUBJECTS:
        optional_fields.append(
            '  "worked_examples": [{"problem": "a specific SOLVABLE problem directly applying this topic\'s '
            'technique, with real numbers (e.g. an equation to solve, an expression to simplify, a shape to '
            'compute) — never a real-life story", "solution": "the complete step-by-step solution, ending in the '
            'final answer"}],'
        )
    if subject in _EXERCISE_SUBJECTS:
        if subject == "Информатика" and code_policy == "needed":
            optional_fields.append(
                '  "worked_examples": [{"problem": "one short plain-language task on this exact topic, with no code inside the sentence", '
                '"code": "the short code only, on separate lines", "solution": "one or two short simple sentences explaining the result"}],'
            )
        else:
            optional_fields.append(
                '  "worked_examples": [{"problem": "one concrete exercise a pupil can actually be marked on, '
                'directly on this topic — with the actual sentence/words/values written out in it, never a '
                'vague instruction", "solution": "the full worked answer, showing the reasoning, ending in the '
                'answer itself"}],'
            )
    if subject in _WORKED_EXAMPLE_SUBJECTS or subject in _EXERCISE_SUBJECTS:
        optional_fields.append(
            '  "practice_problems": [{"problem": "an UNSOLVED problem for the pupil to work out themselves, same '
            'difficulty/style/technique as worked_examples but with genuinely different numbers/wording — never '
            'repeat a worked_examples problem with the numbers changed", "answer": "ONLY the final answer, no '
            'working shown, e.g. \'x = 4\' or \'12 см²\'"}],'
        )
    if subject in _CONCEPT_CARD_SUBJECTS:
        optional_fields.append(
            '  "concept_cards": [{"title": "Short name of one operation/term/rule", "tag": "notation or symbol (optional, empty string if none)", '
            '"table": [["col header 1", "col header 2"], ["row1val1", "row1val2"], ["row2val1", "row2val2"]], '
            '"note": "1 short sentence explaining it"}],'
        )
    if subject in _FIGURE_SHAPES:
        optional_fields.append(
            '  "figures": [{"shape": "one id from the list of available shapes below", '
            '"values": ["short label strings drawn ON the figure, in the order that shape expects"], '
            '"caption": "1 sentence printed under the drawing: what it shows and what to notice"}],'
        )
    if subject == "География":
        optional_fields.append(
            '  "map_locations": ["Specific, real, geocodable place name — a city, country, region, '
            'mountain range, river, or sea, written in English so it geocodes reliably regardless of the lesson language"],'
        )
    if subject in _CODE_SUBJECTS and code_policy == "needed":
        optional_fields.append(
            '  "code_blocks": [{"language": "python", "code": "...", "explanation": "..."}, '
            '{"language": "cpp", "code": "only when the topic genuinely needs a second language", "explanation": "..."}],'
        )
    if include_homework:
        optional_fields.append('  "homework": ["Task 1 written out in full", "Task 2"],')
    if include_assessment:
        optional_fields.append('  "assessment": "Marking criteria as 5 — ...; 4 — ...; 3 — ..."')
    optional_json = "\n" + "\n".join(optional_fields) if optional_fields else ""
    if optional_json and not include_assessment:
        optional_json = optional_json.rstrip(",")

    extra_rules = []
    extra_rules.append(_TEACHER_SIMPLICITY_RULE)
    scope_rule = _topic_scope_rule(subject, topic)
    if scope_rule:
        extra_rules.append(scope_rule)
    if _is_variable_topic(subject, topic):
        extra_rules.append(
            "- PYTHON VARIABLE FACTS: Python variables are not declared with a fixed type. Assignment binds a "
            "name to a value, and the same name may later refer to a value of another type. Do not claim that "
            "assigning 12.5 to an integer variable automatically raises a type-mismatch error. Explain type "
            "conversion only when the topic names it. Keep the title and subtitle neutral; never use phrases such "
            "as superpower, game, mobile game, social-media post, or marketing language."
        )
    extra_rules.append(
        f"- Be SPECIFIC to \"{topic}\": every sentence names a real number, name, formula, mechanism or example. "
        "Cut generic filler (\"this plays an important role\"). \"main_content\" explains HOW and WHY in flowing "
        "prose (no numbered lists inside it). Be concise: no sentence that repeats another."
    )
    if include_examples:
        extra_rules.append(
            "- Each \"key_concepts\" entry: \"Term: definition\" and ends with one tiny concrete example (introduced by the "
            f"lesson language's word for \"For example\") a grade {grade} pupil follows at once; a different example each time."
        )
    else:
        extra_rules.append(
            '- EXAMPLES OPTION OFF: do not add illustrative or real-life examples; keep each key concept to its definition and explanation only.'
        )
        extra_rules.append(
            '- Set "real_life_examples" to an empty list and do not create a separate examples section.'
        )
    if subject in _CODE_SUBJECTS and code_policy == "needed":
        extra_rules.append(
            "- CODE IS RELEVANT TO THIS TOPIC. Add code_blocks only if it directly teaches the requested concept. "
            "Use one short, valid example in the language named by the topic; add a second language only when the "
            "topic explicitly compares languages. Never add Python and C++ just because the subject is Informatics."
        )
    elif subject in _CODE_SUBJECTS:
        extra_rules.append(
            "- CODE IS NOT RELEVANT TO THIS TOPIC. Do not create code_blocks, Python/C++ examples, compiler/API "
            "sections, or programming exercises, and do not list a code editor, IDE, or compiler (e.g. VS Code) "
            "under \"tools\" either. Explain the requested Informatics topic with its own concepts, diagrams, "
            "processes, devices, standards, or real-life examples."
        )
    if subject == "Информатика":
        extra_rules.append(
            "- INFORMATICS FORMAT: identifiers, assignments and code must be shown as plain code in backticks or "
            "a code block, never as LaTeX math between $ signs. Use $ signs only for a genuine mathematical formula."
        )
    if subject in _FORMULA_SUBJECTS:
        extra_rules.append(
            "- \"formulas\": 2-4 formulas central to this topic ([] if none). \"formula\" is plain unicode "
            "(^, √, π, a/b, no markdown); \"latex\" is the same formula in LaTeX."
        )
    if subject in _FORMULA_SUBJECTS or subject in _WORKED_EXAMPLE_SUBJECTS:
        extra_rules.append(
            "- MATH NOTATION: wrap EVERY mathematical expression anywhere in the text in $...$ (\"$x^2 + 5x + 6 = 0$\", "
            "\"$-100$\", a lone variable \"$x$\"); words stay outside. LaTeX commands (\\frac, \\text, ^{}, _{}) only "
            "inside $...$. Fractions are always \\frac{a}{b}, never a slash (slash only in units like м/с). ^{} holds "
            "only the exponent: \"3a^{2}b\", never \"3a^{2b}\"."
        )
    if subject in _WORKED_EXAMPLE_SUBJECTS:
        extra_rules.append(
            "- \"worked_examples\": 6-8 solvable problems (not stories) applying this topic's technique, easiest "
            f"first, rising gently; small friendly numbers; grade {grade} level. Vary the form (compute, solve for the "
            "unknown, simplify, compare, fill a table, a short word problem). Each \"solution\" shows the steps in "
            "plain words and ends with the answer. Double-check arithmetic; never change a number mid-solution to "
            "force a clean answer — pick other numbers instead."
        )
    if subject in _EXERCISE_SUBJECTS:
        exercise_item = "sentence/words" if (subject == "Информатика" and code_policy == "needed") else ("sentence/words/code" if subject != "Информатика" else "sentence/table/data")
        extra_rules.append(
            "- \"worked_examples\": 5-6 exercises, each "
            + _exercise_kind(subject, code_policy, grade)
            + f", with the actual {exercise_item} written inside it; full worked answer with reasoning. Easiest "
            f"first, grade {grade} level, varied form, every answer correct."
        )
        if subject == "Информатика" and code_policy == "needed":
            extra_rules.append(
                "- FORMAT FOR INFORMATICS EXAMPLES: keep each problem as one short plain sentence. Put code only "
                "in the separate 'code' field, one statement per line. Keep 'solution' to 1-2 simple sentences. "
                "Never join prose and code with an em dash, never add labels such as 'Example:' or 'Result:', "
                "never add decorative # comments, Markdown fences, or repeated explanations."
            )
    if subject in _WORKED_EXAMPLE_SUBJECTS or subject in _EXERCISE_SUBJECTS:
        extra_rules.append(
            "- \"practice_problems\": 4-5 problems for pupils, different numbers/wording from every worked example; "
            "\"answer\" is only the bare final result. Fewer rather than a wrong answer."
        )
    if subject in _CONCEPT_CARD_SUBJECTS:
        extra_rules.append(
            "- \"concept_cards\": 3-5 cards for the distinct rules/operations of the topic. \"table\" is a small "
            "correct grid (first row headers, 2-4 cols, 2-4 rows) or omitted when not tabular."
        )
    if subject == "География":
        extra_rules.append(
            "- \"map_locations\": 1-3 real places for this topic, or [] if none."
        )
    subject_visual_pool = _SUBJECT_VISUAL_PREFERENCE.get(subject)
    if subject_visual_pool:
        forced_type = random.choice(subject_visual_pool)
        remaining_pool = [t for t in _VISUAL_BLOCK_TYPES if t != forced_type]
        required_types = [forced_type] + random.sample(remaining_pool, 1)
    else:
        required_types = random.sample(_VISUAL_BLOCK_TYPES, 2)
    extra_rules.append(
        "- \"visual_blocks\": exactly 2 entries of DIFFERENT \"type\", each with real substance (≥3 rows/steps/"
        f"events) and a 1-sentence \"description\". Prefer {', '.join(f'\"{t}\"' for t in required_types)}. "
        "Data shapes — table: {\"headers\": [...], \"rows\": [[...]]}; timeline: {\"events\": [{\"label\", \"date\", "
        "\"description\"}]}; flowchart/process: {\"steps\": [{\"title\", \"description\"}]}; comparison: "
        "{\"criteria\": [...], \"items\": [{\"name\", \"values\": [one per criterion]}]}. \"position_after\" is one of "
        "\"key_concepts\", \"main_content\", \"tools\", \"consolidation\", different for the two. Don't re-explain the "
        "same facts in prose."
    )
    if subject in _FIGURE_SHAPES:
        catalog = "; ".join(f"{name} {hint}" for name, hint in _FIGURE_SHAPES[subject])
        extra_rules.append(
            "- \"figures\": 0-1 entry — a drawing of the shape/graph/body/molecule the lesson works with. \"shape\" "
            f"copied exactly from: {catalog}. \"values\" are short labels in that order (for plot_* shapes: numeric "
            "coefficients); vertex letters are added automatically. \"coordinate_plane\" is bare axes only — use a "
            "plot_* shape to show a curve. [] if nothing drawable."
        )
    extra_rules.append(
        "- \"important_notes\": 0-2 real warnings/misconceptions, no leading label like \"Диққат:\" (the export adds it)."
    )
    if include_homework:
        extra_rules.append(
            "- \"homework\": 2-3 tasks written out in full; never invent textbook page or exercise numbers."
        )
    if _is_variable_topic(subject, topic):
        angle = "Direct textbook explanation of the named Python concepts with short, neutral examples."
        shape = "FOCUSED CONCEPT LESSON: define each named concept, show one minimal example, then check understanding."
    else:
        angle, shape = _pick_variant(previous_digests or [])
    if variant_out is not None:
        variant_out["angle"] = angle[:80]
        variant_out["shape"] = shape[:80]
    extra_rules.append(
        f"- LESSON SHAPE: {shape} Build the lesson order, examples and tasks on it. Framing: {angle} (drop it in a "
        "section where it doesn't fit). The \"subtitle\" reflects this framing."
    )
    variation_rule = _variation_rule(previous_digests or [], angle, shape)
    if variation_rule:
        extra_rules.append(variation_rule)
    extra_rules.append(
        f"- Vocabulary and depth fit grade {grade} — \"{level}\" means the hardest this grade can absorb, never university level."
    )
    extra_rules.append(
        "- \"quick_check\": 2-3 short questions answerable from this konspekt, each with a short answer."
    )
    extra_rules.append(
        "- \"group_work\": 3 short tasks, one per group, each on a DIFFERENT key concept (no \"Group N\" label)."
    )

    extra_rules_text = ("\n" + "\n".join(extra_rules)) if extra_rules else ""

    source_block = ""
    if source_text:
        source_block = f"""

SOURCE MATERIAL (primary source — build every section from it, not from general knowledge):
\"\"\"
{source_text}
\"\"\"
Use its own definitions, terminology, examples and order, organized into the sections below. Preserve every distinct
source fact that is relevant to the topic; condense only repeated filler. Don't contradict it;
supplement from general knowledge only where it has nothing for a section. If it is about a different topic than
"{topic}", ignore it completely."""

    real_life_examples_shape = '["Specific real scenario", "..."]' if include_examples else '[]'
    main_content_rule = 'with real facts and examples' if include_examples else 'with real facts and explanations, without illustrative examples'

    return f"""Create a concise, formal school lesson plan (konspekt) about "{topic}" for grade {grade}, subject "{subject}".

Subject style: {subject_hint}
Difficulty: {level_text}
CRITICAL: Write ALL content in {lang_name} language. Return ONLY valid JSON, nothing else.{source_block}

RULES:
- "competencies" and "objectives": short phrases (max ~12 words). Other text fields: 2-3 sentences; lists: 3-4 items.
- NEVER mix languages. Return ONLY the fields listed below.{extra_rules_text}

RETURN THIS JSON:
{{
  "title": "Title about {topic}",
  "subtitle": "One line, from this generation's framing",
  "duration": "45 minutes",
  "competencies": ["Short skill phrase", "...", "..."],
  "objectives": ["Short goal phrase", "...", "..."],
  "key_concepts": ["Term: explanation. For example, ...", "...", "...", "..."],
  "real_life_examples": {real_life_examples_shape},
  "lesson_stages": [{{"minutes": 5, "stage": "1-3 words", "activity": "one short sentence"}}, {{"minutes": 15, "stage": "...", "activity": "..."}}],
  "tools": ["Tool: how used", "..."],
  "main_content": "2-3 paragraphs of 3-4 sentences explaining {topic}, {main_content_rule}.",
  "visual_blocks": [{{"type": "table|timeline|flowchart|process|comparison", "title": "short label", "description": "1 sentence", "position_after": "section key", "data": {{}}}}],
  "consolidation": "2-3 sentence consolidation activity.",
  "group_work": ["Group 1 task", "Group 2 task", "Group 3 task"],
  "important_notes": [],
  "quick_check": [{{"question": "...", "answer": "..."}}],
  "summary": "2-3 sentence summary"{"," if optional_json else ""}{optional_json}
}}"""


def _lecture_prompt(
    topic: str,
    subject: str,
    level: str,
    grade: str,
    language: str = "English",
    source_text: str | None = None,
    code_policy: str | None = None,
) -> str:
    level_text = _level_text(level)
    subject_hint = _subject_hint(subject, language, grade, topic)
    lang_name = LANGUAGE_NAMES.get(language, "English")
    code_policy = code_policy or _code_relevance(subject, topic)

    optional_fields = []
    if subject in _FORMULA_SUBJECTS:
        optional_fields.append(
            '  "formulas": [{"formula": "compact formula in plain-text/unicode math notation, '
            'e.g. x^2, √(x), Δ, π, 45°, a/b", "explanation": "1-2 sentence plain-language '
            'explanation of what it means and when to use it"}],'
        )
    if subject in _CONCEPT_CARD_SUBJECTS:
        optional_fields.append(
            '  "concept_cards": [{"title": "Short name of one operation/term/rule", "tag": "notation or symbol (optional, empty string if none)", '
            '"table": [["col header 1", "col header 2"], ["row1val1", "row1val2"], ["row2val1", "row2val2"]], '
            '"note": "1 short sentence explaining it"}],'
        )
    if subject == "География":
        optional_fields.append(
            '  "map_locations": ["Specific, real, geocodable place name — a city, country, region, '
            'mountain range, river, or sea, written in English so it geocodes reliably regardless of the lesson language"],'
        )
    if subject in _CODE_SUBJECTS and code_policy == "needed":
        optional_fields.append(
            '  "code_blocks": [{"language": "python", "code": "...", "explanation": "..."}, '
            '{"language": "cpp", "code": "only when the topic explicitly compares languages", "explanation": "..."}] '
            '— see the code_blocks rule below,'
        )
    optional_json = "\n" + "\n".join(optional_fields) if optional_fields else ""

    extra_rules = []
    extra_rules.append(_TEACHER_SIMPLICITY_RULE)
    if subject in _CODE_SUBJECTS and code_policy == "needed":
        extra_rules.append(
            "- CODE IS RELEVANT TO THIS TOPIC. Add at most one short, valid code block only when it directly "
            "explains the requested programming concept. Add another language only if the topic explicitly asks "
            "for a language comparison. Never default to Python/C++ out of habit."
        )
    elif subject in _CODE_SUBJECTS:
        extra_rules.append(
            "- CODE IS NOT RELEVANT TO THIS TOPIC. Do not create code_blocks, Python/C++ examples, compiler/API "
            "sections, or programming exercises. Explain the requested Informatics topic as a conceptual lecture "
            "using only its own terms, mechanisms, diagrams, standards, and examples."
        )
    if subject in _FORMULA_SUBJECTS:
        extra_rules.append(
            "- \"formulas\": give 3-5 formulas central to this specific topic (not generic filler). "
            "Write the \"formula\" field compactly with plain-text/unicode math notation (^, √, Δ, π, °, "
            "fractions as a/b) and no markdown — that field is the fallback for viewers that cannot typeset "
            "mathematics. The LaTeX goes in the separate \"latex\" field (see the notation rule below); do not "
            "put LaTeX in \"formula\". If the topic truly has no formulas, return an empty list."
        )
    if subject in _FORMULA_SUBJECTS:
        extra_rules.append(
            "- MATHEMATICAL NOTATION. The export typesets mathematics properly — stacked fractions, real "
            "radicals, raised exponents — but only from LaTeX. Give it LaTeX and it prints like a textbook; "
            "give it plain text and it prints like a keyboard.\n"
            "  * Every \"formulas\" entry needs a \"latex\" field holding that same formula in LaTeX. Keep the "
            "\"formula\" field too, in the readable plain form, for viewers that show no mathematics.\n"
            "  * Wrap EVERY mathematical expression in dollar signs, ANYWHERE in the lecture — key concepts, "
            "key terms, main_content, real-life examples, important notes, table cells. Even a single letter "
            "standing for a variable, and even a bare power. Ordinary words stay outside the dollars.\n"
            "  * This includes a negative number by itself: write \"$-100$\", never \"\\text{-100}\" — a "
            "\\command{...} written OUTSIDE dollar signs is not LaTeX to the export, it is literal "
            "backslash-and-braces text that prints on the page exactly as typed. \\text{}, \\frac{}{}, ^{}, "
            "_{} and every other LaTeX command belong ONLY inside a $...$ pair, with no exception.\n"
            "  * EVERY fraction is \\frac{}{} — never a slash. Write \"x = \\frac{20}{4} = 5\", not "
            "\"x = 20/4 = 5\". A slash stays a slash only in units of measurement (м/с, км/ч).\n"
            "  * Use real LaTeX: ^{} for powers, _{} for indices, "
            "\\sqrt{}, \\sqrt[3]{}, \\pm, \\cdot, \\times, \\le, \\ge, \\ne, \\approx, \\pi, "
            "\\alpha, \\Delta, \\sum_{i=1}^{n}, \\int_{a}^{b}, and \\left( \\right) for brackets that "
            "must grow around a fraction.\n"
            "  * The ^{} braces hold ONLY the exponent itself, never a variable multiplied after it. A "
            "confirmed real mistake: the cube-of-a-sum expansion's middle term, meant to be \"three times "
            "a-squared times b\", was written \"3a^{2b}\" — that says \"3 times a to the power of (2b)\", a "
            "completely different (and wrong) quantity. The correct form is \"3a^{2}b\": close the ^{} "
            "braces right after the exponent digit, THEN write the next factor outside them.\n"
            "  * The mathematics itself must not change — LaTeX is how it is written, not what it says."
        )
    if subject in _CONCEPT_CARD_SUBJECTS:
        extra_rules.append(
            "- \"concept_cards\": the main visual centerpiece of this lecture — cover the topic thoroughly with 6-10 "
            "cards (not just a token few), e.g. every distinct logical operation/law, every distinct rule/term/"
            "classification that applies. Each \"table\" is a small grid (first row = column headers, 2-4 columns, "
            "2-4 data rows) — omit \"table\" and use nothing instead if a given card isn't naturally a table (a short "
            "rule/law can just use \"note\" alone). Never invent incorrect logic/values in a truth table — they must "
            "be actually correct. Only return fewer cards (or an empty list) if this topic genuinely has that little "
            "tabular content to cover."
        )
    if subject == "География":
        extra_rules.append(
            "- \"map_locations\": name 1-3 REAL places (their actual, correct names — never invent a place) that a "
            "map reader would want to see for this topic. If the topic has no specific geographic location, return "
            "an empty list."
        )
    extra_rules.append(
        "- \"visual_blocks\": KEEP THIS SHORT — this document favors thorough TEXT explanation over graphics/"
        "pictures. Include AT MOST 1 entry, and only if one specific fact genuinely benefits from a structured "
        "table/comparison that prose alone would explain less clearly. The default and most common answer here is "
        "an EMPTY LIST — explain everything in prose instead (main_content, key_concepts, real_life_examples) "
        "rather than reaching for a visual. If you do include the 1 entry, strongly prefer \"table\" or "
        "\"comparison\" (a plain data grid) over \"timeline\"/\"process\" (each renders as a full "
        "illustrated picture, not text) — only use one of those picture types if the content is genuinely "
        "sequential/relational in a way prose truly cannot capture. Never include more than 1 entry no matter how "
        "many visualizable facts this topic has — pick the single most valuable one, if any, and explain the rest "
        "in prose. Each \"data\" shape:\n"
        "  table: {\"headers\": [\"col1\", \"col2\"], \"rows\": [[\"...\", \"...\"]]}\n"
        "  timeline: {\"events\": [{\"label\": \"...\", \"date\": \"...\", \"description\": \"...\"}]}\n"
        "  flowchart/process: {\"steps\": [{\"title\": \"...\", \"description\": \"...\"}]}\n"
        "  comparison: {\"criteria\": [\"...\"], \"items\": [{\"name\": \"...\", \"values\": [\"one per criterion, same order\"]}]}\n"
        "  concept_map: {\"nodes\": [{\"id\": \"short-id\", \"label\": \"...\"}], \"edges\": [{\"from\": \"id\", \"to\": \"id\", \"label\": \"relationship (optional)\"}]}\n"
        "\"position_after\" must be one of: \"key_concepts\", \"main_content\", \"real_life_examples\"."
    )
    extra_rules.append(
        "- \"important_notes\": 0-2 short, genuinely important warnings/caveats/highlights (a common misconception, "
        "a safety note, an exception to the rule just taught). Return an empty list if this topic has nothing that "
        "warrants one — don't invent a filler note."
    )
    extra_rules.append(
        "- \"key_ideas\": 2-3 ONE-SENTENCE statements a student should carry out of this lecture — the thing "
        "itself, stated plainly and memorably, not a description of what will be covered. No more than 20 words each."
    )
    extra_rules.append(
        "- \"teacher_tips\": 1-2 short PRACTICAL notes for the teacher delivering this topic (where students "
        "usually get stuck, what to demonstrate, what to ask). Empty list if nothing useful — never filler."
    )
    angle = random.choice(_KONSPEKT_ANGLES)
    extra_rules.append(
        f"- Framing/angle for this generation: {angle} Let this shape which real-world examples you reach for "
        "and how main_content/real_life_examples are framed — but never at the expense of accuracy: if this angle "
        "doesn't genuinely fit a given section, quietly fall back to the clearest ordinary framing instead of "
        "forcing it."
    )
    extra_rules.append(
        f"- Vocabulary and depth must fit grade {grade} SPECIFICALLY, not just the difficulty label above — a term "
        "routine at university level (formal proofs, unexplained research-paper phrasing, domain jargon no school "
        f"curriculum at this grade would have covered) has no place here regardless of difficulty; \"{level}\" for "
        f"grade {grade} means the hardest version of what a student at THAT grade can actually absorb, never "
        "graduate-level material."
    )
    extra_rules.append(
        "- \"quick_check\": 2-4 short comprehension questions a student can answer right after reading this "
        "lecture, each with its own short answer. Every question must be answerable directly from what's already "
        "in this lecture (main_content/key_concepts), never something requiring outside knowledge. Return an empty "
        "list only if this topic genuinely has nothing checkable this way (very rare)."
    )
    extra_rules.append(
        "- STRUCTURE. A lecture follows the standard form, and these fields ARE that form — fill every one:\n"
        "  * \"objective\" — the aim, in 1-2 sentences: what the listener knows and can do afterwards. Concrete "
        "(\"explain why the discriminant decides the number of roots\"), never \"get acquainted with the topic\".\n"
        "  * \"lecture_plan\" — the plan proper: 3-5 numbered points, each a QUESTION or a heading the lecture "
        "actually answers, in the order it answers them. This is the spine of the whole document, so write it "
        "first and then write everything else to it. Do not number the strings yourself — the export numbers "
        "them.\n"
        "  * \"main_content\" — the body, written TO that plan: one part per plan point, IN THE SAME ORDER, each "
        "part opening with its point as a short heading line (\"1. <the plan point>\") followed by that part's "
        "paragraphs. A reader must be able to lay the plan beside the body and see them match point for point.\n"
        "  * \"summary\" — the conclusion, stated against the plan: what each point established.\n"
        "  * \"references\" — 3-5 real, checkable sources (author, title, year; a textbook, a standard reference "
        "work, an official curriculum document). Never invent a plausible-looking citation: if you are not "
        "confident a source exists as written, leave it out and give fewer.\n"
        "  * EMIT EVERY FIELD of the JSON shape below, in the order shown. A лекция that comes back without its "
        "plan, its conclusion or its sources is a draft, not a lecture — do not stop after \"main_content\".\n"
        "- \"main_content\" is THE core of this document — this is a lecture, not a lesson-management plan, and "
        "with no pictures and visual_blocks kept minimal, the explaining is almost entirely THIS "
        "field's job. Write 7-9 detailed paragraphs (not fewer), each a real explanatory passage, building from "
        "foundational ideas toward more advanced ones in a logical sequence, the way a textbook chapter or a real "
        "lecture transcript would. Go deeper than you normally would: spell out the reasoning behind each idea, "
        "walk through cause-and-effect chains in full, work examples all the way through in words rather than "
        "gesturing at a table for them. Real sentences joined into paragraphs, never a numbered/bulleted list of "
        "facts dressed up as paragraphs — the ONLY numbers allowed in main_content are the part headings that "
        "carry the plan's points (\"1. <plan point>\" on its own line); the material under each heading is "
        "connected sentences, never \"1. ... 2. ... 3. ...\" as a list of facts."
    )
    extra_rules.append(
        "- \"key_concepts\" and \"key_terms\": since this document has no separate lesson-management sections "
        "competing for space, cover the topic more thoroughly here than a normal lesson plan would — 6-8 "
        "key_concepts and 6-8 key_terms, each a genuinely useful, fully-written-out explanation/definition (2-3 "
        "sentences each, not a one-liner), not padding."
    )
    extra_rules_text = ("\n" + "\n".join(extra_rules)) if extra_rules else ""

    source_block = ""
    if source_text:
        source_block = f"""

SOURCE MATERIAL (primary source — this lecture must be built from this text, not from general knowledge):
\"\"\"
{source_text}
\"\"\"
Use this source as the primary basis for every section: preserve its terms, facts, definitions, and examples as
faithfully as possible while still restructuring them into the requested sections below (don't just copy paragraphs
verbatim — organize them clearly and remove only repeated filler). Do NOT invent facts that contradict or aren't supported by the source. Only
if the source genuinely lacks enough material for a required section may you carefully supplement it from your own
general knowledge — when you do, keep that supplemented content clearly factual and uncontroversial (no
speculation), since it isn't source-verified.
If this text turns out to be about a DIFFERENT topic than "{topic}" entirely — not just thin on detail, but a
genuinely different subject — IGNORE this source completely and build the lecture purely from your own knowledge of
"{topic}" instead. The topic given below always wins over a mismatched source."""

    return f"""Create an in-depth lecture (лекция) that thoroughly EXPLAINS the topic "{topic}" for grade {grade}, subject "{subject}". \
Unlike a конспект (which manages how a teacher runs the lesson — goals, activities, homework), this лекция's only \
job is to explain the topic itself, deeply and clearly, like a textbook chapter or lecture transcript.

Subject style: {subject_hint}
Difficulty: {level_text}
CRITICAL: Write ALL content in {lang_name} language. Return ONLY valid JSON, nothing else.{source_block}

RULES:
- Every text field should be DETAILED: real facts, examples, and explanations — this document has no other sections
  competing for the reader's attention, so don't hold back depth.
- NEVER mix languages
- Return ONLY the fields listed below — do not add any others (specifically: do NOT include competencies,
  objectives, lesson_program, tools, pair_work, consolidation, homework, warmup, or assessment — those are
  конспект-only fields and have no place in a лекция).{extra_rules_text}

RETURN THIS JSON:
{{
  "title": "Title about {topic}",
  "subtitle": "One-line catchy description",
  "objective": "1-2 sentences: what the listener will know and be able to do after this lecture",
  "lecture_plan": ["Question 1 the lecture answers", "Question 2", "Question 3", "Question 4"],
  "key_concepts": ["Concept 1: thorough explanation (2-3 sentences)", "Concept 2: thorough explanation", "Concept 3: thorough explanation", "Concept 4: thorough explanation", "Concept 5: thorough explanation", "Concept 6: thorough explanation"],
  "key_terms": ["Term 1: definition and example", "Term 2: definition and example", "Term 3: definition and example", "Term 4: definition and example", "Term 5: definition and example", "Term 6: definition and example"],
  "main_content": "The body of the lecture, written to the plan above: one titled part per plan point, in the same order, each part 2-3 paragraphs of 4-6 sentences. Head each part with its plan point on its own line, e.g. '1. <plan point>' followed by the paragraphs of that part.",
  "real_life_examples": ["Example 1: detailed scenario", "Example 2: detailed scenario", "Example 3: practical use case"],
  "visual_blocks": [{{"type": "table|timeline|flowchart|process|comparison|concept_map", "title": "short label", "position_after": "key_concepts|main_content|real_life_examples", "data": {{"...": "shape depends on type, see rules above"}}}}] — but per the rule above, an EMPTY list is the normal/expected answer; only include the 1 entry when it's truly warranted,
  "important_notes": ["A short, genuinely important warning/caveat/highlight — empty list if none apply"],
  "key_ideas": ["One sentence a student should remember from this lecture", "Another one"],
  "teacher_tips": ["A short practical note for the teacher delivering this topic"],
  "quick_check": [{{"question": "Short comprehension question answerable from this lecture", "answer": "Short answer"}}],
  "summary": "4-5 sentence conclusion: what was established, point by point against the plan",
  "references": ["Author, Title, year — a real, checkable source a teacher could actually find", "Second source", "Third source"]{"," if optional_json else ""}{optional_json}
}}"""



_TEST_IMAGE_RULE = (
    "IMAGE (optional, most questions have none): add \"image_query\" (a precise 2-4 word ENGLISH "
    "Wikimedia Commons search phrase) to a question ONLY when the question is genuinely about a picture — "
    "\"which labelled part is the mitochondrion\", \"identify this country on the map\", \"what shape is "
    "shown\" — never as decoration for a question answerable from its own text. Name the exact real thing "
    "the question is about (its formula, structure, place, figure), never a metaphor from a different "
    "field. At most 3 questions in the whole test should carry an image. Omit \"image_query\" entirely on "
    "every other question."
)

_QUESTION_TYPE_INFO = {
    "multiple_choice": {
        "instructions": 'Exactly 4 "options" (A-D) with exactly 1 correct answer in "correct_index".',
        "shape": lambda topic, lang: f"""{{
  "type": "multiple_choice",
  "question": "Clear, specific question about {topic}",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_index": 0,
  "explanation": "Why this answer is correct — include the key fact or reasoning"
}}""",
    },
    "true_false": {
        "instructions": 'Exactly 2 "options": the words for "True" and "False" translated into the target language (e.g. "Верно"/"Неверно" in Russian, "True"/"False" in English, "Дуруст"/"Нодуруст" in Tajik). Set "correct_index" to 0 or 1.',
        "shape": lambda topic, lang: f"""{{
  "type": "true_false",
  "question": "A factual statement about {topic} to judge as true or false",
  "options": ["<the word for True translated into {lang}>", "<the word for False translated into {lang}>"],
  "correct_index": 0,
  "explanation": "Why the statement is true or false"
}}""",
    },
    "multiple_select": {
        "instructions": '4-5 "options" with 2 or more correct answers listed in "correct_indices". Make the question text say to choose all that apply.',
        "shape": lambda topic, lang: f"""{{
  "type": "multiple_select",
  "question": "Choose ALL correct answers about {topic}",
  "options": ["Option A", "Option B", "Option C", "Option D", "Option E"],
  "correct_indices": [0, 2],
  "explanation": "Why these options are correct and the others are not"
}}""",
    },
    "open_ended": {
        "instructions": 'NO "options" — give a complete "model_answer" instead so the teacher can grade a free-text response.',
        "shape": lambda topic, lang: f"""{{
  "type": "open_ended",
  "question": "Short-answer question about {topic}",
  "model_answer": "A complete sample answer covering the key points",
  "explanation": "What a good answer should include"
}}""",
    },
}


def _test_prompt(
    topic: str,
    subject: str,
    level: str,
    grade: str,
    language: str = "English",
    question_count: int = 10,
    test_type: str = "mixed",
    source_text: str | None = None,
    code_policy: str | None = None,
) -> str:
    level_map = {
        "Лёгкий": "Beginner. Simple, straightforward questions.",
        "Средний": "Intermediate. Mix of easy and medium questions.",
        "Сложный": "Advanced. Challenging questions requiring deeper understanding.",
    }
    level_text = level_map.get(level, level_map["Средний"])
    subject_hint = _subject_hint(subject, language, grade, topic)
    lang_name = LANGUAGE_NAMES.get(language, "English")
    code_policy = code_policy or _code_relevance(subject, topic)
    code_rule = _code_relevance_rule(subject, code_policy)

    source_block = ""
    if source_text:
        source_block = f"""

SOURCE MATERIAL (primary source — every question must be answerable from this text, not from general knowledge):
\"\"\"
{source_text}
\"\"\"
Base every question on facts, terms, and examples actually present in this source. Do NOT invent facts that
contradict or aren't supported by it. Only if the source genuinely lacks enough material for the requested number
of questions may you carefully supplement from your own general knowledge — kept factual and uncontroversial.
If this text turns out to be about a DIFFERENT topic than "{topic}" entirely — not just thin on detail, but a
genuinely different subject (e.g. this looks like a document about some other topic, not "{topic}") — IGNORE this
source completely and write the test purely from your own knowledge of "{topic}" instead. The topic given below
always wins over a mismatched source; never silently write questions about whatever the source happens to cover."""

    if test_type in _QUESTION_TYPE_INFO:
        info = _QUESTION_TYPE_INFO[test_type]
        example = info["shape"](topic, lang_name)
        return f"""Create a test with {question_count} questions about "{topic}" for grade {grade}, subject "{subject}".

CRITICAL: Write ALL content in {lang_name} language. Every question, option, explanation, title, description — everything must be in {lang_name}.{source_block}

ALL {question_count} questions must be the SAME type: "{test_type}". {info['instructions']}

RULES:
1. ALL questions must be specifically about "{topic}" ONLY
2. Every question needs "type" set to exactly "{test_type}"
3. Explanations should be clear and educational — tell WHY the answer is correct
4. Questions should vary in difficulty: some easy, some medium, some hard
5. Use real-life examples and practical scenarios when possible
6. Any mathematical/scientific expression — a formula, an equation, a single variable, a unit with an exponent — must be written in LaTeX inside dollar signs: "$a^{{2}} + b^{{2}} = c^{{2}}$", "$\\frac{{1}}{{2}}$", "$\\sqrt{{x}}$". This applies in the question text, the options, and the explanation alike. Use \\frac for every fraction, ^{{}} for powers, _{{}} for indices — and the ^{{}} braces hold ONLY the exponent itself, never a variable multiplied after it ("3a^{{2}}b", never "3a^{{2b}}").
{(chr(10) + code_rule) if code_rule else ""}
{_TEACHER_SIMPLICITY_RULE}

Subject style: {subject_hint}
Difficulty: {level_text}
{_TEST_IMAGE_RULE}

Return THIS exact JSON (nothing else) — repeat this shape for all {question_count} questions:
{{
  "title": "Test: {topic}",
  "description": "{question_count} questions about {topic} for grade {grade}",
  "questions": [
    {example}
  ]
}}"""

    return f"""Create a test with {question_count} questions about "{topic}" for grade {grade}, subject "{subject}".

CRITICAL: Write ALL content in {lang_name} language. Every question, option, explanation, title, description — everything must be in {lang_name}.{source_block}

MIX FOUR QUESTION TYPES — do NOT make every question a 4-option multiple choice. Distribute roughly like this across the {question_count} questions:
- ~50% "multiple_choice" — exactly 4 options (A-D), exactly 1 correct.
- ~20% "true_false" — a factual statement about {topic} the student judges as true or false. Exactly 2 options: the words for "True" and "False" translated into {lang_name} (e.g. "Верно"/"Неверно" in Russian, "True"/"False" in English, "Дуруст"/"Нодуруст" in Tajik).
- ~20% "multiple_select" — 4-5 options where 2-3 are correct. Do NOT add "choose all that apply" (or any translation of it) to the question text yourself — the export already prints that instruction under every multiple_select question automatically; writing your own copy in the text prints it TWICE, once inline and once again right below in the export's own hint line. Just ask the question itself.
- ~10% "open_ended" — a short-answer question with NO options; the student writes a free-text answer.
If {question_count} is small, still include at least one true_false question rather than skipping the mix entirely.

RULES:
1. ALL questions must be specifically about "{topic}" ONLY
2. Every question needs a "type" field set to exactly one of: "multiple_choice", "true_false", "multiple_select", "open_ended"
3. "multiple_choice" and "true_false": use "options" (list of strings) and "correct_index" (0-based index of the single correct option)
4. "multiple_select": use "options" (4-5 strings) and "correct_indices" (list of 0-based indices, 2 or more correct)
5. "open_ended": NO "options"/"correct_index" — instead give "model_answer" (a complete sample answer) so the teacher can grade a free-text response
6. Every question needs "explanation" — for "open_ended" it should describe what a good answer must cover
7. Explanations should be clear and educational — tell WHY the answer is correct
8. Questions should vary in difficulty: some easy, some medium, some hard
9. Use real-life examples and practical scenarios when possible
10. Any mathematical/scientific expression — a formula, an equation, a single variable, a unit with an exponent — must be written in LaTeX inside dollar signs: "$a^{{2}} + b^{{2}} = c^{{2}}$", "$\\frac{{1}}{{2}}$", "$\\sqrt{{x}}$". This applies in the question text, the options, and the explanation alike. Use \\frac for every fraction, ^{{}} for powers, _{{}} for indices — and the ^{{}} braces hold ONLY the exponent itself, never a variable multiplied after it ("3a^{{2}}b", never "3a^{{2b}}").
{(chr(10) + code_rule) if code_rule else ""}
{_TEACHER_SIMPLICITY_RULE}

Subject style: {subject_hint}
Difficulty: {level_text}
{_TEST_IMAGE_RULE}

The 4 sample questions below only illustrate the JSON shape for each type — generate exactly {question_count} questions total, mixed in the proportions above, not just these 4.

Return THIS exact JSON (nothing else):
{{
  "title": "Test: {topic}",
  "description": "{question_count} questions about {topic} for grade {grade}",
  "questions": [
    {_QUESTION_TYPE_INFO['multiple_choice']['shape'](topic, lang_name)},
    {_QUESTION_TYPE_INFO['true_false']['shape'](topic, lang_name)},
    {_QUESTION_TYPE_INFO['multiple_select']['shape'](topic, lang_name)},
    {_QUESTION_TYPE_INFO['open_ended']['shape'](topic, lang_name)}
  ]
}}"""



def _visual_labels(visual: dict) -> list[str]:
    if not isinstance(visual, dict):
        return []
    data = visual.get("data") or {}
    out: list[str] = []
    for step in (data.get("steps") or []):
        if isinstance(step, dict):
            out.append(str(step.get("title") or ""))
    for row in (data.get("rows") or []):
        if isinstance(row, (list, tuple)) and row:
            out.append(str(row[0]))
    for item in (data.get("items") or []):
        if isinstance(item, dict):
            out.append(str(item.get("name") or ""))
    out.extend(str(c) for c in (data.get("categories") or []))
    return [s for s in out if s]


def _norm_label(s: str) -> str:
    s = re.sub(r"\$[^$]*\$", " ", str(s or ""))
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip().lower()


def _drop_bullets_duplicating_visual(content: dict, topic: str) -> None:
    for slide in (content.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        labels = [_norm_label(x) for x in _visual_labels(slide.get("visual") or {})]
        labels = [x for x in labels if len(x) >= 8]
        if not labels:
            continue
        bullets = slide.get("bullet_points")
        if not isinstance(bullets, list):
            continue
        kept, dropped = [], []
        for bp in bullets:
            nb = _norm_label(bp)
            if nb and any(nb.startswith(lab) or lab.startswith(nb) for lab in labels):
                dropped.append(str(bp))
                continue
            kept.append(bp)
        if dropped:
            slide["bullet_points"] = kept
            logger.info(
                f"Slide '{str(slide.get('title'))[:40]}': dropped {len(dropped)} "
                f"bullet(s) duplicating its visual (topic={topic[:40]})")


def _validate_practical_quality(content: dict, topic: str) -> None:
    individual = content.get("individual_tasks")
    group = content.get("group_tasks")
    has_individual = isinstance(individual, list) and any(
        isinstance(t, dict) and str(t.get("instructions") or "").strip() for t in individual)
    has_group = isinstance(group, list) and any(
        isinstance(t, dict) and str(t.get("instructions") or "").strip() for t in group)
    if not has_individual and not has_group:
        raise ValueError(
            f"AI returned an empty practical-tasks worksheet for topic={topic[:50]!r} "
            "(no individual or group tasks survived)")


def _validate_game_quality(content: dict, topic: str) -> None:
    rounds = content.get("rounds")
    has_round = isinstance(rounds, list) and any(
        isinstance(r, dict) and (r.get("question") or r.get("statement") or r.get("instructions")) for r in rounds)
    if not has_round:
        raise ValueError(
            f"AI returned an empty game for topic={topic[:50]!r} (no rounds survived)")


def _practical_prompt(
    topic: str,
    subject: str,
    level: str,
    grade: str,
    language: str = "English",
    source_text: str | None = None,
    code_policy: str | None = None,
) -> str:
    level_map = {
        "Лёгкий": "Beginner. Short, closely-guided tasks with one clear step at a time.",
        "Средний": "Intermediate. Multi-step tasks that still fit one lesson.",
        "Сложный": "Advanced. Open-ended tasks requiring the pupil to plan their own approach.",
    }
    level_text = level_map.get(level, level_map["Средний"])
    subject_hint = _subject_hint(subject, language, grade, topic)
    lang_name = LANGUAGE_NAMES.get(language, "English")
    code_policy = code_policy or _code_relevance(subject, topic)
    code_rule = _code_relevance_rule(subject, code_policy)
    math_rule = _MATH_NOTATION_RULE if subject in _FORMULA_SUBJECTS else ""

    source_block = ""
    if source_text:
        source_block = f"""

SOURCE MATERIAL (base every task on facts/terms/examples actually in this text):
\"\"\"
{source_text}
\"\"\"
If this text turns out to be about a DIFFERENT topic than "{topic}" entirely — not just thin on detail, but a
genuinely different subject — IGNORE this source completely and write the tasks purely from your own knowledge of
"{topic}" instead. The topic given below always wins over a mismatched source."""

    return f"""Create a set of hands-on PRACTICAL tasks about "{topic}" for grade {grade}, subject "{subject}".

CRITICAL: Write ALL content in {lang_name} language.{source_block}

RULES:
1. Every task must have the pupil DO or MAKE something concrete (measure, build, classify, interview, write,
   calculate from real data, observe and record) — never a multiple-choice question wearing a "task" label.
2. Exactly 3 INDIVIDUAL tasks, each a different difficulty (one easy, one medium, one hard) so a teacher can
   assign by pupil level within the same class.
3. Exactly 2 GROUP tasks (for 3-4 pupils each), each naming concrete roles so the work actually splits between
   group members rather than one pupil doing it alone.
4. Every task needs "expected_outcome" — what a completed answer/product actually looks like, concrete enough
   that a teacher can grade it without guessing.
5. Every field, including short ones like "group_size" and "difficulty" labels, must be written entirely in
   {lang_name} — no stray English words like "pupils" or "students" left untranslated.
6. Subject style: {subject_hint}
7. Difficulty spread: {level_text}
{(chr(10) + code_rule) if code_rule else ""}
{(chr(10) + math_rule) if math_rule else ""}
{_TEACHER_SIMPLICITY_RULE}

Return THIS exact JSON (nothing else):
{{
  "title": "A short worksheet title in {lang_name} mentioning {topic} — never the English words \"Practical tasks\"",
  "description": "One sentence on what these tasks practice",
  "individual_tasks": [
    {{"title": "Short task name", "difficulty": "easy", "instructions": "What the pupil does, step by step", "expected_outcome": "What a completed answer looks like"}},
    {{"title": "...", "difficulty": "medium", "instructions": "...", "expected_outcome": "..."}},
    {{"title": "...", "difficulty": "hard", "instructions": "...", "expected_outcome": "..."}}
  ],
  "group_tasks": [
    {{"title": "Short task name", "group_size": "group size in {lang_name}, e.g. \"3-4 \" + the {lang_name} word for pupils", "roles": ["Role 1: what they do", "Role 2: what they do", "Role 3: what they do"], "instructions": "What the group does together, step by step", "expected_outcome": "What a completed group answer looks like"}},
    {{"title": "...", "group_size": "group size in {lang_name}", "roles": ["...", "...", "..."], "instructions": "...", "expected_outcome": "..."}}
  ]
}}"""



_GAME_ROUND_SHAPES = """  {"type": "quiz", "question": "A question about the topic", "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "One short sentence saying WHY that option is the correct one"},
  {"type": "true_false", "statement": "A factual statement to judge true or false", "answer": true},
  {"type": "matching", "instructions": "Match each item on the left to its pair on the right", "pairs": [{"left": "term", "right": "its matching definition/example"}, {"left": "...", "right": "..."}, {"left": "...", "right": "..."}, {"left": "...", "right": "..."}]},
  {"type": "order", "instructions": "Put these in the correct order", "items": ["step/item 1 in correct order", "step/item 2", "step/item 3", "step/item 4"]},
  {"type": "speed", "question": "A quick-recall question", "answer": "The short correct answer", "time_limit_seconds": 15}"""


def _game_prompt(
    topic: str,
    subject: str,
    level: str,
    grade: str,
    language: str = "English",
    source_text: str | None = None,
    code_policy: str | None = None,
) -> str:
    level_map = {
        "Лёгкий": "Beginner. Simple recall, generous options, no trick questions.",
        "Средний": "Intermediate. Requires understanding, not just memorised facts.",
        "Сложный": "Advanced. Requires applying the concept, not just recalling it.",
    }
    level_text = level_map.get(level, level_map["Средний"])
    subject_hint = _subject_hint(subject, language, grade, topic)
    lang_name = LANGUAGE_NAMES.get(language, "English")
    code_policy = code_policy or _code_relevance(subject, topic)
    code_rule = _code_relevance_rule(subject, code_policy)
    math_rule = _MATH_NOTATION_RULE if subject in _FORMULA_SUBJECTS else ""

    source_block = ""
    if source_text:
        source_block = f"""

SOURCE MATERIAL (base every round on facts/terms actually in this text):
\"\"\"
{source_text}
\"\"\"
If this text turns out to be about a DIFFERENT topic than "{topic}" entirely — not just thin on detail, but a
genuinely different subject — IGNORE this source completely and write the rounds purely from your own knowledge of
"{topic}" instead. The topic given below always wins over a mismatched source."""

    return f"""Create a 12-round interactive game about "{topic}" for grade {grade}, subject "{subject}".

CRITICAL: Write ALL content in {lang_name} language.{source_block}

RULES:
1. Exactly 12 rounds total, MIXING all five types below — roughly 4 "quiz", 3 "true_false", 2 "matching",
   2 "order", 1 "speed". Never make every round the same type.
2. Every round must be answerable purely from what a pupil already learned about "{topic}" — no outside
   general-knowledge trivia unrelated to the lesson.
3. "matching": exactly 4 pairs, each a real term/definition or cause/effect from the topic — never a decorative
   pairing with only one sensible match per side removed to make it "hard".
4. "order": exactly 4 items whose correct sequence is a real fact about the topic (steps of a process, a
   chronological sequence, smallest-to-largest) — never an arbitrary list with no real order.
5. "speed": a single short-answer fact a pupil should recall within {{"time_limit_seconds": 10-20}}.
6. Subject style: {subject_hint}
7. Difficulty: {level_text}
{(chr(10) + code_rule) if code_rule else ""}
{(chr(10) + math_rule) if math_rule else ""}
{_TEACHER_SIMPLICITY_RULE}

Return THIS exact JSON (nothing else) — the shapes below show the 5 round types, repeat/mix them to reach
exactly 12 rounds:
{{
  "title": "A short game title in {lang_name} mentioning {topic} — never the English word \"Game\"",
  "description": "One sentence on what this game practices",
  "rounds": [
{_GAME_ROUND_SHAPES}
  ]
}}"""



def _presentation_prompt(
    topic: str,
    subject: str,
    level: str,
    grade: str,
    language: str = "English",
    slide_count: int = 10,
    source_text: str | None = None,
    previous_digests: list[dict] | None = None,
    variant_out: dict | None = None,
    code_policy: str | None = None,
) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    subject_hint = _subject_hint(subject, language, grade, topic)
    code_policy = code_policy or _code_relevance(subject, topic)
    code_rule = (
        "CODE RELEVANCE: code is not needed for this topic. Do not add a slide-level `code` field, "
        "Python/C++ examples, compiler/API material, or programming exercises."
        if code_policy != "needed" else
        "CODE RELEVANCE: include slide-level code only when it directly teaches this topic's programming "
        "concept; never add Python/C++ merely because the subject is Informatics."
    )

    intro_end = max(1, round(slide_count * 0.15))
    body_end = max(intro_end + 1, min(slide_count - 1, round(slide_count * 0.75)))
    intro_label = f"Slide 1" if intro_end <= 1 else f"Slides 1-{intro_end}"
    structure = (
        f"- {intro_label}: Introduction / Overview (what/who this topic is, why it matters)\n"
        f"- Slides {intro_end + 1}-{body_end}: Key facts, history, deeper analysis, quotes, achievements, significance\n"
        f"- Slides {body_end + 1}-{slide_count}: Impact, legacy, interesting facts, conclusion, summary, why this matters"
    )

    angle, shape = _pick_variant(previous_digests or [])
    if variant_out is not None:
        variant_out["angle"] = angle[:80]
        variant_out["shape"] = shape[:80]
    variation_block = (
        f"\n\nLESSON SHAPE for this deck — it decides how the material is BUILT, not just how it opens: {shape} "
        f"Framing/angle: {angle} Let both shape which examples you reach for, what the practice slides ask, and "
        "the order the ideas arrive in — never at the expense of accuracy.\n"
        + _variation_rule(previous_digests or [], angle, shape).replace("konspekt", "presentation")
    )

    figure_visual_rule = ""
    if subject in _FIGURE_SHAPES:
        catalog = "; ".join(f"{name} {hint}" for name, hint in _FIGURE_SHAPES[subject])
        figure_visual_rule = (
            f'\n   - {{"type": "figure", "data": {{"shape": "one id from this list: {catalog}", '
            '"values": ["short label strings drawn ON the figure, in that shape\'s order — see the '
            'bracketed hint after each id"]}}, "caption": "1 sentence: what it shows and what to notice"}} '
            '— an ACTUAL DRAWING of the thing the slide is about, exactly like a teacher sketches it on the '
            'board (a cube for a volume slide, a parabola on real axes for a quadratic slide, an atom\'s shell '
            'model for an element slide). Use it whenever a slide names or works with a concrete shape, body, '
            'graph, circuit or molecule — it teaches more than any bullet list could. "shape" MUST be copied '
            'exactly from the list above; an id not on it draws nothing.'
        )

    source_block = ""
    if source_text:
        source_block = f"""

SOURCE MATERIAL (primary source — this presentation must be built from this text, not from general knowledge):
\"\"\"
{source_text}
\"\"\"
Base every slide's content on facts, terms, and examples actually present in this source — preserve them faithfully
while restructuring into slide form. Do NOT invent facts that contradict or aren't supported by it. Only if the
source genuinely lacks enough material for a slide may you carefully supplement from general knowledge — kept
factual and uncontroversial.
If this text turns out to be about a DIFFERENT topic than "{topic}" entirely — not just thin on detail, but a
genuinely different subject — IGNORE this source completely and build the presentation purely from your own
knowledge of "{topic}" instead. The topic given below always wins over a mismatched source."""

    return f"""Create a rich, detailed presentation with {slide_count} slides about "{topic}" for grade {grade}, subject "{subject}".

CRITICAL: Write ALL content in {lang_name} language. Every title, bullet point, speaker note — everything must be in {lang_name}.{source_block}

Subject style: {subject_hint}{variation_block}
{code_rule}
{_TEACHER_SIMPLICITY_RULE}

RULES:
1. ALL slides must be about "{topic}" ONLY
2. Each slide MUST have a title, bullet points, and speaker notes
3. Content must be directly related to {topic}
4. Create EXACTLY {slide_count} slides — no more, no less
5. This is a SCREEN a class looks at, not a printed handout, but a slide with only 2-3 tiny fragments and nothing else reads as EMPTY and unfinished — direct feedback both ways (first "too much text", then "too little, looks weak") landed here: bullet points are SHORT phrases, roughly 4-8 words each (a clear idea, not a full clause) — never a multi-clause sentence. A slide with no "visual" gets 3-4 bullets. A slide WITH a "visual" keeps bullet_points to 1-2 short lead-in items. Alongside them every slide carries a "body" — ONE real sentence, roughly 18-30 words, that adds an actual fact/definition/reason the bullets don't already spell out (not filler, not a restatement of the bullets in prose). This is the slide's substance: a pupil reading only the bullets+body must come away having learned the specific point, not just a topic label. "speaker_notes" still carries the EXTRA depth beyond that — dates, examples, discussion prompts — not the slide's core content itself. It must be specific to "{topic}" — the actual terms, numbers, names and relationships of THIS topic, never a sentence that would fit any other lesson ("this concept is very important and widely used" is worthless filler and is not acceptable).
6. Speaker notes should be EXTENSIVE — at least 3-4 sentences with the facts/dates/names, teaching tips, discussion questions. This is where the detail lives; the slide itself stays lean because the teacher talks through it.
7. Include variety: facts, dates, quotes, achievements, significance, cultural impact — in the speaker notes and visuals, not as walls of bullet text
8. Every slide should read differently from the others — mix fact-driven, story-driven, comparison, and question-driven slides so it doesn't feel like one long repetitive list
9. "visual" — a presentation should be mostly graphics, not paragraphs: AT LEAST HALF of all slides (aim higher whenever the topic allows it) MUST carry a "visual" object, whichever type actually fits that slide's content best:
   - {{"type": "table", "data": {{"headers": ["col1", "col2", ...], "rows": [["...", "..."], ...]}}}} — for any slide-worthy grid of facts/figures
   - {{"type": "comparison", "data": {{"criteria": ["...", "..."], "items": [{{"name": "...", "values": ["one value per criterion, same order"]}}, ...]}}}} — for contrasting 2-4 things (eras, processes, options, viewpoints)
   - {{"type": "process", "data": {{"steps": [{{"title": "...", "description": "..."}}, ...]}}}} — for an ordered sequence/cause→effect chain/algorithm (3-6 steps). ANY "steps to do X" / "how to get started" / "how it works" content — installation steps, a recipe, a procedure, stages of a life cycle — is a "process", never plain bullet_points, even if it's only 2-3 steps.
   - {{"type": "chart", "data": {{"chart_type": "bar|pie|line", "categories": ["...", ...], "series": [{{"name": "...", "values": [numbers, same order/length as categories]}}, ...]}}}} — a REAL editable PowerPoint chart (not a table) for anything that is fundamentally NUMBERS: proportions/shares → "pie"; comparing sizes across categories → "bar"; a trend or change over time → "line". Prefer this over "table" whenever the data is numeric — a chart communicates numbers faster than a grid of digits. Only use real, well-established figures (known statistics, measured quantities, textbook values) or clearly illustrative/approximate teaching figures (e.g. relative energy shares in a process) — never invent precise-looking statistics you're not confident are correct; if genuinely unsure, use "process" or "table" instead so nothing false-looking gets presented as fact.{figure_visual_rule}
   Before defaulting to plain bullet_points, actively look for a way to reshape THIS slide's content into one of the four shapes above — most factual/historical/scientific content can be told as a timeline (process), a breakdown (table), a contrast (comparison), or numbers (chart) instead of a list. Only leave a slide as plain bullet_points when it truly resists all four (e.g. a single open question, a short intro/transition beat). A slide with "visual" keeps bullet_points to at most 1-2 short items (a lead-in fragment, not a sentence) — the visual itself carries the content, bullet_points must never repeat what's already inside the visual's data.

10. FORMULAS. Every mathematical or scientific expression — a formula, an equation, a single variable, a unit
    with an exponent — must be written in LaTeX inside dollar signs: "$a^{{2}} + b^{{2}} = c^{{2}}$",
    "$\\frac{{1}}{{2}}$", "$\\sqrt{{x}}$", "$\\pi r^{{2}}$", "$\\alpha$", "$v = \\frac{{s}}{{t}}$". The export turns
    these into REAL PowerPoint equation objects — a stacked fraction is stacked, an exponent is raised, and it
    stays sharp on a projector — but only from LaTeX; plain "1/2" or "x2" prints as typed. Use \\frac for every
    fraction, ^{{}} for powers, _{{}} for indices, \\sqrt{{}} for roots, and \\pi/\\alpha/\\beta/\\Delta for Greek
    letters. Keep formulas SHORT on a slide — one equation per bullet, the derivation belongs in speaker_notes.
    The ^{{}} braces hold ONLY the exponent itself, never a variable multiplied after it — a confirmed real
    mistake wrote "3a^{{2b}}" (meaning "3 times a to the power of 2b") when it meant "3a^{{2}}b" (three times
    a-squared times b); close the ^{{}} braces right after the exponent digit, then write the next factor outside.

SLIDE ARC (scaled to {slide_count} slides — adjust the exact split to fit the topic naturally).
This deck is for ONE 45-60 minute lesson, so it has to walk a class through the topic, not just list facts:
opening (what today is about, why it matters) -> the key concepts named -> each concept explained on its own
slide -> a worked example -> a visual/scheme that shows the idea -> a second example or practice task ->
where it is used in real life -> questions for the class -> a short task for pupils -> recap and conclusion.
Fit that arc to the {slide_count} slides asked for, dropping or merging beats where the topic is simple and
spending two slides on a beat where it is hard — the arc is the lesson's shape, not a fixed checklist:
{structure}

For each slide, include:
- "title": engaging slide title
- "bullet_points": 3-4 short phrases (4-8 words each), NOT full sentences (or 1-2 phrases if this slide has a "visual" — see rule 9)
- "body": REQUIRED — ONE real sentence (~18-30 words) adding a specific fact/definition/reason this exact topic needs, not a restatement of the bullets. See rule 5.
- "speaker_notes": extensive notes for the teacher (3-4 sentences minimum) — this carries the actual detail
- "visual": REQUIRED on at least half of all slides — see rule 9; omit the key only on slides that genuinely can't be reshaped into one
- "kind": which KIND of slide this is, so the deck is built from several different layouts instead of one repeated
  one. Exactly one of: "intro" (the opening slide), "concepts" (the key terms named), "explanation" (an idea
  unpacked), "formula" (a slide whose point IS an equation), "example" (a worked example, problem then answer),
  "task" (something the pupils do), "summary" (the closing recap). Use them in a natural teaching order and do
  NOT make every slide "explanation".
- "code": OPTIONAL — ONLY for a subject where the slide's actual point is a piece of REAL, RUNNABLE code (Informatics/
  programming topics — a language construct, an algorithm walked through in a specific language, a worked coding
  example). Never invent one for a subject that merely mentions computers in passing. {{"language": "python",
  "snippet": "for i in range(5):
    print(i)", "explanation": "One sentence saying what this does"}}. The
  snippet must be real, correct, idiomatic code — at most 8 short lines, using 
 for line breaks, no pseudo-code
  and no placeholder "...". Omit this key entirely on every slide it does not apply to.
- "callout": OPTIONAL, and genuinely optional — at most 2-3 slides in the whole deck should have one. A single
  short sentence the class must not miss, lifted out of the flow into its own box: {{"kind": "...", "text":
  "..."}}. "kind" is exactly one of "important" (a rule that must not be got wrong), "remember" (something to
  memorise), "fact" (a striking aside that makes the topic stick), "why" (the reason behind what was just
  stated). Write the text as ONE sentence, under 140 characters, and never as a restatement of a bullet that is
  already on the slide — a callout that repeats the slide is worse than no callout.

Return THIS exact JSON:
{{
  "title": "Full presentation title about {topic}",
  "description": "Brief 1-2 sentence description of the presentation",
        "slides": [
    {{
      "title": "Engaging slide title",
      "kind": "explanation",
      "callout": {{"kind": "remember", "text": "One sentence the class must not miss — omit this key entirely on most slides"}},
      "bullet_points": ["Short punchy fragment", "Another short fragment", "One more, still brief"],
      "body": "Two to three sentences that actually explain this slide's point using this topic's own terms, numbers and relationships — what it is, when it holds, what follows from it.",
      "speaker_notes": "Extensive teaching notes with the actual facts/dates/names, discussion questions, and tips for the teacher. At least 3-4 sentences — this is where the detail lives, not on the slide."
    }},
    {{
      "title": "A slide whose point IS the equation, e.g.",
      "kind": "formula",
      "bullet_points": ["$a^{{2}} + b^{{2}} = c^{{2}}$", "Short reading of what it says"],
      "speaker_notes": "Extensive teaching notes. At least 3-4 sentences."
    }},
    {{
      "title": "A slide whose content is naturally a comparison, e.g.",
      "bullet_points": ["Short lead-in fragment"],
      "speaker_notes": "Extensive teaching notes with additional facts, discussion questions, and tips for the teacher. At least 3-4 sentences.",
      "visual": {{"type": "comparison", "data": {{"criteria": ["Criterion A", "Criterion B"], "items": [{{"name": "Option 1", "values": ["...", "..."]}}, {{"name": "Option 2", "values": ["...", "..."]}}]}}}}
    }},
    {{
      "title": "A slide whose content is naturally numeric, e.g.",
      "bullet_points": ["Short lead-in fragment"],
      "speaker_notes": "Extensive teaching notes with additional facts, discussion questions, and tips for the teacher. At least 3-4 sentences.",
      "visual": {{"type": "chart", "data": {{"chart_type": "bar", "categories": ["Category A", "Category B", "Category C"], "series": [{{"name": "Series label", "values": [42, 27, 15]}}]}}}}
    }}
  ]
}}"""



def _roadmap_prompt(
    mode: str,
    grade: str,
    level: str,
    language: str,
    day_count: int,
    topic_list_text: str | None = None,
    goal_topic: str | None = None,
    subject: str | None = None,
) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    known_subjects = list(_SUBJECT_KONSPEKT_PROMPTS.keys())

    if mode == "topic_list":
        given_topics = [t.strip() for t in (topic_list_text or "").splitlines() if t.strip()]
        n_given = len(given_topics)
        exam_budget = day_count - n_given
        if exam_budget >= 0:
            fit_rule = (
                f"There are exactly {n_given} lesson days — use ONE topic per lesson day, in order, NEVER "
                f"merging two+ topics onto the same day and NEVER splitting one topic across multiple days. "
                f"The other {exam_budget} day(s) are exam/review days interspersed among the lessons at natural "
                f"checkpoints (skip this if {exam_budget} is 0)."
            )
        else:
            fit_rule = (
                f"You were given {n_given} topics but there are only {day_count} lesson/exam days — you MUST "
                f"compress. When a day covers more than one original topic, that day's \"topic\" field MUST "
                f"literally combine the ACTUAL given topic names (join 2-3 of them, e.g. with \"; \"), NEVER "
                f"invent a new abstract summary phrase that replaces them. A teacher must recognize their own "
                f"topics in the output. Only group topics that are genuinely closely related — it's fine for a "
                f"combined \"topic\" field to be a bit long, that's better than losing the original wording."
            )
        source_instructions = f"""The teacher gave this list of topics they want covered, in this EXACT order — this is the SOURCE OF TRUTH for the whole course, likely an official syllabus whose sequence is already pedagogically deliberate. Do not replace it with a curriculum of your own invention; every day's topic must be traceable back to one or more of these exact given topics.
---
{topic_list_text}
---
{fit_rule}

ORDER IS FIXED: process the given topics top-to-bottom EXACTLY as listed and never reorder, reshuffle, or reprioritize them by your own judgment of what "makes more sense" — the 1st given topic must end up on the earliest lesson day, the last given topic on the latest lesson day, with every lesson day in between strictly following the same top-to-bottom sequence (exam days inserted between them don't change this). Deduplicate only EXACT repeated lines; do not merge or drop anything else beyond what {"the compression rule above allows" if exam_budget < 0 else "'one topic per day' already implies"}."""
    else:
        source_instructions = f"""The teacher's goal is: "{goal_topic}". They want to teach this to students starting from ABSOLUTE ZERO — assume no prior knowledge.
Design a complete curriculum from first principles to a solid working competency. Each day must build directly on the previous ones: order topics from foundational to advanced, never introduce a concept before its prerequisites, and never repeat a previous day's topic."""

    if subject:
        subject_instructions = f'The subject is "{subject}".'
    else:
        subject_instructions = f"""Figure out the single best-fitting subject for this course yourself from EXACTLY this list (copy one value verbatim, do not invent a new one):
{json.dumps(known_subjects, ensure_ascii=False)}"""

    total_slots = day_count
    exam_guidance = (
        f"Out of the {total_slots} total days, insert periodic review/exam days at natural checkpoints "
        f"(e.g. roughly every 5-8 lessons, and as the final day if the course is long enough) so students "
        f"are tested on what they just learned before moving on. Mark those with \"day_type\": \"exam\" and "
        f"give them a \"topic\" describing what material the exam covers (e.g. \"Review exam: lessons 1-6\"). "
        f"Every other day is \"day_type\": \"lesson\". Do not make day 1 an exam. For very short courses "
        f"(under 5 days) it's fine to have zero exam days — do not force one in."
        if total_slots >= 5 else
        "This course is too short for a dedicated exam day — make every day \"day_type\": \"lesson\"."
    )

    return f"""Design a {day_count}-day teaching curriculum (course roadmap) for grade {grade}.

{subject_instructions}

{source_instructions}

{exam_guidance}

CRITICAL: Write ALL text ("title", "subject", every "topic", every "goal") in {lang_name} language — EXCEPT "subject", which must be copied verbatim from the list above if one was given (that list is not translated). Return ONLY valid JSON, nothing else. No filler commentary or meta-text anywhere.

Difficulty: {level}

Return THIS exact JSON — exactly {day_count} entries in "topics", "day_index" starting at 0:
{{
  "title": "Short course title",
  "subject": "{subject or 'One value copied verbatim from the subject list'}",
  "topics": [
    {{"day_index": 0, "day_type": "lesson", "topic": "Specific, concrete lesson topic for day 1", "goal": "One sentence: what students can do after this lesson"}}
  ]
}}"""


_VARAQ_BLOCK_SHAPES = """  {"type": "word_bank", "instructions": "Circle every word from the bank that belongs to the requested group", "word_bank": ["correct term 1", "correct term 2", "a distractor that does NOT belong", "another distractor"], "correct": ["correct term 1", "correct term 2"]},
  {"type": "cloze", "instructions": "Fill in each blank", "text": "A sentence or short passage with each blank written as ___(1)___, ___(2)___ in order", "blanks": ["answer for blank 1", "answer for blank 2"]},
  {"type": "matching", "instructions": "Match each item on the left to its pair on the right", "left": ["term/question 1", "term/question 2", "term/question 3"], "right": ["matching answer A", "matching answer B", "matching answer C"], "correct_pairs": [[0, 1], [1, 2], [2, 0]]},
  {"type": "table_fill", "instructions": "Complete the table", "headers": ["col1", "col2", "col3"], "rows": [["given value", "", ""], ["", "given value", ""]], "answer_rows": [["given value", "computed value", "computed value"], ["computed value", "given value", "computed value"]]},
  {"type": "picture_order", "instructions": "Write the correct order number in each circle", "items": [{"image_query": "precise 2-4 word ENGLISH Wikimedia Commons search phrase for item 1"}, {"image_query": "..."}, {"image_query": "..."}, {"image_query": "..."}], "correct_order": [3, 1, 4, 2]}"""

# "diagram_label" only ever uses shape "compass" — the only diagram this
# renderer can draw. Offered unconditionally but the rule text below makes
# clear it is a rare fit, not a default choice.
_VARAQ_DIAGRAM_BLOCK_SHAPE = """,
  {"type": "diagram_label", "instructions": "Label the diagram", "shape": "compass", "labels": ["label for the N position", "label for the E position", "label for the S position", "label for the W position"]}"""

# Only offered when code_policy=="needed" — a programming topic (e.g. "Python
# lists") cannot be taught through word banks/matching/tables alone, which
# forced the model toward Python-trivia (release dates, who invented it)
# instead of actual coding practice. This gives it a real code exercise shape.
_VARAQ_CODE_BLOCK_SHAPE = """,
  {"type": "code_trace", "instructions": "Read the code and answer the question", "language": "python", "code": "a short, real, runnable snippet (<=8 lines) directly on this topic", "question": "What does this code print / what is the value of X after it runs?", "answer": "the exact correct answer"}"""


def _varaq_prompt(
    topic: str,
    subject: str,
    level: str,
    grade: str,
    language: str = "English",
    source_text: str | None = None,
    code_policy: str | None = None,
) -> str:
    level_map = {
        "Лёгкий": "Beginner. Very short, generous word banks, obvious distractors.",
        "Средний": "Intermediate. Mix of recall and light reasoning.",
        "Сложный": "Advanced. Requires applying the concept, not just recalling it.",
    }
    level_text = level_map.get(level, level_map["Средний"])
    subject_hint = _subject_hint(subject, language, grade, topic)
    lang_name = LANGUAGE_NAMES.get(language, "English")
    code_policy = code_policy or _code_relevance(subject, topic)
    code_rule = _code_relevance_rule(subject, code_policy)
    math_rule = _MATH_NOTATION_RULE if subject in _FORMULA_SUBJECTS else ""

    source_block = ""
    if source_text:
        source_block = f"""

SOURCE MATERIAL (base every block on facts/terms actually in this text):
\"\"\"
{source_text}
\"\"\"
If this text turns out to be about a DIFFERENT topic than "{topic}" entirely — not just thin on detail, but a
genuinely different subject — IGNORE this source completely and write the worksheet purely from your own
knowledge of "{topic}" instead. The topic given below always wins over a mismatched source."""

    code_type_available = subject in _CODE_SUBJECTS and code_policy == "needed"
    block_shapes = _VARAQ_BLOCK_SHAPES + _VARAQ_DIAGRAM_BLOCK_SHAPE + (_VARAQ_CODE_BLOCK_SHAPE if code_type_available else "")
    type_count = "6" if code_type_available else "5"
    code_type_rule = (
        "9. This topic genuinely requires code — use \"code_trace\" for the blocks where reading/tracing code is "
        "the actual point (never force the other types to describe code in prose instead of showing it)."
        if code_type_available else ""
    )

    return f"""Create a printable A4 worksheet ("рабочий лист") with 4-8 short exercises about "{topic}" for grade {grade}, subject "{subject}".

CRITICAL: Write ALL content in {lang_name} language.{source_block}

RULES:
1. Pick 4-8 blocks from the {type_count} types below, MIXING at least 2 different types — never make every block
   the same type. Choose only the types that genuinely fit this topic (e.g. "matching" for term/definition pairs,
   "table_fill" for data with a pattern to compute, "cloze" for a short descriptive passage, "word_bank" for
   sorting/classifying terms).
2. "word_bank": the bank includes 1-2 distractors that do NOT belong, so circling is a real decision, not just
   copying the whole list. "correct" lists only the ones that truly belong.
3. "cloze": write a genuine short passage/sentence (not a single word) with each blank marked in order; "blanks"
   gives the exact correct word/phrase for each blank, same order.
4. "matching": 3-5 pairs; "correct_pairs" are 0-based [left_index, right_index] pairs — every left item has
   exactly one correct right item.
5. "table_fill": "rows" is what the PUPIL sees — some cells already filled in as given information, the rest
   empty strings ""; "answer_rows" is the SAME table with every cell correctly filled in, same shape. Never leave
   "rows" with every cell empty — there must be enough given information to solve it.
6. "picture_order": exactly 4 items, each a precise real-world photo search phrase (seasons, life-cycle stages,
   historical events in sequence, process steps) — never use this for topics with no real sequence to order.
   "correct_order" says what number belongs under each item AS LISTED (items are shown in a scrambled order on
   purpose); e.g. correct_order [3,1,4,2] means the 1st listed item is actually 3rd in the true sequence.
7. "diagram_label": ONLY use "shape": "compass", and ONLY for a topic genuinely about cardinal directions/map
   orientation — never for any other topic, there is no other diagram available. "labels" are the 4 correct
   answers in this fixed order: North, East, South, West.
8. Every block needs "instructions" — one short, specific sentence (not generic "fill in the blanks").
9. Subject style: {subject_hint}
10. Difficulty: {level_text}
{code_type_rule}
{(chr(10) + code_rule) if code_rule else ""}
{(chr(10) + math_rule) if math_rule else ""}
{_TEACHER_SIMPLICITY_RULE}

Return THIS exact JSON (nothing else) — the shapes below show the {type_count} block types, pick and repeat/mix 4-8 of them:
{{
  "title": "A short worksheet title in {lang_name} mentioning {topic}",
  "description": "One sentence on what this worksheet practices",
  "blocks": [
{block_shapes}
  ]
}}"""


def _validate_varaq_quality(content: dict, topic: str) -> None:
    blocks = content.get("blocks")
    has_block = isinstance(blocks, list) and any(
        isinstance(b, dict) and b.get("instructions") for b in blocks)
    if not has_block:
        raise ValueError(
            f"AI returned an empty worksheet for topic={topic[:50]!r} (no blocks survived)")


def _render_varaq_diagrams(content: dict, topic: str) -> None:
    from app.figure_builder import save_figure
    for block in (content.get("blocks") or []):
        if not isinstance(block, dict) or block.get("type") != "diagram_label":
            continue
        shape = str(block.get("shape") or "compass")
        try:
            path = save_figure(shape, [])
        except Exception as e:
            logger.warning(f"Varaq diagram render failed for topic={topic[:50]}: {e}")
            path = None
        if path:
            block["image"] = path
        else:
            logger.info(f"Varaq diagram_label dropped (unknown shape {shape!r}) topic={topic[:50]}")


async def _render_varaq_images(content: dict, topic: str) -> None:
    blocks = [b for b in (content.get("blocks") or [])
             if isinstance(b, dict) and b.get("type") == "picture_order"]
    if not blocks:
        return
    from app.image_builder import fetch_lesson_images
    for block in blocks:
        items = [it for it in (block.get("items") or []) if isinstance(it, dict)]
        for item in items:
            query = str(item.get("image_query") or "").strip()
            if not query:
                continue
            try:
                found = await fetch_lesson_images([query], count=1, grade=content.get("grade"),
                                                  language=content.get("language"),
                                                  subject=content.get("subject"))
                if found:
                    path = found[0]["path"]
                    _shrink_image_file(path, max_dim=360)
                    item["image"] = {"path": path, "credit": found[0].get("credit", "")}
            except Exception as e:
                logger.warning(f"Varaq picture_order image fetch failed for topic={topic[:50]} query={query[:50]}: {e}")


def _shrink_image_file(path: str, max_dim: int = 360) -> None:
    """picture_order shows these at ~110pt wide; the fetched source can be
    several megapixels, which bloated a 4-picture worksheet PDF past 10MB.
    Downsize the saved file in place so it embeds at a sane size."""
    try:
        from PIL import Image as PILImage
        full = os.path.join(os.path.dirname(__file__), "..", path.lstrip("/"))
        with PILImage.open(full) as im:
            if max(im.size) <= max_dim:
                return
            fmt = im.format or "PNG"
            im.thumbnail((max_dim, max_dim), PILImage.LANCZOS)
            im.save(full, fmt)
    except Exception as e:
        logger.warning(f"Image shrink failed for {path}: {e}")


def _regenerate_varaq_block_prompt(topic: str, subject: str, level: str, grade: str, language: str,
                                   existing_instructions: list[str]) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    subject_hint = _subject_hint(subject, language, grade, topic)
    existing_text = "\n".join(f"- {t}" for t in existing_instructions) or "(none)"
    code_policy = _code_relevance(subject, topic)
    code_rule = _code_relevance_rule(subject, code_policy)
    code_type_available = subject in _CODE_SUBJECTS and code_policy == "needed"
    block_shapes = _VARAQ_BLOCK_SHAPES + _VARAQ_DIAGRAM_BLOCK_SHAPE + (_VARAQ_CODE_BLOCK_SHAPE if code_type_available else "")
    type_count = "6" if code_type_available else "5"

    return f"""Create exactly ONE new worksheet block about "{topic}" for grade {grade}, subject "{subject}".

CRITICAL: Write ALL content in {lang_name} language. Return ONLY valid JSON, nothing else.

Pick whichever of the {type_count} types below best fits this topic.

Subject style: {subject_hint}
{(chr(10) + code_rule) if code_rule else ""}
{_TEACHER_SIMPLICITY_RULE}

This block MUST be different in focus from these existing blocks on the same worksheet:
{existing_text}

Return THIS exact JSON (nothing else) — pick ONE shape from these {type_count}:
{block_shapes}"""


PROMPTS = {
    "konspekt": _konspekt_prompt,
    "lektsiya": _lecture_prompt,
    "test": _test_prompt,
    "prezentatsiya": _presentation_prompt,
    "amaliy": _practical_prompt,
    "igra": _game_prompt,
    "varaq": _varaq_prompt,
}


def _fix_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    first_brace = text.find("{")
    if first_brace == -1:
        return text
    text = text[first_brace:]

    depth = 0
    in_str = False
    escape = False
    end_pos = len(text)
    for i, c in enumerate(text):
        if escape:
            escape = False
            continue
        if c == '\\':
            if in_str:
                escape = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if not in_str:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end_pos = i + 1
                    break
    text = text[:end_pos]

    if not in_str:
        pass
    else:
        text += '"'

    def fix_newlines_in_strings(text):
        result = []
        in_string = False
        esc = False
        i = 0
        while i < len(text):
            c = text[i]
            if esc:
                result.append(c)
                esc = False
                i += 1
                continue
            if c == '\\' and in_string:
                result.append(c)
                esc = True
                i += 1
                continue
            if c == '"':
                in_string = not in_string
                result.append(c)
                i += 1
                continue
            if in_string and c == '\n':
                result.append('\\n')
                i += 1
                continue
            if in_string and c == '\r':
                i += 1
                continue
            result.append(c)
            i += 1
        return ''.join(result)

    text = fix_newlines_in_strings(text)

    def fix_unquoted(match):
        key_part = match.group(1)
        value_part = match.group(2).strip()
        if value_part and value_part[0] in ('"', '[', '{') or re.match(r'^-?\d', value_part) or value_part in ('true', 'false', 'null'):
            return match.group(0)
        value_part = value_part.rstrip(',')
        fixed = f'{key_part}"{value_part}"'
        if match.group(0).rstrip().endswith(','):
            fixed += ','
        return fixed

    text = re.sub(r'("(?:[^"\\]|\\.)*"\s*:\s*)([^"\[\{\d\-][^,}\]]*?)(?=\s*[,}\]])', fix_unquoted, text)
    text = re.sub(r',\s*([}\]])', r'\1', text)

    depth2 = 0
    in_str2 = False
    esc2 = False
    for c in text:
        if esc2:
            esc2 = False
            continue
        if c == '\\' and in_str2:
            esc2 = True
            continue
        if c == '"':
            in_str2 = not in_str2
            continue
        if not in_str2:
            if c == '{':
                depth2 += 1
            elif c == '}':
                depth2 -= 1
    while depth2 > 0:
        text += '}'
        depth2 -= 1

    return text


_JSON_STRUCTURAL = set('"\\/')
_JSON_AMBIGUOUS = set("bfnrt")


def _escape_literal(lit: str, mode: str) -> str:
    out = []
    i, n = 0, len(lit)
    in_math = (mode == "all")
    while i < n:
        c = lit[i]
        if c == "$" and mode == "spans":
            in_math = not in_math
            out.append(c)
            i += 1
            continue
        if c != "\\":
            out.append(c)
            i += 1
            continue
        nxt = lit[i + 1] if i + 1 < n else ""
        if nxt in _JSON_STRUCTURAL:
            out.append(lit[i:i + 2])
            i += 2
        elif nxt == "u" and re.fullmatch(r"[0-9a-fA-F]{4}", lit[i + 2:i + 6] or ""):
            out.append(lit[i:i + 6])
            i += 6
        elif nxt in _JSON_AMBIGUOUS and not in_math:
            out.append(lit[i:i + 2])
            i += 2
        else:
            out.append("\\\\")
            i += 1
    return "".join(out)


def _fix_backslashes(text: str) -> str:
    out = []
    i, n = 0, len(text)
    last_key = None
    while i < n:
        c = text[i]
        if c != '"':
            out.append(c)
            i += 1
            continue
        j = i + 1
        buf = []
        while j < n:
            ch = text[j]
            if ch == "\\" and j + 1 < n:
                buf.append(text[j:j + 2])
                j += 2
                continue
            if ch == '"':
                break
            buf.append(ch)
            j += 1
        literal = "".join(buf)
        k = j + 1
        while k < n and text[k] in " \t\r\n":
            k += 1
        is_key = k < n and text[k] == ":"
        if is_key:
            mode = "none"
        elif last_key == "latex":
            mode = "all"
        elif "$" in literal:
            mode = "spans"
        else:
            mode = "none"
        out.append('"' + _escape_literal(literal, mode) + '"')
        if is_key:
            last_key = literal
        i = j + 1
    return "".join(out)



_MISSING_GLYPH_HYPHENS = str.maketrans({"\u2010": "-", "\u2011": "-"})


def _normalize_missing_glyphs(obj):
    if isinstance(obj, str):
        # Some model responses double-escape ordinary quotes inside prose and
        # code (for example: score = \"10\"). They are JSON artifacts, not
        # intended backslashes in the rendered school material.
        normalized = obj.translate(_MISSING_GLYPH_HYPHENS).replace('\\"', '"')
        return re.sub(r'\\n(?=\s*#)', "\n", normalized)
    if isinstance(obj, dict):
        return {k: _normalize_missing_glyphs(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_missing_glyphs(v) for v in obj]
    return obj


def _parse_json(text: str) -> dict:
    text = text.strip()
    for candidate in (_fix_backslashes(text), text):
        try:
            return _normalize_missing_glyphs(json.loads(candidate))
        except json.JSONDecodeError:
            pass
    fixed = _fix_json(text)
    for candidate in (_fix_backslashes(fixed), fixed, fixed.replace("'", '"')):
        try:
            return _normalize_missing_glyphs(json.loads(candidate))
        except json.JSONDecodeError:
            pass
    raise json.JSONDecodeError(
        f"Could not parse JSON. First 300 chars: {text[:300]}",
        text, 0
    )





_TAJIK_RUSSIAN_FIXES = {
    "Термины:": "Истилоҳот:",
    "Пример:": "Намуна:",
    "Пример": "Намуна",
    "Время урока:": "Вақти дарс:",
    "Компетенции": "Салоҳиятҳо",
    "Цели урока": "Мақсадҳои дарс",
    "Ключевые понятия": "Мафҳумҳои асосӣ",
    "Материалы урока": "Маводи дарс",
    "Домашнее задание": "Супориши хонагӣ",
    "Итоги урока": "Хулосаи дарс",
    "Навыки": "Малакаҳо",
    "Практика": "Амалиёт",
    "Задание": "Супориш",
    "Тема": "Мавзӯъ",
    "Цель": "Мақсад",
    "Вопросы": "Саволҳо",
    "Ответ": "Ҷавоб",
    "Запомните": "Дар хотир доред",
    "Попробуйте": "Санҷед",
    "Используйте": "Истифода баред",
    "Важно": "Муҳим",
    "Интересный факт": "Факти ҷолиб",
    "Полезно": "Муфид",
    "Введение": "Муқаддима",
    "Заключение": "Хулоса",
    "Резюме": "Хулоса",
    "Ключевые выводы": "Хулосаҳои асосӣ",
    "Вопросы для обсуждения": "Саволҳо барои баррасӣ",
    "Дополнительные материалы": "Маводи иловагӣ",
    "Ключевые моменты": "Нуқтаҳои асосӣ",
    "Основные": "Асосӣ",
    "Определение": "Таъриф",
    "Примеры": "Намунаҳо",
    "Теория": "Назария",
    "Практическое применение": "Татбиқи амалӣ",
    "Итог": "Натиҷа",
    "Главное": "Асосӣ",
    "Вывод": "Хулоса",
    "Запомните главное": "Асосиро дар хотир доред",
    "Для учителя": "Барои омӯзгор",
    "Для студентов": "Барои донишҷӯён",
    "Для учащихся": "Барои хонандагон",
    "Задачи урока": "Вазифаҳои дарс",
    "План урока": "Нақшаи дарс",
    "Ход урока": "Ҷараёни дарс",
    "Тип урока": "Навъи дарс",
    "Форма урока": "Шакли дарс",
    "Оборудование": "Таҷҳизот",
    "Учебник": "Китоби дарсӣ",
    "Учебное пособие": "Кӯмаки таълимӣ",
    "Тетрадь": "Дафтар",
    "Доска": "Лавҳа",
    "Книга": "Китоб",
    "Абзац": "Параграф",
    "Предложение": "Ҷумла",
    "Слово": "Калима",
    "Значение": "Аҳамият",
    "Смысл": "Мақсад",
    "Суть": "Моҳият",
    "Проблема": "Мушкилӣ",
    "Вопрос": "Савол",
    "Решение": "Ҳалли",
    "Анализ": "Таҳлил",
    "Сравнение": "Муқоиса",
    "Результат": "Натиҷа",
    "Прогресс": "Пешрафт",
    "Развитие": "Рушд",
    "Изменение": "Тағйирот",
    "Процесс": "Раванд",
    "Система": "Система",
    "Метод": "Усул",
    "Способ": "Роҳ",
    "Приём": "Усул",
    "Форма": "Шакл",
    "Содержание": "Мундариҷа",
    "Структура": "Тарҳ",
    "Состав": "Таркиб",
    "Часть": "Қисм",
    "Вид": "Намуд",
    "Тип": "Навъ",
    "Роль": "Нақш",
    "Влияние": "Таъсир",
    "Связь": "Алоқа",
    "Отношение": "Муносибат",
    "Условие": "Шарт",
    "Причина": "Сабаб",
    "Следствие": "Оқибат",
    "Факт": "Воқеият",
    "Доказательство": "Исбот",
    "Источник": "Манбаъ",
    "Период": "Давра",
    "Эпоха": "Давра",
    "Дата": "Сана",
    "Событие": "Рӯйдод",
    "Деятель": "Шахсият",
    "Автор": "Муаллиф",
    "Произведение": "Эҷодӣ",
    "Литература": "Адабиёт",
    "Поэзия": "Шеър",
    "Проза": "Наср",
    "Рассказ": "Ҳикоя",
    "Стихотворение": "Байт",
    "Газель": "Ғазал",
    "Касыда": "Қасида",
    "Жанр": "Жанр",
    "Идея": "Андарз",
    "Символ": "Рамз",
    "Образ": "Тасвир",
    "Герой": "Қаҳрамон",
    "Сюжет": "Маҷрои воқеа",
    "Конфликт": "Зiddӣ",
    "Эпитет": "Сифат",
    "Метафора": "Метафора",
    "Гипербола": "Барзиёд",
    "Олицетворение": "Шахсиятнок",
    "Фольклор": "Халқӣ",
    "Миф": "Афсона",
    "Легенда": "Ривоят",
    "Сказка": "Афсона",
    "Пословица": "Мақол",
    "Поговорка": "Забондаст",
    "Загадка": "Панд",
    "Творчество": "Эҷодкорӣ",
    "Вдохновение": "Илҳом",
    "Красота": "Зебоӣ",
    "Правда": "Ҳақиқат",
    "Ложь": "Дурӯғ",
    "Честь": "Номус",
    "Совесть": "Виҷдон",
    "Доброта": "Некӣ",
    "Зло": "Бадӣ",
    "Любов": "Муҳаббат",
    "Ненависть": "Нафрат",
    "Радость": "Шодӣ",
    "Грусть": "Ғам",
    "Храбрость": "Шуҷоат",
    "Трусость": "Тарс",
    "Мудрость": "Хирад",
    "Глупость": "Нодонӣ",
    "Справедливость": "Адолат",
    "Несправедливость": "Бедодӣ",
    "Свобода": "Озодӣ",
    "Равенство": "Баробарӣ",
    "Братство": "Бародарӣ",
    "Мир": "Оштӣ",
    "Война": "Ҷанг",
    "Труд": "Меҳнат",
    "Знание": "Дониш",
    "Невежество": "Нодонӣ",
    "Вера": "Имон",
    "Надежда": "Умед",
    "Учитель": "Омӯзгор",
    "Ученик": "Хонанда",
    "Студент": "Донишҷӯй",
    "Класс": "Синф",
    "Школа": "Мактаб",
    "Университет": "Донишгоҳ",
    "Занятие": "Дарс",
    "Урок": "Дарс",
    "Экзамен": "Имтиҳон",
    "Оценка": "Баҳо",
    "Отлично": "Аъло",
    "Хорошо": "Хуб",
}


_STRAY_SCRIPT_PATTERN = re.compile(
    r'[^\u0000-\u007F\u0400-\u04FF\u00A0\u00AB\u00B0-\u00B3\u00BB\u2010-\u2015\u2018-\u201F\u2212\u221A\u2260]+'
)


_LEGACY_TAJIK_GLYPH_FIXES = {
    'њ': 'ҳ', 'Њ': 'Ҳ',
    'ќ': 'қ', 'Ќ': 'Қ',
    'ѓ': 'ғ', 'Ѓ': 'Ғ',
    'љ': 'ҷ', 'Љ': 'Ҷ',
    'ї': 'ӣ', 'Ї': 'Ӣ',
}


def fix_legacy_tajik_glyphs(text: str) -> str:
    return ''.join(_LEGACY_TAJIK_GLYPH_FIXES.get(c, c) for c in text)


def _fix_tajik(text: str) -> str:
    for ru, tg in _TAJIK_RUSSIAN_FIXES.items():
        text = text.replace(ru, tg)
    text = _STRAY_SCRIPT_PATTERN.sub('', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def _fix_json_strings(obj, fn):
    if isinstance(obj, str):
        return fn(obj)
    elif isinstance(obj, list):
        return [_fix_json_strings(item, fn) for item in obj]
    elif isinstance(obj, dict):
        return {k: _fix_json_strings(v, fn) for k, v in obj.items()}
    return obj


def _translate_json(data: dict, target_lang: str) -> dict:
    if target_lang == "Таджикский":
        return _fix_json_strings(data, _fix_tajik)
    return data


def _language_rules(language: str) -> str:
    if language == "Таджикский":
        return """
ADDITIONAL TAJIK LANGUAGE RULES:
- Write in correct literary Tajik (тоҷикӣ), not Russian transliteration
- Use Tajik vocabulary: шеър not стихотворение, байт not куплет, ғазал not газель, қасида not касыда, адабиёт not литература, муаллиф not автор, асар not произведение, достон not поэма, ҳикоя not рассказ, китоб not книга, дарс not урок, мактаб not школа, синф not класс, хонанда not ученик, омӯзгор not учитель, донишҷӯй not студент, вазифа not задача, таҳлил not анализ, муқоиса not сравнение, хулоса not вывод, намуна not пример, савол not вопрос, ҷавоб not ответ, ҳақиқат not правда, муҳаббат not любовь, озодӣ not свобода, адолат not справедливость, меҳнат not труд, дониш not знание, шуҷоат not храбрость, некӣ not доброта, зебоӣ not красота, донишгоҳ not университет, тағйирот not изменение, раванд not процесс, нақш not роль, таъсир not влияние, мавзӯъ not тема, мақсад not цель, саволҳо not вопросы
- For literature specifically: шеър (poem), байт (couplet), ғазал (ghazal), қасида (qasida), достон (epic), маснавӣ (masnavi), таҳлил (analysis), муқоиса (comparison), тасвир (image), рамз (symbol), ғоя (idea), панд (moral), қаҳрамон (hero), маҷрои воқеа (plot)
- Prefer ordinary, school-textbook Tajik over literal word-for-word translation. In particular, use
  "тағйирёбанда" for a programming variable, "шарт" for a condition, "давр/давра" for a loop,
  "функсия" for a function, and "синтаксис" for syntax. Never leave Russian words such as
  "условие", "луп", "переменная", "пример", "вопрос" or "ответ" in Tajik prose.
- Check agreement, case endings, verb forms, spelling of ҳ/қ/ғ/ҷ/ӣ, and natural Tajik word order.
  If a specialist term is uncertain, explain it in simple Tajik instead of inventing a term.
- NEVER mix Russian words into Tajik text
- NEVER mix Uzbek words or Uzbek-style grammar into Tajik text, even though the scripts look similar. A real,
  confirmed mistake: "кайси" (Uzbek for "which") used instead of the correct Tajik "кадом". Other Uzbek words
  that have leaked in before and must never appear in Tajik prose: "системасининг", "имконияти", "бир нечта",
  "бўлиш", "шаклида", "қўшилган", "запутанлик". If a sentence reads naturally in Uzbek but not in Tajik, it is
  wrong — rewrite it in plain literary Tajik instead.
- Every prose field must be natural, readable Tajik suitable for a school teacher; code, formulas,
  proper names, and internationally accepted technical names may remain unchanged."""
    return ""


def _konspekt_system_prompt(language: str) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    tajik_rules = _language_rules(language)
    return f"""You are a school teacher writing a formal, concise lesson plan (konspekt). Return ONLY valid JSON.
Write ALL content in {lang_name} language.{tajik_rules}
{_TEACHER_SIMPLICITY_RULE}

RULES:
1. Write ONLY about the topic given.
2. Concise and factual, like an official school konspekt: "competencies"/"objectives" are short phrases;
   other text fields are 2-3 clear sentences with real facts and examples. No padding or repetition.
3. NEVER mix languages - write ONLY in {lang_name}.
4. No meta-text, disclaimers or apologies in any value."""


def _lecture_system_prompt(language: str) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    tajik_rules = _language_rules(language)
    return f"""You are a subject-matter expert writing an in-depth lecture (лекция) that explains a topic thoroughly \
— NOT a lesson plan. Return ONLY valid JSON.
Write ALL content in {lang_name} language.{tajik_rules}
{_TEACHER_SIMPLICITY_RULE}

CRITICAL RULES:
1. Write ONLY about the topic given.
2. This document's entire job is to EXPLAIN the topic deeply and clearly — like a textbook chapter or lecture
   transcript, not a plan for how a teacher should run a class.
3. Do NOT include any lesson-management content: no lesson goals/competencies, no lesson program/schedule, no
   pair-work/group activities, no homework, no assessment criteria. Only the fields listed in the user prompt.
4. Every field must be SUBSTANTIAL — real facts, reasoning, and examples. NEVER write one-sentence answers.
5. NEVER mix languages - write ONLY in {lang_name}.
6. NO filler commentary, meta-text, disclaimers, or apologies anywhere in the JSON values."""


_BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}"}
_BRACKET_CLOSERS = set(_BRACKET_PAIRS.values())


def _code_block_is_balanced(code: str) -> bool:
    stack: list[str] = []
    in_string: str | None = None
    i = 0
    n = len(code)
    while i < n:
        ch = code[i]
        if in_string:
            if ch == "\\":
                i += 2
                continue
            if ch == in_string:
                in_string = None
        elif ch in ("'", '"'):
            in_string = ch
        elif ch == "/" and i + 1 < n and code[i + 1] == "/":
            nl = code.find("\n", i)
            i = nl if nl != -1 else n
            continue
        elif ch == "#":
            nl = code.find("\n", i)
            i = nl if nl != -1 else n
            continue
        elif ch in _BRACKET_PAIRS:
            stack.append(_BRACKET_PAIRS[ch])
        elif ch in _BRACKET_CLOSERS:
            if not stack or stack.pop() != ch:
                return False
        i += 1
    return not stack and in_string is None


def _validate_code_blocks(content: dict, topic: str) -> None:
    blocks = content.get("code_blocks")
    if not isinstance(blocks, list):
        return
    kept = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        code = block.get("code") or ""
        if not code.strip():
            continue
        try:
            if not _code_block_is_balanced(code):
                logger.warning(f"Dropping unbalanced code_block for topic={topic[:50]}")
                continue
        except Exception as e:
            logger.warning(f"code_blocks validation failed for topic={topic[:50]}: {e}")
            continue
        kept.append(block)
    content["code_blocks"] = kept


def _enforce_code_relevance(content: dict, policy: str, topic: str) -> None:
    """Prevent the legacy Informatics template from leaking irrelevant code."""
    if not isinstance(content, dict):
        return
    if policy != "needed":
        if content.get("code_blocks"):
            logger.info(
                f"Dropped irrelevant code_blocks for non-programming topic={topic[:80]}"
            )
        # Keep a stable empty field for exporters and downstream editors.
        content["code_blocks"] = []
        slides = content.get("slides")
        if isinstance(slides, list):
            for slide in slides:
                if isinstance(slide, dict) and slide.pop("code", None):
                    logger.info(
                        f"Dropped irrelevant slide code for non-programming topic={topic[:80]}"
                    )


def _has_programming_content(content: dict) -> bool:
    """Detect code leaking into prose/exercises, not only code_blocks."""
    if not isinstance(content, dict):
        return False
    if content.get("code_blocks"):
        return True
    parts: list[str] = []

    def collect(value):
        if isinstance(value, str):
            parts.append(value.casefold())
        elif isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key not in {"code", "language", "latex", "formula"}:
                    collect(item)

    collect(content)
    text = "\n".join(parts)
    return any(term in text for term in (
        "python", "c++", "javascript", "java", "компилятор", "compiler", "api",
        "код", "code", "барномасозӣ", "барномасозии",
    ))


_NO_MATH_KEYS = {"code", "language", "image", "images", "image_url", "url",
                 "path", "map_image", "src", "shape", "id", "color", "icon",
                 "lesson_image_queries", "real_image_query", "credit", "source",
                 "image_query", "kind", "caption"}


def _typeset_math(node, key: str | None = None):
    from app.math_render import normalize_math, brace_scripts

    if isinstance(node, str):
        if key in _NO_MATH_KEYS:
            return node
        return brace_scripts(node) if key == "latex" else normalize_math(node)
    if isinstance(node, list):
        return [_typeset_math(item, key) for item in node]
    if isinstance(node, dict):
        return {k: _typeset_math(v, k if isinstance(k, str) else None)
                for k, v in node.items()}
    return node



_STOPWORDS = {
    "что", "как", "какой", "какая", "какое", "какие", "кто", "где", "когда",
    "почему", "зачем", "это", "такое", "для", "чего", "из", "на", "в", "и",
    "или", "не", "ли", "the", "a", "an", "is", "are", "of", "to", "in", "on",
    "what", "which", "who", "where", "when", "why", "how", "does", "do",
    "чӣ", "чист", "кадом", "кӣ", "куҷо", "кай", "чаро", "аз", "ба", "дар", "ва",
}


_STEM_CHARS = 4


def _question_fingerprint(text: str) -> frozenset:
    words = re.findall(r"\w+", (text or "").lower())
    return frozenset(
        w[:_STEM_CHARS] for w in words if len(w) > 2 and w not in _STOPWORDS
    )


def _near_duplicate(a: frozenset, b: frozenset) -> bool:
    if not a or not b:
        return False
    if len(a) < 3 or len(b) < 3:
        return a == b
    return len(a & b) / len(a | b) >= 0.75


def _validate_test_quality(content: dict, topic: str, requested_count: int) -> None:
    questions = content.get("questions")
    if not isinstance(questions, list) or not questions:
        return

    kept: list[dict] = []
    seen: list[frozenset] = []
    dropped = {"malformed": 0, "duplicate": 0, "no_answer": 0, "trivial_options": 0}

    for q in questions:
        if not isinstance(q, dict):
            dropped["malformed"] += 1
            continue
        text = (q.get("question") or "").strip()
        if not text:
            dropped["malformed"] += 1
            continue
        q["question"] = text
        qtype = q.get("type") or "multiple_choice"

        if qtype == "open_ended":
            pass
        else:
            options = q.get("options")
            if not isinstance(options, list):
                dropped["malformed"] += 1
                continue
            cleaned = [str(o).strip() for o in options if str(o).strip()]
            if len(cleaned) < len(options):
                index_map = {}
                new_i = 0
                for old_i, o in enumerate(options):
                    if str(o).strip():
                        index_map[old_i] = new_i
                        new_i += 1
                if isinstance(q.get("correct_index"), int):
                    q["correct_index"] = index_map.get(q["correct_index"])
                if isinstance(q.get("correct_indices"), list):
                    q["correct_indices"] = [
                        index_map[i] for i in q["correct_indices"] if i in index_map
                    ]
                q["options"] = cleaned
                options = cleaned

            if len(options) < 2:
                dropped["malformed"] += 1
                continue

            lowered = [o.strip().lower() for o in options]
            if len(set(lowered)) < len(lowered):
                dropped["trivial_options"] += 1
                continue

            if qtype == "multiple_select":
                idx = q.get("correct_indices")
                if not isinstance(idx, list) or not idx or any(
                    not isinstance(i, int) or i < 0 or i >= len(options) for i in idx
                ):
                    dropped["no_answer"] += 1
                    continue
                q["correct_indices"] = sorted(set(idx))
                if len(q["correct_indices"]) == len(options):
                    dropped["trivial_options"] += 1
                    continue
            else:
                idx = q.get("correct_index")
                if not isinstance(idx, int) or idx < 0 or idx >= len(options):
                    dropped["no_answer"] += 1
                    continue
                if lowered.count(lowered[idx]) > 1:
                    dropped["trivial_options"] += 1
                    continue

        fingerprint = _question_fingerprint(text)
        if any(_near_duplicate(fingerprint, prev) for prev in seen):
            dropped["duplicate"] += 1
            continue
        seen.append(fingerprint)
        kept.append(q)

    removed = len(questions) - len(kept)
    if removed:
        logger.warning(
            f"Test quality gate removed {removed}/{len(questions)} question(s) for "
            f"topic={topic[:60]!r}: {dropped}"
        )
    if kept:
        content["questions"] = kept
    elif removed:
        logger.error(
            f"Test quality gate would have emptied the test for topic={topic[:60]!r}; "
            f"keeping the original {len(questions)} question(s) for the teacher to edit"
        )

    if requested_count and len(content["questions"]) < requested_count:
        logger.info(
            f"Test for topic={topic[:60]!r} has {len(content['questions'])} of "
            f"{requested_count} requested questions after the quality gate"
        )


def _typeset_math_content(content: dict, topic: str) -> None:
    try:
        fixed = _typeset_math(content)
        if isinstance(fixed, dict):
            content.clear()
            content.update(fixed)
    except Exception as e:
        logger.warning(f"Math typesetting pass failed for topic={topic[:50]}: {e}")


_IMAGE_ANCHORS = ("key_concepts", "main_content", "worked_examples",
                  "real_life_examples", "consolidation", "key_terms")


def _section_text(content: dict, key: str, limit: int = 400) -> str:
    val = content.get(key)
    if isinstance(val, list):
        text = " ".join(str(v) for v in val if v)
    elif isinstance(val, dict):
        text = " ".join(str(v) for v in val.values() if isinstance(v, str))
    else:
        text = str(val or "")
    text = text.strip()
    return text[:limit] if text else key


def _place_lesson_images(content: dict, images: list[dict], requests: list[dict]) -> None:
    available = [key for key in _IMAGE_ANCHORS if content.get(key)]
    if not available:
        available = ["main_content"]
    by_query = {str(r.get("query") or "").strip(): r for r in requests}
    used: set[str] = set()
    for i, image in enumerate(images):
        request = by_query.get(str(image.get("query") or "").strip())
        if request is None:
            request = requests[i] if i < len(requests) else {}
        anchor = str(request.get("position_after") or "").strip()
        if anchor not in available or anchor in used:
            anchor = next((k for k in available if k not in used), available[0])
        used.add(anchor)
        image["position_after"] = anchor
        explanation = str(request.get("explanation") or "").strip()
        if explanation:
            image["explanation"] = explanation[:300]


async def _caption_and_verify_images(content: dict, topic: str, images: list[dict],
                                     context_of=None) -> list[dict]:
    if context_of is None:
        context_of = lambda im: im.get("position_after") or "main_content"
    described = [im for im in images if im.get("file_title") or im.get("caption")]
    if not described:
        return images
    lang_name = LANGUAGE_NAMES.get(content.get("language") or "", "Russian")
    listing = "\n".join(
        f'{i + 1}. FILE TITLE: "{im.get("file_title") or im.get("caption")}"\n'
        f'   FILE DESCRIPTION: "{str(im.get("description") or "")[:300]}"\n'
        f'   MUST ILLUSTRATE: {str(context_of(im))[:200]}'
        for i, im in enumerate(described)
    )
    system_prompt = (
        "You check whether a Wikimedia Commons file actually shows what a school lesson needed it for, "
        "and write the one-line reading instruction printed under it when it does. "
        f"Answer ONLY with valid JSON, every sentence written in {lang_name}."
    )
    user_prompt = (
        f'A lesson for grade {content.get("grade", "")} on "{topic}" ({content.get("subject", "")}) '
        f"tried to illustrate itself with these Wikimedia Commons files:\n{listing}\n\n"
        "For EACH file, judge ONLY from its own FILE TITLE/FILE DESCRIPTION above (not the search query, "
        "which may be wrong) whether it genuinely depicts what MUST ILLUSTRATE describes:\n"
        "- \"relevant\": true only if the file's own title/description show it is actually about that "
        "specific thing — not merely related, not a different field's diagram that happens to share a "
        "word, not a generic/decorative photo. When genuinely unsure, prefer false: a missing picture "
        "costs nothing, a wrong one misleads the pupil.\n"
        "- \"explanation\": when relevant is true, ONE short sentence telling the pupil what to look at in "
        "THAT PARTICULAR picture and how it relates to the topic — describe only what the file's own "
        "title/description says is in it, never invent elements (squares, arrows, labels, colours) it "
        "does not state it has. If the file shows a variant/special case (an 'inverse', a 'converse', one "
        "particular example), say so plainly instead of describing the general case. Max 20 words, no "
        "title, no file name, no licence. When relevant is false, leave this an empty string.\n"
        '\nReturn exactly this JSON shape: {"results": [{"relevant": true, "explanation": "..."}, ...]} — '
        f"exactly {len(described)} entries, in the same order as the files listed above."
    )
    try:
        result = await _call_ai(system_prompt, user_prompt, content.get("language") or "Русский",
                                "image relevance check")
        results = result.get("results")
        if not isinstance(results, list):
            return images
        dropped: set[int] = set()
        for image, verdict in zip(described, results):
            if not isinstance(verdict, dict):
                continue
            if verdict.get("relevant") is False:
                dropped.add(id(image))
                continue
            text = str(verdict.get("explanation") or "").strip()
            if text:
                image["explanation"] = text[:300]
        if dropped:
            kept = [im for im in images if id(im) not in dropped]
            logger.info(f"Image relevance check: dropped {len(dropped)}/{len(described)} "
                       f"mismatched picture(s) for topic={topic[:50]}")
            return kept
        return images
    except Exception as e:
        logger.warning(f"Image relevance check failed for topic={topic[:50]}: {e}")
        return images


def _render_slide_figures(content: dict, topic: str) -> None:
    from app.figure_builder import save_figure
    for slide in (content.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        visual = slide.get("visual")
        if not isinstance(visual, dict) or visual.get("type") != "figure":
            continue
        data = visual.get("data") or {}
        path = None
        try:
            path = save_figure(data.get("shape"), data.get("values") or [])
        except Exception as e:
            logger.warning(f"Slide figure render failed for topic={topic[:50]}: {e}")
        if path:
            visual["image"] = path
        else:
            slide.pop("visual", None)


async def _render_test_images(content: dict, topic: str) -> None:
    questions = content.get("questions") or []
    wanted = [q for q in questions
              if isinstance(q, dict) and str(q.get("image_query") or "").strip()][:3]
    if not wanted:
        return

    async def _do() -> None:
        from app.image_builder import fetch_lesson_images
        fetched: list[tuple[dict, dict]] = []
        for q in wanted:
            query = str(q["image_query"]).strip()
            found = await fetch_lesson_images([query], count=1, grade=content.get("grade"),
                                              language=content.get("language"),
                                              subject=content.get("subject"))
            if found:
                fetched.append((q, found[0]))
        if not fetched:
            return
        q_of = {id(image): q for q, image in fetched}
        context_of = lambda im: str(q_of[id(im)].get("question") or "")[:200]
        images = await _caption_and_verify_images(
            content, topic, [image for _, image in fetched], context_of=context_of)
        kept_ids = {id(im) for im in images}
        for q, image in fetched:
            if id(image) not in kept_ids:
                continue
            q["image"] = {
                "path": image["path"],
                "caption": image.get("caption", ""),
                "credit": image.get("credit", ""),
                "source": image.get("source", ""),
            }

    try:
        await asyncio.wait_for(_do(), timeout=15.0)
    except Exception as e:
        logger.warning(f"Test image fetch failed for topic={topic[:50]}: {e}")


def _copy_textbook_image_to_uploads(source_path: str) -> str | None:
    import shutil
    import uuid

    images_dir = os.path.join(os.path.dirname(__file__), "..", "uploads", "images")
    try:
        os.makedirs(images_dir, exist_ok=True)
        ext = os.path.splitext(source_path)[1] or ".png"
        filename = f"{uuid.uuid4().hex}{ext}"
        shutil.copyfile(source_path, os.path.join(images_dir, filename))
        return f"/uploads/images/{filename}"
    except OSError as e:
        logger.warning(f"Textbook image copy failed for {source_path}: {e}")
        return None


async def _lookup_lesson_image_cache(subject: str, topic_key: str, limit: int) -> list[dict]:
    if limit <= 0 or not topic_key:
        return []
    try:
        from app.database import async_session
        from app.models import LessonImageCache
        from sqlalchemy import select, func

        async with async_session() as db:
            rows = (await db.execute(
                select(LessonImageCache)
                .where(LessonImageCache.subject == subject, LessonImageCache.topic_key == topic_key)
                .order_by(LessonImageCache.slot)
                .limit(limit)
            )).scalars().all()
            if not rows:
                return []
            for row in rows:
                row.hit_count += 1
                row.last_used_at = datetime.now(timezone.utc)
            await db.commit()
            return [{
                "path": r.path, "caption": r.caption or "", "credit": r.credit or "",
                "source": r.source or "", "explanation": r.explanation or "",
                "width": r.width, "height": r.height,
            } for r in rows]
    except Exception as e:
        logger.warning(f"Lesson image cache lookup failed for subject={subject}, topic={topic_key[:50]}: {e}")
        return []


async def _save_lesson_images_to_cache(subject: str, topic: str, topic_key: str, images: list[dict]) -> None:
    if not images or not topic_key:
        return
    try:
        from app.database import async_session
        from app.models import LessonImageCache
        from sqlalchemy import select

        async with async_session() as db:
            for image in images:
                slot = image.get("_cache_slot")
                if slot is None:
                    continue
                existing = (await db.execute(
                    select(LessonImageCache).where(
                        LessonImageCache.subject == subject,
                        LessonImageCache.topic_key == topic_key,
                        LessonImageCache.slot == slot,
                    )
                )).scalar_one_or_none()
                if existing is not None:
                    continue
                db.add(LessonImageCache(
                    subject=subject, topic=topic[:255], topic_key=topic_key, slot=slot,
                    path=image.get("path", ""), caption=image.get("caption") or None,
                    credit=image.get("credit") or None, source=image.get("source") or None,
                    explanation=image.get("explanation") or None,
                    width=image.get("width"), height=image.get("height"),
                ))
            await db.commit()
    except Exception as e:
        logger.warning(f"Lesson image cache save failed for subject={subject}, topic={topic_key[:50]}: {e}")


async def _render_lesson_images(content: dict, topic: str) -> None:
    subject = str(content.get("subject") or "").strip()
    topic_key = topic.strip().lower()
    requested = content.get("lesson_images")
    requests: list[dict] = []
    if isinstance(requested, list):
        for entry in requested:
            if isinstance(entry, dict) and str(entry.get("query") or "").strip():
                requests.append(entry)
            elif isinstance(entry, str) and entry.strip():
                requests.append({"query": entry.strip()})
    if not requests:
        legacy = content.get("lesson_image_queries")
        if isinstance(legacy, list):
            requests = [{"query": str(q).strip()} for q in legacy if str(q or "").strip()]
    requests = requests[:2]
    while len(requests) < 2:
        requests.append({"query": f"{topic} diagram" if requests else topic})

    async def _do() -> None:
        from app.image_builder import fetch_lesson_images

        images: list[dict] = []
        textbook_image = _find_textbook_image(content.get("subject") or "", content.get("grade") or "", topic)
        if textbook_image:
            copied = _copy_textbook_image_to_uploads(textbook_image["path"])
            if copied:
                images.append({
                    "path": copied, "caption": topic,
                    "credit": f"Аз китоби дарсии расмии синфи {content.get('grade')}",
                    "description": f"Тасвири аслии китоби дарсии расмии синфи {content.get('grade')}, наздики мавзӯи «{topic}».",
                    "source": None, "width": None, "height": None,
                })

        remaining_slots = 2 - len(images)
        if remaining_slots > 0:
            cached = await _lookup_lesson_image_cache(subject, topic_key, remaining_slots)
            images.extend(cached)
            still_needed = remaining_slots - len(cached)
            if still_needed > 0:
                fetched = await fetch_lesson_images([r["query"] for r in requests[:still_needed]], count=still_needed,
                                                     grade=content.get("grade"),
                                                     language=content.get("language"),
                                                     subject=content.get("subject"))
                for i, image in enumerate(fetched):
                    image["_cache_slot"] = len(cached) + i
                images.extend(fetched)

        _seen: set[str] = set()
        _unique: list[dict] = []
        for im in images:
            key = str(im.get("file_title") or im.get("path") or "")
            if key and key in _seen:
                logger.info(f"Lesson image dropped as duplicate: {key}")
                continue
            if key:
                _seen.add(key)
            _unique.append(im)
        images = _unique

        if images:
            _place_lesson_images(content, images, requests)
            images = await _caption_and_verify_images(
                content, topic, images,
                context_of=lambda im: _section_text(content, im.get("position_after") or "main_content"))
        if images:
            to_cache = [im for im in images if im.get("_cache_slot") is not None]
            if to_cache and topic_key:
                await _save_lesson_images_to_cache(subject, topic, topic_key, to_cache)
            for im in images:
                im.pop("_cache_slot", None)
            content["lesson_images"] = images
        else:
            content.pop("lesson_images", None)

    try:
        await asyncio.wait_for(_do(), timeout=15.0)
    except Exception as e:
        logger.warning(f"Lesson image fetch failed for topic={topic[:50]}: {e}")
        content.pop("lesson_images", None)


def _render_subject_figures(content: dict, topic: str) -> None:
    from app.figure_builder import save_figure

    kept = []
    for fig in (content.get("figures") or []):
        if not isinstance(fig, dict) or not fig.get("shape"):
            continue
        try:
            path = save_figure(fig.get("shape"), fig.get("values") or [])
        except Exception as e:
            logger.warning(f"Figure render failed for topic={topic[:50]}: {e}")
            path = None
        if not path:
            logger.info(f"Figure skipped (unknown shape {fig.get('shape')!r}) topic={topic[:50]}")
            continue
        fig["image"] = path
        kept.append(fig)
    if content.get("figures") is not None:
        content["figures"] = kept


def _render_timeline_images(content: dict, topic: str) -> None:
    from app.timeline_builder import save_timeline_image, save_process_image, save_concept_map_image

    for block in (content.get("visual_blocks") or []):
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype not in ("timeline", "flowchart", "process", "concept_map"):
            continue
        try:
            data = block.get("data") or {}
            if btype == "timeline":
                image_path = save_timeline_image(data.get("events") or [])
            elif btype == "concept_map":
                image_path = save_concept_map_image(data.get("nodes") or [], data.get("edges") or [])
            else:
                image_path = save_process_image(data.get("steps") or [])
            if image_path:
                block["image"] = image_path
        except Exception as e:
            logger.warning(f"Visual block image generation failed for topic={topic[:50]}: {e}")


async def _fetch_real_world_image(content: dict, topic: str) -> None:
    query = (content.get("real_image_query") or "").strip()
    if not query:
        return
    style = (content.get("real_image_style") or "").strip().lower()
    if style not in ("logo", "cutout", "diagram"):
        style = "cutout"
    try:
        from app.image_builder import fetch_real_image
        language = content.get("language") or "Русский"
        result = await asyncio.wait_for(fetch_real_image(query, language, style), timeout=12.0)
        if result:
            result["style"] = style
            content["real_image"] = result
    except Exception as e:
        logger.warning(f"Real-world image fetch failed for topic={topic[:50]} query={query[:50]}: {e}")


async def retry_visual_assets(content: dict, topic: str, subject: str) -> bool:
    changed = False
    if subject == "География" and content.get("map_locations") and not content.get("map_image"):
        try:
            from app.map_builder import build_geography_map
            map_path = await build_geography_map(content["map_locations"])
            if map_path:
                content["map_image"] = map_path
                changed = True
        except Exception as e:
            logger.warning(f"Map retry failed for topic={topic[:50]}: {e}")
    if content.get("real_image_query") and not content.get("real_image"):
        await _fetch_real_world_image(content, topic)
        changed = changed or bool(content.get("real_image"))
    return changed


async def retry_lesson_image(content: dict, topic: str, index: int) -> bool:
    images = content.get("lesson_images")
    if not isinstance(images, list) or not (0 <= index < len(images)):
        return False
    current = images[index]
    if not isinstance(current, dict):
        return False
    query = str(current.get("query") or "").strip() or topic
    exclude_title = current.get("file_title") or ""
    try:
        from app.image_builder import fetch_lesson_images
        fetched = await fetch_lesson_images([query], count=2,
                                            grade=content.get("grade"),
                                            language=content.get("language"),
                                            subject=content.get("subject"))
        candidate = next((im for im in fetched if im.get("file_title") != exclude_title), None)
        if not candidate:
            return False
        candidate["position_after"] = current.get("position_after", "")
        candidate["explanation"] = current.get("explanation", "")
        verified = await _caption_and_verify_images(
            content, topic, [candidate],
            context_of=lambda im: im.get("position_after") or "main_content")
        if not verified:
            return False
        images[index] = verified[0]
        content["lesson_images"] = images
        return True
    except Exception as e:
        logger.warning(f"Lesson image retry failed for topic={topic[:50]}, index={index}: {e}")
        return False


# Keep enough context for a lesson while avoiding sending an entire textbook
# excerpt on every request. The source is split into small chunks and the
# chunks most relevant to the requested topic are selected before prompting.
# This keeps retrieval useful for long uploaded books without changing the
# Dastyor output schema or lesson architecture.
_SOURCE_EXCERPT_CHARS = 12000
_SOURCE_CHUNK_CHARS = 2400

_SOURCE_STOPWORDS = {
    # Tajik / Uzbek / Russian / English words which commonly occur in a
    # request but carry little retrieval signal on their own.
    "ва", "дар", "барои", "ба", "аз", "бо", "доир", "оид", "дарс",
    "мавзӯъ", "мавзуъ", "сохтани", "дар", "учебник", "тема", "урок",
    "про", "для", "по", "из", "с", "и", "the", "and", "for", "with",
    "lesson", "topic", "about", "class", "grade",
}


def _source_terms(text: str) -> list[str]:
    """Return meaningful words for lightweight lexical source retrieval."""
    if not text:
        return []
    words = re.findall(r"[^\W\d_]{3,}|[A-Za-z_]\w*", text.lower(), flags=re.UNICODE)
    terms: list[str] = []
    seen: set[str] = set()
    for word in words:
        if word in _SOURCE_STOPWORDS or len(word) < 4 or word in seen:
            continue
        seen.add(word)
        terms.append(word)
    return terms


def _source_chunks(source_text: str) -> list[tuple[int, str]]:
    """Split source into overlapping chunks while retaining original offsets."""
    chunks: list[tuple[int, str]] = []
    step = _SOURCE_CHUNK_CHARS - 300
    start = 0
    while start < len(source_text):
        end = min(len(source_text), start + _SOURCE_CHUNK_CHARS)
        if end < len(source_text):
            # Prefer a paragraph or line boundary so selected excerpts remain
            # readable, but do not make a huge source chunk if no boundary is
            # nearby (PDF extraction often has very few newlines).
            boundary = max(source_text.rfind("\n\n", start + 900, end), source_text.rfind("\n", start + 900, end))
            if boundary > start + 900:
                end = boundary
        chunk = source_text[start:end].strip()
        if chunk:
            chunks.append((start, chunk))
        if end >= len(source_text):
            break
        start = max(start + step, end - 300)
    return chunks


def _find_topic_offset(source_text: str, topic: str) -> int:
    haystack = source_text.lower()
    needle = topic.lower().strip()
    idx = -1
    if needle:
        # The first hit in a school book is often the table of contents and
        # the last hit can be an index. Prefer the first meaningful hit after
        # the opening pages, where the actual lesson normally begins.
        start = 0
        hits = []
        while True:
            found = haystack.find(needle, start)
            if found == -1:
                break
            hits.append(found)
            start = found + max(1, len(needle))
        if hits:
            body_start = max(0, int(len(haystack) * 0.08))
            idx = next((hit for hit in hits if hit >= body_start), hits[0])
    if idx == -1 and needle:
        for word in sorted(set(needle.split()), key=len, reverse=True):
            if len(word) > 3:
                idx = haystack.find(word)
                if idx != -1:
                    break
    return idx


def _select_relevant_excerpt(
    source_text: str,
    topic: str,
    max_chars: int = _SOURCE_EXCERPT_CHARS,
    query_text: str | None = None,
) -> str:
    """Select topic-relevant source chunks while preserving source order.

    This is intentionally a small, dependency-free RAG layer. It is not a
    replacement for Dastyor's generation schema: it only controls which part
    of a book is placed in the prompt. Explicitly uploaded source remains the
    primary source, and no source content is returned to logs.
    """
    if len(source_text) <= max_chars:
        return source_text

    chunks = _source_chunks(source_text)
    if not chunks:
        return source_text[:max_chars]

    terms = _source_terms(query_text or topic)
    topic_phrase = re.sub(r"\s+", " ", (topic or "").strip().lower())
    ranked: list[tuple[float, int, str]] = []
    for index, (offset, chunk) in enumerate(chunks):
        lowered = chunk.lower()
        score = 0.0
        if topic_phrase and topic_phrase in lowered:
            score += 12.0
        for term in terms:
            occurrences = lowered.count(term)
            if occurrences:
                score += min(occurrences, 4) * (2.5 if len(term) >= 6 else 1.0)
        # The opening chunk usually contains the source title, objectives, or
        # definitions. Keep it as a low-priority anchor, not as the only data.
        if index == 0:
            score += 1.5
        ranked.append((score, offset, chunk))

    # Select the best chunks under a strict budget, then restore their source
    # order. A no-match source still gets a small opening excerpt so the model
    # can detect a mismatched document and follow the topic guard in prompts.
    ranked.sort(key=lambda item: (-item[0], item[1]))
    body_limit = max(1000, max_chars - 180)
    selected: list[tuple[int, str]] = []
    used = 0
    for score, offset, chunk in ranked:
        if score <= 0 and selected:
            continue
        extra = len(chunk) + (2 if selected else 0)
        if used + extra > body_limit:
            continue
        selected.append((offset, chunk))
        used += extra
        if used >= body_limit * 0.9:
            break

    if not selected:
        selected = [(chunks[0][0], chunks[0][1][:body_limit])]

    selected.sort(key=lambda item: item[0])
    body = "\n\n".join(chunk for _, chunk in selected)
    excerpt = (
        "[SELECTED SOURCE EXCERPTS — relevant passages from the provided source; keep the requested topic as the source of truth]\n"
        f"{body}\n"
        "[END SELECTED SOURCE EXCERPTS]"
    )
    logger.info(
        "Source retrieval selected %s of %s characters across %s chunks for topic=%s",
        len(body), len(source_text), len(selected), (topic or "")[:80],
    )
    return excerpt[:max_chars]


_TEXTBOOK_CACHE_DIR = os.path.join(os.path.dirname(__file__), "textbooks_cache")
_textbook_manifest_cache: dict | None = None
_textbook_manifest_mtime: float | None = None


def _textbook_manifest() -> dict:
    global _textbook_manifest_cache, _textbook_manifest_mtime
    manifest_path = os.path.join(_TEXTBOOK_CACHE_DIR, "_manifest.json")
    try:
        mtime = os.path.getmtime(manifest_path)
    except OSError:
        mtime = None
    if _textbook_manifest_cache is None or mtime != _textbook_manifest_mtime:
        try:
            with open(manifest_path, encoding="utf-8") as f:
                _textbook_manifest_cache = json.load(f)
            _textbook_manifest_mtime = mtime
        except (FileNotFoundError, json.JSONDecodeError):
            _textbook_manifest_cache = {}
            _textbook_manifest_mtime = mtime
    return _textbook_manifest_cache


def _textbook_entry(subject: str, grade: str) -> dict | None:
    grade_num = (grade or "").strip().split()[0] if grade else ""
    manifest = _textbook_manifest()
    # New local index format: many sources per subject/grade, ordered by
    # textbook > curriculum > reference > lesson plan.
    if "by_subject_grade" in manifest:
        grade_map = manifest.get("by_subject_grade", {}).get(subject, {})
        source_ids = list(grade_map.get(grade_num, []))
        if grade_num != "all":
            source_ids += [sid for sid in grade_map.get("all", []) if sid not in source_ids]
        records = {item.get("id"): item for item in manifest.get("sources", [])}
        source_records = [records[sid] for sid in source_ids if sid in records]
        if not source_records:
            return None
        return {
            "name": source_records[0]["id"],
            "sources": source_records,
            "images_ok": False,
        }
    # Backward compatibility with the original one-file manifest.
    return manifest.get(subject, {}).get(grade_num)


def _load_cached_textbook(subject: str, grade: str, topic: str | None = None) -> str | None:
    entry = _textbook_entry(subject, grade)
    if not entry:
        return None

    records = entry.get("sources") or [{"id": entry.get("name")}]
    terms = [word.lower() for word in re.findall(r"[\w\u0400-\u04ff]+", topic or "") if len(word) >= 4]
    ranked: list[tuple[int, dict, str]] = []
    for record in records:
        source_id = record.get("id")
        if not source_id:
            continue
        try:
            with open(os.path.join(_TEXTBOOK_CACHE_DIR, f"{source_id}.txt"), encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            continue
        lowered = text.lower()
        score = sum(lowered.count(term) for term in terms)
        ranked.append((score, record, text))
    if not ranked:
        return None

    # Prefer sources that actually mention the topic. If the topic was typed
    # in another language, fall back to the ordered official sources.
    matched = [item for item in ranked if item[0] > 0]
    chosen = sorted(matched or ranked, key=lambda item: (-item[0], item[1].get("kind", "")))[:2]
    parts = []
    for _, record, text in chosen:
        excerpt = _select_relevant_excerpt(text, topic or "", max_chars=3000)
        parts.append(f"SOURCE: {record.get('title', '')}\n{excerpt}")
    return "\n\n".join(parts)[:_SOURCE_EXCERPT_CHARS]


def _find_textbook_image(subject: str, grade: str, topic: str) -> dict | None:
    entry = _textbook_entry(subject, grade)
    if not entry or not entry.get("images_ok"):
        return None

    name = entry["name"]
    try:
        with open(os.path.join(_TEXTBOOK_CACHE_DIR, f"{name}.txt"), encoding="utf-8") as f:
            text = f.read()
        with open(os.path.join(_TEXTBOOK_CACHE_DIR, f"{name}.pages.json"), encoding="utf-8") as f:
            breakpoints = json.load(f)
        images_dir = os.path.join(_TEXTBOOK_CACHE_DIR, f"{name}_images")
        with open(os.path.join(images_dir, "images.json"), encoding="utf-8") as f:
            images = json.load(f)
    except FileNotFoundError:
        return None
    if not images:
        return None

    offset = _find_topic_offset(text, topic)
    if offset == -1:
        return None

    page = 0
    for off, pg in breakpoints:
        if off <= offset:
            page = pg
        else:
            break

    best = min(images, key=lambda im: abs(im["page"] - page))
    if abs(best["page"] - page) > 5:
        return None
    return {"path": os.path.join(images_dir, best["path"]), "page": best["page"]}


async def generate_material(
    material_type: str,
    topic: str,
    subject: str,
    language: str,
    level: str,
    grade: str,
    slide_count: int | None = None,
    question_count: int | None = None,
    test_type: str | None = None,
    include_homework: bool = True,
    include_fun_facts: bool = True,
    include_assessment: bool = True,
    include_examples: bool = True,
    template: str | None = None,
    source_text: str | None = None,
    previous_digests: list[dict] | None = None,
    teacher_context: str | None = None,
) -> dict:
    prompt_fn = PROMPTS.get(material_type)
    if not prompt_fn:
        logger.error(f"Unknown material type: {material_type}")
        raise ValueError(f"Unknown material type: {material_type}")

    # Focused beginner Python lessons should not inherit a broad cached
    # textbook excerpt (often containing lists, games, or later chapters).
    # An explicitly uploaded/book-selected source still remains authoritative.
    if not source_text and not _is_variable_topic(subject, topic):
        source_text = _load_cached_textbook(subject, grade, topic)
    # Retrieve by the requested lesson identity. Teacher preferences are used
    # later to shape the writing, but should not pull unrelated book chapters
    # into the source excerpt just because a preference word happens to recur.
    retrieval_query = " ".join(value for value in (topic, subject, grade) if value)
    source_excerpt = (
        _select_relevant_excerpt(source_text, topic, query_text=retrieval_query)
        if source_text else None
    )
    code_policy = _code_relevance(subject, topic)

    variant: dict = {}
    test_type = test_type or "mixed"
    if material_type == "prezentatsiya":
        user_prompt = prompt_fn(topic, subject, level, grade, language, slide_count or 10,
                                source_excerpt, previous_digests, variant, code_policy)
    elif material_type == "test":
        user_prompt = prompt_fn(topic, subject, level, grade, language, question_count or 10, test_type,
                                source_excerpt, code_policy=code_policy)
    elif material_type == "konspekt":
        user_prompt = prompt_fn(topic, subject, level, grade, language, include_homework, include_fun_facts,
                                include_assessment, include_examples, source_excerpt, previous_digests, variant,
                                code_policy)
    elif material_type == "lektsiya":
        user_prompt = prompt_fn(topic, subject, level, grade, language,
                                source_text=source_excerpt, code_policy=code_policy)
    else:
        user_prompt = prompt_fn(topic, subject, level, grade, language, source_text=source_excerpt,
                                code_policy=code_policy)

    # Apply the exact-topic guard to every material type. Previously the
    # focused variables/data-types rules lived mainly in the konspekt prompt,
    # so tests, presentations and lectures could still inherit the broad
    # Informatics template or an unrelated cached excerpt.
    scope_rule = _topic_scope_rule(subject, topic)
    if scope_rule:
        user_prompt += f"\n\n{scope_rule}"
    if _is_variable_topic(subject, topic):
        user_prompt += """

PYTHON VARIABLE FACTS FOR THIS EXACT TOPIC:
- Python assignment does not declare a fixed type for a variable name.
- The same name may later refer to a value of another type.
- Assigning 12.5 to a name that previously held 10 does not automatically cause a type-mismatch error.
- Do not add lists, dictionaries, functions/def, imports/modules, games, social-media posts, or superpower framing
  unless the teacher explicitly names them in the topic.
"""

    if language == "Таджикский" and subject == "Информатика" and code_policy == "needed":
        user_prompt += """

TAJIK CODE LANGUAGE RULE:
- Write every human-readable code string, comment, label, and explanation in natural Tajik.
- Variable names should use simple Tajik transliteration in Latin letters, for example nom, sinf, sin, qad,
  shogird, matn, raqam, natija. Do not use English variable names such as name, age, score, value, or student.
- Keep only Python built-ins and literals in their required form: input, print, int, float, str, bool, True, False.
- Text inside input() and print() must be Tajik Cyrillic, not Russian, Uzbek, or English.
- Keep code short and limited to the exact lesson topic; do not add def, import, classes, or unrelated libraries
  unless the topic explicitly asks for them.
"""

    if not include_examples:
        user_prompt += (
            '\n\nUSER OPTION: examples are disabled. Do not add illustrative or real-life examples. '
            'For any real_life_examples field, return an empty list. Keep only necessary exercises or solutions '
            'that are intrinsic to the requested material type.'
        )

    if teacher_context:
        user_prompt += f"""

TEACHER PREFERENCES (use these answers to tailor the difficulty, explanation style, timing and tasks; do not mention this block in the output):
{teacher_context[:2000]}
If a lesson design framework is included above, use its stages to organize the existing Dastyor lesson_stages and lesson_program fields. Keep Dastyor's JSON schema and all material-specific sections unchanged; do not output a separate generic lesson-plan schema.
"""

    lang_name = LANGUAGE_NAMES.get(language, "English")
    tajik_rules = _language_rules(language)

    if test_type in _QUESTION_TYPE_INFO:
        test_type_rule = f'Create exactly the number of questions requested, ALL of type "{test_type}".'
    else:
        test_type_rule = "Create exactly the number of questions requested, MIXING four types: multiple_choice, true_false, multiple_select, open_ended — do NOT make every question a 4-option multiple choice."


    system_prompts = {
        "konspekt": _konspekt_system_prompt(language),
        "lektsiya": _lecture_system_prompt(language),

        "test": f"""You are a school teacher creating a test. Return ONLY valid JSON.
Write ALL content in {lang_name} language.{tajik_rules}
{_TEACHER_SIMPLICITY_RULE}

CRITICAL RULES:
1. Write ONLY about the topic given.
2. {test_type_rule}
3. NEVER mix languages - write ONLY in {lang_name}.""",

        "prezentatsiya": f"""You are a school teacher creating a presentation with slides. Return ONLY valid JSON.
Write ALL content in {lang_name} language.{tajik_rules}
{_TEACHER_SIMPLICITY_RULE}

CRITICAL RULES:
1. Write ONLY about the topic given.
2. Create exactly the number of slides requested.
3. Each slide MUST have a title, 3-5 bullet points, and speaker notes.
4. NEVER mix languages - write ONLY in {lang_name}.
5. Return ONLY valid JSON, nothing else.""",

        "amaliy": f"""You are a school teacher writing hands-on practical tasks. Return ONLY valid JSON.
Write ALL content in {lang_name} language.{tajik_rules}
{_TEACHER_SIMPLICITY_RULE}

CRITICAL RULES:
1. Write ONLY about the topic given.
2. Every task has the pupil DO or MAKE something concrete, never answer a multiple-choice question.
3. NEVER mix languages - write ONLY in {lang_name}.""",

        "igra": f"""You are a school teacher building an interactive in-class game. Return ONLY valid JSON.
Write ALL content in {lang_name} language.{tajik_rules}
{_TEACHER_SIMPLICITY_RULE}

CRITICAL RULES:
1. Write ONLY about the topic given.
2. Every round must be answerable from the lesson itself, never unrelated general trivia.
3. NEVER mix languages - write ONLY in {lang_name}.""",

        "varaq": f"""You are a school teacher building a printable A4 worksheet. Return ONLY valid JSON.
Write ALL content in {lang_name} language.{tajik_rules}
{_TEACHER_SIMPLICITY_RULE}

CRITICAL RULES:
1. Write ONLY about the topic given.
2. Mix at least 2 different block types; every block must be solvable from the lesson itself.
3. NEVER mix languages - write ONLY in {lang_name}.""",
    }

    system_prompt = system_prompts.get(material_type, system_prompts["konspekt"])

    content = await _call_ai(system_prompt, user_prompt, language, log_label=f"{material_type} topic={topic[:50]}",
                             max_tokens=_MAX_TOKENS_BY_TYPE.get(material_type, 10000))

    if not include_examples and material_type in ("konspekt", "lektsiya"):
        content["real_life_examples"] = []

    if material_type in ("konspekt", "lektsiya", "prezentatsiya", "test", "amaliy", "igra", "varaq"):
        _enforce_code_relevance(content, code_policy, topic)

    # Tajik output gets a final subject + language review. The model can produce
    # structurally valid JSON while still leaving Russian loanwords, literal
    # translations, or generic text unrelated to the requested topic.
    if language == "Таджикский" and _needs_tajik_review(material_type, content, topic, code_policy):
        content = await _verify_and_fix(
            material_type, content, language, topic, subject, grade, code_policy
        )

    if material_type in ("konspekt", "lektsiya", "prezentatsiya", "test", "amaliy", "igra", "varaq"):
        _enforce_code_relevance(content, code_policy, topic)

    if material_type in ("konspekt", "lektsiya", "prezentatsiya", "test", "amaliy", "igra", "varaq"):
        content["subject"] = subject
        content["grade"] = grade
        content["language"] = language
        content["level"] = level
        content["template"] = template
        if variant:
            content["variant"] = variant

    if material_type in ("konspekt", "lektsiya") and subject == "География" and content.get("map_locations"):
        try:
            from app.map_builder import build_geography_map
            map_path = await build_geography_map(content["map_locations"])
            if map_path:
                content["map_image"] = map_path
        except Exception as e:
            logger.warning(f"Map generation failed for topic={topic[:50]}: {e}")

    if material_type in ("konspekt", "lektsiya"):
        _validate_code_blocks(content, topic)
        _typeset_math_content(content, topic)
        _render_timeline_images(content, topic)
        _render_subject_figures(content, topic)
        # No pictures in a konspekt or a lecture (see konspekt_design /
        # lecture_design), so nothing is fetched from Commons or Wikipedia.

    if material_type == "prezentatsiya":
        _drop_bullets_duplicating_visual(content, topic)
        _typeset_math_content(content, topic)
        _render_slide_figures(content, topic)
        # No fetched photos in presentations (see the prompt below, which no
        # longer asks for "image_query" either) -- only the data-driven
        # "visual" figures above (charts/diagrams) appear on slides.

    if material_type == "test":
        _validate_test_quality(content, topic, question_count or 10)
        _typeset_math_content(content, topic)
        await _render_test_images(content, topic)

    if material_type == "amaliy":
        _validate_practical_quality(content, topic)

    if material_type == "igra":
        _validate_game_quality(content, topic)
        _typeset_math_content(content, topic)

    if material_type == "varaq":
        _validate_varaq_quality(content, topic)
        _typeset_math_content(content, topic)
        _render_varaq_diagrams(content, topic)
        await _render_varaq_images(content, topic)


    return content


_exhausted_keys: set[str] = set()


async def _call_ai(system_prompt: str, user_prompt: str, language: str, log_label: str,
                   max_tokens: int = 24000, temperature: float | None = None) -> dict:
    global _api_call_count, _daily_reset_time

    async with ai_slot(log_label):
        return await _call_ai_inner(system_prompt, user_prompt, language, log_label, max_tokens, temperature)


async def _call_ai_inner(system_prompt: str, user_prompt: str, language: str, log_label: str,
                         max_tokens: int = 24000, temperature: float | None = None) -> dict:
    global _api_call_count, _daily_reset_time

    today = datetime.now(timezone.utc).date()
    if today != _daily_reset_time:
        _api_call_count = 0
        _daily_reset_time = today
        logger.info(f"Daily API call count reset on {today}")


    api_keys = [k for k in [settings.AI_API_KEY, settings.AI_API_KEY_2, settings.AI_API_KEY_3, settings.AI_API_KEY_4, settings.AI_API_KEY_5] if k]
    _live = [k for k in api_keys if k not in _exhausted_keys]
    if _live:
        api_keys = _live
    if not api_keys:
        logger.error("No AI API keys configured")
        raise Exception("AI service not configured")

    last_error = None
    start_time = time.time()

    for key_idx, key in enumerate(api_keys):
        for attempt in range(3):
            if attempt > 0 or key_idx > 0:
                import asyncio
                await asyncio.sleep(2)
            try:
                # Lower temperature keeps school facts, terminology, and the
                # requested topic stable instead of encouraging decoration.
                temp = temperature if temperature is not None else (0.25 if attempt > 0 else 0.4)
                logger.info(f"AI request: {log_label} attempt={attempt+1} key_idx={key_idx}")

                async with httpx.AsyncClient(timeout=180.0, verify=SSL_CONTEXT) as client:
                    response = await client.post(
                        f"{settings.AI_BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.AI_MODEL,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": temp,
                            "max_tokens": max_tokens,
                        },
                    )

                if response.status_code == 402:
                    last_error = Exception(f"API key credits exhausted")
                    if key not in _exhausted_keys:
                        _exhausted_keys.add(key)
                        logger.warning(f"AI API key {key[:8]}... credits exhausted, skipping it for the rest of this process")
                    break

                if response.status_code != 200:
                    error_msg = f"AI API error: {response.status_code} - {response.text[:200]}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()

                if not content:
                    raise Exception("AI returned empty response")

                parsed = _parse_json(content)
                translated = _translate_json(parsed, language)

                elapsed_time = time.time() - start_time
                _api_call_count += 1

                usage = data.get("usage") or {}
                logger.info(
                    f"AI SUCCESS: {log_label} time={elapsed_time:.2f}s "
                    f"calls_today={_api_call_count} "
                    f"tokens_in={usage.get('prompt_tokens', '?')} "
                    f"tokens_out={usage.get('completion_tokens', '?')} "
                    f"tokens_total={usage.get('total_tokens', '?')}"
                )
                return translated

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"AI JSON parse error on attempt {attempt+1}/{3}: {str(e)[:200]}")
                continue
            except httpx.TimeoutException:
                last_error = Exception("Server timeout. Please try again.")
                logger.error(f"AI timeout on attempt {attempt+1}/{3}")
                continue
            except httpx.ConnectError:
                last_error = Exception("Cannot connect to server. Check your internet connection.")
                logger.error(f"AI connection error on attempt {attempt+1}/{3}")
                continue
            except Exception as e:
                last_error = e
                logger.error(f"AI error on attempt {attempt+1}/{3}: {str(e)[:200]}")
                continue

    logger.error(f"AI FAILED after all attempts: {log_label} error={last_error}")
    raise Exception(f"AI returned invalid JSON after all attempts. Last error: {last_error}")


async def _call_ai_stream(system_prompt: str, user_prompt: str, log_label: str, max_tokens: int = 24000):
    global _api_call_count, _daily_reset_time

    async with ai_slot(f"{log_label} (stream)"):
        async for delta in _call_ai_stream_inner(system_prompt, user_prompt, log_label, max_tokens):
            yield delta


async def _call_ai_stream_inner(system_prompt: str, user_prompt: str, log_label: str, max_tokens: int = 24000):
    global _api_call_count, _daily_reset_time

    today = datetime.now(timezone.utc).date()
    if today != _daily_reset_time:
        _api_call_count = 0
        _daily_reset_time = today
        logger.info(f"Daily API call count reset on {today}")


    api_keys = [k for k in [settings.AI_API_KEY, settings.AI_API_KEY_2, settings.AI_API_KEY_3, settings.AI_API_KEY_4, settings.AI_API_KEY_5] if k]
    _live = [k for k in api_keys if k not in _exhausted_keys]
    if _live:
        api_keys = _live
    if not api_keys:
        logger.error("No AI API keys configured")
        raise Exception("AI service not configured")

    last_error = None
    start_time = time.time()

    for key_idx, key in enumerate(api_keys):
        for attempt in range(3):
            if attempt > 0 or key_idx > 0:
                await asyncio.sleep(2)
            got_any_content = False
            try:
                temp = 0.25 if attempt > 0 else 0.4
                logger.info(f"AI stream request: {log_label} attempt={attempt+1} key_idx={key_idx}")

                async with httpx.AsyncClient(timeout=180.0, verify=SSL_CONTEXT) as client:
                    async with client.stream(
                        "POST",
                        f"{settings.AI_BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.AI_MODEL,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": temp,
                            "max_tokens": max_tokens,
                            "stream": True,
                        },
                    ) as response:
                        if response.status_code == 402:
                            last_error = Exception("API key credits exhausted")
                            if key not in _exhausted_keys:
                                _exhausted_keys.add(key)
                                logger.warning(f"AI API key {key[:8]}... credits exhausted, skipping it for the rest of this process")
                            break

                        if response.status_code != 200:
                            body = await response.aread()
                            error_msg = f"AI API error: {response.status_code} - {body[:200]}"
                            logger.error(error_msg)
                            raise Exception(error_msg)

                        async for line in response.aiter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            payload = line[len("data:"):].strip()
                            if payload == "[DONE]":
                                break
                            try:
                                chunk = json.loads(payload)
                            except json.JSONDecodeError:
                                continue
                            delta = (chunk.get("choices") or [{}])[0].get("delta", {}).get("content")
                            if delta:
                                got_any_content = True
                                yield delta

                if got_any_content:
                    elapsed_time = time.time() - start_time
                    _api_call_count += 1
                    logger.info(f"AI STREAM SUCCESS: {log_label} time={elapsed_time:.2f}s calls_today={_api_call_count}")
                    return
                last_error = Exception("AI returned empty response")
                continue

            except httpx.TimeoutException as e:
                if got_any_content:
                    logger.error(f"AI stream interrupted (timeout) mid-response: {log_label}")
                    raise Exception("Stream interrupted by a timeout partway through.") from e
                last_error = Exception("Server timeout. Please try again.")
                logger.error(f"AI stream timeout on attempt {attempt+1}/{3}")
                continue
            except httpx.ConnectError as e:
                if got_any_content:
                    logger.error(f"AI stream interrupted (connection) mid-response: {log_label}")
                    raise Exception("Connection was lost partway through.") from e
                last_error = Exception("Cannot connect to server. Check your internet connection.")
                logger.error(f"AI stream connection error on attempt {attempt+1}/{3}")
                continue
            except Exception as e:
                if got_any_content:
                    logger.error(f"AI stream interrupted mid-response: {log_label}: {str(e)[:200]}")
                    raise
                last_error = e
                logger.error(f"AI stream error on attempt {attempt+1}/{3}: {str(e)[:200]}")
                continue

    logger.error(f"AI STREAM FAILED after all attempts: {log_label} error={last_error}")
    raise Exception(f"AI streaming failed after all attempts. Last error: {last_error}")


def _resolve_pointer(root, pointer: str):
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return None
    node = root
    parts = [seg.replace("~1", "/").replace("~0", "~") for seg in pointer[1:].split("/")]
    for i, seg in enumerate(parts):
        last = i == len(parts) - 1
        if isinstance(node, list):
            if not seg.lstrip("-").isdigit():
                return None
            idx = int(seg)
            if not (0 <= idx < len(node)):
                return None
            if last:
                return node, idx
            node = node[idx]
        elif isinstance(node, dict):
            if seg not in node:
                return None
            if last:
                return node, seg
            node = node[seg]
        else:
            return None
    return None


def _apply_fixes(content: dict, fixes: list) -> tuple[dict, int]:
    patched = copy.deepcopy(content)
    applied = 0
    for fix in fixes:
        if not isinstance(fix, dict):
            continue
        target = _resolve_pointer(patched, fix.get("path"))
        if target is None:
            logger.warning(f"Verify fix skipped, path not found: {str(fix.get('path'))[:120]}")
            continue
        parent, key = target
        new = fix.get("new")
        if not isinstance(new, (str, int, float)) or isinstance(new, bool):
            logger.warning(f"Verify fix skipped, non-scalar value at: {str(fix.get('path'))[:120]}")
            continue
        if parent[key] == new:
            continue
        parent[key] = new
        applied += 1
    return patched, applied


def _needs_tajik_review(
    material_type: str,
    content: dict,
    topic: str,
    code_policy: str | None = None,
) -> bool:
    """Cheap gate so a second AI call happens only when it is justified."""
    if not isinstance(content, dict):
        return True

    text_parts: list[str] = []

    def collect(value, key: str = ""):
        if isinstance(value, str):
            if key not in {"latex", "formula", "language"} and (key != "code" or code_policy == "needed"):
                text_parts.append(value.lower())
        elif isinstance(value, list):
            for item in value:
                collect(item, key)
        elif isinstance(value, dict):
            for child_key, child_value in value.items():
                collect(child_value, str(child_key))

    collect(content)
    text = "\n".join(text_parts)
    if not text.strip():
        return True

    # These are high-signal failures seen in real Tajik generations. The list
    # stays small on purpose; the expensive reviewer is the fallback, not the
    # normal path for every document.
    bad_words = (
        "условие", "условия", "переменная", "переменные", "луп", "лупа",
        "пример", "вопрос", "ответ", "уроков", "ученик", "учитель",
        "интизор", "сонлари", "қиммат", "типни", "сақлайдиган",
        "системасининг", "имконияти", "бир нечта", "бўлиш", "шаклида",
        "қўшилган", "запутанлик", "неравенствос", "кайси",
    )
    if any(word in text for word in bad_words):
        return True

    if code_policy == "none" and _has_programming_content(content):
        return True

    if code_policy == "needed" and _is_variable_topic("Информатика", topic):
        # Focused Tajik Python lessons also need a code-language and factual
        # review: the model can otherwise keep English identifiers or claim
        # that Python variables have a fixed declared type.
        return True

    main_content = content.get("main_content")
    if isinstance(main_content, str) and len(main_content.strip()) < 180:
        return True
    if material_type == "konspekt" and isinstance(main_content, str):
        paragraphs = [p for p in re.split(r"\n\s*\n", main_content.strip()) if p.strip()]
        if len(paragraphs) < 2:
            return True
    concepts = content.get("key_concepts")
    if isinstance(concepts, list) and len(concepts) < 3:
        return True

    # If none of the meaningful topic terms appears in the generated prose,
    # the model probably answered a generic subject instead of this topic.
    topic_terms = [
        token.lower() for token in re.findall(r"[\w\u0400-\u04ff]+", topic or "")
        if len(token) >= 4 and token.lower() not in {"мавзӯъ", "тема", "topic"}
    ]
    if topic_terms and not any(token in text for token in topic_terms):
        return True

    return False


async def _verify_and_fix(
    material_type: str,
    content: dict,
    language: str,
    topic: str,
    subject: str | None = None,
    grade: str | None = None,
    code_policy: str | None = None,
) -> dict:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    system_prompt = (
        "You are a meticulous subject-matter and language editor reviewing educational content for a school "
        f"teacher. Return ONLY valid JSON, with every prose field still written in {lang_name}."
    )
    language_check = (
        "\n- Any word from a different language that has no business being in {lang} text — a foreign "
        "spelling variant, a loanword used where a normal {lang} word exists, or a technical/grammatical "
        "term that was invented rather than being a real word an educated native speaker would recognize "
        "from a school textbook. This class of error reads as fluent and doesn't look 'wrong' at a glance, "
        "so check it deliberately rather than skimming for it."
    ).format(lang=lang_name)
    if language == "Таджикский":
        language_check += (
            " For Tajik specifically, watch for these exact confusions found before: 'ёроғ' (a real Tajik "
            "word but means WEAPON — wrong whenever it's used to mean an auxiliary/marker/particle, correct "
            "term is 'ёридиҳанда'/'ёвар'), 'келима' (Turkish spelling — correct Tajik spelling is 'калима'), "
            "'ҳозирон' used for the present tense (means 'those present/attendees' — correct term for present "
            "tense is 'ҳозира'), and the Russian conjunction 'и' used in place of Tajik 'ва' (and)."
        )

    code_check = ""
    if code_policy == "none":
        code_check = (
            "\n- This topic is not a programming topic. Remove or rewrite every irrelevant Python, C++, "
            "compiler, API, code example, and programming exercise from prose fields, objectives, lesson stages, "
            "homework, examples, and assessment. Replace it with a concrete example or task about the requested "
            "topic itself. Do not leave a code task merely because the subject is Informatics."
        )
    elif subject == "Информатика" and _is_variable_topic(subject, topic):
        code_check = (
            "\n- This is a focused Python variables/data-types lesson. Correct the Python facts: assignment does "
            "not declare a fixed variable type, and assigning a float to a name that previously held an integer "
            "does not by itself cause a type-mismatch error. Remove lists, inventory, swapping variables, and any "
            "other data type not explicitly named in the topic. In code fields, keep Python built-ins/literals "
            "input, print, int, float, str, bool, True, False unchanged, but use Tajik transliterated variable "
            "names such as nom, sinf, sin, qad, shogird, matn, raqam, natija instead of name, age, score, value, "
            "player, or student. Text inside input() and print() must be Tajik Cyrillic. Remove game, social-media, "
            "and \"superpower\" framing."
        )

    subject_context = f', subject "{subject}"' if subject else ""
    grade_context = f', grade "{grade}"' if grade else ""
    user_prompt = f"""Review the following {material_type} JSON about "{topic}"{subject_context}{grade_context} for factual accuracy, topic relevance, completeness, and language correctness.

Fix ONLY real problems:
- Invented, incorrect, or unverifiable facts, dates, statistics, or named people/events
- Claims that contradict each other within the document
- Anything generic, nonsensical, or unrelated to "{topic}"; replace it with a concrete explanation, fact,
  mechanism, example, exercise, or step that is genuinely about the requested topic
- Missing or empty required prose in a field that the document's schema already provides
- For a konspekt, keep the existing schema but ensure main_content has 2-3 substantive paragraphs and
  the key_concepts, objectives, quick_check, and exercises contain concrete topic-specific content.
- For Tajik: grammar, spelling, unnatural literal translations, Russian words, and invented or wrong
  school terminology. Rewrite the whole string when a word-by-word patch would leave the sentence unnatural.{language_check}{code_check}

Do NOT report anything that is already correct. Most documents have no errors at all — an empty list is the expected, normal answer.

Return ONLY a JSON object listing the corrections, in this exact shape:
{{"fixes": [{{"path": "/main_content/2/text", "new": "the corrected text"}}]}}

- "path" is an RFC 6901 JSON Pointer to the exact value that is wrong, in the document below. Array items are addressed by index, e.g. "/key_concepts/0/definition".
- "new" is the corrected value, a string or number only. Rewrite as little as possible: keep the original wording, tone and length, changing only the part that is actually wrong.
- Never invent a path that is not in the document, never add fields, and never remove or reorder array items.
- Fix every affected string in a list with its own path. Preserve code, formulas, JSON shape, and proper names unless they are actually wrong.
- If the document is fine, return exactly: {{"fixes": []}}

The document to review:
{json.dumps(content, ensure_ascii=False)}"""

    try:
        result = await _call_ai(
            system_prompt,
            user_prompt,
            language,
            log_label=f"verify {material_type} topic={topic[:50]}",
            max_tokens=5000,
        )
        if isinstance(result, dict) and isinstance(result.get("fixes"), list):
            fixes = result["fixes"]
            if not fixes:
                return content
            patched, applied = _apply_fixes(content, fixes)
            logger.info(
                f"Verify pass for {material_type}: {applied}/{len(fixes)} fix(es) applied"
            )
            return patched if applied else content
        logger.warning(f"Verify pass for {material_type} returned an unexpected shape, keeping original")
    except Exception as e:
        logger.warning(f"Verify pass failed for {material_type} topic={topic[:50]}, keeping original: {str(e)[:200]}")
    return content


# Output caps are deliberately close to the requested document size. A large
# cap does not improve the lesson; it only lets the model spend tokens on
# repetition and reasoning.
_MAX_TOKENS_BY_TYPE = {
    "konspekt": 7500,
    "test": 5000,
    "prezentatsiya": 8000,
    "lektsiya": 9000,
    "amaliy": 6000,
    "igra": 6000,
    "varaq": 6000,
}
KONSPEKT_MAX_TOKENS = _MAX_TOKENS_BY_TYPE["konspekt"]

_KONSPEKT_STREAM_FIELDS = [
    "title", "subtitle", "duration", "competencies", "objectives", "key_concepts",
    "key_terms", "real_life_examples", "lesson_program", "lesson_stages", "tools", "main_content",
    "pair_work", "consolidation", "group_work", "visual_aid", "summary", "formulas",
    "worked_examples", "concept_cards", "map_locations", "homework", "assessment",
    "important_notes", "key_ideas", "teacher_tips",
    "visual_blocks", "quick_check", "code_blocks", "figures",
]


async def generate_konspekt_stream(
    topic: str,
    subject: str,
    language: str,
    level: str,
    grade: str,
    include_homework: bool = True,
    include_fun_facts: bool = True,
    include_assessment: bool = True,
    include_examples: bool = True,
    source_text: str | None = None,
    template: str | None = None,
    previous_digests: list[dict] | None = None,
):
    try:
        if not source_text and not _is_variable_topic(subject, topic):
            source_text = _load_cached_textbook(subject, grade, topic)
        retrieval_query = " ".join(value for value in (topic, subject, grade) if value)
        source_excerpt = (
            _select_relevant_excerpt(source_text, topic, query_text=retrieval_query)
            if source_text else None
        )
        code_policy = _code_relevance(subject, topic)

        yield {"stage": "source_analysis", "status": "start"}
        yield {"stage": "source_analysis", "status": "done", "used_source": bool(source_excerpt)}

        yield {"stage": "understand_topic", "status": "start"}
        system_prompt = _konspekt_system_prompt(language)
        yield {"stage": "understand_topic", "status": "done"}

        yield {"stage": "extract_info", "status": "start"}
        variant: dict = {}
        user_prompt = _konspekt_prompt(
            topic, subject, level, grade, language,
            include_homework, include_fun_facts, include_assessment, include_examples,
            source_excerpt, previous_digests, variant, code_policy,
        )
        yield {"stage": "extract_info", "status": "done"}

        yield {"stage": "outline", "status": "start"}

        buffer = ""
        remaining_fields = list(_KONSPEKT_STREAM_FIELDS)
        active_field: str | None = None
        outline_done = False
        generate_sections_started = False

        async for delta in _call_ai_stream(system_prompt, user_prompt, log_label=f"konspekt-stream topic={topic[:50]}",
                                           max_tokens=KONSPEKT_MAX_TOKENS):
            if not outline_done:
                outline_done = True
                yield {"stage": "outline", "status": "done"}
                yield {"stage": "generate_sections", "status": "start"}
                generate_sections_started = True

            buffer += delta
            yield {"type": "token", "delta": delta}

            found = None
            for field in remaining_fields:
                if f'"{field}"' in buffer and (f'"{field}":' in buffer or f'"{field}" :' in buffer):
                    found = field
                    break
            if found:
                remaining_fields.remove(found)
                if active_field:
                    yield {"type": "field_done", "field": active_field}
                active_field = found
                yield {"type": "field_start", "field": active_field}

        if not generate_sections_started:
            yield {"type": "error", "message": "AI returned an empty response.", "code": "ai_error"}
            return
        if active_field:
            yield {"type": "field_done", "field": active_field}
        yield {"stage": "generate_sections", "status": "done"}

        yield {"stage": "format", "status": "start"}
        try:
            parsed = _parse_json(buffer)
        except Exception as e:
            logger.error(f"konspekt-stream JSON parse failed topic={topic[:50]}: {str(e)[:200]}")
            yield {"type": "error", "message": "AI javobini qayta ishlab bo'lmadi. Qayta urinib ko'ring.", "code": "parse_error"}
            return
        content = _translate_json(parsed, language)
        _enforce_code_relevance(content, code_policy, topic)
        yield {"stage": "format", "status": "done"}

        if language == "Таджикский" and _needs_tajik_review("konspekt", content, topic, code_policy):
            yield {"stage": "language_review", "status": "start"}
            content = await _verify_and_fix(
                "konspekt", content, language, topic, subject, grade, code_policy
            )
            _enforce_code_relevance(content, code_policy, topic)
            yield {"stage": "language_review", "status": "done"}

        yield {"stage": "visual_elements", "status": "start"}
        content["subject"] = subject
        content["grade"] = grade
        content["language"] = language
        if variant:
            content["variant"] = variant
        content["level"] = level
        content["template"] = template
        if subject == "География" and content.get("map_locations"):
            try:
                from app.map_builder import build_geography_map
                map_path = await build_geography_map(content["map_locations"])
                if map_path:
                    content["map_image"] = map_path
            except Exception as e:
                logger.warning(f"Map generation failed for topic={topic[:50]}: {e}")
        _validate_code_blocks(content, topic)
        _typeset_math_content(content, topic)
        _render_timeline_images(content, topic)
        _render_subject_figures(content, topic)
        yield {"stage": "visual_elements", "status": "done", "block_count": len(content.get("visual_blocks") or [])}

        yield {"stage": "validate", "status": "start"}
        yield {"stage": "validate", "status": "done"}

        yield {"type": "complete", "content": content}

    except Exception as e:
        logger.error(f"generate_konspekt_stream failed topic={topic[:50]}: {str(e)[:300]}", exc_info=True)
        message = str(e) or "Noma'lum xatolik yuz berdi."
        code = "daily_limit" if "Daily limit reached" in message else "ai_error"
        yield {"type": "error", "message": message, "code": code}


def _regenerate_question_prompt(topic: str, subject: str, level: str, grade: str, language: str, existing_questions: list[str], question_type: str = "multiple_choice") -> str:
    level_map = {
        "Лёгкий": "Beginner. Simple, straightforward question.",
        "Средний": "Intermediate.",
        "Сложный": "Advanced. Challenging, requires deeper understanding.",
    }
    level_text = level_map.get(level, level_map["Средний"])
    subject_hint = _subject_hint(subject, language, grade, topic)
    lang_name = LANGUAGE_NAMES.get(language, "English")
    existing_text = "\n".join(f"- {q}" for q in existing_questions) or "(none)"
    code_rule = _code_relevance_rule(subject, _code_relevance(subject, topic))

    info = _QUESTION_TYPE_INFO.get(question_type) or _QUESTION_TYPE_INFO["multiple_choice"]
    question_type = question_type if question_type in _QUESTION_TYPE_INFO else "multiple_choice"
    type_instructions = info["instructions"]
    shape = info["shape"](topic, lang_name)

    return f"""Create exactly ONE new "{question_type}" question about "{topic}" for grade {grade}, subject "{subject}".

CRITICAL: Write ALL content in {lang_name} language. Return ONLY valid JSON, nothing else.

Subject style: {subject_hint}
Difficulty: {level_text}
{(chr(10) + code_rule) if code_rule else ""}
{_TEACHER_SIMPLICITY_RULE}

{type_instructions}

The question MUST be different in wording and focus from these existing questions in the same test:
{existing_text}

Return THIS exact JSON (nothing else):
{shape}"""


def _regenerate_practical_task_prompt(kind: str, topic: str, subject: str, level: str, grade: str,
                                      language: str, existing_titles: list[str]) -> str:
    level_map = {
        "Лёгкий": "Beginner. Short, closely-guided, one clear step at a time.",
        "Средний": "Intermediate. Multi-step but still fits one lesson.",
        "Сложный": "Advanced. Open-ended, the pupil plans their own approach.",
    }
    level_text = level_map.get(level, level_map["Средний"])
    subject_hint = _subject_hint(subject, language, grade, topic)
    lang_name = LANGUAGE_NAMES.get(language, "English")
    existing_text = "\n".join(f"- {t}" for t in existing_titles) or "(none)"
    code_rule = _code_relevance_rule(subject, _code_relevance(subject, topic))

    if kind == "group_tasks":
        shape = ('{"title": "Short task name", "group_size": "group size in ' + lang_name +
                 ', e.g. \\"3-4 \\" + the ' + lang_name + ' word for pupils", '
                 '"roles": ["Role 1: what they do", "Role 2: what they do", "Role 3: what they do"], '
                 '"instructions": "What the group does together, step by step", '
                 '"expected_outcome": "What a completed group answer looks like"}')
        kind_instructions = (
            "Name concrete roles so the work actually splits between group members rather than one pupil "
            "doing it alone — 3-4 roles, each with its own real contribution."
        )
    else:
        kind = "individual_tasks"
        shape = ('{"title": "Short task name", "difficulty": "easy|medium|hard", '
                 '"instructions": "What the pupil does, step by step", '
                 '"expected_outcome": "What a completed answer looks like"}')
        kind_instructions = "Pick whichever difficulty fits naturally — it doesn't have to match the task it's replacing."

    return f"""Create exactly ONE new hands-on practical task ({kind}) about "{topic}" for grade {grade}, subject "{subject}".

CRITICAL: Write ALL content in {lang_name} language. Return ONLY valid JSON, nothing else.

The pupil must DO or MAKE something concrete (measure, build, classify, interview, write, calculate from real
data, observe and record) — never a multiple-choice question wearing a "task" label. {kind_instructions}
Every task needs "expected_outcome" — what a completed answer/product actually looks like, concrete enough
that a teacher can grade it without guessing.

Subject style: {subject_hint}
Difficulty: {level_text}
{(chr(10) + code_rule) if code_rule else ""}
{_TEACHER_SIMPLICITY_RULE}

The task MUST be different in focus from these existing tasks on the same worksheet:
{existing_text}

Return THIS exact JSON (nothing else):
{shape}"""


def _regenerate_slide_prompt(topic: str, subject: str, level: str, grade: str, language: str, slide_index: int, total_slides: int, existing_titles: list[str]) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    existing_text = "\n".join(f"- {t}" for t in existing_titles) or "(none)"
    code_rule = _code_relevance_rule(subject, _code_relevance(subject, topic))

    return f"""Create exactly ONE new presentation slide (slide {slide_index + 1} of {total_slides}) about "{topic}" for grade {grade}, subject "{subject}".

CRITICAL: Write ALL content in {lang_name} language. Return ONLY valid JSON, nothing else.

The slide MUST cover different ground than these other slides already in the presentation:
{existing_text}
{(chr(10) + code_rule) if code_rule else ""}
{_TEACHER_SIMPLICITY_RULE}

RULES (this slide must fit in seamlessly with the rest of an existing deck built to these same rules):
- Bullet points are for reading off a screen, not a script: each one a SHORT, clear phrase (4-8 words), never a full sentence.
- Prefer a "visual" over plain bullets whenever the content fits one of these shapes — actively look for this before defaulting to a bullet list:
  - {{"type": "table", "data": {{"headers": [...], "rows": [[...], ...]}}}} — a grid of facts/figures
  - {{"type": "comparison", "data": {{"criteria": [...], "items": [{{"name": "...", "values": [...]}}, ...]}}}} — contrasting 2-4 things
  - {{"type": "process", "data": {{"steps": [{{"title": "...", "description": "..."}}, ...]}}}} — an ordered sequence (3-6 steps). ANY "steps to do X"/"how to"/procedure content is a "process", never plain bullets.
  - {{"type": "chart", "data": {{"chart_type": "bar|pie|line", "categories": [...], "series": [{{"name": "...", "values": [numbers]}}, ...]}}}} — a real editable chart for numeric content: shares/proportions → "pie", comparing sizes → "bar", a trend over time → "line". Only real or clearly illustrative figures — never invent precise-looking fake statistics.
- If there IS a "visual": bullet_points has 1-2 short lead-in items, and must not repeat the visual's own data.
- If there is NO "visual": bullet_points has 3-4 items — enough to actually cover the point, not so many it becomes a wall of text.
- body: ONE real sentence (~18-30 words) adding a specific fact/definition/reason, not a restatement of the bullets — every other slide in this deck has one, so this slide needs one too to fit in.
- speaker_notes: EXTENSIVE, at least 3-4 sentences — this is where the actual facts/dates/names/explanations live, not on the slide itself.

Return THIS exact JSON (nothing else) — omit the "visual" key entirely if this slide doesn't have one:
{{
  "title": "Engaging slide title",
  "bullet_points": ["Short phrase", "Another short phrase", "A third", "A fourth"],
  "body": "One real sentence with a specific fact this topic needs, not a restatement of the bullets.",
  "speaker_notes": "Extensive teaching notes for the teacher, at least 3-4 sentences — the actual detail lives here."
}}"""


_KONSPEKT_SECTION_SPECS = {
    "competencies": "a JSON array of 3-4 SHORT phrases (max ~12 words each) — not detailed sentences",
    "objectives": "a JSON array of 3-4 SHORT phrases (max ~12 words each) — not detailed sentences",
    "key_concepts": "a JSON array of 4-5 detailed items, each formatted as \"Concept: explanation\"",
    "key_terms": "a JSON array of 3-4 items, each formatted as \"Term: definition and example\"",
    "real_life_examples": "a JSON array of 3-4 detailed scenario items",
    "lesson_program": "a single string: a 4-5 sentence description of the lesson flow",
    "tools": "a JSON array of 3-4 items, each formatted as \"Tool: why/how it's used\"",
    "main_content": "a single string: 3-4 detailed paragraphs (separated by \\n\\n), 4-5 sentences each, with real facts and examples",
    "pair_work": "a single string: a 3-4 sentence pair-work activity with instructions and expected outcomes",
    "consolidation": "a single string: a 3-4 sentence consolidation activity with specific tasks",
    "group_work": "a JSON array of exactly 3 task strings, one per group, each targeting a different key term/concept from this lesson (see the group_work rule)",
    "visual_aid": "a single string: a 3-4 sentence description of a visual aid and how to use it",
    "summary": "a single string: a 4-5 sentence summary covering all key points",
    "homework": "a JSON array of 2-3 detailed task items",
    "assessment": "a single string: 3-4 sentences of assessment criteria",
}


def _regenerate_konspekt_section_prompt(
    section: str, existing_content: dict, topic: str, subject: str, level: str, grade: str, language: str,
    material_type: str = "konspekt",
) -> str:
    doc_word = "lecture (лекция)" if material_type == "lektsiya" else "lesson plan (konspekt)"
    lang_name = LANGUAGE_NAMES.get(language, "English")
    level_map = {
        "Лёгкий": "Beginner. Very simple language, like talking to a friend.",
        "Средний": "Intermediate. Clear with real examples.",
        "Сложный": "Advanced. Deeper but still practical and engaging.",
    }
    level_text = level_map.get(level, level_map["Средний"])
    shape_hint = _KONSPEKT_SECTION_SPECS.get(section, "content matching the existing field's type (array or string)")
    code_rule = _code_relevance_rule(subject, _code_relevance(subject, topic))

    other_context = {
        k: v for k, v in existing_content.items()
        if k != section and k not in ("title", "subtitle", "language", "subject", "grade") and isinstance(v, (str, list)) and v
    }
    context_json = json.dumps(other_context, ensure_ascii=False)
    if len(context_json) > 2500:
        context_json = context_json[:2500] + "…"

    return f"""Rewrite ONLY the "{section}" section of an existing {doc_word} about "{topic}" for grade {grade}, subject "{subject}".

Subject style/difficulty: {level_text}
{(chr(10) + code_rule) if code_rule else ""}
{_TEACHER_SIMPLICITY_RULE}

CRITICAL: Write in {lang_name} language. Return ONLY valid JSON with exactly one key: "{section}".

The rest of this {doc_word} already exists (for context and consistency only — do not repeat or return it):
{context_json}

Write a NEW, meaningfully DIFFERENT version of "{section}" than whatever it likely was before — the teacher specifically asked to regenerate this section because they didn't like it. It must stay factually consistent with the rest of the document shown above, in the same {lang_name} language, with the same rules as normal generation (real facts, no invented statistics, no filler/meta commentary).

"{section}" must be {shape_hint}.

Return THIS exact JSON shape (nothing else):
{{"{section}": <the new content described above>}}"""


async def regenerate_item(
    material_type: str,
    topic: str,
    subject: str,
    language: str,
    level: str,
    grade: str,
    item_index: int = 0,
    existing_items: list[dict] | None = None,
    section: str | None = None,
    existing_content: dict | None = None,
) -> dict:
    existing_items = existing_items or []
    lang_name = LANGUAGE_NAMES.get(language, "English")
    tajik_rules = ""
    if language == "Таджикский":
        tajik_rules = (
            "\nWrite in correct literary Tajik (тоҷикӣ). NEVER mix Russian words into Tajik text."
        )

    if material_type in ("konspekt", "lektsiya"):
        if not section:
            raise ValueError(f"Regenerating a {material_type} item requires 'section'")
        user_prompt = _regenerate_konspekt_section_prompt(
            section, existing_content or {}, topic, subject, level, grade, language, material_type=material_type
        )
        doc_word = "lecture (лекция)" if material_type == "lektsiya" else "lesson plan (konspekt)"
        system_prompt = (
            f"You are revising one section of an existing {doc_word}. Return ONLY valid JSON.\n"
            f"Write ALL content in {lang_name} language.{tajik_rules}\n"
            f"Return ONLY the single key \"{section}\" — no other fields, no commentary."
        )
        return await _call_ai(system_prompt, user_prompt, language, log_label=f"regenerate-section {material_type} topic={topic[:50]} section={section}")

    if material_type == "test":
        existing_questions = [item.get("question", "") for item in existing_items if item.get("question")]
        question_type = "multiple_choice"
        if 0 <= item_index < len(existing_items):
            question_type = existing_items[item_index].get("type") or "multiple_choice"
        user_prompt = _regenerate_question_prompt(topic, subject, level, grade, language, existing_questions, question_type)
        system_prompt = (
            "You are a school teacher writing a single test question. Return ONLY valid JSON.\n"
            f"Write ALL content in {lang_name} language.{tajik_rules}"
        )
    elif material_type == "prezentatsiya":
        existing_titles = [item.get("title", "") for item in existing_items if item.get("title")]
        user_prompt = _regenerate_slide_prompt(
            topic, subject, level, grade, language, item_index, len(existing_items) or item_index + 1, existing_titles
        )
        system_prompt = (
            "You are a school teacher writing a single presentation slide. Return ONLY valid JSON.\n"
            f"Write ALL content in {lang_name} language.{tajik_rules}"
        )
    elif material_type == "amaliy":
        kind = section if section in ("individual_tasks", "group_tasks") else "individual_tasks"
        existing_titles = [item.get("title", "") for item in existing_items if item.get("title")]
        user_prompt = _regenerate_practical_task_prompt(kind, topic, subject, level, grade, language, existing_titles)
        system_prompt = (
            "You are a school teacher writing a single hands-on practical task. Return ONLY valid JSON.\n"
            f"Write ALL content in {lang_name} language.{tajik_rules}"
        )
    elif material_type == "varaq":
        existing_instructions = [item.get("instructions", "") for item in existing_items if item.get("instructions")]
        user_prompt = _regenerate_varaq_block_prompt(topic, subject, level, grade, language, existing_instructions)
        system_prompt = (
            "You are a school teacher writing a single worksheet block. Return ONLY valid JSON.\n"
            f"Write ALL content in {lang_name} language.{tajik_rules}"
        )
    else:
        raise ValueError(f"Regenerating a single item is only supported for 'test', 'prezentatsiya', 'amaliy', and 'varaq', got {material_type!r}")

    return await _call_ai(system_prompt, user_prompt, language, log_label=f"regenerate-item {material_type} topic={topic[:50]} idx={item_index}")


_CHAT_EDIT_DOC_WORD = {
    "konspekt": "lesson plan (konspekt)",
    "lektsiya": "lecture (лекция)",
    "test": "test",
    "prezentatsiya": "presentation",
}


async def chat_edit_material(
    material_type: str,
    content: dict,
    instruction: str,
    topic: str,
    subject: str,
    language: str,
    level: str,
    grade: str,
) -> dict:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    tajik_rules = ""
    if language == "Таджикский":
        tajik_rules = "\nWrite in correct literary Tajik (тоҷикӣ). NEVER mix Russian words into Tajik text."

    doc_word = _CHAT_EDIT_DOC_WORD.get(material_type, material_type)
    system_prompt = (
        f"You are editing an existing {doc_word} for a school teacher, per their instruction.\n"
        "You will be given the CURRENT content as JSON and an EDIT INSTRUCTION in natural language.\n"
        "Return ONLY the full updated content as JSON, in EXACTLY the same top-level keys and the same "
        "nested shape (e.g. the \"questions\" or \"slides\" list items keep the same fields) as the current "
        "content — you are editing it in place, not redesigning its schema.\n"
        "Apply ONLY what the instruction asks for. Every other field's value must be copied over unchanged "
        "from the current content — do not paraphrase, shorten, or \"improve\" anything the instruction did "
        "not mention.\n"
        f"Write ALL content in {lang_name} language.{tajik_rules}\n"
        "Return ONLY valid JSON — no markdown code fences, no commentary before or after it."
    )
    user_prompt = (
        f"CURRENT CONTENT (JSON):\n{json.dumps(content, ensure_ascii=False)}\n\n"
        f"EDIT INSTRUCTION: {instruction}\n\n"
        f"Context: topic=\"{topic}\", subject=\"{subject}\", level=\"{level}\", grade=\"{grade}\"."
    )
    result = await _call_ai(
        system_prompt, user_prompt, language,
        log_label=f"chat-edit {material_type} topic={topic[:50]} instruction={instruction[:60]!r}",
    )
    if not result.get("title") and content.get("title"):
        result["title"] = content["title"]
    return result


_MATERIAL_WORD = {
    "konspekt": "lesson notes (konspekt)",
    "lektsiya": "lecture",
    "test": "test",
    "prezentatsiya": "presentation",
    "amaliy": "practical worksheet",
    "varaq": "worksheet",
}

_CLARIFY_LANGUAGE_NAMES = {
    "русский": "Russian",
    "russian": "Russian",
    "ru": "Russian",
    "таджикский": "Tajik (Cyrillic Tajik, тоҷикӣ)",
    "tajik": "Tajik (Cyrillic Tajik, тоҷикӣ)",
    "tg": "Tajik (Cyrillic Tajik, тоҷикӣ)",
    "английский": "English",
    "english": "English",
    "en": "English",
}


async def clarify_topic(
    material_type: str,
    topic: str,
    subject: str,
    language: str,
    grade: str,
) -> dict:
    """Cheap pre-generation check: is `topic` specific enough to write one
    focused lesson from, or does it span several unrelated subtopics (e.g.
    "Python" for a whole course vs. "Python: variables and data types" for
    one lesson)? If too broad, ask ONE short clarifying question in the
    teacher's own language instead of letting the real generation prompt
    guess and produce an unfocused or misdirected material — this mirrors
    how a teacher assistant would actually behave, and is the single
    cheapest, highest-leverage quality improvement available before the
    expensive full-generation call runs. The teacher picks one of the
    returned `options` by tapping it — they never type a free-text answer
    — so each option must stand alone as a complete, specific sub-topic,
    not a fragment that needs the question's wording to make sense.
    Returns {"needs_clarification": bool, "question": str | None,
    "options": list[str]}.
    """
    lang_name = _CLARIFY_LANGUAGE_NAMES.get(str(language or "").strip().casefold(), "Russian")
    doc_word = _MATERIAL_WORD.get(material_type, material_type)
    tajik_rules = _language_rules(language)
    system_prompt = (
        f"A school teacher wants a single focused {doc_word} for ONE lesson, on subject "
        f"\"{subject}\", grade {grade}. Judge whether their topic is specific enough to write "
        "one focused lesson from, or whether it actually spans multiple unrelated lessons/subtopics "
        "(e.g. a whole course name, a whole chapter, a whole programming language, a whole historical "
        "era, or a whole book) where picking the wrong sub-focus would produce an unfocused or "
        "misdirected material.\n"
        "Examples of TOO BROAD (needs_clarification=true): \"Python\", \"World War II\", \"Fractions\", "
        "\"Shakespeare\", \"Grammar\". Each of these could mean many different single lessons.\n"
        "Examples of SPECIFIC ENOUGH (needs_clarification=false): \"Python: variables and data types\", "
        "\"The Battle of Stalingrad\", \"Adding fractions with different denominators\", \"Romeo and "
        "Juliet: Act 1 themes\", \"Subject-verb agreement\". Treat a short but concrete sub-topic as "
        "specific enough — do NOT ask just because the topic is brief.\n"
        f"If (and only if) the topic is TOO BROAD like the first example set, write ONE short question "
        f"in {lang_name}, and you MUST also fill \"options\" with exactly 3-4 concrete, non-empty answer "
        "options the teacher can tap instead of typing. Each option is a short, complete, specific "
        f"sub-topic phrase in {lang_name} (2-6 simple words) that stands on its own as a lesson topic — never a "
        "fragment, never yes/no, never numbered. Use only everyday words suitable for the stated grade; do not "
        "use difficult academic words. needs_clarification=true is only ever valid together "
        "with a non-empty \"options\" list — never return true with an empty or missing options list.\n"
        f"ABSOLUTE LANGUAGE RULE: write the question and every option ONLY in {lang_name}. NEVER use "
        "Uzbek, even if the topic or the model's default language is Uzbek. Never mix in Russian or "
        f"any other language, even a single word. If the target is Tajik, use literary Tajik Cyrillic "
        "(тоҷикӣ), not Uzbek vocabulary or Uzbek sentence structure. This rule is more important than "
        f"the language of the topic.{tajik_rules}\n"
        "Return ONLY this JSON, no markdown fences, no commentary:\n"
        '{"needs_clarification": true|false, "question": "..." or null, "options": ["...", "...", "..."] or []}'
    )
    user_prompt = f'Target output language: {lang_name}. Topic: "{topic}"'
    try:
        result = await _call_ai(
            system_prompt, user_prompt, language,
            log_label=f"clarify-topic {material_type} topic={topic[:50]}",
            max_tokens=500,
            temperature=0.1,
        )
    except Exception:
        # Never let this optional pre-check block material generation — if
        # it fails for any reason, just skip straight to generating.
        return {"needs_clarification": False, "question": None, "options": []}
    options = result.get("options")
    options = [o for o in options if isinstance(o, str) and o.strip()] if isinstance(options, list) else []
    needs_clarification = bool(result.get("needs_clarification"))
    if needs_clarification and not options:
        logger.warning(f"clarify-topic topic={topic[:50]!r}: model said needs_clarification but sent no options, skipping")
    return {
        "needs_clarification": needs_clarification and bool(options),
        "question": result.get("question") or None,
        "options": options,
    }


_ALL_DEFAULT_TEMPLATES = {
    "konspekt": "nakscha",
    "prezentatsiya": "playful",
    "lektsiya": "planspekt",
}


def _default_template_for(material_type: str, subject: str | None,
                          grade: str | None) -> str | None:
    if material_type == "prezentatsiya":
        from app.subject_templates import resolve
        return resolve(subject, grade).id
    return _ALL_DEFAULT_TEMPLATES.get(material_type)


async def generate_all_materials(
    topic: str,
    subject: str,
    language: str,
    level: str,
    grade: str,
    slide_count: int = 10,
    question_count: int = 10,
    test_type: str | None = None,
    include_examples: bool = True,
    types: list[str] | None = None,
    source_text: str | None = None,
    teacher_context: str | None = None,
) -> dict:
    import asyncio

    if types is None:
        types = ["konspekt", "test", "prezentatsiya", "lektsiya"]

    results = {}
    errors = {}

    # Each generation burns 10-15k AI tokens. Four of them back-to-back (the
    # old behavior: Semaphore(1) only forced one-at-a-time, with no pacing)
    # can exceed the AI provider's tokens-per-minute cap mid-batch, failing
    # the later types with a 429 that the retry loop can't recover from
    # (see app/ai_service.py's _call_ai_inner - it retries the same key, it
    # doesn't wait out a per-minute window). Spacing calls out so the batch
    # spans more than a minute gives that window time to refill.
    PACE_SECONDS = 12

    for i, mt in enumerate(types):
        if i > 0:
            await asyncio.sleep(PACE_SECONDS)
        try:
            results[mt] = await generate_material(
                material_type=mt,
                topic=topic,
                subject=subject,
                language=language,
                level=level,
                grade=grade,
                slide_count=slide_count if mt == "prezentatsiya" else None,
                question_count=question_count if mt == "test" else None,
                test_type=test_type if mt == "test" else None,
                include_examples=include_examples,
                template=_default_template_for(mt, subject, grade),
                source_text=source_text,
                teacher_context=teacher_context,
            )
        except Exception as e:
            logger.warning(f"generate_all: {mt} FAILED: {e}")
            errors[mt] = str(e)

    out: dict = {mt: results.get(mt) for mt in types}
    out["errors"] = errors if errors else None
    return out


async def extract_topics_from_document(raw_text: str) -> str:
    trimmed = raw_text[:12000]
    system_prompt = (
        "You extract a clean lesson-topic list from messy raw text dumped from a school "
        "curriculum document. Return ONLY valid JSON. No filler commentary."
    )
    user_prompt = f"""Below is raw text extracted from a teacher's curriculum/lesson-plan document (paragraphs and table cells, in original order, with no formatting).

It mixes real lesson topics together with document noise: titles, teacher names, dates, subject/grade headers, table column labels (like "№", "Дата", "Соат"/"Часы"/hours), page numbers, signatures, etc.

Extract ONLY the actual lesson topic names, one per line, in the SAME language they appear in (do not translate), in their original order. Skip everything else — headers, metadata, hour/date columns, numbering, signatures. If the same topic appears to be split across multiple table cells (e.g. a number cell, a topic cell, an hours cell all as separate lines), merge them back into one clean topic line without the number/hours.

RAW TEXT:
---
{trimmed}
---

Return ONLY this JSON:
{{"topics": ["First topic", "Second topic"]}}"""

    content = await _call_ai(system_prompt, user_prompt, "Русский", log_label="extract-topics-from-docx")
    topics = content.get("topics")
    if not isinstance(topics, list) or not topics:
        raise ValueError("Topic extraction returned no topics")
    return "\n".join(str(t).strip() for t in topics if str(t).strip())


async def generate_roadmap(
    mode: str,
    grade: str,
    level: str,
    language: str,
    day_count: int,
    topic_list_text: str | None = None,
    goal_topic: str | None = None,
    subject: str | None = None,
) -> dict:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    user_prompt = _roadmap_prompt(mode, grade, level, language, day_count, topic_list_text, goal_topic, subject)
    system_prompt = (
        "You are an experienced curriculum designer building a multi-day teaching plan. "
        f"Return ONLY valid JSON, with every field written in {lang_name} (except \"subject\" if a fixed list was given). "
        "No filler commentary, meta-text, or apologies — structured output only."
    )
    content = await _call_ai(system_prompt, user_prompt, language, log_label=f"roadmap mode={mode} days={day_count}")
    topics = content.get("topics")
    if not isinstance(topics, list) or not topics:
        raise ValueError("Roadmap response missing a non-empty 'topics' list")
    if subject:
        content["subject"] = subject
    elif not content.get("subject") or content["subject"] not in _SUBJECT_KONSPEKT_PROMPTS:
        content["subject"] = next(iter(_SUBJECT_KONSPEKT_PROMPTS))
    return content



async def generate_quiz_set(
    topic: str,
    subject: str,
    level: str,
    grade: str,
    language: str,
    count: int,
) -> list[dict]:
    if language not in LANGUAGE_NAMES:
        raise ValueError(
            f"Unknown language {language!r} — expected one of {sorted(LANGUAGE_NAMES)}"
        )
    lang_name = LANGUAGE_NAMES[language]
    subject_hint = _SUBJECT_KONSPEKT_PROMPTS.get(subject, "")
    level_map = {
        "Лёгкий": "Beginner. Simple recall, clearly-wrong distractors, no trick questions.",
        "Средний": "Intermediate. Requires understanding, not just memorised facts.",
        "Сложный": "Advanced. Requires applying the concept, not just recalling it.",
    }
    level_text = level_map.get(level, level_map["Средний"])

    user_prompt = f"""Create exactly {count} multiple-choice questions about "{topic}" for grade {grade}, subject "{subject}".

Difficulty: {level_text}
{subject_hint}

Rules:
- Every question has EXACTLY 4 options.
- Exactly one option is correct; "correct_index" is its 0-based position.
- The three wrong options must be plausible for the grade level, never joke answers.
- "explanation" is one or two short sentences saying WHY the correct option is correct.
  Write it so a pupil who got the question wrong understands the reason, not just the fact.
- Vary which position holds the correct answer across the set.
- Every field must be written in {lang_name}.

Return ONLY valid JSON in exactly this shape:
{{
  "questions": [
    {{"question": "...", "options": ["...", "...", "...", "..."], "correct_index": 0, "explanation": "..."}}
  ]
}}"""

    system_prompt = (
        "You are an experienced teacher writing assessment questions. "
        f"Return ONLY valid JSON, with every field written in {lang_name}. "
        "No filler commentary, meta-text, or apologies — structured output only."
    )
    content = await _call_ai(
        system_prompt, user_prompt, language, log_label=f"quiz-set topic={topic[:50]} n={count}"
    )
    raw = content.get("questions")
    if not isinstance(raw, list) or not raw:
        raise ValueError("Quiz-set response missing a non-empty 'questions' list")

    cleaned: list[dict] = []
    for q in raw:
        if not isinstance(q, dict):
            continue
        text = q.get("question")
        options = q.get("options")
        idx = q.get("correct_index")
        if not text or not isinstance(options, list) or len(options) != 4:
            continue
        if not isinstance(idx, int) or not 0 <= idx < 4:
            continue
        cleaned.append({
            "question": str(text),
            "options": [str(o) for o in options],
            "correct_index": idx,
            "explanation": str(q.get("explanation") or ""),
        })
    if not cleaned:
        raise ValueError("Quiz-set response contained no usable questions")
    return cleaned
