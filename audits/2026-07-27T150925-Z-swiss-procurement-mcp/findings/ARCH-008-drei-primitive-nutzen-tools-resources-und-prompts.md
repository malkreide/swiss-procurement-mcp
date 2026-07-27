## Finding: ARCH-008 — Drei Primitive nutzen: Tools, Resources und Prompts

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** ARCH-008
**PDF-Reference:** Anhang A2

### Observed Behavior

- Tools only; 9 read-only tools would be Resource candidates

### Expected Behavior

See the Pass Criteria of `ARCH-008` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No Resources, no Prompts, and no documented rationale in the README for tools-only

### Remediation

Either expose the stable reference data (canton list, code systems, rubric taxonomy) as Resources, or add a short README paragraph stating why this server is tools-only. The rationale is cheap and closes the check.

### Effort Estimate

S
