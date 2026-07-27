## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP / SSE

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** SCALE-002
**PDF-Reference:** Sec 5.2

### Observed Behavior

- Single-instance design; SECURITY.md and README document the deployment scope

### Expected Behavior

See the Pass Criteria of `SCALE-002` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No sticky-session or shared-state session manager; multi-instance HTTP deployment would break session affinity
- Deployment profile is local-stdio, so the exposure is currently theoretical

### Remediation

Only relevant if the server is ever deployed multi-instance over HTTP. Document the single-instance constraint in the README deployment section, or add a shared-state session manager before scaling out.

### Effort Estimate

L
