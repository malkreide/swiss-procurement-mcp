"""Tests for the 0.2.0 hardening: input bounds, egress guard, match_type, and
coverage for the three tools the first audit flagged as untested (OPS-001)."""

import pathlib

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

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

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


# ---------------------------------------------------------------------------
# Tier-A audit remediation: SEC-004, ARCH-005, SEC-013, OPS-003
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://www.simap.ch/api/publications/v2/project/project-search",
        "ftp://www.simap.ch/api",
        "//www.simap.ch/api",
    ],
)
def test_non_https_egress_is_refused(url: str) -> None:
    """SEC-004: the host allow-list alone left plaintext reachable.

    `http://www.simap.ch/...` passes an allow-list keyed on hostname while
    sending the request in the clear — a gap that reads as covered.
    """
    with pytest.raises(UpstreamError, match="non-HTTPS"):
        _assert_host_allowed(url)


def test_https_to_an_allowed_host_still_passes() -> None:
    """The scheme check must not have broken the normal path."""
    _assert_host_allowed(f"{SIMAP_BASE}/publications/v2/project/project-search")


def test_scheme_is_checked_before_the_host() -> None:
    """A plaintext URL to a foreign host should name the scheme, not the host.

    Ordering matters for the error message: reporting "host not allow-listed"
    for an `http://` URL sends the reader after the wrong problem.
    """
    with pytest.raises(UpstreamError, match="non-HTTPS"):
        _assert_host_allowed("http://evil.example/api")


@pytest.mark.parametrize(
    "path",
    [".env.example", "docs/secret-management.md", "ROADMAP.md"],
)
def test_required_document_exists(path: str) -> None:
    """ARCH-005 / SEC-013 / OPS-003 each require a specific file on disk.

    Asserted rather than assumed: all three were reported missing by an audit
    and are the kind of file that quietly disappears in a refactor.
    """
    assert (REPO_ROOT / path).is_file(), f"{path} is required by the audit catalogue"


def test_env_example_documents_every_environment_variable() -> None:
    """An `.env.example` that has drifted from the code is worse than none.

    It reads as the authoritative configuration surface, so a variable the code
    honours but the file omits is invisible to whoever is deploying.
    """
    import re

    example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    referenced = set()
    for src in (REPO_ROOT / "src").rglob("*.py"):
        referenced |= set(
            re.findall(r'environ\.get\(\s*"([A-Z_]+)"', src.read_text(encoding="utf-8"))
        )
    missing = sorted(v for v in referenced if v not in example)
    assert not missing, f".env.example does not mention: {missing}"


def test_env_example_assigns_no_credential_value() -> None:
    """The checked-in template must never hold a real credential.

    Checks the assignments, not the prose: any `*KEY`, `*TOKEN`, `*SECRET` or
    `*PASSWORD` variable must be absent, commented out, or assigned an empty
    value. A template is exactly the file where a real key gets committed by
    accident, because it looks like documentation rather than configuration.
    """
    import re

    example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    offenders = [
        line
        for line in example.splitlines()
        if not line.lstrip().startswith("#")
        and re.match(r"^\s*\w*(KEY|TOKEN|SECRET|PASSWORD)\s*=\s*\S", line, re.I)
    ]
    assert not offenders, f".env.example assigns a credential value: {offenders}"
