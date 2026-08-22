"""MCP server exposing the public read endpoints of the simap.ch procurement API.

Strictly read-only. The simap API also exposes ~200 write / OIDC-protected
endpoints (publishing tenders, submitting offers); none of them are wrapped here.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.caching import CacheHint
from mcp.server.mcpserver import MCPServer
from mcp.types import LATEST_PROTOCOL_VERSION

from ._fuzzy import empty_note, widen, widening_note
from ._log import configure_logging, log_event, logged_tool
from .client import (
    SimapClient,
    UpstreamError,
    close_client,
    get_client,
    normalise_language,
    pick_lang,
    utc_now_iso,
)
from .constants import (
    ATTRIBUTION,
    AWARD_PUB_TYPES,
    CANTON_IDS,
    CANTON_INSTITUTION_IDS,
    CANTON_MATCH_MODES,
    CODE_SYSTEMS,
    PROCESS_TYPES,
    PROJECT_SUB_TYPES,
    PUB_TYPES,
)
from .inputs import (
    MAX_DETAIL_N,
    AwardSearchInput,
    ConstructionCodeInput,
    CpvSearchInput,
    DetailedSearchInput,
    HistoryInput,
    OfficeSearchInput,
    ProcurementDetailInput,
    SearchInput,
    StatusInput,
)
from .models import (
    CodeEntry,
    CodeSearchResponse,
    EnrichedSearchResponse,
    HistoryEntry,
    HistoryResponse,
    OfficeSearchResponse,
    ProcurementDetail,
    ProcurementOffice,
    ProcurementSummary,
    SearchResponse,
    SourceStatus,
    StatusResponse,
)


@asynccontextmanager
async def _lifespan(_server: MCPServer):
    """SDK-001: release the pooled HTTP client when the server stops.

    Nothing is opened here — `get_client()` builds the shared client lazily on
    first use, so that calling a tool function directly (as the test suite does)
    needs no server. This exists so the pooled connections are closed cleanly
    rather than left to the garbage collector.
    """
    try:
        yield {}
    finally:
        await close_client()


# SEP-2549, spec 2026-07-28: every cacheable list result carries `ttlMs` and
# `cacheScope`. The SDK defaults both to "immediately stale, never shared", so a
# server that passes no `cache_hints` is not neutral — it makes each client
# re-list on every connection, for a list that cannot change while the process
# runs. The nine tools are registered at import; there is no dynamic
# registration and no per-caller filtering.
#
# `public` follows from that second property rather than from convenience: the
# answer is identical for every authorization context. The day a tool list
# becomes caller-dependent, this has to become `private` in the same commit.
#
# `prompts/list` and `resources/list` stay unset on purpose — this server
# registers neither, and hinting at them would describe a surface that does not
# exist.
LIST_CACHE_TTL_MS = 300_000

CACHE_HINTS = {
    "tools/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "server/discover": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
}

mcp = MCPServer("swiss-procurement-mcp", lifespan=_lifespan, cache_hints=CACHE_HINTS)

# OBS-003: structured JSON to stderr. stdout carries the MCP protocol.
configure_logging()

# ARCH-012: the MCP protocol version this server is written and tested against,
# pinned explicitly rather than inherited from whatever the SDK happens to
# default to.
#
# The SDK negotiates the version in the session layer and offers no constructor
# parameter for it, so the pin cannot be enforced by configuration. It is
# enforced by detection instead: a mismatch logs at WARNING on startup, and
# tests/test_protocol_version.py fails in CI. That splits the two audiences
# correctly — an SDK bump breaks the build for us, not the runtime for someone
# who upgraded `mcp` downstream.
MCP_PROTOCOL_VERSION = "2026-07-28"

if LATEST_PROTOCOL_VERSION != MCP_PROTOCOL_VERSION:
    log_event(
        logging.WARNING,
        "protocol_version_drift",
        pinned=MCP_PROTOCOL_VERSION,
        sdk_latest=LATEST_PROTOCOL_VERSION,
        hint="the installed mcp SDK negotiates a different protocol version than "
        "this server was tested against; see the README's MCP Protocol Version section",
    )

# ARCH-009: every tool is read-only, non-destructive, idempotent, and reaches
# the live simap.ch API (open world). All four hints are set explicitly —
# omitting destructiveHint would leave it to the client's default, which is not
# the same as stating that these tools destroy nothing.
READ_TOOL = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}

# SEC-018: bounds, allow-lists and patterns are declared on the input models in
# inputs.py and enforced by Pydantic before a tool body runs. MAX_LIMIT,
# MAX_TEXT_LEN and MAX_DETAIL_N are re-exported here because the tool docstrings
# and notes quote them.


def _degraded(exc: Exception) -> dict[str, Any]:
    # OBS-003: the operator gets the exception type at WARNING; the model gets
    # the sanitised note below. This is the single funnel for every upstream
    # failure path, so one call site covers all of them.
    log_event(
        logging.WARNING,
        "upstream_degraded",
        error_type=type(exc).__name__,
    )
    # OBS-002: surface a fixed, sanitised note — never the raw exception or the
    # upstream response body — to the model.
    return {
        "source": ATTRIBUTION,
        "provenance": "degraded",
        "retrieved_at": utc_now_iso(),
        "note": "simap.ch is currently unreachable or returned an error. Please retry shortly.",
    }


def _code_str(value: Any) -> str | None:
    """Code fields come back as {"code":..,"label":..} objects, not bare strings."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("code")
    return str(value)


