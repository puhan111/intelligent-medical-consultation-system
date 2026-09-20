"""Pure retrieval metrics used by the offline RAG regression evaluator."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class RetrievalCase:
    case_id: str
    query: str
    expected_sources: tuple[str, ...]
    category: str = "known_fact"
    expectation: str = "retrieve"
    source_type: str | None = None


def load_cases(path: str | Path) -> list[RetrievalCase]:
    """Load the versioned JSON dataset used by retrieval evaluation."""
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw_cases, list):
        raise ValueError("evaluation dataset must be a JSON list")

    cases = []
    for raw in raw_cases:
        try:
            cases.append(
                RetrievalCase(
                    case_id=raw["case_id"],
                    query=raw["query"],
                    expected_sources=tuple(raw["expected_sources"]),
                    category=raw.get("category", "known_fact"),
                    expectation=raw.get("expectation", "retrieve"),
                    source_type=raw.get("source_type"),
                )
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(f"invalid evaluation case: {raw!r}") from exc
    return cases


def evaluate_retrieval(
    cases: Sequence[RetrievalCase],
    rankings: Mapping[str, Sequence[str]],
    top_k: int,
) -> dict:
    """Evaluate ranked source names with Hit@K, Recall@K and MRR@K.

    Cases whose expectation is not ``retrieve`` are reported as skipped because
    retrieval ranking alone cannot prove that the final answer abstained.
    """
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("case_id values must be unique")

    details = []
    evaluated = []

    for case in cases:
        if case.expectation != "retrieve":
            details.append(
                {
                    "case_id": case.case_id,
                    "category": case.category,
                    "expectation": case.expectation,
                    "status": "skipped",
                    "reason": "requires answer-level evaluation",
                }
            )
            continue

        expected = set(case.expected_sources)
        if not expected:
            raise ValueError(
                f"retrieve case '{case.case_id}' must define expected_sources"
            )

        # Keep the first occurrence so duplicate sources cannot inflate recall.
        ranked = list(dict.fromkeys(rankings.get(case.case_id, ())))[:top_k]
        hit_sources = [source for source in ranked if source in expected]
        first_relevant_rank = next(
            (index for index, source in enumerate(ranked, start=1) if source in expected),
            None,
        )
        hit_at_k = 1.0 if hit_sources else 0.0
        recall_at_k = len(set(hit_sources)) / len(expected)
        reciprocal_rank = 1.0 / first_relevant_rank if first_relevant_rank else 0.0

        result = {
            "case_id": case.case_id,
            "category": case.category,
            "expectation": case.expectation,
            "status": "evaluated",
            "expected_sources": list(case.expected_sources),
            "retrieved_sources": ranked,
            "hit_sources": hit_sources,
            f"hit_at_{top_k}": hit_at_k,
            f"recall_at_{top_k}": recall_at_k,
            f"reciprocal_rank_at_{top_k}": reciprocal_rank,
        }
        details.append(result)
        evaluated.append(result)

    count = len(evaluated)
    summary = {
        "case_count": len(cases),
        "evaluated_case_count": count,
        "skipped_case_count": len(cases) - count,
        f"hit_rate_at_{top_k}": (
            sum(item[f"hit_at_{top_k}"] for item in evaluated) / count if count else 0.0
        ),
        f"mean_recall_at_{top_k}": (
            sum(item[f"recall_at_{top_k}"] for item in evaluated) / count if count else 0.0
        ),
        f"mrr_at_{top_k}": (
            sum(item[f"reciprocal_rank_at_{top_k}"] for item in evaluated) / count
            if count
            else 0.0
        ),
    }
    return {"top_k": top_k, "summary": summary, "cases": details}


def check_retrieval_thresholds(
    summary: Mapping[str, float | int],
    top_k: int,
    *,
    min_hit_rate: float | None = None,
    min_recall: float | None = None,
    min_mrr: float | None = None,
) -> list[str]:
    """Return human-readable failures for configured retrieval thresholds."""
    thresholds = {
        f"hit_rate_at_{top_k}": min_hit_rate,
        f"mean_recall_at_{top_k}": min_recall,
        f"mrr_at_{top_k}": min_mrr,
    }
    failures = []
    for metric, minimum in thresholds.items():
        if minimum is None:
            continue
        if not 0.0 <= minimum <= 1.0:
            raise ValueError(f"{metric} threshold must be between 0 and 1")
        actual = float(summary[metric])
        if actual < minimum:
            failures.append(f"{metric}={actual:.4f} is below {minimum:.4f}")
    return failures
