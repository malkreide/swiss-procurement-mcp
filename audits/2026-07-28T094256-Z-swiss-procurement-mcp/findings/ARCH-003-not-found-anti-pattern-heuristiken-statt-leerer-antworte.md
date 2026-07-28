## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-003
**Category:** ARCH
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points).

- match_type field present on all 6 search-style responses (server.py:427,505,566,666,708,766)
- Envelope carries an optional `note` field

### Expected Behavior

All pass criteria of ARCH-003 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- match_type only ever takes exact|none — no fuzzy match implemented
- Empty result carries no suggestions and no actionable hint

### Evaluator Notes

The field exists but the heuristic behind it does not.

### Effort Estimate

S
