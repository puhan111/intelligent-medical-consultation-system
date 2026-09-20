import asyncio
from types import SimpleNamespace

from app.services.common import rag_service


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
    assert [result.id for result in results] == [2, 1]
