import pytest
from llama_index.core.schema import NodeWithScore, TextNode

from askoz.retrieval.fusion import reciprocal_rank_fusion


def _results(*ids: str, score: float) -> list[NodeWithScore]:
    return [NodeWithScore(node=TextNode(id_=i, text=i), score=score) for i in ids]


def test_chunk_found_by_both_searches_beats_one_found_by_either() -> None:
    vector = _results("a", "shared", score=0.9)
    keyword = _results("b", "shared", score=0.01)
    fused = [r.node.node_id for r in reciprocal_rank_fusion([vector, keyword])]
    assert fused[0] == "shared"


def test_raw_scores_are_ignored() -> None:
    # Keyword scores are tiny next to cosine similarity; RRF must not care.
    vector = _results("v1", "v2", score=0.95)
    keyword = _results("k1", "k2", score=0.001)
    fused = [r.node.node_id for r in reciprocal_rank_fusion([vector, keyword])]
    assert set(fused[:2]) == {"v1", "k1"}


def test_weights_let_a_trusted_list_win() -> None:
    original = _results("orig", score=1.0)
    rewrite = _results("rw", score=1.0)
    assert reciprocal_rank_fusion([original, rewrite])[0].score == pytest.approx(1 / 61)
    fused = reciprocal_rank_fusion([original, rewrite], weights=[2.0, 1.0])
    assert fused[0].node.node_id == "orig"
