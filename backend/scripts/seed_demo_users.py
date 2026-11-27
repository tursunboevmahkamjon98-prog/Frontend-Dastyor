"""Demo-data seeding for the competition: ~223 realistic Tajik teacher
accounts with activity history (materials + balance top-ups), so the
admin panel (user list, balance history, materials list) has real
content to show instead of a handful of test rows.

Run once with the backend's venv:
    ./.venv/Scripts/python.exe scripts/seed_demo_users.py

Safe to re-run: skips phone numbers that already exist.
"""
import asyncio
import json
import random
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.database import async_session
from app.auth import hash_password
from app.models import User, Konspekt, Lecture, Presentation, Test, BalanceTransaction, BalanceTopupRequest

N_USERS = 223
NOW = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

MALE_FIRST = [
    "Акмал", "Алишер", "Бахтиёр", "Фаридун", "Хуршед", "Шерали", "Дилшод", "Фирдавс",
    "Ҷамшед", "Исмоил", "Абдурашид", "Расул", "Назир", "Саидали", "Умед", "Фарход",
    "Нурали", "Шамсиддин", "Абдулло", "Комил", "Истам", "Рустам", "Зафар", "Мансур",
    "Қодир", "Самад", "Хайрулло", "Эмомали", "Davlat", "Муҳаммад",
]
FEMALE_FIRST = [
    "Гулнора", "Зарина", "Мадина", "Нигина", "Сайёра", "Фарангис", "Дилафруз", "Шахноза",
    "Муҳаббат", "Фотима", "Зулайҳо", "Малика", "Нилуфар", "Парвина", "Сабоҳат",
    "Гулчеҳра", "Ситора", "Хосият", "Манижа", "Фарзона", "Дилором", "Шукрона",
]
SURNAME_ROOTS = [
    "Раҳимов", "Каримов", "Қодиров", "Юсупов", "Назаров", "Сафаров", "Шарипов",
    "Исмоилов", "Абдуллоев", "Холиқов", "Турсунов", "Муродов", "Зиёев", "Эргашев",
    "Шодиев", "Рустамов", "Файзуллоев", "Одинаев", "Бобоев", "Саидов", "Давлатов",
    "Ҳакимов", "Собиров", "Латипов", "Назриев",
]

SUBJECTS = [
    "Математика", "Физика", "Химия", "Биология", "Таърих", "География",
    "Забони тоҷикӣ", "Забони русӣ", "Забони англисӣ", "Информатика",
]
GRADES = [f"{i} синф" for i in range(5, 12)]

LANGUAGES = ["Таджикский", "Русский"]

PHONE_PREFIXES = ["90", "91", "92", "93", "98", "99", "55", "50"]


def make_phone(used: set) -> str:
    while True:
        prefix = random.choice(PHONE_PREFIXES)
        rest = "".join(str(random.randint(0, 9)) for _ in range(7))
        phone = f"+992{prefix}{rest}"
        if phone not in used:
            used.add(phone)
            return phone


def make_name():
    is_male = random.random() < 0.5
    first = random.choice(MALE_FIRST if is_male else FEMALE_FIRST)
    root = random.choice(SURNAME_ROOTS)
    surname = root if is_male else root[:-2] + ("ева" if root.endswith("ев") else "ова")
    return f"{first} {surname}"


def random_past(days_back: int):
    delta = timedelta(days=random.uniform(0, days_back), hours=random.uniform(0, 24))
    return NOW - delta


def placeholder_konspekt():
    return json.dumps({
        "title": "Намунавӣ", "subtitle": "", "duration": "45 дақиқа",
        "objectives": ["Мафҳумҳои асосиро фаҳмидан"], "key_concepts": [],
        "key_terms": [], "real_life_examples": [], "lesson_program": [],
        "lesson_stages": [], "tools": [], "main_content": "Матни демо барои намоиш.",
        "homework": "", "summary": "",
    }, ensure_ascii=False)


def placeholder_slides():
    return json.dumps({
        "title": "Намунавӣ", "description": "", "template": None,
        "slides": [{"title": "Муқаддима", "kind": "intro", "bullet_points": ["Нуқтаи аввал"], "body": "Матни демо."}],
    }, ensure_ascii=False)


def placeholder_questions():
    return json.dumps([{
        "type": "mcq", "question": "Саволи намунавӣ?",
        "options": ["A", "B", "C", "D"], "correct_index": 0,
    }], ensure_ascii=False)


