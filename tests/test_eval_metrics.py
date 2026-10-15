import pytest

from askoz.evals.retrieval import first_relevant_rank, metrics


def test_first_relevant_rank() -> None:
    pages = ["a", "b", "c"]
    assert first_relevant_rank(pages, {"b", "c"}) == 2
    assert first_relevant_rank(pages, {"z"}) is None


def test_metrics() -> None:
    m = metrics([1, 3, None, 6])
    assert m["hit@1"] == 0.25
    assert m["hit@5"] == 0.5
    assert m["hit@10"] == 0.75
    assert m["mrr"] == pytest.approx((1 + 1 / 3 + 1 / 6) / 4)
