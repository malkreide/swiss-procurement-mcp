## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

search_procurements returns an actionable note on empty results, and find_procurement_office does client-side substring matching, but responses carry no match_type field and the code/award/history searches have no fuzzy-or-suggestion fallback on an empty result.

### Expected Behavior

Non-sensitive search tools should distinguish exact/fuzzy/none via a match_type field and offer a suggestion or term-refinement hint when nothing matches, so the model refines rather than dead-ends.

### Evidence

- `src/swiss_procurement_mcp/server.py:164-166 — search_procurements returns actionable note on empty results ('Widen the date range or check canton/CPV filters')`
- `src/swiss_procurement_mcp/server.py:398,417 — find_procurement_office does client-side substring (fuzzy-ish) matching`

### Gaps

- No match_type field (exact/fuzzy/none) on any response
- No fuzzy-match/suggestion fallback for empty CPV/construction-code or award searches (search_awards has no empty-result note)

### Risk Description

Low. On an empty result the model may report 'nothing found' without offering the user a way forward; it will not hallucinate here because the envelope is structured and honest.

### Remediation

Add a `match_type` field to the search envelopes and a short suggestion note (or nearest-code fuzzy fallback) on empty CPV/construction-code/award/history results, mirroring the existing search_procurements note.

### Effort Estimate

S