def _code_list(values: Any) -> list[str]:
    if not values:
        return []
    return [c for c in (_code_str(v) for v in values) if c]


def _to_summary(entry: dict[str, Any], lang: str) -> ProcurementSummary:
    addr = entry.get("orderAddress") or {}
    return ProcurementSummary(
        project_id=entry.get("id", ""),
        publication_id=entry.get("publicationId", ""),
        title=pick_lang(entry.get("title"), lang) or "",
        project_number=entry.get("projectNumber"),
        publication_number=entry.get("publicationNumber"),
        project_type=entry.get("projectType"),
        project_sub_type=entry.get("projectSubType"),
        process_type=entry.get("processType"),
        pub_type=entry.get("pubType"),
        publication_date=entry.get("publicationDate"),
        procurement_office=pick_lang(entry.get("procOfficeName"), lang),
        canton=addr.get("cantonId"),
        city=pick_lang(addr.get("city"), lang),
        postal_code=addr.get("postalCode"),
    )


def _canton_filters(canton: str | None, canton_match: str) -> list[dict[str, Any]]:
    """Translate `canton` + `canton_match` into one or two upstream filters.

    Two filters exist and they answer different questions (see the measurement
    in `constants.py`): `issuedByOrganizations` selects by procuring body,
    `orderAddressCantons` by where the work is delivered. The latter silently
    drops the ~60% of publications whose order address is free text.

    Returns a list because `both` needs two upstream calls; the caller unions
    the results.
    """
    if canton_match not in CANTON_MATCH_MODES:
        raise ValueError(f"canton_match must be one of {CANTON_MATCH_MODES}.")
    if not canton:
        return [{}]
    code = canton.upper()
    if code not in CANTON_IDS:
        raise ValueError(f"Unknown canton {canton!r}. Use a bare id like ZH, not CH-ZH.")

    by_body = {"issuedByOrganizations": CANTON_INSTITUTION_IDS[code]}
    by_place = {"orderAddressCantons": code}
    if canton_match == "procuring_body":
        return [by_body]
    if canton_match == "place_of_delivery":
        return [by_place]
    return [by_body, by_place]


def _canton_note(canton: str | None, canton_match: str) -> str | None:
    """State which canton semantics were applied — the counts differ a lot."""
    if not canton:
        return None
    if canton_match == "procuring_body":
        return (
            f"canton={canton.upper()} matched on the PROCURING BODY (simap "
            "`issuedByOrganizations`, incl. subordinate offices). Publications "
            "procured by federal bodies but delivered in this canton (e.g. ETH, "
            "SBB) are not included — use canton_match='both' for those."
        )
    if canton_match == "place_of_delivery":
        return (
            f"canton={canton.upper()} matched on the PLACE OF DELIVERY (simap "
            "`orderAddressCantons`). Around 60% of publications carry no "
            "structured order address and are invisible to this filter — "
            "canton_match='procuring_body' (the default) does not have that gap."
        )
    return (
        f"canton={canton.upper()} matched on BOTH the procuring body and the "
        "place of delivery; results are the union of two upstream queries, so "
        "pagination is unavailable in this mode."
    )


