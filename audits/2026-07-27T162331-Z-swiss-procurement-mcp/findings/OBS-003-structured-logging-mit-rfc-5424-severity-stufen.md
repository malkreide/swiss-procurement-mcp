## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 6.3 |
| **Audit-Datum** | 2026-07-27 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- Structured JSON to stderr with a custom formatter (_log.py:28-41)
- One tool_call record per call with tool/status/latency_ms on all 9 tools (_log.py:59-88, server.py decorators)
- No print() anywhere in src/
- upstream_degraded at WARNING carrying the exception type only (server.py:79-87)

### Expected Behavior

See the Pass Criteria of `OBS-003` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No structured-logging dependency (structlog/loguru): stdlib logging with a hand-rolled JSON formatter. Achieves structured output, but the criterion names a library in `dependencies` and pyproject.toml lists none.
- Only 2 severity levels actively used (INFO, WARNING); the criterion asks for at least 4 (debug, info, warning, error).
- Per-call context carries tool/status/latency but no session_id or correlation_id, so records from concurrent sessions cannot be grouped.

### Effort Estimate

S
