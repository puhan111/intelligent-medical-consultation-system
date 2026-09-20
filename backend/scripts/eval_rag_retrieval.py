"""Run repeatable retrieval evaluation against the configured RAG database."""

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import async_session
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.common.rag_evaluation import evaluate_retrieval, load_cases
from app.services.common.rag_service import search


DEFAULT_CASES = Path(__file__).parent / "fixtures" / "rag_eval_cases.json"
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "eval_results"


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval with a fixed dataset")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


async def run(cases_path: Path, top_k: int, rerank: bool) -> dict:
    cases = load_cases(cases_path)
    expected_sources = {
        source
        for case in cases
        if case.expectation == "retrieve"
        for source in case.expected_sources
    }

    rankings = {}
    diagnostics_by_case = {}
    async with async_session() as db:
        stored_sources = set(
            (
                await db.execute(
                    select(KnowledgeChunk.source)
                    .where(KnowledgeChunk.source.in_(expected_sources))
                    .distinct()
                )
            ).scalars().all()
        )
        missing_sources = sorted(expected_sources - stored_sources)
        if missing_sources:
            raise RuntimeError(
                "evaluation fixtures are missing; run "
                "'python scripts/prepare_rag_eval_fixtures.py' first: "
                + ", ".join(missing_sources)
            )

        for case in cases:
            if case.expectation != "retrieve":
                continue
            diagnostics = {}
            results = await search(
                db,
                query=case.query,
                top_k=top_k,
                source_type=case.source_type,
                rerank=rerank,
                agent_type="rag_eval",
                log_query=False,
                diagnostics=diagnostics,
            )
            rankings[case.case_id] = [result.source for result in results]
            ranked_ids = {
                chunk_id
                for key in (
                    "vector_ranked_ids",
                    "fulltext_ranked_ids",
                    "rrf_ranked_ids",
                    "final_result_ids",
                )
                for chunk_id in diagnostics.get(key, [])
            }
            source_by_id = {}
            if ranked_ids:
                source_by_id = dict(
                    (
                        await db.execute(
                            select(KnowledgeChunk.id, KnowledgeChunk.source).where(
                                KnowledgeChunk.id.in_(ranked_ids)
                            )
                        )
                    ).all()
                )
            diagnostics["vector_ranked_sources"] = [
                source_by_id.get(chunk_id) for chunk_id in diagnostics["vector_ranked_ids"]
            ]
            diagnostics["fulltext_ranked_sources"] = [
                source_by_id.get(chunk_id) for chunk_id in diagnostics["fulltext_ranked_ids"]
            ]
            diagnostics["rrf_ranked_sources"] = [
                source_by_id.get(chunk_id) for chunk_id in diagnostics["rrf_ranked_ids"]
            ]
            diagnostics["final_result_sources"] = [result.source for result in results]
            diagnostics_by_case[case.case_id] = diagnostics

    evaluation = evaluate_retrieval(cases, rankings, top_k)
    for detail in evaluation["cases"]:
        if detail["status"] == "evaluated":
            detail["diagnostics"] = diagnostics_by_case[detail["case_id"]]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "cases_path": str(cases_path),
            "top_k": top_k,
            "rerank": rerank,
            "query_logging": False,
        },
        **evaluation,
    }


async def main() -> None:
    args = parse_args()
    result = await run(args.cases, args.top_k, args.rerank)
    output = args.output
    if output is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output = DEFAULT_OUTPUT_DIR / f"rag-retrieval-{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"saved_to={output}")


if __name__ == "__main__":
    asyncio.run(main())
