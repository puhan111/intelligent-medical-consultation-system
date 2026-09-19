"""初始化系统内置的后台账号。

Alembic 迁移负责维护数据库表结构，本脚本负责初始化登录后台所需的
最小账号数据。

在应用容器中执行：
    docker exec -it app-app python scripts/init_data.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.db.session import async_session
from app.models.admin import Admin, UserRole


async def create_admin(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: UserRole,
) -> None:
    """创建已启用的后台账号；如果邮箱已经存在，则跳过创建。"""
    async with async_session() as db:
        result = await db.execute(select(Admin).where(Admin.email == email))
        if result.scalar_one_or_none():
            print(f"后台账号已经存在，跳过创建：{email}")
            return

        admin = Admin(
            email=email,
            password=Admin.get_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        print(f"创建成功：{email}（角色：{role.value}）")


async def main() -> None:
    await create_admin(
        email="superadmin@test.com",
        password="admin123",
        first_name="Super",
        last_name="Admin",
        role=UserRole.SUPERADMIN,
    )
    await create_admin(
        email="pharmacist1@test.com",
        password="pharm123",
        first_name="Pharmacist",
        last_name="Wang",
        role=UserRole.PHARMACIST,
    )
    await create_admin(
        email="cashier1@test.com",
        password="cashier123",
        first_name="Cashier",
        last_name="Li",
        role=UserRole.CASHIER,
    )
    await create_admin(
        email="lab1@test.com",
        password="lab123",
        first_name="Lab",
        last_name="Chen",
        role=UserRole.LAB,
    )


if __name__ == "__main__":
    asyncio.run(main())
