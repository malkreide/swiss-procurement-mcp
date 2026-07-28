## Finding: ARCH-004 — Inversion of Control: Transport-agnostische Server-Logik

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-004
**Category:** ARCH
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (3 evidence points).

- Transport selected by MCP_TRANSPORT env var, stdio default (__main__.py)
- Outputs transport-independent
- Lifespan is now shared across transports (server.py:66) — was absent at the previous run

### Expected Behavior

All pass criteria of ARCH-004 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No tool uses ctx: Context
- Config read via os.environ at module scope, not a Settings object

### Evaluator Notes

Improved by the SDK-001 work: 3 of 5 criteria now met, previously 2.

### Effort Estimate

M