def _build_search_params(
    lang: str,
    query: str | None,
    canton: str | None,
    cpv_codes: list[str] | None,
    process_type: str | None,
    pub_type: str | None,
    published_from: str | None,
    published_until: str | None,
    cursor: str | None,
) -> dict[str, Any]:
    """Validate the shared search filters and build the project-search params.

    The canton filter is added separately by `_canton_filters`, because it can
    expand into two upstream queries.
    """
    if process_type and process_type not in PROCESS_TYPES:
        raise ValueError(f"process_type must be one of {PROCESS_TYPES}.")
    if pub_type and pub_type not in PUB_TYPES:
        raise ValueError(f"pub_type must be one of {PUB_TYPES}.")

    params: dict[str, Any] = {"lang": lang}
    if query:
        params["search"] = query
    if cpv_codes:
        params["cpvCodes"] = cpv_codes
    if process_type:
        params["processTypes"] = process_type
    if pub_type:
        params["newestPubTypes"] = pub_type
    if published_from:
        params["newestPublicationFrom"] = published_from
    if published_until:
        params["newestPublicationUntil"] = published_until
    if cursor:
        params["lastItem"] = cursor
    return params


def _assert_filtered(params: dict[str, Any], canton: str | None) -> None:
    """simap returns 0 projects when NO filter is set — not "no matches".

    Without this the tool answers a filterless call with an empty result and the
    note "widen the date range", which misdiagnoses the cause: nothing was
    narrowed in the first place.
    """
    if canton:
        return
    if any(k != "lang" for k in params):
        return
    raise ValueError(
        "simap's project-search requires at least one filter — a filterless "
        "query returns nothing rather than everything. Pass at least one of "
        "query, canton, cpv_codes, process_type, pub_type, published_from or "
        "published_until."
    )


def _detail_from_payload(
    payload: dict[str, Any],
    project_id: str,
    publication_id: str,
    lang: str,
    provenance: str,
    stamp: str,
) -> ProcurementDetail:
    """Map a publication-details payload to a ProcurementDetail envelope."""
    info = payload.get("project-info") or {}
    proc = payload.get("procurement") or {}
    dates = payload.get("dates") or {}
    base = payload.get("base") or {}
    office_addr = (
        info.get("procOfficeAddress") if isinstance(info.get("procOfficeAddress"), dict) else None
    )
    return ProcurementDetail(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        project_id=project_id,
        publication_id=publication_id,
        title=pick_lang(info.get("title") or base.get("title"), lang) or "",
        order_description=pick_lang(proc.get("orderDescription"), lang),
        process_type=proc.get("processType") or info.get("processType"),
        order_type=proc.get("orderType"),
        cpv_code=_code_str(base.get("cpvCode")),
        additional_cpv_codes=_code_list(proc.get("additionalCpvCodes")),
        bkp_codes=_code_list(proc.get("bkpCodes")),
        npk_codes=_code_list(proc.get("npkCodes")),
        procurement_office=pick_lang(office_addr.get("name"), lang) if office_addr else None,
        procurement_office_address=office_addr,
        offer_deadline=dates.get("offerDeadline"),
        # `dates` gibt es nur bei Ausschreibungen — aufgezeichnet am 2026-08-14
        # und ueber 90 Publikationen gemessen: 40 tragen `dates.publicationDate`,
        # aber alle 90 tragen `base.publicationDate`. Nur aus `dates` gelesen,
        # lieferte dieses Feld fuer jeden Zuschlag `null`, obwohl die Quelle das
        # Datum mitschickt. Die handgeschriebene Fixture hatte ein `dates`
        # erfunden, das ein Zuschlag nie hat, und die Suite stimmte damit dem
        # Mapper zu statt der Quelle.
        #
        # `offer_deadline` bleibt bewusst allein an `dates`: ein Zuschlag hat
        # keine Angebotsfrist, dort ist leer die richtige Antwort.
        publication_date=dates.get("publicationDate") or base.get("publicationDate"),
        has_documents=bool(payload.get("hasProjectDocuments")),
    )


