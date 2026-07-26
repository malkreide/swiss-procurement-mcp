## Finding: ARCH-008 — Drei Primitive nutzen: Tools, Resources und Prompts

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | accepted-risk |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `ARCH-008` |
| **PDF-Reference** | Anhang A2 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

The server exposes only the Tools primitive (8 `@mcp.tool`). No MCP Resources or Prompts are registered, and the README does not state a justification for tools-only.

### Expected Behavior

The catalogue encourages using Resources (e.g. a publication or reference-code list as a cacheable URI) and/or Prompts where natural, or documenting why tools-only was chosen.

### Evidence

- `src/swiss_procurement_mcp/server.py — only Tools primitive used; no @mcp.resource or @mcp.prompt registrations`
- `README.md:89-102 — Tools table present`

### Gaps

- Only one of three primitives used and README does not document a justification for tools-only
- Idempotent read-only tools (e.g. reference-code searches) not assessed for Resources-migration potential

### Risk Description

None security-relevant. Purely a capability-completeness gap; discovery works today via the search tools.

### Remediation

Accepted risk — identical posture to the rest of the portfolio (tools-only for Phase-1 wrappers). Add a one-paragraph 'MCP primitives' note to the README, and revisit Resources once the portfolio standardises a URI scheme.

### Effort Estimate

M
