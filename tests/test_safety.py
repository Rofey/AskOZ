from types import SimpleNamespace

import fakeredis
import pytest

from askoz.safety.cache import AnswerCache, normalise
from askoz.safety.ratelimit import Limit, RateLimiter, hash_identity
from askoz.safety.spend import SpendTracker, cost_usd


@pytest.fixture
def store() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()


def test_sliding_window_blocks_then_recovers(store: fakeredis.FakeRedis) -> None:
    limiter = RateLimiter(store, [Limit("minute", 3, 60)])
    t0 = 1_000_000
    assert all(limiter.hit("ip", now_ms=t0 + i).allowed for i in range(3))
    blocked = limiter.hit("ip", now_ms=t0 + 10_000)
    assert not blocked.allowed
    assert blocked.retry_after_seconds == 50  # oldest request leaves the window at t0+60s
    assert limiter.hit("ip", now_ms=t0 + 60_001).allowed


def test_no_burst_at_window_boundary(store: fakeredis.FakeRedis) -> None:
    # A fixed per-minute window would allow 3 at 0:59 and 3 more at 1:00.
    limiter = RateLimiter(store, [Limit("minute", 3, 60)])
    for i in range(3):
        assert limiter.hit("ip", now_ms=59_000 + i).allowed
    assert not limiter.hit("ip", now_ms=61_000).allowed


def test_rejected_requests_are_not_counted(store: fakeredis.FakeRedis) -> None:
    limiter = RateLimiter(store, [Limit("minute", 1, 60)])
    assert limiter.hit("ip", now_ms=0).allowed
    for t in range(1_000, 50_000, 1_000):
        assert not limiter.hit("ip", now_ms=t).allowed  # hammering doesn't extend the block
    assert limiter.hit("ip", now_ms=60_001).allowed


def test_daily_limit_applies_across_minutes(store: fakeredis.FakeRedis) -> None:
    limiter = RateLimiter(store, [Limit("minute", 5, 60), Limit("day", 6, 86_400)])
    times = [0, 1, 2, 3, 4, 120_000]  # 5 in the first minute, 1 later
    assert all(limiter.hit("ip", now_ms=t).allowed for t in times)
    decision = limiter.hit("ip", now_ms=240_000)
    assert not decision.allowed and decision.limit and decision.limit.name == "day"


def test_identities_are_independent(store: fakeredis.FakeRedis) -> None:
    limiter = RateLimiter(store, [Limit("minute", 1, 60)])
    assert limiter.hit("a", now_ms=0).allowed
    assert limiter.hit("b", now_ms=0).allowed


def test_ip_hash_is_keyed() -> None:
    assert hash_identity("1.2.3.4", "secret-a") != hash_identity("1.2.3.4", "secret-b")
    assert "1.2.3.4" not in hash_identity("1.2.3.4", "secret-a")


def test_cost_from_usage() -> None:
    usage = SimpleNamespace(
        input_tokens=10_000,
        output_tokens=1_000,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    assert cost_usd("claude-opus-5-5", usage) == pytest.approx(0.04 + 0.02)
    assert cost_usd("claude-haiku-5-5", usage) == pytest.approx(0.001 + 0.0005)


def test_spend_cap(store: fakeredis.FakeRedis) -> None:
    spend = SpendTracker(store, daily_cap_usd=0.10)
    spend.record(0.06)
    assert not spend.over_cap()
    spend.record(0.05)
    assert spend.over_cap()
    assert spend.spent_today_usd() == pytest.approx(0.11)


def test_answer_cache_normalises_questions(store: fakeredis.FakeRedis) -> None:
    cache = AnswerCache(store, ttl_seconds=60, model="m")
    cache.set("What is a TFN?", {"answer": "x", "sources": []})
    assert cache.get("  what is a   tfn ") == {"answer": "x", "sources": []}
    assert normalise("Hello  World?!") == "hello world"
    assert AnswerCache(store, ttl_seconds=60, model="other").get("What is a TFN?") is None
