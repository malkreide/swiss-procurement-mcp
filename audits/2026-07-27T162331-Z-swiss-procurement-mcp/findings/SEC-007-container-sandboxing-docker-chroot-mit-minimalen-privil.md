## Finding: SEC-007 — Container-Sandboxing: Docker / chroot mit minimalen Privilegien

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `SEC-007` |
| **PDF-Reference** | Sec 4.5 |
| **Audit-Datum** | 2026-07-27 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- Multi-stage Dockerfile, runtime stage ships only the venv (Dockerfile:1-40)
- Non-root USER mcp (Dockerfile:29-35)
- compose: read_only=true, cap_drop [ALL], no-new-privileges (compose.yaml:16-18)
- Resource limits mem 256m / cpus 0.5 / pids 128 (compose.yaml:20-22)
- CI asserts non-root uid and import under --read-only --cap-drop ALL (.github/workflows/ci.yml)

### Expected Behavior

See the Pass Criteria of `SEC-007` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- `useradd --system` assigns a UID from the system range (100-999 on Debian); the criterion requires a non-root UID >= 10000. No explicit --uid is set.
- No seccomp profile declared. Docker applies its default profile, but the criterion asks for RuntimeDefault to be stated rather than implied.

### Effort Estimate

S
