"""OBS-001: protocol errors and execution errors, as a client actually sees them.

Every other test in this suite calls the tool functions directly. That is fine
for tool logic, and useless for this check: it cannot observe `is_error`, cannot
observe a JSON-RPC error code, and cannot tell the two apart. These tests drive
a real client over an in-memory transport instead.

The distinction OBS-001 is about:

- **Execution error** — the tool was found and ran, and something went wrong.
  Belongs in the tool result with `is_error: true`, so the model sees it as a
  result it can reason about.
- **Protocol error** — the request itself was wrong (unknown method, malformed
  params). Belongs in a JSON-RPC error with a standardised code, because there
  is no tool result to put it in.

Under `mcp` 1.x the second half of that was unenforceable: the lowlevel server
emitted error **code 0** on every protocol error, and this file pinned that with
two tests whose stated purpose was to fail the day the SDK started emitting real
codes. `mcp` 2.0 does, so they failed, so they were rewritten into the
assertions below. That is the mechanism working as designed rather than a test
being repaired.

One deviation is still pinned rather than endorsed: an unknown **tool** is
reported as `is_error` in a tool result, not as a protocol error. Arguably right
— the method `tools/call` does exist — but it means "you called a tool that does
not exist" and "the tool failed" stay indistinguishable to a client without
reading the text.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from mcp import Client, MCPError

from swiss_procurement_mcp import client as _client
from swiss_procurement_mcp.constants import SIMAP_BASE
from swiss_procurement_mcp.server import mcp

pytestmark = pytest.mark.asyncio

# The JSON-RPC codes a protocol fault may legitimately carry. Spec `2026-07-28`
# partitions the server-error range explicitly — -32000..-32019 stays
# implementation-defined, -32020..-32099 belongs to the MCP specification — and
# the pre-defined JSON-RPC codes below sit outside both.
PROTOCOL_ERROR_CODES = frozenset({-32700, -32600, -32601, -32602, -32603})


@pytest.fixture(autouse=True)
def no_backoff_delay(monkeypatch):
    """The degraded-path tests wait out real 2s/4s/8s retries otherwise.

    Same fixture as `test_resilience.py`, for the same reason: the retry timing
    is tested there, and these tests only care about the envelope that comes out
    the far end. Without it this file costs 28 seconds.
    """

    async def _instant(_seconds):
        return None

    monkeypatch.setattr(_client, "_sleep", _instant)


# --- execution errors: found the tool, running it failed -------------------


async def test_invalid_argument_is_an_execution_error() -> None:
    """A too-long query is the tool's problem to report, not the protocol's."""
    async with Client(mcp) as client:
        result = await client.call_tool("search_cpv_codes", {"args": {"query": "x" * 500}})
    assert result.is_error is True
    assert "validation error" in result.content[0].text.lower()


async def test_unknown_field_is_rejected_at_the_boundary() -> None:
    """SEC-018 forbids extras; OBS-001 governs how that refusal is delivered."""
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_cpv_codes", {"args": {"query": "metall", "bogus": 1}}
        )
    assert result.is_error is True


async def test_execution_error_carries_no_stack_trace() -> None:
    """OBS-002's substance, asserted at the boundary where it matters.

    `mask_error_details` does not exist in `mcp` 2.0.0 either — it was absent in
    1.x and the major version did not introduce it. The guarantee is checked
    here rather than configured anywhere.
    """
    async with Client(mcp) as client:
        result = await client.call_tool("search_cpv_codes", {"args": {"query": "x" * 500}})
    text = result.content[0].text
    assert "Traceback" not in text
    assert "/home/" not in text and "site-packages" not in text


# --- the degraded envelope: a deliberate deviation, pinned -----------------


async def test_upstream_failure_is_not_an_execution_error() -> None:
    """A documented deviation from OBS-001, kept on purpose.

    The check says application errors should carry `is_error: true`. An upstream
    outage returns a normal result with `provenance="degraded"` instead, because
    the envelope carries strictly more than an error string would: the source,
    the retrieval time, and a note saying the source could not be reached.

    Raising instead would collapse all of that into one line of text. The
    distinction the model needs — "nothing matched" versus "I could not ask" —
    survives in `provenance`, and this test is what stops it being lost.
    """
    async with Client(mcp) as client:
        with respx.mock:
            respx.get(f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
                side_effect=httpx.ConnectError("down")
            )
            result = await client.call_tool("search_cpv_codes", {"args": {"query": "metall"}})

    assert result.is_error is False, "degraded is a result, not an error"
    assert result.structured_content is not None
    assert result.structured_content["provenance"] == "degraded"
    assert result.structured_content["count"] == 0
    assert "unreachable" in result.structured_content["note"].lower()


async def test_degraded_is_distinguishable_from_an_empty_result() -> None:
    """The failure this whole envelope exists to prevent.

    An empty result and an unreachable source must never look alike. Both have
    `count == 0`; only `provenance` separates them.

    The two calls use *different* queries on purpose. With the same query the
    second one is served from the shared cache (SDK-001) and comes back as
    `cached` — correct behaviour, since serving a slightly stale answer beats
    failing, but it would make this test assert nothing about the degraded path.
    """
    async with Client(mcp) as client:
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

    assert empty.structured_content["count"] == degraded.structured_content["count"] == 0
    assert empty.structured_content["provenance"] == "live_api"
    assert degraded.structured_content["provenance"] == "degraded"


# --- protocol errors: the request itself was wrong ------------------------


async def test_protocol_error_carries_a_standardised_code() -> None:
    """OBS-001 criterion 3 — and the reason this server moved to `mcp` 2.x.

    Under 1.x every protocol error came back with `code == 0`, not a JSON-RPC
    code at all, even though `mcp.types` defined the constants. The criterion
    could not pass, so the gap was pinned by a test instead of papered over.

    2.0 emits real codes. A resource that does not exist is `-32602`
    (INVALID_PARAMS), which is also the spec's own correction: `2026-07-28`
    moved resource-not-found from `-32002` to `-32602` to align with JSON-RPC.
    """
    async with Client(mcp) as client:
        with pytest.raises(MCPError) as exc:
            await client.read_resource("file:///nope")

    assert exc.value.error.code == -32602
    assert exc.value.error.code in PROTOCOL_ERROR_CODES


async def test_no_protocol_error_falls_outside_the_standard_codes() -> None:
    """The general form, so a regression to code 0 cannot pass unnoticed.

    `get_prompt` answers `-32603` (INTERNAL_ERROR) rather than something
    prompt-specific. In range, so it passes — but worth naming as imprecise: the
    request was well-formed and named a prompt that does not exist, which is
    nearer INVALID_PARAMS than an internal fault. Asserted against the range as
    well as the literals, so the imprecision is recorded without being frozen.
    """
    async with Client(mcp) as client:
        codes = []
        for call in (
            lambda: client.read_resource("file:///nope"),
            lambda: client.get_prompt("no_such_prompt"),
        ):
            with pytest.raises(MCPError) as exc:
                await call()
            codes.append(exc.value.error.code)

    assert codes == [-32602, -32603]
    assert all(c in PROTOCOL_ERROR_CODES for c in codes), codes
    assert 0 not in codes, "code 0 is back — OBS-001 has regressed to the 1.x behaviour"


async def test_protocol_error_message_leaks_nothing_internal() -> None:
    """OBS-002 again, on the path that got *more* conservative in 2.0.

    1.x answered `get_prompt` with the raw `ValueError` text ("Unknown prompt:
    nope"). 2.0 answers "Internal server error" and keeps the detail server-side.
    Less helpful to a developer reading logs, better for a boundary that faces a
    model.
    """
    async with Client(mcp) as client:
        with pytest.raises(MCPError) as exc:
            await client.get_prompt("no_such_prompt")

    message = exc.value.error.message
    assert "Traceback" not in message
    assert "/home/" not in message and "site-packages" not in message


async def test_unknown_tool_is_reported_as_an_execution_error() -> None:
    """Still pinned rather than endorsed, and unchanged by the migration.

    Calling a tool that does not exist is arguably a protocol error, but the SDK
    reports it inside a tool result with `is_error: true` — in 2.0 exactly as in
    1.x. That makes "no such tool" and "the tool failed" indistinguishable
    without reading the text.
    """
    async with Client(mcp) as client:
        result = await client.call_tool("no_such_tool", {})
    assert result.is_error is True
    assert "unknown tool" in result.content[0].text.lower()


async def test_every_advertised_tool_is_callable() -> None:
    """The general form: a tool listed but not dispatchable is the worst case,
    because the model has no way to know before trying."""
    async with Client(mcp) as client:
        listed = {t.name for t in (await client.list_tools()).tools}
        result = await client.call_tool("no_such_tool", {})

    assert len(listed) == 9
    # The negative control: an unlisted name really does fail, so the assertion
    # above is not passing vacuously.
    assert result.is_error is True
