## Finding: SEC-009 — Session-ID Cryptographic Binding (user_id:session_id)

**Severity:** critical
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SEC-009
**Category:** SEC
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **fail** (2 Evidenzpunkte).

- Serverseitige Invalidierung ueber DELETE am streamable-http-Endpunkt
- MCP_STATELESS=1 entfernt Session-Tracking vollstaendig

### Expected Behavior

Alle Pass-Kriterien von SEC-009 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- Keine Authentifizierung, kein OAuth-sub-Claim — es gibt keine Identitaet zum Binden
- Kein expliziter Session-TTL setzbar
- SDK-Session-IDs tragen 122 statt 128 Zufallsbits

### Effort Estimate

XL
