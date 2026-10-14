"""Structured logging.

In dev, logs are pretty-printed for humans. In prod they're JSON, one
object per line, so a log platform can filter on fields like
`event="retrieval_done" latency_ms>2000` instead of grepping text.
"""

import logging

import structlog

from askoz.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if settings.env == "prod"
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # carries request_id etc. across calls
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[settings.log_level.upper()]
        ),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
