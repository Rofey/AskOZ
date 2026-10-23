"""FastAPI app: one streaming endpoint, wrapped in the safety layers.

Order of checks for POST /v1/ask, cheapest first, so abuse is turned away
before it costs anything:

    1. body validation        question length (FastAPI/Pydantic -> 422)
    2. rate limit per IP      sliding windows in Redis              -> 429
    3. answer cache           identical recent question -> replay, no Claude call
    4. daily spend cap        measured Claude spend today           -> 503
    5. concurrency cap        Claude calls in flight                -> 503
    6. answer graph           guard -> plan -> retrieve -> generate (SSE stream)

The response is Server-Sent Events: `text` chunks as the answer is written,
then `sources`, then `done` (or `error`). Question text is never logged.
"""

import json
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Protocol, cast

import anthropic
import redis
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from askoz.answer.referral import referral_payload
from askoz.config import ClientIpSource, Settings, get_settings
from askoz.logging import configure_logging, get_logger
from askoz.safety.cache import AnswerCache
from askoz.safety.ratelimit import Limit, RateLimiter, hash_identity
from askoz.safety.spend import SpendTracker, UsageMeter

log = get_logger(__name__)

BUSY = "AskOz is busy right now. Please try again in a little while."
FAILED = "Sorry, something went wrong while answering. Please try again."


class SlotLease:
    """A concurrency slot that is released exactly once, whoever releases it first.

    A streaming generator's `finally` only runs if the generator was started.
    If the client disconnects before the first byte, it never starts, so the
    slot is also released by a background task that Starlette runs when the
    response ends. Without this, disconnects would leak slots until the
    server answered "busy" forever.
    """

    def __init__(self, semaphore: threading.BoundedSemaphore) -> None:
        self._semaphore = semaphore
        self._lock = threading.Lock()
        self._released = False

    def release(self) -> None:
        with self._lock:
            if not self._released:
                self._released = True
                self._semaphore.release()


