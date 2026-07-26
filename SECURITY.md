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
| Egress | Every request targets a single hard-coded HTTPS base URL (`https://www.simap.ch/api`, `SIMAP_BASE`); the caller never supplies a host |
| TLS | Certificate verification on by default (httpx default; never disabled) |
| Transport | stdio by default — stdout reserved for the JSON-RPC stream; HTTP transports (`MCP_TRANSPORT=sse\|streamable-http`) bind to loopback (`127.0.0.1`) unless `MCP_HOST`/`HOST=0.0.0.0` is set explicitly (SEC-016) |
| Input | Pydantic v2 validation on every tool input; canton ids, process types and publication types are checked against fixed allow-lists and rejected with an actionable error (e.g. `ZH` vs. `CH-ZH`) |
| Secrets | No API keys or credentials — the wrapped simap endpoints are fully public. The required session cookie is obtained transparently by the HTTP client and is not a secret |
| Errors | Upstream 4xx bodies are truncated to 300 chars; network failures return a generic `degraded` envelope. No stack traces are surfaced to the model |
| Stdout | Reserved for the JSON-RPC stream; the server writes no logs to stdout |
| Scope | The ~200 write / `my/` / OIDC-protected simap endpoints (publishing, submissions) are deliberately not wrapped |
| Tests | respx-mocked unit suite on every PR (3.10/3.11/3.12); live API tests gated to a nightly job |

## Audit findings (2026-07-26)

17 findings were documented (`fail-or-partial` policy). None blocks production.
They fall into two groups; full per-finding docs are under
`audits/2026-07-26T131630-Z-swiss-procurement-mcp/findings/`.

**Planned hardening (low impact, actionable):**

- **ARCH-012** (fail, medium) — pin/record the MCP protocol version, add an
  SDK-update policy note and a Dependabot config.
- **ARCH-009** (high) — add `openWorldHint: true` to every tool (all reach live
  simap.ch).
- **OBS-002** (high) — initialise FastMCP with `mask_error_details=True` and drop
  the raw upstream body from the degraded note.
- **SEC-018** (high) — bound numeric `limit` params and free-text length.
- **SEC-021** (high) — add an explicit `assert_host_allowed` guard + a
  `docs/network-egress.md` (egress is already hardcoded to one host).
- **SEC-019** (critical, structurally safe) — write down the lethal-trifecta
  assessment (only the external-fetch leg is present).
- **ARCH-005** (critical, no secrets exist) — add CI secret-scanning as a
  regression guard.
- Plus **ARCH-003 / ARCH-007 / CH-004 / OPS-001 / OPS-003** — documentation,
  test-depth and attribution polish.

**Accepted risk (deferred by profile):** ARCH-008 (tools-only), OBS-003
(structured logging), SCALE-002 (stateful LB), SEC-007 (container sandboxing),
SEC-009 (session binding) — see below.

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
