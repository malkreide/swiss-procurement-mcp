## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** OBS-002
**Category:** OBS
**Audit-Run:** 2026-07-28T062517-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points collected).

- No traceback.format_exc() or sys.exc_info() anywhere in src/
- Upstream error bodies are not echoed — test_details_degraded_note_leaks_no_upstream_body asserts it

### Expected Behavior

All pass criteria of OBS-002 satisfied. See `checks/OBS-002` in the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- FastMCP is constructed without mask_error_details=True (server.py:62)

### Evaluator Notes

Criterion 1 is literally unmet; the substance it protects is covered by tests.

### Effort Estimate

M
