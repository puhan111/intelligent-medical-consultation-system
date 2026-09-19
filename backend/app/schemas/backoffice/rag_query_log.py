from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from typing import List, Optional


@add_padded_id()
class RAGQueryLogResponse(BaseResponseSchema):
    """RAG 检索日志响应（后台监控端）"""
    agent_type: Optional[str] = None
    query: str
    top_k: int
    result_ids: List[int]
    latency_ms: int
    padded_id: Optional[str] = None
