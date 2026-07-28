## Finding: SEC-005 — DNS-Rebinding-Prevention: DNS-Pinning gegen TOCTOU

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SEC-005
**Category:** SEC
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (1 evidence points).

- Single httpx request per attempt; no manual resolve-then-connect split

### Expected Behavior

All pass criteria of SEC-005 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No DNS pinning implemented
- No test asserting one DNS call per request

### Evaluator Notes

(none)

### Effort Estimate

M
