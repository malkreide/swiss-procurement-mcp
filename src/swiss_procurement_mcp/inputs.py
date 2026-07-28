"""Pydantic input models for the tool boundary (SEC-018).

Tool arguments arrive from an LLM — a probabilistic source that can hallucinate,
mis-format, or be steered by prompt injection. Every argument is therefore
validated against a strict schema *before* it reaches tool logic, and the
constraints live in the schema rather than in imperative guards inside the tool
body, so the model can see them in the tool list.

Two model-level settings carry most of the weight:

- ``strict=True`` disables coercion. Without it Pydantic turns ``"10"`` into
  ``10`` and ``"true"`` into ``True``, which hides type confusion instead of
  reporting it.
- ``extra="forbid"`` rejects unknown fields rather than silently dropping them.
  A silently-ignored field is prompt-injection surface: it looks accepted.

The allow-lists (cantons, process types, publication types, code systems,
languages) are derived from ``constants.py`` rather than restated here, so a
change to the probe-derived tables cannot leave a stale copy behind. Patterns
are whitelist-based — a blacklist is bypassable via encoding or Unicode
normalisation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .constants import (
    CANTON_IDS,
    CANTON_MATCH_MODES,
    CODE_SYSTEMS,
    DEFAULT_CANTON_MATCH,
    DEFAULT_LANGUAGE,
    PROCESS_TYPES,
    PUB_TYPES,
    SUPPORTED_LANGUAGES,
)

# Subscripting Literal with a tuple is equivalent to listing its members, which
# is what lets these track constants.py. tests/test_input_models.py asserts the
# resulting members still match the tuples.
CantonId = Literal[CANTON_IDS]
CantonMatch = Literal[CANTON_MATCH_MODES]
ProcessType = Literal[PROCESS_TYPES]
PubType = Literal[PUB_TYPES]
CodeSystem = Literal[CODE_SYSTEMS]
# `search_cpv_codes` owns "cpv"; this tool covers the Swiss construction
# standards. Derived rather than restated, and narrower than CODE_SYSTEMS on
# purpose: the schema used to advertise "cpv" as a valid `system` and the tool
# then rejected it in the body, so a model trusting the schema was guaranteed
# to hit an error.
CONSTRUCTION_CODE_SYSTEMS = tuple(s for s in CODE_SYSTEMS if s != "cpv")
ConstructionCodeSystem = Literal[CONSTRUCTION_CODE_SYSTEMS]
LanguageCode = Literal[SUPPORTED_LANGUAGES]

MAX_LIMIT = 100
MAX_TEXT_LEN = 200
# Cap how many hits the aggregated tool expands to full detail, so one call fans
# out to a bounded number of parallel upstream requests (ARCH-007).
MAX_DETAIL_N = 5
MAX_CPV_CODES = 20

# Whitelist. `\w` is Unicode-aware in Python, so this covers the accented
# characters that German, French and Italian procurement titles actually carry,
# plus the punctuation seen in real queries — without opening the set to control
# characters, null bytes or quoting metacharacters.
#
# The whitespace here is a literal space, deliberately not `\s`: `\s` matches
# CR and LF, which would let `query="a\r\nX-Injected: 1"` through the filter.
# A procurement keyword never needs a line break.
TEXT_PATTERN = r"^[\w \-.,()/&'+:]+$"

# simap ids are UUIDs in the live API, but the shape is not contractually
# guaranteed anywhere we have measured, so this bounds length and character set
# rather than pinning a format we would have to guess at.
ID_PATTERN = r"^[A-Za-z0-9._-]{1,64}$"

DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

# simap CPV codes are numeric, 2 to 8 digits.
CPV_PATTERN = r"^\d{2,8}$"


class _StrictInput(BaseModel):
    """Shared configuration for every tool input model."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class _LanguageMixin(_StrictInput):
    language: LanguageCode = Field(
        default=DEFAULT_LANGUAGE,
        description="Preferred language for localised fields. One of de, fr, it, en.",
    )


class _DateRangeMixin(_LanguageMixin):
    published_from: str | None = Field(
        default=None,
        description="Earliest publication date, ISO 8601 (YYYY-MM-DD).",
        pattern=DATE_PATTERN,
    )
    published_until: str | None = Field(
        default=None,
        description="Latest publication date, ISO 8601 (YYYY-MM-DD).",
        pattern=DATE_PATTERN,
    )


class _CantonMixin(_DateRangeMixin):
    canton: CantonId | None = Field(
        default=None,
        description=(
            "Bare canton id such as ZH, BE, TI — not CH-ZH. Omit for all of "
            "Switzerland. See `canton_match` for what the filter means."
        ),
    )
    canton_match: CantonMatch = Field(
        default=DEFAULT_CANTON_MATCH,
        description=(
            "How `canton` is interpreted. 'procuring_body' (default) matches the "
            "issuing organisation; 'place_of_delivery' matches the order address, "
            "which around 60% of publications do not carry; 'both' unions the two "
            "and gives up pagination."
        ),
    )


