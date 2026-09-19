from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from app.schemas.backoffice.medical_record import MedicalRecordCreate, MedicalRecordResponse
from app.services.backoffice.medical_record import medical_record_service
from app.api.backoffice.deps import get_current_doctor_id
from app.schemas.response import ApiResponse


router = APIRouter()


@router.post("", response_model=MedicalRecordResponse)
async def create_medical_record(
    record_data: MedicalRecordCreate,
    db: AsyncSession = Depends(get_db),
    doctor_id: int = Depends(get_current_doctor_id)
):
    """医生录入病历"""
    async with transaction(db):
        result = await medical_record_service.create_medical_record(db, doctor_id, record_data)
        return ApiResponse.success(data=result)
