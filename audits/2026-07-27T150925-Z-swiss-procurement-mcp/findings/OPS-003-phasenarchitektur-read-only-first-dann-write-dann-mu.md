## Finding: OPS-003 — Phasenarchitektur: Read-only First, dann Write, dann Multi-Agent

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** OPS-003
**PDF-Reference:** Anhang C4

### Observed Behavior

- README 'Maturity & updates' declares Phase 1 (read-only) explicitly
- Annotations match the phase: all tools readOnlyHint; write/OIDC endpoints deliberately unwrapped
- SECURITY.md documents the re-evaluation triggers for a move to a write phase

### Expected Behavior

See the Pass Criteria of `OPS-003` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No roadmap file with phase-specific tasks

### Remediation

Add a ROADMAP.md with the phase-1 scope and the documented preconditions for a phase-2 (write) transition; SECURITY.md already names the triggers.

### Effort Estimate

S
