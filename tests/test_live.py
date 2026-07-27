"""Live tests against the real simap.ch API. Excluded from CI."""

import re

import httpx
import pytest

from swiss_procurement_mcp.client import SimapClient
from swiss_procurement_mcp.constants import (
    CANTON_IDS,
    CANTON_INSTITUTION_IDS,
    INSTITUTION_ID_CONFEDERATION,
    INSTITUTION_ID_FOREIGN,
    PROCESS_TYPES,
    PROJECT_SUB_TYPES,
    PUB_TYPES,
)
from swiss_procurement_mcp.inputs import (
    AwardSearchInput,
    CpvSearchInput,
    ProcurementDetailInput,
    SearchInput,
    StatusInput,
)
from swiss_procurement_mcp.server import (
    get_procurement_details,
    search_awards,
    search_cpv_codes,
    search_procurements,
    source_status,
)

pytestmark = pytest.mark.live

# The machine-readable spec behind https://www.simap.ch/api-doc.
SPEC_URL = "https://www.simap.ch/api/specifications/simap.yaml"


async def test_live_search_zurich():
    result = await search_procurements(SearchInput(canton="ZH", published_from="2026-01-01"))
    assert result.count > 0
    # Deliberately NOT asserting r.canton == "ZH": the default semantics match
    # the procuring body, and a Zurich body may have work delivered elsewhere —
    # or, for ~60% of publications, no structured order address at all.


async def test_live_procuring_body_reaches_projects_without_an_order_address():
    """The regression this release exists for.

    Asserting on counts alone would be weak — a single page saturates at 20 for
    both semantics. What matters is the mechanism: `procuring_body` returns
    projects whose structured order canton is absent, which is precisely the
    ~60% that `orderAddressCantons` can never match.
    """
    window = {"published_from": "2026-06-01", "published_until": "2026-07-27"}
    by_body = await search_procurements(
        SearchInput(canton="ZH", canton_match="procuring_body", **window)
    )
    assert by_body.count > 0
    assert any(not r.canton for r in by_body.results), (
        "expected at least one project with no structured order canton — those "
        "are unreachable via place_of_delivery"
    )


async def test_live_both_is_a_superset_of_each_single_semantics():
    """`both` unions two upstream pages, so it cannot be smaller than either."""
    window = {"published_from": "2026-07-20", "published_until": "2026-07-27"}
    by_body = await search_procurements(
        SearchInput(canton="ZH", canton_match="procuring_body", **window)
    )
    by_place = await search_procurements(
        SearchInput(canton="ZH", canton_match="place_of_delivery", **window)
    )
    both = await search_procurements(SearchInput(canton="ZH", canton_match="both", **window))
    assert both.count >= max(by_body.count, by_place.count)
    assert both.has_more is False and both.next_cursor is None


async def test_live_canton_institution_ids_still_resolve():
    """Pinned ids must match the live institution tree, or `canton=` silently
    filters on a stale organisation."""
    async with SimapClient() as client:
        payload, _prov, _stamp = await client.institutions()

    rows = (
        payload
        if isinstance(payload, list)
        else next((v for v in payload.values() if isinstance(v, list)), [])
    )
    roots = {r["id"] for r in rows if not r.get("parentInstitutionId")}

    missing = {c: i for c, i in CANTON_INSTITUTION_IDS.items() if i not in roots}
    assert not missing, f"canton institution ids no longer root institutions: {missing}"
    assert INSTITUTION_ID_CONFEDERATION in roots
    assert INSTITUTION_ID_FOREIGN in roots
    # 26 cantons + Bund + Ausland. A change here means the taxonomy moved.
    assert len(roots) == len(CANTON_IDS) + 2, f"expected 28 root institutions, got {len(roots)}"


@pytest.mark.parametrize(
    ("schema_name", "ours"),
    [
        ("ProjectSearchPubTypeFilter", PUB_TYPES),
        ("PubProcessType", PROCESS_TYPES),
        ("ProjectSubType", PROJECT_SUB_TYPES),
    ],
)
async def test_live_constants_match_the_openapi_spec(schema_name, ours):
    """Drift guard for the hand-maintained enums.

    They were transcribed from live probes and are currently exact; this catches
    the day simap adds a value, which would otherwise surface as an opaque
    HTTP 400 / errorCode E0025 for users.
    """
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as http:
        spec = (await http.get(SPEC_URL)).text

    start = spec.find(f"\n    {schema_name}:")
    assert start != -1, f"{schema_name} not found in the spec"
    block = spec[start : start + 1600]
    match = re.search(r"enum:\s*\n((?:\s*-\s*\S+\n)+)", block)
    assert match, f"no enum block for {schema_name}"
    upstream = {line.strip(" -\n") for line in match.group(1).strip().splitlines()}

    assert upstream == set(ours), (
        f"{schema_name} drifted — only upstream: {upstream - set(ours)}, "
        f"only local: {set(ours) - upstream}"
    )


async def test_live_details_roundtrip():
    search = await search_procurements(SearchInput(canton="ZH", published_from="2026-01-01"))
    first = search.results[0]
    detail = await get_procurement_details(
        ProcurementDetailInput(project_id=first.project_id, publication_id=first.publication_id)
    )
    assert detail.title


async def test_live_cpv_search():
    result = await search_cpv_codes(CpvSearchInput(query="Metall"))
    assert result.count > 0


async def test_live_awards():
    result = await search_awards(AwardSearchInput(canton="ZH", published_from="2026-01-01"))
    assert result.provenance == "live_api"


async def test_live_status():
    assert (await source_status(StatusInput())).all_healthy is True
