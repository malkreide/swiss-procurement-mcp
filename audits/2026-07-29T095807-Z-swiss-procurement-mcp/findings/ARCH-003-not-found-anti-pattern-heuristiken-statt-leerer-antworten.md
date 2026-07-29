## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

**Severity:** medium
**Status:** partial
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-003
**Category:** ARCH
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (1 Evidenzpunkte).

- match_type-Feld (exact/none) in models.py, 4 Fundstellen

### Expected Behavior

Alle Pass-Kriterien von ARCH-003 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- Kein Fuzzy-/Suggestion-Mechanismus bei leerem Ergebnis — bewusste offene Design-Entscheidung, in ROADMAP.md begründet

### Effort Estimate

M
