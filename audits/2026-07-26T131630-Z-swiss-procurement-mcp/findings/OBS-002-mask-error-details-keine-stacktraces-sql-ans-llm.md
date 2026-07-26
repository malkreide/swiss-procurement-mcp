## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 6.2 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

Upstream 4xx bodies are truncated to 300 chars, no tracebacks/exc_info are surfaced, and the degraded note is a user-friendly message — but FastMCP is not initialised with `mask_error_details=True`, and the degraded note embeds `str(exc)` which can include the truncated upstream body.

### Expected Behavior

The server should mask internal error detail from the model by default (`mask_error_details=True`) and avoid embedding raw upstream response text in tool output.

### Evidence

- `src/swiss_procurement_mcp/client.py:99-100 — upstream 4xx body truncated to 300 chars; no traceback/exc_info surfaced`
- `src/swiss_procurement_mcp/server.py:46-52 — degraded note is a user-friendly message, no stack traces`
- `SECURITY.md:32 — documents that no stack traces are surfaced to the model`

### Gaps

- FastMCP is initialised without mask_error_details=True (src/swiss_procurement_mcp/server.py:43)
- Degraded note embeds str(exc) which can include the truncated upstream response body (public-API text, low sensitivity, but not fully masked)

### Risk Description

Low. The embedded text is public-API error body (low sensitivity), but an unexpected exception could still surface implementation detail to the model.

### Remediation

Initialise `FastMCP(..., mask_error_details=True)` and drop the raw `str(exc)`/upstream-body substring from the degraded note in favour of a fixed message plus a coarse reason code.

### Effort Estimate

S
