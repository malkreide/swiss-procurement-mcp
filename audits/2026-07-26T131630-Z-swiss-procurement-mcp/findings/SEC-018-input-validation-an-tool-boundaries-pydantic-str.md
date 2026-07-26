## Finding: SEC-018 — Input-Validation an Tool-Boundaries (Pydantic strict / Zod)

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `SEC-018` |
| **PDF-Reference** | Sec 3 / Sec 4 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

Enum-like inputs (canton, process_type, pub_type, system, language) are validated against fixed allow-lists and rejected with actionable errors, and edge-case tests exist — but numeric `limit` params are unbounded (no ge/le), free-text params have no min/max length or pattern, and Pydantic `strict=True` / `extra='forbid'` are not set.

### Expected Behavior

Every tool boundary should bound its inputs: numeric ranges (ge/le), string length/pattern limits, and strict typing, so malformed or abusive inputs fail fast.

### Evidence

- `src/swiss_procurement_mcp/server.py:125-130,194,362-365 — canton/process_type/pub_type/system validated against fixed allow-lists (whitelist), rejected with actionable ValueError`
- `src/swiss_procurement_mcp/client.py:38-46 — language validated against SUPPORTED_LANGUAGES allow-list`
- `tests/test_tools.py:32-42 — edge-case tests for rejected ISO canton code and invalid pub_type`

### Gaps

- Numeric limit params (search_cpv_codes, search_construction_codes, find_procurement_office) have no ge/le bounds — unbounded
- Free-text string params (query, name_contains) have no min_length/max_length/pattern; Pydantic strict=True and extra='forbid' are not set; no tests for over-long strings / out-of-range numbers

### Risk Description

Low. Upstream simap.ch bounds the actual query, but an unbounded `limit` or a very long free-text string is passed through without a local guard and is untested.

### Remediation

Add `ge=1, le=100` (or similar) to the `limit` params and `max_length` to `query`/`name_contains`; add a couple of tests for over-long strings and out-of-range numbers. Consider Pydantic input models with `extra='forbid'`.

### Effort Estimate

S