async def _run_search(
    client: SimapClient, base: dict[str, Any], filters: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any], str, str]:
    """Run one project-search per canton filter and union the hits by project id.

    A single filter keeps the upstream pagination; `both` cannot, because the
    two queries carry independent cursors.
    """
    seen: dict[str, dict[str, Any]] = {}
    pagination: dict[str, Any] = {}
    provenance = "cached"
    stamp = utc_now_iso()
    for extra in filters:
        payload, prov, st = await client.project_search({**base, **extra})
        for project in payload.get("projects", []):
            key = project.get("id") or project.get("publicationId") or repr(project)
            seen.setdefault(key, project)
        if len(filters) == 1:
            pagination = payload.get("pagination") or {}
        if prov == "live_api":
            provenance = prov
        stamp = st
    return list(seen.values()), pagination, provenance, stamp


def _combine_notes(*notes: str | None) -> str | None:
    present = [n for n in notes if n]
    return " ".join(present) if present else None


@mcp.tool(annotations=READ_TOOL)
@logged_tool("search_procurements")
async def search_procurements(args: SearchInput) -> SearchResponse:
    """<use_case>Find open tenders matching a topic, canton, CPV code or date window — the default entry point when the question is "what is being tendered?".</use_case>

    Search Swiss public procurement projects on simap.ch.

    Covers all cantons and the Confederation, updated intraday. This is the
    entry point; use `get_procurement_details` with the returned ids for the
    full record.

    Note that simap indexes PROJECTS, not publications: one hit is one project,
    represented by its NEWEST publication. A project tendered in March and
    awarded in July appears once, as the July award. Use
    `get_publication_history` to see the earlier publications of a project.

    At least one filter is required — simap answers a filterless query with
    nothing rather than everything.

    Args:
        query: Free-text search over titles and descriptions.
        canton: Bare canton id, e.g. `ZH` (NOT `CH-ZH`). See `CANTON_IDS`.
        canton_match: How `canton` is interpreted.
            `procuring_body` (default) — procured by that canton's public
            bodies, including communal and subordinate offices.
            `place_of_delivery` — the work is delivered there. Beware: ~60% of
            publications carry no structured order address and are invisible to
            this filter.
            `both` — the union of the two. Costs two upstream calls and does
            not support `cursor`.
        cpv_codes: One or more CPV classification codes. Resolve names to codes
            with `search_cpv_codes` first.
        process_type: One of open, selective, invitation, direct, no_process.
        pub_type: Publication type. For awarded contracts use one of
            award_tender, award_study_contract, award_competition, direct_award —
            a plain "award" is rejected by the API.
        published_from / published_until: ISO dates `YYYY-MM-DD`. These filter on
            the NEWEST publication date of a project.
        cursor: Pagination cursor from a previous response's `next_cursor`.
        language: de, fr, it or en.
    """
    query, canton, canton_match = args.query, args.canton, args.canton_match
    cpv_codes, process_type, pub_type = args.cpv_codes, args.process_type, args.pub_type
    published_from, published_until = args.published_from, args.published_until
    cursor, language = args.cursor, args.language

    lang = normalise_language(language)
    filters = _canton_filters(canton, canton_match)
    if canton_match == "both" and cursor:
        raise ValueError(
            "canton_match='both' unions two upstream queries with independent "
            "cursors, so pagination is unavailable. Narrow the date range, or "
            "paginate each semantics separately."
        )
    params = _build_search_params(
        lang,
        query,
        canton,
        cpv_codes,
        process_type,
        pub_type,
        published_from,
        published_until,
        cursor,
    )
    _assert_filtered(params, canton)

    client = get_client()
    try:
        projects, pagination, provenance, stamp = await _run_search(client, params, filters)
    except UpstreamError as exc:
        return SearchResponse(
            **_degraded(exc), count=0, has_more=False, next_cursor=None, results=[]
        )

    next_cursor = pagination.get("lastItem")
    results = [_to_summary(e, lang) for e in projects]
    has_more = bool(next_cursor) and len(results) >= pagination.get("itemsPerPage", 20)

    # Renamed off `empty_note` to stop it shadowing the helper imported for the
    # taxonomy lookups: these searches deliberately do not widen (ARCH-003).
    no_match_note = None
    if not results:
        no_match_note = f"No projects matched. {_TENDER_HINT}"
    return SearchResponse(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        note=_combine_notes(no_match_note, _canton_note(canton, canton_match)),
        count=len(results),
        match_type="exact" if results else "none",
        has_more=has_more,
        next_cursor=next_cursor if has_more else None,
        results=results,
    )


