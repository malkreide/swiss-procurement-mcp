## Finding: SDK-003 — Context Injection für Progress Reports und Logging

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SDK-003
**Category:** SDK
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points).

- No tool is expected to exceed 2s — each is a single upstream call
- Errors surface as tool results, not silently swallowed

### Expected Behavior

All pass criteria of SDK-003 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No tool takes ctx: Context
- search_procurements_detailed fans out to 5 upstream calls and reports no progress

### Evaluator Notes

(none)

### Effort Estimate

S
