# MCP-Server Audit-Report — `swiss-procurement-mcp`

**Audit-Datum:** 2026-07-26
**Skill-Version:** 1.0.0
**Catalog-Version:** 2026-07

---

## 1. Executive Summary

Server `swiss-procurement-mcp` wurde gegen 32 anwendbare Best-Practice-Checks geprüft. 15 bestanden, 17 Findings dokumentiert (3 critical, 8 high, 6 medium, 0 low). Production-Readiness: erreicht.

**Production-Readiness:** YES

---

## 2. Profil-Snapshot

| Feld | Wert |
|---|---|
| Server-Name | `swiss-procurement-mcp` |
| Audit-Datum | 2026-07-26 |
| Skill-Version | 1.0.0 |
| Catalog-Version | 2026-07 |

---

## 3. Applicability

### Status pro Kategorie

| Kategorie | Pass | Fail | Partial | Todo | N/A |
|---|---|---|---|---|---|
| ARCH | 5 | 1 | 5 | 0 | 0 |
| CH | 0 | 0 | 1 | 0 | 0 |
| OBS | 2 | 0 | 2 | 0 | 0 |
| OPS | 1 | 0 | 2 | 0 | 0 |
| SCALE | 0 | 0 | 1 | 0 | 0 |
| SEC | 7 | 0 | 5 | 0 | 0 |
| **Total** | **15** | **1** | **16** | **0** | **0** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| ARCH-005 | ARCH | critical | partial |
| SEC-009 | SEC | critical | partial |
| SEC-019 | SEC | critical | partial |
| ARCH-009 | ARCH | high | partial |
| OBS-002 | OBS | high | partial |
| OPS-001 | OPS | high | partial |
| OPS-003 | OPS | high | partial |
| SCALE-002 | SCALE | high | partial |
| SEC-007 | SEC | high | partial |
| SEC-018 | SEC | high | partial |
| SEC-021 | SEC | high | partial |
| ARCH-003 | ARCH | medium | partial |
| ARCH-007 | ARCH | medium | partial |
| ARCH-008 | ARCH | medium | partial |
| ARCH-012 | ARCH | medium | fail |
| CH-004 | CH | medium | partial |
| OBS-003 | OBS | medium | partial |

**Gesamt:** 17 Findings

---

## 5. Detail-Findings

### ARCH-003

## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

search_procurements returns an actionable note on empty results, and find_procurement_office does client-side substring matching, but responses carry no match_type field and the code/award/history searches have no fuzzy-or-suggestion fallback on an empty result.

### Expected Behavior

Non-sensitive search tools should distinguish exact/fuzzy/none via a match_type field and offer a suggestion or term-refinement hint when nothing matches, so the model refines rather than dead-ends.

### Evidence

- `src/swiss_procurement_mcp/server.py:164-166 — search_procurements returns actionable note on empty results ('Widen the date range or check canton/CPV filters')`
- `src/swiss_procurement_mcp/server.py:398,417 — find_procurement_office does client-side substring (fuzzy-ish) matching`

### Gaps

- No match_type field (exact/fuzzy/none) on any response
- No fuzzy-match/suggestion fallback for empty CPV/construction-code or award searches (search_awards has no empty-result note)

### Risk Description

Low. On an empty result the model may report 'nothing found' without offering the user a way forward; it will not hallucinate here because the envelope is structured and honest.

### Remediation

Add a `match_type` field to the search envelopes and a short suggestion note (or nearest-code fuzzy fallback) on empty CPV/construction-code/award/history results, mirroring the existing search_procurements note.

### Effort Estimate

S


### ARCH-005

## Finding: ARCH-005 — Keine Hardcoded Secrets: Env-Vars / Secret Manager only

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `ARCH-005` |
| **PDF-Reference** | Sec 2.1 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

No secrets of any kind exist in the source (the API is fully public; only a public User-Agent and a hardcoded public base URL), and `.env` is git-ignored. What is missing is the defence-in-depth tooling: no CI secret-scanning on PRs and no `.env.example`.

