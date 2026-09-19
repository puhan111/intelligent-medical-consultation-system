from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from typing import Optional


class MedicalRecordCreate(BaseSchema):
    """医生录入病历"""
    appointment_id: int
    diagnosis: str
    content: Optional[str] = None


@add_padded_id()
class MedicalRecordResponse(BaseResponseSchema):
    """病历响应（医生端）"""
    appointment_id: int
    patient_id: int
    doctor_id: int
    diagnosis: str
    content: Optional[str] = None
    padded_id: Optional[str] = None
    patient_name: Optional[str] = None
