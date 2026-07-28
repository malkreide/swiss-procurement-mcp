## Finding: OPS-001 — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `OPS-001` |
| **PDF-Reference** | Anhang C1 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- 104 offline tests across 8 files, respx-mocked (tests/)
- 9 live tests marked @pytest.mark.live (tests/test_live.py)
- Marker registered in pyproject.toml:42
- CI runs pytest -m 'not live'; live runs on a nightly schedule only

### Expected Behavior

See the Pass Criteria of `OPS-001` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- The criterion asks for at least 5 unit tests per tool. Coverage is uneven: search_procurements and the input models are heavily covered, while get_publication_history and search_construction_codes have ~2 each.

### Effort Estimate

M
