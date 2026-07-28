# Security Policy & Posture

[🇩🇪 Deutsche Version](SECURITY.de.md)

`swiss-procurement-mcp` is a read-only, no-PII, public-open-data MCP server. It
wraps only the unauthenticated read endpoints of the simap.ch API. This document
states the current security posture and the **accepted-risk** decisions for
controls deliberately deferred for this server profile.

It was audited against the internal MCP best-practice catalogue (the portfolio
`mcp-audit` methodology, 68 checks / 8 categories). The latest measured run
(`audits/2026-07-28T062517-Z-swiss-procurement-mcp/`) scored **17 pass / 15
partial / 4 fail** across **36** applicable checks — **not production-ready**:
four `high`/`critical` checks fail. See `audits/` for the full report and
per-finding docs.

**The applicable set changed in this run, so the numbers are not comparable to
earlier ones.** Every previous run carried `sdk_language: python` in the audit
profile while the catalogue matches on `"Python"`. The comparison is an exact
string match, so `SDK-001` … `SDK-004` were silently filtered out of all four
earlier audits — they were never evaluated, and their absence read as a smaller
applicable set rather than as a gap. With the casing corrected the applicable
set is 36, not 32, and two of the four newly-evaluated checks fail.

Earlier runs, for the record and against the narrower 32-check set:
15/16/1 → 20/11/1 → 21/11/0 → 23/9/0.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository, or contact the
maintainer listed in `README.md`. Do not file public issues for exploitable
vulnerabilities.

## Posture summary

All tools only **query** the simap.ch procurement platform — there is no write
path, no user authentication, and no personal data. Hardening in place:

| Area | Control |
|---|---|
| Egress | Every request targets a single hard-coded HTTPS base URL (`https://www.simap.ch/api`, `SIMAP_BASE`); the caller never supplies a host, and each request is asserted against an `ALLOWED_HOSTS` allow-list before it is sent (SEC-021, see `docs/network-egress.md`) |
| TLS | Certificate verification on by default (httpx default; never disabled) |
| Transport | stdio by default — stdout reserved for the JSON-RPC stream; HTTP transports (`MCP_TRANSPORT=sse\|streamable-http`) bind to loopback (`127.0.0.1`) unless `MCP_HOST`/`HOST=0.0.0.0` is set explicitly (SEC-016) |
| Input | Pydantic v2 validation on every tool input; canton ids, process types and publication types are checked against fixed allow-lists and rejected with an actionable error (e.g. `ZH` vs. `CH-ZH`) |
| Secrets | No API keys or credentials — the wrapped simap endpoints are fully public. The required session cookie is obtained transparently by the HTTP client and is not a secret |
| Errors | Upstream 4xx bodies are truncated to 300 chars; network failures return a generic `degraded` envelope. No stack traces are surfaced to the model |
| Stdout | Reserved for the JSON-RPC stream; the server writes no logs to stdout |
| Scope | The ~200 write / `my/` / OIDC-protected simap endpoints (publishing, submissions) are deliberately not wrapped |
| Tests | respx-mocked unit suite on every PR (3.10/3.11/3.12); live API tests gated to a nightly job |

## Audit findings

The history below records what each release closed. The current open set is 19
findings — 15 `partial` and 4 `fail` — documented under
`audits/2026-07-28T062517-Z-swiss-procurement-mcp/findings/` (`fail-or-partial`
policy).

Four of them block production: `SDK-001` and `SDK-004` (newly evaluated, see the
profile correction above), plus `SEC-009` and `SCALE-002`, which are accepted
risks below but are still recorded as `fail` because the control is genuinely
absent — an accepted risk is a decision, not a passing check.

**`SDK-001` was the substantive one — closed in 0.10.0, not yet re-measured.**
At the time of the run every tool opened its own `httpx.AsyncClient` via
`async with SimapClient()`, and the server passed no `lifespan` to `FastMCP`.
That was a TCP and TLS handshake per tool call, and it made `SimapClient._cache`
dead code: the cache is per-instance, so it was discarded the moment the tool
returned, and the 30-minute TTL was never once reached. 0.10.0 pools one shared
client behind a lifespan, matching the sister server (`amtsblatt-mcp`), which
passes this check.

**`SDK-004` closed in 0.11.0, also not yet re-measured.** The HTTP transports
carried no CORS layer, so `Mcp-Session-Id` was neither exposed nor accepted and
a browser-based MCP client lost its session immediately after initialize.
`_cors.py` now names the header in both directions. Origins are fail-closed:
`MCP_CORS_ORIGINS` is unset by default, so no cross-origin browser access is
permitted until an operator lists origins explicitly.

The counts above are the measured run and are left as measured. Expected after
0.11.0 is 19 pass / 15 partial / 2 fail, the two remaining being the accepted
risks `SEC-009` and `SCALE-002` — **derived, not measured**; only a re-audit
makes it a number.

**Resolved in 0.2.0:**

- **ARCH-012** (was fail, medium) — added `.github/dependabot.yml` (pip +
  actions) and a "Maturity & updates" README section stating the MCP-protocol /
  SDK-update policy.
- **ARCH-009** (high) — every tool now sets `readOnlyHint`, `idempotentHint` and
  `openWorldHint` (shared `READ_TOOL` annotation).
