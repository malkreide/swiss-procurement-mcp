## Finding: SEC-019 — Lethal Trifecta vermeiden: Server-Separation Read vs Write/Send

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `SEC-019` |
| **PDF-Reference** | Anhang B1 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

The server is structurally safe against the lethal trifecta: it reads only PUBLIC data (no private-data leg), egress is fixed to a single hardcoded host with no arbitrary-send capability (no exfiltration leg), and all tools are read-only — at most two trifecta legs are ever present. What is missing is a written assessment.

### Expected Behavior

The catalogue asks for an explicit, documented lethal-trifecta assessment (which legs are present/absent and why) so the safety argument is auditable, not implicit.

### Evidence

- `src/swiss_procurement_mcp/ — reads only PUBLIC procurement data (no private/sensitive data), so the 'private data access' leg of the trifecta is absent`
- `src/swiss_procurement_mcp/constants.py:12 — egress fixed to a single hardcoded host; no send/write-to-arbitrary-destination capability (the exfiltration leg is absent)`
- `server.py — all tools readOnlyHint; at most two trifecta legs present (external fetch + ingesting external content)`

### Gaps

- No explicit lethal-trifecta assessment/ADR documented in README or docs/ (server is structurally safe but the required written evaluation is missing)

### Risk Description

None in practice — the exfiltration leg is genuinely absent. The gap is documentation: the safety property is real but unwritten.

### Remediation

Add a short 'Lethal-trifecta assessment' note to SECURITY.md or docs/ stating that only the external-fetch leg is present, the private-data and arbitrary-send legs are absent, and what would change that.

### Effort Estimate

S
