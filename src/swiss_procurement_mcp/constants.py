"""Constants and lookup tables for the simap.ch procurement API.

Values marked `FINDING:` come from the live probe (2026-07-26) and must survive
future refactorings.
"""

from __future__ import annotations

# FINDING: The public read API lives under /api on the production host. The web
# UI at simap.ch/de is a separate SSR app and does NOT expose these endpoints —
# probing it was the reason for an earlier, wrong "no API" conclusion.
SIMAP_BASE = "https://www.simap.ch/api"

# FINDING: The host enforces a session cookie ("cookie-check"). The very first
# request is redirected to a cookie-check page; once the cookie is stored, all
# /api calls work. A cookie jar / persistent client is therefore mandatory.
COOKIE_SEED_URL = "https://www.simap.ch/api/cantons/v1?lang=de"

USER_AGENT = "swiss-procurement-mcp/0.1.0 (+https://github.com/malkreide/swiss-procurement-mcp)"

ATTRIBUTION = (
    "Data: simap.ch (Swiss public procurement platform), read API v1.5.1. "
    "Operated by the simap.ch association. Unofficial client; publications remain "
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
