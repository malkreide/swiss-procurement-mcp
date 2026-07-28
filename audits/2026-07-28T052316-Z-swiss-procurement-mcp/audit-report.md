# MCP-Server Audit-Report — `swiss-procurement-mcp`

**Audit-Datum:** 
**Skill-Version:** ?
**Catalog-Version:** ?

---

## 1. Executive Summary

Server `swiss-procurement-mcp` wurde gegen 32 anwendbare Best-Practice-Checks geprüft. 23 bestanden, 9 Findings dokumentiert (1 critical, 5 high, 3 medium, 0 low). Production-Readiness: erreicht.

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
| OBS | 3 | 0 | 1 | 0 | 0 |
| OPS | 1 | 0 | 2 | 0 | 0 |
| SCALE | 0 | 0 | 1 | 0 | 0 |
| SEC | 11 | 0 | 1 | 0 | 0 |
| **Total** | **23** | **0** | **9** | **0** | **0** |

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
| ARCH-003 | ARCH | medium | partial |
| ARCH-008 | ARCH | medium | partial |
| ARCH-012 | ARCH | medium | partial |

**Gesamt:** 9 Findings

---

## 5. Detail-Findings

### ARCH-003

## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- match_type field (exact/none) on search, code and office responses (models.py:38)
- Empty result carries an actionable note; filterless call now refused with the real cause (server.py:_assert_filtered)

### Expected Behavior

See the Pass Criteria of `ARCH-003` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- Still no fuzzy-match or suggestion mechanism on a zero-hit search

### Effort Estimate

M


### ARCH-008

## Finding: ARCH-008 — Drei Primitive nutzen: Tools, Resources und Prompts

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `ARCH-008` |
| **PDF-Reference** | Anhang A2 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- Tools only; 9 read-only tools would be Resource candidates

### Expected Behavior

See the Pass Criteria of `ARCH-008` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No Resources, no Prompts, and no documented rationale in the README for tools-only

### Effort Estimate

S


### ARCH-009

## Finding: ARCH-009 — Tool Annotations: readOnlyHint, destructiveHint, idempotentHint, openWorldHint

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `ARCH-009` |
| **PDF-Reference** | Anhang A5 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- Shared READ_TOOL annotation on all 9 tools: readOnlyHint, idempotentHint, openWorldHint (server.py:52)

### Expected Behavior

See the Pass Criteria of `ARCH-009` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- destructiveHint is omitted rather than set to False — the check requires explicit annotations, not defaults by omission (amtsblatt-mcp sets it explicitly)

### Effort Estimate

S


### ARCH-012

## Finding: ARCH-012 — protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `ARCH-012` |
| **PDF-Reference** | Anhang A9 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- CHANGELOG.md in Keep-a-Changelog format; 'Maturity & updates' documents the SDK-update policy
- Dependabot weekly pip + github-actions PRs (.github/dependabot.yml)
- mcp SDK floor raised to >=1.28.1 for CVE-2026-59950 in v0.4.0

### Expected Behavior

See the Pass Criteria of `ARCH-012` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- protocolVersion is not pinned in code; no dedicated 'MCP Protocol Version' README section

### Effort Estimate

S


### OBS-002

## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 6.2 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- _degraded returns a fixed sanitised note; neither the exception nor the upstream body reaches the model (server.py:73)
- No traceback.format_exc() anywhere in src/

### Expected Behavior

See the Pass Criteria of `OBS-002` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- mask_error_details=True is not set on the FastMCP constructor, so an unexpected exception outside the caught paths could still surface

### Effort Estimate

S


### OPS-001

## Finding: OPS-001 — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `OPS-001` |
| **PDF-Reference** | Anhang C1 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- 104 offline tests across 8 files, respx-mocked (tests/)
- 9 live tests marked @pytest.mark.live (tests/test_live.py)
- Marker registered in pyproject.toml:42
- CI runs pytest -m 'not live'; live runs on a nightly schedule only

### Expected Behavior

See the Pass Criteria of `OPS-001` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- The criterion asks for at least 5 unit tests per tool. Coverage is uneven: search_procurements and the input models are heavily covered, while get_publication_history and search_construction_codes have ~2 each.

