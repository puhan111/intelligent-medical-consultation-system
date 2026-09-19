from sqlalchemy import Column, Integer, String, Text
from .base import BaseModel


class LLMCallLog(BaseModel):
    """LLM 调用日志（成本监控与可观测性）"""
    __tablename__ = "llm_call_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agent_type = Column(String(50), nullable=False, index=True, comment="triage / report_interpret")
    prompt_hash = Column(String(64), nullable=True, index=True, comment="prompt 内容 hash，用于缓存判断")
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, index=True, comment="success / error / timeout")
    error_message = Column(Text, nullable=True)
