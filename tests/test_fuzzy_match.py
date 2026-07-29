"""ARCH-003: widen a taxonomy lookup that found nothing, never a tender search.

The check asks that empty results on non-sensitive search tools trigger a fuzzy
or suggestion mechanism, that responses carry a `match_type`, that `none` comes
with an actionable hint, and that *sensitive* tools stay exact-only with the
decision documented.

The last criterion is why this file has two halves. Widening a CPV lookup is
helpful: "no such code" is rarely the answer anyone wants, and the taxonomy is a
closed set the caller can check. Widening a procurement search is not: quietly
broadening the terms can surface a tender that does not answer the question and
present it as though it does, and "no tender matched" is a legitimate,
actionable answer. `test_a_tender_search_never_widens` is the guard for that
split, and it is the one worth keeping if any are dropped.

The widening strategy itself was measured against the live API before it was
written, not assumed. Real cases: `Schulhaus` returns nothing while `Schulh`
returns one code, `Schulhausneubau` nothing while `Schul` returns eighteen,
`Betonsanierungsarbeiten` nothing while `Beto` returns five.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from swiss_procurement_mcp._fuzzy import MIN_TERM_LENGTH, empty_note, widen, widening_note
from swiss_procurement_mcp.constants import SIMAP_BASE
from swiss_procurement_mcp.inputs import CpvSearchInput, OfficeSearchInput, SearchInput
from swiss_procurement_mcp.server import (
    find_procurement_office,
    search_cpv_codes,
    search_procurements,
)

pytestmark = pytest.mark.asyncio

CPV_URL = f"{SIMAP_BASE}/codes/v1/cpv/search"


def _codes(*names: str) -> dict:
    return {"codes": [{"code": "4453", "label": {"de": n}} for n in names]}


# --- the widening strategy -------------------------------------------------


async def test_multi_word_queries_drop_qualifiers_longest_first() -> None:
    """ "mobile Metallbauten" is asking about Metallbauten, not about mobility."""
    assert widen("mobile Metallbauten")[0] == "Metallbauten"


async def test_single_words_are_shortened_to_the_compound_head() -> None:
    """German puts the head at the front, and the upstream matches prefixes.

    Measured: `Schulhausneubau` finds nothing, `Schul` finds eighteen codes.
    """
    assert "Schul" in widen("Schulhausneubau") or "Schu" in widen("Schulhausneubau")


async def test_the_last_candidate_is_the_broadest_one() -> None:
    """A fixed per-step ratio was tried first and measured to be wrong.

    From "Betonsanierungsarbeiten" it reached seven characters and stopped,
    while the term that actually returns results is five. If the last attempt is
    not the widest one, the last resort is not a last resort.
    """
    candidates = widen("Betonsanierungsarbeiten")
    assert len(candidates[-1]) <= MIN_TERM_LENGTH + 1


async def test_short_queries_are_left_alone() -> None:
    """Below the floor a prefix stops narrowing anything and starts matching noise."""
    assert widen("Bau") == []


async def test_the_original_term_is_never_re_tried() -> None:
    """It already returned nothing; asking again is a wasted upstream request."""
    assert "Metall" not in widen("Metall")


async def test_the_notes_name_both_terms() -> None:
    """A model that cannot see which term produced the hits cannot warn anyone."""
    note = widening_note("Schulhaus", "Schul", 18)
    assert "Schulhaus" in note and "Schul" in note

    empty = empty_note("Zzz", ["Zz"], "Try something else.")
    assert "Zzz" in empty and "Try something else." in empty
    assert "source_status" in empty, "an empty result must point somewhere useful"


# --- taxonomy lookups widen ------------------------------------------------


async def test_a_code_lookup_widens_and_says_so() -> None:
    """The whole mechanism, end to end, on the tool a caller actually invokes."""
    async with respx.mock:
        route = respx.get(CPV_URL)
        route.side_effect = [
            httpx.Response(200, json={"codes": []}),  # exact: nothing
            httpx.Response(200, json=_codes("Schulgebäude")),  # widened: a hit
        ]
        result = await search_cpv_codes(CpvSearchInput(query="Schulhausneubau"))

    assert result.match_type == "fuzzy"
    assert result.count == 1
    assert "Schulhausneubau" in result.note, "the caller's own term must appear"
    assert result.note.count("'") >= 4, "both terms are named, not just one"


async def test_an_exact_hit_is_not_labelled_fuzzy() -> None:
    """The negative control. Without it, everything could be reported as fuzzy."""
    async with respx.mock:
        respx.get(CPV_URL).mock(return_value=httpx.Response(200, json=_codes("Metallbau")))
        result = await search_cpv_codes(CpvSearchInput(query="Metall"))

    assert result.match_type == "exact"
    assert result.note is None


async def test_an_exhausted_lookup_is_actionable() -> None:
    """`match_type == "none"` with no guidance is the anti-pattern ARCH-003 names."""
    async with respx.mock:
        respx.get(CPV_URL).mock(return_value=httpx.Response(200, json={"codes": []}))
        result = await search_cpv_codes(CpvSearchInput(query="Zzzzzzunfindbar"))

    assert result.match_type == "none"
    assert result.count == 0
    assert result.note and "Zzzzzzunfindbar" in result.note
    assert "source_status" in result.note


async def test_widening_stops_at_the_first_hit() -> None:
    """Each candidate is another upstream request on an already-failed path."""
    async with respx.mock:
        route = respx.get(CPV_URL)
        route.side_effect = [
            httpx.Response(200, json={"codes": []}),
            httpx.Response(200, json=_codes("Treffer")),
            httpx.Response(200, json=_codes("sollte nie abgerufen werden")),
        ]
        await search_cpv_codes(CpvSearchInput(query="Schulhausneubau"))
        assert route.call_count == 2, "a hit must end the loop"


async def test_the_office_lookup_widens_without_a_second_request() -> None:
    """The office list is already in memory, so widening is a re-filter.

    Worth asserting separately: the code lookups pay an upstream request per
    candidate and this one must not, or a name search would quietly multiply
    traffic against a ~1 MB endpoint.
    """
    payload = {"procOffices": [{"id": "1", "name": {"de": "Hochbauamt Kanton Zürich"}}]}
    async with respx.mock:
        route = respx.get(f"{SIMAP_BASE}/procoffices/v1/po/public")
        route.mock(return_value=httpx.Response(200, json=payload))
        result = await find_procurement_office(OfficeSearchInput(name_contains="Hochbauamtes"))

    assert result.match_type == "fuzzy"
    assert result.count == 1
    assert route.call_count == 1, "widening a client-side filter must not re-fetch"


# --- tender search does not widen, deliberately ----------------------------


async def test_a_tender_search_never_widens() -> None:
    """ARCH-003 criterion 4, and the reason the split exists.

    A broadened procurement query can surface tenders that do not answer the
    question and present them as though they do. "No tender matched" is a real
    answer; an invented one is not. The assertion is on the request count,
    because that is what a widening implementation would change.
    """
    async with respx.mock:
        route = respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search")
        route.mock(
            return_value=httpx.Response(200, json={"content": [], "page": {"totalElements": 0}})
        )
        result = await search_procurements(SearchInput(query="Schulhausneubau"))

    assert route.call_count == 1, "the search must be tried exactly once, never widened"
    assert result.match_type == "none"
    assert result.count == 0


async def test_an_empty_tender_search_still_explains_itself() -> None:
    """Criterion 3 applies to the exact-only tools too — none must be actionable.

    And the hint says *why* it does not widen, so the absence reads as a
    decision rather than a missing feature.
    """
    async with respx.mock:
        respx.get(f"{SIMAP_BASE}/publications/v2/project/project-search").mock(
            return_value=httpx.Response(200, json={"content": [], "page": {"totalElements": 0}})
        )
        result = await search_procurements(SearchInput(query="Schulhausneubau"))

    assert result.note
    assert "search_cpv_codes" in result.note, "point at the tool that does widen"
    assert "does not widen" in result.note
