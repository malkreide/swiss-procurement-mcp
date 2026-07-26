## Finding: ARCH-009 — Tool Annotations: readOnlyHint, destructiveHint, idempotentHint, openWorldHint

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `ARCH-009` |
| **PDF-Reference** | Anhang A5 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

All 8 tools carry `annotations={'readOnlyHint': True}` and the README documents it, but `openWorldHint: true` is not set on any tool even though every tool reaches an external system (simap.ch), and `idempotentHint` is not set on the idempotent read tools.

### Expected Behavior

Tools that query an external, changing world should advertise `openWorldHint: true`; deterministic read tools may advertise `idempotentHint`. This lets clients reason about caching and retaction.

### Evidence

- `src/swiss_procurement_mcp/server.py:92,179,231,284,319,348,387,437 — all 8 tools carry explicit annotations={'readOnlyHint': True}, consistent with read-only behaviour`
- `README.md:102 — 'All tools are readOnlyHint: true' documented`

### Gaps

- openWorldHint: true is NOT set on any tool, yet all 8 reach an external system (simap.ch HTTP) — should be present
- idempotentHint not set on the idempotent read tools

### Risk Description

Low. Clients get a slightly less accurate picture of tool semantics (e.g. that results may change between calls), but behaviour is unaffected.

### Remediation

Add `openWorldHint: True` to every tool's annotations dict (all reach live simap.ch). Optionally add `idempotentHint: True` to the pure reference-code lookups. One-line change per tool.

### Effort Estimate

S
