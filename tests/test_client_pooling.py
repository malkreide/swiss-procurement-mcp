"""SDK-001: one pooled HTTP client behind the server lifespan.

Every tool used to open its own `httpx.AsyncClient` via `async with
SimapClient()`. The connection cost was the obvious part. The part that made it
a correctness bug rather than a performance one is that `_cache` and the session
cookie jar live on the instance: a client that dies when the tool returns can
never serve a cache hit, so `_cached` was dead code wearing the shape of a
working cache.

`test_repeat_search_hits_the_api_once` is the test that would have caught the
original defect — it asserts the payoff, not the plumbing.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from swiss_procurement_mcp import client as client_mod
from swiss_procurement_mcp.client import close_client, get_client
from swiss_procurement_mcp.constants import SIMAP_BASE
from swiss_procurement_mcp.inputs import SearchInput
from swiss_procurement_mcp.server import mcp, search_procurements

pytestmark = pytest.mark.asyncio


async def test_get_client_returns_the_same_instance() -> None:
    assert get_client() is get_client()


async def test_get_client_reuses_the_same_httpx_client() -> None:
    """The SimapClient wrapper being shared is worth nothing if the socket is not."""
    assert get_client()._http is get_client()._http


@respx.mock
async def test_two_tool_calls_share_one_httpx_client(search_payload) -> None:
    route = respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search").mock(
        return_value=httpx.Response(200, json=search_payload)
    )
    await search_procurements(SearchInput(query="Metall"))
    first = get_client()._http
    await search_procurements(SearchInput(query="Fassade"))
    assert get_client()._http is first
    assert route.call_count == 2, "distinct queries must not collapse into one cache key"


@respx.mock
async def test_repeat_search_hits_the_api_once(search_payload) -> None:
    """The behavioural payoff: the response cache now survives the tool call.

    Before SDK-001 this test would see two upstream requests, because the
    client holding the cache was thrown away between calls.
    """
    route = respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search").mock(
        return_value=httpx.Response(200, json=search_payload)
    )
    first = await search_procurements(SearchInput(query="Metall"))
    second = await search_procurements(SearchInput(query="Metall"))

    assert route.call_count == 1, "identical search should be served from the shared cache"
    assert first.count == second.count
    assert first.provenance == "live_api"
    assert second.provenance == "cached", "the second call must be reported as a cache hit"


async def test_close_client_releases_and_allows_a_fresh_one() -> None:
    stale = get_client()._http
    await close_client()
    assert stale.is_closed
    assert get_client()._http is not stale


async def test_get_client_recovers_from_an_externally_closed_client() -> None:
    """A closed client must not be handed back — that would raise on first use."""
    victim = get_client()
    await victim._http.aclose()
    assert get_client()._http.is_closed is False


async def test_server_is_constructed_with_a_lifespan() -> None:
    """Without this wiring nothing ever closes the pooled connections.

    Asserted through the server object rather than by reading the source, so
    dropping the `lifespan=` argument fails here rather than passing quietly.
    """
    from swiss_procurement_mcp.server import _lifespan

    # `mcp` 2.0 renamed the internal handle (`_mcp_server` -> `_lowlevel_server`)
    # and exposes the user-supplied lifespan on the settings object, which is
    # the more direct thing to assert: not merely "some lifespan is wired" but
    # "ours is".
    assert mcp.settings.lifespan is _lifespan, "the pooled client has no shutdown hook"
    assert mcp._lowlevel_server.lifespan is not None


async def test_reset_client_is_synchronous_and_drops_the_instance() -> None:
    before = get_client()
    client_mod.reset_client()
    assert get_client() is not before