### Expected Behavior

Even a no-secret repo should run an automated secret-scan (gitleaks/trufflehog) on every PR as a regression guard, so a future contributor cannot introduce a credential unnoticed.

### Evidence

- `src/swiss_procurement_mcp/constants.py — only a public User-Agent and hardcoded public base URL; no keys/tokens/passwords anywhere in src/`
- `.gitignore:6 — .env is ignored`
- `SECURITY.md:31 — documents there are no API keys/credentials (public endpoints)`

### Gaps

- No CI secret-scanning workflow (gitleaks/trufflehog) on PRs — .github/workflows/ has none
- No .env.example in repo (no secrets exist to template, but the control is absent)

### Risk Description

Low today (nothing to leak), but the guardrail that keeps it that way is absent — a later feature that adds an API key could commit it without CI catching it.

### Remediation

Add a gitleaks GitHub Action on push/PR. Optionally add a `.env.example` if any configuration env vars are introduced. No key rotation needed — there are no secrets in history.

### Effort Estimate

S


### ARCH-007

## Finding: ARCH-007 — Capability-Aggregation: Composability intern, Atomarität extern

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `ARCH-007` |
| **PDF-Reference** | Sec 2.3 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

search_awards aggregates all four award publication types into one call and documents it, but search_procurements returns summaries that require a follow-up get_procurement_details call, and there is no asyncio.gather parallelisation. The anchor demo needs three tool calls.

### Expected Behavior

Tools should return thought-complete results; where a workflow naturally spans several upstream calls, aggregate them internally (parallelised) so the model needs ≤2 calls for the anchor query.

### Evidence

- `src/swiss_procurement_mcp/server.py:197 — search_awards aggregates all four award pub-types into one upstream call`
- `src/swiss_procurement_mcp/server.py:191-192 — docstring states the aggregated character ('queries all four award publication types at once')`

### Gaps

- search_procurements returns summaries requiring a follow-up get_procurement_details call (IDs/pointers, not self-contained)
- No asyncio.gather parallelization anywhere; anchor demo needs 3 tool calls, above the <=2 target

### Risk Description

Low. More tool round-trips mean more latency and a slightly higher chance the model mis-chains, but each tool is individually correct and honest.

### Remediation

Consider an optional aggregated tool (e.g. search + auto-detail for the top N hits via asyncio.gather) for the anchor use-case, while keeping the granular tools for precise control.

### Effort Estimate

M


### ARCH-008

## Finding: ARCH-008 — Drei Primitive nutzen: Tools, Resources und Prompts

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | accepted-risk |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `ARCH-008` |
| **PDF-Reference** | Anhang A2 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

The server exposes only the Tools primitive (8 `@mcp.tool`). No MCP Resources or Prompts are registered, and the README does not state a justification for tools-only.

### Expected Behavior

The catalogue encourages using Resources (e.g. a publication or reference-code list as a cacheable URI) and/or Prompts where natural, or documenting why tools-only was chosen.

### Evidence

- `src/swiss_procurement_mcp/server.py — only Tools primitive used; no @mcp.resource or @mcp.prompt registrations`
- `README.md:89-102 — Tools table present`

### Gaps

- Only one of three primitives used and README does not document a justification for tools-only
- Idempotent read-only tools (e.g. reference-code searches) not assessed for Resources-migration potential

### Risk Description

None security-relevant. Purely a capability-completeness gap; discovery works today via the search tools.

### Remediation

Accepted risk — identical posture to the rest of the portfolio (tools-only for Phase-1 wrappers). Add a one-paragraph 'MCP primitives' note to the README, and revisit Resources once the portfolio standardises a URI scheme.

### Effort Estimate

M


### ARCH-009

## Finding: ARCH-009 — Tool Annotations: readOnlyHint, destructiveHint, idempotentHint, openWorldHint

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `ARCH-009` |
| **PDF-Reference** | Anhang A5 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

