"""API tests: every safety layer, with fake Redis and a stub answer graph."""

import json
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import anthropic
import fakeredis
import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from askoz.answer.context import SourcePage
from askoz.api.app import create_app
from askoz.config import Settings

PAGE = SourcePage(url="https://www.ato.gov.au/x", title="Working holiday makers", last_updated=None)
# 10k input + 1k output tokens on Opus 5.5 = $0.06 per answer.
USAGE = SimpleNamespace(
    input_tokens=10_000,
    output_tokens=1_000,
    cache_read_input_tokens=0,
    cache_creation_input_tokens=0,
)


class StubGraph:
    def __init__(self, *, fail_with: Exception | None = None) -> None:
        self.calls = 0
        self.fail_with = fail_with

    def stream(self, input: Any, config: Any = None, *, stream_mode: Any = None) -> Iterator[Any]:
        self.calls += 1
        config["configurable"]["on_usage"]("claude-opus-5-5", USAGE)
        if self.fail_with:
            raise self.fail_with
        yield ("custom", {"text": "15% on the first $45,000 "})
        yield ("custom", {"text": "[1]"})
        yield (
            "values",
            {
                "question": input["question"],
                "answer": "15% on the first $45,000 [1]",
                "route": "answered",
                "sources": [PAGE],
            },
        )


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "rate_limit_per_minute": 3,
        "rate_limit_per_day": 100,
        "daily_spend_cap_usd": 10.0,
        "max_concurrent_answers": 1,
    }
    return Settings(_env_file=None, **(base | overrides))  # pyright: ignore[reportCallIssue]


def _client(graph: StubGraph | None = None, **overrides: Any) -> tuple[TestClient, StubGraph]:
    graph = graph or StubGraph()
    app = create_app(
        settings=_settings(**overrides), redis_client=fakeredis.FakeRedis(), graph=graph
    )
    return TestClient(app), graph


def _events(response: httpx.Response) -> list[tuple[str, Any]]:
    events = []
    for block in response.text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def _ask(
    client: TestClient, question: str = "how much tax do backpackers pay", **kw: Any
) -> httpx.Response:
    return client.post("/v1/ask", json={"question": question}, **kw)


def test_streams_text_then_sources_then_done() -> None:
    client, _ = _client()
    response = _ask(client)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _events(response)
    assert [name for name, _ in events] == ["text", "text", "sources", "done"]
    assert events[2][1] == [{"title": PAGE.title, "url": PAGE.url}]
    assert events[3][1] == {"route": "answered", "cached": False}


def test_rate_limit_returns_429_with_retry_after() -> None:
    client, _ = _client()
    for i in range(3):
        assert _ask(client, f"question number {i}").status_code == 200
    blocked = _ask(client, "question number 4")
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_forged_proxy_headers_are_ignored_by_default() -> None:
    client, _ = _client()
    for i in range(3):
        _ask(client, f"q {i} padding", headers={"x-forwarded-for": f"10.0.0.{i}"})
    assert _ask(client, "q 9 padding", headers={"x-forwarded-for": "10.0.0.99"}).status_code == 429


def test_trusted_proxy_header_separates_clients() -> None:
    client, _ = _client(trust_proxy_headers=True)
    for i in range(3):
        _ask(client, f"q {i} padding", headers={"cf-connecting-ip": "203.0.113.1"})
    assert (
        _ask(client, "q 9 padding", headers={"cf-connecting-ip": "203.0.113.2"}).status_code == 200
    )


def test_repeat_question_is_served_from_cache() -> None:
    client, graph = _client()
    _ask(client, "What is a TFN?")
    events = _events(_ask(client, "what is a tfn"))
    assert graph.calls == 1
    assert events[-1] == ("done", {"route": "answered", "cached": True})


def test_spend_cap_stops_claude_calls() -> None:
    client, graph = _client(daily_spend_cap_usd=0.05)
    assert _ask(client, "first question here").status_code == 200  # costs $0.06
    response = _ask(client, "second question here")
    assert response.status_code == 503
    assert graph.calls == 1


def test_question_length_is_validated() -> None:
    client, graph = _client()
    assert _ask(client, "x" * 501).status_code == 422
    assert _ask(client, "hi").status_code == 422
    assert graph.calls == 0


def test_concurrency_slot_is_released_after_each_answer() -> None:
    client, graph = _client(max_concurrent_answers=1)
    for i in range(3):
        assert _ask(client, f"sequential question {i}").status_code == 200
    assert graph.calls == 3


def test_claude_failure_becomes_error_event_and_frees_slot() -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    error = anthropic.APIConnectionError(request=request)
    client, _ = _client(StubGraph(fail_with=error), max_concurrent_answers=1)
    events = _events(_ask(client, "first failing question"))
    assert events[-1][0] == "error"
    assert "something went wrong" in events[-1][1]["message"]
    assert _ask(client, "second question after failure").status_code == 200


def test_security_headers_and_health() -> None:
    client, _ = _client()
    response = client.get("/healthz")
    assert response.json() == {"status": "ok"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_docs_are_hidden_in_prod(path: str) -> None:
    client, _ = _client(env="prod", anthropic_api_key="sk-test", ip_hash_secret="s3cret")
    assert client.get(path).status_code == 404
