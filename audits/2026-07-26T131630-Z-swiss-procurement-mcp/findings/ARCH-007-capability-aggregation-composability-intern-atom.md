## Finding: ARCH-007 — Capability-Aggregation: Composability intern, Atomarität extern

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `ARCH-007` |
| **PDF-Reference** | Sec 2.3 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

search_awards aggregates all four award publication types into one call and documents it, but search_procurements returns summaries that require a follow-up get_procurement_details call, and there is no asyncio.gather parallelisation. The anchor demo needs three tool calls.

### Expected Behavior

Tools should return thought-complete results; where a workflow naturally spans several upstream calls, aggregate them internally (parallelised) so the model needs ≤2 calls for the anchor query.

### Evidence

- `src/swiss_procurement_mcp/server.py:197 — search_awards aggregates all four award pub-types into one upstream call`
- `src/swiss_procurement_mcp/server.py:191-192 — docstring states the aggregated character ('queries all four award publication types at once')`

### Gaps

- search_procurements returns summaries requiring a follow-up get_procurement_details call (IDs/pointers, not self-contained)
- No asyncio.gather parallelization anywhere; anchor demo needs 3 tool calls, above the <=2 target

### Risk Description

Low. More tool round-trips mean more latency and a slightly higher chance the model mis-chains, but each tool is individually correct and honest.

### Remediation

Consider an optional aggregated tool (e.g. search + auto-detail for the top N hits via asyncio.gather) for the anchor use-case, while keeping the granular tools for precise control.

### Effort Estimate

M
