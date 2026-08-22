"""SEP-2549: `tools/list` must answer with a freshness hint, not with silence.

Spec `2026-07-28` gives every cacheable result a `ttlMs` and a `cacheScope`. The
SDK fills neither on its own — `CacheHint()` defaults to `ttl_ms=0`,
`scope="private"`, the wire encoding of "already stale, never share it". A
server that passes no `cache_hints` therefore does not stay neutral: it tells
every client to re-list on every connection, for a list that cannot change while
the process runs.

Asserted over a real `ClientSession` rather than by reading `CACHE_HINTS` back
out of the module. The constant is the input to the behaviour, not the
behaviour: `MCPServer` applies the hint per field and only to results whose
handler left it unset, so reading the dict would pass just as happily if the
argument were dropped at the constructor.
"""

from __future__ import annotations

from mcp import Client
from mcp.server.caching import CACHEABLE_METHODS
from mcp.server.mcpserver import MCPServer

from swiss_procurement_mcp.server import CACHE_HINTS, LIST_CACHE_TTL_MS, mcp


async def test_the_tool_list_carries_the_ttl() -> None:
    async with Client(mcp) as client:
        result = await client.list_tools()

    assert result.ttl_ms == LIST_CACHE_TTL_MS, (
        f"tools/list answered with ttlMs={result.ttl_ms}; clients re-list on every "
        "connection when this is 0"
    )


async def test_the_tool_list_is_shareable_across_authorization_contexts() -> None:
    """`public` is a claim about this server, so it is worth stating out loud:
    the nine tools are registered at import and the list is identical for every
    caller, so a shared cache of it discloses nothing."""
    async with Client(mcp) as client:
        result = await client.list_tools()

    assert result.cache_scope == "public"


async def test_a_server_without_the_hints_says_nothing() -> None:
    """The negative control: same SDK, same client, no `cache_hints`. If this
    ever starts returning our TTL, the SDK grew a default of its own and the
    tests above stopped proving that we set it."""
    async with Client(MCPServer("control")) as client:
        result = await client.list_tools()

    assert result.ttl_ms == 0
    assert result.cache_scope == "private"


def test_the_hint_is_long_enough_to_be_worth_sending() -> None:
    """Guards the direction of a future edit rather than the exact number:
    dropping the TTL towards zero silently restores the behaviour this file
    exists to prevent."""
    assert LIST_CACHE_TTL_MS >= 60_000


def test_every_hinted_method_is_one_the_spec_can_cache() -> None:
    """`MCPServer` rejects an unknown key at construction, so a typo would be an
    import error surfacing as a collection error somewhere unrelated. Named
    here instead."""
    unknown = sorted(set(CACHE_HINTS) - set(CACHEABLE_METHODS))
    assert not unknown, f"not cacheable per spec 2026-07-28: {unknown}"


def test_no_hint_describes_a_surface_this_server_does_not_have() -> None:
    """`prompts/list` and `resources/list` are cacheable methods, and hinting at
    them would be a lie about what is registered. The day either is registered,
    this test is the reminder to hint at it deliberately."""
    assert set(CACHE_HINTS) == {"tools/list", "server/discover"}
