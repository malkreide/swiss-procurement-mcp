## Finding: ARCH-012 — protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-012
**Category:** ARCH
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (4 evidence points).

- MCP_PROTOCOL_VERSION = '2025-11-25' pinned (server.py)
- CHANGELOG.md in Keep-a-Changelog format
- README:236 'MCP Protocol Version' section present
- Dependabot active (.github/dependabot.yml)

### Expected Behavior

All pass criteria of ARCH-012 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- README:355 contradicts README:236 — claims the version is 'negotiated by the pinned mcp SDK' when it is an explicit constant

### Evaluator Notes

Stale sentence left behind by the ARCH-012 work.

### Effort Estimate

S
