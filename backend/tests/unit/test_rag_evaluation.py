from pathlib import Path

import pytest

from app.services.common.rag_evaluation import (
    RetrievalCase,
    evaluate_retrieval,
    load_cases,
)


def test_retrieval_metrics_measure_hit_recall_and_first_relevant_rank():
    cases = [
        RetrievalCase(
            case_id="known-fact",
            query="问题一",
            expected_sources=("doc-a", "doc-b"),
        ),
        RetrievalCase(
            case_id="multi-document",
            query="问题二",
            expected_sources=("doc-c",),
            category="multi_document",
        ),
        RetrievalCase(
            case_id="no-hit",
            query="问题三",
            expected_sources=("doc-d",),
        ),
    ]
    rankings = {
        "known-fact": ["doc-a", "doc-a", "noise"],
        "multi-document": ["noise", "doc-c", "other"],
        "no-hit": ["noise", "other"],
    }

    result = evaluate_retrieval(cases, rankings, top_k=3)

    assert result["summary"] == {
        "case_count": 3,
        "evaluated_case_count": 3,
        "skipped_case_count": 0,
        "hit_rate_at_3": pytest.approx(2 / 3),
        "mean_recall_at_3": pytest.approx(0.5),
        "mrr_at_3": pytest.approx(0.5),
    }
    assert result["cases"][0]["retrieved_sources"] == ["doc-a", "noise"]
    assert result["cases"][0]["recall_at_3"] == 0.5
    assert result["cases"][1]["reciprocal_rank_at_3"] == 0.5
    assert result["cases"][2]["hit_at_3"] == 0.0


def test_answer_level_case_is_reported_as_skipped():
    cases = [
        RetrievalCase(
            case_id="missing-fact",
            query="知识库中不存在的问题",
            expected_sources=(),
            category="missing_fact",
            expectation="abstain",
        )
    ]

    result = evaluate_retrieval(cases, {}, top_k=5)

    assert result["summary"]["evaluated_case_count"] == 0
    assert result["summary"]["skipped_case_count"] == 1
    assert result["cases"][0]["status"] == "skipped"
    assert result["cases"][0]["reason"] == "requires answer-level evaluation"


@pytest.mark.parametrize("top_k", [0, -1])
def test_top_k_must_be_positive(top_k):
    with pytest.raises(ValueError, match="top_k"):
        evaluate_retrieval([], {}, top_k=top_k)


def test_case_ids_must_be_unique():
    cases = [
        RetrievalCase("same-id", "问题一", ("doc-a",)),
        RetrievalCase("same-id", "问题二", ("doc-b",)),
    ]

    with pytest.raises(ValueError, match="unique"):
        evaluate_retrieval(cases, {}, top_k=5)


def test_versioned_fixture_dataset_contains_required_scenarios():
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "fixtures"
        / "rag_eval_cases.json"
    )

    cases = load_cases(fixture_path)

    assert len(cases) == 5
    assert {case.category for case in cases} == {
        "known_fact",
        "multi_document",
        "conflict_fact",
        "missing_fact",
    }
    assert sum(case.expectation == "abstain" for case in cases) == 1
