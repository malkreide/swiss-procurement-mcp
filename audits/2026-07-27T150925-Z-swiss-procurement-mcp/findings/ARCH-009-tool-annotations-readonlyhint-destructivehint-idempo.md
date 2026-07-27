## Finding: ARCH-009 — Tool Annotations: readOnlyHint, destructiveHint, idempotentHint, openWorldHint

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** ARCH-009
**PDF-Reference:** Anhang A5

### Observed Behavior

- Shared READ_TOOL annotation on all 9 tools: readOnlyHint, idempotentHint, openWorldHint (server.py:52)

### Expected Behavior

See the Pass Criteria of `ARCH-009` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- destructiveHint is omitted rather than set to False — the check requires explicit annotations, not defaults by omission (amtsblatt-mcp sets it explicitly)

### Remediation

Add "destructiveHint": False to the shared READ_TOOL dict. One line; the check asks for explicit annotations rather than defaults by omission.

### Effort Estimate

S
