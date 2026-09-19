from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from typing import Optional, Any, Dict, List
from datetime import datetime


class AppointmentUpdate(BaseSchema):
    """医生更新预约状态（确认接诊 / 开检查等结果 / 完成接诊）"""
    status: str  # confirmed / waiting_exam / completed


class AppointmentReportSummary(BaseSchema):
    """就诊关联的检查报告摘要（医生端列表与病历录入时参考）"""
    id: int
    type: str
    content: Dict[str, Any]
    ai_interpretation: Optional[str] = None
    interpretation_status: str
    created_at: datetime


@add_padded_id()
class AppointmentResponse(BaseResponseSchema):
    """预约响应（医生端，含患者信息与检查报告状态）"""
    patient_id: int
    doctor_id: int
    department_id: int
    appointment_time: datetime
    status: str
    padded_id: Optional[str] = None
    patient_name: Optional[str] = None
    department_name: Optional[str] = None
    # 本次就诊已出的检查报告数量，医生据此判断能否继续诊断
    report_count: int = 0
    reports: List[AppointmentReportSummary] = []
