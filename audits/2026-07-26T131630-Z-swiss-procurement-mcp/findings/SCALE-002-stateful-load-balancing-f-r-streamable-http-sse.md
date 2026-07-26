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
