> **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide/swiss-public-data-mcp)** — Open-Source-MCP-Server, die KI-Agenten mit Schweizer Behörden- und Open-Data-Quellen verbinden.
>
> Dies ist ein **privates Projekt**. Es ist unabhängig von jeder Arbeitgeberin und jeder institutionellen Zugehörigkeit und stellt keine offizielle Position einer Behörde dar.

# swiss-procurement-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-orange.svg)](https://modelcontextprotocol.io/)
[![English](https://img.shields.io/badge/Docs-English-blue.svg)](README.md)

MCP-Server für das **öffentliche Beschaffungswesen der Schweiz** — lesender Zugriff auf die offizielle simap.ch-API, alle Kantone und der Bund, tagesaktuell.

---

## 🎯 Anchor Demo Query

> *«Welche Bauausschreibungen für Schulhäuser hat die Stadt Zürich 2026 publiziert, welche BKP-Kategorien betreffen sie, und wer sind die ausschreibenden Stellen?»*

Diese Frage verkettet `search_procurements`, `search_construction_codes` und
`get_procurement_details` und verbindet die Beschaffung über die BKP-Codes mit
der Schulraumplanung.

---

## Warum dieser Server

Öffentliche Beschaffungen werden auf simap.ch publiziert. Die Weboberfläche ist
von Hand durchsuchbar, aber der Server
[`amtsblatt-mcp`](https://github.com/malkreide/amtsblatt-mcp) erreicht nur die
drei Kantone (AR, BS, TI), die ihre Ausschreibungen noch ins Amtsblattportal
spiegeln — Zürich fehlt.

simap schliesst diese Lücke: Die Plattform betreibt eine dokumentierte
**OpenAPI-3-Lese-API (v1.5.1)**, deren Such- und Detail-Endpoints mit
`security: None` markiert und **ohne Authentifizierung** aufrufbar sind. Dieser
Server kapselt genau diese Lese-Endpoints.

> **Eselsbrücke:** *Die Weboberfläche ist der Vordereingang, die API die Laderampe. Prüfe die Rampe.*

---

## Architektur-Entscheid

**Architektur A (Live-API only, kurzer Cache).**

- Die öffentlichen Such-, Detail- und Referenz-Endpoints sind ohne
  Authentifizierung nutzbar, live bestätigt am 26.07.2026.
- Publikationen ändern sich untertägig, deshalb ein bewusst kurzer Cache (30 Min.).
- Die rund 200 schreibenden, `my/`- und OIDC-geschützten Endpoints (Ausschreibung
  erfassen, Angebot einreichen) sind **ausserhalb des Umfangs** — dieser Server
  schreibt nie.

Jede Antwort trägt `source` und `provenance` (`live_api` / `cached` /
`degraded`). Ein Upstream-Ausfall liefert einen `degraded`-Envelope, nie eine
stillschweigend leere Liste.

---

## Live-Probe-Befunde (26.07.2026)

| Endpoint | Auth | Ergebnis |
|---|---|---|
| `/publications/v2/project/project-search` | keine | 20 Treffer, Kantonsfilter, tagesaktuell |
| `/publications/v1/.../publication-details/...` | keine | vollständiger Datensatz: Kriterien, Fristen, Codes |
| `/publications/v1/publication/{id}/past-publications` | keine | Verfahrensverlauf |
| `/codes/v1/cpv/search` | keine | CPV-Volltextsuche |
| `/codes/v1/{bkp,npk,ebkp-h,ebkp-t,oag,cpc}/search` | keine | Schweizer Baukosten-Codes |
| `/procoffices/v1/po/public` | keine | ~1 MB Stellenliste (clientseitig gefiltert) |
| `/cantons/v1`, `/countries/v1` | keine | Referenzdaten |

### Known findings

1. **Falscher Host, falscher Schluss.** Die Lese-API liegt unter
   `www.simap.ch/api`. Die Weboberfläche `simap.ch/de` ist eine separate
   SSR-Anwendung und exponiert nichts davon — die Prüfung der Oberfläche führte
   zunächst zum falschen Urteil «keine API».
2. **`lang` ist Pflicht** bei project-search. Fehlt der Parameter, folgt HTTP 400
   (errorCode `E0025`), kein leeres Ergebnis. Der Client setzt einen Standardwert.
3. **Zuschlag heisst nicht «award».** `newestPubTypes=award` liefert HTTP 400.
   Zuschläge sind nach Verfahren aufgeteilt: `award_tender`,
   `award_study_contract`, `award_competition`, `direct_award`. Das Tool
   `search_awards` fragt alle vier zusammen ab.
4. **Kantons-Ids sind nackt.** `ZH`, nicht `CH-ZH`. Ein ISO-Subdivision-Code
   matcht stillschweigend nichts; dieser Server weist ihn mit klarer Meldung ab.
5. **Ein Session-Cookie ist nötig.** Der erste Aufruf setzt es; ein persistenter
   HTTP-Client erledigt das transparent.

---

## Tools

| Tool | Zweck |
|---|---|
| `search_procurements` | Publikationen nach Kanton, CPV, Verfahrensart, Datum, Text |
| `search_awards` | Nur Zuschläge (alle vier Zuschlagsarten zusammen) |
| `get_procurement_details` | Vollständiger Datensatz einer Publikation |
| `get_publication_history` | Frühere Publikationen desselben Projekts (Ausschreibung → Zuschlag) |
| `search_cpv_codes` | Stichwort zu CPV-Klassifikationscode auflösen |
| `search_construction_codes` | Schweizer Baukosten-Codes (BKP, NPK, eBKP, OAG, CPC) |
| `find_procurement_office` | Beschaffungsstellen nach Teilname |
| `source_status` | Erreichbarkeit und Latenz der simap.ch-API |

Alle Tools sind `readOnlyHint: true`.

---

## Portfolio-Verbindungen

- Die UID einer Anbieterfirma verknüpft mit
  [`register-mcp`](https://github.com/malkreide/register-mcp).
- BKP-/eBKP-Baukosten-Codes einer Ausschreibung verbinden die Beschaffung mit der
  Schulraumplanung und mit
  [`zh-education-mcp`](https://github.com/malkreide/zh-education-mcp).
- Ergänzt [`amtsblatt-mcp`](https://github.com/malkreide/amtsblatt-mcp) um
  nationale Abdeckung statt drei Kantonen.

---

## Installation

```bash
uvx swiss-procurement-mcp
```

### Claude Desktop

```json
{
  "mcpServers": {
    "swiss-procurement": {
      "command": "uvx",
      "args": ["swiss-procurement-mcp"]
    }
  }
}
```

### Cloud (Render / Railway)

```bash
MCP_TRANSPORT=sse PORT=8000 python -m swiss_procurement_mcp
```

---

## Testing

```bash
PYTHONPATH=src pytest tests/ -m "not live"   # offline, respx-gemockt
PYTHONPATH=src pytest tests/ -m live         # gegen die echte API
```

---

## Bekannte Einschränkungen

- **Bewusst rein lesend.** Publikations- und Einreiche-Endpoints existieren in der
  simap-API, werden aber bewusst nicht gekapselt.
- **Zuschlagsabdeckung ist ungleich** über die Kantone; einige publizieren
  Zuschläge konsequent, andere selten. Das Fehlen eines Zuschlags ist kein Beweis,
  dass keiner erfolgt ist.
- **Keine Auftragswerte in den Suchresultaten.** Beträge liegen, wo publiziert, im
  Statistikteil des Detaildatensatzes und variieren je nach Verfahren.
- **Inoffizieller Client.** Verbindlich bleiben die Publikationen auf simap.ch.

---

## Credits

- Daten: [simap.ch](https://www.simap.ch) Lese-API v1.5.1, betrieben vom Verein simap.ch. API-Doku: [simap.ch/api-doc](https://www.simap.ch/api-doc), Anleitungen: [kissimap.ch](https://www.kissimap.ch/de/anleitungen).
- Gebaut nach der Methodik `mcp-data-source-probe`.

MIT-lizenziert. Public money, public code.
