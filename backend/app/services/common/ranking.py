from collections.abc import Sequence


# RRF 融合常数。值越大，不同名次之间的分差越平滑。
RRF_K = 60


def reciprocal_rank_fusion(
    vector_ranked: Sequence[int],
    fulltext_ranked: Sequence[int],
) -> tuple[list[int], dict[int, float]]:
    """Fuse two ranked chunk-id lists with Reciprocal Rank Fusion."""
    scores: dict[int, float] = {}

    for rank, chunk_id in enumerate(vector_ranked):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)

    for rank, chunk_id in enumerate(fulltext_ranked):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)

    ranked_ids = sorted(scores, key=scores.__getitem__, reverse=True)
    return ranked_ids, scores

