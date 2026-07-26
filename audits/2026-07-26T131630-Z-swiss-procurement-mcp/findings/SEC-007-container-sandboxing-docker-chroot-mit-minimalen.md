## Finding: SEC-007 — Container-Sandboxing: Docker / chroot mit minimalen Privilegien

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | accepted-risk |
| **Server** | `swiss-procurement-mcp` |
| **Check-Reference** | `SEC-007` |
| **PDF-Reference** | Sec 4.5 |
| **Audit-Datum** | 2026-07-26 |
| **Audit-Status** | partial |

### Observed Behavior

No Dockerfile or Kubernetes hardening (non-root USER, securityContext, readOnlyRootFilesystem, capability drop, seccomp) is shipped; the server runs as a local stdio process.

### Expected Behavior

For container deployments the catalogue wants a hardened image (minimal base, non-root, read-only FS, dropped capabilities).

### Evidence

- `SECURITY.md:42-48 — container sandboxing explicitly documented as accepted risk for a local-stdio public-data server`
- `Repo — no Dockerfile shipped (deployment is local-stdio; defense-in-depth deferred to OS user level)`

### Gaps

- No Dockerfile with non-root USER / no Kubernetes securityContext (runAsNonRoot, readOnlyRootFilesystem, capabilities.drop, seccomp) — none exist to satisfy the container hardening criteria

### Risk Description

Acceptable for a local-stdio public-data server — no write path, no secrets, no privileged operations; defense-in-depth lives at the OS user level.

### Remediation

Accepted risk — already documented in SECURITY.md. Ship a hardened, non-root container image if the deployment profile ever moves to a persistent cloud service.

### Effort Estimate

M
