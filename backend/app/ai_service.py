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

    "Таджикская литература": "Start with a poem or excerpt from a Tajik classic. CRITICAL RULES for academic accuracy: 1) For Rudakiy: He made significant CONTRIBUTIONS to qasida and ghazal development, but did NOT create or standardize them. Use 'contributed to development' NOT 'created' or 'standardized'. 2) Avoid claiming he 'organized language and rhythm' - instead say 'enriched the literary language and demonstrated its artistic possibilities'. 3) Birthplace: use 'traditionally attributed to' when discussing birthplace, as exact location is debated. 4) For literary influence: use 'influenced' or 'was part of the tradition of' NOT direct borrowing claims. 5) Distinguish between well-established facts and scholarly debates. 6) Use 'approximately' for uncertain dates. 7) Present Persian-Tajik civilizational heritage, not just Tajik-only claims. IMPORTANT: When writing in Tajik, MANDATORY vocabulary: шеър (not стихотворение), байт (not куплет), ғазал (not газель), қасида (not касыда), адабиёт (not литература), муаллиф (not автор), эҷодӣ (not произведение), достон (not поэма), ҳикоя (not рассказ), китоб (not книга), дарс (not урок), мактаб (not школа), синф (not класс), хонанда (not ученик), омӯзгор (not учитель), донишҷӯй (not студент), таҳлил (not анализ), муқоиса (not сравнение), хулоса (not вывод), намуна (not пример), савол (not вопрос), ҷавоб (not ответ), ҳақиқат (not правда), муҳаббат (not любовь), озодӣ (not свобода), адолат (not справедливость), меҳнат (not труд), дониш (not знание), шуҷоат (not храбрость), некӣ (not доброта), зебоӣ (not красота). Never use Russian words when Tajik equivalents exist.",

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
        "a concrete task on this exact topic: code to trace by hand and say what it prints, "
        "a number to convert between number systems, a value to compute from a truth table, "
        "an algorithm step to write out, a short program to fix"
    ),
    "Таджикский язык": (
        "a concrete language exercise on this exact rule: a sentence to analyse, words to sort "
        "into their parts of speech, a word to change form, a sentence to build from given words, "
        "a mistake to correct"
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

_REAL_IMAGE_SUBJECTS = {
    "Биология",
    "География",
    "История Таджикистана",
    "Всемирная история",
    "Таджикская литература",
    "Информатика",
}

_CODE_SUBJECTS = {"Информатика"}

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
        "images": _first_texts(content.get("lesson_image_queries"), 2, chars=60),
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
        if digest.get("images"):
            parts.append("illustrations asked for: " + " | ".join(digest["images"]))
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
        "  * Use different illustrations: both \"lesson_image_queries\" entries must differ from every one "
        "listed above and point at a different aspect of the topic.\n"
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
    source_text: str | None = None,
    previous_digests: list[dict] | None = None,
    variant_out: dict | None = None,
) -> str:
    level_map = {
        "Лёгкий": "Beginner. Very simple language, like talking to a friend. Avoid academic/technical jargon "
                  "entirely — if a term is truly unavoidable, define it in plain words the moment it's used.",
        "Средний": "Intermediate. Clear with real examples. Subject-specific terminology is fine but always "
                   "explained in context, never assumed.",
        "Сложный": "Advanced. Deeper but still practical and engaging. Technical vocabulary is fine, but still "
                   "explained — this is still the hardest version of what THIS grade can absorb, not "
                   "university-level material (see the grade rule below).",
    }
    level_text = level_map.get(level, level_map["Средний"])

    subject_hint = _SUBJECT_KONSPEKT_PROMPTS.get(subject, "")
    lang_name = LANGUAGE_NAMES.get(language, "English")

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
        optional_fields.append(
            '  "worked_examples": [{"problem": "one concrete exercise a pupil can actually be marked on, '
            'directly on this topic — with the actual sentence/words/code/values written out in it, never a '
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
            '  "concept_cards": [{"title": "Short name of one operation/term/rule", "tag": "notation, e.g. a symbol or the Python keyword (optional, empty string if none)", '
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
    if subject in _CODE_SUBJECTS:
        optional_fields.append(
            '  "code_blocks": [{"language": "python", "code": "...", "explanation": "..."}, '
            '{"language": "cpp", "code": "the SAME algorithm as above, in this different language", "explanation": "..."}, '
            '{"language": "java", "code": "the SAME algorithm again, in this different language", "explanation": "..."}] '
            '— see the code_blocks rule below: for a language-agnostic topic (an algorithm/general concept) this '
            'MUST be 3 entries in 3 different languages like the example shown here, not 1,'
        )
    if include_homework:
        optional_fields.append('  "homework": ["Task 1: detailed assignment", "Task 2: detailed exercise", "Task 3: detailed project"],')
    if include_assessment:
        optional_fields.append('  "assessment": "3-4 sentence assessment criteria."')
    optional_json = "\n" + "\n".join(optional_fields) if optional_fields else ""
    if optional_json and not include_assessment:
        optional_json = optional_json.rstrip(",")

    real_image_json = (
        '\n  "real_image_query": "Precise English search term for a real photo/logo/diagram, or empty string — see rules above",'
        '\n  "real_image_style": "\\"logo\\", \\"cutout\\", or \\"diagram\\", or empty string if real_image_query is empty",'
        if subject in _REAL_IMAGE_SUBJECTS
        else ""
    )

    extra_rules = []
    extra_rules.append(
        "- DEPTH — the #1 way a konspekt fails: content so generic it could be pasted into a lesson on almost any "
        "other topic unchanged. Before finalizing each sentence, check whether it names something specific to "
        f"\"{topic}\" — a real number, date, name, formula, mechanism, cause, or concrete example — versus a vague "
        "generality like \"this plays an important role\", \"there are many factors\", \"it has several uses\" left "
        "unspecified. Cut or rewrite anything that fails that check. \"main_content\" specifically must explain HOW "
        "and WHY, not just restate WHAT in different words paragraph to paragraph — trace a mechanism, a cause-"
        "and-effect chain, or a worked-through reasoning process, the way a teacher would actually walk students "
        "through the idea rather than list facts about it. Every \"key_concepts\"/\"key_terms\" entry must contain "
        "at least one concrete, checkable detail (not just a one-line dictionary definition), and every "
        "\"real_life_examples\" entry must name a specific, real scenario (a real place/product/event/number) "
        "rather than a generic \"for example, in daily life...\" placeholder. When two draft sentences say "
        "essentially the same generic thing, keep the more specific one and cut the other rather than keeping both."
    )
    extra_rules.append(
        "- AN EXAMPLE IN EVERY LIST ITEM — this is a hard requirement, not a nice-to-have: EACH AND EVERY entry of "
        "\"key_concepts\" and \"key_terms\" must end with its own short, concrete example of that specific concept/"
        f"term, introduced by the lesson language's word for \"For example\". The example must be simple enough for a grade {grade} "
        "student to follow immediately — a tiny concrete case (a small number, a short sentence, one named thing), "
        "NOT another abstract restatement of the definition and NOT a long scenario. An entry that only defines "
        "without showing one is incomplete: go back and add the example. Give a DIFFERENT example in each entry — "
        "never reuse the same illustration twice in the list."
    )
    if subject in _CODE_SUBJECTS:
        extra_rules.append(
            "- \"code_blocks\" LANGUAGE COUNT — read this carefully, it is a hard requirement, not a suggestion:\n"
            "  STEP 1: is this topic tied to ONE specific language's own syntax (e.g. \"Python lists\", \"pointers in "
            "C++\", \"Java interfaces\")? If yes: write ONLY that 1 language, 1 code_blocks entry. Stop here.\n"
            "  STEP 2: otherwise, is this topic an ALGORITHM or a general programming concept that isn't tied to one "
            "language (sorting, searching, recursion, loops, data structures, complexity, etc.)? If yes: you MUST "
            "return EXACTLY 3 code_blocks entries — the literal SAME algorithm, implemented natively/idiomatically in "
            "3 DIFFERENT languages (choose 3 different ones each time from: python, cpp, java, javascript, csharp — "
            "do not always pick the same 3). Returning only 1 language here is WRONG even if that 1 example is "
            "correct — a single-language answer fails this requirement. Do not skip this or default back to Python "
            "alone out of habit.\n"
            "  STEP 3: topic has no code to show at all (hardware, networking, abstract theory)? Return an empty list.\n"
            "  Every snippet must be real, syntactically valid code a compiler for that language would accept — "
            "never a fabricated API/library."
        )
    if subject in _FORMULA_SUBJECTS:
        extra_rules.append(
            "- \"formulas\": give 3-5 formulas central to this specific topic (not generic filler). "
            "Write the \"formula\" field compactly with plain-text/unicode math notation (^, √, Δ, π, °, "
            "fractions as a/b) and no markdown — that field is the fallback for viewers that cannot typeset "
            "mathematics. The LaTeX goes in the separate \"latex\" field (see the notation rule below); do not "
            "put LaTeX in \"formula\". If the topic truly has no formulas, return an empty list."
        )
    if subject in _FORMULA_SUBJECTS or subject in _WORKED_EXAMPLE_SUBJECTS:
        extra_rules.append(
            "- MATHEMATICAL NOTATION. The export typesets mathematics properly — stacked fractions, real "
            "radicals, raised exponents — but only from LaTeX. Give it LaTeX and it prints like a textbook; "
            "give it plain text and it prints like a keyboard.\n"
            "  * Every \"formulas\" entry needs a \"latex\" field holding that same formula in LaTeX. Keep the "
            "\"formula\" field too, in the readable plain form, for viewers that show no mathematics.\n"
            "  * Wrap EVERY mathematical expression in dollar signs, ANYWHERE in the konspekt — worked "
            "examples, key concepts, key terms, main_content, the lesson steps, real-life examples, "
            "important notes, table cells. \"Ҳисоб кунед: $x^2 + 5x + 6 = 0$\", \"дар ин ҷо $x$ "
            "номаълум аст\", \"$6^2 = 36$\". Even a single letter standing for a variable, and even a "
            "bare power. Ordinary words stay outside the dollars.\n"
            "  * This includes a negative number by itself: write \"$-100$ сомонӣ\", never "
            "\"\\text{-100} сомонӣ\" — a \\command{...} written OUTSIDE dollar signs is not LaTeX to the "
            "export, it is literal backslash-and-braces text that prints on the page exactly as typed. "
            "\\text{}, \\frac{}{}, ^{}, _{} and every other LaTeX command belong ONLY inside a $...$ pair, "
            "with no exception.\n"
            "  * EVERY fraction is \\frac{}{} — never a slash. Write \"x = \\frac{20}{4} = 5\", not "
            "\"x = 20/4 = 5\"; \"\\frac{-10}{5}\", not \"-10/5\"; \"\\frac{b}{a}\", not \"b/a\". This applies "
            "to the solution steps in worked_examples as much as to the formulas. A slash stays a slash only "
            "in units of measurement (м/с, км/ч).\n"
            "  * Use real LaTeX: ^{} for powers, _{} for indices, "
            "\\sqrt{}, \\sqrt[3]{}, \\pm, \\cdot, \\times, \\le, \\ge, \\ne, \\approx, \\pi, "
            "\\alpha, \\Delta, \\sum_{i=1}^{n}, \\int_{a}^{b}, and \\left( \\right) for brackets that "
            "must grow around a fraction.\n"
            "  * The ^{} braces hold ONLY the exponent itself, never a variable multiplied after it. A "
            "confirmed real mistake: the cube-of-a-sum expansion's middle term, meant to be \"three times "
            "a-squared times b\", was written \"3a^{2b}\" — that says \"3 times a to the power of (2b)\", a "
            "completely different (and wrong) quantity. The correct form is \"3a^{2}b\" (or "
            "\"3a^{2}\\cdot b\"): close the ^{} braces right after the exponent digit, THEN write the next "
            "factor outside them. This applies everywhere a power is immediately followed by another "
            "variable — check every ^{...} you write for a stray trailing letter that doesn't belong to the "
            "exponent before finalizing.\n"
            "  * The mathematics itself must not change — LaTeX is how it is written, not what it says."
        )
    if subject in _WORKED_EXAMPLE_SUBJECTS:
        extra_rules.append(
            "- \"worked_examples\" — teachers specifically asked for this, treat it as one of the most important "
            "fields in a math konspekt: give MANY fully worked example problems ('misol') — 16-20 of them, and "
            "treat 16 as a hard floor, not a target to undershoot; a list of 3-4 does not satisfy this rule. "
            "Real teacher-written konspekts for this subject are mostly examples — pages of them — with the "
            "explanation being the short part; match that balance. "
            "Each one directly applies THIS topic's technique/formula to real numbers — an actual solvable "
            "problem (an equation to solve, an expression to simplify, a shape to compute), never a real-life "
            "story (that's what \"real_life_examples\" is for instead). Each \"solution\" must show the complete "
            "step-by-step working, not just the final answer.\n"
            "  SIMPLICITY IS THE POINT — teachers were explicit about this: these examples exist so a child in "
            f"grade {grade} actually UNDERSTANDS the method, not to show off hard problems. Start from the "
            "easiest possible case of this topic and rise only gently; even the last example should still be "
            "solvable by a student who just met this material. Prefer small whole numbers that divide evenly "
            "(2, 3, 5, 10, 12...) over awkward decimals/fractions, keep each problem to ONE step of new "
            "difficulty at a time, and write each solution step in plain words a child can follow (say what you "
            "are doing and why, not just the algebra line). If an example needs a long chain of tricky "
            "arithmetic to finish, it is the wrong example — replace it with a simpler one.\n"
            "  VARY THE FORM across the list. Sixteen exercises of the identical shape (all \"compute this\") "
            "drill one keystroke and teach one skill — a real teacher's konspekt mixes them. Rotate between: "
            "direct computation, solve for the unknown, simplify/transform an expression, compare two values, "
            "fill in a table of values, read or plot a point on the graph, and a short task stated in words that "
            "the pupil must turn into the calculation. Also cover EVERY sub-skill the topic names — if the topic "
            "mentions a graph, a chart, or a property, some of the examples must actually be about that and not "
            "only about the arithmetic.\n"
            "  Every example must be mathematically correct — double-check the arithmetic before finalizing, an "
            "example with a wrong answer is worse than no example. NEVER alter a number mid-solution to force a "
            "clean-looking answer — a confirmed real mistake: an equation \"11x - 7 = 36\" was correctly reduced "
            "to \"11x = 43\", then the solution silently changed it to \"11x = 44\" with the excuse \"swapping the "
            "numbers for divisibility\" so x would come out to a whole number 4 — but 4 does NOT satisfy the "
            "original equation (11·4 - 7 = 37, not 36). If the numbers you chose for a problem don't divide "
            "evenly, either pick different numbers before writing the solution, or show the true fractional/"
            "decimal answer honestly — inventing a fake intermediate step to manufacture a clean result is a "
            "worse error than an ugly fraction, because it teaches the pupil a nonexistent shortcut."
        )
    if subject in _EXERCISE_SUBJECTS:
        extra_rules.append(
            "- \"worked_examples\" — treat this as one of the most important fields in the konspekt: give MANY "
            "fully worked exercises ('misol') — 12-16 of them, and treat 12 as a hard floor, not a target to "
            "undershoot. Each is "
            + _EXERCISE_KIND.get(subject, "a concrete task on this exact topic")
            + ". The exercise MUST contain the actual material to work on written out inside it — the sentence, "
            "the words, the code, the numbers. \"Analyse a sentence\" is not an exercise; \"Analyse: 'Мактаби мо "
            "калон ва зебост' — find the noun and the adjective\" is. Each \"solution\" gives the full worked "
            "answer with the reasoning, not just a verdict.\n"
            f"  Keep them at grade {grade} level and order them from the easiest case to the hardest, one new "
            "step of difficulty at a time — the last one should still be within reach of a pupil who has just "
            "met this material. Vary the FORM across the list (do not give twelve of the same shape of task), "
            "and make sure every answer is actually correct."
        )
    if subject in _WORKED_EXAMPLE_SUBJECTS or subject in _EXERCISE_SUBJECTS:
        extra_rules.append(
            "- \"practice_problems\" — 6-10 problems for the PUPIL to solve themselves in class, not you. Same "
            "topic/technique/difficulty range as worked_examples, but every problem must use genuinely different "
            "numbers/wording/scenario from every worked_examples entry — copying one with the numbers swapped is "
            "not acceptable, a pupil who just watched that exact problem solved isn't practising anything new. "
            "\"answer\" is ONLY the bare final result (a number, an expression, a short phrase) — never a solution, "
            "never a hint, never the word \"see above\". If you cannot write genuinely correct answers for every "
            "single one, write fewer problems rather than guess."
        )
    if subject in _CONCEPT_CARD_SUBJECTS:
        extra_rules.append(
            "- \"concept_cards\": the main visual centerpiece of this konspekt — cover the topic thoroughly with 6-10 cards "
            "(not just a token few), e.g. every distinct logical operation/law, every distinct rule/term/classification that "
            "applies. Each \"table\" is a small grid (first row = column headers, 2-4 columns, 2-4 data rows) — omit \"table\" "
            "and use nothing instead if a given card isn't naturally a table (a short rule/law can just use \"note\" alone). "
            "Never invent incorrect logic/values in a truth table — they must be actually correct. Only return fewer cards "
            "(or an empty list) if this topic genuinely has that little tabular content to cover."
        )
    if subject == "География":
        extra_rules.append(
            "- \"map_locations\": name 1-3 REAL places (their actual, correct names — never invent a place) that a map "
            "reader would want to see for this topic. If the topic has no specific geographic location, return an empty list."
        )
    subject_visual_pool = _SUBJECT_VISUAL_PREFERENCE.get(subject)
    if subject_visual_pool:
        forced_type = random.choice(subject_visual_pool)
        remaining_pool = [t for t in _VISUAL_BLOCK_TYPES if t != forced_type]
        required_types = [forced_type] + random.sample(remaining_pool, 2)
    else:
        required_types = random.sample(_VISUAL_BLOCK_TYPES, 3)
    extra_rules.append(
        "- \"visual_blocks\": include EXACTLY 5 entries. Not 2, not 3 — five, every time. Treat this as a fixed "
        "count you must reach, not a maximum to stay under: the export lays these out across the whole document, "
        "so a konspekt that returns two leaves whole pages with nothing but paragraphs on them. Only go below 5 "
        "if this topic truly cannot support a fifth distinct, genuinely useful visualization, and even then never "
        "fewer than 4. Each must earn its place — do not repeat the same data in two blocks or invent a filler "
        "grid; find five DIFFERENT angles on the topic instead (a classification, a comparison, a sequence of "
        "steps, a set of worked values, a before/after).\n"
        "  All five must be DIFFERENT \"type\" values — never two tables or two processes in one "
        "konspekt. With five entries and five available types that means using each type once.\n"
        "  Each must carry real substance, not a token shell: a table/comparison needs at least 3 data "
        "rows, a process/flowchart at least 3 steps, a timeline at least 3 events. A two-row table teaches "
        "nothing and takes the slot a real one could have used. "
        f"Prefer these types where they fit: {', '.join(f'\"{t}\"' for t in required_types)}; swap in another "
        "type instead if one truly doesn't suit the topic. Prefer \"timeline\", \"flowchart\"/\"process\" and "
        "over \"table\"/\"comparison\" when either would fit, but use table/comparison freely "
        "where they are the better fit. Vary both \"type\" and \"position_after\" across entries — never anchor "
        "two blocks to the same section. Every entry MUST also carry a \"description\": 1-2 sentences printed UNDER the visual, saying what it shows and what the reader should notice in it — a table with no reading underneath leaves the pupil to guess why it is there. If a fact or sequence appears in a block, do not also re-explain it in "
        "full in the prose sections — cover it once, wherever it teaches best. Type choice: \"table\" for "
        "tabular facts, \"timeline\" for dated events, \"flowchart\"/\"process\" for ordered steps or "
        "cause→effect, \"comparison\" for contrasting 2+ things across shared criteria. Each \"data\" shape:\n"
        "  table: {\"headers\": [\"col1\", \"col2\"], \"rows\": [[\"...\", \"...\"]]}\n"
        "  timeline: {\"events\": [{\"label\": \"...\", \"date\": \"...\", \"description\": \"...\"}]}\n"
        "  flowchart/process: {\"steps\": [{\"title\": \"...\", \"description\": \"...\"}]}\n"
        "  comparison: {\"criteria\": [\"...\"], \"items\": [{\"name\": \"...\", \"values\": [\"one per criterion, same order\"]}]}\n"
        "\"position_after\" must be one of: \"key_concepts\", \"main_content\", \"real_life_examples\", "
        "\"tools\", \"pair_work\", \"consolidation\", \"visual_aid\", \"lesson_program\" — pick whichever fits "
        "the block best rather than defaulting to \"main_content\". Never use \"competencies\"/\"objectives\" "
        "(nothing taught yet) or \"summary\"/\"homework\"/\"assessment\" (reads as an afterthought)."
    )
    if subject in _FIGURE_SHAPES:
        catalog = "; ".join(f"{name} {hint}" for name, hint in _FIGURE_SHAPES[subject])
        extra_rules.append(
            "- \"figures\": 1-2 entries. This is an ACTUAL DRAWING of the thing the lesson is about, drawn by "
            "the export the way a teacher draws it on the blackboard — a cube with dashed hidden edges for a "
            "volume lesson, a parabola on real axes for a quadratic lesson, a Bohr shell model for an atom "
            "lesson. If this topic names or works with a concrete shape, body, graph, circuit or molecule, you "
            "MUST include it; that drawing is the single most useful thing on the page for this subject. "
            "\"shape\" MUST be copied exactly from this list and nothing else — an id that is not on the list "
            "draws nothing at all:\n"
            f"  {catalog}\n"
            "The bracketed list after each id is what \"values\" means for that shape, in that order: short "
            "label strings printed on the drawing (\"5 см\", \"a\", \"h\"), NOT sentences. For plot_* shapes "
            "\"values\" are NUMBERS (the coefficients), e.g. plot_parabola with [\"1\",\"0\",\"-4\"] draws "
            "y = x² - 4. Vertex letters (A, B, C, A₁...) are added automatically — never put them in \"values\". "
            "Pick values that match the worked examples in this konspekt so the drawing illustrates a problem "
            "the pupil is actually solving. Return [] only if the topic truly centres on no drawable object.\n"
            "  \"coordinate_plane\" draws ONLY bare, unlabeled x/y axes — nothing plotted on them, no point, no "
            "line, no curve, no marked root. A confirmed real mistake: a topic about an equation's root picked "
            "\"coordinate_plane\" and captioned it \"shows the equation's root on the number line\" — the export "
            "then printed that caption over empty axes with nothing marked, since the shape never draws a point. "
            "Only caption \"coordinate_plane\" as a plain, generic coordinate system (e.g. \"the coordinate "
            "plane used to plot functions\") — if you actually need a specific point, line or curve shown, use "
            "one of the \"plot_*\" shapes instead (they take real numeric coefficients and draw the actual "
            "graph), or leave the figure out entirely."
        )
    extra_rules.append(
        "- \"important_notes\": 0-2 short, genuinely important warnings/caveats/highlights (a common misconception, a "
        "safety note, an exception to the rule just taught). Return an empty list if this topic has nothing that "
        "warrants one — don't invent a filler note. The export already prints a bold \"Диққат.\" label in front of "
        "every item automatically — write ONLY the note's own content, with NO leading label of your own "
        "(\"Диққат:\", \"Ёд доред:\", \"Внимание:\" or similar), or it prints twice, e.g. \"Диққат. Диққат: ...\"."
    )
    if include_homework:
        extra_rules.append(
            "- \"homework\": never invent a specific textbook page number, exercise number, or edition detail "
            "(e.g. \"саҳифаи 72\") — you have no way of knowing which textbook this teacher actually uses, so a "
            "made-up page number just misleads them. Describe the task itself in full instead (the actual "
            "problem, or precisely what to produce), never \"see page N\"."
        )
    if subject in _WORKED_EXAMPLE_SUBJECTS:
        extra_rules.append(
            "- \"real_life_examples\": if a scenario names its unknown with a letter (e.g. \"z\"), the equation "
            "you write for it must use that SAME letter — a confirmed real mistake named the unknown \"z\" in "
            "the story, then wrote the equation with \"x\" instead. Also make sure the unknown is actually "
            "unknown: a confirmed real mistake built a scenario where the \"unknown\" quantity was already "
            "stated as a known number earlier in the very same sentence, leaving nothing to actually solve for."
        )
    extra_rules.append(
        "- \"lesson_images\": EXACTLY 2 entries, each an object with THREE fields — \"query\", \"position_after\" "
        "and \"explanation\".\n"
        "  * \"query\": a precise ENGLISH search phrase for Wikimedia Commons naming a teaching illustration (a "
        "labelled diagram, a scheme, a graph, a geometric construction, a scientific figure) that actually "
        "explains part of THIS specific topic — never a decorative or merely related picture, and never the same "
        "idea twice. Good: [\"Pythagorean theorem proof diagram\", \"right triangle labeled sides\"] for the "
        "Pythagorean theorem; [\"water cycle diagram\", \"cloud formation diagram\"] for precipitation; "
        "[\"parabola graph vertex\", \"quadratic function coefficients diagram\"] for quadratic functions. Bad: a "
        "generic photo of a classroom, a flag for an unrelated topic. NEVER reach for an illustration from a "
        "DIFFERENT field as a METAPHOR or COMPARISON for this topic, even one you plan to explain in the caption — "
        "the pupil just sees a snail, a waveform, a random molecule with no connection to the lesson on the page "
        "in front of them. Confirmed mistakes to never repeat: a snail-anatomy diagram for a lesson on sentence "
        "structure (\"compare its complexity to a complex sentence\"), a signal-processing waveform for a lesson "
        "on simple/complex chemical substances (\"compare a simple/complex signal\"); a lesson on EQUATIONS "
        "queried \"algebraic notation diagram\" and Commons returned a labelled algebraic EXPRESSION (terms/"
        "coefficients of \"3x² − 2xy + c\", no \"=\" sign anywhere) captioned as showing \"the structure of an "
        "equation\" — an expression is explicitly NOT an equation (this konspekt's own \"ифода\"/\"муодила\" "
        "vocabulary says so), so the picture contradicted the lesson it was supposed to illustrate. If the topic "
        "is specifically about equations, the query must target an image that visibly contains an \"=\" sign "
        "(e.g. \"algebraic equation solving diagram\", \"linear equation labeled\") — never a bare-expression or "
        "generic \"algebra notation\" image. Every \"query\" must name "
        "the actual real-world thing THIS lesson is about (its formula, its object, its named process) — never "
        "an analogy, comparison, or illustration of a DIFFERENT subject's concept, however cleverly it connects. "
        "Add the word \"diagram\" or \"scheme\" when "
        "the topic is abstract (a rule, a process, an equation) so the search finds an illustration of it rather "
        "than a photo. Keep the phrase SHORT — 2 to 4 words carrying the subject; a long phrase matches nothing "
        "on Commons.\n"
        "  * \"position_after\": WHICH section of THIS konspekt the picture explains — one of \"key_concepts\", "
        "\"main_content\", \"worked_examples\", \"real_life_examples\", \"consolidation\". The picture will be "
        "printed directly under that section's text, so choose the section whose sentences the picture actually "
        "illustrates. Think about what you wrote in each section and put the diagram where a pupil reading that "
        "paragraph would need to look at it. The two entries must NOT both point at the same section — they "
        "illustrate two different parts of the lesson.\n"
        "  * \"explanation\": ONE short sentence, in the lesson's own language, telling the pupil what to see in "
        "the picture and what it proves about the text above it — e.g. \"Дар расм бинед, ки чӣ тавр квадратҳои "
        "катетҳо ба квадрати гипотенуза баробаранд\". Not a title, not a caption repeating the file name: an "
        "instruction for reading the picture. This is what turns the illustration into part of the explanation "
        "instead of decoration.\n"
        "  Always return exactly 2 entries — never 0, 1, or more than 2."
    )
    if subject in _REAL_IMAGE_SUBJECTS:
        extra_rules.append(
            "- \"real_image_query\"/\"real_image_style\": use ONLY when this exact topic centers on ONE specific, "
            "concrete, recognizable real-world subject that a real photo/logo/diagram actually exists for — a named "
            "software/OS/company/product/brand (e.g. \"Windows\", \"Python\", \"Microsoft\"), or a specific animal/plant "
            "species, or a real historical figure/artifact/landmark, or (biology specifically) an animal/plant/human "
            "organ system whose INTERNAL structure/anatomy is the actual subject of the lesson. Write real_image_query "
            "as a precise ENGLISH search term for it (e.g. \"Windows 11 logo\", \"Bengal tiger\", \"Eiffel Tower\", "
            "\"Frog internal anatomy\") — never a vague/generic phrase. Set real_image_style to \"logo\" when the "
            "subject is a brand/software/product/flag/symbol (rendered as a clean mark, no background removal needed), "
            "\"cutout\" when it's a living organism or physical object best shown whole as a background-removed photo, "
            "or \"diagram\" when the lesson is specifically about that organism's INTERNAL structure/anatomy/organs "
            "(e.g. topic is \"ichki tuzilishi\"/\"внутреннее строение\" of a frog/fish/human — write the query as "
            "\"<organism> internal anatomy\" or \"<organism> anatomy diagram\" so the fetched image is the labeled "
            "cutaway/anatomy illustration itself, not a plain photo of the whole animal). Leave BOTH as empty strings "
            "for the many topics with no single concrete photographable/diagrammable subject (grammar rules, math "
            "procedures, abstract concepts, generic activities) — do not force a tenuous or symbolic connection just to "
            "fill this field."
        )
    angle, shape = _pick_variant(previous_digests or [])
    if variant_out is not None:
        variant_out["angle"] = angle[:80]
        variant_out["shape"] = shape[:80]
    extra_rules.append(
        f"- LESSON SHAPE for this generation — this decides how the lesson is BUILT, not just how it opens, and "
        f"it outranks habit: {shape} Every section has to follow from it: the order ideas are introduced in, what "
        "the worked examples look like, what the pair/group tasks ask for, and what the homework practises. Two "
        "konspekts on one topic built on two different shapes are two different lessons; two built on the same "
        "shape are the same lesson twice."
    )
    variation_rule = _variation_rule(previous_digests or [], angle, shape)
    if variation_rule:
        extra_rules.append(variation_rule)
    extra_rules.append(
        f"- Framing/angle for this generation: {angle} Let this shape which real-world examples you reach for "
        "and how main_content/real_life_examples/lesson_program/subtitle are framed — but never at the expense of "
        "accuracy: if this angle doesn't genuinely fit a given section, quietly fall back to the clearest ordinary "
        "framing for that section instead of forcing it. \"subtitle\" specifically must NOT be a generic one-liner "
        "that would fit this topic regardless of angle (confirmed live: without this, subtitle converges on the "
        "same safest phrasing across regenerations even when the rest of the angle correctly varies) — it should "
        "read as written under today's angle specifically."
    )
    extra_rules.append(
        f"- Vocabulary and depth must fit grade {grade} SPECIFICALLY, not just the difficulty label above — a term "
        "routine at university level (formal proofs, unexplained research-paper phrasing, domain jargon no school "
        f"curriculum at this grade would have covered) has no place here regardless of difficulty; \"{level}\" for "
        f"grade {grade} means the hardest version of what a student at THAT grade can actually absorb, never "
        "graduate-level material."
    )
    extra_rules.append(
        "- \"quick_check\": 2-4 short comprehension questions a teacher can ask right after teaching this content, "
        "each with its own short answer — a fast way to confirm the class understood before moving on. Every "
        "question must be answerable directly from what's already in this konspekt (main_content/key_concepts), "
        "never something requiring outside knowledge. Return an empty list only if this topic genuinely has "
        "nothing checkable this way (very rare)."
    )
    extra_rules.append(
        "- \"main_content\" MUST be flowing prose — real sentences joined into paragraphs, never a numbered/"
        "bulleted list of facts dressed up as paragraphs. If you catch yourself about to write \"1. ... 2. ... "
        "3. ...\" inside main_content, rewrite it as connected sentences instead — a wall of short numbered "
        "fragments reads as a raw AI output dump, not an explanation a teacher would actually read aloud in class."
    )
    extra_rules.append(
        "- \"group_work\": exactly 3 tasks, one per group, split across the class — this is DIFFERENT from "
        "pair_work above (a whole-class activity) and consolidation (a wrap-up). Each of the 3 tasks must target a "
        "DIFFERENT key term/concept from this lesson (e.g. from key_concepts/key_terms) — never give all three "
        "groups the same or near-identical task. A real classroom pattern to match: one group finds/explains real-"
        "world examples of one concept, another solves a short concrete problem using a second concept, a third "
        "solves a short problem using a third concept. Each task string should read as a complete instruction a "
        "teacher could read aloud to that group as-is (don't include the \"Group N\" label itself — the app adds "
        "that automatically from the array position)."
    )

    extra_rules_text = ("\n" + "\n".join(extra_rules)) if extra_rules else ""

    source_block = ""
    if source_text:
        source_block = f"""

SOURCE MATERIAL (primary source — this konspekt must be built from this text, not from general knowledge; follow it
as CLOSELY AS POSSIBLE, this is not optional background reading):
\"\"\"
{source_text}
\"\"\"
Use this source as the primary basis for EVERY section, not just main_content — key_concepts, key_terms, formulas,
worked_examples/practice_problems, real_life_examples, all of it: pull the actual definitions, the actual worked
problems, the actual terminology and the actual examples this source itself uses, in the same order the source
presents them where that's reasonable, rather than reaching for your own equivalents. Preserve its terms, facts,
definitions, and examples as faithfully as possible while still restructuring them into the concise konspekt format
below (don't just copy paragraphs verbatim — condense and organize them into the requested sections, but the
SUBSTANCE must be the source's own, not a paraphrase from memory of "a similar textbook"). Do NOT invent facts that
contradict or aren't supported by the source. Only if the source genuinely has NO material at all for a required
section (not merely "less than you'd prefer") may you carefully supplement it from your own general knowledge — when
you do, keep that supplemented content clearly factual and uncontroversial (no speculation), since it isn't
source-verified, and keep it to the minimum needed to fill the gap.
If this text turns out to be about a DIFFERENT topic than "{topic}" entirely — not just thin on detail, but a
genuinely different subject (e.g. the requested topic is "{topic}" but this text is actually about something
else) — IGNORE this source completely and build the konspekt purely from your own knowledge of "{topic}" instead.
The topic given below always wins over a mismatched source; never silently write about whatever the source happens
to cover instead of the requested topic."""

    return f"""Create a comprehensive lesson plan (konspekt) about "{topic}" for grade {grade}, subject "{subject}".

Subject style: {subject_hint}
Difficulty: {level_text}
CRITICAL: Write ALL content in {lang_name} language. Return ONLY valid JSON, nothing else.{source_block}

RULES:
- "competencies" and "objectives" must be SHORT — a single concise phrase or sentence each (max ~12 words), like real lesson-plan bullet points, NOT a paragraph. Everything else should still be DETAILED: 3-5 sentences per text field, 3-5 items per list, with real facts, examples, and explanations.
- Every "lesson_images" query names a diagram of "{topic}" ITSELF. Not the
  subject in general, not a neighboring concept a student might meet in the
  same course — "{topic}" specifically. Measured live: a лексия titled "Реша
  ва вазифаҳои он" (root systems) once asked for diagrams of "human
  circulatory system" and "savanna food web" — real diagrams, just not of
  anything in this lesson, because both are things a biology course also
  covers. If you cannot think of a diagram that shows "{topic}" itself,
  leave "lesson_images" empty rather than reaching for whatever else the
  subject brings to mind.
- NEVER mix languages
- Return ONLY the fields listed below — do not add any others.{extra_rules_text}

RETURN THIS JSON:
{{
  "title": "Title about {topic}",
  "subtitle": "One-line catchy description written from THIS generation's angle/framing above, not a generic one",
  "duration": "45 minutes",
  "competencies": ["Short skill phrase 1 (max ~12 words)", "Short skill phrase 2", "Short skill phrase 3"],
  "objectives": ["Short goal phrase 1 (max ~12 words)", "Short goal phrase 2", "Short goal phrase 3", "Short goal phrase 4"],
  "key_concepts": ["Concept 1: explanation + a short simple example of it", "Concept 2: explanation + a short simple example", "Concept 3: explanation + a short simple example", "Concept 4: explanation + a short simple example", "Concept 5: explanation + a short simple example"],
  "key_terms": ["Term 1: definition and example", "Term 2: definition and example", "Term 3: definition and example", "Term 4: definition and example"],
  "real_life_examples": ["Example 1: detailed scenario", "Example 2: detailed scenario", "Example 3: practical use case"],
  "lesson_program": "4-5 sentence description of lesson flow.",
  "tools": ["Tool 1: why needed", "Tool 2: how used", "Tool 3"],
  "main_content": "3-4 detailed paragraphs each 4-5 sentences explaining {topic} with facts and examples.",
  "visual_blocks": [{{"type": "table|timeline|flowchart|process|comparison", "title": "short label", "description": "1-2 sentences under the visual explaining what it shows and what to notice", "position_after": "a section key above, e.g. main_content", "data": {{"...": "shape depends on type, see rules above"}}}}],
  "pair_work": "3-4 sentence pair activity with instructions and expected outcomes.",
  "consolidation": "3-4 sentence consolidation activity with specific tasks.",
  "group_work": ["Task for Group 1: find/explain real examples of one key term/concept from this lesson", "Task for Group 2: solve a short problem about a DIFFERENT key term/concept", "Task for Group 3: solve a short problem about a THIRD key term/concept"],
  "visual_aid": "3-4 sentence description of a visual aid and how to use it.",
  "important_notes": ["A short, genuinely important warning/caveat/highlight — empty list if none apply"],
  "quick_check": [{{"question": "Short comprehension question answerable from this konspekt", "answer": "Short answer"}}],
  "lesson_images": [{{"query": "Short English Commons search phrase for a diagram of {topic} ITSELF, not a broader or merely-related concept from the same subject", "position_after": "the section key this picture explains", "explanation": "One sentence telling the pupil what to see in it"}}, {{"query": "...still {topic} itself, a DIFFERENT aspect of it", "position_after": "a DIFFERENT section key", "explanation": "..."}}],{real_image_json}
  "summary": "4-5 sentence summary covering all key points"{"," if optional_json else ""}{optional_json}
}}"""


def _lecture_prompt(
    topic: str,
    subject: str,
    level: str,
    grade: str,
    language: str = "English",
    source_text: str | None = None,
) -> str:
    level_map = {
        "Лёгкий": "Beginner. Very simple language, like talking to a friend. Avoid academic/technical jargon "
                  "entirely — if a term is truly unavoidable, define it in plain words the moment it's used.",
        "Средний": "Intermediate. Clear with real examples. Subject-specific terminology is fine but always "
                   "explained in context, never assumed.",
        "Сложный": "Advanced. Deeper but still practical and engaging. Technical vocabulary is fine, but still "
                   "explained — this is still the hardest version of what THIS grade can absorb, not "
                   "university-level material (see the grade rule below).",
    }
    level_text = level_map.get(level, level_map["Средний"])
    subject_hint = _SUBJECT_KONSPEKT_PROMPTS.get(subject, "")
    lang_name = LANGUAGE_NAMES.get(language, "English")

    optional_fields = []
    if subject in _FORMULA_SUBJECTS:
        optional_fields.append(
            '  "formulas": [{"formula": "compact formula in plain-text/unicode math notation, '
            'e.g. x^2, √(x), Δ, π, 45°, a/b", "explanation": "1-2 sentence plain-language '
            'explanation of what it means and when to use it"}],'
        )
    if subject in _CONCEPT_CARD_SUBJECTS:
        optional_fields.append(
            '  "concept_cards": [{"title": "Short name of one operation/term/rule", "tag": "notation, e.g. a symbol or the Python keyword (optional, empty string if none)", '
            '"table": [["col header 1", "col header 2"], ["row1val1", "row1val2"], ["row2val1", "row2val2"]], '
            '"note": "1 short sentence explaining it"}],'
        )
    if subject == "География":
        optional_fields.append(
            '  "map_locations": ["Specific, real, geocodable place name — a city, country, region, '
            'mountain range, river, or sea, written in English so it geocodes reliably regardless of the lesson language"],'
        )
    if subject in _CODE_SUBJECTS:
        optional_fields.append(
            '  "code_blocks": [{"language": "python", "code": "...", "explanation": "..."}, '
            '{"language": "cpp", "code": "the SAME algorithm as above, in this different language", "explanation": "..."}, '
            '{"language": "java", "code": "the SAME algorithm again, in this different language", "explanation": "..."}] '
            '— see the code_blocks rule below,'
        )
    optional_json = "\n" + "\n".join(optional_fields) if optional_fields else ""

    extra_rules = []
    if subject in _CODE_SUBJECTS:
        extra_rules.append(
            "- \"code_blocks\" LANGUAGE COUNT — read this carefully, it is a hard requirement, not a suggestion:\n"
            "  STEP 1: is this topic tied to ONE specific language's own syntax (e.g. \"Python lists\", \"pointers in "
            "C++\", \"Java interfaces\")? If yes: write ONLY that 1 language, 1 code_blocks entry. Stop here.\n"
            "  STEP 2: otherwise, is this topic an ALGORITHM or a general programming concept that isn't tied to one "
            "language (sorting, searching, recursion, loops, data structures, complexity, etc.)? If yes: you MUST "
            "return EXACTLY 3 code_blocks entries — the literal SAME algorithm, implemented natively/idiomatically in "
            "3 DIFFERENT languages (choose 3 different ones each time from: python, cpp, java, javascript, csharp — "
            "do not always pick the same 3). Returning only 1 language here is WRONG even if that 1 example is "
            "correct — a single-language answer fails this requirement. Do not skip this or default back to Python "
            "alone out of habit.\n"
            "  STEP 3: topic has no code to show at all (hardware, networking, abstract theory)? Return an empty list.\n"
            "  Every snippet must be real, syntactically valid code a compiler for that language would accept — "
            "never a fabricated API/library."
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
    extra_rules.append(
        "- \"lesson_images\": EXACTLY 2 entries, each {\"query\", \"position_after\", \"explanation\"}. \"query\" "
        "is a SHORT (2-4 word) ENGLISH Commons search phrase for a teaching illustration that explains part of "
        "THIS topic — a labelled diagram, a scheme, a graph, a scientific figure, never a decorative picture and "
        "never the same idea twice; name the actual real-world thing this lecture is about (its formula, its "
        "object, its named process). NEVER a metaphor, analogy, or comparison borrowed from a different field, "
        "even one you plan to explain in the caption — the pupil just sees whatever unrelated thing was pictured, "
        "not the connection (confirmed mistakes: a snail-anatomy diagram \"to compare its complexity to a complex "
        "sentence\", a signal-processing waveform \"to compare a simple/complex signal\" to a simple/complex "
        "substance). Add \"diagram\"/\"scheme\" "
        "when the topic is abstract. \"position_after\" is "
        "which section of this document the picture explains (\"key_concepts\", \"main_content\", "
        "\"real_life_examples\"), and the two entries must point at DIFFERENT sections — the picture prints "
        "directly under that section's text, so pick the one whose sentences it illustrates. \"explanation\" is "
        "one short sentence in the document's own language telling the reader what to see in the picture and how "
        "it relates to the text above it. Always return exactly 2 entries."
    )
    extra_rules.append(
        "- \"real_image_query\"/\"real_image_style\": LEAVE BOTH AS EMPTY STRINGS in almost every case — this "
        "document prioritizes text explanation over pictures, so a photo/logo/diagram here should be rare, not the "
        "default. Only fill these in for the truly exceptional case where the topic IS one single, extremely "
        "iconic, immediately-recognizable real-world subject (a specific named software/brand logo, a specific "
        "animal/plant species, a real historical landmark) AND a picture would add real understanding a paragraph "
        "genuinely couldn't. When in doubt, leave both empty — describe it in words in main_content instead. Write "
        "real_image_query as a precise ENGLISH search term for it. Set real_image_style to \"logo\" when the "
        "subject is a brand/software/product/flag/symbol, \"cutout\" when it's a living organism or physical object "
        "best shown whole as a background-removed photo, or \"diagram\" when the topic is specifically about that "
        "organism's INTERNAL structure/anatomy/organs."
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
        "with visual_blocks/real_image kept minimal (see rules above), the explaining is almost entirely THIS "
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
verbatim — condense and organize them). Do NOT invent facts that contradict or aren't supported by the source. Only
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
- Every "lesson_images" query names a diagram of "{topic}" ITSELF. Not the
  subject in general, not a neighboring concept a student might meet in the
  same course — "{topic}" specifically. Measured live: a лексия titled "Реша
  ва вазифаҳои он" (root systems) once asked for diagrams of "human
  circulatory system" and "savanna food web" — real diagrams, just not of
  anything in this lecture, because both are things a biology course also
  covers. If you cannot think of a diagram that shows "{topic}" itself,
  leave "lesson_images" empty rather than reaching for whatever else the
  subject brings to mind.
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
  "real_image_query": "Precise English search term for a real photo/logo/diagram, or empty string — see rules above",
  "real_image_style": "\"logo\", \"cutout\", or \"diagram\", or empty string if real_image_query is empty",
  "lesson_images": [{{"query": "Short English Commons search phrase for a diagram of {topic} ITSELF, not a broader or merely-related concept from the same subject", "position_after": "the section key this picture explains", "explanation": "One sentence telling the pupil what to see in it"}}, {{"query": "...still {topic} itself, a DIFFERENT aspect of it", "position_after": "a DIFFERENT section key", "explanation": "..."}}],
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
) -> str:
    level_map = {
        "Лёгкий": "Beginner. Simple, straightforward questions.",
        "Средний": "Intermediate. Mix of easy and medium questions.",
        "Сложный": "Advanced. Challenging questions requiring deeper understanding.",
    }
    level_text = level_map.get(level, level_map["Средний"])
    subject_hint = _SUBJECT_KONSPEKT_PROMPTS.get(subject, "")
    lang_name = LANGUAGE_NAMES.get(language, "English")

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


def _practical_prompt(
    topic: str,
    subject: str,
    level: str,
    grade: str,
    language: str = "English",
    source_text: str | None = None,
) -> str:
    level_map = {
        "Лёгкий": "Beginner. Short, closely-guided tasks with one clear step at a time.",
        "Средний": "Intermediate. Multi-step tasks that still fit one lesson.",
        "Сложный": "Advanced. Open-ended tasks requiring the pupil to plan their own approach.",
    }
    level_text = level_map.get(level, level_map["Средний"])
    subject_hint = _SUBJECT_KONSPEKT_PROMPTS.get(subject, "")
    lang_name = LANGUAGE_NAMES.get(language, "English")

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
) -> str:
    level_map = {
        "Лёгкий": "Beginner. Simple recall, generous options, no trick questions.",
        "Средний": "Intermediate. Requires understanding, not just memorised facts.",
        "Сложный": "Advanced. Requires applying the concept, not just recalling it.",
    }
    level_text = level_map.get(level, level_map["Средний"])
    subject_hint = _SUBJECT_KONSPEKT_PROMPTS.get(subject, "")
    lang_name = LANGUAGE_NAMES.get(language, "English")

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
) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    subject_hint = _SUBJECT_KONSPEKT_PROMPTS.get(subject, "")

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
- "image_query": REQUIRED on EVERY slide — direct feedback was that a deck with only some slides carrying a
  picture reads as unfinished, so every single slide (formula slides included — search for what the formula is
  ABOUT, not the equation itself) needs one. A short (2-4 word) ENGLISH search phrase for a real Wikimedia
  Commons photo/diagram/figure that illustrates THIS slide's own content: "right triangle labeled", "water cycle
  diagram", "plant cell structure", "Samanid mausoleum", "linear equation graph". Make it as concrete and
  specific to this exact slide as the topic allows — a generic query ("mathematics", "history") returns a
  generic/unrelated picture, a specific one returns a real illustration. Never leave this key out.
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
      "title": "A slide the picture actually teaches, e.g.",
      "kind": "explanation",
      "image_query": "right triangle labeled",
      "bullet_points": ["Short fragment naming what to look at"],
      "speaker_notes": "Extensive teaching notes. At least 3-4 sentences."
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


