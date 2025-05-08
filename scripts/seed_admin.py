# scripts/seed_admin.py

import asyncio

from app.database import AsyncSessionLocal
from app.models import Admin, RoleEnum
from app.utils.security import hash_password

async def main() -> None:
    async with AsyncSessionLocal() as session:
        # check if admin already exists
        exists = await session.execute(
            Admin.__table__.select().where(Admin.username == "admin")
        )
        if exists.first():
            print("Admin user already exists, skipping seed.")
            return

        admin = Admin(
            username="admin",
            password=hash_password("P@ssw0rd"),
            role=RoleEnum.admin,
        )
        session.add(admin)
        await session.commit()
        print("Seeded admin user.")

if __name__ == "__main__":
    asyncio.run(main())