class SearchInput(_CantonMixin):
    """Arguments for `search_procurements`."""

    query: str | None = Field(
        default=None,
        description="Free-text search over the project title and description.",
        min_length=2,
        max_length=MAX_TEXT_LEN,
        pattern=TEXT_PATTERN,
    )
    cpv_codes: list[str] | None = Field(
        default=None,
        description="CPV classification codes, 2–8 digits each, e.g. ['72000000'].",
        max_length=MAX_CPV_CODES,
    )
    process_type: ProcessType | None = Field(
        default=None,
        description="Procurement process type.",
    )
    pub_type: PubType | None = Field(
        default=None,
        description="Publication type.",
    )
    cursor: str | None = Field(
        default=None,
        description=(
            "Pagination cursor from a previous response's `next_cursor`. "
            "Unavailable when canton_match='both'."
        ),
        max_length=256,
    )

    # Declared on the field type as list[str]; the per-item pattern is not
    # expressible through Field(), so it is enforced here and still surfaces in
    # the error rather than in tool logic.
    def model_post_init(self, __context: object) -> None:
        import re

        for code in self.cpv_codes or []:
            if not re.match(CPV_PATTERN, code):
                raise ValueError(f"cpv_codes entries must be 2–8 digits; got {code!r}.")


class DetailedSearchInput(_CantonMixin):
    """Arguments for `search_procurements_detailed`."""

    query: str | None = Field(
        default=None,
        description="Free-text search over the project title and description.",
        min_length=2,
        max_length=MAX_TEXT_LEN,
        pattern=TEXT_PATTERN,
    )
    cpv_codes: list[str] | None = Field(
        default=None,
        description="CPV classification codes, 2–8 digits each.",
        max_length=MAX_CPV_CODES,
    )
    process_type: ProcessType | None = Field(default=None, description="Process type.")
    pub_type: PubType | None = Field(default=None, description="Publication type.")
    top_n: int = Field(
        default=3,
        description=(
            f"How many hits to expand to full detail (1–{MAX_DETAIL_N}). Each one "
            "costs an extra upstream request."
        ),
        ge=1,
        le=MAX_DETAIL_N,
    )

    def model_post_init(self, __context: object) -> None:
        import re

        for code in self.cpv_codes or []:
            if not re.match(CPV_PATTERN, code):
                raise ValueError(f"cpv_codes entries must be 2–8 digits; got {code!r}.")


class AwardSearchInput(_CantonMixin):
    """Arguments for `search_awards`."""

    cursor: str | None = Field(
        default=None,
        description="Pagination cursor from a previous response's `next_cursor`.",
        max_length=256,
    )


class ProcurementDetailInput(_LanguageMixin):
    """Arguments for `get_procurement_details`."""

    project_id: str = Field(
        description="Project id from a `search_procurements` result.",
        pattern=ID_PATTERN,
    )
    publication_id: str = Field(
        description="Publication id from the same result.",
        pattern=ID_PATTERN,
    )


class HistoryInput(_LanguageMixin):
    """Arguments for `get_publication_history`."""

    publication_id: str = Field(
        description="Publication id whose earlier publications should be returned.",
        pattern=ID_PATTERN,
    )


class CpvSearchInput(_LanguageMixin):
    """Arguments for `search_cpv_codes`."""

    query: str = Field(
        description="Keyword to search the CPV classification for.",
        min_length=2,
        max_length=MAX_TEXT_LEN,
        pattern=TEXT_PATTERN,
    )
    limit: int = Field(
        default=10,
        description=f"Maximum number of codes to return (1–{MAX_LIMIT}).",
        ge=1,
        le=MAX_LIMIT,
    )


class ConstructionCodeInput(_LanguageMixin):
    """Arguments for `search_construction_codes`."""

    system: ConstructionCodeSystem = Field(
        description="Which classification to search.",
    )
    query: str = Field(
        description="Keyword to search that classification for.",
        min_length=2,
        max_length=MAX_TEXT_LEN,
        pattern=TEXT_PATTERN,
    )
    limit: int = Field(
        default=10,
        description=f"Maximum number of codes to return (1–{MAX_LIMIT}).",
        ge=1,
        le=MAX_LIMIT,
    )


class OfficeSearchInput(_LanguageMixin):
    """Arguments for `find_procurement_office`."""

    name_contains: str = Field(
        description="Substring of the procurement office name.",
        min_length=2,
        max_length=MAX_TEXT_LEN,
        pattern=TEXT_PATTERN,
    )
    limit: int = Field(
        default=20,
        description=f"Maximum number of offices to return (1–{MAX_LIMIT}).",
        ge=1,
        le=MAX_LIMIT,
    )


class StatusInput(_StrictInput):
    """`source_status` takes no arguments; the model still forbids extras."""


class ProvenanceObservationInput(_StrictInput):
    """Bounded read-only observation of one public procurement or supplier URL."""

    url: str = Field(
        description=(
            "Public HTTP(S) URL to observe once. The result describes page reachability "
            "only; it does not establish stock, fulfillment, identity, or willingness to transact."
        ),
        min_length=12,
        max_length=2048,
        pattern=r"^https://[^\\s]+$",
    )
    timeout_seconds: int = Field(default=10, ge=1, le=20)
