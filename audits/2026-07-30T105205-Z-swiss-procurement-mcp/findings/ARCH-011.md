## Finding: ARCH-011 — Standardisierte Repo-Struktur (src-Layout, tests, README.de.md)

**Severity:** medium
**Status:** accepted-risk
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-011
**PDF-Reference:** Anhang A8

### Observed Behavior

Five of seven criteria are met: `src`-layout, the five mandatory top-level files,
`src/` + `tests/` + `.github/workflows/`, `ci.yml` + `publish.yml`, and
`README.de.md` parallel to `README.md` (19 top-level sections each).

Two are not. The server exposes **9 tools** and has no `tools/` package — all
handlers sit in `server.py` (902 lines). And the deviation is argued in
`SECURITY.md`, while the criterion asks for it in the README.

### Expected Behavior

- "Bei > 5 Tools: `tools/`-Verzeichnis mit File-pro-Gruppe-Aufteilung"
- "Abweichungen vom Standard sind im README begründet"

### Evidence

- `src/swiss_procurement_mcp/server.py` — 902 lines, 9 `@mcp.tool` handlers.
- No `src/swiss_procurement_mcp/tools/` directory.
- Already-separate modules: `_net`, `_cors`, `_log`, `_fuzzy`, `client`,
  `constants`, `inputs`, `models`.
- `SECURITY.md` § "`ARCH-011` — a deliberate deviation, not deferred work".
- `README.md` — no deviation rationale (0 matches for the relevant terms).

### Risk Description

Low. The intent of the criterion — a codebase navigable without scrolling an
omnibus file — is substantially met at 902 lines with eight sibling modules
already extracted. The measurable gap is the literal wording plus the location of
the justification.

The case against doing the split is recorded and is not hypothetical: the
companion server's equivalent refactor (`amtsblatt-mcp` 0.21.0, 2477 → 252 lines)
introduced a defect — an extracted module captured a cache global by value, so a
tool silently reported stale state — and the full suite stayed green because no
test covered that path. It was caught by reading the diff.

### Remediation

Two independent steps; the second is cheap and should happen regardless.

1. **Move the justification into the README** (S, < 1h). The criterion looks
   there, and a reader comparing repo structure against the standard looks there
   too. `SECURITY.md` is the wrong file for a structural deviation.
2. **Split into `tools/`** (M, 1-3d) if the deviation is not accepted. Nine
   handlers, four plausible groups. Given the companion server's experience, this
   needs per-module import-time review — value-imports of mutable module state are
   the specific failure mode, and they do not surface in tests.

Revisit if `server.py` passes roughly 1500 lines.

### Effort Estimate

S (< 1d) for step 1; M (1-3d) for step 2.
