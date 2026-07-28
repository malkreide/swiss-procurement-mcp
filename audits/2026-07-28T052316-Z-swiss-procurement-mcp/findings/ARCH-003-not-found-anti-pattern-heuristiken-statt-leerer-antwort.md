## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- match_type field (exact/none) on search, code and office responses (models.py:38)
- Empty result carries an actionable note; filterless call now refused with the real cause (server.py:_assert_filtered)

### Expected Behavior

See the Pass Criteria of `ARCH-003` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- Still no fuzzy-match or suggestion mechanism on a zero-hit search

### Effort Estimate

M
