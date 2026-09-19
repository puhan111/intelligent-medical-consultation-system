import logging

from fastapi import APIRouter, Depends
from kombu.exceptions import OperationalError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.knowledge_chunk import KnowledgeChunk
from app.schemas.backoffice.knowledge_chunk import (
    KnowledgeLibraryResponse,
    KnowledgeUploadRequest,
)
from app.schedule.jobs.knowledge_embed import execute as knowledge_embed_execute
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.schemas.response import ApiResponse
from app.exceptions.http_exceptions import APIException


router = APIRouter()
logger = logging.getLogger(__name__)
KNOWLEDGE_SOURCE_TYPES = ("分诊指引", "医学参考资料")


def _enqueue_knowledge_embedding(upload_data: KnowledgeUploadRequest):
    """Publish the task, recovering once from a stale broker connection."""
    task_kwargs = {
        "content": upload_data.content,
        "source": upload_data.source,
        "source_type": upload_data.source_type,
    }
    publish_options = {
        "queue": "celery",
        "retry": True,
        "retry_policy": {
            "max_retries": 3,
            "interval_start": 0,
            "interval_step": 0.5,
            "interval_max": 1,
        },
    }

    try:
        return knowledge_embed_execute.apply_async(
            kwargs=task_kwargs,
            **publish_options,
        )
    except OperationalError:
        # A Redis container restart can leave a dead connection in Kombu's
        # process-level pool. Drop it before one final publish attempt.
        knowledge_embed_execute.app.close()
        return knowledge_embed_execute.apply_async(
            kwargs=task_kwargs,
            **publish_options,
        )


@router.get("", response_model=KnowledgeLibraryResponse)
async def list_knowledge_documents(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """List vectorized knowledge grouped by type and source document."""
    if current_admin.role != "superadmin":
        raise APIException(status_code=403, message="Not enough permissions")

    source_type = KnowledgeChunk.chunk_metadata["source_type"].as_string()
    result = await db.execute(
        select(
            source_type.label("source_type"),
            KnowledgeChunk.source,
            func.count(KnowledgeChunk.id).label("chunk_count"),
            func.min(KnowledgeChunk.created_at).label("created_at"),
            func.max(KnowledgeChunk.created_at).label("updated_at"),
        )
        .where(source_type.in_(KNOWLEDGE_SOURCE_TYPES))
        .group_by(source_type, KnowledgeChunk.source)
        .order_by(source_type, func.max(KnowledgeChunk.created_at).desc())
    )

    grouped = {category: [] for category in KNOWLEDGE_SOURCE_TYPES}
    for row in result:
        grouped[row.source_type].append(
            {
                "source": row.source,
                "chunk_count": row.chunk_count,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    categories = [
        {
            "source_type": category,
            "document_count": len(documents),
            "chunk_count": sum(item["chunk_count"] for item in documents),
            "documents": documents,
        }
        for category, documents in grouped.items()
    ]

    return ApiResponse.success(
        data={
            "document_count": sum(item["document_count"] for item in categories),
            "chunk_count": sum(item["chunk_count"] for item in categories),
            "categories": categories,
        }
    )
@router.post("")
async def upload_knowledge(
    upload_data: KnowledgeUploadRequest,
    current_admin: Admin = Depends(get_current_admin)
):
    """上传知识库文档，异步触发切分+向量化+入库（仅超级管理员）"""
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=403,
            message="Not enough permissions"
        )

    try:
        _enqueue_knowledge_embedding(upload_data)
    except OperationalError as exc:
        logger.exception("Failed to enqueue knowledge embedding task")
        raise APIException(
            code=1005,
            message="Task queue unavailable, please retry later",
            status_code=503,
        ) from exc

    return ApiResponse.success_without_data()
