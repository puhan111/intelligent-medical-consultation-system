from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from typing import Optional
from datetime import datetime


class AppointmentCreate(BaseSchema):
    """患者创建预约"""
    doctor_id: int
    department_id: int
    appointment_time: datetime  # 预约时间（前端传入 ISO 8601 格式）


@add_padded_id()
class AppointmentResponse(BaseResponseSchema):
    """预约响应"""
    patient_id: int
    doctor_id: int
    department_id: int
    appointment_time: datetime
    status: str  # pending / confirmed / waiting_exam / completed / cancelled
    padded_id: Optional[str] = None
    # 关联数据（用于列表展示）
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None
