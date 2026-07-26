# Sicherheitsrichtlinie & Sicherheitslage

[🇬🇧 English Version](SECURITY.md)

`swiss-procurement-mcp` ist ein rein lesender, PII-freier
Public-Open-Data-MCP-Server. Er kapselt ausschliesslich die nicht
authentifizierten Lese-Endpoints der simap.ch-API. Dieses Dokument beschreibt die
aktuelle Sicherheitslage sowie die **akzeptierten Risiken** für Kontrollen, die
für dieses Server-Profil bewusst zurückgestellt werden.

Er wurde gegen den internen MCP-Best-Practice-Katalog (die Portfolio-Methodik
`mcp-audit`, 68 Checks / 8 Kategorien) geprüft. Der jüngste Lauf
(`audits/2026-07-26T131630-Z-swiss-procurement-mcp/`) ergab **15 pass / 16
partial / 1 fail** über die 32 anwendbaren Checks — **produktionsreif, ohne
offenes Finding mit Sicherheits-Impact** (das einzige Fail, ARCH-012, ist eine
`medium`-Doku-/Tooling-Lücke; alle `critical`- und `high`-Findings sind
`partial`, d. h. weitgehend erfüllt mit dokumentiertem Rest). Die vollständigen
Berichte liegen unter `audits/`.

## Schwachstelle melden

Bitte eröffnen Sie ein privates Security Advisory im GitHub-Repository oder
kontaktieren Sie die in `README.md` genannte verantwortliche Person. Erstellen Sie
für ausnutzbare Schwachstellen **keine** öffentlichen Issues.

## Zusammenfassung der Sicherheitslage

Alle Tools **fragen** die simap.ch-Beschaffungsplattform nur ab — es gibt keinen
Schreibpfad, keine Benutzer-Authentifizierung und keine Personendaten. Bereits
umgesetzte Härtung:

| Bereich | Kontrolle |
|---|---|
| Egress | Jede Anfrage geht an eine einzige, fest verdrahtete HTTPS-Basis-URL (`https://www.simap.ch/api`, `SIMAP_BASE`); der Aufrufer gibt nie einen Host an, und jede Anfrage wird vor dem Senden gegen eine `ALLOWED_HOSTS`-Allow-List geprüft (SEC-021, siehe `docs/network-egress.md`) |
| TLS | Zertifikatsprüfung standardmässig aktiv (httpx-Standard; nie deaktiviert) |
| Transport | Standardmässig stdio — stdout für den JSON-RPC-Stream reserviert; HTTP-Transporte (`MCP_TRANSPORT=sse\|streamable-http`) binden an Loopback (`127.0.0.1`), ausser `MCP_HOST`/`HOST=0.0.0.0` wird explizit gesetzt (SEC-016) |
| Input | Pydantic-v2-Validierung für jedes Tool-Input; Kantons-IDs, Verfahrens- und Publikationstypen werden gegen feste Allow-Lists geprüft und mit umsetzbarem Fehler abgewiesen (z. B. `ZH` statt `CH-ZH`) |
| Secrets | Keine API-Keys oder Zugangsdaten — die gekapselten simap-Endpoints sind vollständig öffentlich. Das nötige Session-Cookie wird transparent vom HTTP-Client bezogen und ist kein Geheimnis |
| Fehler | Upstream-4xx-Antworten werden auf 300 Zeichen gekürzt; Netzwerkfehler liefern einen generischen `degraded`-Envelope. Es werden keine Stack-Traces an das Modell gegeben |
| Stdout | Reserviert für den JSON-RPC-Stream; der Server schreibt keine Logs nach stdout |
| Umfang | Die rund 200 schreibenden, `my/`- und OIDC-geschützten simap-Endpoints (Publikation, Einreichung) werden bewusst nicht gekapselt |
| Tests | respx-mockierte Unit-Suite bei jedem PR (3.10/3.11/3.12); Live-API-Tests auf einen Nightly-Job beschränkt |

## Audit-Findings (26.07.2026)

17 Findings wurden dokumentiert (Policy `fail-or-partial`). Keines blockierte die
Produktion. Die vollständigen Finding-Dokumente liegen unter
`audits/2026-07-26T131630-Z-swiss-procurement-mcp/findings/`.

**In 0.2.0 behoben:**

- **ARCH-012** (war fail, medium) — `.github/dependabot.yml` (pip + actions) und
  ein README-Abschnitt „Reifegrad & Updates" mit MCP-Protokoll-/SDK-Update-Policy.
- **ARCH-009** (high) — jedes Tool setzt jetzt `readOnlyHint`, `idempotentHint`
  und `openWorldHint` (gemeinsame `READ_TOOL`-Annotation).
- **SEC-018** (high) — `limit`-Parameter begrenzt (1–100) und Freitext
  längenbegrenzt (`_check_limit` / `_check_text`), mit Tests.
- **SEC-021** (high) — expliziter `_assert_host_allowed`-Guard gegen ein
  `ALLOWED_HOSTS`-frozenset vor jeder Anfrage, plus `docs/network-egress.md`.
