## Finding: SEC-004 — SSRF-Prevention: HTTPS-Enforcement + IP-Blocklisting

**Severity:** critical
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SEC-004
**Category:** SEC
**Audit-Run:** 2026-07-28T062517-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points collected).

- _assert_host_allowed() runs before every request (client.py:104,181)
- ALLOWED_HOSTS frozenset pins www.simap.ch (constants.py:17)

### Expected Behavior

All pass criteria of SEC-004 satisfied. See `checks/SEC-004` in the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No explicit https scheme validation before egress
- No resolved-IP blocklist — 169.254.169.254, private and link-local ranges unchecked
- No DNS pinning, so a TOCTOU rebind is possible

### Evaluator Notes

Base URL is a hardcoded https constant, which mitigates in practice but is not the control the check asks for.

### Effort Estimate

M
