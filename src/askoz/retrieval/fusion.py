"""Reciprocal Rank Fusion: merging ranked lists whose scores aren't comparable.

Vector search scores are cosine similarities (~0.5-0.9); keyword search scores
are Postgres ts_rank values (~0.0-0.1). Adding or sorting them together is
meaningless. RRF ignores the scores and uses only each result's *position*:

    score(chunk) = sum over lists of 1 / (k + rank_in_that_list)

A chunk ranked well by both searches beats one ranked first by only one.
k=60 comes from the original paper (Cormack et al., 2009); it softens the
gap between rank 1 and rank 2 so no single list dominates.
"""

from llama_index.core.schema import NodeWithScore

RRF_K = 60


def reciprocal_rank_fusion(
    result_lists: list[list[NodeWithScore]], *, k: int = RRF_K
) -> list[NodeWithScore]:
    scores: dict[str, float] = {}
    nodes: dict[str, NodeWithScore] = {}
    for results in result_lists:
        for rank, result in enumerate(results, start=1):
            node_id = result.node.node_id
            scores[node_id] = scores.get(node_id, 0.0) + 1.0 / (k + rank)
            nodes.setdefault(node_id, result)
    ranked = sorted(scores, key=lambda node_id: scores[node_id], reverse=True)
    return [NodeWithScore(node=nodes[node_id].node, score=scores[node_id]) for node_id in ranked]
