## Finding: ARCH-005 — Keine Hardcoded Secrets: Env-Vars / Secret Manager only

**Severity:** critical
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-005
**Category:** ARCH
**Audit-Run:** 2026-07-28T062517-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (5 evidence points collected).

- No secrets in source; server has no auth model at all
- .gitignore excludes .env (line 6)
- gitleaks runs on PRs (.github/workflows/security.yml:11)
- tests/test_secrets.py present in sister server pattern

### Expected Behavior

All pass criteria of ARCH-005 satisfied. See `checks/ARCH-005` in the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No .env.example in the repo

### Evaluator Notes

Nothing to leak, but the required placeholder file is absent.

### Effort Estimate

M
