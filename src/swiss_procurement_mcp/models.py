"""Pydantic v2 models. Every response carries source + provenance."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Provenance = Literal["live_api", "cached", "degraded"]


class Envelope(BaseModel):
    source: str
    provenance: Provenance
    retrieved_at: str
    note: str | None = None


class ProcurementSummary(BaseModel):
    project_id: str
    publication_id: str
    title: str
    project_number: str | None = None
    publication_number: str | None = None
    project_type: str | None = Field(default=None, description="e.g. tender, award")
    project_sub_type: str | None = Field(default=None, description="e.g. construction, service")
    process_type: str | None = Field(default=None, description="e.g. open, selective, direct")
    pub_type: str | None = None
    publication_date: str | None = None
    procurement_office: str | None = None
    canton: str | None = Field(default=None, description="Bare canton id, e.g. ZH (not CH-ZH).")
    city: str | None = None
    postal_code: str | None = None


class SearchResponse(Envelope):
    count: int
    match_type: str = Field(
        default="none", description="exact when results were returned, none when empty."
    )
    has_more: bool = Field(description="True if the pagination cursor can be advanced.")
    next_cursor: str | None = Field(
        default=None, description="Pass as `cursor` to search_procurements for the next page."
    )
    results: list[ProcurementSummary]


class ProcurementDetail(Envelope):
    project_id: str
    publication_id: str
    title: str
    order_description: str | None = None
    process_type: str | None = None
    order_type: str | None = None
    cpv_code: str | None = Field(default=None, description="Main CPV classification code.")
    additional_cpv_codes: list[str] = Field(default_factory=list)
    bkp_codes: list[str] = Field(default_factory=list, description="Swiss BKP construction codes.")
    npk_codes: list[str] = Field(default_factory=list)
    procurement_office: str | None = None
    procurement_office_address: dict | None = None
    offer_deadline: str | None = None
    publication_date: str | None = None
    has_documents: bool = False


class EnrichedSearchResponse(Envelope):
    count: int = Field(description="Number of full detail records returned (<= top_n).")
    match_type: str = Field(
        default="none", description="exact when results were returned, none when empty."
    )
    total_matched: int = Field(
        default=0, description="Total search hits before the top_n detail cutoff."
    )
    results: list[ProcurementDetail]


class CodeEntry(BaseModel):
    code: str
    label: str


class CodeSearchResponse(Envelope):
    system: str = Field(description="cpv, bkp, npk, cpc, ebkp-h, ebkp-t or oag.")
    count: int
    match_type: str = Field(
        default="none", description="exact when codes were returned, none when empty."
    )
    codes: list[CodeEntry]


class ProcurementOffice(BaseModel):
    id: str
    name: str
    type: str | None = Field(default=None, description="e.g. cantonal, federal, communal.")
    institution_id: str | None = None


class OfficeSearchResponse(Envelope):
    count: int
    match_type: str = Field(
        default="none", description="exact when offices matched, none when empty."
    )
    offices: list[ProcurementOffice]


class HistoryEntry(BaseModel):
    publication_id: str | None = None
    publication_number: str | None = None
    pub_type: str | None = None
    publication_date: str | None = None
    title: str | None = None


class HistoryResponse(Envelope):
    project_id: str | None = None
    count: int
    publications: list[HistoryEntry]


class SourceStatus(BaseModel):
    name: str
    base_url: str
    reachable: bool
    http_status: int | None = None
    latency_ms: int | None = None


class StatusResponse(Envelope):
    sources: list[SourceStatus]
    all_healthy: bool


class ProvenanceObservation(BaseModel):
    source_url: str
    observed_at: str
    retrieval_method: Literal["https_get"]
    http_status: int | None = None
    latency_ms: int
    reachable: bool
    bounded_confidence: float = Field(ge=0, le=1)
    freshness: str
    unknowns: list[str]


class ProvenanceObservationResponse(Envelope):
    observation: ProvenanceObservation
