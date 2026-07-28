# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.8.1] — 2026-07-28

Documentation only. Records SEC-009 and SCALE-002 as accepted risks, and repairs
drift in `SECURITY.md` that had been there for four audit runs.

### SEC-009 and SCALE-002 — accepted, with the condition that ends each

Both were going to be closed by removing the HTTP transports, which would have
made them non-applicable. Measuring that change first showed it also drops
**SEC-005** and **SEC-016** from the applicable set — and both of those *pass*.
SEC-016 is `critical` and was closed with real work in v0.1.1 (the loopback
default bind).

So the scope reduction would have traded two documented partials for two earned
passes, and made the server no safer. The transports stay; the two findings are
recorded as accepted risks instead, each with the condition that would end the
acceptance:

- **SEC-009** becomes real the moment the server gains authentication, per-user
  state, or any endpoint whose response depends on who is asking.
- **SCALE-002** becomes real when multi-instance deployment and session state
  exist *together*. Either alone is survivable.

### Fixed — SECURITY.md described a server that no longer existed

The document still cited **15 pass / 16 partial / 1 fail** from the first audit,
four runs stale, and listed *container sandboxing* and *structured logging* as
accepted risks — long after both were implemented and had flipped to `pass`.

That is worse than an omission. A stale acceptance reads as a considered
decision, so a reader auditing this server would have concluded it ships no
container and no structured logging. Both are removed from the list rather than
edited in place, with a note saying they were closed rather than dropped.

Same corrections applied to `SECURITY.de.md`.

### Added

- `tests/test_security_doc.py` — asserts SECURITY.md cites the newest audit run,
  quotes that run's counts, and never lists a check as an accepted risk while
  the latest audit has it passing. Mutation-tested by re-adding a closed check
  to the list.

## [0.8.0] — 2026-07-28

Closes ARCH-009, ARCH-008 and ARCH-012 from the 2026-07-28 re-audit. One
annotation, one constant, and documentation — no behaviour changes.

### ARCH-009 — `destructiveHint` set explicitly

`READ_TOOL` declared `readOnlyHint`, `idempotentHint` and `openWorldHint` but
omitted `destructiveHint`, leaving it to the client's default. The check asks
for explicit annotations, and a default by omission is not the same statement as
"these tools destroy nothing" — the companion `amtsblatt-mcp` has set it
explicitly all along.

One line, and it was carrying a `high` severity.

### ARCH-012 — MCP protocol version pinned

**Spec version `2025-11-25`** is now pinned as `MCP_PROTOCOL_VERSION` in
`server.py`, with a new *MCP Protocol Version* section in the README stating the
version, where it lives, and the update policy.

The SDK offers no way to configure this — negotiation happens in the session
layer, and neither `FastMCP.__init__` nor `Settings` takes the parameter. So the
pin is a declared constant plus detection: a mismatch logs
`protocol_version_drift` at `WARNING` at runtime, and
`tests/test_protocol_version.py` fails in CI.

That split is deliberate. An SDK bump should break *our* build, not the runtime
of someone who upgraded `mcp` downstream.

Future protocol-version bumps get their own CHANGELOG line rather than being
folded into a dependency-bump entry.

### ARCH-008 — tools-only rationale documented

The check accepts either two of the three primitives or a documented reason for
using one. The README now carries the reason.

Two tools were checked concretely for resource-migration potential and rejected
with specific reasons rather than by blanket policy: `source_status` is
resource-shaped but exists to be *called* when a result looks wrong, and a
resource the model must remember to re-read is worse at that job; the CPV
catalogue is enumerable but ~10k entries, and pushing it into the context window
defeats the point of a server-side lookup.

Resources and prompts will be revisited if this server ever gains a genuinely
enumerable, slow-changing dataset. simap is the opposite — every useful call is
a filtered query over a corpus that changes intraday.

### Added

- `tests/test_protocol_version.py` — 4 tests: the pin matches the installed SDK,
  it is a dated spec version rather than a moving target, and the README names
  both the version and an update policy

## [0.7.0] — 2026-07-27

Closes the two findings the 2026-07-27 re-audit left open. No tool, argument or
return shape changed.

### SEC-007 — container hardening

`useradd --system` picked a UID from the 100–999 range, which the check rejects.
That range is reserved for host system accounts, so under a bind mount the
container user can inherit a real host user's ownership — and the exact number
depends on package install order, so it moved between rebuilds. Now an explicit
`10001`, with a numeric `USER 10001:10001` and a matching `user:` in compose.

**seccomp:** Docker already applies its built-in profile — the equivalent of
Kubernetes' `RuntimeDefault` — and Compose has no syntax that names it. The
obvious-looking line is actively harmful:

```yaml
security_opt: [seccomp:unconfined]   # WRONG — this DISABLES seccomp
```

So the posture is stated in a comment and in `docs/container-hardening.md`
rather than "fixed" with a line that makes things worse.

CI asserts both rather than trusting the Dockerfile: uid ≥ 10000 (not merely
non-zero) and `Seccomp: 2` in `/proc/self/status`. The probe runs through
`python` rather than `grep -oP`, because PCRE support in the base image is an
assumption and the interpreter is not.

### OBS-003 — structured logging

