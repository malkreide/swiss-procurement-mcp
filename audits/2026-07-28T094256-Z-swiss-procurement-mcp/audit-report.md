# MCP-Server Audit-Report — `<server>`

**Audit-Datum:** 
**Skill-Version:** ?
**Catalog-Version:** ?

---

## 1. Executive Summary

Server `<server>` wurde gegen 36 anwendbare Best-Practice-Checks geprüft. 19 bestanden, 17 Findings dokumentiert (3 critical, 7 high, 7 medium, 0 low). Production-Readiness: NICHT erreicht — blockierend: SCALE-002, SEC-009.

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
| ARCH | 5 | 0 | 6 | 0 | 0 |
| CH | 1 | 0 | 0 | 0 | 0 |
| OBS | 2 | 0 | 2 | 0 | 0 |
| OPS | 1 | 0 | 2 | 0 | 0 |
| SCALE | 0 | 1 | 0 | 0 | 0 |
| SDK | 2 | 0 | 2 | 0 | 0 |
| SEC | 8 | 1 | 3 | 0 | 0 |
| **Total** | **19** | **2** | **15** | **0** | **0** |

---

## 4. Findings-Übersicht

_Policy: `fail-or-partial`_

| ID | Category | Severity | Status |
|---|---|---|---|
| ARCH-005 | ARCH | critical | partial |
| SEC-004 | SEC | critical | partial |
| SEC-009 | SEC | critical | fail |
| ARCH-004 | ARCH | high | partial |
| OBS-001 | OBS | high | partial |
| OBS-002 | OBS | high | partial |
| OPS-003 | OPS | high | partial |
| SCALE-002 | SCALE | high | fail |
| SEC-005 | SEC | high | partial |
| SEC-013 | SEC | high | partial |
| ARCH-002 | ARCH | medium | partial |
| ARCH-003 | ARCH | medium | partial |
| ARCH-011 | ARCH | medium | partial |
| ARCH-012 | ARCH | medium | partial |
| OPS-002 | OPS | medium | partial |
| SDK-002 | SDK | medium | partial |
| SDK-003 | SDK | medium | partial |

**Gesamt:** 17 Findings

---

## 5. Detail-Findings

### ARCH-002

## Finding: ARCH-002 — Tool-Beschreibung mit Use-Case-Tags

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-002
**Category:** ARCH
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (3 evidence points).

- Median description length 319 chars, >=100 required
- search_procurements (1910) vs search_procurements_detailed (990) differentiate explicitly

### Expected Behavior

All pass criteria of ARCH-002 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No <use_case> tag in any of 9 tools (0%, >=80% required)
- source_status description is 57 chars, below the 100-char floor

### Evaluator Notes

(none)

### Effort Estimate

S


### ARCH-003

## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-003
**Category:** ARCH
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points).

- match_type field present on all 6 search-style responses (server.py:427,505,566,666,708,766)
- Envelope carries an optional `note` field

### Expected Behavior

All pass criteria of ARCH-003 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- match_type only ever takes exact|none — no fuzzy match implemented
- Empty result carries no suggestions and no actionable hint

### Evaluator Notes

The field exists but the heuristic behind it does not.

### Effort Estimate

S


### ARCH-004

## Finding: ARCH-004 — Inversion of Control: Transport-agnostische Server-Logik

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-004
**Category:** ARCH
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (3 evidence points).

- Transport selected by MCP_TRANSPORT env var, stdio default (__main__.py)
- Outputs transport-independent
- Lifespan is now shared across transports (server.py:66) — was absent at the previous run

### Expected Behavior

All pass criteria of ARCH-004 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No tool uses ctx: Context
- Config read via os.environ at module scope, not a Settings object

### Evaluator Notes

Improved by the SDK-001 work: 3 of 5 criteria now met, previously 2.

### Effort Estimate

M


### ARCH-005

## Finding: ARCH-005 — Keine Hardcoded Secrets: Env-Vars / Secret Manager only

**Severity:** critical
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-005
**Category:** ARCH
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (5 evidence points).

- No secrets in source; server has no auth model at all
- .gitignore excludes .env (line 6)
- gitleaks runs on PRs (.github/workflows/security.yml:11)
- tests/test_secrets.py present in sister server pattern

### Expected Behavior

