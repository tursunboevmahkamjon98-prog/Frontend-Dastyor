"""Shape checks for app/topic_guard.py.

Runs offline - no server, no database, no model. The point of these cases is
that the free layer must reject mashing without ever rejecting a real Tajik,
Russian or English lesson topic, because a false rejection stops a teacher
from working.

    python -m tests.test_topic_guard
"""

import sys

from app.topic_guard import shape_verdict

FAIL = []


def check(name, condition, detail=""):
    print(("  PASS  " if condition else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not condition:
        FAIL.append(name)


REAL_TOPICS = [
    "Ҳуҷайра — воҳиди асосии зинда",
    "Сохт ва вазифаи системаи нафаскашии инсон",
    "Клетка — основная единица живого",
    "Фотосинтез",
    "Квадратные уравнения",
    "Алгоритм ва блок-схема",
    "The Present Perfect Tense",
    "Python",
    "ДНК",
    "HTML ва CSS",
    # Exercises the acronym path inside a realistic phrase. A bare "pH" is
    # rejected by MIN_LENGTH, which is intended: a two-character string is
    # not a lesson topic, and teachers write the surrounding phrase.
    "Кислоты и pH",
    "3D геометрия",
    "Второй закон Ньютона",
    "Истиқлолияти Тоҷикистон",
    "Рӯдакӣ — падари шеъри форсу тоҷик",
    "Фанни география: иқлим",
]

MASHING = [
    "asdkjh",
    "qwerty",
    "йцукен",
    "фыва",
    "ццццц",
    "aaaaaa",
    "zxcvbn",
    "ghjkl",
    "...",
    "12345",
    "!!!",
    "a",
    "бвгджз",
]


def main():
    print("real topics must pass")
    for topic in REAL_TOPICS:
        verdict = shape_verdict(topic)
        check(f"accepts {topic!r}", verdict.ok, verdict.detail)

    print("")
    print("mashing must be rejected")
    for topic in MASHING:
        verdict = shape_verdict(topic)
        check(f"rejects {topic!r}", not verdict.ok, verdict.reason)

    print("")
    if FAIL:
        print(f"{len(FAIL)} FAILED")
        for name in FAIL:
            print("  - " + name)
        sys.exit(1)
    print(f"all {len(REAL_TOPICS) + len(MASHING)} cases passed")


if __name__ == "__main__":
    main()