@mcp.tool(annotations=READ_TOOL)
@logged_tool("search_procurements_detailed")
async def search_procurements_detailed(args: DetailedSearchInput) -> EnrichedSearchResponse:
    """<use_case>Answer a question needing both the hit list and each hit's detail in one step, e.g. "which school-building tenders ran in ZH and what BKP codes do they carry?". Prefer this over search_procurements followed by N detail calls.</use_case>

    Search publications and return the FULL record for the top matches at once.

    Aggregated entry point for the common "find tenders and show me their details"
    question: it runs the search and then fetches `get_procurement_details` for the
    first `top_n` hits in parallel, so a typical query is answered in a single tool
    call instead of a search-then-N-details chain. Each result carries the CPV and
    Swiss construction codes (BKP, NPK), deadlines and procurement office.

    Prefer `search_procurements` when you only need the summaries or want to
    paginate; use this when you want the leading hits fully expanded immediately.

    Args:
        top_n: How many of the top hits to expand to full detail (1-5).
        query, canton, canton_match, cpv_codes, process_type, pub_type,
        published_from, published_until, language: identical to
        `search_procurements` — including the `canton_match` semantics, which
        default to matching the procuring body.
    """
    query, canton, canton_match = args.query, args.canton, args.canton_match
    cpv_codes, process_type, pub_type = args.cpv_codes, args.process_type, args.pub_type
    published_from, published_until = args.published_from, args.published_until
    top_n, language = args.top_n, args.language

    lang = normalise_language(language)
    if not 1 <= top_n <= MAX_DETAIL_N:
        raise ValueError(f"top_n must be between 1 and {MAX_DETAIL_N}.")
    filters = _canton_filters(canton, canton_match)
    params = _build_search_params(
        lang,
        query,
        canton,
        cpv_codes,
        process_type,
        pub_type,
        published_from,
        published_until,
        None,
    )
    _assert_filtered(params, canton)

    client = get_client()
    try:
        projects, _pagination, provenance, stamp = await _run_search(client, params, filters)
    except UpstreamError as exc:
        return EnrichedSearchResponse(**_degraded(exc), count=0, total_matched=0, results=[])

    total = len(projects)
    pairs = [(p.get("id", ""), p.get("publicationId", "")) for p in projects[:top_n]]

    async def _fetch(pid: str, pubid: str) -> ProcurementDetail | None:
        try:
            d_payload, d_prov, d_stamp = await client.publication_details(pid, pubid, lang)
        except UpstreamError:
            return None
        return _detail_from_payload(d_payload, pid, pubid, lang, d_prov, d_stamp)

    details = await asyncio.gather(*(_fetch(pid, pubid) for pid, pubid in pairs))

    results = [d for d in details if d is not None]
    no_match_note = None
    if not total:
        no_match_note = f"No projects matched. {_TENDER_HINT}"
    return EnrichedSearchResponse(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        note=_combine_notes(no_match_note, _canton_note(canton, canton_match)),
        count=len(results),
        match_type="exact" if results else "none",
        total_matched=total,
        results=results,
    )


