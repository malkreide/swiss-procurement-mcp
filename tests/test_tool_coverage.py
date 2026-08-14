"""OPS-001: unit coverage for the tools that had almost none.

The 2026-07-28 re-audit put OPS-001 at `partial` on an uneven distribution:
`search_procurements` and the input models were heavily covered while seven
tools sat at one or two tests each. Counted rather than estimated — four of them
had exactly one.

That is the distribution where a silently broken tool survives a green suite,
and this repo has already produced two tests that passed while asserting
nothing. So these target the paths that would actually break quietly: payload
shape fallbacks, degraded envelopes, client-side filtering and truncation.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from swiss_procurement_mcp import client as _client
from swiss_procurement_mcp.constants import SIMAP_BASE
from swiss_procurement_mcp.inputs import (
    CONSTRUCTION_CODE_SYSTEMS,
    AwardSearchInput,
    ConstructionCodeInput,
    DetailedSearchInput,
    HistoryInput,
    OfficeSearchInput,
    ProcurementDetailInput,
    StatusInput,
)
from swiss_procurement_mcp.server import (
    find_procurement_office,
    get_procurement_details,
    get_publication_history,
    search_awards,
    search_construction_codes,
    search_procurements_detailed,
    source_status,
)

PROJ, PUB = "proj-1", "pub-1"
DETAIL_URL = f"{SIMAP_BASE}/publications/v1/project/{PROJ}/publication-details/{PUB}"
PAST_URL = f"{SIMAP_BASE}/publications/v1/publication/{PUB}/past-publications"
OFFICES_URL = f"{SIMAP_BASE}/procoffices/v1/po/public"
SEARCH_URL = f"{SIMAP_BASE}/publications/v2/project/project-search"
CANTONS_URL = f"{SIMAP_BASE}/cantons/v1"


@pytest.fixture(autouse=True)
def no_backoff_delay(monkeypatch):
    """Same pattern as tests/test_resilience.py.

    Seven of these tests exercise the degraded envelope, which means three real
    retries at 2s/4s/8s each — about 100s of pure sleeping for behaviour that
    test_resilience.py already covers. The retry *logic* is tested there; here
    only the envelope matters.
    """

    async def _instant(_seconds):
        return None

    monkeypatch.setattr(_client, "_sleep", _instant)


def _office(oid: str, name: str, otype: str = "cantonal") -> dict:
    return {"id": oid, "name": {"de": name}, "type": otype, "institutionId": f"inst-{oid}"}


# --- get_procurement_details ----------------------------------------------


@respx.mock
async def test_details_returns_the_record():
    respx.get(DETAIL_URL).mock(
        return_value=httpx.Response(200, json={"project-info": {"title": {"de": "Schulhaus Nord"}}})
    )
    r = await get_procurement_details(ProcurementDetailInput(project_id=PROJ, publication_id=PUB))
    assert r.title == "Schulhaus Nord"
    assert r.provenance == "live_api"


@respx.mock
async def test_details_degrades_without_losing_the_ids():
    """The degraded envelope must still say which record was asked for.

    A degraded response that drops the ids is unusable: the caller cannot retry
    or report what failed.
    """
    respx.get(DETAIL_URL).mock(return_value=httpx.Response(500, text="boom"))
    r = await get_procurement_details(ProcurementDetailInput(project_id=PROJ, publication_id=PUB))
    assert r.provenance == "degraded"
    assert r.project_id == PROJ and r.publication_id == PUB


@respx.mock
async def test_details_degraded_note_leaks_no_upstream_body():
    """OBS-002: the upstream body never reaches the model."""
    respx.get(DETAIL_URL).mock(
        return_value=httpx.Response(500, text="Traceback: secret-internal-detail")
    )
    r = await get_procurement_details(ProcurementDetailInput(project_id=PROJ, publication_id=PUB))
    assert "secret-internal-detail" not in r.model_dump_json()


@respx.mock
async def test_details_picks_the_requested_language():
    respx.get(DETAIL_URL).mock(
        return_value=httpx.Response(
            200,
            json={"project-info": {"title": {"de": "Schulhaus", "fr": "École", "it": "Scuola"}}},
        )
    )
    r = await get_procurement_details(
        ProcurementDetailInput(project_id=PROJ, publication_id=PUB, language="fr")
    )
    assert r.title == "École"


@respx.mock
async def test_details_falls_back_from_project_info_to_base_title():
    """The title lives under `project-info` or `base` depending on the record."""
    respx.get(DETAIL_URL).mock(
        return_value=httpx.Response(200, json={"base": {"title": {"de": "Nur Base"}}})
    )
    r = await get_procurement_details(ProcurementDetailInput(project_id=PROJ, publication_id=PUB))
    assert r.title == "Nur Base"


# --- get_publication_history ----------------------------------------------


@respx.mock
async def test_history_lists_earlier_publications():
    respx.get(PAST_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "pastPublications": [
                    {
                        "publicationId": "old-1",
                        "publicationNumber": "41694-01",
                        "pubType": "tender",
                        "publicationDate": "2026-03-01",
                        "title": {"de": "Ausschreibung"},
                    }
                ]
            },
        )
    )
    r = await get_publication_history(HistoryInput(publication_id=PUB))
    assert r.count == 1
    assert r.publications[0].publication_id == "old-1"
    assert r.publications[0].pub_type == "tender"


@respx.mock
async def test_history_falls_back_from_publicationId_to_id():
    """The upstream uses both spellings; losing the id would break the follow-up call."""
    respx.get(PAST_URL).mock(
        return_value=httpx.Response(
            200, json={"pastPublications": [{"id": "only-id", "pubType": "award"}]}
        )
    )
    r = await get_publication_history(HistoryInput(publication_id=PUB))
    assert r.publications[0].publication_id == "only-id"


@respx.mock
async def test_history_empty_is_normal_not_an_error():
    """A first publication has no history — that must not read as a failure."""
    respx.get(PAST_URL).mock(return_value=httpx.Response(200, json={"pastPublications": []}))
    r = await get_publication_history(HistoryInput(publication_id=PUB))
    assert r.count == 0
    assert r.provenance == "live_api"


@respx.mock
async def test_history_missing_key_is_treated_as_empty():
    respx.get(PAST_URL).mock(return_value=httpx.Response(200, json={}))
    r = await get_publication_history(HistoryInput(publication_id=PUB))
    assert r.count == 0


@respx.mock
async def test_history_degrades_on_upstream_error():
    respx.get(PAST_URL).mock(return_value=httpx.Response(503, text="down"))
    r = await get_publication_history(HistoryInput(publication_id=PUB))
    assert r.provenance == "degraded"
    assert r.count == 0


# --- find_procurement_office ----------------------------------------------
#
# This tool has a four-way fallback for the payload shape and none of it was
# covered. Each branch gets a test, because a silently-unmatched shape returns
# zero offices rather than failing — the worst kind of wrong answer.


@respx.mock
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"procOffices": [_office("1", "Amt für Hochbauten")]}, id="procOffices"),
        pytest.param({"offices": [_office("1", "Amt für Hochbauten")]}, id="offices"),
        pytest.param([_office("1", "Amt für Hochbauten")], id="bare-list"),
        pytest.param({"somethingElse": [_office("1", "Amt für Hochbauten")]}, id="first-list"),
    ],
)
async def test_office_handles_every_payload_shape(payload):
    respx.get(OFFICES_URL).mock(return_value=httpx.Response(200, json=payload))
    r = await find_procurement_office(OfficeSearchInput(name_contains="hochbauten"))
    assert r.count == 1, f"shape produced no match: {payload!r}"
    assert r.offices[0].name == "Amt für Hochbauten"


@respx.mock
async def test_office_match_is_case_insensitive():
    respx.get(OFFICES_URL).mock(
        return_value=httpx.Response(200, json={"procOffices": [_office("1", "Grün Stadt Zürich")]})
    )
    r = await find_procurement_office(OfficeSearchInput(name_contains="GRÜN STADT"))
    assert r.count == 1


@respx.mock
async def test_office_respects_the_limit():
    offices = [_office(str(i), f"Amt {i}") for i in range(10)]
    respx.get(OFFICES_URL).mock(return_value=httpx.Response(200, json={"procOffices": offices}))
    r = await find_procurement_office(OfficeSearchInput(name_contains="Amt", limit=3))
    assert r.count == 3


@respx.mock
async def test_office_no_match_returns_empty_not_error():
    respx.get(OFFICES_URL).mock(
        return_value=httpx.Response(200, json={"procOffices": [_office("1", "Amt A")]})
    )
    r = await find_procurement_office(OfficeSearchInput(name_contains="nonexistent"))
    assert r.count == 0
    assert r.provenance == "live_api"


@respx.mock
async def test_office_degrades_on_upstream_error():
    respx.get(OFFICES_URL).mock(return_value=httpx.Response(500, text="boom"))
    r = await find_procurement_office(OfficeSearchInput(name_contains="amt"))
    assert r.provenance == "degraded"
    assert r.offices == []


# --- source_status ---------------------------------------------------------


@respx.mock
async def test_status_reports_healthy():
    respx.get(url__startswith=CANTONS_URL).mock(return_value=httpx.Response(200, json=[]))
    r = await source_status(StatusInput())
    assert r.all_healthy is True
    assert r.sources[0].reachable is True


@respx.mock
async def test_status_reports_unhealthy_without_raising():
    """A status tool that raises when the source is down is useless."""
    respx.get(url__startswith=CANTONS_URL).mock(return_value=httpx.Response(503, text="down"))
    r = await source_status(StatusInput())
    assert r.all_healthy is False


@respx.mock
async def test_status_survives_a_connection_error():
    respx.get(url__startswith=CANTONS_URL).mock(side_effect=httpx.ConnectError("no route"))
    r = await source_status(StatusInput())
    assert r.all_healthy is False


@respx.mock
async def test_status_works_without_an_argument():
    """The tool is callable with no arguments; the model may omit them."""
    respx.get(url__startswith=CANTONS_URL).mock(return_value=httpx.Response(200, json=[]))
    r = await source_status()
    assert r.sources


@respx.mock
async def test_status_carries_attribution():
    respx.get(url__startswith=CANTONS_URL).mock(return_value=httpx.Response(200, json=[]))
    r = await source_status(StatusInput())
    assert r.source and "simap" in r.source.lower()


# --- search_awards ---------------------------------------------------------


@respx.mock
async def test_awards_degrades_on_upstream_error():
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(500, text="boom"))
    r = await search_awards(AwardSearchInput(canton="ZH"))
    assert r.provenance == "degraded"
    assert r.count == 0


@respx.mock
async def test_awards_empty_result_is_not_an_error(search_payload):
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json={**search_payload, "projects": []})
    )
    r = await search_awards(AwardSearchInput(canton="ZH"))
    assert r.count == 0
    assert r.match_type == "none"


@respx.mock
async def test_awards_states_the_canton_semantics(search_payload):
    """Which canton filter was applied changes the counts a lot — say so."""
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload))
    r = await search_awards(AwardSearchInput(canton="ZH"))
    assert r.note and "PROCURING BODY" in r.note


@respx.mock
async def test_awards_without_canton_carries_no_canton_note(search_payload):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload))
    r = await search_awards(AwardSearchInput(published_from="2026-07-01"))
    assert r.note is None or "canton=" not in r.note


# --- search_construction_codes ---------------------------------------------


@respx.mock
@pytest.mark.parametrize("system", CONSTRUCTION_CODE_SYSTEMS)
async def test_every_advertised_system_is_actually_accepted(system):
    """The schema must not advertise a value the tool rejects.

    This is the regression that prompted narrowing the Literal: `cpv` was in the
    enum and refused in the body, so a model trusting the tool schema was
    guaranteed to hit an error.
    """
    respx.get(f"{SIMAP_BASE}/codes/v1/{system}/search").mock(
        return_value=httpx.Response(200, json={"codes": []})
    )
    r = await search_construction_codes(ConstructionCodeInput(system=system, query="beton"))
    assert r.system == system


@respx.mock
async def test_construction_codes_degrade_on_upstream_error():
    respx.get(f"{SIMAP_BASE}/codes/v1/bkp/search").mock(
        return_value=httpx.Response(500, text="boom")
    )
    r = await search_construction_codes(ConstructionCodeInput(system="bkp", query="fassade"))
    assert r.provenance == "degraded"
    assert r.codes == []


@respx.mock
async def test_construction_codes_accept_a_bare_list_payload():
    respx.get(f"{SIMAP_BASE}/codes/v1/bkp/search").mock(
        return_value=httpx.Response(200, json=[{"code": "211", "label": {"de": "Baugrube"}}])
    )
    r = await search_construction_codes(ConstructionCodeInput(system="bkp", query="baugrube"))
    assert r.codes[0].code == "211"


# --- search_procurements_detailed ------------------------------------------


@respx.mock
async def test_detailed_degrades_on_search_error():
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(500, text="boom"))
    r = await search_procurements_detailed(DetailedSearchInput(canton="ZH"))
    assert r.provenance == "degraded"
    assert r.total_matched == 0


@respx.mock
async def test_detailed_keeps_the_list_when_one_detail_fails(search_payload, detail_payload):
    """A partial answer beats no answer."""
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=search_payload))
    respx.get(url__regex=rf"{SIMAP_BASE}/publications/v1/project/.*").mock(
        return_value=httpx.Response(500, text="boom")
    )
    r = await search_procurements_detailed(DetailedSearchInput(canton="ZH", top_n=1))
    assert r.total_matched >= 1


@respx.mock
async def test_construction_codes_pick_the_requested_language():
    respx.get(f"{SIMAP_BASE}/codes/v1/npk/search").mock(
        return_value=httpx.Response(
            200,
            json={"codes": [{"code": "237", "label": {"de": "Fenster", "fr": "Fenêtres"}}]},
        )
    )
    r = await search_construction_codes(
        ConstructionCodeInput(system="npk", query="fenster", language="fr")
    )
    assert r.codes[0].label == "Fenêtres"


@respx.mock
async def test_construction_codes_empty_result_is_not_an_error():
    respx.get(f"{SIMAP_BASE}/codes/v1/oag/search").mock(
        return_value=httpx.Response(200, json={"codes": []})
    )
    r = await search_construction_codes(ConstructionCodeInput(system="oag", query="xyzzy"))
    assert r.count == 0
    assert r.provenance == "live_api"


# --- the guard -------------------------------------------------------------


def test_every_tool_meets_the_coverage_floor():
    """OPS-001 as an executable rule, not a one-off clean-up.

    The finding existed because coverage was uneven and nobody was counting.
    A new tool added with two tests would recreate exactly that state, so the
    floor is enforced here rather than rediscovered at the next audit.

    Counting is deliberately generous — a test is credited to every tool it
    exercises, since one test legitimately covers two. It is a floor, not a
    quality measure: passing this says a tool is not *un*tested, nothing more.
    """
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent
    server_src = (root.parent / "src/swiss_procurement_mcp/server.py").read_text(encoding="utf-8")
    # `source_status` takes an optional arg and so does not match the `(args`
    # shape the other tools share.
    tools = sorted([*re.findall(r"^async def (\w+)\(args", server_src, re.M), "source_status"])
    assert len(tools) >= 9, f"tool discovery found only {tools}"

    unit: dict[str, int] = dict.fromkeys(tools, 0)
    live: dict[str, int] = dict.fromkeys(tools, 0)
    for path in root.glob("test_*.py"):
        target = live if path.name == "test_live.py" else unit
        for block in re.split(
            r"\n(?=(?:@|async def test_|def test_))", path.read_text(encoding="utf-8")
        ):
            if not re.search(r"(async )?def test_", block):
                continue
            for tool in tools:
                if re.search(rf"\b{tool}\(", block):
                    target[tool] += 1

    short = [f"{t}: {unit[t]} unit / {live[t]} live" for t in tools if unit[t] < 5 or live[t] < 1]
    assert not short, "tools below the OPS-001 floor (>=5 unit, >=1 live):\n  " + "\n  ".join(short)


# ---------------------------------------------------------------------------
# ARCH-002: every tool description carries a use-case tag
# ---------------------------------------------------------------------------

TOOL_NAMES = (
    "search_procurements",
    "search_procurements_detailed",
    "search_awards",
    "get_procurement_details",
    "get_publication_history",
    "search_cpv_codes",
    "search_construction_codes",
    "find_procurement_office",
    "source_status",
)
USE_CASE_COVERAGE = 0.8
MIN_DESCRIPTION_CHARS = 100


def _tool_descriptions() -> dict[str, str]:
    import inspect

    import swiss_procurement_mcp.server as srv

    return {name: inspect.getdoc(getattr(srv, name)) or "" for name in TOOL_NAMES}


def test_tools_carry_a_use_case_tag() -> None:
    """The description is what the model reads when choosing a tool.

    Naming the *function* is not the same as naming the *occasion*:
    `search_procurements` and `search_procurements_detailed` are otherwise hard
    to tell apart from the name alone.
    """
    descriptions = _tool_descriptions()
    tagged = [n for n, d in descriptions.items() if "<use_case>" in d]
    ratio = len(tagged) / len(descriptions)
    assert ratio >= USE_CASE_COVERAGE, (
        f"only {len(tagged)}/{len(descriptions)} tools carry <use_case>; "
        f"the floor is {USE_CASE_COVERAGE:.0%}"
    )


def test_no_description_is_too_short() -> None:
    """`source_status` sat at 57 characters, which is a label rather than a
    description — and it is the tool a model reaches for when confused."""
    short = {n: len(d) for n, d in _tool_descriptions().items() if len(d) < MIN_DESCRIPTION_CHARS}
    assert not short, f"tool descriptions below {MIN_DESCRIPTION_CHARS} chars: {short}"
