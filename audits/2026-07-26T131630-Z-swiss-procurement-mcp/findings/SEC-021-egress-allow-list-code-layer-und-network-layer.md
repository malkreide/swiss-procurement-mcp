## Finding: SEC-021 — Egress-Allow-List: Code-Layer und Network-Layer

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `SEC-021` |
| **PDF-Reference** | Anhang B5 + B12 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

Egress is hardcoded to a single HTTPS host (SIMAP_BASE) that no user input can redirect — effectively a one-host allow-list, tighter than a general allow-list — and the posture is documented in SECURITY.md. What is missing is an explicit code-layer guard and a network-layer control.

### Expected Behavior

The catalogue wants an explicit egress allow-list enforced at the code layer (a checked frozenset / assert_host_allowed) and, where deployed, a network-layer egress policy, plus a documented update procedure.

### Evidence

- `src/swiss_procurement_mcp/constants.py:12 — egress is hardcoded to a single HTTPS host (SIMAP_BASE); no user input can redirect the host, effectively a one-host allow-list`
- `SECURITY.md:26-29 — egress posture documented (single hard-coded HTTPS base URL, caller never supplies a host)`

### Gaps

- No explicit frozenset allow-list + assert_host_allowed pre-request guard (relies on hardcoding instead)
- No network-layer egress control (NetworkPolicy/SG) and no docs/network-egress.md with an update procedure

### Risk Description

Low. Because the host is hardcoded and not user-influenced, the practical SSRF/exfiltration surface is already closed; the gap is an explicit, testable guard rather than an implicit one.

### Remediation

Add a small `assert_host_allowed` check (frozenset of allowed hosts) before each request as an explicit, testable invariant, and a `docs/network-egress.md` noting the single allowed host and how to change it. Add a NetworkPolicy only for a future cloud deployment.

### Effort Estimate

S
