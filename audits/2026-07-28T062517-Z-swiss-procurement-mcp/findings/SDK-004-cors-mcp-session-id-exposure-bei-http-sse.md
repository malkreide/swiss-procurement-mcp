## Finding: SDK-004 — CORS Mcp-Session-Id Exposure bei HTTP/SSE

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SDK-004
**Category:** SDK
**Audit-Run:** 2026-07-28T062517-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **fail** (1 evidence points collected).

- Transport is dual — SSE and streamable-http reachable via MCP_TRANSPORT

### Expected Behavior

All pass criteria of SDK-004 satisfied. See `checks/SDK-004` in the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No CORS middleware configured anywhere in src/
- expose_headers does not include Mcp-Session-Id
- allow_headers not configured

### Evaluator Notes

A browser-based MCP client cannot read the session header, so HTTP transport is effectively browser-unusable.

### Effort Estimate

M
