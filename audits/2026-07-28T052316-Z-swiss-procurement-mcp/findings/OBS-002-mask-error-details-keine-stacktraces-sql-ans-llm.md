## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 6.2 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- _degraded returns a fixed sanitised note; neither the exception nor the upstream body reaches the model (server.py:73)
- No traceback.format_exc() anywhere in src/

### Expected Behavior

See the Pass Criteria of `OBS-002` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- mask_error_details=True is not set on the FastMCP constructor, so an unexpected exception outside the caught paths could still surface

### Effort Estimate

S
