## Finding: OPS-001 — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `OPS-001` |
| **PDF-Reference** | Anhang C1 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

Test infrastructure is strong: respx-mocked unit tests, a registered `live` marker, CI running `pytest -m 'not live'` on 3.10–3.12 plus a separate nightly live job. But unit depth is below the '≥5 per tool' guidance (~7 unit + 4 resilience tests for 8 tools), and live tests cover only 5 of the 8 tools.

### Expected Behavior

Each tool should have several unit tests covering happy path plus edge/error cases, and the live suite should exercise every tool at least once.

### Evidence

- `tests/test_tools.py + tests/test_resilience.py — respx-mocked unit tests present`
- `tests/test_live.py:13 — pytestmark = pytest.mark.live; live tests gated`
- `pyproject.toml:42 — 'live' marker registered; ci.yml:43 runs pytest -m 'not live'; ci.yml:64-82 separate nightly/dispatch live job`

### Gaps

- Unit-test depth below spec: ~7 unit + 4 resilience tests total, not >=5 per tool for 8 tools
- Live tests cover 5 of 8 tools (missing get_publication_history, search_construction_codes, find_procurement_office)

### Risk Description

Low. Core paths and the resilience/degrade path are tested; the untested tools (get_publication_history, search_construction_codes, find_procurement_office) could regress without a failing test.

### Remediation

Add unit tests for the three uncovered tools and a few more edge cases per tool (empty results, cache hit, code-object normalisation), and add a live test per remaining tool.

### Effort Estimate

M
