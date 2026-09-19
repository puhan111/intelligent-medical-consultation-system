from pydantic import Field
from typing import Optional, List
from ..base import BaseSchema


class TriageChatRequest(BaseSchema):
    """分诊对话请求"""
    message: str = Field(..., min_length=1, max_length=500, description="患者症状描述")
    session_id: Optional[str] = Field(None, description="会话ID，首次对话可为空，后续轮次必填")


class DepartmentRecommendation(BaseSchema):
    """推荐科室"""
    department_id: int
    department_name: str
    confidence: str = Field(..., description="推荐置信度：high/medium/low")


class TriageChatResponse(BaseSchema):
    """分诊对话响应"""
    session_id: str = Field(..., description="会话ID，客户端需在后续请求中携带")
    message: str = Field(..., description="AI回复内容")
    recommendations: List[DepartmentRecommendation] = Field(default_factory=list, description="推荐科室列表")
    turn_count: int = Field(..., description="当前对话轮次（从1开始）")
