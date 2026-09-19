from sqlalchemy import Column, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector
from .base import BaseModel


class KnowledgeChunk(BaseModel):
    """知识片段（RAG 检索用）"""
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source = Column(String(500), nullable=False, comment="来源文档路径或标题")
    content = Column(Text, nullable=False, comment="知识片段文本内容")
    embedding = Column(Vector(1024), nullable=False, comment="DashScope text-embedding-v3 向量（该模型输出维度为 1024）")
    chunk_metadata = Column(
        "metadata",
        JSON,
        nullable=True,
        comment="额外元数据：source_type(分诊指引/医学参考资料)、章节标题等"
    )
    content_tsv = Column(TSVECTOR, nullable=True, comment="全文检索列，混合检索用")
