from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from datetime import datetime
from typing import Optional, Dict, Any, List


class KnowledgeChunkCreate(BaseSchema):
    source: str
    content: str
    source_type: Optional[str] = None  # 分诊指引 / 医学参考资料


@add_padded_id()
class KnowledgeChunkResponse(BaseResponseSchema):
    """知识片段响应（后台管理端）"""
    source: str
    content: str
    chunk_metadata: Optional[Dict[str, Any]] = None
    padded_id: Optional[str] = None


class KnowledgeUploadRequest(BaseSchema):
    """知识库文档上传请求（触发 Celery 异步 embedding）"""
    source: str
    content: str
    source_type: str  # 分诊指引 / 医学参考资料


class KnowledgeDocumentResponse(BaseSchema):
    """A vectorized document grouped from its stored chunks."""

    source: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class KnowledgeCategoryResponse(BaseSchema):
    source_type: str
    document_count: int
    chunk_count: int
    documents: List[KnowledgeDocumentResponse]


class KnowledgeLibraryResponse(BaseSchema):
    document_count: int
    chunk_count: int
    categories: List[KnowledgeCategoryResponse]
