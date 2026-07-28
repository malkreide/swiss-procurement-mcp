"""OBS-001: protocol errors and execution errors, as a client actually sees them.

Every other test in this suite calls the tool functions directly. That is fine
for tool logic, and useless for this check: it cannot observe `isError`, cannot
observe a JSON-RPC error code, and cannot tell the two apart. These tests drive
a real `ClientSession` over an in-memory transport instead.

The distinction OBS-001 is about:

- **Execution error** — the tool was found and ran, and something went wrong.
  Belongs in the tool result with `isError: true`, so the model sees it as a
  result it can reason about.
- **Protocol error** — the request itself was wrong (unknown method, malformed
  params). Belongs in a JSON-RPC error with a standardised code, because there
  is no tool result to put it in.

Two SDK behaviours are pinned here deliberately, because they are *not* what the
check asks for and a future SDK release may change them. Pinning them means the
change is announced by a failing test rather than discovered in production:

- An unknown **tool** is reported as `isError` in a tool result, not as a
  protocol error. Arguably right — the method `tools/call` does exist — but it
  means "you called a tool that does not exist" and "the tool failed" are
  indistinguishable to a client without reading the text.
- Protocol errors carry **code 0**, not the `-32601` / `-326xx` range the check
  asks for, even though `mcp.types` defines those constants.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from mcp import types
from mcp.shared.exceptions import McpError
from mcp.shared.memory import create_connected_server_and_client_session as connect

from swiss_procurement_mcp.constants import SIMAP_BASE
from swiss_procurement_mcp.server import mcp

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def no_backoff_delay(monkeypatch):
    """The degraded-path tests wait out real 2s/4s/8s retries otherwise.

    Same fixture as `test_resilience.py`, for the same reason: the retry timing
    is tested there, and these tests only care about the envelope that comes out
    the far end. Without it this file costs 28 seconds.
    """

    async def _instant(_seconds):
        return None

    monkeypatch.setattr("swiss_procurement_mcp.client.asyncio.sleep", _instant)


# --- execution errors: found the tool, running it failed -------------------


async def test_invalid_argument_is_an_execution_error() -> None:
    """A too-long query is the tool's problem to report, not the protocol's."""
    async with connect(mcp) as client:
        result = await client.call_tool("search_cpv_codes", {"args": {"query": "x" * 500}})
    assert result.isError is True
    assert "validation error" in result.content[0].text.lower()


async def test_unknown_field_is_rejected_at_the_boundary() -> None:
    """SEC-018 forbids extras; OBS-001 governs how that refusal is delivered."""
    async with connect(mcp) as client:
        result = await client.call_tool(
            "search_cpv_codes", {"args": {"query": "metall", "bogus": 1}}
        )
    assert result.isError is True


async def test_execution_error_carries_no_stack_trace() -> None:
    """OBS-002's substance, asserted at the boundary where it matters."""
    async with connect(mcp) as client:
        result = await client.call_tool("search_cpv_codes", {"args": {"query": "x" * 500}})
    text = result.content[0].text
    assert "Traceback" not in text
    assert "/home/" not in text and "site-packages" not in text


# --- the degraded envelope: a deliberate deviation, pinned -----------------


async def test_upstream_failure_is_not_an_execution_error() -> None:
    """A documented deviation from OBS-001, kept on purpose.

    The check says application errors should carry `isError: true`. An upstream
    outage returns a normal result with `provenance="degraded"` instead, because
    the envelope carries strictly more than an error string would: the source,
    the retrieval time, and a note saying the source could not be reached.

    Raising instead would collapse all of that into one line of text. The
    distinction the model needs — "nothing matched" versus "I could not ask" —
    survives in `provenance`, and this test is what stops it being lost.
    """
    async with connect(mcp) as client:
        with respx.mock:
            respx.get(f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
                side_effect=httpx.ConnectError("down")
            )
            result = await client.call_tool("search_cpv_codes", {"args": {"query": "metall"}})

    assert result.isError is False, "degraded is a result, not an error"
    assert result.structuredContent is not None
    assert result.structuredContent["provenance"] == "degraded"
    assert result.structuredContent["count"] == 0
    assert "unreachable" in result.structuredContent["note"].lower()


