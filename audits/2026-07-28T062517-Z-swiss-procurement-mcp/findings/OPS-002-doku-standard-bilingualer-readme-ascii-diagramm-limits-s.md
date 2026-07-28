## Finding: OPS-002 — Doku-Standard: bilingualer README, ASCII-Diagramm, Limits-Sektion

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** OPS-002
**Category:** OPS
**Audit-Run:** 2026-07-28T062517-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (5 evidence points collected).

- All 8 mandatory sections present in README.md
- Anchor demo query concrete and natural-language (README:21)
- ASCII/Mermaid diagram present
- Known limitations section explicit (README:310)
- CONTRIBUTING.md + CONTRIBUTING.de.md bilingual

### Expected Behavior

All pass criteria of OPS-002 satisfied. See `checks/OPS-002` in the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- README.de.md has 17 top-level sections against README.md's 19

### Evaluator Notes

(none)

### Effort Estimate

S
