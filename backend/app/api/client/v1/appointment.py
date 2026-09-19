from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from app.schemas.client.appointment import AppointmentCreate, AppointmentResponse
from app.services.client.appointment import appointment_service
from app.api.client.deps import get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator
from app.exceptions.http_exceptions import APIException


router = APIRouter()


@router.post("", response_model=AppointmentResponse)
async def create_appointment(
    appointment_data: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """患者创建预约"""
    async with transaction(db):
        result = await appointment_service.create_appointment(db, current_user.id, appointment_data)
        return ApiResponse.success(data=result)


@router.get("", response_model=list[AppointmentResponse])
async def list_my_appointments(
    page: int = 1,
    per_page: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的预约列表（分页）"""
    query = await appointment_service.get_my_appointments_query(db, current_user.id)

    paginator = Paginator(query, db)
    result = await paginator.paginate(page, per_page)
    response_items = await appointment_service.list_appointments(db, result.items)

    return ApiResponse.success(data={
        "items": response_items,
        "total": result.total,
        "per_page": result.per_page,
        "current_page": result.current_page,
        "last_page": result.last_page,
        "has_more": result.has_more
    })


@router.delete("/{appointment_id}")
async def cancel_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """取消预约"""
    async with transaction(db):
        result = await appointment_service.cancel_appointment(db, current_user.id, appointment_id)
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Appointment not found"
            )

        return ApiResponse.success_without_data()
