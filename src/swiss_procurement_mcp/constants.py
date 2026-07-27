"""Constants and lookup tables for the simap.ch procurement API.

Values marked `FINDING:` come from the live probe (2026-07-26) and must survive
future refactorings.
"""

from __future__ import annotations

# FINDING: The public read API lives under /api on the production host. The web
# UI at simap.ch/de is a separate SSR app and does NOT expose these endpoints —
# probing it was the reason for an earlier, wrong "no API" conclusion.
SIMAP_BASE = "https://www.simap.ch/api"

# SEC-021: explicit egress allow-list. Every outbound request is asserted
# against this set before it is sent, so even a future refactor cannot widen
# egress beyond the simap.ch host without changing this line.
ALLOWED_HOSTS = frozenset({"www.simap.ch"})

# FINDING: The host enforces a session cookie ("cookie-check"). The very first
# request is redirected to a cookie-check page; once the cookie is stored, all
# /api calls work. A cookie jar / persistent client is therefore mandatory.
COOKIE_SEED_URL = "https://www.simap.ch/api/cantons/v1?lang=de"

# Single source of truth for the version string; `__init__` re-exports it, so
# the User-Agent cannot drift from the packaged version again (it said 0.3.0
# while the package was already 0.3.1).
VERSION = "0.4.0"
USER_AGENT = f"swiss-procurement-mcp/{VERSION} (+https://github.com/malkreide/swiss-procurement-mcp)"

ATTRIBUTION = (
    "Data: simap.ch (Swiss public procurement platform), read API v1.5.1, operated "
    "by the simap.ch association (www.simap.ch). The underlying tenders are official "
    "public-procurement announcements by Swiss public bodies. simap.ch publishes no "
    "explicit open-data licence; reuse is subject to the simap.ch terms "
    "(www.simap.ch/de/about/legal). Unofficial client; publications remain "
    "authoritative on the platform itself."
)

DEFAULT_LANGUAGE = "de"
SUPPORTED_LANGUAGES = ("de", "fr", "it", "en")

# FINDING: lang is a REQUIRED query parameter on project-search. Omitting it
# yields HTTP 400 / errorCode E0025, not an empty result.

# FINDING: project-search, publication-details and all reference endpoints are
# marked `security: None` in the OpenAPI spec and were confirmed callable
# without any authentication. Everything under /my, /pub-drafts and the write
# verbs needs OIDC and is deliberately NOT wrapped by this server.

# FINDING: 26 cantons, returned as {"cantons": [{"id": "ZH", "nuts3": "CH040"}]}
# — an object, not a bare list. Canton ids are bare two-letter codes (ZH),
# NOT ISO subdivision codes (CH-ZH). Do not prepend "CH-".
CANTON_IDS = (
    "ZH",
    "BE",
    "LU",
    "UR",
    "SZ",
    "OW",
    "NW",
    "ZG",
    "GL",
    "FR",
    "SO",
    "BS",
    "BL",
    "SH",
    "AR",
    "AI",
    "SG",
    "GR",
    "AG",
    "TG",
    "TI",
    "VD",
    "VS",
    "NE",
    "GE",
    "JU",
)

# FINDING (verified live): the award filter is NOT "award". A naive guess of
# newestPubTypes=award returns HTTP 400. Awards are split by procedure:
PUB_TYPES = (
    "advance_notice",
    "request_for_information",
    "tender",
    "competition",
    "study_contract",
    "award_tender",
    "award_study_contract",
    "award_competition",
    "direct_award",
    "participant_selection",
    "revocation",
    "abandonment",
    "selective_offering_phase",
)

# Convenience group: everything that represents an awarded contract.
AWARD_PUB_TYPES = (
    "award_tender",
    "award_study_contract",
    "award_competition",
    "direct_award",
)

PROCESS_TYPES = ("open", "selective", "invitation", "direct", "no_process")