async def main():
    async with async_session() as db:
        existing = (await db.execute(select(User.phone))).scalars().all()
        used_phones = {p for p in existing if p}

        result = await db.execute(select(User).where(User.role == "user"))
        current_demo_count = len(result.scalars().all())
        to_create = max(0, N_USERS - current_demo_count)
        print(f"Existing non-admin users: {current_demo_count}. Creating {to_create} more.")

        created_users = []
        for _ in range(to_create):
            phone = make_phone(used_phones)
            created_at = random_past(120)
            user = User(
                full_name=make_name(),
                phone=phone,
                phone_verified=True,
                hashed_password=hash_password("Demo-" + phone[-6:]),
                role="user",
                is_premium=random.random() < 0.22,
                language=random.choice(LANGUAGES),
                balance_dirams=0,
                created_at=created_at,
            )
            db.add(user)
            created_users.append((user, created_at))

        await db.flush()
        print(f"Inserted {len(created_users)} users.")

        # --- materials: each user gets 0-6 items, spread after their signup date
        material_count = 0
        for user, created_at in created_users:
            n_items = random.choices([0, 1, 2, 3, 4, 5, 6], weights=[8, 15, 20, 20, 15, 12, 10])[0]
            for _ in range(n_items):
                mt = random.choices(
                    ["konspekt", "lektsiya", "test", "prezentatsiya"],
                    weights=[35, 20, 25, 20],
                )[0]
                subject = random.choice(SUBJECTS)
                grade = random.choice(GRADES)
                item_created = created_at + timedelta(
                    days=random.uniform(0, max(1, (NOW - created_at).days)),
                    hours=random.uniform(0, 24),
                )
                if item_created > NOW:
                    item_created = NOW - timedelta(hours=random.uniform(1, 48))
                title = f"{subject}: мавзӯи {random.randint(1, 20)}"

                if mt == "konspekt":
                    row = Konspekt(title=title, subject=subject, grade=grade,
                                    content=placeholder_konspekt(), owner_id=user.id,
                                    created_at=item_created, updated_at=item_created)
                elif mt == "lektsiya":
                    row = Lecture(title=title, subject=subject, grade=grade,
                                   content=placeholder_konspekt(), owner_id=user.id,
                                   created_at=item_created, updated_at=item_created)
                elif mt == "test":
                    row = Test(title=title, subject=subject, grade=grade,
                               questions_json=placeholder_questions(), owner_id=user.id,
                               created_at=item_created, updated_at=item_created)
                else:
                    row = Presentation(title=title, subject=subject, grade=grade,
                                        slides_json=placeholder_slides(), owner_id=user.id,
                                        created_at=item_created, updated_at=item_created)
                db.add(row)
                material_count += 1
        print(f"Inserted {material_count} materials.")

        # --- balance top-ups for ~35% of users: a credited transaction +
        # matching balance, so "who paid" has real history.
        topup_count = 0
        pending_count = 0
        for user, created_at in created_users:
            if random.random() > 0.35:
                continue
            n_topups = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
            balance_before = 0
            tx_time = created_at
            for _ in range(n_topups):
                tx_time = tx_time + timedelta(days=random.uniform(1, 25))
                if tx_time > NOW:
                    break
                amount = random.choice([2000, 3000, 5000, 10000, 15000, 20000]) * 100  # dirams
                balance_after = balance_before + amount
                db.add(BalanceTransaction(
                    user_id=user.id, kind="topup", amount_dirams=amount,
                    balance_before=balance_before, balance_after=balance_after,
                    reason="Пардохти тарифи пулакӣ", created_at=tx_time,
                    public_code=f"TX-{random.randint(10**6, 10**7-1):07X}",
                ))
                balance_before = balance_after
                topup_count += 1
            user.balance_dirams = balance_before

            if random.random() < 0.12:
                db.add(BalanceTopupRequest(
                    user_id=user.id,
                    requested_dirams=random.choice([5000, 10000, 15000]) * 100,
                    note="Чаллон аз Алиф/Душанбе Сити карта кардам",
                    status="pending",
                    created_at=NOW - timedelta(hours=random.uniform(1, 72)),
                ))
                pending_count += 1
        print(f"Inserted {topup_count} balance top-ups, {pending_count} pending requests.")

        await db.commit()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