- **SEC-019** (critical, strukturell sicher) — Lethal-Trifecta-Bewertung
  schriftlich festgehalten (siehe unten).
- **ARCH-005** (critical, keine Secrets vorhanden) — gitleaks-CI-Workflow
  (`.github/workflows/security.yml`).
- **ARCH-003** (medium) — Such-/Code-/Office-Antworten tragen jetzt `match_type`
  (`exact` / `none`).
- **OPS-003** (high) — explizite Deklaration „Phase 1 — rein lesend" im README.

**In 0.2.0 teilweise adressiert:**

- **OBS-002** (high) — die degraded-Note ist jetzt ein fester, bereinigter String
  (keine rohe Exception / kein Upstream-Body). `mask_error_details=True` wird
  **nicht** gesetzt, da das gepinnte `mcp`-SDK diese Einstellung nicht bietet.
- **OPS-001** (high) — Tests für die drei zuvor ungetesteten Tools und die neuen
  Input-Grenzen ergänzt; die Unit-Tiefe pro Tool liegt noch unter dem strikten
  ≥5-Ziel.

**Weiterhin offen (zurückgestellte Politur):** ARCH-007 (interne Aggregation, um
die Anchor-Query auf ≤2 Aufrufe zu bringen), CH-004 (explizite Datenlizenz nennen,
sobald die Nutzungsbedingungen von simap bestätigt sind).

**Akzeptiertes Risiko (profilbedingt zurückgestellt):** ARCH-008 (tools-only),
OBS-003 (strukturiertes Logging), SCALE-002 (Stateful-LB), SEC-007
(Container-Sandboxing), SEC-009 (Session-Binding) — siehe unten.

## Lethal-Trifecta-Bewertung (SEC-019)

Die „Lethal Trifecta" ist die gefährliche Kombination aus (1) Zugriff auf private
Daten, (2) Exposition gegenüber nicht vertrauenswürdigem Inhalt und (3) der
Fähigkeit zur Exfiltration. Dieser Server hat **höchstens einen** der drei Zweige:

| Zweig | Vorhanden? | Begründung |
|---|---|---|
| Zugriff auf private/sensible Daten | **Nein** | Nur öffentliche simap.ch-Publikationen werden gelesen; keine Auth, keine PII, keine benutzerbezogenen Daten |
| Exposition gegenüber nicht vertrauenswürdigem Inhalt | Teilweise | Tool-Resultate enthalten Upstream-Text, den das Modell aufnimmt — aber öffentliche Beschaffungsdaten, kein angreifergewählter privater Inhalt |
| Fähigkeit zur Exfiltration / Aktion | **Nein** | Egress ist auf einen Allow-List-Host (`www.simap.ch`) fixiert; keine Send-/Schreib-/Beliebig-Anfrage-Fähigkeit, alle Tools rein lesend |

Da der Privatdaten- und der Exfiltrations-Zweig beide fehlen, kann sich die
Trifecta nicht schliessen. Neu zu bewerten, falls der Server je Schreibzugriff
erhält, private Daten verarbeitet oder Egress zu beliebigen Hosts erlaubt.

## Akzeptierte Risiken

Die folgenden Kontrollen sind für einen rein lesenden Public-Open-Data-Server
bewusst **out of scope**. Keine hat einen Sicherheits-Impact für dieses Profil.

### Container-Sandboxing

**Status:** akzeptiertes Risiko.
Kein `Dockerfile` ausgeliefert. Akzeptabel für einen lokalen
stdio-Public-Data-Server — Defense-in-Depth liegt auf der OS-Benutzerebene. Ein
gehärtetes Image ausliefern, falls sich das Deployment-Profil je auf einen
dauerhaften Cloud-Dienst verschiebt.

### Strukturiertes Logging

**Status:** akzeptiertes Risiko.
Der Server nutzt das Standard-Logging des Hosts. JSON-strukturierte Logs mit
Trace-IDs sind für einen stdio-Server nicht gerechtfertigt; neu zu bewerten,
falls der Server auf ein Cloud-/SSE-Deployment gehoben wird.

### Rate-Limiting / Quota

**Status:** akzeptiertes Risiko.
simap.ch ist ein öffentlicher Dienst ohne Pro-Key-Quota; der Server setzt auf
Retry-with-Backoff (2s / 4s / 8s, 4xx ausser 429 werden nicht wiederholt) und
einen kurzlebigen Cache statt auf clientseitiges Rate-Limiting.

## Re-Evaluierungs-Auslöser

Diese Akzeptanzen sollten neu bewertet werden, falls der Server jemals:

- **Schreib**-Funktionalität erhält oder beginnt, **PII** zu verarbeiten, oder
- Tools **dynamisch** / aus entfernten Quellen registriert, oder
- auf ein **Cloud-/SSE**-Deployment verschoben wird (dann werden strukturiertes
  Logging, Container-Sandboxing und die Netzwerk-Binding-Checks relevant), oder
- hinter einem gemeinsamen MCP-Gateway aggregiert wird (dann Tool-Allow-Listing
  und Poisoning-Erkennung auf Gateway-Ebene umsetzen).