@mcp.tool(annotations=READ_TOOL)
@logged_tool("search_awards")
async def search_awards(args: AwardSearchInput) -> SearchResponse:
    """<use_case>Find who won, not what is open — all four award types at once. Use when the question is about completed procurement rather than current opportunities.</use_case>

    Search only awarded contracts (who won).

    Convenience wrapper over `search_procurements` that queries all four award
    publication types at once.

    Two coverage caveats. First, award coverage is uneven across cantons — some
    publish awards diligently, others rarely, so absence is not proof that no
    award happened. Second, the filter matches a project's NEWEST publication:
    a project awarded in May and corrected in June is no longer an "award" to
    this filter and drops out. Use `get_publication_history` on a project to see
    whether an award exists further back.

    `canton_match` works exactly as in `search_procurements` and defaults to
    matching the procuring body.
    """
    canton, canton_match = args.canton, args.canton_match
    published_from, published_until = args.published_from, args.published_until
    cursor, language = args.cursor, args.language

    lang = normalise_language(language)
    filters = _canton_filters(canton, canton_match)
    if canton_match == "both" and cursor:
        raise ValueError(
            "canton_match='both' unions two upstream queries with independent "
            "cursors, so pagination is unavailable."
        )

    params: dict[str, Any] = {"lang": lang, "newestPubTypes": list(AWARD_PUB_TYPES)}
    if published_from:
        params["newestPublicationFrom"] = published_from
    if published_until:
        params["newestPublicationUntil"] = published_until
    if cursor:
        params["lastItem"] = cursor

    client = get_client()
    try:
        projects, pagination, provenance, stamp = await _run_search(client, params, filters)
    except UpstreamError as exc:
        return SearchResponse(
            **_degraded(exc), count=0, has_more=False, next_cursor=None, results=[]
        )

    next_cursor = pagination.get("lastItem")
    results = [_to_summary(e, lang) for e in projects]
    has_more = bool(next_cursor) and len(results) >= pagination.get("itemsPerPage", 20)
    return SearchResponse(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        note=_combine_notes(
            None if results else f"No awards matched. {_TENDER_HINT}",
            _canton_note(canton, canton_match),
        ),
        count=len(results),
        match_type="exact" if results else "none",
        has_more=has_more,
        next_cursor=next_cursor if has_more else None,
        results=results,
    )


@mcp.tool(annotations=READ_TOOL)
@logged_tool("get_procurement_details")
async def get_procurement_details(args: ProcurementDetailInput) -> ProcurementDetail:
    """<use_case>Retrieve the full record for one publication once you have its ids: criteria, deadlines, classification codes and the procuring body.</use_case>

    Return the full record for one procurement publication.

    Both ids come from a `search_procurements` result. The record includes the
    order description, CPV and Swiss construction codes (BKP, NPK), deadlines and
    the procurement office — the BKP codes make this joinable with construction
    cost data and school-building planning.
    """
    project_id, publication_id = args.project_id, args.publication_id
    language = args.language

    lang = normalise_language(language)
    client = get_client()
    try:
        payload, provenance, stamp = await client.publication_details(
            project_id, publication_id, lang
        )
    except UpstreamError as exc:
        return ProcurementDetail(
            **_degraded(exc), project_id=project_id, publication_id=publication_id, title=""
        )

    return _detail_from_payload(payload, project_id, publication_id, lang, provenance, stamp)


@mcp.tool(annotations=READ_TOOL)
@logged_tool("get_publication_history")
async def get_publication_history(args: HistoryInput) -> HistoryResponse:
    """<use_case>Trace one project through time — tender to award to correction. Use when the question is "what happened to this procurement?".</use_case>

    Return earlier publications of the same procurement project.

    Traces a project's lifecycle: tender → correction → award. An empty list is
    normal for a first publication.
    """
    publication_id, language = args.publication_id, args.language

    lang = normalise_language(language)
    client = get_client()
    try:
        payload, provenance, stamp = await client.past_publications(publication_id, lang)
    except UpstreamError as exc:
        return HistoryResponse(**_degraded(exc), project_id=None, count=0, publications=[])

    past = payload.get("pastPublications", [])
    entries = [
        HistoryEntry(
            publication_id=p.get("publicationId") or p.get("id"),
            publication_number=p.get("publicationNumber"),
            pub_type=p.get("pubType"),
            publication_date=p.get("publicationDate"),
            title=pick_lang(p.get("title"), lang),
        )
        for p in past
    ]
    return HistoryResponse(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        project_id=None,
        count=len(entries),
        publications=entries,
    )


