"""OBS-003: structured logging — stream, format, severity levels, per-call context.

Rewritten for the structlog implementation. The earlier version asserted stdlib
`logging` internals (handlers, formatters, `propagate`), which no longer exist;
the properties those tests were protecting are all still asserted here, just
against the observable behaviour rather than the mechanism.

The stdout test is the load-bearing one, and it runs in a subprocess on purpose.
On a stdio transport stdout carries the MCP protocol, so one stray line corrupts
the session — and that is exactly the kind of thing pytest's capture can hide
from an in-process assertion.
"""

from __future__ import annotations

import io
import json
import logging
import subprocess
import sys
import textwrap

import httpx
import pytest
import respx
import structlog
from pydantic import ValidationError

from swiss_procurement_mcp._log import configure_logging, log_event, logged_tool
from swiss_procurement_mcp.client import UpstreamError
from swiss_procurement_mcp.constants import SIMAP_BASE
from swiss_procurement_mcp.inputs import CpvSearchInput, SearchInput
from swiss_procurement_mcp.server import mcp, search_cpv_codes, search_procurements


@pytest.fixture
def events():
    """Capture real rendered output through the production processor chain.

    `structlog.testing.capture_logs` is not usable for the context assertions:
    it replaces the whole chain, dropping `merge_contextvars` and every
    correlation id with it. This reconfigures with `processor_chain()` — the
    same list production uses — at DEBUG, writing to a buffer.
    """
    buf = io.StringIO()
    configure_logging(level=logging.DEBUG, stream=buf, force=True)
    try:
        yield lambda: [json.loads(ln) for ln in buf.getvalue().splitlines() if ln.strip()]
    finally:
        structlog.contextvars.clear_contextvars()
        configure_logging(force=True)


# --- output stream --------------------------------------------------------


def test_logger_factory_targets_stderr() -> None:
    configure_logging()
    factory = structlog.get_config()["logger_factory"]
    assert factory._file is sys.stderr


def test_nothing_reaches_stdout(tmp_path) -> None:
    """Run a real process and check stdout is byte-for-byte empty.

    An in-process assertion cannot prove this: pytest replaces the streams, and
    a logger that captured the wrong one at import time would still look fine.
    """
    script = textwrap.dedent(
        """
        import asyncio, logging
        from swiss_procurement_mcp._log import configure_logging, log_event, logged_tool

        configure_logging()

        @logged_tool("probe")
        async def probe():
            log_event(logging.WARNING, "mid_call")
            return 1

        asyncio.run(probe())
        log_event(logging.ERROR, "after")
        """
    )
    path = tmp_path / "emit.py"
    path.write_text(script)
    proc = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "LOG_LEVEL": "DEBUG", "PYTHONPATH": "src"},
        cwd=".",
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "", f"stdout must stay empty, got: {proc.stdout!r}"

    lines = [ln for ln in proc.stderr.splitlines() if ln.strip()]
    assert lines, "expected events on stderr"
    for line in lines:
        payload = json.loads(line)  # every line must parse on its own
        assert "event" in payload and "level" in payload and "timestamp" in payload


# --- severity levels ------------------------------------------------------


async def test_all_four_severity_levels_are_used(events) -> None:
    """OBS-003 asks for at least four actively used. Prove it, don't claim it."""

    @logged_tool("probe_ok")
    async def ok():
        return 1

    @logged_tool("probe_err")
    async def err():
        raise UpstreamError("nope")

    await ok()  # debug + info
    with pytest.raises(UpstreamError):
        await err()  # debug + error
    log_event(logging.WARNING, "upstream_degraded", error_type="UpstreamError")

    levels = {e["level"] for e in events()}
    assert {"debug", "info", "warning", "error"} <= levels, levels


async def test_errored_call_logs_type_not_message(events) -> None:
    """OBS-002 keeps the message from the model; it stays out of the log too."""

    @logged_tool("probe")
    async def boom():
        raise UpstreamError("https://internal.example/x?token=abc123")

    with pytest.raises(UpstreamError):
        await boom()

    recorded = events()
    assert "token=abc123" not in json.dumps(recorded)
    errors = [e for e in recorded if e["level"] == "error"]
    assert errors and errors[0]["error_type"] == "UpstreamError"


# --- per-call context -----------------------------------------------------


@respx.mock
async def test_tool_call_carries_name_status_latency_and_correlation_id(events) -> None:
    respx.get(f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
        return_value=httpx.Response(200, json={"codes": []})
    )
    await search_cpv_codes(CpvSearchInput(query="metall", limit=5))

    done = [e for e in events() if e["event"] == "tool_call"]
    assert len(done) == 1
    assert done[0]["tool"] == "search_cpv_codes"
    assert done[0]["status"] == "ok"
    assert isinstance(done[0]["latency_ms"], int)
    assert len(done[0]["correlation_id"]) == 16


