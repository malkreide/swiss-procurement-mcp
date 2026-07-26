## Finding: OPS-003 — Phasenarchitektur: Read-only First, dann Write, dann Multi-Agent

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `OPS-003` |
| **PDF-Reference** | Anhang C4 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

The read-only-first posture is explicit (Architecture A, write endpoints out of scope) and consistent with the readOnlyHint annotations, and SECURITY.md documents the re-evaluation triggers for gaining write/PII/cloud capability — but there is no explicit 'Phase 1/2/3' declaration and no roadmap file.

### Expected Behavior

The catalogue asks for an explicit phase declaration (read-only first, then write, then multi-agent) so consumers know the maturity stage and what is intentionally deferred.

### Evidence

- `README.md:44-56 — read-only-first posture explicit (Architecture A, write endpoints out of scope), consistent with readOnlyHint annotations`
- `SECURITY.md:63-73 — Re-evaluation triggers document prerequisites for gaining write/PII/cloud capability (phase-transition conditions)`

### Gaps

- No explicit 'Phase 1/2/3' declaration in README
- No roadmap file with phase-specific tasks

### Risk Description

None. This is a documentation-completeness gap; the actual posture is already correct and stated.

### Remediation

Add a one-line 'Phase 1 (read-only)' statement to the README and, optionally, a short roadmap section referencing the SECURITY.md re-evaluation triggers as the phase-transition conditions.

### Effort Estimate

S
