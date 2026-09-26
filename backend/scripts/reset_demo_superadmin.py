"""Create or reset the local demo superadmin account in a development database."""

import asyncio
import getpass
import sys
from pathlib import Path

from sqlalchemy import select, update

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.session import async_session
from app.models.admin import Admin
from app.models.token import AdminToken


EMAIL = "superadmin@test.com"


async def reset_password(password: str) -> None:
    async with async_session() as db:
        admin = (await db.execute(select(Admin).where(Admin.email == EMAIL))).scalar_one_or_none()
        if admin is None:
            admin = Admin(
                email=EMAIL,
                first_name="Super",
                last_name="Admin",
                role="superadmin",
                password=Admin.get_password_hash(password),
                is_active=True,
            )
            db.add(admin)
        else:
            await db.execute(
                update(AdminToken)
                .where(AdminToken.admin_id == admin.id, AdminToken.is_active.is_(True))
                .values(is_active=False)
            )
            admin.password = Admin.get_password_hash(password)
            admin.is_active = True
        await db.commit()

    async with async_session() as db:
        saved = (await db.execute(select(Admin).where(Admin.email == EMAIL))).scalar_one_or_none()
        if saved is None or not saved.verify_password(password):
            raise RuntimeError("数据库重新读取后密码验证失败")


def main() -> None:
    if settings.ENV != "development":
        raise SystemExit("仅允许在开发环境重设演示账号")

    password = getpass.getpass("请输入新的演示管理员密码（至少12位）：")
    if len(password) < 12:
        raise SystemExit("密码至少需要12位，账号未修改")
    if password != getpass.getpass("请再输入一次："):
        raise SystemExit("两次输入不一致，账号未修改")

    asyncio.run(reset_password(password))
    print(f"数据库校验通过：{EMAIL}（{settings.POSTGRES_HOST}/{settings.POSTGRES_DB}）")


if __name__ == "__main__":
    main()