- **SEC-018** (high) — `limit` params are bounded (1–100) and free-text params are
  length-capped (`_check_limit` / `_check_text`), with tests.
- **SEC-021** (high) — explicit `_assert_host_allowed` guard against an
  `ALLOWED_HOSTS` frozenset before every request, plus `docs/network-egress.md`.
- **SEC-019** (critical, structurally safe) — lethal-trifecta assessment written
  down (see below).
- **ARCH-005** (critical, no secrets exist) — added a gitleaks CI workflow
  (`.github/workflows/security.yml`).
- **ARCH-003** (medium) — search/code/office responses now carry `match_type`
  (`exact` / `none`).
- **OPS-003** (high) — explicit "Phase 1 — read-only" declaration in the README.

**Partially addressed in 0.2.0:**

- **OBS-002** (high) — the degraded note is now a fixed, sanitised string (no raw
  exception / upstream body). `mask_error_details=True` is **not** set because the
  pinned `mcp` SDK does not expose that setting.
- **OPS-001** (high) — added tests for the three previously-uncovered tools and
  the new input bounds; per-tool unit depth is still below the strict ≥5 target.

**Resolved in 0.3.0:**

- **ARCH-007** (medium) — added the aggregated `search_procurements_detailed` tool,
  which runs the search and fetches the top-*n* detail records in parallel
  (`asyncio.gather`), so the anchor query is answered in one call.
- **CH-004** (medium) — attribution now names the source, operator and terms and
  states the reuse basis. simap.ch publishes **no explicit open-data licence**, so
  none is asserted; the tenders are official public-procurement announcements and
  reuse follows the simap.ch terms (documented in `ATTRIBUTION`, README Credits and
  every response's `source` field).

**Accepted risk (deferred by profile):** SCALE-002 (stateful LB) and SEC-009
(session binding) — see [Accepted risks](#accepted-risks) for the reasoning and
the condition that would end each acceptance.

ARCH-008 (tools-only), OBS-003 (structured logging) and SEC-007 (container
sandboxing) were on this list and are **no longer accepted risks** — all three
were closed, in v0.8.0, v0.7.0 and v0.6.0 respectively.

## Lethal-trifecta assessment (SEC-019)

The "lethal trifecta" is the dangerous combination of (1) access to private data,
(2) exposure to untrusted content, and (3) the ability to exfiltrate. This server
has **at most one** of the three legs:

| Leg | Present? | Why |
|---|---|---|
| Access to private/sensitive data | **No** | Only public simap.ch procurement publications are read; no auth, no PII, no per-user data |
| Exposure to untrusted content | Partial | Tool results contain upstream text, which the model ingests — but it is public procurement data, not attacker-chosen private content |
| Ability to exfiltrate / act | **No** | Egress is pinned to one allow-listed host (`www.simap.ch`); there is no send/write/arbitrary-request capability, and all tools are read-only |

With the private-data and exfiltration legs both absent, the trifecta cannot
close. This would need re-evaluation if the server ever gained write capability,
processed private data, or allowed egress to arbitrary hosts.

## Accepted risks

The following controls are deliberately **out of scope** for a read-only
public-open-data server. None has a security impact for this profile.

> Two entries previously listed here — container sandboxing and structured
> logging — have been **closed** rather than accepted, in v0.6.0 and v0.7.0
> respectively. The server now ships a hardened non-root image (SEC-007) and
> structlog-based JSON logging with correlation ids (OBS-003). They are removed
> from this list rather than left standing, because a stale acceptance reads as
> a decision when it is really an out-of-date document.

### Session-to-user binding (SEC-009)

**Status:** accepted risk. Severity in the catalogue: `critical`.

There is no cryptographic binding of a session id to a user, because there is
neither. The server has no authentication, no per-user state and no private
data: every byte it returns comes from a public simap.ch endpoint that anyone
can query unauthenticated. A session id would bind an anonymous caller to
public data.

The `critical` severity is about what the control protects elsewhere, not about
exposure here. It is recorded rather than dismissed so the reasoning is
checkable.

**This becomes real if** the server gains authentication, any per-user state, or
any endpoint whose response depends on who is asking. At that point session
binding is required before the feature ships, not after.

### Stateful load balancing (SCALE-002)

**Status:** accepted risk. Severity in the catalogue: `high`.

There is no sticky-session or shared-state session manager. The server is
single-instance by design and the documented deployment profile is local stdio.
The HTTP transports exist and work, but run stateless — a second instance would
not break sessions, because there are none to break.

**This becomes real if** the server is deployed multi-instance behind a load
balancer *and* gains session state. Either alone is survivable; the combination
is not.

### Rate limiting / quota

**Status:** accepted risk.
simap.ch is a public service without per-key quota; the server relies on
retry-with-backoff (2s / 4s / 8s, 4xx except 429 not retried) and a short-lived
cache rather than client-side rate limiting.

## Re-evaluation triggers

These acceptances should be revisited if the server ever:

- gains **write** capability or starts processing **PII**, or
- registers tools **dynamically** / from remote sources, or
- is moved to a **cloud / SSE** deployment (then structured logging, container
  sandboxing and the network-binding checks become relevant), or
- is aggregated behind a shared MCP gateway (then implement gateway-level tool
  allow-listing and poisoning detection there).
