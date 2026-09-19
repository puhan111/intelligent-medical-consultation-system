import asyncio
import logging
import time
from typing import List, Optional
import dashscope
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.db.base import create_scheduler_engine, create_scheduler_session_factory
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.rag_query_log import RAGQueryLog
from app.services.common.ranking import reciprocal_rank_fusion
from app.services.common.tokenizer import segment

logger = logging.getLogger("rag_service")

dashscope.api_key = settings.DASHSCOPE_API_KEY

class ChunkResult:
    def __init__(self, id: int, source: str, content: str, chunk_metadata: Optional[dict], score: float):
        self.id = id
        self.source = source
        self.content = content
        self.chunk_metadata = chunk_metadata
        self.score = score


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def _embed(text_input: str) -> List[float]:
    """调用 DashScope embedding API 将文本转为向量，tenacity 指数退避重试最多 3 次"""
    response = dashscope.TextEmbedding.call(
        model=settings.DASHSCOPE_EMBEDDING_MODEL,
        input=text_input,
    )
    if response.status_code != 200:
        raise RuntimeError(f"DashScope embedding failed: {response.code} {response.message}")
    return response.output["embeddings"][0]["embedding"]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def _rerank(query: str, documents: List[str]) -> List[int]:
    """
    调用 DashScope gte-rerank-v2 对候选文档重排，返回按相关性降序排列的原始索引列表
    rerank 模型走业务空间专属 endpoint，与 embedding 使用的默认 endpoint 不同
    """
    response = dashscope.TextReRank.call(
        model=settings.DASHSCOPE_RERANK_MODEL,
        query=query,
        documents=documents,
        base_address=settings.DASHSCOPE_RERANK_BASE_URL,
    )
    if response.status_code != 200:
        raise RuntimeError(f"DashScope rerank failed: {response.code} {response.message}")
    ranked = sorted(response.output["results"], key=lambda r: r["relevance_score"], reverse=True)
    return [r["index"] for r in ranked]


async def _vector_search(db: AsyncSession, query_vector: List[float], candidate_n: int, source_type: Optional[str]):
    """pgvector 余弦距离检索候选池，返回按距离升序排列的 (chunk, rank) 列表"""
    stmt = select(KnowledgeChunk)
    if source_type:
        stmt = stmt.where(KnowledgeChunk.chunk_metadata["source_type"].as_string() == source_type)
    stmt = stmt.order_by(KnowledgeChunk.embedding.cosine_distance(query_vector)).limit(candidate_n)

    result = await db.execute(stmt)
    return result.scalars().all()


async def _fulltext_search(db: AsyncSession, query: str, candidate_n: int, source_type: Optional[str]):
    """Postgres 全文检索候选池（jieba 分词 + plainto_tsquery），按相关性排序"""
    segmented_query = segment(query)
    if not segmented_query:
        return []

    sql = """
        SELECT id, source, content, metadata
        FROM knowledge_chunks
        WHERE content_tsv @@ plainto_tsquery('simple', :query)
    """
    params = {"query": segmented_query, "limit": candidate_n}
    if source_type:
        sql += " AND metadata->>'source_type' = :source_type"
        params["source_type"] = source_type
    sql += " ORDER BY ts_rank(content_tsv, plainto_tsquery('simple', :query)) DESC LIMIT :limit"

    result = await db.execute(text(sql), params)
    return result.fetchall()


