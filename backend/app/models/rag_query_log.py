from sqlalchemy import Column, Integer, String, Text, JSON
from .base import BaseModel


class RAGQueryLog(BaseModel):
    """RAG 检索日志（检索质量监控）"""
    __tablename__ = "rag_query_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agent_type = Column(
        String(50),
        nullable=True,
        index=True,
        comment="triage / report_interpret / report_followup",
    )
    query = Column(Text, nullable=False)
    top_k = Column(Integer, nullable=False)
    result_ids = Column(JSON, nullable=False, comment="返回的 knowledge_chunks.id 列表")
    latency_ms = Column(Integer, nullable=False)
