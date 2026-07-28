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
| Resolved-IP blocklist for private, loopback, link-local and `169.254.169.254` | `SEC-004` | open |
| DNS pinning so the resolved IP is the one connected to | `SEC-005` | open |
| `<use_case>` tags on all tool descriptions; `source_status` description above the 100-char floor | `ARCH-002` | open |
| Fuzzy match or suggestions when a search returns nothing | `ARCH-003` | open — needs a design decision first, see below |
| Split `server.py` handlers into a `tools/` package | `ARCH-011` | open — refactor with regression risk, low payoff |
| Per-tool-call progress reporting via `ctx: Context` | `SDK-003` | not planned while every tool returns in milliseconds |

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