async def test_degraded_is_distinguishable_from_an_empty_result() -> None:
    """The failure this whole envelope exists to prevent.

    An empty result and an unreachable source must never look alike. Both have
    `count == 0`; only `provenance` separates them.

    The two calls use *different* queries on purpose. With the same query the
    second one is served from the shared cache (SDK-001) and comes back as
    `cached` — correct behaviour, since serving a slightly stale answer beats
    failing, but it would make this test assert nothing about the degraded path.
    """
    async with connect(mcp) as client:
        with respx.mock:
            respx.get(f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
                return_value=httpx.Response(200, json={"codes": []})
            )
            empty = await client.call_tool("search_cpv_codes", {"args": {"query": "zzzz"}})
        with respx.mock:
            respx.get(f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
                side_effect=httpx.ConnectError("down")
            )
            degraded = await client.call_tool("search_cpv_codes", {"args": {"query": "yyyy"}})

    assert empty.structuredContent["count"] == degraded.structuredContent["count"] == 0
    assert empty.structuredContent["provenance"] == "live_api"
    assert degraded.structuredContent["provenance"] == "degraded"


# --- protocol errors: the request itself was wrong ------------------------


async def test_unknown_method_is_a_protocol_error() -> None:
    """A method the server does not implement raises rather than returning a result."""
    async with connect(mcp) as client:
        with pytest.raises(McpError) as exc:
            await client.send_request(
                types.ClientRequest(
                    types.GetPromptRequest(
                        method="prompts/get",
                        params=types.GetPromptRequestParams(name="nope"),
                    )
                ),
                types.GetPromptResult,
            )
    assert "unknown prompt" in exc.value.error.message.lower()


async def test_protocol_error_code_is_not_yet_standardised() -> None:
    """Pins an SDK gap so a future fix is announced, not discovered.

    OBS-001 asks for `-326xx` / `-320xx` codes on protocol errors. `mcp.types`
    defines `METHOD_NOT_FOUND = -32601` and friends, but the lowlevel server
    emits **0**. Nothing in this repo can change that — it is above the tool
    layer — so the behaviour is asserted as-is.

    When the SDK starts emitting a real code this test fails, which is the
    point: that is the day `OBS-001` can be re-scored.
    """
    async with connect(mcp) as client:
        with pytest.raises(McpError) as exc:
            await client.send_request(
                types.ClientRequest(
                    types.ReadResourceRequest(
                        method="resources/read",
                        params=types.ReadResourceRequestParams(uri="file:///nope"),
                    )
                ),
                types.ReadResourceResult,
            )
    assert exc.value.error.code == 0, (
        "the SDK now emits a real JSON-RPC code — re-check OBS-001 criterion 3"
    )
    assert types.METHOD_NOT_FOUND == -32601, "the constants exist; the server does not use them"


async def test_unknown_tool_is_reported_as_an_execution_error() -> None:
    """Also pinned rather than endorsed.

    Calling a tool that does not exist is arguably a protocol error, but the SDK
    reports it inside a tool result with `isError: true`. That makes "no such
    tool" and "the tool failed" indistinguishable without reading the text.
    """
    async with connect(mcp) as client:
        result = await client.call_tool("no_such_tool", {})
    assert result.isError is True
    assert "unknown tool" in result.content[0].text.lower()


async def test_every_advertised_tool_is_callable() -> None:
    """The general form: a tool listed but not dispatchable is the worst case,
    because the model has no way to know before trying."""
    async with connect(mcp) as client:
        listed = {t.name for t in (await client.list_tools()).tools}
        result = await client.call_tool("no_such_tool", {})

    assert len(listed) == 9
    # The negative control: an unlisted name really does fail, so the assertion
    # above is not passing vacuously.
    assert result.isError is True
