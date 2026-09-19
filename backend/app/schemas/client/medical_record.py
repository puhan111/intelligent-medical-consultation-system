from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from typing import Optional


@add_padded_id()
class MedicalRecordResponse(BaseResponseSchema):
    """病历响应（患者端）"""
    appointment_id: int
    doctor_id: int
    diagnosis: str
    content: Optional[str] = None
    padded_id: Optional[str] = None
    doctor_name: Optional[str] = None