Moved to [structlog](https://www.structlog.org/). The previous implementation
was stdlib `logging` with a hand-rolled JSON formatter: structured output, but
no logging library in `dependencies`, only two severity levels ever emitted, and
nothing correlating the events of one call.

This was flagged before starting as the one item where the obvious fix would be
cosmetic — adding a dependency for a checkbox, emitting `DEBUG` to reach a
count. What settled it was the third gap. `structlog.contextvars` binds context
to the async task, so an event emitted deep inside the HTTP client carries the
surrounding call's `correlation_id` without being threaded through every
signature. That is a capability, not a formality, and it is the one gap that
could not be closed by hand.

The four levels sit where they carry operational meaning:

| Level | Emitted when |
|---|---|
| `DEBUG` | tool entry — tells you whether a hung call was ever entered |
| `INFO` | tool finished cleanly, with latency |
| `WARNING` | upstream degraded |
| `ERROR` | the tool raised; exception **type** only, never the message |

`log_event` keeps its int-based signature, so no call site outside `_log.py`
changed.

#### What the tests had to work around

`structlog.testing.capture_logs` replaces the entire processor chain, which
silently drops `merge_contextvars`. Every correlation assertion would have
passed vacuously, and the context-leak test would have proven nothing at all —
the id it checks for absence of is *always* absent under `capture_logs`.

So `configure_logging` grew test-only keyword arguments and the chain is exposed
as `processor_chain()`, letting the tests drive the production pipeline into a
`StringIO` rather than a copy of it. The stdout test runs in a subprocess for
the same reason: in-process, pytest replaces the streams, so a logger holding
the wrong one would still look correct.

### Added

- `docs/container-hardening.md` — incl. the Kubernetes `securityContext`
  equivalent and how to verify seccomp on a running container
- `structlog>=24.1` dependency

## [0.6.0] — 2026-07-27

Closes the last two open `high` findings, SEC-018 and SEC-007. **Breaking: every
tool now takes a single argument object.**

### Breaking — tool arguments move into one validated object

Tools used to take flat keyword arguments. They now take one input model each:

```diff
- search_procurements(canton="ZH", query="Schulhaus", limit=20)
+ search_procurements({"canton": "ZH", "query": "Schulhaus", "limit": 20})
```

This is the shape SEC-018 requires and the shape the companion `amtsblatt-mcp`
already uses, so the two servers now read the same way. No tool was renamed, no
argument was renamed, removed or given a different meaning, and no return shape
changed — only the nesting.

### SEC-018 — validation moves from the tool body to the boundary

Bounds used to be enforced imperatively inside the tools by `_check_limit` and
`_check_text`, which meant the model could not see them: the tool schema
advertised a bare `integer` and the rejection only happened after the call.

`inputs.py` now declares them, so they appear in the tool list:

| | before | after |
|---|---|---|
| `limit` | `{"type": "integer"}` | `{"type": "integer", "minimum": 1, "maximum": 100}` |
| `query` | `{"type": "string"}` | `minLength` 2, `maxLength` 200, whitelist `pattern` |
| `canton` | `{"type": "string"}` | enum of the 26 ids |

Every model sets `strict=True` and `extra="forbid"`:

- **`strict=True`** — no coercion. `limit="10"` is now an error rather than
  silently becoming `10`, so type confusion is reported instead of hidden.
- **`extra="forbid"`** — an unknown field is rejected rather than dropped. A
  silently-ignored field looks accepted, which is prompt-injection surface.

The allow-lists (cantons, process types, publication types, code systems,
languages) are **derived from `constants.py`** rather than restated, so a probe
that updates those tables cannot leave a stale copy behind in the schema. A
parametrised test asserts the derivation still holds.

`_check_limit` and `_check_text` are gone; the schema does their work.

#### One deliberate tightening

Under `strict=True`, `language="DE"` is now rejected instead of being
lower-cased to `"de"`. Silent normalisation is exactly what strict mode exists
to prevent, so this is intended rather than incidental.

#### One thing the new tests caught

The first draft of the free-text whitelist used `\s` for whitespace. `\s`
matches CR and LF, so `query="a\r\nX-Injected: 1"` passed the filter — a
whitelist with a hole in it. The pattern now uses a literal space; a
procurement keyword never needs a line break. The test that found it is in
`tests/test_input_models.py` and is still there.

#### Where validation now happens

Schema violations are rejected *before* the tool body runs, so they no longer
produce a `tool_call` log record — there is no call to account for. Errors
raised inside a tool body still log with `status="error"` as before. Both
behaviours are pinned by tests.

### SEC-007 — hardened container

Ported from `amtsblatt-mcp`: multi-stage `Dockerfile`, non-root system user,
plus a `compose.yaml` with a read-only root filesystem, `cap_drop: [ALL]`,
`no-new-privileges`, and memory/CPU/PID limits. No runtime secret — the wrapped
endpoints are public.

Pinned to `python:3.12-slim` rather than the newest interpreter, because CI
tests 3.10–3.12; shipping an image on a version no test runs against would put
the container outside the evidence the rest of this repo relies on.

CI gained a `Docker build` job that does more than build: it asserts the image
does not run as uid 0, and that the server still imports under
`--read-only --cap-drop ALL`. A Dockerfile that builds but runs as root would
otherwise pass silently while failing the check it was written for.

### Added

- `src/swiss_procurement_mcp/inputs.py` — nine strict input models
- `tests/test_input_models.py` — 40 tests, one group per SEC-018 pass criterion,
  including the allow-list drift guard and the whitelist-pattern cases
- `Dockerfile`, `compose.yaml`, `.dockerignore`, and the `Docker build` CI job

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
