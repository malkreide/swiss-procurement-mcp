## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP / SSE

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `SCALE-002` |
| **PDF-Reference** | Sec 5.2 |
| **Audit-Datum** | 2026-07-27 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- Single-instance design; SECURITY.md and README document the deployment scope

### Expected Behavior

See the Pass Criteria of `SCALE-002` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No sticky-session or shared-state session manager; multi-instance HTTP deployment would break session affinity
- Deployment profile is local-stdio, so the exposure is currently theoretical

### Effort Estimate

L
