"""One-off: insert a plain (role='user') local test account, separate from
the admin account in dev-test-user.txt. Run once with the backend's venv:
    ./.venv/Scripts/python.exe scripts/create_plain_test_user.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import async_session
from app.auth import hash_password
from app.models import User

PHONE = "+992900000202"
PASSWORD = "User-7xQmZpT2vA"


async def main():
    async with async_session() as db:
        from sqlalchemy import select

        result = await db.execute(select(User).where(User.phone == PHONE))
        user = result.scalar_one_or_none()
        if user:
            print(f"Already exists: {PHONE} (role={user.role})")
            return

        user = User(
            full_name="Oddiy Foydalanuvchi",
            phone=PHONE,
            phone_verified=True,
            hashed_password=hash_password(PASSWORD),
            role="user",
            is_premium=False,
        )
        db.add(user)
        await db.commit()
        print(f"Created plain user: {PHONE} / {PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
