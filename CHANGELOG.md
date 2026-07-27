# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.5.0] — 2026-07-27

Closes OBS-003, the only `fail` in either server's audit. No behaviour changes.

### The gap

The 2026-07-27 re-audit graded OBS-003 down from `partial` to `fail` on unchanged
code: this server had no logging at all — no mechanism, no output format, no
severity levels, no per-call context. Exactly one of five criteria was met, and
that one was "does not use `print()`", which it met by having no output at all.

An operator running this server could not answer "is it being called, is it
slow, is simap.ch up" from anything the process emitted.

### Added

- **`_log.py`** — structured JSON to stderr, ported from the companion
  `amtsblatt-mcp`. One change was needed: the tools here take ordinary keyword
  arguments and return Pydantic models, where the original assumed a single
  `params` model and a `str` return, so `logged_tool` now wraps
  `*args, **kwargs` generically.
- **One `tool_call` record per call** on all nine tools, carrying tool name,
  `ok`/`error` status and latency in milliseconds. Rejected inputs count as
  `error` rather than going unrecorded.
- **`upstream_degraded` at `WARNING`** on simap.ch failures, carrying the
  exception *type*. `_degraded()` is the single funnel for all eight upstream
  failure paths, so one call site covers every one of them.
- **`LOG_LEVEL`** (default `INFO`), documented in the README's configuration
  table alongside a sample record.

### Why stderr, specifically

On a stdio transport stdout carries the MCP protocol; one stray line there
corrupts the session. The logger writes to stderr and sets `propagate = False`
so records cannot reach root handlers, which commonly target stdout.
`tests/test_logging.py` asserts both, and asserts them against the constructor
path rather than the import-time handle that pytest's capture replaces.

### The risk this port carried

`logged_tool` wraps `*args, **kwargs`, and FastMCP derives each tool's argument
schema from the function signature. Had `functools.wraps` not set `__wrapped__`
for `inspect.signature` to follow, every tool would have silently degraded to
"no arguments" — a regression no existing test would have caught, since the
functions stay directly callable and the whole suite calls them directly.
`test_decorator_preserves_the_tool_argument_schema` goes through
`mcp.list_tools()` and pins the real parameters instead of assuming.

### Not changed

OBS-002 still holds: the sanitised note the model sees never carries the
exception message or an upstream response body, and the new `WARNING` record
carries only the exception type — asserted by a test that feeds a URL with a
token in it and checks it does not appear in the log.

## [0.4.0] — 2026-07-27

Correctness release. The canton filter was measurably wrong, and the fix changes
what `canton=` means — see *Breaking* below.

### Breaking

- **`canton=` now matches the PROCURING BODY, not the place of delivery.**

  simap offers exactly one geographic filter, `orderAddressCantons`, and the
  OpenAPI spec describes it as the canton the project *takes place* in. When a
  procuring office files a free-text address (`orderAddressOnlyDescription:
  "yes"`) the structured `orderAddress.cantonId` is `null` and the publication is
  invisible to that filter. Measured CH-wide over 500 projects published since
  2026-07-01: **303 (60.6%) carry no canton** — among them the Amt für Hochbauten
  Zürich, Grün Stadt Zürich, Universitätsspital Zürich, BBL and SBB.

  `issuedByOrganizations` is the remedy: the spec states it matches publications
  issued by an organisation *or as a child of it*, so one root institution id
  covers a canton's whole tree of procurement offices. `/institutions/v1/institutions`
  is public and returns 28 roots — the 26 cantons plus Bund and Ausland.

  Measured for ZH over 2026-07-01…27, both filters fully paginated:

  | Filter | Projects |
  |---|---|
  | `orderAddressCantons=ZH` (old behaviour) | 263 |
  | `issuedByOrganizations=<Zürich>` (new default) | **410** |
  | union | 441 |

  The 31 projects only the address filter finds are federal bodies procuring in
  Zurich (ETH, Empa, Flughafen Zürich AG) — a different question, not a gap.
  Hence three explicit semantics via the new `canton_match` argument
  (`procuring_body` default, `place_of_delivery`, `both`) rather than a silent
  union, and every response states in `note` which one was applied.

  To keep the previous behaviour, pass `canton_match="place_of_delivery"`.

- **A filterless `search_procurements()` now raises instead of returning empty.**
  simap answers an unfiltered project-search with zero projects, not with
  everything. The old code reported that as "No publications matched. Widen the
  date range" — a misdiagnosis, since nothing had been narrowed. It now says
  that at least one filter is required.

### Fixed

- **`mcp>=1.28.1`** (was `>=1.2.0`), matching the CVE-2026-59950 floor already
  set in the companion server `amtsblatt-mcp`.
- **User-Agent no longer drifts from the package version.** It advertised 0.3.0
  while the package was 0.3.1; `VERSION` in `constants.py` is now the single
  source and `__init__.__version__` re-exports it (it had been pinned at 0.1.0).

### Added

- `canton_match` on `search_procurements`, `search_procurements_detailed` and
  `search_awards`; `CANTON_INSTITUTION_IDS` (26 pinned root institution ids) and
  `SimapClient.institutions()`.
- **Live drift guards.** One verifies all 26 pinned institution ids are still
  root institutions and that exactly 28 roots exist; another checks
  `PUB_TYPES`, `PROCESS_TYPES` and `PROJECT_SUB_TYPES` against the machine-readable
  spec at `https://www.simap.ch/api/specifications/simap.yaml` (13/13, 5/5, 10/10
  — currently exact). A third asserts `procuring_body` keeps finding at least as
  much as `place_of_delivery`.

### Changed

- Documented that `project-search` indexes **projects**, not publications: each
  hit is a project represented by its newest publication. `search_awards`
  consequently only finds projects whose *newest* publication is an award — a
  later correction hides it, and `get_publication_history` is the way back.
  Tool descriptions and README updated; no behavioural change.

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
