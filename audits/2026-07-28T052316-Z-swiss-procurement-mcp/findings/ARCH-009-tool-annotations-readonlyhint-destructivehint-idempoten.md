## Finding: ARCH-009 — Tool Annotations: readOnlyHint, destructiveHint, idempotentHint, openWorldHint

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `ARCH-009` |
| **PDF-Reference** | Anhang A5 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- Shared READ_TOOL annotation on all 9 tools: readOnlyHint, idempotentHint, openWorldHint (server.py:52)

### Expected Behavior

See the Pass Criteria of `ARCH-009` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- destructiveHint is omitted rather than set to False — the check requires explicit annotations, not defaults by omission (amtsblatt-mcp sets it explicitly)

### Effort Estimate

S