async def search(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    source_type: Optional[str] = None,
    rerank: bool = False,
    agent_type: Optional[str] = None,
    log_query: bool = True,
    diagnostics: Optional[dict] = None,
) -> List[ChunkResult]:
    """
    混合检索：向量检索 + 全文检索，RRF 融合排序，可选 rerank 精排

    Args:
        db: 数据库会话
        query: 查询词
        top_k: 最终返回结果数
        source_type: 按 分诊指引/医学参考资料 过滤
        rerank: 是否调用 DashScope gte-rerank 对候选池重排（候选池会放大以提升重排效果）
        agent_type: 调用方 Agent 类型，用于 RAG 可观测性归属
        log_query: 是否写入 RAG 查询日志；离线对比评测时可关闭，避免污染线上监控
        diagnostics: 可选的诊断信息输出字典，供离线评测识别 Rerank 成功或降级
    """
    start = time.monotonic()

    candidate_n = 20 if rerank else max(top_k, 10)
    if diagnostics is not None:
        diagnostics.clear()
        diagnostics.update({
            "rerank_requested": rerank,
            "rerank_applied": False,
            "rerank_fallback": False,
            "candidate_n": candidate_n,
        })
    # DashScope SDK 是同步接口，放入线程池，避免阻塞 FastAPI 事件循环。
    query_vector = await asyncio.to_thread(_embed, query)

    vector_chunks = await _vector_search(db, query_vector, candidate_n, source_type)
    fulltext_rows = await _fulltext_search(db, query, candidate_n, source_type)

    chunk_map = {c.id: c for c in vector_chunks}
    for row in fulltext_rows:
        if row.id not in chunk_map:
            chunk_map[row.id] = row

    vector_ranked_ids = [c.id for c in vector_chunks]
    fulltext_ranked_ids = [row.id for row in fulltext_rows]
    fused_ids, scores = reciprocal_rank_fusion(
        vector_ranked_ids,
        fulltext_ranked_ids,
    )

    if rerank and fused_ids:
        candidates = [chunk_map[cid] for cid in fused_ids]
        documents = [c.content for c in candidates]
        try:
            rerank_order = await asyncio.to_thread(_rerank, query, documents)
            final_chunks = [candidates[i] for i in rerank_order[:top_k]]
            if diagnostics is not None:
                diagnostics["rerank_applied"] = True
        except Exception:
            # Rerank 是精排增强层，不应因其不可用让整个 RAG 和 Agent 失败。
            logger.warning(
                "Rerank failed, falling back to RRF results: query=%r",
                query,
                exc_info=True,
            )
            final_chunks = [chunk_map[cid] for cid in fused_ids[:top_k]]
            if diagnostics is not None:
                diagnostics["rerank_fallback"] = True
    else:
        final_chunks = [chunk_map[cid] for cid in fused_ids[:top_k]]

    results = [
        ChunkResult(
            id=c.id,
            source=c.source,
            content=c.content,
            # KnowledgeChunk ORM 实例用 chunk_metadata 属性访问；declarative Base 自带 .metadata
            # 指向 SQLAlchemy 的 MetaData 对象，不能用来判断分支，因此这里用 isinstance 区分
            chunk_metadata=c.chunk_metadata if isinstance(c, KnowledgeChunk) else c.metadata,
            score=scores.get(c.id, 0.0)
        )
        for c in final_chunks
    ]

    latency_ms = int((time.monotonic() - start) * 1000)
    if diagnostics is not None:
        diagnostics.update({
            "candidate_count": len(fused_ids),
            "result_count": len(results),
            "latency_ms": latency_ms,
        })
    if log_query:
        _log_query_async(query, top_k, [r.id for r in results], latency_ms, agent_type)

    return results


def _log_query_async(
    query: str,
    top_k: int,
    result_ids: List[int],
    latency_ms: int,
    agent_type: Optional[str],
) -> None:
    """异步 fire-and-forget 写入 rag_query_logs，不阻塞检索响应"""
    asyncio.create_task(_write_query_log(query, top_k, result_ids, latency_ms, agent_type))


async def _write_query_log(
    query: str,
    top_k: int,
    result_ids: List[int],
    latency_ms: int,
    agent_type: Optional[str],
) -> None:
    engine = create_scheduler_engine()
    session_factory = create_scheduler_session_factory(engine)
    try:
        async with session_factory() as session:
            session.add(RAGQueryLog(
                agent_type=agent_type,
                query=query,
                top_k=top_k,
                result_ids=result_ids,
                latency_ms=latency_ms,
            ))
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to write rag_query_log: {e}", exc_info=True)
    finally:
        await engine.dispose()
