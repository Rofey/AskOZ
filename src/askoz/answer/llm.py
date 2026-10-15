"""Shared Claude client and request options."""

from functools import lru_cache
from typing import Any

import anthropic

from askoz.config import get_settings

# Server-side refusal fallback: if a model's safety classifier declines a
# request, the API re-runs it on a suitable fallback model inside the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@lru_cache
def client() -> anthropic.Anthropic:
    key = get_settings().anthropic_api_key
    if key is None:
        raise RuntimeError("Set ASKOZ_ANTHROPIC_API_KEY in .env")
    return anthropic.Anthropic(api_key=key.get_secret_value(), max_retries=3)


def fallback_options(model: str) -> dict[str, Any]:
    """Request options enabling refusal fallbacks, where the model supports them."""
    if model.startswith("claude-haiku"):
        return {}  # Haiku has no server-side fallback
    return {"betas": [FALLBACK_BETA], "fallbacks": "default"}