# ARCH-003 hints. Written once so the three taxonomy lookups say the same thing
# and the two search tools say why they deliberately do not widen.
_CODE_HINT = (
    "Try a shorter or more general term — the upstream matches prefixes, so "
    "'Metall' finds what 'Metallbauarbeiten' may not."
)
_OFFICE_HINT = "Try a distinctive fragment of the name rather than the full official title."
_TENDER_HINT = (
    "This search is exact by design and does not widen your terms: a broadened "
    "procurement query can suggest a tender that does not exist. Drop a filter, "
    "widen the date range, or resolve the subject to a CPV code with "
    "`search_cpv_codes` and filter on that instead."
)


async def _code_search_widened(system: str, query: str, lang: str, limit: int):
    """Exact first; on an empty result retry with broader terms (ARCH-003).

    Returns `(raw, provenance, stamp, term_used, tried)`. `term_used` is what
    actually produced the rows — the caller needs it for the note, because a
    widened result presented as an exact one is precisely the failure mode this
    is meant to prevent.

    Each retry is another upstream request, so it only happens on a path that
    already returned nothing, and `widen()` caps how many there can be.
    """
    client = get_client()

    def _rows(payload):
        return payload.get("codes", []) if isinstance(payload, dict) else payload

    payload, provenance, stamp = await client.code_search(system, query, lang, limit)
    raw = _rows(payload)
    if raw:
        return raw, provenance, stamp, query, []

    tried: list[str] = []
    for candidate in widen(query):
        tried.append(candidate)
        payload, provenance, stamp = await client.code_search(system, candidate, lang, limit)
        raw = _rows(payload)
        if raw:
            return raw, provenance, stamp, candidate, tried
    return [], provenance, stamp, query, tried


@mcp.tool(annotations=READ_TOOL)
@logged_tool("search_cpv_codes")
async def search_cpv_codes(args: CpvSearchInput) -> CodeSearchResponse:
    """<use_case>Translate a keyword into the CPV classification codes needed to filter a search. Call this first when the user names a subject rather than a code.</use_case>

    Search CPV classification codes by keyword.

    CPV (Common Procurement Vocabulary) is the international code system used to
    filter `search_procurements` by category. Resolve a keyword like "Metall" to
    its code here, then pass the code to `search_procurements(cpv_codes=[...])`.
    """
    query, limit, language = args.query, args.limit, args.language

    lang = normalise_language(language)
    try:
        raw, provenance, stamp, used, tried = await _code_search_widened("cpv", query, lang, limit)
    except UpstreamError as exc:
        return CodeSearchResponse(**_degraded(exc), system="cpv", count=0, codes=[])

    codes = [
        CodeEntry(code=c.get("code", ""), label=pick_lang(c.get("label"), lang) or "") for c in raw
    ]
    widened = bool(codes) and used != query
    return CodeSearchResponse(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        system="cpv",
        count=len(codes),
        match_type="fuzzy" if widened else ("exact" if codes else "none"),
        note=widening_note(query, used, len(codes))
        if widened
        else (None if codes else empty_note(query, tried, _CODE_HINT)),
        codes=codes,
    )


@mcp.tool(annotations=READ_TOOL)
@logged_tool("search_construction_codes")
async def search_construction_codes(args: ConstructionCodeInput) -> CodeSearchResponse:
    """<use_case>Translate a keyword into Swiss construction cost codes (BKP, NPK, eBKP, OAG, CPC) — the bridge between a building topic and procurement filters.</use_case>

    Search Swiss construction classification codes by keyword.

    Args:
        system: One of bkp, npk, ebkp-h, ebkp-t, oag, cpc.
        query: Keyword.

    These are the Swiss construction cost standards (Baukostenplan, Normpositionen-
    katalog) used in building tenders — relevant for school-building procurement.
    """
    system, query = args.system, args.query
    limit, language = args.limit, args.language

    lang = normalise_language(language)
    sys_norm = system.lower()
    allowed = tuple(s for s in CODE_SYSTEMS if s != "cpv")
    if sys_norm not in allowed:
        raise ValueError(f"system must be one of {allowed}. For CPV use search_cpv_codes.")

    try:
        raw, provenance, stamp, used, tried = await _code_search_widened(
            sys_norm, query, lang, limit
        )
    except UpstreamError as exc:
        return CodeSearchResponse(**_degraded(exc), system=sys_norm, count=0, codes=[])

    codes = [
        CodeEntry(code=c.get("code", ""), label=pick_lang(c.get("label"), lang) or "") for c in raw
    ]
    widened = bool(codes) and used != query
    return CodeSearchResponse(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        system=sys_norm,
        count=len(codes),
        match_type="fuzzy" if widened else ("exact" if codes else "none"),
        note=widening_note(query, used, len(codes))
        if widened
        else (None if codes else empty_note(query, tried, _CODE_HINT)),
        codes=codes,
    )


