import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models import User
from app.auth import hash_password

PHONE = "+992997776726"
EMAIL = "admin997776726@dastyor.local"
PASSWORD = "adminpp"


async def main():
    async with async_session() as db:
        result = await db.execute(select(User).where(User.phone == PHONE))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                full_name="Admin",
                phone=PHONE,
                phone_verified=True,
                email=EMAIL,
                hashed_password=hash_password(PASSWORD),
                role="admin",
            )
            db.add(user)
            print(f"Created new admin: {PHONE} / {EMAIL}")
        else:
            user.role = "admin"
            user.email = EMAIL
            user.hashed_password = hash_password(PASSWORD)
            user.phone_verified = True
            print(f"Promoted/updated existing account to admin: {PHONE} / {EMAIL}")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
