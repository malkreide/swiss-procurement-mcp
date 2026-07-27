## Finding: OPS-001 — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** OPS-001
**PDF-Reference:** Anhang C1

### Observed Behavior

- 35 offline tests (respx-mocked) across 5 files + 10 live tests
- live marker registered in pyproject.toml; CI runs pytest -m 'not live'
- Dedicated nightly live job (cron 23 3 * * *) plus workflow_dispatch, never on PR
- v0.4.0 added drift guards: institution ids and spec enums verified against the live API

### Expected Behavior

See the Pass Criteria of `OPS-001` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- ~4 offline tests per tool, below the 5-per-tool bar

### Remediation

Raise offline coverage toward five tests per tool; get_publication_history, search_construction_codes and find_procurement_office are the thinnest.

### Effort Estimate

M
