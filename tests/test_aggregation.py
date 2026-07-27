"""Tests for the aggregated search_procurements_detailed tool (ARCH-007)."""

import httpx
import pytest
import respx
from pydantic import ValidationError

from swiss_procurement_mcp.constants import SIMAP_BASE
from swiss_procurement_mcp.inputs import (
    DetailedSearchInput,
)
from swiss_procurement_mcp.server import search_procurements_detailed


@respx.mock
async def test_detailed_search_enriches_top_hits(search_payload, detail_payload):
    respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search").mock(
        return_value=httpx.Response(200, json=search_payload)
    )
    respx.get(url__regex=rf"{SIMAP_BASE}/publications/v1/project/.*/publication-details/.*").mock(
        return_value=httpx.Response(200, json=detail_payload)
    )

    result = await search_procurements_detailed(DetailedSearchInput(canton="ZH", top_n=3))

    # One search hit expanded to a full detail record in a single call.
    assert result.total_matched == 1
    assert result.count == 1
    assert result.match_type == "exact"
    detail = result.results[0]
    assert detail.bkp_codes == ["215.2"]
    assert detail.cpv_code == "45262650"
    assert detail.offer_deadline == "2026-08-30"


@respx.mock
async def test_detailed_search_empty(search_payload):
    respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search").mock(
        return_value=httpx.Response(200, json={"projects": [], "pagination": {}})
    )
    result = await search_procurements_detailed(DetailedSearchInput(canton="ZH"))
    assert result.total_matched == 0
    assert result.count == 0
    assert result.match_type == "none"
    assert result.results == []


async def test_detailed_search_rejects_bad_top_n():
    with pytest.raises(ValidationError) as low:
        DetailedSearchInput(canton="ZH", top_n=0)
    assert low.value.errors()[0]["type"] == "greater_than_equal"
    with pytest.raises(ValidationError) as high:
        DetailedSearchInput(canton="ZH", top_n=6)
    assert high.value.errors()[0]["type"] == "less_than_equal"
