## Finding: SDK-001 — FastMCP Lifespan via @asynccontextmanager + AsyncExitStack

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SDK-001
**Category:** SDK
**Audit-Run:** 2026-07-28T062517-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **fail** (1 evidence points collected).

- httpx.AsyncClient constructed per tool call via 'async with SimapClient()' in all 9 tools (server.py:406,477,549,587,611,650,692,726,775)

### Expected Behavior

All pass criteria of SDK-001 satisfied. See `checks/SDK-001` in the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No @asynccontextmanager lifespan defined
- FastMCP('swiss-procurement-mcp') receives no lifespan= argument
- New AsyncClient per tool call — the explicit anti-pattern in the check
- SimapClient._cache is per-instance, so the response cache is discarded on every call

### Evaluator Notes

Costs a TCP+TLS handshake per tool call and makes the cache dead code.

### Effort Estimate

M
