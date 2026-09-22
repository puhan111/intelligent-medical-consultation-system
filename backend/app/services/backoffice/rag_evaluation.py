from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.models.knowledge_chunk import KnowledgeChunk
from app.services.common.rag_evaluation import evaluate_retrieval, load_cases
from app.services.common.rag_service import search

CASES_PATH = Path(__file__).parents[3] / "scripts" / "fixtures" / "rag_eval_cases.json"


async def run_evaluation(db, *, top_k: int, rerank: bool) -> dict:
    cases = load_cases(CASES_PATH)
    expected = {
        source for case in cases if case.expectation == "retrieve"
        for source in case.expected_sources
    }
    stored = set((await db.execute(
        select(KnowledgeChunk.source).where(KnowledgeChunk.source.in_(expected)).distinct()
    )).scalars().all())
    missing = sorted(expected - stored)
    if missing:
        return {"ready": False, "missing_sources": missing}

    rankings, diagnostics_by_case = {}, {}
    for case in cases:
        if case.expectation != "retrieve":
            continue
        diagnostics = {}
        results = await search(
            db, query=case.query, top_k=top_k, source_type=case.source_type,
            rerank=rerank, agent_type="rag_eval", log_query=False,
            diagnostics=diagnostics,
        )
        rankings[case.case_id] = [item.source for item in results]
        diagnostics_by_case[case.case_id] = {
            key: value for key, value in diagnostics.items()
            if not key.endswith("_ids")
        }
        diagnostics_by_case[case.case_id]["results"] = [
            {"source": item.source, "score": item.score, "preview": item.content[:300]}
            for item in results
        ]

    evaluation = evaluate_retrieval(cases, rankings, top_k)
    for detail in evaluation["cases"]:
        if detail["status"] == "evaluated":
            detail["diagnostics"] = diagnostics_by_case[detail["case_id"]]
    return {
        "ready": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {"dataset": "内置合成回归集", "rerank": rerank},
        **evaluation,
    }
