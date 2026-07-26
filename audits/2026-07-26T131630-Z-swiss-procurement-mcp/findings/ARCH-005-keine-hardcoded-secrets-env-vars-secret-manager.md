## Finding: ARCH-005 — Keine Hardcoded Secrets: Env-Vars / Secret Manager only

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `ARCH-005` |
| **PDF-Reference** | Sec 2.1 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

No secrets of any kind exist in the source (the API is fully public; only a public User-Agent and a hardcoded public base URL), and `.env` is git-ignored. What is missing is the defence-in-depth tooling: no CI secret-scanning on PRs and no `.env.example`.

### Expected Behavior

Even a no-secret repo should run an automated secret-scan (gitleaks/trufflehog) on every PR as a regression guard, so a future contributor cannot introduce a credential unnoticed.

### Evidence

- `src/swiss_procurement_mcp/constants.py — only a public User-Agent and hardcoded public base URL; no keys/tokens/passwords anywhere in src/`
- `.gitignore:6 — .env is ignored`
- `SECURITY.md:31 — documents there are no API keys/credentials (public endpoints)`

### Gaps

- No CI secret-scanning workflow (gitleaks/trufflehog) on PRs — .github/workflows/ has none
- No .env.example in repo (no secrets exist to template, but the control is absent)

### Risk Description

Low today (nothing to leak), but the guardrail that keeps it that way is absent — a later feature that adds an API key could commit it without CI catching it.

### Remediation

Add a gitleaks GitHub Action on push/PR. Optionally add a `.env.example` if any configuration env vars are introduced. No key rotation needed — there are no secrets in history.

### Effort Estimate

S
