"""Offline tool tests (respx-mocked)."""

import httpx
import pytest
import respx

from swiss_procurement_mcp.client import normalise_language
from swiss_procurement_mcp.constants import SIMAP_BASE
from swiss_procurement_mcp.server import (
    get_procurement_details,
    search_awards,
    search_cpv_codes,
    search_procurements,
)


@respx.mock
async def test_search_happy_path(search_payload):
    respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search").mock(
        return_value=httpx.Response(200, json=search_payload)
    )
    result = await search_procurements(canton="ZH", published_from="2026-07-01")

    assert result.provenance == "live_api"
    assert result.count == 1
    r = result.results[0]
    assert r.canton == "ZH"
    assert r.city == "Schlieren"
    assert r.title.startswith("Wohnen")


async def test_search_rejects_iso_canton_code():
    """Probe finding: canton ids are bare (ZH), not CH-ZH."""
    with pytest.raises(ValueError, match="bare id"):
        await search_procurements(canton="CH-ZH")


async def test_search_rejects_bad_pub_type():
    """Probe finding: 'award' is not a valid pub_type; the split values are."""
    with pytest.raises(ValueError, match="pub_type"):
        await search_procurements(pub_type="award")


@respx.mock
async def test_search_awards_uses_all_award_types(search_payload):
    route = respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search").mock(
        return_value=httpx.Response(200, json=search_payload)
    )
    await search_awards(canton="ZH")
    sent = str(route.calls.last.request.url)
    assert "award_tender" in sent
    assert "direct_award" in sent


@respx.mock
async def test_details_extracts_bkp_codes(detail_payload):
    respx.get(url__regex=rf"{SIMAP_BASE}/publications/v1/project/.*/publication-details/.*").mock(
        return_value=httpx.Response(200, json=detail_payload)
    )
    result = await get_procurement_details("proj-1", "pub-1")
    assert result.cpv_code == "45262650"
    assert result.bkp_codes == ["215.2"]
    assert result.offer_deadline == "2026-08-30"


@respx.mock
async def test_cpv_search():
    respx.get(f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
        return_value=httpx.Response(
            200, json={"codes": [{"code": "14000000", "label": {"de": "Bergbau, Basismetalle"}}]}
        )
    )
    result = await search_cpv_codes("Metall")
    assert result.system == "cpv"
    assert result.codes[0].code == "14000000"


def test_language_validation():
    assert normalise_language("DE") == "de"
    with pytest.raises(ValueError):
        normalise_language("es")
