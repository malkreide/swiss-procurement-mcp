"""Tests for the 0.2.0 hardening: input bounds, egress guard, match_type, and
coverage for the three tools the first audit flagged as untested (OPS-001)."""

import httpx
import pytest
import respx
from pydantic import ValidationError

from swiss_procurement_mcp.client import UpstreamError, _assert_host_allowed
from swiss_procurement_mcp.constants import SIMAP_BASE
from swiss_procurement_mcp.inputs import (
    ConstructionCodeInput,
    CpvSearchInput,
    HistoryInput,
    OfficeSearchInput,
    SearchInput,
)
from swiss_procurement_mcp.server import (
    find_procurement_office,
    get_publication_history,
    search_construction_codes,
    search_cpv_codes,
    search_procurements,
)

# --- SEC-018: input bounds ------------------------------------------------


async def test_limit_below_range_rejected():
    # Rejected at the boundary now: the model refuses before the tool body runs.
    with pytest.raises(ValidationError) as exc:
        CpvSearchInput(query="metall", limit=0)
    assert exc.value.errors()[0]["type"] == "greater_than_equal"


async def test_limit_above_range_rejected():
    with pytest.raises(ValidationError) as exc:
        OfficeSearchInput(name_contains="zurich", limit=1000)
    assert exc.value.errors()[0]["type"] == "less_than_equal"


async def test_overlong_text_rejected():
    with pytest.raises(ValueError, match="at most"):
        await search_cpv_codes(CpvSearchInput(query="x" * 201))


# --- SEC-021: egress allow-list guard -------------------------------------


def test_host_guard_allows_simap():
    # Does not raise for the allow-listed host.
    _assert_host_allowed(f"{SIMAP_BASE}/cantons/v1")


def test_host_guard_rejects_foreign_host():
    with pytest.raises(UpstreamError, match="non-allow-listed host"):
        _assert_host_allowed("https://evil.example.com/exfil")


# --- ARCH-003: match_type -------------------------------------------------


@respx.mock
async def test_match_type_exact_on_results(search_payload):
    respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search").mock(
        return_value=httpx.Response(200, json=search_payload)
    )
    result = await search_procurements(SearchInput(canton="ZH"))
    assert result.match_type == "exact"


@respx.mock
async def test_match_type_none_on_empty():
    respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search").mock(
        return_value=httpx.Response(200, json={"projects": [], "pagination": {}})
    )
    result = await search_procurements(SearchInput(canton="ZH"))
    assert result.match_type == "none"
    assert result.count == 0


# --- OPS-001: coverage for previously-untested tools ----------------------


@respx.mock
async def test_publication_history():
    respx.get(url__regex=rf"{SIMAP_BASE}/publications/v1/publication/.*/past-publications").mock(
        return_value=httpx.Response(
            200,
            json={
                "pastPublications": [
                    {
                        "publicationId": "pub-0",
                        "publicationNumber": "41694-00",
                        "pubType": "tender",
                        "publicationDate": "2026-06-01",
                        "title": {"de": "Erstausschreibung"},
                    }
                ]
            },
        )
    )
    result = await get_publication_history(HistoryInput(publication_id="pub-1"))
    assert result.count == 1
    assert result.publications[0].pub_type == "tender"
    assert result.publications[0].title == "Erstausschreibung"


@respx.mock
async def test_construction_code_search():
    respx.get(f"{SIMAP_BASE}/codes/v1/bkp/search").mock(
        return_value=httpx.Response(
            200, json={"codes": [{"code": "215.2", "label": {"de": "Fassadenbau"}}]}
        )
    )
    result = await search_construction_codes(ConstructionCodeInput(system="bkp", query="Fassade"))
    assert result.system == "bkp"
    assert result.match_type == "exact"
    assert result.codes[0].code == "215.2"


async def test_construction_code_rejects_cpv():
    """`cpv` belongs to search_cpv_codes, and the schema now says so.

    The rejection used to happen in the tool body, which meant the tool schema
    advertised `cpv` as a valid `system` and then errored on it — a model
    trusting the schema was guaranteed to hit that. The Literal is now narrowed,
    so the boundary refuses it before the tool runs.
    """
    with pytest.raises(ValidationError) as exc:
        ConstructionCodeInput(system="cpv", query="metall")
    assert exc.value.errors()[0]["type"] == "literal_error"


@respx.mock
async def test_find_procurement_office_filters_client_side():
    respx.get(f"{SIMAP_BASE}/procoffices/v1/po/public").mock(
        return_value=httpx.Response(
            200,
            json={
                "procOffices": [
                    {
                        "id": "po1",
                        "name": {"de": "Bereich Liegenschaften Zürich"},
                        "type": "cantonal",
                        "institutionId": "i1",
                    },
                    {"id": "po2", "name": {"de": "Gemeinde Bern"}, "type": "communal"},
                ]
            },
        )
    )
    result = await find_procurement_office(OfficeSearchInput(name_contains="liegenschaften"))
    assert result.count == 1
    assert result.offices[0].id == "po1"
    assert result.match_type == "exact"
