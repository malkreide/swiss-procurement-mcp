## Finding: ARCH-012 — protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `ARCH-012` |
| **PDF-Reference** | Anhang A9 |
| **Audit-Datum** | 2026-07-27 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- CHANGELOG.md in Keep-a-Changelog format; 'Maturity & updates' documents the SDK-update policy
- Dependabot weekly pip + github-actions PRs (.github/dependabot.yml)
- mcp SDK floor raised to >=1.28.1 for CVE-2026-59950 in v0.4.0

### Expected Behavior

See the Pass Criteria of `ARCH-012` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- protocolVersion is not pinned in code; no dedicated 'MCP Protocol Version' README section

### Effort Estimate

S
