## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP / SSE

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SCALE-002
**Category:** SCALE
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **fail** (2 Evidenzpunkte).

- docs/load-balancing.md mit nginx- und K8s-Ingress-Konfiguration auf Mcp-Session-Id
- MCP_STATELESS=1 entfernt Session-Affinitaet als Frage

### Expected Behavior

Alle Pass-Kriterien von SCALE-002 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- Kein Sticky-LB und kein Shared-State-Session-Manager tatsaechlich deployed
- Kein expliziter Session-TTL setzbar: session_idle_timeout wird von MCPServer nicht durchgereicht (an mcp 2.0.0 erneut geprueft)

### Effort Estimate

L
