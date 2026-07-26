## Finding: SEC-009 — Session-ID Cryptographic Binding (user_id:session_id)

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | accepted-risk |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `SEC-009` |
| **PDF-Reference** | Sec 4.6 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

There is no auth model and no per-user data; the server exposes only public read data, and each tool call uses an ephemeral client with no per-user server-side session state. There is therefore no application-level cryptographic user_id:session_id binding and no explicitly-set session TTL.

### Expected Behavior

Where an OAuth identity exists, sessions should be cryptographically bound to the user and given an explicit TTL/invalidation to prevent hijacking.

### Evidence

- `src/swiss_procurement_mcp/ — no auth model; server exposes only public read data, so there is no OAuth user identity to bind a session to`
- `src/swiss_procurement_mcp/client.py:63-66 — per-call ephemeral client, no per-user server-side session state to hijack`

### Gaps

- No application-level cryptographic user_id:session_id binding (no OAuth sub-claim exists); relies on FastMCP default session handling
- No explicitly-set session TTL / server-side invalidation — low real impact because there is no per-user data, but the specific controls are absent for the SSE transport

### Risk Description

Largely inapplicable to this profile: no OAuth sub-claim exists, and there is no per-user or sensitive data behind a session to hijack. Relies on FastMCP default session handling.

### Remediation

Accepted risk for a no-auth public-read server. Implement user:session binding and explicit TTLs if an authentication model and per-user data are ever added (a documented re-evaluation trigger).

### Effort Estimate

M