# FINDING (verified live 2026-07-27, and against the OpenAPI spec at
# https://www.simap.ch/api/specifications/simap.yaml): `orderAddressCantons` is
# the ONLY geographic filter project-search offers, and the spec describes it as
# the canton the project "takes place" in — the delivery address, not the
# procuring body. When a procuring office files a free-text address
# (`orderAddressOnlyDescription: "yes"`) the structured `orderAddress.cantonId`
# is null, and the publication becomes invisible to that filter.
#
# Measured CH-wide over 500 projects published since 2026-07-01: 303 (60.6%)
# carry `cantonId: null`. Among them the Amt für Hochbauten Zürich, Grün Stadt
# Zürich, Universitätsspital Zürich, BBL and SBB.
#
# `issuedByOrganizations` is the fix. The spec states it matches publications
# "issued by one of the selected organizations OR AS A CHILD of the selected
# organizations", so one root institution id covers a canton's whole tree of
# procurement offices. `/institutions/v1/institutions` is public and returns 28
# roots: the 26 cantons plus Bund and Ausland.
#
# Measured for ZH over 2026-07-01..27, both filters fully paginated:
#   orderAddressCantons=ZH    263 projects
#   issuedByOrganizations=ZH  410 projects   (+178, of which 177 cantonId null)
#   union                     441            (31 only via the address filter)
# The 31 address-only hits are federal bodies procuring in Zurich (ETH, Empa,
# Flughafen Zürich AG) — a different question, not a gap, hence three explicit
# semantics rather than a silent union.
INSTITUTIONS_PATH = "/institutions/v1/institutions"

# Root institution per canton. An explicit literal map, NOT a name match: the
# institution names are localised and irregular ("Tessin", "Waadt", "Genf",
# "Appenzell A.Rh."), so matching them at runtime would be exactly the kind of
# silent-failure heuristic this codebase avoids. `test_live.py` verifies every
# id against the live endpoint, which is what catches an upstream change.
CANTON_INSTITUTION_IDS: dict[str, str] = {
    "AG": "1bd29620-e4b2-4586-ac50-1d3095db276a",
    "AI": "1a3a0479-5cee-477b-9df1-9cd949299e9b",
    "AR": "8a3d36db-471a-4291-9ff9-02cb9981527f",
    "BE": "62faa47e-8f6e-41de-8b12-0ed76ea91ddc",
    "BL": "60f90ca8-671a-4523-bd8d-e17bdca06062",
    "BS": "6c460fe0-370d-49f2-a16f-6e4bd9601048",
    "FR": "fa1d37de-f257-444f-89fe-697d102669d5",
    "GE": "d03fdaa0-62a2-4338-894e-8ff20828b067",
    "GL": "8d8dc54a-9b3d-44c7-900c-625c7c1d9f7a",
    "GR": "b1be671a-1bd4-4b7f-b0df-48b8485b7716",
    "JU": "ceceb99b-854d-4ef3-87e2-a0463ce706d5",
    "LU": "936b7d5b-7838-4a04-a31c-7e1a5301730a",
    "NE": "c1965ee3-76bc-4621-b21a-f618b6a43713",
    "NW": "c329864f-0912-48ce-bc47-c82b33501751",
    "OW": "9d1f82ad-a5ab-4877-b9de-b0812af7f684",
    "SG": "85e540d1-7d85-42ce-a294-7cdfa5f177a7",
    "SH": "69a6e1d1-8377-4023-9d6e-302748b3aad0",
    "SO": "c0acbf83-7a34-4042-b581-1feeba5fddf6",
    "SZ": "221f3f07-657a-4faa-815d-1a8ea41c8b76",
    "TG": "16102a65-a5dc-433c-bf08-33c2f77aa7e2",
    "TI": "1306538b-12b9-4874-801c-9d0e4fa18a4d",
    "UR": "2fd79e15-368d-404d-adaf-d4207d1b3426",
    "VD": "f595059a-68c3-4143-812f-82bc1f44f889",
    "VS": "f8e02dc2-fd1f-4d80-85ab-21878cb328c8",
    "ZG": "27f906df-279a-456b-9006-fe267d9e124c",
    "ZH": "47a89920-1758-4cf4-aa7d-11f02fcc631e",
}

# The two non-cantonal roots. Not reachable via `canton=`, but named so the
# live test can assert the full set of 28 and notice a taxonomy change.
INSTITUTION_ID_CONFEDERATION = "52ec29e2-da01-4edc-a563-5b8a431f7cb1"
INSTITUTION_ID_FOREIGN = "f81834be-ccf1-4c99-8248-ef4e5c8b236c"

CANTON_MATCH_MODES = ("procuring_body", "place_of_delivery", "both")
DEFAULT_CANTON_MATCH = "procuring_body"

PROJECT_SUB_TYPES = (
    "construction",
    "service",
    "supply",
    "project_competition",
    "idea_competition",
    "overall_performance_competition",
    "project_study",
    "idea_study",
    "overall_performance_study",
    "request_for_information",
)

# Construction classification systems exposed as their own search endpoints.
# CPV is the international one; the rest are Swiss construction cost standards.
CODE_SYSTEMS = ("cpv", "cpc", "bkp", "npk", "ebkp-h", "ebkp-t", "oag")
