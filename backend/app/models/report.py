from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Text, TIMESTAMP
from .base import BaseModel


class Report(BaseModel):
    """检查检验报告（含 AI 解读字段）"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True, index=True)
    type = Column(String(50), nullable=False, comment="报告类型：血常规、尿常规、X光等")
    content = Column(JSON, nullable=False, comment="报告内容（结构化 JSON 或纯文本）")
    ai_interpretation = Column(Text, nullable=True, comment="AI 解读结果")
    interpretation_status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending: 待解读, completed: 已完成, failed: 解读失败"
    )
    interpretation_at = Column(TIMESTAMP(timezone=True), nullable=True)
    referenced_chunks = Column(JSON, nullable=True, comment="引用的 knowledge_chunks.id 列表（可追溯性）")
