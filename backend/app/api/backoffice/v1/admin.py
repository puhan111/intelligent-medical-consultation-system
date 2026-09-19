from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from app.schemas.backoffice.admin import AdminCreate, AdminResponse, AdminUpdate, AdminChangePassword, ResetPassword
from app.services.backoffice.admin import admin_service
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator
from typing import List
from app.exceptions.http_exceptions import APIException


router = APIRouter()


@router.post("", response_model=AdminResponse)
async def create_admin(
    admin_data: AdminCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """创建新管理员（仅超级管理员）"""
    # 验证当前管理员是否为超级管理员
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=400,
            message="Not enough permissions"
        )

    async with transaction(db):
        result = await admin_service.create_admin(db, admin_data)
        return ApiResponse.success(data=result)


@router.get("", response_model=List[AdminResponse])
async def list_admins(
    page: int = 1,
    per_page: int = 10,
    email: str = None,
    sort_by: str = None,
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取所有管理员列表（仅超级管理员）

    Args:
        page: 页码，从 1 开始
        per_page: 每页条数
        email: 可选的邮箱过滤条件
        sort_by: 排序字段，支持 email 或 created_at
        sort_order: 排序方向，asc 或 desc
    """
    # 验证当前管理员是否为超级管理员
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=400,
            message="Not enough permissions"
        )
    
    query = await admin_service.get_admins_query(db, email=email, sort_by=sort_by, sort_order=sort_order)

    paginator = Paginator(query, db)
    result = await paginator.paginate(page, per_page)
    result = result.map(AdminResponse)
        
    return result.response()


@router.get("/{admin_id}", response_model=AdminResponse)
async def get_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取管理员详情（仅超级管理员或管理员本人）"""
    # 验证权限：超级管理员可查看任意管理员，普通管理员仅可查看自己
    if not current_admin.role == "superadmin" and current_admin.id != admin_id:
        raise APIException(
            status_code=403,
            message="Not enough permissions"
        )
    
    result = await admin_service.get_admin(db, admin_id)
    if not result:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Admin not found"
        )

    return ApiResponse.success(data=result)


@router.put("/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: int,
    admin_data: AdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """更新管理员信息（仅超级管理员或管理员本人）"""
    # 验证权限：超级管理员可更新任意管理员，普通管理员仅可更新自己
    if not current_admin.role == "superadmin" and current_admin.id != admin_id:
        raise APIException(
            status_code=403,
            message="Not enough permissions"
        )

    async with transaction(db):
        result = await admin_service.update_admin(db, admin_id, admin_data.model_dump(exclude_unset=True))
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Admin not found"
            )

        return ApiResponse.success_without_data()


@router.delete("/{admin_id}")
async def delete_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """删除管理员（仅超级管理员）"""
    # 验证当前管理员是否为超级管理员
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=403,
            message="Not enough permissions"
        )

    # 不能删除自己
    if current_admin.id == admin_id:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot delete yourself"
        )

    async with transaction(db):
        result = await admin_service.delete_admin(db, admin_id)
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Admin not found"
            )

        return ApiResponse.success_without_data()


@router.post("/{admin_id}/change-password")
async def change_password(
    admin_id: int,
    password_data: AdminChangePassword,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """修改管理员密码（仅管理员本人）"""
    # 只能修改自己的密码
    if current_admin.id != admin_id:
        raise APIException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Can only change your own password"
        )

    async with transaction(db):
        result = await admin_service.change_password(
            db,
            admin_id,
            password_data.current_password,
            password_data.new_password
        )

        return ApiResponse.success_without_data()


@router.post("/{admin_id}/reset-password")
async def reset_password(
    admin_id: int,
    password_data: ResetPassword,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """重置管理员密码（仅管理员本人和超级管理员）"""
    # 只能修改自己的密码
    if current_admin.role != "superadmin" and current_admin.id != admin_id:
        raise APIException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Can only change your own password"
        )

    async with transaction(db):
        result = await admin_service.reset_password(
            db,
            admin_id,
            password_data.password
        )

        return ApiResponse.success_without_data()
