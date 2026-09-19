from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from app.schemas.backoffice.appointment import AppointmentResponse, AppointmentUpdate
from app.services.backoffice.appointment import appointment_service
from app.api.backoffice.deps import get_current_doctor_id
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator
from app.exceptions.http_exceptions import APIException


router = APIRouter()


@router.get("", response_model=list[AppointmentResponse])
async def list_appointments(
    page: int = 1,
    per_page: int = 10,
    status_filter: str = None,
    db: AsyncSession = Depends(get_db),
    doctor_id: int = Depends(get_current_doctor_id)
):
    """获取待接诊列表（医生本人）"""
    query = await appointment_service.get_doctor_appointments_query(db, doctor_id, status_filter)

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


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    update_data: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    doctor_id: int = Depends(get_current_doctor_id)
):
    """医生更新预约状态（确认接诊/等待检查结果/完成接诊）"""
    async with transaction(db):
        result = await appointment_service.update_appointment_status(db, doctor_id, appointment_id, update_data)
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Appointment not found"
            )

        return ApiResponse.success(data=result)
