"""OBS-003: structured logging — output stream, format, severity, per-call context.

The 2026-07-27 re-audit graded OBS-003 down from `partial` to `fail`: this server
had no logging at all, meeting exactly one of five criteria ("no `print()`"). The
mechanism is ported from the companion `amtsblatt-mcp`; these tests pin the four
properties that make it worth having.

The stdout test is the load-bearing one. On a stdio transport stdout carries the
MCP protocol, so a single stray line there corrupts the session — a logging port
that gets this wrong is worse than no logging.
"""

from __future__ import annotations

import json
import logging
import sys

import httpx
import pytest
import respx

from swiss_procurement_mcp._log import configure_logging, log_event, logged_tool, logger
from swiss_procurement_mcp.client import UpstreamError
from swiss_procurement_mcp.constants import SIMAP_BASE
from swiss_procurement_mcp.server import mcp, search_cpv_codes


@pytest.fixture
def caplog_json(caplog):
    """Capture records off our logger, which is `propagate = False` by design."""
    caplog.set_level(logging.INFO, logger="swiss_procurement_mcp")
    logger.propagate = True
    yield caplog
    logger.propagate = False


def _events(caplog) -> list[dict]:
    out = []
    for rec in caplog.records:
        fields = getattr(rec, "extra_fields", {}) or {}
        out.append({"msg": rec.getMessage(), "level": rec.levelname, **fields})
    return out


# --- output stream --------------------------------------------------------


def test_handler_writes_to_stderr_never_stdout():
    """Re-run the constructor path: the handler installed at import time holds
    whatever `sys.stderr` was then, which pytest's capture has since replaced."""
    saved = logger.handlers[:]
    logger.handlers.clear()
    try:
        configure_logging()
        assert logger.handlers, "configure_logging() installed no handler"
        assert logger.handlers[0].stream is sys.stderr
    finally:
        logger.handlers[:] = saved


def test_no_handler_targets_stdout():
    """Holds for the import-time handler too, whatever capture is in effect."""
    configure_logging()
    for h in logger.handlers:
        stream = getattr(h, "stream", None)
        assert stream is not sys.stdout
        assert stream is not sys.__stdout__
        assert getattr(stream, "name", None) != "<stdout>"


def test_logger_does_not_propagate_to_root():
    """Root handlers commonly target stdout; propagation would leak there."""
    configure_logging()
    assert logger.propagate is False


def test_configure_logging_is_idempotent():
    configure_logging()
    before = len(logger.handlers)
    configure_logging()
    assert len(logger.handlers) == before


# --- format ---------------------------------------------------------------


def test_records_format_as_single_line_json():
    configure_logging()
    formatter = logger.handlers[0].formatter
    record = logger.makeRecord(
        logger.name, logging.INFO, __file__, 0, "tool_call", (), None
    )
    record.extra_fields = {"tool": "search_procurements", "status": "ok", "latency_ms": 7}
    line = formatter.format(record)

    assert "\n" not in line, "a multi-line record breaks line-delimited JSON parsing"
    payload = json.loads(line)
    assert payload["msg"] == "tool_call"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "swiss_procurement_mcp"
    assert payload["tool"] == "search_procurements"
    assert payload["latency_ms"] == 7
    assert "ts" in payload


def test_non_ascii_survives_the_formatter():
    """Procurement titles are German, French and Italian."""
    configure_logging()
    formatter = logger.handlers[0].formatter
    record = logger.makeRecord(logger.name, logging.INFO, __file__, 0, "x", (), None)
    record.extra_fields = {"title": "Metallverkleidung Zürich"}
    assert json.loads(formatter.format(record))["title"] == "Metallverkleidung Zürich"


# --- severity levels ------------------------------------------------------


def test_degraded_upstream_logs_at_warning(caplog_json):
    from swiss_procurement_mcp.server import _degraded

    _degraded(UpstreamError("connect timeout"))

    warnings = [e for e in _events(caplog_json) if e["level"] == "WARNING"]
    assert warnings, "an upstream failure produced no WARNING"
    assert warnings[0]["msg"] == "upstream_degraded"
    assert warnings[0]["error_type"] == "UpstreamError"


def test_degraded_log_does_not_leak_the_exception_message(caplog_json):
    """OBS-002 keeps the message from the model; it stays out of the log too."""
    from swiss_procurement_mcp.server import _degraded

    _degraded(UpstreamError("https://internal.example/secret?token=abc123"))

    for event in _events(caplog_json):
        assert "token=abc123" not in json.dumps(event)


# --- per-call context -----------------------------------------------------


@respx.mock
async def test_successful_tool_call_logs_name_status_and_latency(caplog_json):
    respx.get(f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
        return_value=httpx.Response(200, json={"codes": []})
    )
    await search_cpv_codes("metall", limit=5)

    calls = [e for e in _events(caplog_json) if e["msg"] == "tool_call"]
    assert len(calls) == 1
    assert calls[0]["tool"] == "search_cpv_codes"
    assert calls[0]["status"] == "ok"
    assert isinstance(calls[0]["latency_ms"], int)


async def test_failed_tool_call_logs_status_error(caplog_json):
    """A rejected input still produces exactly one accounted call."""
    with pytest.raises(ValueError):
        await search_cpv_codes("metall", limit=0)

    calls = [e for e in _events(caplog_json) if e["msg"] == "tool_call"]
    assert len(calls) == 1
    assert calls[0]["tool"] == "search_cpv_codes"
    assert calls[0]["status"] == "error"


def test_every_registered_tool_is_wrapped():
    """A tool added without @logged_tool logs nothing — catch that here."""
    import swiss_procurement_mcp.server as srv

    names = [
        "search_procurements",
        "search_procurements_detailed",
        "search_awards",
        "get_procurement_details",
        "get_publication_history",
        "search_cpv_codes",
        "search_construction_codes",
        "find_procurement_office",
        "source_status",
    ]
    for name in names:
        fn = getattr(srv, name)
        assert hasattr(fn, "__wrapped__"), f"{name} is not wrapped by @logged_tool"


# --- the wrapper must not eat the tool schema -----------------------------


async def test_decorator_preserves_the_tool_argument_schema():
    """`logged_tool` wraps *args/**kwargs; FastMCP still needs the real signature.

    Without `functools.wraps` setting `__wrapped__` this silently degrades every
    tool to "no arguments", which no other test in this suite would catch.
    """
    tools = {t.name: t for t in await mcp.list_tools()}
    assert len(tools) == 9

    params = set(tools["search_procurements"].inputSchema.get("properties", {}))
    assert {"query", "canton", "canton_match", "cpv_codes", "language"} <= params

    required = tools["get_procurement_details"].inputSchema.get("required", [])
    assert {"project_id", "publication_id"} <= set(required)

    assert tools["source_status"].inputSchema.get("properties", {}) == {}


async def test_decorator_preserves_return_values():
    """The amtsblatt original is typed to `str`; these tools return models."""
    with respx.mock:
        respx.get(f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
            return_value=httpx.Response(200, json={"codes": []})
        )
        result = await search_cpv_codes("metall", limit=5)
    assert result.system == "cpv"
    assert result.codes == []


def test_log_event_accepts_arbitrary_fields():
    configure_logging()
    log_event(logging.INFO, "probe", a=1, b="two")  # must not raise


async def test_logged_tool_reraises_the_original_exception():
    @logged_tool("probe")
    async def boom() -> None:
        raise UpstreamError("nope")

    with pytest.raises(UpstreamError, match="nope"):
        await boom()
