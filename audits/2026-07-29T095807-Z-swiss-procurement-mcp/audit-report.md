# MCP-Server Audit-Report — `<server>`

**Audit-Datum:** 
**Skill-Version:** ?
**Catalog-Version:** ?

---

## 1. Executive Summary

Server `<server>` wurde gegen 36 anwendbare Best-Practice-Checks geprüft. 29 bestanden, 7 Findings dokumentiert (1 critical, 3 high, 3 medium, 0 low). Production-Readiness: NICHT erreicht — blockierend: SCALE-002, SEC-009.

**Production-Readiness:** NO

---

## 2. Profil-Snapshot

| Feld | Wert |
|---|---|
| Server-Name | `?` |
| Audit-Datum | ? |
| Skill-Version | ? |
| Catalog-Version | ? |

---

## 3. Applicability

### Status pro Kategorie

| Kategorie | Pass | Fail | Partial | Todo | N/A |
|---|---|---|---|---|---|
| architecture | 9 | 0 | 2 | 0 | 0 |
| compliance | 1 | 0 | 0 | 0 | 0 |
| observability | 2 | 0 | 2 | 0 | 0 |
| operations | 3 | 0 | 0 | 0 | 0 |
| scalability | 0 | 1 | 0 | 0 | 0 |
| sdk | 3 | 0 | 1 | 0 | 0 |
| security | 11 | 1 | 0 | 0 | 0 |
| **Total** | **29** | **2** | **5** | **0** | **0** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| SEC-009 | security | critical | fail |
| OBS-001 | observability | high | partial |
| OBS-002 | observability | high | partial |
| SCALE-002 | scalability | high | fail |
| ARCH-003 | architecture | medium | partial |
| ARCH-011 | architecture | medium | partial |
| SDK-003 | sdk | medium | partial |

**Gesamt:** 7 Findings

---

## 5. Detail-Findings

### ARCH-003

## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

**Severity:** medium
**Status:** partial
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-003
**Category:** ARCH
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (1 Evidenzpunkte).

- match_type-Feld (exact/none) in models.py, 4 Fundstellen

### Expected Behavior

Alle Pass-Kriterien von ARCH-003 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- Kein Fuzzy-/Suggestion-Mechanismus bei leerem Ergebnis — bewusste offene Design-Entscheidung, in ROADMAP.md begründet

### Effort Estimate

M


### ARCH-011

## Finding: ARCH-011 — Standardisierte Repo-Struktur (src-Layout, tests, README.de.md)

**Severity:** medium
**Status:** partial
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-011
**Category:** ARCH
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 Evidenzpunkte).

- Module getrennt: _net, _cors, _log, client, constants, inputs, models
- server.py 824 Zeilen

### Expected Behavior

Alle Pass-Kriterien von ARCH-011 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- Kein tools/-Package — alle 9 Handler in server.py. Refactor mit Regressionsrisiko, bewusst zurückgestellt

### Effort Estimate

L


### OBS-001

## Finding: OBS-001 — Protocol vs. Execution Errors: korrekte Trennung

**Severity:** high
**Status:** partial
**Server:** swiss-procurement-mcp
**Check-Reference:** OBS-001
**Category:** OBS
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (3 Evidenzpunkte).

- Protokollfehler tragen jetzt echte JSON-RPC-Codes: -32602 (resources/read), -32603 (prompts/get) — an mcp 2.0.0 gemessen
- tests/test_error_paths.py deckt beide Pfade ueber einen echten Client ab (11 Tests)
- Argument- und Extra-Field-Fehler kommen als tool-result mit is_error=true

### Expected Behavior

Alle Pass-Kriterien von OBS-001 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- Upstream-Ausfall kommt als normales Ergebnis mit provenance='degraded' statt is_error=true — dokumentierte, begruendete Abweichung
- Unbekanntes Tool wird als tool-result statt als Protokollfehler geliefert (SDK-Verhalten, oberhalb der Tool-Schicht)

### Effort Estimate

M


### OBS-002

## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

**Severity:** high
**Status:** partial
**Server:** swiss-procurement-mcp
**Check-Reference:** OBS-002
**Category:** OBS
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (3 Evidenzpunkte).

- Keine Tracebacks/Pfade in Tool-Results, per Test abgesichert (test_execution_error_carries_no_stack_trace)
- Upstream-4xx-Bodies auf 300 Zeichen gekuerzt
- prompts/get antwortet unter 2.0 mit 'Internal server error' statt rohem ValueError

### Expected Behavior

Alle Pass-Kriterien von OBS-002 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- mask_error_details existiert in mcp 2.0.0 nicht — Einstellung nicht setzbar, an 2.0.0 erneut geprueft

### Effort Estimate

S


### SCALE-002

## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP / SSE

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SCALE-002
**Category:** SCALE
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **fail** (2 Evidenzpunkte).

- docs/load-balancing.md mit nginx- und K8s-Ingress-Konfiguration auf Mcp-Session-Id
- MCP_STATELESS=1 entfernt Session-Affinitaet als Frage

### Expected Behavior

Alle Pass-Kriterien von SCALE-002 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- Kein Sticky-LB und kein Shared-State-Session-Manager tatsaechlich deployed
- Kein expliziter Session-TTL setzbar: session_idle_timeout wird von MCPServer nicht durchgereicht (an mcp 2.0.0 erneut geprueft)

### Effort Estimate

L


### SDK-003

## Finding: SDK-003 — Context Injection für Progress Reports und Logging

**Severity:** medium
**Status:** partial
**Server:** swiss-procurement-mcp
**Check-Reference:** SDK-003
**Category:** SDK
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (1 Evidenzpunkte).

- Kein Tool laeuft laenger als Millisekunden; Progress waere ohne Aussage

### Expected Behavior

Alle Pass-Kriterien von SDK-003 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- Kein ctx: Context-Parameter — bewusst nicht geplant, in ROADMAP.md begruendet

### Effort Estimate

M


### SEC-009

## Finding: SEC-009 — Session-ID Cryptographic Binding (user_id:session_id)

**Severity:** critical
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SEC-009
**Category:** SEC
**Audit-Run:** 2026-07-29T095807-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **fail** (2 Evidenzpunkte).

- Serverseitige Invalidierung ueber DELETE am streamable-http-Endpunkt
- MCP_STATELESS=1 entfernt Session-Tracking vollstaendig

### Expected Behavior

Alle Pass-Kriterien von SEC-009 erfuellt. Siehe den mcp-audit-Katalog
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- Keine Authentifizierung, kein OAuth-sub-Claim — es gibt keine Identitaet zum Binden
- Kein expliziter Session-TTL setzbar
- SDK-Session-IDs tragen 122 statt 128 Zufallsbits

### Effort Estimate

XL


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **SEC-009** (critical, fail)
2. **OBS-001** (high, partial)
3. **OBS-002** (high, partial)
4. **SCALE-002** (high, fail)
5. **ARCH-003** (medium, partial)
6. **ARCH-011** (medium, partial)
7. **SDK-003** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|


_Generated by tools/build_report.py — do not edit by hand._
