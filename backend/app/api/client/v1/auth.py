from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.client.auth import Token, Login, Register, RefreshToken, Logout
from app.services.client.auth import client_auth_service
from app.schemas.response import ApiResponse

router = APIRouter()


@router.post("/register")
async def register(
    register_data: Register,
    db: AsyncSession = Depends(get_db)
):
    """患者注册，注册即激活账户"""
    result = await client_auth_service.register(
        db,
        register_data.email,
        register_data.password,
        register_data.first_name,
        register_data.last_name,
    )
    return ApiResponse.success(data=result)


@router.post("/login", response_model=Token)
async def login(
    login_data: Login,
    db: AsyncSession = Depends(get_db)
):
    """患者登录"""
    result = await client_auth_service.login(db, login_data.email, login_data.password)
    return ApiResponse.success(data=result)


@router.post("/refresh", response_model=Token)
async def refresh(
    request: RefreshToken,
    db: AsyncSession = Depends(get_db)
):
    """刷新患者 token"""
    result = await client_auth_service.refresh_token(db, request.refresh_token)
    return ApiResponse.success(data=result)


@router.post("/logout")
async def logout(
    request: Logout,
    db: AsyncSession = Depends(get_db),
):
    """患者登出"""
    await client_auth_service.logout(db, request.refresh_token)
    return ApiResponse.success_without_data()
