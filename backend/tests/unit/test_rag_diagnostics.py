import asyncio
from types import SimpleNamespace

from app.services.common import rag_service
from app.models.knowledge_chunk import KnowledgeChunk


def test_fulltext_query_uses_distinct_or_terms():
    query = rag_service._build_fulltext_web_query("成人组XQ-9指标的复查标签是什么？成人组")

    terms = query.split(" OR ")
    assert "成人" in terms
    assert "XQ" in terms
    assert "9" in terms
    assert "复查" in terms
    assert "标签" in terms
    assert "-" not in terms
    assert "？" not in terms
    assert len(terms) == len(set(terms))


def test_rerank_uses_default_or_configured_endpoint(monkeypatch):
    calls = []

    def rerank_call(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            status_code=200,
            output={
                "results": [
                    {"index": 1, "relevance_score": 0.9},
                    {"index": 0, "relevance_score": 0.4},
                ]
            },
        )

    monkeypatch.setattr(rag_service.dashscope.TextReRank, "call", rerank_call)

    monkeypatch.setattr(rag_service.settings, "DASHSCOPE_RERANK_BASE_URL", "")
    assert rag_service._rerank.__wrapped__("query", ["a", "b"]) == [1, 0]
    assert "base_address" not in calls[-1]

    custom_endpoint = "https://workspace.example/api/v1"
    monkeypatch.setattr(
        rag_service.settings,
        "DASHSCOPE_RERANK_BASE_URL",
        custom_endpoint,
    )
    assert rag_service._rerank.__wrapped__("query", ["a", "b"]) == [1, 0]
    assert calls[-1]["base_address"] == custom_endpoint


def test_search_diagnostics_preserve_each_ranking_stage(monkeypatch):
    chunks = {
        chunk_id: SimpleNamespace(
            id=chunk_id,
            source=f"doc-{chunk_id}",
            content=f"content-{chunk_id}",
            metadata={"source_type": "医学参考资料"},
        )
        for chunk_id in (1, 2, 3)
    }

    monkeypatch.setattr(rag_service, "_embed", lambda _query: [0.1, 0.2])

    async def vector_search(*_args, **_kwargs):
        return [chunks[1], chunks[2]]

    async def fulltext_search(*_args, **_kwargs):
        return [chunks[2], chunks[3]]

    monkeypatch.setattr(rag_service, "_vector_search", vector_search)
    monkeypatch.setattr(rag_service, "_fulltext_search", fulltext_search)
    diagnostics = {}

    results = asyncio.run(
        rag_service.search(
            db=object(),
            query="测试问题",
            top_k=2,
            source_type="医学参考资料",
            log_query=False,
            diagnostics=diagnostics,
        )
    )

    assert diagnostics["vector_ranked_ids"] == [1, 2]
    assert diagnostics["fulltext_ranked_ids"] == [2, 3]
    assert diagnostics["rrf_ranked_ids"] == [2, 1, 3]
    assert diagnostics["final_result_ids"] == [2, 1]
    assert diagnostics["embedding_latency_ms"] >= 0
    assert diagnostics["vector_search_latency_ms"] >= 0
    assert diagnostics["fulltext_search_latency_ms"] >= 0
    assert "rerank_latency_ms" not in diagnostics
    assert diagnostics["latency_ms"] >= sum(
        diagnostics[key]
        for key in (
            "embedding_latency_ms",
            "vector_search_latency_ms",
            "fulltext_search_latency_ms",
        )
    )
    assert [result.id for result in results] == [2, 1]


def test_search_reads_metadata_from_real_orm_attribute(monkeypatch):
    chunk = KnowledgeChunk(
        id=7,
        source="orm-source",
        content="orm-content",
        embedding=[0.1, 0.2],
        chunk_metadata={"source_type": "医学参考资料"},
    )
    monkeypatch.setattr(rag_service, "_embed", lambda _query: [0.1, 0.2])

    async def vector_search(*_args, **_kwargs):
        return [chunk]

    async def fulltext_search(*_args, **_kwargs):
        return []

    monkeypatch.setattr(rag_service, "_vector_search", vector_search)
    monkeypatch.setattr(rag_service, "_fulltext_search", fulltext_search)

    results = asyncio.run(
        rag_service.search(db=object(), query="医学", top_k=1, log_query=False)
    )

    assert results[0].chunk_metadata == {"source_type": "医学参考资料"}


def test_search_diagnostics_record_rerank_latency(monkeypatch):
    chunks = [
        SimpleNamespace(
            id=chunk_id,
            source=f"doc-{chunk_id}",
            content=f"content-{chunk_id}",
            metadata={"source_type": "医学参考资料"},
        )
        for chunk_id in (1, 2)
    ]

    monkeypatch.setattr(rag_service, "_embed", lambda _query: [0.1, 0.2])
    monkeypatch.setattr(rag_service, "_rerank", lambda _query, _documents: [1, 0])

    async def vector_search(*_args, **_kwargs):
        return chunks

    async def fulltext_search(*_args, **_kwargs):
        return []

    monkeypatch.setattr(rag_service, "_vector_search", vector_search)
    monkeypatch.setattr(rag_service, "_fulltext_search", fulltext_search)
    diagnostics = {}

    results = asyncio.run(
        rag_service.search(
            db=object(),
            query="测试问题",
            top_k=2,
            source_type="医学参考资料",
            rerank=True,
            log_query=False,
            diagnostics=diagnostics,
        )
    )

    assert diagnostics["rerank_applied"] is True
    assert diagnostics["rerank_fallback"] is False
    assert diagnostics["rerank_latency_ms"] >= 0
    assert diagnostics["final_result_ids"] == [2, 1]
    assert [result.id for result in results] == [2, 1]


def test_search_diagnostics_record_rerank_fallback_reason(monkeypatch, caplog):
    chunk = SimpleNamespace(
        id=1,
        source="doc-1",
        content="content-1",
        metadata={"source_type": "医学参考资料"},
    )

    monkeypatch.setattr(rag_service, "_embed", lambda _query: [0.1, 0.2])

    def rerank_failure(*_args, **_kwargs):
        raise PermissionError("private-provider-detail")

    monkeypatch.setattr(rag_service, "_rerank", rerank_failure)

    async def vector_search(*_args, **_kwargs):
        return [chunk]

    async def fulltext_search(*_args, **_kwargs):
        return []

    monkeypatch.setattr(rag_service, "_vector_search", vector_search)
    monkeypatch.setattr(rag_service, "_fulltext_search", fulltext_search)
    diagnostics = {}

    results = asyncio.run(
        rag_service.search(
            db=object(),
            query="private-patient-question",
            top_k=1,
            rerank=True,
            log_query=False,
            diagnostics=diagnostics,
        )
    )

    assert diagnostics["rerank_applied"] is False
    assert diagnostics["rerank_fallback"] is True
    assert diagnostics["rerank_error_type"] == "PermissionError"
    assert diagnostics["rerank_error_message"] == "private-provider-detail"
    assert "PermissionError" in caplog.text
    assert "private-patient-question" not in caplog.text
    assert "private-provider-detail" not in caplog.text
    assert [result.id for result in results] == [1]
