## Finding: SEC-007 — Container-Sandboxing: Docker / chroot mit minimalen Privilegien

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** SEC-007
**PDF-Reference:** Sec 4.5

### Observed Behavior

- Deployment profile is local-stdio; no container is shipped

### Expected Behavior

See the Pass Criteria of `SEC-007` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No Dockerfile at all, so none of the sandboxing criteria can be met. The companion amtsblatt-mcp ships a hardened non-root multi-stage image that could be adopted

### Remediation

Port the hardened Dockerfile and compose.yaml from amtsblatt-mcp: multi-stage build, non-root USER, read-only root filesystem, memory/CPU/PID limits.

### Effort Estimate

M
