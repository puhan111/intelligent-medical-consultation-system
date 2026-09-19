from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from pydantic import Field
from typing import Optional, Any, Dict
from datetime import datetime


class ReportChatRequest(BaseSchema):
    """报告追问请求"""
    message: str = Field(..., min_length=1, max_length=500, description="患者的追问内容")
    session_id: Optional[str] = Field(None, description="会话ID，首轮可为空，后续轮次必填")


class ReportChatResponse(BaseSchema):
    """报告追问响应"""
    session_id: str
    message: str
    turn_count: int


@add_padded_id()
class ReportResponse(BaseResponseSchema):
    """报告响应（患者端，含 AI 解读）"""
    appointment_id: Optional[int] = None
    type: str
    content: Dict[str, Any]
    ai_interpretation: Optional[str] = None
    interpretation_status: str
    interpretation_at: Optional[datetime] = None
    padded_id: Optional[str] = None
