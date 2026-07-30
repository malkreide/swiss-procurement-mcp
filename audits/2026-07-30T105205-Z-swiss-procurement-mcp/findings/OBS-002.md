## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

**Severity:** high
**Status:** partial
**Server:** swiss-procurement-mcp
**Check-Reference:** OBS-002
**Category:** OBS
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (3 Evidenzpunkte).

- Keine Tracebacks/Pfade in Tool-Results, per Test abgesichert (test_execution_error_carries_no_stack_trace)
- Upstream-4xx-Bodies auf 300 Zeichen gekuerzt
- prompts/get antwortet unter 2.0 mit 'Internal server error' statt rohem ValueError

### Expected Behavior

Alle Pass-Kriterien von OBS-002 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- mask_error_details existiert in mcp 2.0.0 nicht — Einstellung nicht setzbar, an 2.0.0 erneut geprueft

### Effort Estimate

S
