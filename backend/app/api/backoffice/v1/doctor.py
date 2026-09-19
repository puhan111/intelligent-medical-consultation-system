from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from app.schemas.backoffice.doctor import DoctorCreate, DoctorResponse, DoctorUpdate
from app.services.backoffice.doctor import doctor_service
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator
from app.exceptions.http_exceptions import APIException


router = APIRouter()


@router.post("", response_model=DoctorResponse)
async def create_doctor(
    doctor_data: DoctorCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """创建医生（仅超级管理员）"""
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=403,
            message="Not enough permissions"
        )

    async with transaction(db):
        result = await doctor_service.create_doctor(db, doctor_data)
        return ApiResponse.success(data=result)


@router.get("", response_model=list[DoctorResponse])
async def list_doctors(
    page: int = 1,
    per_page: int = 10,
    department_id: int = None,
    title: str = None,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取医生列表（分页，仅超级管理员）"""
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=403,
            message="Not enough permissions"
        )

    query = await doctor_service.get_doctors_query(db, department_id=department_id, title=title)

    paginator = Paginator(query, db)
    result = await paginator.paginate(page, per_page)
    response_items = await doctor_service.list_doctors(db, result.items)

    return ApiResponse.success(data={
        "items": response_items,
        "total": result.total,
        "per_page": result.per_page,
        "current_page": result.current_page,
        "last_page": result.last_page,
        "has_more": result.has_more
    })


@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(
    doctor_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取医生详情（超级管理员或医生本人）"""
    result = await doctor_service.get_doctor(db, doctor_id)
    if not result:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Doctor not found"
        )

    if not current_admin.role == "superadmin" and current_admin.id != result.admin_id:
        raise APIException(
            status_code=403,
            message="Not enough permissions"
        )

    return ApiResponse.success(data=result)


@router.put("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(
    doctor_id: int,
    doctor_data: DoctorUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """更新医生信息（仅超级管理员）"""
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=403,
            message="Not enough permissions"
        )

    async with transaction(db):
        result = await doctor_service.update_doctor(db, doctor_id, doctor_data.model_dump(exclude_unset=True))
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Doctor not found"
            )

        return ApiResponse.success(data=result)


@router.delete("/{doctor_id}")
async def delete_doctor(
    doctor_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """删除医生（仅超级管理员）"""
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=403,
            message="Not enough permissions"
        )

    async with transaction(db):
        result = await doctor_service.delete_doctor(db, doctor_id)
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Doctor not found"
            )

        return ApiResponse.success_without_data()
