# MCP-Server Audit-Report — `swiss-procurement-mcp`

**Audit-Datum:** 
**Skill-Version:** ?
**Catalog-Version:** ?

---

## 1. Executive Summary

Server `swiss-procurement-mcp` wurde gegen 32 anwendbare Best-Practice-Checks geprüft. 20 bestanden, 12 Findings dokumentiert (1 critical, 7 high, 4 medium, 0 low). Production-Readiness: erreicht.

**Production-Readiness:** YES

---

## 2. Profil-Snapshot

| Feld | Wert |
|---|---|
| Server-Name | `swiss-procurement-mcp` |
| Audit-Datum | ? |
| Skill-Version | ? |
| Catalog-Version | ? |

---

## 3. Applicability

### Status pro Kategorie

| Kategorie | Pass | Fail | Partial | Todo | N/A |
|---|---|---|---|---|---|
| ARCH | 7 | 0 | 4 | 0 | 0 |
| CH | 1 | 0 | 0 | 0 | 0 |
| OBS | 2 | 1 | 1 | 0 | 0 |
| OPS | 1 | 0 | 2 | 0 | 0 |
| SCALE | 0 | 0 | 1 | 0 | 0 |
| SEC | 9 | 0 | 3 | 0 | 0 |
| **Total** | **20** | **1** | **11** | **0** | **0** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| SEC-009 | SEC | critical | partial |
| ARCH-009 | ARCH | high | partial |
| OBS-002 | OBS | high | partial |
| OPS-001 | OPS | high | partial |
| OPS-003 | OPS | high | partial |
| SCALE-002 | SCALE | high | partial |
| SEC-007 | SEC | high | partial |
| SEC-018 | SEC | high | partial |
| ARCH-003 | ARCH | medium | partial |
| ARCH-008 | ARCH | medium | partial |
| ARCH-012 | ARCH | medium | partial |
| OBS-003 | OBS | medium | fail |

**Gesamt:** 12 Findings

---

## 5. Detail-Findings

### ARCH-003

## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** ARCH-003
**PDF-Reference:** Sec 2.2

### Observed Behavior

- match_type field (exact/none) on search, code and office responses (models.py:38)
- Empty result carries an actionable note; filterless call now refused with the real cause (server.py:_assert_filtered)

### Expected Behavior

See the Pass Criteria of `ARCH-003` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- Still no fuzzy-match or suggestion mechanism on a zero-hit search

### Remediation

Add a suggestion path for a zero-hit search: on match_type == "none", offer the nearest CPV code or a widened date range rather than only stating that nothing matched.

### Effort Estimate

M


### ARCH-008

## Finding: ARCH-008 — Drei Primitive nutzen: Tools, Resources und Prompts

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** ARCH-008
**PDF-Reference:** Anhang A2

### Observed Behavior

- Tools only; 9 read-only tools would be Resource candidates

### Expected Behavior

See the Pass Criteria of `ARCH-008` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No Resources, no Prompts, and no documented rationale in the README for tools-only

### Remediation

Either expose the stable reference data (canton list, code systems, rubric taxonomy) as Resources, or add a short README paragraph stating why this server is tools-only. The rationale is cheap and closes the check.

### Effort Estimate

S


### ARCH-009

## Finding: ARCH-009 — Tool Annotations: readOnlyHint, destructiveHint, idempotentHint, openWorldHint

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** ARCH-009
**PDF-Reference:** Anhang A5

### Observed Behavior

- Shared READ_TOOL annotation on all 9 tools: readOnlyHint, idempotentHint, openWorldHint (server.py:52)

### Expected Behavior

See the Pass Criteria of `ARCH-009` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- destructiveHint is omitted rather than set to False — the check requires explicit annotations, not defaults by omission (amtsblatt-mcp sets it explicitly)

### Remediation

Add "destructiveHint": False to the shared READ_TOOL dict. One line; the check asks for explicit annotations rather than defaults by omission.

### Effort Estimate

S


### ARCH-012

