"""SEC-018: input validation at the tool boundary.

The check's pass criteria, one test group each: every argument schema-validated,
numeric fields bounded, string fields length-bounded with whitelist patterns,
`strict=True` and `extra="forbid"` set, and edge cases covered — over-long
strings, out-of-range numbers, unknown fields.

The drift guard at the bottom is the one worth keeping in mind: the allow-lists
are derived from `constants.py` rather than restated, and that derivation is
what these assertions protect.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from swiss_procurement_mcp.constants import (
    CANTON_IDS,
    CANTON_MATCH_MODES,
    PROCESS_TYPES,
    PUB_TYPES,
    SUPPORTED_LANGUAGES,
)
from swiss_procurement_mcp.inputs import (
    CONSTRUCTION_CODE_SYSTEMS,
    MAX_LIMIT,
    MAX_TEXT_LEN,
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

ALL_MODELS = [
    SearchInput,
    DetailedSearchInput,
    AwardSearchInput,
    ProcurementDetailInput,
    HistoryInput,
    CpvSearchInput,
    ConstructionCodeInput,
    OfficeSearchInput,
    StatusInput,
]


def _first_error_type(exc: pytest.ExceptionInfo[ValidationError]) -> str:
    return exc.value.errors()[0]["type"]


# --- model configuration --------------------------------------------------


@pytest.mark.parametrize("model", ALL_MODELS, ids=lambda m: m.__name__)
def test_every_model_is_strict_and_forbids_extras(model) -> None:
    assert model.model_config.get("strict") is True, f"{model.__name__} allows coercion"
    assert model.model_config.get("extra") == "forbid", f"{model.__name__} accepts extras"


@pytest.mark.parametrize("model", ALL_MODELS, ids=lambda m: m.__name__)
def test_every_model_rejects_an_unknown_field(model) -> None:
    """A silently-ignored field looks accepted — that is injection surface."""
    with pytest.raises(ValidationError) as exc:
        model.model_validate({"definitely_not_a_field": "x"})
    assert "extra_forbidden" in {e["type"] for e in exc.value.errors()}


def test_strict_mode_refuses_to_coerce_a_numeric_string() -> None:
    """Without strict=True Pydantic turns "10" into 10 and hides the confusion."""
    with pytest.raises(ValidationError) as exc:
        CpvSearchInput(query="metall", limit="10")
    assert _first_error_type(exc) == "int_type"


def test_strict_mode_refuses_to_coerce_a_boolean_string() -> None:
    with pytest.raises(ValidationError) as exc:
        SearchInput(query="metall", cpv_codes="72000000")
    assert _first_error_type(exc) == "list_type"


# --- numeric bounds -------------------------------------------------------


@pytest.mark.parametrize("limit", [0, -1])
def test_limit_below_range_rejected(limit) -> None:
    with pytest.raises(ValidationError) as exc:
        CpvSearchInput(query="metall", limit=limit)
    assert _first_error_type(exc) == "greater_than_equal"


@pytest.mark.parametrize("limit", [MAX_LIMIT + 1, 99999])
def test_limit_above_range_rejected(limit) -> None:
    with pytest.raises(ValidationError) as exc:
        OfficeSearchInput(name_contains="zurich", limit=limit)
    assert _first_error_type(exc) == "less_than_equal"


def test_limit_at_the_boundaries_is_accepted() -> None:
    assert CpvSearchInput(query="metall", limit=1).limit == 1
    assert CpvSearchInput(query="metall", limit=MAX_LIMIT).limit == MAX_LIMIT


def test_top_n_is_bounded_by_the_fan_out_cap() -> None:
    """ARCH-007: top_n drives parallel upstream requests, so it must stay small."""
    assert DetailedSearchInput(canton="ZH", top_n=5).top_n == 5
    with pytest.raises(ValidationError):
        DetailedSearchInput(canton="ZH", top_n=6)


# --- string bounds and patterns -------------------------------------------


def test_over_long_query_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        CpvSearchInput(query="x" * (MAX_TEXT_LEN + 1))
    assert _first_error_type(exc) == "string_too_long"


def test_too_short_query_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        CpvSearchInput(query="x")
    assert _first_error_type(exc) == "string_too_short"


@pytest.mark.parametrize(
    "hostile",
    [
        "test\x00injection",  # null byte
        "test\r\nX-Injected: 1",  # header-ish control characters
        "test<script>",  # markup
        'test"; DROP',  # quoting metacharacters
    ],
)
def test_query_pattern_is_a_whitelist(hostile) -> None:
    """Whitelist, not blacklist — a blacklist is bypassable via encoding."""
    with pytest.raises(ValidationError) as exc:
        CpvSearchInput(query=hostile)
    assert _first_error_type(exc) == "string_pattern_mismatch"


@pytest.mark.parametrize(
    "legitimate",
    [
        "Metallverkleidung",
        "Zürich Schulhaus",  # German umlauts
        "Bâtiment scolaire",  # French circumflex
        "Manutenzione stradale",
        "IT-Beschaffung (Los 2)",
        "Reinigung & Unterhalt",
        "72000000",
    ],
)
def test_real_procurement_language_passes_the_pattern(legitimate) -> None:
    """The whitelist has to survive three national languages, or it is useless."""
    assert CpvSearchInput(query=legitimate).query == legitimate


def test_dates_must_be_iso() -> None:
    assert SearchInput(published_from="2026-07-01").published_from == "2026-07-01"
    with pytest.raises(ValidationError) as exc:
        SearchInput(published_from="01.07.2026")
    assert _first_error_type(exc) == "string_pattern_mismatch"


def test_ids_are_bounded_and_character_restricted() -> None:
    ok = ProcurementDetailInput(project_id="proj-1", publication_id="pub-1")
    assert ok.project_id == "proj-1"
    with pytest.raises(ValidationError):
        ProcurementDetailInput(project_id="a" * 65, publication_id="pub-1")
    with pytest.raises(ValidationError):
        ProcurementDetailInput(project_id="../etc/passwd", publication_id="pub-1")


def test_cpv_codes_entries_must_be_numeric() -> None:
    assert SearchInput(cpv_codes=["72000000", "45"]).cpv_codes == ["72000000", "45"]
    with pytest.raises(ValueError, match="2–8 digits"):
        SearchInput(cpv_codes=["not-a-code"])


def test_cpv_codes_list_is_length_capped() -> None:
    with pytest.raises(ValidationError):
        SearchInput(cpv_codes=["72000000"] * 21)


# --- allow-lists ----------------------------------------------------------


def test_canton_must_be_a_bare_id() -> None:
    """Probe finding: simap uses ZH, not CH-ZH."""
    assert SearchInput(canton="ZH").canton == "ZH"
    with pytest.raises(ValidationError) as exc:
        SearchInput(canton="CH-ZH")
    assert _first_error_type(exc) == "literal_error"


def test_pub_type_award_is_rejected_in_favour_of_the_split_values() -> None:
    """Probe finding: a plain "award" is not a pub_type; the four split ones are."""
    with pytest.raises(ValidationError):
        SearchInput(pub_type="award")
    assert SearchInput(pub_type="award_tender").pub_type == "award_tender"


def test_unknown_language_rejected() -> None:
    with pytest.raises(ValidationError):
        CpvSearchInput(query="metall", language="rm")


def test_uppercase_language_rejected_under_strict_mode() -> None:
    """Deliberate: strict mode does not silently normalise 'DE' to 'de'."""
    with pytest.raises(ValidationError):
        CpvSearchInput(query="metall", language="DE")


# --- drift guard ----------------------------------------------------------


@pytest.mark.parametrize(
    "model,field,expected",
    [
        (SearchInput, "canton", CANTON_IDS),
        (SearchInput, "canton_match", CANTON_MATCH_MODES),
        (SearchInput, "process_type", PROCESS_TYPES),
        (SearchInput, "pub_type", PUB_TYPES),
        (ConstructionCodeInput, "system", CONSTRUCTION_CODE_SYSTEMS),
        (CpvSearchInput, "language", SUPPORTED_LANGUAGES),
    ],
)
def test_allow_lists_still_track_constants(model, field, expected) -> None:
    """The Literals are derived from constants.py; prove the derivation held.

    If someone restates a list inline, or a probe updates constants.py without
    the schema following, this is what fails.
    """
    schema = model.model_json_schema()
    prop = schema["properties"][field]

    # Optional fields render as anyOf[enum, null]; required ones render inline.
    if "anyOf" in prop:
        enums = [b["enum"] for b in prop["anyOf"] if "enum" in b]
        members = enums[0] if enums else []
    elif "$ref" in prop or "allOf" in prop:
        ref = prop.get("$ref") or prop["allOf"][0]["$ref"]
        members = schema["$defs"][ref.rsplit("/", 1)[-1]]["enum"]
    else:
        members = prop["enum"]

    assert set(members) == set(expected)
