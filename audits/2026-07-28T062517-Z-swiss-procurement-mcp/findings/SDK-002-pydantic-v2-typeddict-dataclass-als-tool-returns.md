## Finding: SDK-002 — Pydantic v2 / TypedDict / Dataclass als Tool-Returns

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SDK-002
**Category:** SDK
**Audit-Run:** 2026-07-28T062517-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (3 evidence points collected).

- pydantic>=2.7 in dependencies
- All 9 tools have explicit BaseModel return annotations
- Envelope carries source, provenance, retrieved_at

### Expected Behavior

All pass criteria of SDK-002 satisfied. See `checks/SDK-002` in the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- match_type typed as str, not Literal['exact','none'] (models.py:38,68,85,100)

### Evaluator Notes

(none)

### Effort Estimate

S