All 8 tools carry `annotations={'readOnlyHint': True}` and the README documents it, but `openWorldHint: true` is not set on any tool even though every tool reaches an external system (simap.ch), and `idempotentHint` is not set on the idempotent read tools.

### Expected Behavior

Tools that query an external, changing world should advertise `openWorldHint: true`; deterministic read tools may advertise `idempotentHint`. This lets clients reason about caching and retaction.

### Evidence

- `src/swiss_procurement_mcp/server.py:92,179,231,284,319,348,387,437 — all 8 tools carry explicit annotations={'readOnlyHint': True}, consistent with read-only behaviour`
- `README.md:102 — 'All tools are readOnlyHint: true' documented`

### Gaps

- openWorldHint: true is NOT set on any tool, yet all 8 reach an external system (simap.ch HTTP) — should be present
- idempotentHint not set on the idempotent read tools

### Risk Description

Low. Clients get a slightly less accurate picture of tool semantics (e.g. that results may change between calls), but behaviour is unaffected.

### Remediation

Add `openWorldHint: True` to every tool's annotations dict (all reach live simap.ch). Optionally add `idempotentHint: True` to the pure reference-code lookups. One-line change per tool.

### Effort Estimate

S


### ARCH-012

## Finding: ARCH-012 — protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `ARCH-012` |
| **PDF-Reference** | Anhang A9 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | fail |

### Observed Behavior

A Keep-a-Changelog CHANGELOG with a versioned 0.1.0 entry is present, but the MCP `protocolVersion` is not pinned anywhere (the SDK default negotiation is relied upon), the README has no 'MCP Protocol Version' / SDK-update-policy section, and there is no Dependabot/Renovate config for SDK update PRs.

### Expected Behavior

The catalogue asks for an explicit protocol-version and SDK-update discipline: pin/record the supported MCP protocol version, document an update policy, and automate dependency-update PRs so a breaking SDK bump is caught deliberately.

### Evidence

- `CHANGELOG.md:1-4 — present, explicitly Keep-a-Changelog format`
- `CHANGELOG.md:6 — versioned 0.1.0 entry with Added/Security/Scope sections`

### Gaps

- protocolVersion is not pinned anywhere in server code (relies on SDK default negotiation)
- No 'MCP Protocol Version' section and no SDK update policy in README
- No Dependabot/Renovate config for SDK update PRs (.github/dependabot.yml / renovate.json absent)

### Risk Description

Low-to-medium over time. Without a pinned protocol version and dependency automation, a future `mcp` SDK release could silently change negotiated behaviour or break the server, with no PR surfacing it.

### Remediation

Add a `.github/dependabot.yml` (pip ecosystem) so SDK bumps arrive as reviewable PRs; add a short 'MCP protocol version & SDK updates' note to the README stating the tested `mcp` version range; optionally assert the negotiated protocol version at startup.

### Effort Estimate

S


### CH-004

## Finding: CH-004 — OGD-CH Lizenz-Compliance: CC BY 4.0 Attribution

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `CH-004` |
| **PDF-Reference** | Custom (OGD-CH-Richtlinien) |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

The ATTRIBUTION constant names the source (simap.ch), operator (simap.ch association) and API version, every response carries source/provenance/retrieved_at, and the README Credits section links the data source — but no explicit data licence is named.

### Expected Behavior

OGD-CH attribution should name source, author/operator, licence and (where applicable) modification, so downstream consumers know the reuse terms.

### Evidence

- `src/swiss_procurement_mcp/constants.py:21-25 — ATTRIBUTION names source (simap.ch), operator (simap.ch association) and API version`
- `src/swiss_procurement_mcp/models.py:12-16 — every response Envelope carries source + provenance + retrieved_at (per-response provenance)`
- `README.md:209-214 — Credits section documents the simap.ch data source and API docs link`

### Gaps

- Attribution text does not name an explicit data license (e.g. CC BY 4.0 with author/source/license/modification); only source+operator+version are cited

### Risk Description

Low. Attribution is substantially present; only the explicit licence label is missing, which could matter for strict OGD reuse-compliance.