@mcp.tool(annotations=READ_TOOL)
@logged_tool("find_procurement_office")
async def find_procurement_office(args: OfficeSearchInput) -> OfficeSearchResponse:
    """<use_case>Resolve a partial organisation name to the procuring offices simap knows, when the user names an authority rather than a project.</use_case>

    Find public procurement offices by (partial) name.

    The public office list is large (~1 MB), so this fetches it once and filters
    client-side. Returns the office id, type (cantonal / federal / communal) and
    the linked institution id.
    """
    name_contains, limit, language = args.name_contains, args.limit, args.language

    lang = normalise_language(language)
    needle = name_contains.lower().strip()
    client = get_client()
    try:
        payload, provenance, stamp = await client.procurement_offices_public(lang)
    except UpstreamError as exc:
        return OfficeSearchResponse(**_degraded(exc), count=0, offices=[])

    # The upstream has been observed returning the office list under two
    # different keys, so the shape is probed rather than assumed. The list case
    # is checked FIRST: it used to sit last, after two `.get()` calls that raise
    # AttributeError on a list — so the branch that claimed to handle a bare
    # list could never be reached, and that payload shape crashed the tool.
    if isinstance(payload, list):
        raw = payload
    elif isinstance(payload, dict):
        raw = (
            payload.get("procOffices")
            or payload.get("offices")
            or next((v for v in payload.values() if isinstance(v, list)), [])
        )
    else:
        raw = []

    def _filter(fragment: str) -> list[ProcurementOffice]:
        found: list[ProcurementOffice] = []
        for o in raw:
            name = pick_lang(o.get("name"), lang) or ""
            if fragment in name.lower():
                found.append(
                    ProcurementOffice(
                        id=o.get("id", ""),
                        name=name,
                        type=o.get("type"),
                        institution_id=o.get("institutionId"),
                    )
                )
                if len(found) >= limit:
                    break
        return found

    matched = _filter(needle)
    used, tried = name_contains, []
    # ARCH-003. Free here, unlike the code lookups: the office list is already in
    # memory, so widening costs a re-filter rather than another upstream request.
    if not matched:
        for candidate in widen(name_contains):
            tried.append(candidate)
            matched = _filter(candidate.lower().strip())
            if matched:
                used = candidate
                break

    widened = bool(matched) and used != name_contains
    return OfficeSearchResponse(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        count=len(matched),
        match_type="fuzzy" if widened else ("exact" if matched else "none"),
        note=widening_note(name_contains, used, len(matched))
        if widened
        else (None if matched else empty_note(name_contains, tried, _OFFICE_HINT)),
        offices=matched,
    )


@mcp.tool(annotations=READ_TOOL)
@logged_tool("source_status")
async def source_status(args: StatusInput | None = None) -> StatusResponse:
    """<use_case>Check whether simap.ch is reachable and how fast it is responding. Call this when a search returns nothing and you need to distinguish "no matching tenders" from "the source could not be asked" — the two are not the same answer.</use_case>

    Report reachability and latency of the simap.ch read API."""
    client = get_client()
    probe = await client.probe("simap.ch read API", "/cantons/v1?lang=de")
    status = SourceStatus(**probe)
    return StatusResponse(
        source=ATTRIBUTION,
        provenance="live_api",
        retrieved_at=utc_now_iso(),
        sources=[status],
        all_healthy=status.reachable,
    )


__all__ = ["PROJECT_SUB_TYPES", "mcp"]
