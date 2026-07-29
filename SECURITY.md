# Security Policy & Posture

[🇩🇪 Deutsche Version](SECURITY.de.md)

`swiss-procurement-mcp` is a read-only, no-PII, public-open-data MCP server. It
wraps only the unauthenticated read endpoints of the simap.ch API. This document
states the current security posture and the **accepted-risk** decisions for
controls deliberately deferred for this server profile.

It was audited against the internal MCP best-practice catalogue (the portfolio
`mcp-audit` methodology, 68 checks / 8 categories). The latest measured run
(`audits/2026-07-28T094256-Z-swiss-procurement-mcp/`) scored **19 pass / 15
partial / 2 fail** across **36** applicable checks. See `audits/` for the full
report and per-finding docs.

**Not production-ready, and the two remaining fails are the reason — by
decision, not by oversight.** `SEC-009` (session-to-user binding) and
`SCALE-002` (stateful load balancing) are the accepted risks documented below.
They stay recorded as `fail` because the controls are genuinely absent; an
accepted risk is a decision, not a passing check. Every finding that was not a
deliberate acceptance is now closed or `partial`.

**The applicable set changed on 2026-07-28, so nothing before that date is
comparable.** Every earlier run carried `sdk_language: python` in the audit
profile while the catalogue matches on `"Python"`. The comparison is an exact
string match, so `SDK-001` … `SDK-004` were silently filtered out of all four
earlier audits — never evaluated, their absence reading as a smaller applicable
set rather than as a gap. With the casing corrected the applicable set is 36,
not 32, and two of the four newly-evaluated checks failed. Both are now fixed:

- `SDK-001` (0.10.0) — every tool opened its own `httpx.AsyncClient` and the
  server passed no `lifespan`. One pooled client behind a lifespan now. The
  response cache had been dead code: per-instance, discarded on every return,
  its 30-minute TTL never once reached.
- `SDK-004` (0.11.0) — the HTTP transports carried no CORS layer, so
  `Mcp-Session-Id` was neither exposed nor accepted and a browser client lost
  its session immediately after initialize.

Runs against the 36-check set: 17/15/4 → **19/15/2**.
Earlier runs, for the record, against the narrower 32-check set:
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

The history below records what each release closed. The current open set is 17
findings — 15 `partial` and 2 `fail` — documented under
`audits/2026-07-28T094256-Z-swiss-procurement-mcp/findings/` (`fail-or-partial`
policy).

Both fails are the accepted risks `SEC-009` and `SCALE-002`, recorded as `fail`
because the control is genuinely absent. Nothing else in the applicable set
fails.

**Closed in 0.10.0 — `SDK-001`, confirmed by the 09:42 run.** Every tool opened
its own `httpx.AsyncClient` via `async with SimapClient()`, and the server
passed no `lifespan` to the server object. That was a TCP and TLS handshake per tool
call, and it made `SimapClient._cache` dead code: the cache is per-instance, so
it was discarded the moment the tool returned and the 30-minute TTL was never
once reached. One pooled client now sits behind a lifespan, matching the sister
server (`amtsblatt-mcp`).

**Closed in 0.11.0 — `SDK-004`, confirmed by the same run.** The HTTP transports
carried no CORS layer, so `Mcp-Session-Id` was neither exposed nor accepted and
a browser-based MCP client lost its session immediately after initialize.
`_cors.py` names the header in both directions. Origins are fail-closed:
`MCP_CORS_ORIGINS` is unset by default, so no cross-origin browser access is
permitted until an operator lists origins explicitly.

**Closed in 0.12.0, not yet re-measured.** `ARCH-005` (a `.env.example` now
documents the seven environment variables the server honours; it holds no
secrets and `docs/secret-management.md` records why), `SEC-013`
(`docs/secret-management.md`), `OPS-003` (`ROADMAP.md`), `SDK-002`
(`match_type` is a `Literal`, not a bare `str`) and `OPS-002` (README.de parity
at 19 sections). `SEC-004` improved but stays `partial`: HTTPS is now enforced
before egress, while the resolved-IP blocklist and DNS pinning remain open.

**Closed in 0.13.0 and 0.14.0, not yet re-measured.** `SEC-004` and `SEC-005`
(a resolved-address blocklist and DNS pinning, `_net.py`, `tests/test_ssrf.py`)
and `ARCH-002` (a `<use_case>` tag on all nine tool descriptions).

**`ARCH-012` — the README no longer contradicts itself.** The "MCP Protocol
Version" section stated the version is pinned as an explicit constant while
"Maturity & updates" still called it "negotiated by the pinned `mcp` SDK" —
stale text left behind by the original ARCH-012 work, telling the reader the
opposite of what the code does. Both language versions were corrected.

**`OBS-001` — as closed in 0.16.0 as this repo can close it.** The gap was that
no test distinguished the protocol-error path from the execution-error path;
every existing test called the tool functions directly, where `isError` is not
observable at all. `tests/test_error_paths.py` drives a real `ClientSession`
over an in-memory transport and asserts both: an argument error arrives as a
tool result with `isError: true`, a bad request raises `McpError`, and the
`degraded` envelope stays a result rather than becoming either.

At the time that was written the check still could not pass: the lowlevel SDK
emitted protocol-error **code 0**, not the `-32601` the check asks for, though
`mcp.types` defined the constant. Two tests asserted that gap so an SDK fix
would arrive as a failing test rather than as a surprise. **It did — see 0.17.0
below.**

