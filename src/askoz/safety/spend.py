"""Measuring Claude spend and enforcing a daily cap.

Cost is computed from the token counts each API response reports, not
estimated up front, so the cap tracks what Anthropic will actually bill.
The day boundary is midnight in Sydney, matching when users' days roll over.

The cap is checked before a request starts, so requests already in flight can
overshoot it by at most `max_concurrent_answers` answers (about $0.50 at the
defaults). The Anthropic Console spend limit is the hard backstop beyond that.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import redis

from askoz.logging import get_logger

log = get_logger(__name__)

SYDNEY = ZoneInfo("Australia/Sydney")
MICRODOLLARS = 1_000_000  # Redis counts integer micro-dollars: exact, no float drift

# USD per million tokens: (input, output, cache read). Cache writes cost 1.25x input.
# Source: Anthropic pricing, October 2026. Update when models or prices change.
PRICES_PER_MTOK: dict[str, tuple[float, float, float]] = {
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
}
_UNKNOWN_MODEL_PRICES = PRICES_PER_MTOK["claude-opus-5-5"]  # assume the expensive case


def cost_usd(model: str, usage: Any) -> float:
    """Cost of one API response from its `usage` block (thinking is billed as output)."""
    prices = PRICES_PER_MTOK.get(model)
    if prices is None:
        log.warning("unpriced_model", model=model)
        prices = _UNKNOWN_MODEL_PRICES
    input_price, output_price, cache_read_price = prices
    tokens_x_price = (
        (usage.input_tokens or 0) * input_price
        + (usage.output_tokens or 0) * output_price
        + (getattr(usage, "cache_read_input_tokens", 0) or 0) * cache_read_price
        + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * input_price * 1.25
    )
    return tokens_x_price / 1_000_000


@dataclass
class UsageMeter:
    """Accumulates the cost of every Claude call made while answering one question."""

    total_usd: float = 0.0
    calls: list[tuple[str, float]] = field(default_factory=list)

    def add(self, model: str, usage: Any) -> None:
        cost = cost_usd(model, usage)
        self.total_usd += cost
        self.calls.append((model, cost))


class SpendTracker:
    def __init__(self, client: redis.Redis, daily_cap_usd: float, *, prefix: str = "askoz:spend"):
        self.client = client
        self.daily_cap_usd = daily_cap_usd
        self.prefix = prefix

    def _key(self, now: datetime | None = None) -> str:
        day = (now or datetime.now(SYDNEY)).astimezone(SYDNEY).date()
        return f"{self.prefix}:{day.isoformat()}"

    def spent_today_usd(self) -> float:
        value = self.client.get(self._key())
        return int(value) / MICRODOLLARS if value else 0.0  # type: ignore[arg-type]

    def over_cap(self) -> bool:
        return self.spent_today_usd() >= self.daily_cap_usd

    def record(self, usd: float) -> None:
        if usd <= 0:
            return
        key = self._key()
        pipe = self.client.pipeline()
        pipe.incrby(key, round(usd * MICRODOLLARS))
        pipe.expire(key, 3 * 24 * 3600)  # keep a few days for checking, then drop
        pipe.execute()
