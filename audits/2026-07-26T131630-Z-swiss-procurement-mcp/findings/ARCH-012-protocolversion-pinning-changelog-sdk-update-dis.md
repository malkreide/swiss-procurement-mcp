## Finding: ARCH-012 — protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `ARCH-012` |
| **PDF-Reference** | Anhang A9 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | fail |

### Observed Behavior

A Keep-a-Changelog CHANGELOG with a versioned 0.1.0 entry is present, but the MCP `protocolVersion` is not pinned anywhere (the SDK default negotiation is relied upon), the README has no 'MCP Protocol Version' / SDK-update-policy section, and there is no Dependabot/Renovate config for SDK update PRs.

### Expected Behavior

The catalogue asks for an explicit protocol-version and SDK-update discipline: pin/record the supported MCP protocol version, document an update policy, and automate dependency-update PRs so a breaking SDK bump is caught deliberately.

### Evidence

- `CHANGELOG.md:1-4 — present, explicitly Keep-a-Changelog format`
- `CHANGELOG.md:6 — versioned 0.1.0 entry with Added/Security/Scope sections`

### Gaps

- protocolVersion is not pinned anywhere in server code (relies on SDK default negotiation)
- No 'MCP Protocol Version' section and no SDK update policy in README
- No Dependabot/Renovate config for SDK update PRs (.github/dependabot.yml / renovate.json absent)

### Risk Description

Low-to-medium over time. Without a pinned protocol version and dependency automation, a future `mcp` SDK release could silently change negotiated behaviour or break the server, with no PR surfacing it.

### Remediation

Add a `.github/dependabot.yml` (pip ecosystem) so SDK bumps arrive as reviewable PRs; add a short 'MCP protocol version & SDK updates' note to the README stating the tested `mcp` version range; optionally assert the negotiated protocol version at startup.

### Effort Estimate

S
