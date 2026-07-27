## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** ARCH-003
**PDF-Reference:** Sec 2.2

### Observed Behavior

- match_type field (exact/none) on search, code and office responses (models.py:38)
- Empty result carries an actionable note; filterless call now refused with the real cause (server.py:_assert_filtered)

### Expected Behavior

See the Pass Criteria of `ARCH-003` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- Still no fuzzy-match or suggestion mechanism on a zero-hit search

### Remediation

Add a suggestion path for a zero-hit search: on match_type == "none", offer the nearest CPV code or a widened date range rather than only stating that nothing matched.

### Effort Estimate

M
