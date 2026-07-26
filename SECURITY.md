# Security Policy & Posture

[🇩🇪 Deutsche Version](SECURITY.de.md)

`swiss-procurement-mcp` is a read-only, no-PII, public-open-data MCP server. It
wraps only the unauthenticated read endpoints of the simap.ch API. This document
states the current security posture and the **accepted-risk** decisions for
controls deliberately deferred for this server profile.

It was audited against the internal MCP best-practice catalogue (the portfolio
`mcp-audit` methodology, 68 checks / 8 categories). The latest run
(`audits/2026-07-26T131630-Z-swiss-procurement-mcp/`) scored **15 pass / 16
partial / 1 fail** across the 32 applicable checks — **production-ready, no
security-impacting finding open** (the single fail, ARCH-012, is a `medium`
documentation/tooling gap; all `critical` and `high` findings are `partial`, i.e.
substantially met with a documented remainder). See `audits/` for the full report
and per-finding docs.

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

## Audit findings (2026-07-26)

17 findings were documented (`fail-or-partial` policy). None blocked production.
Full per-finding docs are under
`audits/2026-07-26T131630-Z-swiss-procurement-mcp/findings/`.

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

**Accepted risk (deferred by profile):** ARCH-008 (tools-only), OBS-003
(structured logging), SCALE-002 (stateful LB), SEC-007 (container sandboxing),
SEC-009 (session binding) — see below.

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

### Container sandboxing

**Status:** accepted risk.
No `Dockerfile` is shipped. Acceptable for a local-stdio public-data server —
defense-in-depth lives at the OS user level. Ship a hardened image if the
deployment profile ever moves to a persistent cloud service.

### Structured logging

**Status:** accepted risk.
The server relies on the host's default logging. JSON-structured logs with trace
IDs are not justified for a stdio server; revisit if the server is lifted to a
cloud/SSE deployment.

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
