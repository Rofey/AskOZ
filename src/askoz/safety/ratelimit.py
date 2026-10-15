"""Sliding-window rate limiting in Redis.

Why a sliding window: a fixed window ("5 per calendar minute") lets someone
send 5 at 12:00:59 and 5 more at 12:01:00, 10 in two seconds. A sliding window
counts requests in the last 60 seconds from *now*, so there's no burst at the
boundary.

Each identity gets one Redis sorted set per window, holding a member per
request scored by its timestamp. The check-and-record runs as one Lua script,
which Redis executes atomically: two simultaneous requests can't both see
"4 used" and both get in. Rejected requests are not recorded, so a client that
backs off as told regains access on schedule.
"""

import hashlib
import hmac
import time
import uuid
from dataclasses import dataclass

import redis

# KEYS: one sorted set per window. ARGV: now_ms, member, then (window_ms, limit)
# per key. Returns {0, 0} if allowed, else {index of the limit hit, retry-after s}.
_SLIDING_WINDOW_LUA = """
local now = tonumber(ARGV[1])
local member = ARGV[2]
for i, key in ipairs(KEYS) do
  local window = tonumber(ARGV[1 + i * 2])
  local limit = tonumber(ARGV[2 + i * 2])
  redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
  if redis.call('ZCARD', key) >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    return {i, math.ceil((tonumber(oldest[2]) + window - now) / 1000)}
  end
end
for i, key in ipairs(KEYS) do
  redis.call('ZADD', key, now, member)
  redis.call('PEXPIRE', key, tonumber(ARGV[1 + i * 2]))
end
return {0, 0}
"""


@dataclass(frozen=True)
class Limit:
    name: str
    max_requests: int
    window_seconds: int


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after_seconds: int = 0
    limit: Limit | None = None  # the limit that was hit


class RateLimiter:
    def __init__(self, client: redis.Redis, limits: list[Limit], *, prefix: str = "askoz:rl"):
        self.limits = limits
        self.prefix = prefix
        self._script = client.register_script(_SLIDING_WINDOW_LUA)

    def hit(self, identity: str, *, now_ms: int | None = None) -> Decision:
        """Record one request for `identity` if every limit allows it."""
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        keys = [f"{self.prefix}:{limit.name}:{identity}" for limit in self.limits]
        args: list[int | str] = [now_ms, f"{now_ms}-{uuid.uuid4().hex[:8]}"]
        for limit in self.limits:
            args += [limit.window_seconds * 1000, limit.max_requests]
        index, retry_after = self._script(keys=keys, args=args)  # type: ignore[misc]
        if index == 0:
            return Decision(allowed=True)
        return Decision(
            allowed=False,
            retry_after_seconds=max(1, int(retry_after)),
            limit=self.limits[int(index) - 1],
        )


def hash_identity(value: str, secret: str) -> str:
    """Keyed hash of an IP address: stable for rate limiting, useless if leaked.

    A plain sha256 of an IPv4 address can be reversed by trying all 4 billion
    addresses; an HMAC with a server-side secret can't.
    """
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()[:32]
