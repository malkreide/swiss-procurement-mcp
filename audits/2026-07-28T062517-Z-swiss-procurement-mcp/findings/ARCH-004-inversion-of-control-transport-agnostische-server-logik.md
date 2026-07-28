## Finding: ARCH-004 — Inversion of Control: Transport-agnostische Server-Logik

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-004
**Category:** ARCH
**Audit-Run:** 2026-07-28T062517-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points collected).

- Transport selected by MCP_TRANSPORT env var, stdio default (__main__.py)
- Tool outputs are transport-independent

### Expected Behavior

All pass criteria of ARCH-004 satisfied. See `checks/ARCH-004` in the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No tool uses ctx: Context
- Config read via os.environ at module scope, not a Settings object
- No shared lifespan — setup is not common across transports

### Evaluator Notes

(none)

### Effort Estimate

M