## Finding: ARCH-012 — protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** ARCH-012
**PDF-Reference:** Anhang A9

### Observed Behavior

- CHANGELOG.md in Keep-a-Changelog format; 'Maturity & updates' documents the SDK-update policy
- Dependabot weekly pip + github-actions PRs (.github/dependabot.yml)
- mcp SDK floor raised to >=1.28.1 for CVE-2026-59950 in v0.4.0

### Expected Behavior

See the Pass Criteria of `ARCH-012` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- protocolVersion is not pinned in code; no dedicated 'MCP Protocol Version' README section

### Remediation

Pin the negotiated protocolVersion explicitly in the server module and add a short "MCP Protocol Version" README section naming it.

### Effort Estimate

S


### OBS-002

## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** OBS-002
**PDF-Reference:** Sec 6.2

### Observed Behavior

- _degraded returns a fixed sanitised note; neither the exception nor the upstream body reaches the model (server.py:73)
- No traceback.format_exc() anywhere in src/

### Expected Behavior

See the Pass Criteria of `OBS-002` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- mask_error_details=True is not set on the FastMCP constructor, so an unexpected exception outside the caught paths could still surface

### Remediation

Pass mask_error_details=True to the FastMCP constructor so an unexpected exception outside the caught paths cannot surface internals.

### Effort Estimate

S


### OBS-003

## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** OBS-003
**PDF-Reference:** Sec 6.3

### Observed Behavior

- No print() in src/ (0 hits)

### Expected Behavior

See the Pass Criteria of `OBS-003` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No logger at all: no structured logging dependency, no JSON/logfmt output, no severity levels, no per-tool-call context. Only 1 of 5 criteria met
- Re-grade: the prior run recorded 'partial' for the same code; on the criteria as written this is a fail

### Remediation

Adopt the structured-logging module from the companion amtsblatt-mcp (_log.py: JSON to stderr, logged_tool decorator, per-call context). It is a direct port and closes the only failing check.

### Effort Estimate

M


### OPS-001

## Finding: OPS-001 — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** OPS-001
**PDF-Reference:** Anhang C1

### Observed Behavior

- 35 offline tests (respx-mocked) across 5 files + 10 live tests
- live marker registered in pyproject.toml; CI runs pytest -m 'not live'
- Dedicated nightly live job (cron 23 3 * * *) plus workflow_dispatch, never on PR
- v0.4.0 added drift guards: institution ids and spec enums verified against the live API

### Expected Behavior

See the Pass Criteria of `OPS-001` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- ~4 offline tests per tool, below the 5-per-tool bar

### Remediation

Raise offline coverage toward five tests per tool; get_publication_history, search_construction_codes and find_procurement_office are the thinnest.

### Effort Estimate

M


### OPS-003

## Finding: OPS-003 — Phasenarchitektur: Read-only First, dann Write, dann Multi-Agent

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** OPS-003
**PDF-Reference:** Anhang C4

### Observed Behavior

- README 'Maturity & updates' declares Phase 1 (read-only) explicitly
- Annotations match the phase: all tools readOnlyHint; write/OIDC endpoints deliberately unwrapped
- SECURITY.md documents the re-evaluation triggers for a move to a write phase

### Expected Behavior

See the Pass Criteria of `OPS-003` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No roadmap file with phase-specific tasks

### Remediation

Add a ROADMAP.md with the phase-1 scope and the documented preconditions for a phase-2 (write) transition; SECURITY.md already names the triggers.

### Effort Estimate

S


### SCALE-002

## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP / SSE

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** SCALE-002
**PDF-Reference:** Sec 5.2

### Observed Behavior

- Single-instance design; SECURITY.md and README document the deployment scope

### Expected Behavior

See the Pass Criteria of `SCALE-002` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No sticky-session or shared-state session manager; multi-instance HTTP deployment would break session affinity
- Deployment profile is local-stdio, so the exposure is currently theoretical

### Remediation

Only relevant if the server is ever deployed multi-instance over HTTP. Document the single-instance constraint in the README deployment section, or add a shared-state session manager before scaling out.

