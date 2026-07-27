## Finding: SEC-009 — Session-ID Cryptographic Binding (user_id:session_id)

**Severity:** critical
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** SEC-009
**PDF-Reference:** Sec 4.6

### Observed Behavior

- No authentication and no session state: stdio has no sessions, and the HTTP transports run stateless

### Expected Behavior

See the Pass Criteria of `SEC-009` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- If an HTTP transport is exposed there is no session-to-user binding at all; acceptable only because there is no auth and no per-user data

### Remediation

Only relevant once an HTTP transport is exposed with authentication. Until then the absence of sessions is the mitigation; revisit as part of any phase-2 transition.

### Effort Estimate

L
