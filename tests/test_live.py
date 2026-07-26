"""Live tests against the real simap.ch API. Excluded from CI."""

import pytest

from swiss_procurement_mcp.server import (
    get_procurement_details,
    search_awards,
    search_cpv_codes,
    search_procurements,
    source_status,
)

pytestmark = pytest.mark.live


async def test_live_search_zurich():
    result = await search_procurements(canton="ZH", published_from="2026-01-01")
    assert result.count > 0
    assert all(r.canton == "ZH" for r in result.results if r.canton)


async def test_live_details_roundtrip():
    search = await search_procurements(canton="ZH", published_from="2026-01-01")
    first = search.results[0]
    detail = await get_procurement_details(first.project_id, first.publication_id)
    assert detail.title


async def test_live_cpv_search():
    result = await search_cpv_codes("Metall")
    assert result.count > 0


async def test_live_awards():
    result = await search_awards(canton="ZH", published_from="2026-01-01")
    assert result.provenance == "live_api"


async def test_live_status():
    assert (await source_status()).all_healthy is True