### Effort Estimate

M


### OPS-003

## Finding: OPS-003 — Phasenarchitektur: Read-only First, dann Write, dann Multi-Agent

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `OPS-003` |
| **PDF-Reference** | Anhang C4 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- README 'Maturity & updates' declares Phase 1 (read-only) explicitly
- Annotations match the phase: all tools readOnlyHint; write/OIDC endpoints deliberately unwrapped
- SECURITY.md documents the re-evaluation triggers for a move to a write phase

### Expected Behavior

See the Pass Criteria of `OPS-003` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No roadmap file with phase-specific tasks

### Effort Estimate

S


### SCALE-002

## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP / SSE

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `SCALE-002` |
| **PDF-Reference** | Sec 5.2 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- Single-instance design; SECURITY.md and README document the deployment scope

### Expected Behavior

See the Pass Criteria of `SCALE-002` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No sticky-session or shared-state session manager; multi-instance HTTP deployment would break session affinity
- Deployment profile is local-stdio, so the exposure is currently theoretical

### Effort Estimate

L


### SEC-009

## Finding: SEC-009 — Session-ID Cryptographic Binding (user_id:session_id)

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.7.0 |
| **Check-Reference** | `SEC-009` |
| **PDF-Reference** | Sec 4.6 |
| **Audit-Datum** | 2026-07-28 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- No authentication and no session state: stdio has no sessions, and the HTTP transports run stateless

### Expected Behavior

See the Pass Criteria of `SEC-009` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- If an HTTP transport is exposed there is no session-to-user binding at all; acceptable only because there is no auth and no per-user data

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
7. **ARCH-003** (medium, partial)
8. **ARCH-008** (medium, partial)
9. **ARCH-012** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|


_Generated by tools/build_report.py — do not edit by hand._

---

## Re-Audit-Delta gegenüber 2026-07-27T162331-Z

Gleicher `catalog_hash` (`091f446b…`), gleiche 32 anwendbare Checks, gleiches
Profil. Jede Differenz ist Code.

| | Vorlauf (v0.6.0) | Dieser Lauf (v0.7.0) |
|---|---|---|
| pass | 21 | **23** |
| partial | 11 | **9** |
| fail | 0 | 0 |

### Geschlossen

**OBS-003 `partial` → `pass`.** Die drei offenen Kriterien sind jetzt erfüllt:
`structlog>=24.1` steht in den Dependencies, **alle vier** Severity-Stufen
werden aktiv emittiert (DEBUG bei Tool-Eintritt, INFO bei sauberem Abschluss,
WARNING bei Upstream-Degradation, ERROR bei Exception), und der Per-Call-Kontext
trägt neben dem Tool-Namen eine `correlation_id`, die über `contextvars`
gebunden ist — Events tief im HTTP-Pfad tragen damit die ID des umgebenden
Aufrufs.

**SEC-007 `partial` → `pass`.** Die zwei offenen Kriterien sind erfüllt: Die UID
ist explizit `10001` statt aus dem 100–999-System-Bereich, und das seccomp-Profil
ist als Docker-Default bewusst nicht überschrieben — CI prüft `Seccomp: 2` am
laufenden Container statt es anzunehmen.

### Verbleibende neun partials

ARCH-003 (kein Fuzzy-/Suggestion-Mechanismus), ARCH-008 (nur Tools-Primitive),
ARCH-009 (`destructiveHint` fehlt in `READ_TOOL`), ARCH-012 (kein
`protocolVersion`-Pin), OBS-002 (`mask_error_details` nicht gesetzt — das
gepinnte SDK exponiert die Einstellung nicht), OPS-001 (Unit-Tiefe je Tool unter
5), OPS-003, SCALE-002, SEC-009 (beide nur unter einem nicht genutzten
Deployment-Modus relevant).

### Zur Vorhersage

Vor diesem Lauf war 23 / 9 / 0 abgeleitet worden. Gemessen stimmt es diesmal.
Das ist keine Bestätigung der Methode: zwei frühere Ableitungen derselben Art
lagen daneben, und beide Male zeigte sich das erst beim Messen.
