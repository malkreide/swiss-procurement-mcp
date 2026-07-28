## Finding: SEC-009 — Session-ID Cryptographic Binding (user_id:session_id)

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `SEC-009` |
| **PDF-Reference** | Sec 4.6 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- No authentication and no session state: stdio has no sessions, and the HTTP transports run stateless

### Expected Behavior

See the Pass Criteria of `SEC-009` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- If an HTTP transport is exposed there is no session-to-user binding at all; acceptable only because there is no auth and no per-user data

### Effort Estimate

M