class AnswerGraph(Protocol):
    def stream(
        self, input: Any, config: Any = None, *, stream_mode: Any = None
    ) -> Iterator[Any]: ...


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def client_ip(request: Request, *, source: ClientIpSource) -> str:
    """The caller's IP, read only from where our own proxy puts it (see Settings)."""
    if source == "cloudflare" and (cf_ip := request.headers.get("cf-connecting-ip")):
        return cf_ip.strip()
    if source == "cloud_run" and (forwarded := request.headers.get("x-forwarded-for")):
        # "spoofed, spoofed, real": Google appends the address it saw last.
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def create_app(
    *,
    settings: Settings | None = None,
    redis_client: redis.Redis | None = None,
    graph: AnswerGraph | None = None,
) -> FastAPI:
    """Build the app. Tests pass fakes for Redis and the graph; production passes nothing."""
    settings = settings or get_settings()
    store = redis_client or redis.Redis.from_url(str(settings.redis_url))
    limiter = RateLimiter(
        store,
        [
            Limit("ip_minute", settings.rate_limit_per_minute, 60),
            Limit("ip_day", settings.rate_limit_per_day, 24 * 3600),
        ],
    )
    spend = SpendTracker(store, settings.daily_spend_cap_usd)
    cache = AnswerCache(store, settings.answer_cache_ttl_seconds, model=settings.answer_model)
    slots = threading.BoundedSemaphore(settings.max_concurrent_answers)
    state: dict[str, AnswerGraph] = {}
    if graph is not None:
        state["graph"] = graph

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        configure_logging()
        if "graph" not in state:
            from askoz.answer.graph import build_graph

            state["graph"] = cast(AnswerGraph, build_graph())  # loads the embedding model once
        yield

    is_prod = settings.env == "prod"
    app = FastAPI(
        title="AskOz",
        lifespan=lifespan,
        # No interactive docs in production: less surface for scanners.
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
        # Browsers hide response headers from cross-origin JavaScript unless
        # they're exposed here. Without this the web app can't read how long
        # to wait after a 429 and would guess.
        expose_headers=["Retry-After"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    class AskRequest(BaseModel):
        question: str = Field(min_length=3, max_length=settings.max_question_chars)
        # Up to 3 earlier questions from this conversation (kept only in the
        # browser), so follow-ups like "can I extend it?" make sense.
        history: list[Annotated[str, Field(max_length=settings.max_question_chars)]] = Field(
            default_factory=list, max_length=3
        )

    @app.get("/health")  # not /healthz: Cloud Run reserves paths ending in "z"
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code, headers=exc.headers)

    @app.post("/v1/ask")
    def ask(body: AskRequest, request: Request) -> StreamingResponse:
        request_id = uuid.uuid4().hex[:12]
        ip = client_ip(request, source=settings.client_ip_source)
        identity = hash_identity(ip, settings.ip_hash_secret.get_secret_value())

        decision = limiter.hit(identity)
        if not decision.allowed:
            log.info(
                "rate_limited", request_id=request_id, limit=decision.limit and decision.limit.name
            )
            raise HTTPException(
                429,
                detail="You've asked a lot of questions. Please wait a little and try again.",
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )

        # With history, the same words can mean different things ("my
        # assessment" after visa vs tax questions), so only standalone
        # questions use the cache.
        if not body.history and (cached := cache.get(body.question)):
            log.info("answer_served", request_id=request_id, cached=True, cost_usd=0.0)
            return StreamingResponse(_replay(cached), media_type="text/event-stream")

        if spend.over_cap():
            log.warning(
                "spend_cap_reached", request_id=request_id, cap_usd=settings.daily_spend_cap_usd
            )
            raise HTTPException(503, detail=BUSY, headers={"Retry-After": "600"})
        if not slots.acquire(blocking=False):
            log.warning("concurrency_cap_reached", request_id=request_id)
            raise HTTPException(503, detail=BUSY, headers={"Retry-After": "10"})

        lease = SlotLease(slots)
        return StreamingResponse(
            _answer(body.question, body.history, request_id, lease),
            media_type="text/event-stream",
            background=BackgroundTask(lease.release),
        )

    def _replay(cached: dict[str, Any]) -> Iterator[str]:
        yield _sse("text", {"text": cached["answer"]})
        if cached.get("referral"):
            yield _sse("referral", cached["referral"])
        yield _sse("sources", cached["sources"])
        yield _sse("done", {"route": cached.get("route", "answered"), "cached": True})

    def _answer(
        question: str, history: list[str], request_id: str, lease: SlotLease
    ) -> Iterator[str]:
        """Runs in a worker thread; always releases its concurrency slot and records spend."""
        meter = UsageMeter()
        started = time.perf_counter()
        route = "error"
        try:
            final: dict[str, Any] = {}
            streamed = False
            config = {"configurable": {"on_usage": meter.add}}
            for mode, chunk in state["graph"].stream(
                {"question": question, "history": history},
                config,
                stream_mode=["custom", "values"],
            ):
                if mode == "custom":
                    streamed = True
                    yield _sse("text", {"text": chunk["text"]})
                else:
                    final = chunk
            if not streamed:
                yield _sse("text", {"text": final.get("answer", "")})
            sources = [{"title": p.title, "url": p.url} for p in final.get("sources", [])]
            route = final.get("route", "answered")
            referral = (
                referral_payload(final["referral"], final.get("suggestion"))
                if final.get("referral")
                else None
            )
            if referral:
                yield _sse("referral", referral)
            if final.get("options"):
                yield _sse("clarify", {"options": final["options"]})
            yield _sse("sources", sources)
            yield _sse("done", {"route": route, "cached": False})
            if not history and route in ("answered", "referral"):
                cache.set(
                    question,
                    {
                        "answer": final.get("answer", ""),
                        "sources": sources,
                        "referral": referral,
                        "route": route,
                    },
                )
        except anthropic.APIError as exc:
            log.error(
                "claude_api_error",
                request_id=request_id,
                error=type(exc).__name__,
                status=getattr(exc, "status_code", None),
            )
            yield _sse("error", {"message": FAILED})
        except Exception:
            log.exception("answer_failed", request_id=request_id)
            yield _sse("error", {"message": FAILED})
        finally:
            lease.release()
            spend.record(meter.total_usd)
            log.info(
                "answer_served",
                request_id=request_id,
                cached=False,
                route=route,
                claude_calls=len(meter.calls),
                cost_usd=round(meter.total_usd, 5),
                seconds=round(time.perf_counter() - started, 2),
            )

    return app
