"""Answer cache: identical questions within a few hours cost nothing extra.

Keys are hashes of the normalised question, so the cache never holds question
text. Only successful answers are cached; refusals, errors and blocked
questions never are. The key includes the answer model and a version, so
changing either starts a fresh cache instead of serving stale answers.
"""

import hashlib
import json
import re
from typing import Any

import redis

CACHE_VERSION = "v9"  # bump when prompts or retrieval change answers materially


def normalise(question: str) -> str:
    return re.sub(r"\s+", " ", question).strip().rstrip("?!. ").lower()


class AnswerCache:
    def __init__(
        self, client: redis.Redis, ttl_seconds: int, *, model: str, prefix: str = "askoz:answer"
    ):
        self.client = client
        self.ttl_seconds = ttl_seconds
        self.model = model
        self.prefix = prefix

    def _key(self, question: str) -> str:
        digest = hashlib.sha256(f"{CACHE_VERSION}|{self.model}|{normalise(question)}".encode())
        return f"{self.prefix}:{digest.hexdigest()}"

    def get(self, question: str) -> dict[str, Any] | None:
        raw = self.client.get(self._key(question))
        return json.loads(raw) if raw else None  # type: ignore[arg-type]

    def set(self, question: str, answer: dict[str, Any]) -> None:
        self.client.set(self._key(question), json.dumps(answer), ex=self.ttl_seconds)
