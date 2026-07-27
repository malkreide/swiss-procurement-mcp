# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.1] — 2026-07-27

Release-plumbing only — no functional change to the server or its tools.

### Fixed

- **MCP Registry publish.** The registry rejected `server.json` with a `422`
  because `description` exceeded the 100-character limit (it was 217). Shortened
  to 97 characters, keeping the searchable domain terms and the scope claim
  (all cantons + federal).
- **PyPI package ownership validation.** The registry verifies ownership of a
  PyPI package by looking for an `mcp-name: <server-name>` marker in the
  published package README. It was missing, so the registry could not attribute
  the package to `io.github.malkreide/swiss-procurement-mcp`. Added as an HTML
  comment at the top of `README.md` (the package `long_description`), which
  keeps it invisible in the rendered README. Because PyPI releases are
  immutable, the marker can only reach PyPI via a new version — hence 0.3.1.

## [0.3.0] — 2026-07-26

Closes the last two open audit findings from the 0.2.0 hardening pass.

### Added

- **`search_procurements_detailed`** — aggregated tool that runs a search and
  fetches the full detail record for the top *n* hits in parallel
  (`asyncio.gather`), so the anchor query is answered in a single call instead of a
  search-then-N-details chain (ARCH-007). Bounded by `top_n` (1–5).
- `EnrichedSearchResponse` model (`count`, `total_matched`, `match_type`,
  `results: list[ProcurementDetail]`).

### Changed

- Attribution now states the data-reuse basis: the tenders are official
  public-procurement announcements and simap.ch publishes no explicit open-data
  licence, so reuse follows the simap.ch terms. Source/operator/terms are named in
  `ATTRIBUTION`, the README Credits and every response's `source` (CH-004).
- Refactored shared search-param building and detail mapping into `_build_search_params`
  and `_detail_from_payload` (used by both the single and aggregated tools).

## [0.2.0] — 2026-07-26

Audit-driven hardening following the `mcp-audit` run
(`audits/2026-07-26T131630-Z-swiss-procurement-mcp/`). No breaking change to
tool names or arguments; response models gain a `match_type` field.

### Added

- `match_type` (`exact` / `none`) on search, code and office responses (ARCH-003).
- Explicit egress allow-list: `ALLOWED_HOSTS` frozenset + `_assert_host_allowed`
  guard before every request, plus `docs/network-egress.md` (SEC-021).
- Input bounds at the tool boundary: `limit` restricted to 1–100 and free-text
  params length-capped (SEC-018), with tests.
- `openWorldHint` and `idempotentHint` on every tool via a shared `READ_TOOL`
  annotation (ARCH-009).
- `.github/workflows/security.yml` — gitleaks secret scan on push/PR (ARCH-005).
- `.github/dependabot.yml` — weekly pip + github-actions update PRs (ARCH-012).
- Tests for `get_publication_history`, `search_construction_codes` and
  `find_procurement_office`, previously uncovered (OPS-001).
- README "Maturity & updates" section (Phase 1 read-only, SDK-update policy)
  (OPS-003, ARCH-012); lethal-trifecta assessment in `SECURITY.md` (SEC-019).

### Changed

- The `degraded` envelope note is now a fixed, sanitised message and no longer
  embeds the raw exception or upstream response body (OBS-002).

## [0.1.0] — 2026-07-26

### Added

- Eight read-only tools over the simap.ch public procurement API (v1.5.1),
  covering all cantons and the Confederation.
- `search_procurements`, `search_awards`, `get_procurement_details`,
  `get_publication_history`, `search_cpv_codes`, `search_construction_codes`,
  `find_procurement_office`, `source_status`.
- Dual transport: stdio (Claude Desktop) and SSE / streamable-http (cloud).
- Pydantic v2 response envelope with `source`, `provenance`, `retrieved_at`.
- Retry with exponential backoff (2s / 4s / 8s); 4xx except 429 not retried.
- Graceful degradation instead of silent empty lists.

### Security

- HTTP transports (`MCP_TRANSPORT=sse|streamable-http`) bind to loopback
  (`127.0.0.1`) by default; exposing all interfaces now requires an explicit
  `MCP_HOST`/`HOST=0.0.0.0` opt-in (SEC-016). stdio (the default) does not bind.

### Known findings (live probe, 2026-07-26)

- **Read API lives under `www.simap.ch/api`**, not the `simap.ch/de` web UI.
  Probing the UI produced an earlier, mistaken "no API" conclusion. The search
  and detail endpoints are `security: None` and callable without authentication.
- **`lang` is mandatory** on project-search; omitting it is HTTP 400 (E0025),
  not an empty result. The client injects a default.
- **Award is not "award".** The value is split by procedure: `award_tender`,
  `award_study_contract`, `award_competition`, `direct_award`. `search_awards`
  queries all four.
- **Canton ids are bare** (`ZH`, not `CH-ZH`); an ISO code matches nothing and is
  rejected with a clear error.
- **Code fields are objects**, not strings: `cpvCode` and `bkpCodes` come back as
  `{code, label}`. Caught by a live test that a mocked fixture had missed —
  normalised centrally.
- **A session cookie is required**; a persistent HTTP client handles it.

### Scope

- Read-only. The ~200 write / OIDC-protected endpoints (publishing, submissions)
  are deliberately not wrapped.
