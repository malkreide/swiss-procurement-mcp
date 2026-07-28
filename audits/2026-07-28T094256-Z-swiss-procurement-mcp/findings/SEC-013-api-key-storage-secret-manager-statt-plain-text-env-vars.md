## Finding: SEC-013 — API-Key-Storage: Secret Manager statt Plain-Text Env-Vars

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SEC-013
**Category:** SEC
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points).

- Server uses no API key at all — auth_model is none
- Container image carries no secrets

### Expected Behavior

All pass criteria of SEC-013 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- docs/secret-management.md absent, which the check requires even at Stufe 1

### Evaluator Notes

(none)

### Effort Estimate

M
