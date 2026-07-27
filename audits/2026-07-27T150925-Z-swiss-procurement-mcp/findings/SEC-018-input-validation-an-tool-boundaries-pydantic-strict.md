## Finding: SEC-018 — Input-Validation an Tool-Boundaries (Pydantic strict / Zod)

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** SEC-018
**PDF-Reference:** Sec 3 / Sec 4 (Defense-in-Depth)

### Observed Behavior

- limit bounded 1..100 and free-text capped at 200 chars (server.py:_check_limit/_check_text)
- canton, process_type, pub_type, canton_match and code system validated against fixed allow-lists
- v0.4.0 added the filterless-call guard, refusing an unbounded query with its real cause

### Expected Behavior

See the Pass Criteria of `SEC-018` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- Inputs are flat keyword arguments validated imperatively; no Pydantic input models, so no strict=True / extra='forbid' and no declarative ge/le or pattern constraints

### Remediation

Move tool inputs to Pydantic models with strict=True and extra="forbid", replacing the imperative _check_limit/_check_text guards with declarative ge/le and pattern constraints. amtsblatt-mcp already does this and passes the check.

### Effort Estimate

M
