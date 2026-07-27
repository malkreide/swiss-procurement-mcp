"""Structured JSON logging for swiss-procurement-mcp.

OBS-003: ported from the companion `amtsblatt-mcp`, with one change — the tools
here take ordinary keyword arguments rather than a single params model, so
`logged_tool` wraps `*args, **kwargs` and returns whatever the tool returns
(a Pydantic response model) instead of a string.

Everything goes to stderr. stdout carries the MCP protocol on a stdio transport,
so a stray line there corrupts the session.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import sys
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

logger = logging.getLogger("swiss_procurement_mcp")

R = TypeVar("R")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extras = getattr(record, "extra_fields", None)
        if isinstance(extras, dict):
            payload.update(extras)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Configure the swiss_procurement_mcp logger once. Idempotent."""
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
    logger.propagate = False


def log_event(level: int, msg: str, **fields: Any) -> None:
    logger.log(level, msg, extra={"extra_fields": fields})


def logged_tool(
    tool_name: str,
) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., Awaitable[R]]]:
    """Decorator: emits a single INFO event per tool call with latency + status.

    `functools.wraps` sets `__wrapped__`, which `inspect.signature` follows, so
    FastMCP still derives the tool's argument schema from the real signature.
    `tests/test_logging.py` asserts that rather than assuming it.
    """

    def wrap(fn: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
        @functools.wraps(fn)
        async def inner(*args: Any, **kwargs: Any) -> R:
            start = time.monotonic()
            status = "ok"
            try:
                return await fn(*args, **kwargs)
            except Exception:
                # Input-validation errors (ValueError from _check_limit/_check_text)
                # reach the client as tool errors; record them as such.
                status = "error"
                raise
            finally:
                log_event(
                    logging.INFO,
                    "tool_call",
                    tool=tool_name,
                    status=status,
                    latency_ms=int((time.monotonic() - start) * 1000),
                )

        return inner

    return wrap
