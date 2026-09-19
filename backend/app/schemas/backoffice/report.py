from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import EmailStr, Field


class ReportItem(BaseSchema):
    """一项结构化检验指标。"""
    name: str = Field(min_length=1, max_length=100)
    code: Optional[str] = Field(default=None, max_length=30)
    value: str = Field(min_length=1, max_length=100)
    unit: Optional[str] = Field(default=None, max_length=50)
    reference_range: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default=None, max_length=20)


class ReportContent(BaseSchema):
    """手工录入和 CSV 上传共用的报告内容格式。"""
    items: List[ReportItem] = Field(min_length=1, max_length=200)
    conclusion: Optional[str] = Field(default=None, max_length=2000)


class ReportCreate(BaseSchema):
    """
    检验科上传报告

    appointment_id 关联本次就诊，报告出来后医生才能凭其下诊断。
    当前业务只接受医生标记为“待检查结果”的就诊，不允许脱离就诊直接录入。
    """
    patient_id: int
    appointment_id: int
    type: str
    content: ReportContent


class ExamPendingAppointmentResponse(BaseSchema):
    """待检查就诊记录（检验科据此录入报告）"""
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    patient_email: Optional[str] = None
    department_name: Optional[str] = None
    doctor_name: Optional[str] = None
    appointment_time: datetime
    status: str
    report_count: int = 0


class ReportPatientResponse(BaseSchema):
    """检验检查人员选择报告归属患者时使用的最小患者信息。"""
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None


@add_padded_id()
class ReportResponse(BaseResponseSchema):
    """报告响应（检验科端）"""
    patient_id: int
    appointment_id: Optional[int] = None
    type: str
    content: Dict[str, Any]
    ai_interpretation: Optional[str] = None
    interpretation_status: str
    interpretation_at: Optional[datetime] = None
    referenced_chunks: Optional[List[int]] = None
    padded_id: Optional[str] = None
    # 关联数据（列表展示用）
    patient_name: Optional[str] = None
    patient_email: Optional[str] = None