All pass criteria of ARCH-005 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No .env.example in the repo

### Evaluator Notes

Nothing to leak, but the required placeholder file is absent.

### Effort Estimate

M


### ARCH-011

## Finding: ARCH-011 — Standardisierte Repo-Struktur (src-Layout, tests, README.de.md)

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-011
**Category:** ARCH
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (4 evidence points).

- All mandatory top-level files present
- src/ layout correct, tests/ and .github/workflows/ present
- ci.yml + publish.yml both present
- README.de.md parallel

### Expected Behavior

All pass criteria of ARCH-011 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- 9 tools (>5) but no tools/ directory split — server.py holds all handlers
- No README justification for the deviation

### Evaluator Notes

(none)

### Effort Estimate

S


### ARCH-012

## Finding: ARCH-012 — protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** ARCH-012
**Category:** ARCH
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (4 evidence points).

- MCP_PROTOCOL_VERSION = '2025-11-25' pinned (server.py)
- CHANGELOG.md in Keep-a-Changelog format
- README:236 'MCP Protocol Version' section present
- Dependabot active (.github/dependabot.yml)

### Expected Behavior

All pass criteria of ARCH-012 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- README:355 contradicts README:236 — claims the version is 'negotiated by the pinned mcp SDK' when it is an explicit constant

### Evaluator Notes

Stale sentence left behind by the ARCH-012 work.

### Effort Estimate

S


### OBS-001

## Finding: OBS-001 — Protocol vs. Execution Errors: korrekte Trennung

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** OBS-001
**Category:** OBS
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points).

- Argument errors raise ValueError, surfaced by FastMCP as tool errors
- Degraded-mode envelope tested in test_tool_coverage.py

### Expected Behavior

All pass criteria of OBS-001 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No explicit isError construction or documented -326xx/-320xx protocol codes
- No test distinguishes the protocol-error path from the execution-error path

### Evaluator Notes

(none)

### Effort Estimate

M


### OBS-002

## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** OBS-002
**Category:** OBS
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points).

- No traceback.format_exc() or sys.exc_info() anywhere in src/
- Upstream error bodies are not echoed — test_details_degraded_note_leaks_no_upstream_body asserts it

### Expected Behavior

All pass criteria of OBS-002 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- FastMCP is constructed without mask_error_details=True (server.py:62)

### Evaluator Notes

Criterion 1 is literally unmet; the substance it protects is covered by tests.

### Effort Estimate

M


### OPS-002

## Finding: OPS-002 — Doku-Standard: bilingualer README, ASCII-Diagramm, Limits-Sektion

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** OPS-002
**Category:** OPS
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (5 evidence points).

- All 8 mandatory sections present in README.md
- Anchor demo query concrete and natural-language (README:21)
- ASCII/Mermaid diagram present
- Known limitations section explicit (README:310)
- CONTRIBUTING.md + CONTRIBUTING.de.md bilingual

### Expected Behavior

All pass criteria of OPS-002 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- README.de.md has 17 top-level sections against README.md's 19

### Evaluator Notes

(none)

### Effort Estimate

S


### OPS-003

## Finding: OPS-003 — Phasenarchitektur: Read-only First, dann Write, dann Multi-Agent

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** OPS-003
**Category:** OPS
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points).

- README:350 declares 'Phase 1 — read-only'
- Annotations match the declared phase (all readOnlyHint)

### Expected Behavior

All pass criteria of OPS-003 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No roadmap file with phase-specific tasks
- Phase-transition preconditions not documented

### Evaluator Notes

(none)

### Effort Estimate

M


### SCALE-002

## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP / SSE

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SCALE-002
**Category:** SCALE
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **fail** (1 evidence points).

- No sticky-session or shared-state session manager

### Expected Behavior

All pass criteria of SCALE-002 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- Neither pattern implemented
- No session TTL
- No failover test

### Evaluator Notes

Documented as an accepted risk in SECURITY.md by explicit decision — recorded here as fail because the control is absent.

### Effort Estimate

M


### SDK-002

## Finding: SDK-002 — Pydantic v2 / TypedDict / Dataclass als Tool-Returns

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SDK-002
**Category:** SDK
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (3 evidence points).

- pydantic>=2.7 in dependencies
- All 9 tools have explicit BaseModel return annotations
- Envelope carries source, provenance, retrieved_at

