## Finding: CH-004 — OGD-CH Lizenz-Compliance: CC BY 4.0 Attribution

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `CH-004` |
| **PDF-Reference** | Custom (OGD-CH-Richtlinien) |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

The ATTRIBUTION constant names the source (simap.ch), operator (simap.ch association) and API version, every response carries source/provenance/retrieved_at, and the README Credits section links the data source — but no explicit data licence is named.

### Expected Behavior

OGD-CH attribution should name source, author/operator, licence and (where applicable) modification, so downstream consumers know the reuse terms.

### Evidence

- `src/swiss_procurement_mcp/constants.py:21-25 — ATTRIBUTION names source (simap.ch), operator (simap.ch association) and API version`
- `src/swiss_procurement_mcp/models.py:12-16 — every response Envelope carries source + provenance + retrieved_at (per-response provenance)`
- `README.md:209-214 — Credits section documents the simap.ch data source and API docs link`

### Gaps

- Attribution text does not name an explicit data license (e.g. CC BY 4.0 with author/source/license/modification); only source+operator+version are cited

### Risk Description

Low. Attribution is substantially present; only the explicit licence label is missing, which could matter for strict OGD reuse-compliance.

### Remediation

Add the applicable licence to the ATTRIBUTION text and README Credits (confirm simap.ch's terms; if it is opendata.swiss-style, cite the licence and 'source: simap.ch'). Text-only change.

### Effort Estimate

S
