import asyncio
import logging
from app.core.celery_app import celery_app
from sqlalchemy import func
from app.db.base import create_scheduler_engine, create_scheduler_session_factory
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.common.chunking_service import chunk_document
from app.services.common.tokenizer import segment
from app.services.common.rag_service import _embed

logger = logging.getLogger("knowledge_embed")


@celery_app.task(name="app.schedule.jobs.knowledge_embed.execute")
def execute(content: str, source: str, source_type: str):
    """
    知识库导入任务：切分 -> 向量化 -> 写入 knowledge_chunks（含全文检索列）

    Args:
        content: 文档全文（Markdown 格式）
        source: 原文档标题/路径
        source_type: 分诊指引 / 医学参考资料
    """
    logger.info(f"=== KNOWLEDGE EMBED TASK STARTED: source={source} ===")

    scheduler_engine = create_scheduler_engine()
    SchedulerSessionLocal = create_scheduler_session_factory(scheduler_engine)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        succeeded, failed = loop.run_until_complete(
            _embed_and_store(SchedulerSessionLocal, content, source, source_type)
        )
        logger.info(f"=== KNOWLEDGE EMBED TASK COMPLETED: succeeded={succeeded} failed={failed} ===")
        return {"status": "success", "succeeded": succeeded, "failed": failed}
    except Exception as e:
        logger.error(f"Knowledge embed task failed for source={source}: {e}", exc_info=True)
        raise
    finally:
        loop.run_until_complete(scheduler_engine.dispose())
        loop.close()


async def _embed_and_store(session_factory, content: str, source: str, source_type: str) -> tuple:
    """对切分后的每个 chunk 调用 embedding，写入 chunks（跳过单个失败的 chunk，不影响整体）"""
    pieces = chunk_document(content, source, source_type)

    succeeded = 0
    failed = 0
    async with session_factory() as session:
        for piece in pieces:
            try:
                vector = _embed(piece["content"])
                # content_tsv 是 tsvector 类型，Postgres 无法从纯文本隐式转换，需用 to_tsvector 表达式
                chunk = KnowledgeChunk(
                    source=source,
                    content=piece["content"],
                    embedding=vector,
                    chunk_metadata=piece["metadata"],
                    content_tsv=func.to_tsvector("simple", segment(piece["content"])),
                )
                session.add(chunk)
                succeeded += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to embed chunk for source={source}: {e}", exc_info=True)

        await session.commit()

    return succeeded, failed
