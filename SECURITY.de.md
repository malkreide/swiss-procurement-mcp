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
| Egress | Jede Anfrage geht an eine einzige, fest verdrahtete HTTPS-Basis-URL (`https://www.simap.ch/api`, `SIMAP_BASE`); der Aufrufer gibt nie einen Host an |
| TLS | Zertifikatsprüfung standardmässig aktiv (httpx-Standard; nie deaktiviert) |
| Transport | Standardmässig stdio — stdout für den JSON-RPC-Stream reserviert; HTTP-Transporte (`MCP_TRANSPORT=sse\|streamable-http`) binden an Loopback (`127.0.0.1`), ausser `MCP_HOST`/`HOST=0.0.0.0` wird explizit gesetzt (SEC-016) |
| Input | Pydantic-v2-Validierung für jedes Tool-Input; Kantons-IDs, Verfahrens- und Publikationstypen werden gegen feste Allow-Lists geprüft und mit umsetzbarem Fehler abgewiesen (z. B. `ZH` statt `CH-ZH`) |
| Secrets | Keine API-Keys oder Zugangsdaten — die gekapselten simap-Endpoints sind vollständig öffentlich. Das nötige Session-Cookie wird transparent vom HTTP-Client bezogen und ist kein Geheimnis |
| Fehler | Upstream-4xx-Antworten werden auf 300 Zeichen gekürzt; Netzwerkfehler liefern einen generischen `degraded`-Envelope. Es werden keine Stack-Traces an das Modell gegeben |
| Stdout | Reserviert für den JSON-RPC-Stream; der Server schreibt keine Logs nach stdout |
| Umfang | Die rund 200 schreibenden, `my/`- und OIDC-geschützten simap-Endpoints (Publikation, Einreichung) werden bewusst nicht gekapselt |
| Tests | respx-mockierte Unit-Suite bei jedem PR (3.10/3.11/3.12); Live-API-Tests auf einen Nightly-Job beschränkt |

## Audit-Findings (26.07.2026)

17 Findings wurden dokumentiert (Policy `fail-or-partial`). Keines blockiert die
Produktion. Sie fallen in zwei Gruppen; die vollständigen Finding-Dokumente
liegen unter `audits/2026-07-26T131630-Z-swiss-procurement-mcp/findings/`.

**Geplante Härtung (geringer Impact, umsetzbar):**

- **ARCH-012** (fail, medium) — MCP-Protokoll-Version pinnen/festhalten,
  SDK-Update-Policy und Dependabot-Konfiguration ergänzen.
- **ARCH-009** (high) — `openWorldHint: true` an jedem Tool ergänzen (alle rufen
  live simap.ch auf).
- **OBS-002** (high) — FastMCP mit `mask_error_details=True` initialisieren und
  den rohen Upstream-Body aus der degraded-Note entfernen.
- **SEC-018** (high) — numerische `limit`-Parameter und Freitext-Länge begrenzen.
- **SEC-021** (high) — expliziten `assert_host_allowed`-Guard + `docs/network-egress.md`
  ergänzen (Egress ist bereits auf einen Host fest verdrahtet).
- **SEC-019** (critical, strukturell sicher) — die Lethal-Trifecta-Bewertung
  schriftlich festhalten (nur der External-Fetch-Zweig ist vorhanden).
- **ARCH-005** (critical, keine Secrets vorhanden) — CI-Secret-Scanning als
  Regressions-Guard ergänzen.
- Dazu **ARCH-003 / ARCH-007 / CH-004 / OPS-001 / OPS-003** — Doku-, Test-Tiefe-
  und Attributions-Politur.

**Akzeptiertes Risiko (profilbedingt zurückgestellt):** ARCH-008 (tools-only),
OBS-003 (strukturiertes Logging), SCALE-002 (Stateful-LB), SEC-007
(Container-Sandboxing), SEC-009 (Session-Binding) — siehe unten.

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
