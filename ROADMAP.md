# Roadmap (OPS-003)

Phase model from the portfolio standard: **read-only first, then write, then
multi-agent.** A phase is not a plan, it is a claim about what the server is
allowed to do — so the current phase is stated in `README.md` and every tool
annotation must agree with it.

## Current phase: 1 — read-only

All nine tools are `readOnlyHint: True`, `destructiveHint: False`,
`openWorldHint: True`. The server wraps only the public read endpoints of the
simap.ch API. The ~200 write / `my/` / OIDC-protected endpoints (publishing
tenders, submitting offers) are deliberately not wrapped.

Nothing here is a stepping stone to Phase 2. Phase 2 is not planned.

## Phase 1 — open work

Ordered by value, not by severity. Audit ids refer to the `mcp-audit`
catalogue; the current run lives under `audits/`.

| Item | Check | State |
|---|---|---|
| Fuzzy match or suggestions when a search returns nothing | `ARCH-003` | open — needs a design decision first, see below |
| Split `server.py` handlers into a `tools/` package | `ARCH-011` | open — refactor with regression risk, low payoff |
| Retire the deprecated HTTP+SSE transport | — | open, see below |
| Per-tool-call progress reporting via `ctx: Context` | `SDK-003` | not planned while every tool returns in milliseconds |

Closed since the last audit run, and therefore still listed as `partial` there:
`SEC-004` and `SEC-005` (resolved-address blocklist and DNS pinning, `_net.py`,
`tests/test_ssrf.py`) and `ARCH-002` (`<use_case>` on all nine tools). The audit
under `audits/` is a measurement, not a status board — it will say `partial`
until it is re-run.

**`OBS-001` — the blocked criterion cleared in 0.17.0.** `tests/test_error_paths.py`
drives a real client and asserts the two paths apart: an execution error arrives
as a tool result with `is_error: true`, a protocol error raises `MCPError` with
a real JSON-RPC code (`-32602` / `-32603`). Under `mcp` 1.x the code was always
`0`, which the file pinned with two tests written to fail the day the SDK fixed
it. The migration made them fail; they were rewritten into assertions. What
remains open is not a code change: an unknown *tool* is still delivered as a
tool result rather than a protocol error.

**Retiring SSE is now a question with a deadline.** Spec `2026-07-28` reclassifies
HTTP+SSE as Deprecated under a twelve-month removal window, and removes
protocol-level sessions and stream resumability from streamable-http. This server
offers SSE via `MCP_TRANSPORT=sse`, and the SDK still ships it, so nothing breaks
today. The work is to decide when to drop it rather than to discover the date
from a broken deployment — and dropping it is what eventually retires
`MCP_STATELESS`, the `Mcp-Session-Id` half of `_cors.py`, and the sticky-session
half of `docs/load-balancing.md` along with it.

**`ARCH-003` needs a decision before it needs code.** The check wants empty
results to trigger a fuzzy or suggestion mechanism. For CPV and construction
code lookups that is straightforward and useful. For tender search it is not
obviously right: a procurement search that silently widens its terms can imply
a tender exists when none does, which is worse than an honest empty result. The
likely landing point is fuzzy for the code lookups, exact-only for tender
search, documented as a deliberate split — which is what the check permits for
sensitive tools.

## Accepted risks, not roadmap items

`SEC-009` (session-to-user binding) and `SCALE-002` (stateful load balancing)
are recorded as `fail` in every audit and will stay that way. They are accepted
by explicit decision, documented in `SECURITY.md`. An accepted risk is a
decision, not a passing check, and not a backlog item either.

They become roadmap items only if the deployment model changes — see below.

## What Phase 1 → 2 would require

Not planned. Recorded so that the bar is written down before anyone is tempted
to clear it informally:

- An audit run with no open `critical` or `high` findings that are not accepted
  risks
- ISDS (Informationssicherheits- und Datenschutzkonzept)
- A DSG processing-activity record (`Verarbeitungsverzeichnis`)
- Re-evaluation of the lethal-trifecta assessment in `SECURITY.md`: a write
  capability turns the third leg on, and the current assessment depends on it
  being off
- `SEC-009` and `SCALE-002` cease to be acceptable the moment the server holds
  sessions on behalf of identified users

## Phase 2 → 3

Out of scope. Listed for completeness: semantic layer, identity resolution,
sign-off from management and the data protection officer.
