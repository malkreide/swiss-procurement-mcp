## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** OBS-003
**PDF-Reference:** Sec 6.3

### Observed Behavior

- No print() in src/ (0 hits)

### Expected Behavior

See the Pass Criteria of `OBS-003` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No logger at all: no structured logging dependency, no JSON/logfmt output, no severity levels, no per-tool-call context. Only 1 of 5 criteria met
- Re-grade: the prior run recorded 'partial' for the same code; on the criteria as written this is a fail

### Remediation

Adopt the structured-logging module from the companion amtsblatt-mcp (_log.py: JSON to stderr, logged_tool decorator, per-call context). It is a direct port and closes the only failing check.

### Effort Estimate

M
