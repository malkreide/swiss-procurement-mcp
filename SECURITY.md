# Security Policy & Posture

[🇩🇪 Deutsche Version](SECURITY.de.md)

`swiss-procurement-mcp` is a read-only, no-PII, public-open-data MCP server. It
wraps only the unauthenticated read endpoints of the simap.ch API. This document
states the current security posture and the **accepted-risk** decisions for
controls deliberately deferred for this server profile.

> A formal audit against the internal MCP best-practice catalogue (the portfolio
> `mcp-audit` methodology) has not yet been recorded for this server. Once run,
> the report will live under `audits/` and this document will reference it.

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
