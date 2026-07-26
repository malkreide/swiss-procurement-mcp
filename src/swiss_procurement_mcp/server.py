"""MCP server exposing the public read endpoints of the simap.ch procurement API.

Strictly read-only. The simap API also exposes ~200 write / OIDC-protected
endpoints (publishing tenders, submitting offers); none of them are wrapped here.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import (
    SimapClient,
    UpstreamError,
    normalise_language,
    pick_lang,
    utc_now_iso,
)
from .constants import (
    ATTRIBUTION,
    AWARD_PUB_TYPES,
    CANTON_IDS,
    CODE_SYSTEMS,
    PROCESS_TYPES,
    PROJECT_SUB_TYPES,
    PUB_TYPES,
)
from .models import (
    CodeEntry,
    CodeSearchResponse,
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

mcp = FastMCP("swiss-procurement-mcp")

# ARCH-009: every tool is read-only, idempotent, and reaches the live simap.ch
# API (open world). Shared so the hints stay consistent across all tools.
READ_TOOL = {"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True}

# SEC-018: bound inputs at the tool boundary so out-of-range or oversized
# arguments fail fast with a clear error instead of being passed upstream.
MAX_LIMIT = 100
MAX_TEXT_LEN = 200


def _check_limit(limit: int) -> None:
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}.")


def _check_text(value: str | None, field: str) -> None:
    if value is not None and len(value) > MAX_TEXT_LEN:
        raise ValueError(f"{field} must be at most {MAX_TEXT_LEN} characters.")


def _degraded(exc: Exception) -> dict[str, Any]:
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


@mcp.tool(annotations=READ_TOOL)
async def search_procurements(
    query: str | None = None,
    canton: str | None = None,
    cpv_codes: list[str] | None = None,
    process_type: str | None = None,
    pub_type: str | None = None,
    published_from: str | None = None,
    published_until: str | None = None,
    cursor: str | None = None,
    language: str = "de",
) -> SearchResponse:
    """Search Swiss public procurement publications on simap.ch.

    Covers all cantons and the Confederation, updated intraday. This is the
    entry point; use `get_procurement_details` with the returned ids for the
    full record.

    Args:
        query: Free-text search over titles and descriptions.
        canton: Bare canton id, e.g. `ZH` (NOT `CH-ZH`). See `CANTON_IDS`.
        cpv_codes: One or more CPV classification codes. Resolve names to codes
            with `search_cpv_codes` first.
        process_type: One of open, selective, invitation, direct, no_process.
        pub_type: Publication type. For awarded contracts use one of
            award_tender, award_study_contract, award_competition, direct_award —
            a plain "award" is rejected by the API.
        published_from / published_until: ISO dates `YYYY-MM-DD`.
        cursor: Pagination cursor from a previous response's `next_cursor`.
        language: de, fr, it or en.
    """
    lang = normalise_language(language)
    _check_text(query, "query")

    if canton and canton.upper() not in CANTON_IDS:
        raise ValueError(f"Unknown canton {canton!r}. Use a bare id like ZH, not CH-ZH.")
    if process_type and process_type not in PROCESS_TYPES:
        raise ValueError(f"process_type must be one of {PROCESS_TYPES}.")
    if pub_type and pub_type not in PUB_TYPES:
        raise ValueError(f"pub_type must be one of {PUB_TYPES}.")

    params: dict[str, Any] = {"lang": lang}
    if query:
        params["search"] = query
    if canton:
        params["orderAddressCantons"] = canton.upper()
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

    async with SimapClient() as client:
        try:
            payload, provenance, stamp = await client.project_search(params)
        except UpstreamError as exc:
            return SearchResponse(
                **_degraded(exc), count=0, has_more=False, next_cursor=None, results=[]
            )

    projects = payload.get("projects", [])
    pagination = payload.get("pagination") or {}
    next_cursor = pagination.get("lastItem")
    results = [_to_summary(e, lang) for e in projects]
    has_more = bool(next_cursor) and len(results) >= pagination.get("itemsPerPage", 20)

    note = None
    if not results:
        note = "No publications matched. Widen the date range or check canton/CPV filters."
    return SearchResponse(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        note=note,
        count=len(results),
        match_type="exact" if results else "none",
        has_more=has_more,
        next_cursor=next_cursor if has_more else None,
        results=results,
    )


@mcp.tool(annotations=READ_TOOL)
async def search_awards(
    canton: str | None = None,
    published_from: str | None = None,
    published_until: str | None = None,
    cursor: str | None = None,
    language: str = "de",
) -> SearchResponse:
    """Search only awarded contracts (who won).

    Convenience wrapper over `search_procurements` that queries all four award
    publication types at once. Note that award coverage is uneven across
    cantons — some publish awards diligently, others rarely.
    """
    lang = normalise_language(language)
    if canton and canton.upper() not in CANTON_IDS:
        raise ValueError(f"Unknown canton {canton!r}. Use a bare id like ZH.")

    params: dict[str, Any] = {"lang": lang, "newestPubTypes": list(AWARD_PUB_TYPES)}
    if canton:
        params["orderAddressCantons"] = canton.upper()
    if published_from:
        params["newestPublicationFrom"] = published_from
    if published_until:
        params["newestPublicationUntil"] = published_until
    if cursor:
        params["lastItem"] = cursor

    async with SimapClient() as client:
        try:
            payload, provenance, stamp = await client.project_search(params)
        except UpstreamError as exc:
            return SearchResponse(
                **_degraded(exc), count=0, has_more=False, next_cursor=None, results=[]
            )

    projects = payload.get("projects", [])
    pagination = payload.get("pagination") or {}
    next_cursor = pagination.get("lastItem")
    results = [_to_summary(e, lang) for e in projects]
    has_more = bool(next_cursor) and len(results) >= pagination.get("itemsPerPage", 20)
    return SearchResponse(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        count=len(results),
        match_type="exact" if results else "none",
        has_more=has_more,
        next_cursor=next_cursor if has_more else None,
        results=results,
    )


@mcp.tool(annotations=READ_TOOL)
async def get_procurement_details(
    project_id: str, publication_id: str, language: str = "de"
) -> ProcurementDetail:
    """Return the full record for one procurement publication.

    Both ids come from a `search_procurements` result. The record includes the
    order description, CPV and Swiss construction codes (BKP, NPK), deadlines and
    the procurement office — the BKP codes make this joinable with construction
    cost data and school-building planning.
    """
    lang = normalise_language(language)
    async with SimapClient() as client:
        try:
            payload, provenance, stamp = await client.publication_details(
                project_id, publication_id, lang
            )
        except UpstreamError as exc:
            return ProcurementDetail(
                **_degraded(exc), project_id=project_id, publication_id=publication_id, title=""
            )

    info = payload.get("project-info") or {}
    proc = payload.get("procurement") or {}
    dates = payload.get("dates") or {}
    base = payload.get("base") or {}

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
        procurement_office=pick_lang(info.get("procOfficeAddress", {}).get("name"), lang)
        if isinstance(info.get("procOfficeAddress"), dict)
        else None,
        procurement_office_address=info.get("procOfficeAddress")
        if isinstance(info.get("procOfficeAddress"), dict)
        else None,
        offer_deadline=dates.get("offerDeadline"),
        publication_date=dates.get("publicationDate"),
        has_documents=bool(payload.get("hasProjectDocuments")),
    )


@mcp.tool(annotations=READ_TOOL)
async def get_publication_history(publication_id: str, language: str = "de") -> HistoryResponse:
    """Return earlier publications of the same procurement project.

    Traces a project's lifecycle: tender → correction → award. An empty list is
    normal for a first publication.
    """
    lang = normalise_language(language)
    async with SimapClient() as client:
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


@mcp.tool(annotations=READ_TOOL)
async def search_cpv_codes(query: str, limit: int = 10, language: str = "de") -> CodeSearchResponse:
    """Search CPV classification codes by keyword.

    CPV (Common Procurement Vocabulary) is the international code system used to
    filter `search_procurements` by category. Resolve a keyword like "Metall" to
    its code here, then pass the code to `search_procurements(cpv_codes=[...])`.
    """
    lang = normalise_language(language)
    _check_limit(limit)
    _check_text(query, "query")
    async with SimapClient() as client:
        try:
            payload, provenance, stamp = await client.code_search("cpv", query, lang, limit)
        except UpstreamError as exc:
            return CodeSearchResponse(**_degraded(exc), system="cpv", count=0, codes=[])

    raw = payload.get("codes", []) if isinstance(payload, dict) else payload
    codes = [
        CodeEntry(code=c.get("code", ""), label=pick_lang(c.get("label"), lang) or "") for c in raw
    ]
    return CodeSearchResponse(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        system="cpv",
        count=len(codes),
        match_type="exact" if codes else "none",
        codes=codes,
    )


@mcp.tool(annotations=READ_TOOL)
async def search_construction_codes(
    system: str, query: str, limit: int = 10, language: str = "de"
) -> CodeSearchResponse:
    """Search Swiss construction classification codes by keyword.

    Args:
        system: One of bkp, npk, ebkp-h, ebkp-t, oag, cpc.
        query: Keyword.

    These are the Swiss construction cost standards (Baukostenplan, Normpositionen-
    katalog) used in building tenders — relevant for school-building procurement.
    """
    lang = normalise_language(language)
    _check_limit(limit)
    _check_text(query, "query")
    sys_norm = system.lower()
    allowed = tuple(s for s in CODE_SYSTEMS if s != "cpv")
    if sys_norm not in allowed:
        raise ValueError(f"system must be one of {allowed}. For CPV use search_cpv_codes.")

    async with SimapClient() as client:
        try:
            payload, provenance, stamp = await client.code_search(sys_norm, query, lang, limit)
        except UpstreamError as exc:
            return CodeSearchResponse(**_degraded(exc), system=sys_norm, count=0, codes=[])

    raw = payload.get("codes", []) if isinstance(payload, dict) else payload
    codes = [
        CodeEntry(code=c.get("code", ""), label=pick_lang(c.get("label"), lang) or "") for c in raw
    ]
    return CodeSearchResponse(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        system=sys_norm,
        count=len(codes),
        match_type="exact" if codes else "none",
        codes=codes,
    )


@mcp.tool(annotations=READ_TOOL)
async def find_procurement_office(
    name_contains: str, limit: int = 20, language: str = "de"
) -> OfficeSearchResponse:
    """Find public procurement offices by (partial) name.

    The public office list is large (~1 MB), so this fetches it once and filters
    client-side. Returns the office id, type (cantonal / federal / communal) and
    the linked institution id.
    """
    lang = normalise_language(language)
    _check_limit(limit)
    _check_text(name_contains, "name_contains")
    needle = name_contains.lower().strip()
    async with SimapClient() as client:
        try:
            payload, provenance, stamp = await client.procurement_offices_public(lang)
        except UpstreamError as exc:
            return OfficeSearchResponse(**_degraded(exc), count=0, offices=[])

    raw = (
        payload.get("procOffices")
        or payload.get("offices")
        or (
            payload
            if isinstance(payload, list)
            else next((v for v in payload.values() if isinstance(v, list)), [])
        )
    )
    matched: list[ProcurementOffice] = []
    for o in raw:
        name = pick_lang(o.get("name"), lang) or ""
        if needle in name.lower():
            matched.append(
                ProcurementOffice(
                    id=o.get("id", ""),
                    name=name,
                    type=o.get("type"),
                    institution_id=o.get("institutionId"),
                )
            )
            if len(matched) >= limit:
                break
    return OfficeSearchResponse(
        source=ATTRIBUTION,
        provenance=provenance,
        retrieved_at=stamp,
        count=len(matched),
        match_type="exact" if matched else "none",
        offices=matched,
    )


@mcp.tool(annotations=READ_TOOL)
async def source_status() -> StatusResponse:
    """Report reachability and latency of the simap.ch read API."""
    async with SimapClient() as client:
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