### Expected Behavior

All pass criteria of SDK-002 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- match_type typed as str, not Literal['exact','none'] (models.py:38,68,85,100)

### Evaluator Notes

(none)

### Effort Estimate

S


### SDK-003

## Finding: SDK-003 — Context Injection für Progress Reports und Logging

**Severity:** medium
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SDK-003
**Category:** SDK
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points).

- No tool is expected to exceed 2s — each is a single upstream call
- Errors surface as tool results, not silently swallowed

### Expected Behavior

All pass criteria of SDK-003 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No tool takes ctx: Context
- search_procurements_detailed fans out to 5 upstream calls and reports no progress

### Evaluator Notes

(none)

### Effort Estimate

S


### SEC-004

## Finding: SEC-004 — SSRF-Prevention: HTTPS-Enforcement + IP-Blocklisting

**Severity:** critical
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SEC-004
**Category:** SEC
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points).

- _assert_host_allowed() runs before every request (client.py:104,181)
- ALLOWED_HOSTS frozenset pins www.simap.ch (constants.py:17)

### Expected Behavior

All pass criteria of SEC-004 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No explicit https scheme validation before egress
- No resolved-IP blocklist — 169.254.169.254, private and link-local ranges unchecked
- No DNS pinning, so a TOCTOU rebind is possible

### Evaluator Notes

Base URL is a hardcoded https constant, which mitigates in practice but is not the control the check asks for.

### Effort Estimate

M


### SEC-005

## Finding: SEC-005 — DNS-Rebinding-Prevention: DNS-Pinning gegen TOCTOU

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SEC-005
**Category:** SEC
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (1 evidence points).

- Single httpx request per attempt; no manual resolve-then-connect split

### Expected Behavior

All pass criteria of SEC-005 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No DNS pinning implemented
- No test asserting one DNS call per request

### Evaluator Notes

(none)

### Effort Estimate

M


### SEC-009

## Finding: SEC-009 — Session-ID Cryptographic Binding (user_id:session_id)

**Severity:** critical
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SEC-009
**Category:** SEC
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **fail** (1 evidence points).

- Server maintains no session layer of its own

### Expected Behavior

All pass criteria of SEC-009 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- No session id generation, binding, TTL or invalidation

### Evaluator Notes

Documented as an accepted risk in SECURITY.md by explicit decision — recorded as fail because the control is absent.

### Effort Estimate

M


### SEC-013

## Finding: SEC-013 — API-Key-Storage: Secret Manager statt Plain-Text Env-Vars

**Severity:** high
**Status:** open
**Server:** swiss-procurement-mcp
**Check-Reference:** SEC-013
**Category:** SEC
**Audit-Run:** 2026-07-28T094256-Z-swiss-procurement-mcp

### Observed Behavior

Check status: **partial** (2 evidence points).

- Server uses no API key at all — auth_model is none
- Container image carries no secrets

### Expected Behavior

All pass criteria of SEC-013 satisfied. See the mcp-audit catalogue
(catalog_hash 091f446b27965044ce658a1d5f4b2cabe2b0ab5661dcc1a53b6be8f1f2e093c0).

### Evidence / Gaps

- docs/secret-management.md absent, which the check requires even at Stufe 1

### Evaluator Notes

(none)

### Effort Estimate

M


---

## 6. Remediation-Plan

### Empfohlene Reihenfolge

1. **ARCH-005** (critical, partial)
2. **SEC-004** (critical, partial)
3. **SEC-009** (critical, fail)
4. **ARCH-004** (high, partial)
5. **OBS-001** (high, partial)
6. **OBS-002** (high, partial)
7. **OPS-003** (high, partial)
8. **SCALE-002** (high, fail)
9. **SEC-005** (high, partial)
10. **SEC-013** (high, partial)
11. **ARCH-002** (medium, partial)
12. **ARCH-003** (medium, partial)
13. **ARCH-011** (medium, partial)
14. **ARCH-012** (medium, partial)
15. **OPS-002** (medium, partial)
16. **SDK-002** (medium, partial)
17. **SDK-003** (medium, partial)

---

## 7. Audit-Metadata

| Feld | Wert |
|---|---|


_Generated by tools/build_report.py — do not edit by hand._
