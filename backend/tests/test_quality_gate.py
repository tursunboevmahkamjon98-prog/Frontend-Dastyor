# -*- coding: utf-8 -*-
"""Checks on the deterministic test-quality gate (ai_service.
_validate_test_quality). No database and no AI call — it is a pure
function over a dict, which is the point of doing this in code rather
than with a second model pass."""
import sys

from app.ai_service import _validate_test_quality, _question_fingerprint, _near_duplicate

FAIL = []


def check(name, condition, detail=""):
    print(("  PASS  " if condition else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not condition:
        FAIL.append(name)


def mc(q, options, correct, **extra):
    return {"question": q, "type": "multiple_choice", "options": options,
            "correct_index": correct, **extra}


print("\n1. An out-of-range answer key is dropped")
content = {"questions": [
    mc("Что такое атом?", ["A", "B", "C", "D"], 1),
    mc("Из чего состоит ядро?", ["A", "B"], 7),      # index past the end
]}
_validate_test_quality(content, "Атом", 2)
check("the unanswerable question is gone", len(content["questions"]) == 1,
      f"n={len(content['questions'])}")
check("the good question survives", content["questions"][0]["question"] == "Что такое атом?")

print("\n2. A near-duplicate question is dropped, a merely similar one is not")
content = {"questions": [
    mc("Какие частицы входят в состав атомного ядра?", ["A", "B", "C"], 0),
    mc("Какие частицы входят в состав ядра атома?", ["A", "B", "C"], 1),   # reword
    mc("Какой заряд имеет электрон в атоме вещества?", ["A", "B", "C"], 2),  # different
]}
_validate_test_quality(content, "Атом", 3)
check("the reworded duplicate is gone", len(content["questions"]) == 2,
      f"n={len(content['questions'])}")
check("the genuinely different question stayed",
      any("заряд" in q["question"] for q in content["questions"]))

print("\n3. Blank padding options are removed AND the answer key follows them")
content = {"questions": [
    mc("Столица Таджикистана?", ["Худжанд", "", "Душанбе", "  "], 2),
]}
_validate_test_quality(content, "География", 1)
q = content["questions"][0]
check("blank options removed", q["options"] == ["Худжанд", "Душанбе"], f"{q['options']}")
check("the key still points at 'Душанбе'", q["options"][q["correct_index"]] == "Душанбе",
      f"index={q['correct_index']}")

print("\n4. Two identical options make the question unanswerable")
content = {"questions": [
    mc("2 + 2 = ?", ["4", "5", "4", "6"], 0),
    mc("3 + 3 = ?", ["5", "6", "7", "8"], 1),
]}
_validate_test_quality(content, "Математика", 2)
check("the ambiguous question is gone", len(content["questions"]) == 1,
      f"n={len(content['questions'])}")
check("the sound one stayed", content["questions"][0]["question"] == "3 + 3 = ?")

print("\n5. multiple_select with every option correct is not a question")
content = {"questions": [
    {"question": "Что относится к металлам?", "type": "multiple_select",
     "options": ["Железо", "Медь"], "correct_indices": [0, 1]},
    {"question": "Какие газы входят в состав воздуха?", "type": "multiple_select",
     "options": ["Азот", "Кислород", "Гелий-3"], "correct_indices": [0, 1]},
]}
_validate_test_quality(content, "Химия", 2)
check("the all-correct one is gone", len(content["questions"]) == 1,
      f"n={len(content['questions'])}")

print("\n6. A test the gate would empty is left alone rather than destroyed")
content = {"questions": [
    mc("Вопрос один", ["A", "B"], 9),
    mc("Вопрос два", ["A", "B"], 9),
]}
_validate_test_quality(content, "Тема", 2)
check("both questions kept (a broken test beats no test)",
      len(content["questions"]) == 2, f"n={len(content['questions'])}")

print("\n7. open_ended questions pass through untouched")
content = {"questions": [
    {"question": "Опишите строение атома своими словами.", "type": "open_ended",
     "model_answer": "Ядро и электроны."},
]}
_validate_test_quality(content, "Атом", 1)
check("kept", len(content["questions"]) == 1)

print("\n8. Short questions differing by one word are not treated as duplicates")
a = _question_fingerprint("Что такое атом?")
b = _question_fingerprint("Что такое ион?")
check("'атом' and 'ион' are different questions", not _near_duplicate(a, b))

print()
if FAIL:
    print(f"{len(FAIL)} FAILED: {FAIL}")
    sys.exit(1)
print("all quality-gate checks passed")
