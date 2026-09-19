from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from typing import Optional


@add_padded_id()
class LLMCallLogResponse(BaseResponseSchema):
    """LLM 调用日志响应（后台监控端）"""
    agent_type: str
    prompt_hash: Optional[str] = None
    input_tokens: int
    output_tokens: int
    latency_ms: int
    status: str
    error_message: Optional[str] = None
    padded_id: Optional[str] = None
