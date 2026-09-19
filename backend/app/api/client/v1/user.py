from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from app.schemas.client.user import UserProfileResponse, UserProfileUpdate
from app.services.client.user import user_service
from app.api.client.deps import get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.exceptions.http_exceptions import APIException


router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前登录患者的个人资料"""
    result = await user_service.get_profile(db, current_user.id)
    if not result:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found"
        )

    return ApiResponse.success(data=result)


@router.put("/me", response_model=UserProfileResponse)
async def update_my_profile(
    profile_data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新当前登录患者的个人资料"""
    async with transaction(db):
        result = await user_service.update_profile(
            db,
            current_user.id,
            profile_data.model_dump(exclude_unset=True)
        )
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="User not found"
            )

        return ApiResponse.success(data=result)
