## Finding: OBS-001 — Protocol vs. Execution Errors: korrekte Trennung

**Severity:** high
**Status:** partial
**Server:** swiss-procurement-mcp
**Check-Reference:** OBS-001
**Category:** OBS
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (3 Evidenzpunkte).

- Protokollfehler tragen jetzt echte JSON-RPC-Codes: -32602 (resources/read), -32603 (prompts/get) — an mcp 2.0.0 gemessen
- tests/test_error_paths.py deckt beide Pfade ueber einen echten Client ab (11 Tests)
- Argument- und Extra-Field-Fehler kommen als tool-result mit is_error=true

### Expected Behavior

Alle Pass-Kriterien von OBS-001 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- Upstream-Ausfall kommt als normales Ergebnis mit provenance='degraded' statt is_error=true — dokumentierte, begruendete Abweichung
- Unbekanntes Tool wird als tool-result statt als Protokollfehler geliefert (SDK-Verhalten, oberhalb der Tool-Schicht)

### Effort Estimate

M
