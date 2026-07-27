# MCP-Server Audit-Report — `swiss-procurement-mcp`

**Audit-Datum:** 
**Skill-Version:** ?
**Catalog-Version:** ?

---

## 1. Executive Summary

Server `swiss-procurement-mcp` wurde gegen 32 anwendbare Best-Practice-Checks geprüft. 21 bestanden, 11 Findings dokumentiert (1 critical, 6 high, 4 medium, 0 low). Production-Readiness: erreicht.

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
| OBS | 2 | 0 | 2 | 0 | 0 |
| OPS | 1 | 0 | 2 | 0 | 0 |
| SCALE | 0 | 0 | 1 | 0 | 0 |
| SEC | 10 | 0 | 2 | 0 | 0 |
| **Total** | **21** | **0** | **11** | **0** | **0** |

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
| ARCH-003 | ARCH | medium | partial |
| ARCH-008 | ARCH | medium | partial |
| ARCH-012 | ARCH | medium | partial |
| OBS-003 | OBS | medium | partial |

**Gesamt:** 11 Findings

---

## 5. Detail-Findings

### ARCH-003

## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-07-27 |
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
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `ARCH-008` |
| **PDF-Reference** | Anhang A2 |
| **Audit-Datum** | 2026-07-27 |
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
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `ARCH-009` |
| **PDF-Reference** | Anhang A5 |
| **Audit-Datum** | 2026-07-27 |
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
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `ARCH-012` |
| **PDF-Reference** | Anhang A9 |
| **Audit-Datum** | 2026-07-27 |
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
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 6.2 |
| **Audit-Datum** | 2026-07-27 |
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


### OBS-003

## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 6.3 |
| **Audit-Datum** | 2026-07-27 |
| **Auditor** | mcp-audit v1.0.0 (catalog 091f446b…) |

### Observed Behavior

- Structured JSON to stderr with a custom formatter (_log.py:28-41)
- One tool_call record per call with tool/status/latency_ms on all 9 tools (_log.py:59-88, server.py decorators)
- No print() anywhere in src/
- upstream_degraded at WARNING carrying the exception type only (server.py:79-87)

### Expected Behavior

See the Pass Criteria of `OBS-003` in the check catalogue (catalog_hash 091f446b…).

### Evidence / Gaps

- No structured-logging dependency (structlog/loguru): stdlib logging with a hand-rolled JSON formatter. Achieves structured output, but the criterion names a library in `dependencies` and pyproject.toml lists none.
- Only 2 severity levels actively used (INFO, WARNING); the criterion asks for at least 4 (debug, info, warning, error).
- Per-call context carries tool/status/latency but no session_id or correlation_id, so records from concurrent sessions cannot be grouped.

### Effort Estimate

S


### OPS-001

## Finding: OPS-001 — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `OPS-001` |
| **PDF-Reference** | Anhang C1 |
| **Audit-Datum** | 2026-07-27 |
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
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `OPS-003` |
| **PDF-Reference** | Anhang C4 |
| **Audit-Datum** | 2026-07-27 |
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
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `SCALE-002` |
| **PDF-Reference** | Sec 5.2 |
| **Audit-Datum** | 2026-07-27 |
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


### SEC-007

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


### SEC-009

## Finding: SEC-009 — Session-ID Cryptographic Binding (user_id:session_id)

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Status** | open |
| **Server** | `swiss-procurement-mcp` v0.6.0 |
| **Check-Reference** | `SEC-009` |
| **PDF-Reference** | Sec 4.6 |
| **Audit-Datum** | 2026-07-27 |
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
7. **SEC-007** (high, partial)
8. **ARCH-003** (medium, partial)
9. **ARCH-008** (medium, partial)
10. **ARCH-012** (medium, partial)
11. **OBS-003** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|


_Generated by tools/build_report.py — do not edit by hand._

---

## Re-Audit-Delta gegenüber 2026-07-27T150925-Z

Gleicher `catalog_hash` (`091f446b…`), gleiche 32 anwendbare Checks, gleiches
Profil (`deployment: [local-stdio]`, `is_cloud_deployed: false`). Jede Differenz
ist Code, nicht Katalog.

| | Vorlauf (v0.4.0) | Dieser Lauf (v0.6.0) |
|---|---|---|
| pass | 20 | **21** |
| partial | 11 | 11 |
| fail | 1 | **0** |

### Geschlossen

**SEC-018 `partial` → `pass`.** Neun strikte Pydantic-Inputmodelle mit
`strict=True` und `extra="forbid"`; Grenzen, Allow-Lists und Whitelist-Patterns
deklarativ im Schema statt imperativ im Tool-Körper. Alle sieben Pass-Kriterien
erfüllt, inklusive Edge-Case-Tests gegen unbekannte Felder.

### Verbessert, aber nicht bestanden

**OBS-003 `fail` → `partial`.** Der Server hat jetzt strukturiertes Logging, wo
er vorher gar keines hatte. Zwei Kriterien bleiben offen:

- Es fehlt eine Structured-Logging-Abhängigkeit. `pyproject.toml` listet weder
  `structlog` noch `loguru`; die Implementierung ist stdlib-`logging` mit
  handgeschriebenem JSON-Formatter. Das Ergebnis ist strukturiert, das Kriterium
  nennt aber ausdrücklich eine Library in `dependencies`.
- Aktiv genutzt werden **zwei** Severity-Stufen (INFO, WARNING). Gefordert sind
  mindestens vier.
- Der Per-Call-Kontext trägt `tool`/`status`/`latency_ms`, aber keine
  `session_id` oder `correlation_id`.

**SEC-007 bleibt `partial`.** Der Container erfüllt fünf Kriterien
(non-root, read-only Root-FS, `cap_drop: [ALL]`, `no-new-privileges`,
Resource-Limits), verfehlt aber zwei:

- `useradd --system` vergibt eine UID aus dem System-Bereich (100–999 auf
  Debian). Das Kriterium verlangt eine non-root-UID **≥ 10000**; ein explizites
  `--uid` ist nicht gesetzt.
- Kein seccomp-Profil deklariert. Docker wendet sein Default-Profil an, das
  Kriterium will `RuntimeDefault` jedoch benannt sehen.

Beide Lücken sind Aufwand S.

### Korrektur einer früheren Schätzung

Vor diesem Lauf war 23 pass / 9 partial / 0 fail *abgeleitet* worden, unter der
Annahme, OBS-003 und SEC-007 seien mit den Releases v0.5.0/v0.6.0 vollständig
geschlossen. Gegen die Pass-Kriterien geprüft trifft das für beide nicht zu.
Die gemessene Zahl ist **21 / 11 / 0**. Die Ableitung war zu optimistisch —
genau deshalb war der Re-Audit nötig.