### Effort Estimate

L


### SEC-007

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


### SEC-009

## Finding: SEC-009 — Session-ID Cryptographic Binding (user_id:session_id)

**Severity:** critical
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** SEC-009
**PDF-Reference:** Sec 4.6

### Observed Behavior

- No authentication and no session state: stdio has no sessions, and the HTTP transports run stateless

### Expected Behavior

See the Pass Criteria of `SEC-009` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- If an HTTP transport is exposed there is no session-to-user binding at all; acceptable only because there is no auth and no per-user data

### Remediation

Only relevant once an HTTP transport is exposed with authentication. Until then the absence of sessions is the mitigation; revisit as part of any phase-2 transition.

### Effort Estimate

L


### SEC-018

## Finding: SEC-018 — Input-Validation an Tool-Boundaries (Pydantic strict / Zod)

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp v0.4.0
**Check-Reference:** SEC-018
**PDF-Reference:** Sec 3 / Sec 4 (Defense-in-Depth)

### Observed Behavior

- limit bounded 1..100 and free-text capped at 200 chars (server.py:_check_limit/_check_text)
- canton, process_type, pub_type, canton_match and code system validated against fixed allow-lists
- v0.4.0 added the filterless-call guard, refusing an unbounded query with its real cause

### Expected Behavior

See the Pass Criteria of `SEC-018` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- Inputs are flat keyword arguments validated imperatively; no Pydantic input models, so no strict=True / extra='forbid' and no declarative ge/le or pattern constraints

### Remediation

Move tool inputs to Pydantic models with strict=True and extra="forbid", replacing the imperative _check_limit/_check_text guards with declarative ge/le and pattern constraints. amtsblatt-mcp already does this and passes the check.

### Effort Estimate

M


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **SEC-009** (critical, partial)
2. **ARCH-009** (high, partial)
3. **OBS-002** (high, partial)
4. **OPS-001** (high, partial)
5. **OPS-003** (high, partial)
6. **SCALE-002** (high, partial)
7. **SEC-007** (high, partial)
8. **SEC-018** (high, partial)
9. **ARCH-003** (medium, partial)
10. **ARCH-008** (medium, partial)
11. **ARCH-012** (medium, partial)
12. **OBS-003** (medium, fail)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|


_Generated by tools/build_report.py — do not edit by hand._


---

## Re-Audit-Delta gegenüber `2026-07-26T131630-Z-swiss-procurement-mcp`

Beide Läufe verwenden denselben Katalog (`catalog_hash` `091f446b…`) und dieselbe
Applicability-Menge. Unterschiede stammen daher ausschliesslich aus dem Code, nicht
aus einer Katalog-Änderung.

| | Vorlauf (v0.3.0) | Dieser Lauf (v0.4.0) |
|---|---|---|
| pass | 15 | **20** |
| partial | 16 | 11 |
| fail | 1 | 1 |

**Geschlossen seit dem letzten Lauf:** ARCH-005 (gitleaks-Scan), ARCH-007 (aggregiertes
`search_procurements_detailed`), CH-004 (Attribution nennt die Nutzungsgrundlage),
SEC-019 (Trifecta-Assessment in SECURITY.md), SEC-021 (Egress-Allow-List plus
`docs/network-egress.md`), ARCH-012 von `fail` auf `partial` (Dependabot, CHANGELOG,
SDK-Floor).

**Verbessert, aber weiterhin offen:** ARCH-003 (der irreführende Leer-Hinweis ist weg,
Fuzzy-Vorschläge fehlen), OPS-001 (Live-Drift-Guards ergänzt, Testdichte pro Tool noch
unter der Vorgabe), SEC-018 (filterloser Aufruf abgewiesen, aber weiterhin keine
Pydantic-Input-Modelle).

**Neu abgestuft:** OBS-003 von `partial` auf `fail`. Der Code ist unverändert — der
Server hat schlicht kein Logging. Von fünf Kriterien ist eines erfüllt; `partial` war
im Vorlauf zu grosszügig.