**`OBS-001` criterion 3 met in 0.17.0, not yet re-measured.** The migration to
`mcp` 2.x made the two pinned tests fail, exactly as they were written to. Under
2.0 a protocol error carries a real JSON-RPC code: `resources/read` on a missing
resource answers `-32602` (INVALID_PARAMS), `prompts/get` answers `-32603`. The
spec made the same correction from the other side — `2026-07-28` moved
resource-not-found from `-32002` to `-32602` to align with JSON-RPC, and
partitioned the server-error range so `-32020`…`-32099` belongs to MCP.

One deviation stays pinned rather than endorsed, unchanged by the migration: an
unknown **tool** is still reported as `is_error` inside a tool result rather than
as a protocol error, so "no such tool" and "the tool failed" remain
indistinguishable to a client that does not read the text. `OBS-002` is also
unchanged — `mask_error_details` does not exist in 2.0 either, and the guarantee
stays test-enforced rather than configured.

**What the `2026-07-28` spec does to `SEC-009` and `SCALE-002`.** Both controls
are about sessions, and the spec **removes protocol-level sessions entirely** —
no `initialize` handshake, no `Mcp-Session-Id` header, no SSE stream
resumability. Servers needing cross-call state are told to mint explicit handles
and pass them as ordinary tool arguments. This server has no cross-call state,
so it needs none.

That does not make the two findings pass, and it is worth being precise about
why: the audit catalogue still scores them against a protocol that had sessions.
What changes is their *character* — they move from "controls this server has not
implemented" toward "controls the protocol no longer defines". The honest
position until the catalogue catches up is that they remain `fail` and the
reasoning below still applies to the transports as the SDK actually ships them,
which — deliberately — still include the session-bearing legacy ones.

**`SDK-004` is not undone by that.** `_cors.py` names `Mcp-Session-Id` in both
directions, and the SDK still implements the legacy streamable-http transport and
SSE that use it. The CORS layer was re-verified against `starlette` 1.3.1, which
`mcp` 2.0 pulls in: preflight 200, the session header allowed and exposed,
`DELETE` among the allowed methods. It stops being load-bearing only once this
server drops those transports, which is a separate decision — SSE is now formally
deprecated, and `ROADMAP.md` tracks it.

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

**Status:** unreachable as specified. Severity in the catalogue: `critical`.

The check asks that a session id be cryptographically bound to a **user id taken
from a validated OAuth token's `sub` claim**. This server has no authentication —
the simap read endpoints are public and unauthenticated — so there is no `sub`
claim and nothing to bind a session to. This is not an effort question: the input
the control needs does not exist.

What is true today, criterion by criterion:

| Criterion | State |
|---|---|
| Session id entropy ≥128 bit | `uuid4().hex` from the SDK — 122 random bits, marginally short, and not ours to set |
| User id from a validated token | Impossible — no identity provider |
| Session bound to user id | Impossible — same reason |
| 401/403 on mismatch | Not applicable — no user to mismatch |
| Explicit TTL | Not settable: `session_idle_timeout` exists on `StreamableHTTPSessionManager` but `MCPServer` passes it through neither `Settings` nor `streamable_http_app()` (re-verified against `mcp` 2.0.0 — the major version did not change this) |
| Server-side invalidation | Yes — `DELETE` on the streamable-http endpoint terminates a session |

**What has changed:** `MCP_STATELESS=1` with `MCP_TRANSPORT=streamable-http` now
runs the server with no session tracking at all. That is the strongest available
answer — session hijacking and cross-session access become structurally
impossible rather than merely unlikely. It still does not make the check pass,
because the check asks for *binding*, not *absence*. See
[`docs/load-balancing.md`](docs/load-balancing.md).

**Closing it properly** means adding an OAuth/OIDC provider. That is a product
decision about whether this server should have users at all, not a remediation
task.

**This becomes urgent if** the server gains authentication, per-user state, or
any endpoint whose response depends on who is asking.

### Stateful load balancing (SCALE-002)

**Status:** partially addressed; not passing. Severity in the catalogue: `high`.

An earlier version of this section claimed the HTTP transports "run stateless, so
a second instance would not break sessions". **That was wrong.**
`stateless_http` defaults to `False`, so streamable-http did keep per-client
sessions in process memory, and two instances behind a round-robin balancer
would have broken clients exactly as the check describes. The claim is corrected
here rather than quietly removed, because a wrong reassurance is worse than an
open finding.

What exists now — [`docs/load-balancing.md`](docs/load-balancing.md):

- **Stateless mode** (`MCP_STATELESS=1`, streamable-http only), which removes
  session affinity as a question rather than answering it. Opt-in, because it
  gives up SSE stream resumption and server-initiated notifications.
- **Sticky-session configurations** for nginx and Kubernetes Ingress, keyed on
  the `Mcp-Session-Id` header, with the buffering and timeout settings the
  long-lived transports need.
- **An honest failover statement:** affinity prevents misrouting, not loss. If
  the instance holding a session dies, the session dies; a correct client
  re-initializes.

Two criteria remain unmet, which is why this is not recorded as passing: there is
no **explicit session TTL** (not settable through `MCPServer`, see above), and no
**shared-state session manager** — that would need replacing the SDK's in-process
manager, which the server object does not expose as an extension point, plus a
Redis dependency this server does not have.

**This becomes urgent if** the server is deployed multi-instance *and* keeps
sessions. Running stateless removes the combination.

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
