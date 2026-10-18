import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.services.common import rag_service
from app.services.backoffice import rag_evaluation
from scripts import eval_rag_retrieval


@pytest.mark.parametrize("corpus, excluded", [("business", True), ("evaluation", False)])
def test_vector_candidates_filter_evaluation_sources_before_limit(corpus, excluded):
    class Database:
        async def execute(self, statement):
            self.statement = statement
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))

    db = Database()
    asyncio.run(rag_service._vector_search(db, [0.0] * 1024, 10, "医学参考资料", corpus))
    compiled = db.statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert ("NOT LIKE" in sql) is excluded
    assert "LIKE" in sql
    assert "rag-eval://" in compiled.params.values()
    assert "医学参考资料" in compiled.params.values()
    assert sql.index("LIKE") < sql.index("LIMIT")


@pytest.mark.parametrize("corpus, operator", [("business", "NOT LIKE"), ("evaluation", "LIKE")])
def test_fulltext_candidates_filter_evaluation_sources_before_limit(corpus, operator):
    class Database:
        async def execute(self, statement, params):
            self.sql, self.params = str(statement), params
            return SimpleNamespace(fetchall=lambda: [])

    db = Database()
    asyncio.run(rag_service._fulltext_search(db, "Orion 确认码", 10, "医学参考资料", corpus))
    assert f"source {operator} :evaluation_prefix" in db.sql
    assert db.params["evaluation_prefix"] == "rag-eval://%"
    assert db.params["source_type"] == "医学参考资料"
    assert db.sql.index("evaluation_prefix") < db.sql.index("LIMIT")


@pytest.mark.parametrize("corpus", [None, "evaluation"])
def test_search_defaults_to_business_and_passes_explicit_evaluation_scope(monkeypatch, corpus):
    seen = []

    async def candidates(db, query, candidate_n, source_type, selected_corpus):
        seen.append(selected_corpus)
        return []

    monkeypatch.setattr(rag_service, "_embed", lambda _: [0.0] * 1024)
    monkeypatch.setattr(rag_service, "_vector_search", candidates)
    monkeypatch.setattr(rag_service, "_fulltext_search", candidates)
    kwargs = {} if corpus is None else {"corpus": corpus}
    diagnostics = {}
    result = asyncio.run(rag_service.search(
        object(), "测试", log_query=False, diagnostics=diagnostics, **kwargs,
    ))
    assert result == []
    assert seen == [corpus or "business"] * 2
    assert diagnostics["corpus"] == (corpus or "business")


def test_invalid_corpus_fails_before_provider_or_database_access(monkeypatch):
    monkeypatch.setattr(rag_service, "_embed", lambda _: pytest.fail("provider called"))
    with pytest.raises(ValueError, match="corpus"):
        asyncio.run(rag_service.search(object(), "测试", corpus="all"))


@pytest.mark.parametrize("entrypoint", ["backoffice", "script"])
def test_evaluation_entrypoints_explicitly_select_evaluation_corpus(monkeypatch, entrypoint):
    cases = rag_evaluation.load_cases(rag_evaluation.CASES_PATH)
    sources = {source for case in cases for source in case.expected_sources}

    class Database:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def execute(self, _statement):
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: sources))

    selected = []

    async def search(_db, **kwargs):
        selected.append(kwargs["corpus"])
        kwargs["diagnostics"].update({
            "vector_ranked_ids": [], "fulltext_ranked_ids": [],
            "rrf_ranked_ids": [], "final_result_ids": [],
        })
        return []

    if entrypoint == "backoffice":
        monkeypatch.setattr(rag_evaluation, "search", search)
        result = asyncio.run(rag_evaluation.run_evaluation(Database(), top_k=3, rerank=False))
    else:
        monkeypatch.setattr(eval_rag_retrieval, "search", search)
        monkeypatch.setattr(eval_rag_retrieval, "async_session", Database)
        result = asyncio.run(eval_rag_retrieval.run(eval_rag_retrieval.DEFAULT_CASES, 3, False))
    assert selected == ["evaluation"] * 4
    assert result["configuration"]["corpus"] == "evaluation"
    assert result["summary"]["evaluated_case_count"] == 4
    assert result["summary"]["skipped_case_count"] == 1
