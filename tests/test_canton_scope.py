"""The two canton semantics, and the filterless-call guard.

simap offers exactly one geographic filter, `orderAddressCantons`, and it means
"where the work is delivered". For ~60% of publications the structured order
address is absent, so that filter silently drops them. `issuedByOrganizations`
matches the procuring body instead and is the default here. See the measurement
in `constants.py`.
"""

import httpx
import pytest
import respx

from swiss_procurement_mcp.constants import CANTON_IDS, CANTON_INSTITUTION_IDS, SIMAP_BASE
from swiss_procurement_mcp.server import (
    search_awards,
    search_procurements,
    search_procurements_detailed,
)

SEARCH_URL = f"{SIMAP_BASE}/publications/v2/project/project-search"
ZH_INSTITUTION = CANTON_INSTITUTION_IDS["ZH"]


def test_every_canton_has_an_institution_id():
    """A missing id would make `canton=` raise KeyError for that canton."""
    assert set(CANTON_INSTITUTION_IDS) == set(CANTON_IDS)
    assert len(set(CANTON_INSTITUTION_IDS.values())) == len(CANTON_IDS), "ids must be distinct"


@respx.mock
async def test_default_matches_the_procuring_body(search_payload):
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload))
    result = await search_procurements(canton="ZH", published_from="2026-07-01")

    sent = str(route.calls.last.request.url)
    assert ZH_INSTITUTION in sent
    assert "orderAddressCantons" not in sent
    assert "PROCURING BODY" in (result.note or "")


@respx.mock
async def test_place_of_delivery_keeps_the_address_filter(search_payload):
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload))
    result = await search_procurements(
        canton="ZH", canton_match="place_of_delivery", published_from="2026-07-01"
    )

    sent = str(route.calls.last.request.url)
    assert "orderAddressCantons=ZH" in sent
    assert ZH_INSTITUTION not in sent
    # The gap has to be stated, or the narrower result looks authoritative.
    assert "60%" in (result.note or "")


@respx.mock
async def test_both_unions_two_queries_and_dedupes_by_project_id(search_payload):
    """The same project found by both filters must be reported once."""
    other = {
        "projects": [
            dict(search_payload["projects"][0]),  # same id -> duplicate
            {
                "id": "only-via-address",
                "title": {"de": "Bundesbau in Zürich"},
                "publicationId": "pub-2",
                "publicationDate": "2026-07-10",
                "orderAddress": {"cantonId": "ZH"},
            },
        ],
        "pagination": {"lastItem": "x", "itemsPerPage": 20},
    }
    route = respx.get(SEARCH_URL).mock(
        side_effect=[
            httpx.Response(200, json=search_payload),
            httpx.Response(200, json=other),
        ]
    )
    result = await search_procurements(
        canton="ZH", canton_match="both", published_from="2026-07-01"
    )

    assert route.call_count == 2
    assert result.count == 2, "one shared project plus one address-only project"
    ids = [r.project_id for r in result.results]
    assert len(ids) == len(set(ids))
    # Pagination is meaningless across two independent cursors.
    assert result.has_more is False
    assert result.next_cursor is None


@respx.mock
async def test_both_rejects_a_cursor(search_payload):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload))
    with pytest.raises(ValueError, match="pagination is unavailable"):
        await search_procurements(canton="ZH", canton_match="both", cursor="20260726|41694")


async def test_unknown_canton_match_is_rejected():
    with pytest.raises(ValueError, match="canton_match must be one of"):
        await search_procurements(canton="ZH", canton_match="by_vibes")


@respx.mock
async def test_awards_use_the_same_semantics(search_payload):
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload))
    await search_awards(canton="ZH", published_from="2026-07-01")

    sent = str(route.calls.last.request.url)
    assert ZH_INSTITUTION in sent
    assert "award_tender" in sent


@respx.mock
async def test_detailed_search_uses_the_same_semantics(search_payload, detail_payload):
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload))
    respx.get(url__regex=rf"{SIMAP_BASE}/publications/v1/project/.*/publication-details/.*").mock(
        return_value=httpx.Response(200, json=detail_payload)
    )
    result = await search_procurements_detailed(canton="ZH", top_n=1)

    assert ZH_INSTITUTION in str(route.calls[0].request.url)
    assert "PROCURING BODY" in (result.note or "")


# ---------------------------------------------------------------------------
# Filterless call
# ---------------------------------------------------------------------------


async def test_filterless_search_is_refused_with_the_real_reason():
    """simap returns 0 projects for an unfiltered query — not "no matches"."""
    with pytest.raises(ValueError, match="requires at least one filter"):
        await search_procurements()


@respx.mock
async def test_a_single_filter_is_enough(search_payload):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload))
    assert (await search_procurements(query="Schulhaus")).count == 1
    assert (await search_procurements(canton="ZH")).count == 1
