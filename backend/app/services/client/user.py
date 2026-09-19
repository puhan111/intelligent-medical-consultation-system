from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.user import User
from app.schemas.client.user import UserProfileResponse
from typing import Optional


class UserService:
    @staticmethod
    async def get_profile(db: AsyncSession, user_id: int) -> Optional[UserProfileResponse]:
        """获取患者个人资料"""
        user_query = select(User).where(User.id == user_id)
        user = (await db.execute(user_query)).scalar_one_or_none()

        if not user:
            return None

        return UserProfileResponse.model_validate(user)

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        user_id: int,
        profile_data: dict
    ) -> Optional[UserProfileResponse]:
        """更新患者个人资料（仅允许修改姓名、头像、性别）"""
        user_query = select(User).where(User.id == user_id)
        user = (await db.execute(user_query)).scalar_one_or_none()

        if not user:
            return None

        allowed_fields = {"first_name", "last_name", "avatar", "gender"}
        update_data = {k: v for k, v in profile_data.items() if k in allowed_fields}

        if update_data:
            stmt = update(User).where(User.id == user_id).values(**update_data)
            await db.execute(stmt)

            user_query = select(User).where(User.id == user_id)
            user = (await db.execute(user_query)).scalar_one_or_none()

        return UserProfileResponse.model_validate(user)


user_service = UserService()
