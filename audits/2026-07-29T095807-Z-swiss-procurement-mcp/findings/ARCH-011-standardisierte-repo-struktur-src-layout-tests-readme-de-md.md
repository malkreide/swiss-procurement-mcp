## Finding: ARCH-011 — Standardisierte Repo-Struktur (src-Layout, tests, README.de.md)

**Severity:** medium
**Status:** partial
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-011
**Category:** ARCH
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 Evidenzpunkte).

- Module getrennt: _net, _cors, _log, client, constants, inputs, models
- server.py 824 Zeilen

### Expected Behavior

Alle Pass-Kriterien von ARCH-011 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- Kein tools/-Package — alle 9 Handler in server.py. Refactor mit Regressionsrisiko, bewusst zurückgestellt

### Effort Estimate

L
