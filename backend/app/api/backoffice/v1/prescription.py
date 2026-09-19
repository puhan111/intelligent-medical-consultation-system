from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from app.schemas.backoffice.prescription import PrescriptionCreate, PrescriptionResponse
from app.services.backoffice.prescription import prescription_service
from app.api.backoffice.deps import get_current_doctor_id, get_current_pharmacist
from app.models.admin import Admin
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator
from app.exceptions.http_exceptions import APIException


router = APIRouter()


@router.post("", response_model=PrescriptionResponse)
async def create_prescription(
    prescription_data: PrescriptionCreate,
    db: AsyncSession = Depends(get_db),
    doctor_id: int = Depends(get_current_doctor_id)
):
    """医生开处方"""
    async with transaction(db):
        result = await prescription_service.create_prescription(db, doctor_id, prescription_data)
        return ApiResponse.success(data=result)


@router.get("", response_model=list[PrescriptionResponse])
async def list_pending_prescriptions(
    page: int = 1,
    per_page: int = 10,
    db: AsyncSession = Depends(get_db),
    current_pharmacist: Admin = Depends(get_current_pharmacist)
):
    """获取待发药列表（药师）"""
    query = await prescription_service.get_pending_prescriptions_query(db)

    paginator = Paginator(query, db)
    result = await paginator.paginate(page, per_page)
    response_items = await prescription_service.list_prescriptions(db, result.items)

    return ApiResponse.success(data={
        "items": response_items,
        "total": result.total,
        "per_page": result.per_page,
        "current_page": result.current_page,
        "last_page": result.last_page,
        "has_more": result.has_more
    })


@router.post("/{prescription_id}/dispense", response_model=PrescriptionResponse)
async def dispense_prescription(
    prescription_id: int,
    db: AsyncSession = Depends(get_db),
    current_pharmacist: Admin = Depends(get_current_pharmacist)
):
    """药师发药"""
    async with transaction(db):
        result = await prescription_service.dispense_prescription(db, current_pharmacist.id, prescription_id)
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Prescription not found"
            )

        return ApiResponse.success(data=result)