### Remediation

Add the applicable licence to the ATTRIBUTION text and README Credits (confirm simap.ch's terms; if it is opendata.swiss-style, cite the licence and 'source: simap.ch'). Text-only change.

### Effort Estimate

S


### OBS-002

## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 6.2 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

Upstream 4xx bodies are truncated to 300 chars, no tracebacks/exc_info are surfaced, and the degraded note is a user-friendly message — but FastMCP is not initialised with `mask_error_details=True`, and the degraded note embeds `str(exc)` which can include the truncated upstream body.

### Expected Behavior

The server should mask internal error detail from the model by default (`mask_error_details=True`) and avoid embedding raw upstream response text in tool output.

### Evidence

- `src/swiss_procurement_mcp/client.py:99-100 — upstream 4xx body truncated to 300 chars; no traceback/exc_info surfaced`
- `src/swiss_procurement_mcp/server.py:46-52 — degraded note is a user-friendly message, no stack traces`
- `SECURITY.md:32 — documents that no stack traces are surfaced to the model`

### Gaps

- FastMCP is initialised without mask_error_details=True (src/swiss_procurement_mcp/server.py:43)
- Degraded note embeds str(exc) which can include the truncated upstream response body (public-API text, low sensitivity, but not fully masked)

### Risk Description

Low. The embedded text is public-API error body (low sensitivity), but an unexpected exception could still surface implementation detail to the model.

### Remediation

Initialise `FastMCP(..., mask_error_details=True)` and drop the raw `str(exc)`/upstream-body substring from the degraded note in favour of a fixed message plus a coarse reason code.

### Effort Estimate

S


### OBS-003

## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | accepted-risk |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 6.3 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

The server does no logging at all — there is no structured-logging library, no JSON/logfmt output, and no RFC 5424 severities or per-call correlation context. (This is why stdout stays clean; see OBS-004 pass.)

### Expected Behavior

For SIEM ingestion the catalogue wants JSON-structured logs with RFC 5424 severities and a trace/correlation id per tool call.

### Evidence

- `src/swiss_procurement_mcp/ — no print() statements (clean stdout for stdio)`
- `SECURITY.md:50-54 — structured logging explicitly documented as accepted risk for a stdio public-data server`

### Gaps

- No structured logging library (structlog/loguru) in dependencies; no JSON/logfmt output
- No RFC 5424 severity levels or per-tool-call bound context (session_id/correlation_id) — the server does no logging at all

### Risk Description

None for a stdio server consumed by a local client. Structured logging only matters under a centralised log pipeline.

### Remediation

Accepted risk — already documented in SECURITY.md. Introduce structured JSON logging to stderr (structlog) with a per-call correlation id if the server is lifted to a cloud/SSE deployment behind a SIEM.

### Effort Estimate

S


### OPS-001

## Finding: OPS-001 — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `OPS-001` |
| **PDF-Reference** | Anhang C1 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

Test infrastructure is strong: respx-mocked unit tests, a registered `live` marker, CI running `pytest -m 'not live'` on 3.10–3.12 plus a separate nightly live job. But unit depth is below the '≥5 per tool' guidance (~7 unit + 4 resilience tests for 8 tools), and live tests cover only 5 of the 8 tools.

### Expected Behavior

Each tool should have several unit tests covering happy path plus edge/error cases, and the live suite should exercise every tool at least once.

### Evidence

- `tests/test_tools.py + tests/test_resilience.py — respx-mocked unit tests present`
- `tests/test_live.py:13 — pytestmark = pytest.mark.live; live tests gated`
- `pyproject.toml:42 — 'live' marker registered; ci.yml:43 runs pytest -m 'not live'; ci.yml:64-82 separate nightly/dispatch live job`

### Gaps

- Unit-test depth below spec: ~7 unit + 4 resilience tests total, not >=5 per tool for 8 tools
- Live tests cover 5 of 8 tools (missing get_publication_history, search_construction_codes, find_procurement_office)

### Risk Description

Low. Core paths and the resilience/degrade path are tested; the untested tools (get_publication_history, search_construction_codes, find_procurement_office) could regress without a failing test.

### Remediation

Add unit tests for the three uncovered tools and a few more edge cases per tool (empty results, cache hit, code-object normalisation), and add a live test per remaining tool.

### Effort Estimate

M


### OPS-003

## Finding: OPS-003 — Phasenarchitektur: Read-only First, dann Write, dann Multi-Agent

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `OPS-003` |
| **PDF-Reference** | Anhang C4 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

The read-only-first posture is explicit (Architecture A, write endpoints out of scope) and consistent with the readOnlyHint annotations, and SECURITY.md documents the re-evaluation triggers for gaining write/PII/cloud capability — but there is no explicit 'Phase 1/2/3' declaration and no roadmap file.

### Expected Behavior

The catalogue asks for an explicit phase declaration (read-only first, then write, then multi-agent) so consumers know the maturity stage and what is intentionally deferred.

### Evidence

- `README.md:44-56 — read-only-first posture explicit (Architecture A, write endpoints out of scope), consistent with readOnlyHint annotations`
- `SECURITY.md:63-73 — Re-evaluation triggers document prerequisites for gaining write/PII/cloud capability (phase-transition conditions)`

### Gaps

- No explicit 'Phase 1/2/3' declaration in README
- No roadmap file with phase-specific tasks

### Risk Description

None. This is a documentation-completeness gap; the actual posture is already correct and stated.

### Remediation

Add a one-line 'Phase 1 (read-only)' statement to the README and, optionally, a short roadmap section referencing the SECURITY.md re-evaluation triggers as the phase-transition conditions.

### Effort Estimate

S


### SCALE-002

## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP / SSE

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | accepted-risk |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `SCALE-002` |
| **PDF-Reference** | Sec 5.2 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

The cache is a per-SimapClient instance created per tool call, so there is no shared cross-request server state to balance. There is no sticky-session or shared-state session manager, and no explicit session TTL/failover test for the SSE transport.

### Expected Behavior

A horizontally-scaled SSE/streamable-http deployment needs sticky sessions or externalised shared state (Redis/Durable Objects) with an explicit TTL.

### Evidence

- `src/swiss_procurement_mcp/client.py:62-66 — cache is per-SimapClient instance created per tool call (no shared cross-request server state to balance)`
- `SECURITY.md:63-72 — cloud/SSE scaling explicitly deferred as a re-evaluation trigger; server is stdio-primary and not cloud-deployed`

### Gaps

- No sticky-session or shared-state (Redis/Durable Objects) session manager for the SSE/streamable-http transport
- No explicit session TTL and no failover test — acceptable only while single-instance/stdio-primary

### Risk Description

None while the server is stdio-primary / single-instance, which is the documented deployment. The controls only become relevant behind a multi-instance load balancer.

### Remediation

Accepted risk — already deferred in SECURITY.md as a re-evaluation trigger. Introduce an external session store and sticky routing only if the server is scaled to multiple SSE instances.

### Effort Estimate

M


### SEC-007

## Finding: SEC-007 — Container-Sandboxing: Docker / chroot mit minimalen Privilegien

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | accepted-risk |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `SEC-007` |
| **PDF-Reference** | Sec 4.5 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

No Dockerfile or Kubernetes hardening (non-root USER, securityContext, readOnlyRootFilesystem, capability drop, seccomp) is shipped; the server runs as a local stdio process.

### Expected Behavior

For container deployments the catalogue wants a hardened image (minimal base, non-root, read-only FS, dropped capabilities).

### Evidence

- `SECURITY.md:42-48 — container sandboxing explicitly documented as accepted risk for a local-stdio public-data server`
- `Repo — no Dockerfile shipped (deployment is local-stdio; defense-in-depth deferred to OS user level)`

### Gaps

- No Dockerfile with non-root USER / no Kubernetes securityContext (runAsNonRoot, readOnlyRootFilesystem, capabilities.drop, seccomp) — none exist to satisfy the container hardening criteria

### Risk Description

Acceptable for a local-stdio public-data server — no write path, no secrets, no privileged operations; defense-in-depth lives at the OS user level.

### Remediation

Accepted risk — already documented in SECURITY.md. Ship a hardened, non-root container image if the deployment profile ever moves to a persistent cloud service.

### Effort Estimate

M


### SEC-009

## Finding: SEC-009 — Session-ID Cryptographic Binding (user_id:session_id)

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | accepted-risk |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `SEC-009` |
| **PDF-Reference** | Sec 4.6 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

There is no auth model and no per-user data; the server exposes only public read data, and each tool call uses an ephemeral client with no per-user server-side session state. There is therefore no application-level cryptographic user_id:session_id binding and no explicitly-set session TTL.

### Expected Behavior

Where an OAuth identity exists, sessions should be cryptographically bound to the user and given an explicit TTL/invalidation to prevent hijacking.

### Evidence

- `src/swiss_procurement_mcp/ — no auth model; server exposes only public read data, so there is no OAuth user identity to bind a session to`
- `src/swiss_procurement_mcp/client.py:63-66 — per-call ephemeral client, no per-user server-side session state to hijack`

### Gaps

- No application-level cryptographic user_id:session_id binding (no OAuth sub-claim exists); relies on FastMCP default session handling
- No explicitly-set session TTL / server-side invalidation — low real impact because there is no per-user data, but the specific controls are absent for the SSE transport

### Risk Description

Largely inapplicable to this profile: no OAuth sub-claim exists, and there is no per-user or sensitive data behind a session to hijack. Relies on FastMCP default session handling.

### Remediation

Accepted risk for a no-auth public-read server. Implement user:session binding and explicit TTLs if an authentication model and per-user data are ever added (a documented re-evaluation trigger).

### Effort Estimate

M


### SEC-018

## Finding: SEC-018 — Input-Validation an Tool-Boundaries (Pydantic strict / Zod)

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `SEC-018` |
| **PDF-Reference** | Sec 3 / Sec 4 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

Enum-like inputs (canton, process_type, pub_type, system, language) are validated against fixed allow-lists and rejected with actionable errors, and edge-case tests exist — but numeric `limit` params are unbounded (no ge/le), free-text params have no min/max length or pattern, and Pydantic `strict=True` / `extra='forbid'` are not set.

### Expected Behavior

Every tool boundary should bound its inputs: numeric ranges (ge/le), string length/pattern limits, and strict typing, so malformed or abusive inputs fail fast.

### Evidence

- `src/swiss_procurement_mcp/server.py:125-130,194,362-365 — canton/process_type/pub_type/system validated against fixed allow-lists (whitelist), rejected with actionable ValueError`
- `src/swiss_procurement_mcp/client.py:38-46 — language validated against SUPPORTED_LANGUAGES allow-list`
- `tests/test_tools.py:32-42 — edge-case tests for rejected ISO canton code and invalid pub_type`

### Gaps

- Numeric limit params (search_cpv_codes, search_construction_codes, find_procurement_office) have no ge/le bounds — unbounded
- Free-text string params (query, name_contains) have no min_length/max_length/pattern; Pydantic strict=True and extra='forbid' are not set; no tests for over-long strings / out-of-range numbers

### Risk Description

Low. Upstream simap.ch bounds the actual query, but an unbounded `limit` or a very long free-text string is passed through without a local guard and is untested.

### Remediation

Add `ge=1, le=100` (or similar) to the `limit` params and `max_length` to `query`/`name_contains`; add a couple of tests for over-long strings and out-of-range numbers. Consider Pydantic input models with `extra='forbid'`.

### Effort Estimate

S


### SEC-019

## Finding: SEC-019 — Lethal Trifecta vermeiden: Server-Separation Read vs Write/Send

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `SEC-019` |
| **PDF-Reference** | Anhang B1 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

The server is structurally safe against the lethal trifecta: it reads only PUBLIC data (no private-data leg), egress is fixed to a single hardcoded host with no arbitrary-send capability (no exfiltration leg), and all tools are read-only — at most two trifecta legs are ever present. What is missing is a written assessment.

### Expected Behavior

The catalogue asks for an explicit, documented lethal-trifecta assessment (which legs are present/absent and why) so the safety argument is auditable, not implicit.

### Evidence

- `src/swiss_procurement_mcp/ — reads only PUBLIC procurement data (no private/sensitive data), so the 'private data access' leg of the trifecta is absent`
- `src/swiss_procurement_mcp/constants.py:12 — egress fixed to a single hardcoded host; no send/write-to-arbitrary-destination capability (the exfiltration leg is absent)`
- `server.py — all tools readOnlyHint; at most two trifecta legs present (external fetch + ingesting external content)`

### Gaps

- No explicit lethal-trifecta assessment/ADR documented in README or docs/ (server is structurally safe but the required written evaluation is missing)

### Risk Description

None in practice — the exfiltration leg is genuinely absent. The gap is documentation: the safety property is real but unwritten.

### Remediation

Add a short 'Lethal-trifecta assessment' note to SECURITY.md or docs/ stating that only the external-fetch leg is present, the private-data and arbitrary-send legs are absent, and what would change that.

### Effort Estimate

S


### SEC-021

## Finding: SEC-021 — Egress-Allow-List: Code-Layer und Network-Layer

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `SEC-021` |
| **PDF-Reference** | Anhang B5 + B12 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

Egress is hardcoded to a single HTTPS host (SIMAP_BASE) that no user input can redirect — effectively a one-host allow-list, tighter than a general allow-list — and the posture is documented in SECURITY.md. What is missing is an explicit code-layer guard and a network-layer control.

### Expected Behavior

The catalogue wants an explicit egress allow-list enforced at the code layer (a checked frozenset / assert_host_allowed) and, where deployed, a network-layer egress policy, plus a documented update procedure.

### Evidence

- `src/swiss_procurement_mcp/constants.py:12 — egress is hardcoded to a single HTTPS host (SIMAP_BASE); no user input can redirect the host, effectively a one-host allow-list`
- `SECURITY.md:26-29 — egress posture documented (single hard-coded HTTPS base URL, caller never supplies a host)`

### Gaps

- No explicit frozenset allow-list + assert_host_allowed pre-request guard (relies on hardcoding instead)
- No network-layer egress control (NetworkPolicy/SG) and no docs/network-egress.md with an update procedure

### Risk Description

Low. Because the host is hardcoded and not user-influenced, the practical SSRF/exfiltration surface is already closed; the gap is an explicit, testable guard rather than an implicit one.

### Remediation

Add a small `assert_host_allowed` check (frozenset of allowed hosts) before each request as an explicit, testable invariant, and a `docs/network-egress.md` noting the single allowed host and how to change it. Add a NetworkPolicy only for a future cloud deployment.

### Effort Estimate

S


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **ARCH-005** (critical, partial)
2. **SEC-009** (critical, partial)
3. **SEC-019** (critical, partial)
4. **ARCH-009** (high, partial)
5. **OBS-002** (high, partial)
6. **OPS-001** (high, partial)
7. **OPS-003** (high, partial)
8. **SCALE-002** (high, partial)
9. **SEC-007** (high, partial)
10. **SEC-018** (high, partial)
11. **SEC-021** (high, partial)
12. **ARCH-003** (medium, partial)
13. **ARCH-007** (medium, partial)
14. **ARCH-008** (medium, partial)
15. **ARCH-012** (medium, fail)
16. **CH-004** (medium, partial)
17. **OBS-003** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|
| skill_version | `1.0.0` |
| catalog_version | `2026-07` |
| applies_when_dsl_version | `1.0` |
| policy | `fail-or-partial` |
| audit_date | `2026-07-26` |


_Generated by tools/build_report.py — do not edit by hand._
