"""Retry, degradation and 4xx-handling (no network)."""

import httpx
import pytest
import respx

from swiss_procurement_mcp.constants import SIMAP_BASE
from swiss_procurement_mcp.inputs import (
    SearchInput,
    StatusInput,
)
from swiss_procurement_mcp.server import search_procurements, source_status


@pytest.fixture(autouse=True)
def no_backoff_delay(monkeypatch):
    async def _instant(_seconds):
        return None

    monkeypatch.setattr("swiss_procurement_mcp.client.asyncio.sleep", _instant)


@respx.mock
async def test_retries_then_succeeds(search_payload):
    route = respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json=search_payload)]
    )
    result = await search_procurements(SearchInput(canton="ZH"))
    assert route.call_count == 2
    assert result.count == 1


@respx.mock
async def test_network_failure_degrades():
    respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search").mock(
        side_effect=httpx.ConnectTimeout("down")
    )
    result = await search_procurements(SearchInput(canton="ZH"))
    assert result.provenance == "degraded"
    assert result.results == []
    assert "retry" in (result.note or "").lower()


@respx.mock
async def test_400_not_retried():
    """E0025 (bad enum / missing lang) is a client error — one attempt only."""
    route = respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search").mock(
        return_value=httpx.Response(400, json={"errorCode": "E0025"})
    )
    result = await search_procurements(SearchInput(canton="ZH"))
    assert route.call_count == 1
    assert result.provenance == "degraded"


@respx.mock
async def test_source_status_outage():
    respx.get(f"{SIMAP_BASE}/cantons/v1").mock(side_effect=httpx.ConnectError("boom"))
    result = await source_status(StatusInput())
    assert result.all_healthy is False
