## Finding: ARCH-011 — Standardisierte Repo-Struktur (src-Layout, tests, README.de.md)

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-011
**Category:** ARCH
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (4 evidence points).

- All mandatory top-level files present
- src/ layout correct, tests/ and .github/workflows/ present
- ci.yml + publish.yml both present
- README.de.md parallel

### Expected Behavior

All pass criteria of ARCH-011 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- 9 tools (>5) but no tools/ directory split — server.py holds all handlers
- No README justification for the deviation

### Evaluator Notes

(none)

### Effort Estimate

S