PROMPTS = {
    "konspekt": _konspekt_prompt,
    "lektsiya": _lecture_prompt,
    "test": _test_prompt,
    "prezentatsiya": _presentation_prompt,
    "amaliy": _practical_prompt,
    "igra": _game_prompt,
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
        return obj.translate(_MISSING_GLYPH_HYPHENS)
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
- Use Tajik vocabulary: шеър not стихотворение, байт not куплет, ғазал not газель, қасида not касыда, адабиёт not литература, муаллиф not автор, эҷодӣ not произведение, достон not поэма, ҳикоя not рассказ, китоб not книга, дарс not урок, мактаб not школа, синф not класс, хонанда not ученик, омӯзгор not учитель, донишҷӯй not студент, вазифа not задача, таҳлил not анализ, тақлид not сравнение, хулоса not вывод, намуна not пример, савол not вопрос, ҷавоб not ответ, ҳақиқат not правда, муҳаббат not любовь, озодӣ not свобода, адолат not справедливость, меҳнат not труд, дониш not знание, шуҷоат not храбрость, некӣ not доброта, зебоӣ not красота, донишгоҳ not университет, тағйирот not изменение, раванд not процесс, нақш not роль, таъсир not влияние, мавзӯъ not тема, мақсад not цель, саволҳо not вопросы
- For literature specifically: шеър (poem), байт (couplet), ғазал (ghazal), қасида (qasida), достон (epic), маснавӣ (masnavi), таҳлил (analysis), муқоиса (comparison), тасвир (image), рамз (symbol), андарз (idea/moral), қаҳрамон (hero), маҷрои воқеа (plot)
- NEVER mix Russian words into Tajik text
- Every single word must be Tajik, zero exceptions"""
    return ""


def _konspekt_system_prompt(language: str) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    tajik_rules = _language_rules(language)
    return f"""You are a school teacher creating a structured lesson plan (konspekt). Return ONLY valid JSON.
Write ALL content in {lang_name} language.{tajik_rules}

CRITICAL RULES:
1. Write ONLY about the topic given.
2. This is a STRUCTURED CURRICULUM lesson plan with specific sections.
3. EXCEPTION — "competencies" and "objectives" must be SHORT, single-phrase/single-sentence bullet points (max ~12 words each), like a real lesson-plan header, NOT paragraphs. Every OTHER section should be DETAILED and SUBSTANTIAL — 3-5 sentences with real facts, examples, and explanations. NOT short phrases!
4. Think of it as a teacher's comprehensive guide — detailed notes that help teach the topic properly (except competencies/objectives, which stay short per rule 3).
5. NEVER write one-sentence answers for the detailed sections. Each of those fields must have enough content to actually teach the material.
6. NEVER mix languages - write ONLY in {lang_name}.
7. NO filler commentary, meta-text, disclaimers, or apologies anywhere in the JSON values — every field is content the teacher will read to students directly, not a note about the content.

The konspekt MUST include these curriculum sections IN ORDER:
1. "competencies" - What skills students will develop (3-4 SHORT phrases, max ~12 words each — not detailed)
2. "objectives" - Learning goals (3-4 SHORT phrases, max ~12 words each — not detailed)
3. "key_concepts" - Core ideas (4-5 detailed items with explanations)
4. "lesson_program" - Detailed lesson structure/plan (4-5 sentences)
5. "tools" - Teaching tools/materials needed (list with descriptions)
6. "main_content" - Main lesson content (3-4 detailed paragraphs, each 4-5 sentences with facts, examples, explanations)
7. "pair_work" - Pair work activity with clear instructions (3-4 sentences)
8. "consolidation" - Lesson consolidation/reinforcement (3-4 sentences)
9. "summary" - Detailed lesson summary (4-5 sentences)
10. "homework" - Homework assignment with specific tasks
11. "assessment" - How to assess student learning (3-4 sentences)

Every field must have SUBSTANTIAL content. Brief notes are NOT acceptable."""


def _lecture_system_prompt(language: str) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    tajik_rules = _language_rules(language)
    return f"""You are a subject-matter expert writing an in-depth lecture (лекция) that explains a topic thoroughly \
— NOT a lesson plan. Return ONLY valid JSON.
Write ALL content in {lang_name} language.{tajik_rules}

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


async def _render_slide_images(content: dict, topic: str) -> None:
    slides = content.get("slides") or []
    wanted = [s for s in slides
              if isinstance(s, dict) and str(s.get("image_query") or "").strip()][:8]
    if not wanted:
        return
    try:
        from app.image_builder import fetch_lesson_images

        from app.image_query import build_queries

        async def _one(slide: dict) -> tuple[dict, dict] | None:
            queries = build_queries(slide, topic, content.get("subject"),
                                    content.get("grade"))[:2]
            found = await fetch_lesson_images(queries, count=1, grade=content.get("grade"),
                                              language=content.get("language"),
                                              subject=content.get("subject"))
            return (slide, found[0]) if found else None

        results = await asyncio.wait_for(
            asyncio.gather(*(_one(slide) for slide in wanted), return_exceptions=True),
            timeout=75.0,
        )
        fetched: list[tuple[dict, dict]] = [
            r for r in results if isinstance(r, tuple)
        ]
        _seen_paths: set[str] = set()
        _unique: list[tuple[dict, dict]] = []
        for _slide, _image in fetched:
            _key = str(_image.get("path") or _image.get("title") or "")
            if _key and _key in _seen_paths:
                logger.info(f"Slide image dropped as duplicate: {_key}")
                continue
            if _key:
                _seen_paths.add(_key)
            _unique.append((_slide, _image))
        fetched = _unique
        if not fetched:
            return
        slide_of = {id(image): slide for slide, image in fetched}
        context_of = lambda im: (
            f'{slide_of[id(im)].get("title", "")} — {str(slide_of[id(im)].get("body") or "")[:200]}'
        )
        images = await _caption_and_verify_images(
            content, topic, [image for _, image in fetched], context_of=context_of)
        kept_ids = {id(im) for im in images}
        for slide, image in fetched:
            if id(image) not in kept_ids:
                continue
            slide["image"] = {
                "path": image["path"],
                "caption": image.get("caption", ""),
                "credit": image.get("credit", ""),
                "source": image.get("source", ""),
            }
            if image.get("explanation"):
                slide["image"]["explanation"] = image["explanation"]
    except Exception as e:
        logger.warning(f"Slide image fetch failed for topic={topic[:50]}: {e}")


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


_SOURCE_EXCERPT_CHARS = 20000


def _find_topic_offset(source_text: str, topic: str) -> int:
    haystack = source_text.lower()
    needle = topic.lower().strip()
    idx = haystack.rfind(needle) if needle else -1
    if idx == -1 and needle:
        for word in sorted(set(needle.split()), key=len, reverse=True):
            if len(word) > 3:
                idx = haystack.rfind(word)
                if idx != -1:
                    break
    return idx


def _select_relevant_excerpt(source_text: str, topic: str, max_chars: int = _SOURCE_EXCERPT_CHARS) -> str:
    if len(source_text) <= max_chars:
        return source_text

    idx = _find_topic_offset(source_text, topic)

    if idx == -1:
        return source_text[:max_chars]

    half = max_chars // 2
    start = max(0, idx - half)
    end = min(len(source_text), start + max_chars)
    start = max(0, end - max_chars)
    excerpt = source_text[start:end]
    if start > 0:
        excerpt = "…" + excerpt
    if end < len(source_text):
        excerpt = excerpt + "…"
    return excerpt


_TEXTBOOK_CACHE_DIR = os.path.join(os.path.dirname(__file__), "textbooks_cache")
_textbook_manifest_cache: dict | None = None


def _textbook_manifest() -> dict:
    global _textbook_manifest_cache
    if _textbook_manifest_cache is None:
        manifest_path = os.path.join(_TEXTBOOK_CACHE_DIR, "_manifest.json")
        try:
            with open(manifest_path, encoding="utf-8") as f:
                _textbook_manifest_cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _textbook_manifest_cache = {}
    return _textbook_manifest_cache


def _textbook_entry(subject: str, grade: str) -> dict | None:
    grade_num = (grade or "").strip().split()[0] if grade else ""
    return _textbook_manifest().get(subject, {}).get(grade_num)


def _load_cached_textbook(subject: str, grade: str) -> str | None:
    entry = _textbook_entry(subject, grade)
    if not entry:
        return None
    try:
        with open(os.path.join(_TEXTBOOK_CACHE_DIR, f"{entry['name']}.txt"), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


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
    template: str | None = None,
    source_text: str | None = None,
    previous_digests: list[dict] | None = None,
) -> dict:
    prompt_fn = PROMPTS.get(material_type)
    if not prompt_fn:
        logger.error(f"Unknown material type: {material_type}")
        raise ValueError(f"Unknown material type: {material_type}")

    source_text = source_text or _load_cached_textbook(subject, grade)
    source_excerpt = _select_relevant_excerpt(source_text, topic) if source_text else None

    variant: dict = {}
    test_type = test_type or "mixed"
    if material_type == "prezentatsiya":
        user_prompt = prompt_fn(topic, subject, level, grade, language, slide_count or 10,
                                source_excerpt, previous_digests, variant)
    elif material_type == "test":
        user_prompt = prompt_fn(topic, subject, level, grade, language, question_count or 10, test_type, source_excerpt)
    elif material_type == "konspekt":
        user_prompt = prompt_fn(topic, subject, level, grade, language, include_homework, include_fun_facts,
                                include_assessment, source_excerpt, previous_digests, variant)
    else:
        user_prompt = prompt_fn(topic, subject, level, grade, language, source_text=source_excerpt)

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

CRITICAL RULES:
1. Write ONLY about the topic given.
2. {test_type_rule}
3. NEVER mix languages - write ONLY in {lang_name}.""",

        "prezentatsiya": f"""You are a school teacher creating a presentation with slides. Return ONLY valid JSON.
Write ALL content in {lang_name} language.{tajik_rules}

CRITICAL RULES:
1. Write ONLY about the topic given.
2. Create exactly the number of slides requested.
3. Each slide MUST have a title, 3-5 bullet points, and speaker notes.
4. NEVER mix languages - write ONLY in {lang_name}.
5. Return ONLY valid JSON, nothing else.""",

        "amaliy": f"""You are a school teacher writing hands-on practical tasks. Return ONLY valid JSON.
Write ALL content in {lang_name} language.{tajik_rules}

CRITICAL RULES:
1. Write ONLY about the topic given.
2. Every task has the pupil DO or MAKE something concrete, never answer a multiple-choice question.
3. NEVER mix languages - write ONLY in {lang_name}.""",

        "igra": f"""You are a school teacher building an interactive in-class game. Return ONLY valid JSON.
Write ALL content in {lang_name} language.{tajik_rules}

CRITICAL RULES:
1. Write ONLY about the topic given.
2. Every round must be answerable from the lesson itself, never unrelated general trivia.
3. NEVER mix languages - write ONLY in {lang_name}.""",
    }

    system_prompt = system_prompts.get(material_type, system_prompts["konspekt"])

    content = await _call_ai(system_prompt, user_prompt, language, log_label=f"{material_type} topic={topic[:50]}")

    if material_type in ("konspekt", "lektsiya", "prezentatsiya"):
        content = await _verify_and_fix(material_type, content, language, topic)

    if material_type in ("konspekt", "lektsiya", "prezentatsiya", "test", "amaliy"):
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
        await _fetch_real_world_image(content, topic)
        await _render_lesson_images(content, topic)

    if material_type == "prezentatsiya":
        _drop_bullets_duplicating_visual(content, topic)
        _typeset_math_content(content, topic)
        _render_slide_figures(content, topic)
        await _render_slide_images(content, topic)

    if material_type == "test":
        _validate_test_quality(content, topic, question_count or 10)
        _typeset_math_content(content, topic)
        await _render_test_images(content, topic)

    if material_type == "amaliy":
        _validate_practical_quality(content, topic)


    return content


_exhausted_keys: set[str] = set()


async def _call_ai(system_prompt: str, user_prompt: str, language: str, log_label: str) -> dict:
    global _api_call_count, _daily_reset_time

    async with ai_slot(log_label):
        return await _call_ai_inner(system_prompt, user_prompt, language, log_label)


async def _call_ai_inner(system_prompt: str, user_prompt: str, language: str, log_label: str) -> dict:
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
                temp = 0.5 if attempt > 0 else 0.7
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
                            "max_tokens": 24000,
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


async def _call_ai_stream(system_prompt: str, user_prompt: str, log_label: str):
    global _api_call_count, _daily_reset_time

    async with ai_slot(f"{log_label} (stream)"):
        async for delta in _call_ai_stream_inner(system_prompt, user_prompt, log_label):
            yield delta


async def _call_ai_stream_inner(system_prompt: str, user_prompt: str, log_label: str):
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
                temp = 0.5 if attempt > 0 else 0.7
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
                            "max_tokens": 24000,
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


async def _verify_and_fix(material_type: str, content: dict, language: str, topic: str) -> dict:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    system_prompt = (
        "You are a meticulous fact-checking editor reviewing educational content for a school "
        f"teacher. Return ONLY valid JSON, with every field still written in {lang_name}."
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

    user_prompt = f"""Review the following {material_type} JSON about "{topic}" for factual accuracy, internal consistency, and language correctness.

Fix ONLY real problems:
- Invented, incorrect, or unverifiable facts, dates, statistics, or named people/events
- Claims that contradict each other within the document
- Anything nonsensical or unrelated to "{topic}"{language_check}

Do NOT report anything that is already correct. Most documents have no errors at all — an empty list is the expected, normal answer.

Return ONLY a JSON object listing the corrections, in this exact shape:
{{"fixes": [{{"path": "/main_content/2/text", "new": "the corrected text"}}]}}

- "path" is an RFC 6901 JSON Pointer to the exact value that is wrong, in the document below. Array items are addressed by index, e.g. "/key_concepts/0/definition".
- "new" is the corrected value, a string or number only. Rewrite as little as possible: keep the original wording, tone and length, changing only the part that is actually wrong.
- Never invent a path that is not in the document, never add fields, and never remove or reorder array items.
- If the document is fine, return exactly: {{"fixes": []}}

The document to review:
{json.dumps(content, ensure_ascii=False)}"""

    try:
        result = await _call_ai(system_prompt, user_prompt, language, log_label=f"verify {material_type} topic={topic[:50]}")
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


_KONSPEKT_STREAM_FIELDS = [
    "title", "subtitle", "duration", "competencies", "objectives", "key_concepts",
    "key_terms", "real_life_examples", "lesson_program", "tools", "main_content",
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
    source_text: str | None = None,
    template: str | None = None,
    previous_digests: list[dict] | None = None,
):
    try:
        source_text = source_text or _load_cached_textbook(subject, grade)
        source_excerpt = _select_relevant_excerpt(source_text, topic) if source_text else None

        yield {"stage": "source_analysis", "status": "start"}
        yield {"stage": "source_analysis", "status": "done", "used_source": bool(source_excerpt)}

        yield {"stage": "understand_topic", "status": "start"}
        system_prompt = _konspekt_system_prompt(language)
        yield {"stage": "understand_topic", "status": "done"}

        yield {"stage": "extract_info", "status": "start"}
        variant: dict = {}
        user_prompt = _konspekt_prompt(
            topic, subject, level, grade, language,
            include_homework, include_fun_facts, include_assessment,
            source_excerpt, previous_digests, variant,
        )
        yield {"stage": "extract_info", "status": "done"}

        yield {"stage": "outline", "status": "start"}

        buffer = ""
        remaining_fields = list(_KONSPEKT_STREAM_FIELDS)
        active_field: str | None = None
        outline_done = False
        generate_sections_started = False

        async for delta in _call_ai_stream(system_prompt, user_prompt, log_label=f"konspekt-stream topic={topic[:50]}"):
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
        yield {"stage": "format", "status": "done"}

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
        await _fetch_real_world_image(content, topic)
        await _render_lesson_images(content, topic)
        yield {"stage": "visual_elements", "status": "done", "block_count": len(content.get("visual_blocks") or [])}

        yield {"stage": "validate", "status": "start"}
        content = await _verify_and_fix("konspekt", content, language, topic)
        _typeset_math_content(content, topic)
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
    subject_hint = _SUBJECT_KONSPEKT_PROMPTS.get(subject, "")
    lang_name = LANGUAGE_NAMES.get(language, "English")
    existing_text = "\n".join(f"- {q}" for q in existing_questions) or "(none)"

    info = _QUESTION_TYPE_INFO.get(question_type) or _QUESTION_TYPE_INFO["multiple_choice"]
    question_type = question_type if question_type in _QUESTION_TYPE_INFO else "multiple_choice"
    type_instructions = info["instructions"]
    shape = info["shape"](topic, lang_name)

    return f"""Create exactly ONE new "{question_type}" question about "{topic}" for grade {grade}, subject "{subject}".

CRITICAL: Write ALL content in {lang_name} language. Return ONLY valid JSON, nothing else.

Subject style: {subject_hint}
Difficulty: {level_text}

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
    subject_hint = _SUBJECT_KONSPEKT_PROMPTS.get(subject, "")
    lang_name = LANGUAGE_NAMES.get(language, "English")
    existing_text = "\n".join(f"- {t}" for t in existing_titles) or "(none)"

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

The task MUST be different in focus from these existing tasks on the same worksheet:
{existing_text}

Return THIS exact JSON (nothing else):
{shape}"""


def _regenerate_slide_prompt(topic: str, subject: str, level: str, grade: str, language: str, slide_index: int, total_slides: int, existing_titles: list[str]) -> str:
    lang_name = LANGUAGE_NAMES.get(language, "English")
    existing_text = "\n".join(f"- {t}" for t in existing_titles) or "(none)"

    return f"""Create exactly ONE new presentation slide (slide {slide_index + 1} of {total_slides}) about "{topic}" for grade {grade}, subject "{subject}".

CRITICAL: Write ALL content in {lang_name} language. Return ONLY valid JSON, nothing else.

The slide MUST cover different ground than these other slides already in the presentation:
{existing_text}

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

    other_context = {
        k: v for k, v in existing_content.items()
        if k != section and k not in ("title", "subtitle", "language", "subject", "grade") and isinstance(v, (str, list)) and v
    }
    context_json = json.dumps(other_context, ensure_ascii=False)
    if len(context_json) > 2500:
        context_json = context_json[:2500] + "…"

    return f"""Rewrite ONLY the "{section}" section of an existing {doc_word} about "{topic}" for grade {grade}, subject "{subject}".

Subject style/difficulty: {level_text}

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
    else:
        raise ValueError(f"Regenerating a single item is only supported for 'test', 'prezentatsiya', and 'amaliy', got {material_type!r}")

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
    types: list[str] | None = None,
) -> dict:
    import asyncio

    if types is None:
        types = ["konspekt", "test", "prezentatsiya", "lektsiya"]

    results = {}
    errors = {}

    sem = asyncio.Semaphore(1)

    async def _gen(mt: str):
        async with sem:
            try:
                return mt, await generate_material(
                    material_type=mt,
                    topic=topic,
                    subject=subject,
                    language=language,
                    level=level,
                    grade=grade,
                    slide_count=slide_count if mt == "prezentatsiya" else None,
                    question_count=question_count if mt == "test" else None,
                    test_type=test_type if mt == "test" else None,
                    template=_default_template_for(mt, subject, grade),
                )
            except Exception as e:
                logger.warning(f"generate_all: {mt} FAILED: {e}")
                return mt, e

    tasks = [_gen(mt) for mt in types]
    done = await asyncio.gather(*tasks)

    for mt, result in done:
        if isinstance(result, Exception):
            errors[mt] = str(result)
        else:
            results[mt] = result

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
