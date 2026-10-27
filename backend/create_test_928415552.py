import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models import User
from app.auth import hash_password

PHONE = "+992928415552"
PASSWORD = "123qwe"


async def main():
    async with async_session() as db:
        result = await db.execute(select(User).where(User.phone == PHONE))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                full_name="Test User",
                phone=PHONE,
                phone_verified=True,
                hashed_password=hash_password(PASSWORD),
                role="user",
            )
            db.add(user)
            print(f"Created new account: {PHONE} / {PASSWORD}")
        else:
            user.hashed_password = hash_password(PASSWORD)
            user.phone_verified = True
            print(f"Reset existing account's password: {PHONE} / {PASSWORD}")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
