from app.services.common.ranking import RRF_K, reciprocal_rank_fusion


def test_rrf_rewards_chunks_found_by_both_retrievers() -> None:
    ranked_ids, scores = reciprocal_rank_fusion(
        vector_ranked=[1, 2, 3],
        fulltext_ranked=[2, 3, 4],
    )

    assert ranked_ids == [2, 3, 1, 4]
    assert scores[2] == 1 / (RRF_K + 2) + 1 / (RRF_K + 1)
    assert scores[3] == 1 / (RRF_K + 3) + 1 / (RRF_K + 2)


def test_rrf_handles_empty_results() -> None:
    ranked_ids, scores = reciprocal_rank_fusion([], [])

    assert ranked_ids == []
    assert scores == {}