@respx.mock
async def test_correlation_id_is_stable_within_a_call(events) -> None:
    """The start and finish events must be joinable — that is the whole point."""
    respx.get(f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
        return_value=httpx.Response(200, json={"codes": []})
    )
    await search_cpv_codes(CpvSearchInput(query="metall", limit=5))

    ids = {e["correlation_id"] for e in events() if "correlation_id" in e}
    assert len(ids) == 1, f"one call produced {len(ids)} correlation ids"


@respx.mock
async def test_correlation_ids_differ_between_calls(events) -> None:
    respx.get(f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
        return_value=httpx.Response(200, json={"codes": []})
    )
    await search_cpv_codes(CpvSearchInput(query="metall", limit=5))
    await search_cpv_codes(CpvSearchInput(query="beton", limit=5))

    ids = {e["correlation_id"] for e in events() if e["event"] == "tool_call"}
    assert len(ids) == 2


async def test_degraded_warning_inherits_the_calls_correlation_id(events) -> None:
    """This is why structlog earns its dependency.

    `_degraded()` is called deep inside the tool and takes no context argument.
    contextvars is what lets its WARNING carry the same id as the surrounding
    call, so an operator can join the failure to the request that caused it.
    """

    @logged_tool("probe")
    async def calls_degraded():
        from swiss_procurement_mcp.server import _degraded

        _degraded(UpstreamError("boom"))
        return 1

    await calls_degraded()

    recorded = events()
    warn = next(e for e in recorded if e["event"] == "upstream_degraded")
    done = next(e for e in recorded if e["event"] == "tool_call")
    assert warn["correlation_id"] == done["correlation_id"]
    assert warn["tool"] == "probe"


async def test_context_does_not_leak_after_the_call(events) -> None:
    """A leaked contextvar would tag unrelated later events with a stale id.

    This must run against the real chain: under `capture_logs` the id is always
    absent, so the assertion would pass without proving anything.
    """

    @logged_tool("probe")
    async def probe():
        return 1

    await probe()
    log_event(logging.INFO, "unrelated")

    after = [e for e in events() if e["event"] == "unrelated"]
    assert len(after) == 1
    assert "correlation_id" not in after[0]
    assert "tool" not in after[0]


async def test_schema_violation_is_rejected_before_the_tool_runs(events) -> None:
    """The boundary rejects invalid input, so no tool call is ever accounted."""
    with pytest.raises(ValidationError):
        CpvSearchInput(query="metall", limit=0)
    assert [e for e in events() if e["event"] == "tool_call"] == []


async def test_error_inside_the_body_is_accounted(events) -> None:
    with pytest.raises(ValueError):
        await search_procurements(
            SearchInput(canton="ZH", canton_match="both", cursor="20260726|41694")
        )
    done = [e for e in events() if e["event"] == "tool_call"]
    assert len(done) == 1
    assert done[0]["status"] == "error"


def test_every_registered_tool_is_wrapped() -> None:
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
        assert hasattr(getattr(srv, name), "__wrapped__"), f"{name} is not wrapped"


# --- the wrapper must not eat the tool schema -----------------------------


async def test_decorator_preserves_the_tool_argument_schema() -> None:
    """`logged_tool` wraps *args/**kwargs; the SDK still needs the real signature.

    Without `functools.wraps` setting `__wrapped__` this silently degrades every
    tool to "no arguments", which no other test in this suite would catch.
    """
    tools = {t.name: t for t in await mcp.list_tools()}
    assert len(tools) == 9

    search = tools["search_procurements"].input_schema
    assert list(search["properties"]) == ["args"]
    fields = set(search["$defs"]["SearchInput"]["properties"])
    assert {"query", "canton", "canton_match", "cpv_codes", "language"} <= fields

    detail = tools["get_procurement_details"].input_schema["$defs"]["ProcurementDetailInput"]
    assert {"project_id", "publication_id"} <= set(detail["required"])

    assert tools["source_status"].input_schema["$defs"]["StatusInput"]["properties"] == {}


async def test_decorator_preserves_return_values() -> None:
    with respx.mock:
        respx.get(f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
            return_value=httpx.Response(200, json={"codes": []})
        )
        result = await search_cpv_codes(CpvSearchInput(query="metall", limit=5))
    assert result.system == "cpv"
    assert result.codes == []


def test_configure_logging_is_idempotent() -> None:
    configure_logging()
    first = structlog.get_config()["processors"]
    configure_logging()
    assert structlog.get_config()["processors"] is first
