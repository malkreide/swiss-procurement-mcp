## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | accepted-risk |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 6.3 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

The server does no logging at all — there is no structured-logging library, no JSON/logfmt output, and no RFC 5424 severities or per-call correlation context. (This is why stdout stays clean; see OBS-004 pass.)

### Expected Behavior

For SIEM ingestion the catalogue wants JSON-structured logs with RFC 5424 severities and a trace/correlation id per tool call.

### Evidence

- `src/swiss_procurement_mcp/ — no print() statements (clean stdout for stdio)`
- `SECURITY.md:50-54 — structured logging explicitly documented as accepted risk for a stdio public-data server`

### Gaps

- No structured logging library (structlog/loguru) in dependencies; no JSON/logfmt output
- No RFC 5424 severity levels or per-tool-call bound context (session_id/correlation_id) — the server does no logging at all

### Risk Description

None for a stdio server consumed by a local client. Structured logging only matters under a centralised log pipeline.

### Remediation

Accepted risk — already documented in SECURITY.md. Introduce structured JSON logging to stderr (structlog) with a per-call correlation id if the server is lifted to a cloud/SSE deployment behind a SIEM.

### Effort Estimate

S
