> **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide/swiss-public-data-mcp)** — Open-Source-MCP-Server, die KI-Agenten mit Schweizer Behörden- und Open-Data-Quellen verbinden.
>
> Dies ist ein **privates Projekt**. Es ist unabhängig von jeder Arbeitgeberin und jeder institutionellen Zugehörigkeit und stellt keine offizielle Position einer Behörde dar.

# swiss-procurement-mcp

[![CI](https://github.com/malkreide/swiss-procurement-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/malkreide/swiss-procurement-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/swiss-procurement-mcp)](https://pypi.org/project/swiss-procurement-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/swiss-procurement-mcp)](https://pypi.org/project/swiss-procurement-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-orange.svg)](https://modelcontextprotocol.io/)
[![Portfolio](https://img.shields.io/badge/portfolio-swiss--public--data--mcp-blue)](https://github.com/malkreide/swiss-public-data-mcp)
[![English](https://img.shields.io/badge/Docs-English-blue.svg)](README.md)

MCP-Server für das **öffentliche Beschaffungswesen der Schweiz** — lesender Zugriff auf die offizielle simap.ch-API, alle Kantone und der Bund, tagesaktuell.

---

## 🎯 Anchor Demo Query

> *«Welche Bauausschreibungen für Schulhäuser hat die Stadt Zürich 2026 publiziert, welche BKP-Kategorien betreffen sie, und wer sind die ausschreibenden Stellen?»*

Ein einziger Aufruf `search_procurements_detailed(query="Schulhaus", canton="ZH", published_from="2026-01-01")`
liefert die führenden Ausschreibungen bereits mit ihren BKP-Codes und
ausschreibenden Stellen — in **einem** Call (optional ergänzt um
`search_construction_codes`). Alternativ verkettet die klassische Variante
`search_procurements`, `search_construction_codes` und
`get_procurement_details` und verbindet die Beschaffung über die BKP-Codes mit
der Schulraumplanung.

### Demo

![Demo: Claude nutzt search_procurements_detailed und search_construction_codes](docs/assets/demo.svg)

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
| `search_procurements` | Projekte nach Kanton, CPV, Verfahrensart, Datum, Text |
| `search_procurements_detailed` | Suche + vollständige Details der Top-*n*-Treffer in einem Call (aggregiert) |
| `search_awards` | Nur Zuschläge (alle vier Zuschlagsarten zusammen) |
| `get_procurement_details` | Vollständiger Datensatz einer Publikation |
| `get_publication_history` | Frühere Publikationen desselben Projekts (Ausschreibung → Zuschlag) |
| `search_cpv_codes` | Stichwort zu CPV-Klassifikationscode auflösen |
| `search_construction_codes` | Schweizer Baukosten-Codes (BKP, NPK, eBKP, OAG, CPC) |
| `find_procurement_office` | Beschaffungsstellen nach Teilname |
| `source_status` | Erreichbarkeit und Latenz der simap.ch-API |

Alle Tools tragen `readOnlyHint`, `idempotentHint` und `openWorldHint` (sie fragen
die Live-simap.ch-API ab).

### Was `canton=` bedeutet

simap kennt genau einen geografischen Filter, `orderAddressCantons`, und der
selektiert nach dem **Leistungsort** — nicht nach der Vergabestelle. Erfasst eine
Vergabestelle die Adresse als Freitext, ist der strukturierte Kanton `null` und
die Publikation für diesen Filter unsichtbar. CH-weit gemessen über 500 seit
2026-07-01 publizierte Projekte: **303 (60,6 %) ohne Kanton**, darunter das Amt
für Hochbauten Zürich, Grün Stadt Zürich, das USZ, das BBL und die SBB.

`canton_match` macht die Frage deshalb explizit:

| Wert | Trifft | Zürich, 2026-07-01…27 |
|---|---|---|
| `procuring_body` *(Standard)* | Beschaffung durch die öffentliche Hand dieses Kantons, inkl. kommunaler und untergeordneter Stellen (`issuedByOrganizations`) | **410** Projekte |
| `place_of_delivery` | Leistung wird dort erbracht (`orderAddressCantons`) | 263 Projekte |
| `both` | Vereinigung beider; zwei Upstream-Calls, keine Pagination | 441 Projekte |

Die 31 Projekte, die nur `place_of_delivery` findet, sind bundesnahe Träger, die
in Zürich beschaffen (ETH, Empa, Flughafen Zürich AG) — eine andere Frage, keine
Lücke. Genau deshalb drei explizite Semantiken statt einer stillen Vereinigung.

Jede Antwort nennt im `note`-Feld, welche Semantik angewendet wurde.

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
MCP_TRANSPORT=sse HOST=0.0.0.0 PORT=8000 python -m swiss_procurement_mcp
```

### Konfiguration

| Variable | Standard | Zweck |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio` \| `sse` \| `streamable-http` |
| `MCP_HOST` / `HOST` | `127.0.0.1` | HTTP-Binding (nur Cloud-Transporte). Standardmässig Loopback; für ein Cloud-Deployment `0.0.0.0` explizit setzen, um alle Interfaces freizugeben. |
| `MCP_CORS_ORIGINS` | _(nicht gesetzt)_ | Kommagetrennte Origins, die die HTTP-Transporte aus dem Browser aufrufen dürfen. Nicht gesetzt heisst: kein Cross-Origin-Zugriff aus dem Browser — stdio und Nicht-Browser-Clients sind nicht betroffen. Für die gelisteten Origins wird `Mcp-Session-Id` exponiert und akzeptiert, damit ein Browser-Client eine Session halten kann. `*` wird akzeptiert, loggt aber eine Warnung und deaktiviert Credentials, weil Browser eine Wildcard-Origin zusammen mit Credentials ablehnen. |
| `PORT` / `MCP_PORT` | `8000` | HTTP-Port (nur Cloud-Transporte) |

Keine API-Keys — die gekapselten simap.ch-Lese-Endpoints sind vollständig öffentlich.

---

## MCP Protocol Version

| | |
|---|---|
| **Unterstützte Spec-Version** | `2025-11-25` |
| **Gepinnt in** | `MCP_PROTOCOL_VERSION` in [`server.py`](src/swiss_procurement_mcp/server.py) |
| **SDK** | `mcp>=1.28.1` |

Das MCP-Python-SDK handelt die Protokollversion in der Session-Schicht aus und
bietet dafür keinen Konstruktor-Parameter — die Version lässt sich also nicht
per Konfiguration pinnen. Sie ist als deklarierte Konstante gepinnt und wird
durch Erkennung durchgesetzt:

- **Zur Laufzeit** loggt eine Abweichung zwischen Konstante und SDK ein
  `protocol_version_drift`-Event auf `WARNING`. Der Server läuft weiter.
- **In der CI** schlägt `tests/test_protocol_version.py` fehl.

Diese Trennung ist Absicht: ein SDK-Bump soll *unseren* Build brechen, nicht die
Laufzeit von jemandem, der `mcp` in seiner eigenen Umgebung aktualisiert hat.

### Update-Policy

- Dependabot öffnet monatlich SDK-Update-PRs (`.github/dependabot.yml`).
- Verschiebt ein SDK-Update die Protokollversion, schlägt der CI-Test fehl. Die
  Lösung ist **nicht**, die Konstante blind anzupassen: erst das Spec-Changelog
  auf die Unterschiede zwischen den Versionen lesen, das Serververhalten prüfen,
  dann Konstante, diesen Abschnitt und `CHANGELOG.md` in einem Commit anheben.
- Protokollversions-Bumps stehen explizit im `CHANGELOG.md` und werden nicht in
  eine Dependency-Bump-Zeile gefaltet.

---

## Primitive: nur Tools

Dieser Server exponiert **Tools** und weder Resources noch Prompts. Das ist eine
Entscheidung, kein Versäumnis — hier die Begründung (ARCH-008).

**Warum keine Resources.** Resources adressieren *identifizierbare, auflistbare*
Inhalte — `GET`-artige Zugriffe, die ein Client aufzählen und cachen kann. Die
simap-Endpunkte sind das Gegenteil: jeder nützliche Aufruf ist eine Abfrage mit
Filtern über einen Korpus von ~200k Publikationen, der sich untertägig ändert.
Eine Resource-URI müsste entweder etwas Unbegrenztes aufzählen oder eine
vollständige Query in die URI kodieren — also ein Tool mit Umweg.

Zwei Tools wurden konkret auf Migrationspotenzial geprüft und aus spezifischen
Gründen verworfen, nicht per Pauschalregel:

| Kandidat | Warum es ein Tool bleibt |
|---|---|
| `source_status` | Tatsächlich resource-förmig — ein festes, cachebares Dokument. Es existiert aber, um *aufgerufen* zu werden, wenn ein Ergebnis merkwürdig aussieht; eine Resource, die das Modell aktiv erneut lesen müsste, erfüllt diese Aufgabe schlechter als ein Tool, das es bei Verdacht aufrufen kann. |
| `search_cpv_codes` | Der CPV-Katalog ist endlich und stabil genug zum Aufzählen. Er hat aber ~10k Einträge; als Resource würde die ganze Klassifikation ins Kontextfenster wandern — obwohl der Sinn des Tools gerade ist, dass der *Server* die Suche übernimmt. |

**Warum keine Prompts.** Eine kuratierte Prompt-Liste würde Fragevorlagen
kodieren («welche Ausschreibungen im Kanton X …»). Die Tool-Docstrings tragen
diese Anleitung bereits dort, wo das Modell sie tatsächlich liest; Prompts
würden sie an einer zweiten Stelle duplizieren, die driften kann — genau diese
Art von Duplikation hat dieses Repo schon zweimal eingeholt.

Das wird neu bewertet, falls der Server je einen wirklich aufzählbaren,
langsam veränderlichen Datensatz bekommt.

---

## Tests

```bash
PYTHONPATH=src pytest tests/ -m "not live"   # offline, respx-gemockt
PYTHONPATH=src pytest tests/ -m live         # gegen die echte API
```

Siehe [EXAMPLES.md](EXAMPLES.md) für Anwendungsfälle nach Zielgruppe (Schule,
Öffentlichkeit, Verwaltung, Entwickler:innen) und eine Tool-Auswahl-Referenztabelle.

---

## Bekannte Einschränkungen

- **Projekte, nicht Publikationen.** `project-search` indexiert Projekte und
  vertritt jedes durch seine *neueste* Publikation. Ein im März ausgeschriebenes
  und im Juli zugeschlagenes Projekt erscheint einmal, als Juli-Zuschlag;
  ebenso findet `search_awards` nur Projekte, deren neueste Publikation ein
  Zuschlag ist — eine spätere Berichtigung verdeckt ihn.
  `get_publication_history` erreicht die früheren Publikationen.
- **Mindestens ein Filter ist nötig.** simap beantwortet eine filterlose Abfrage
  mit nichts statt mit allem; die Tools weisen sie deshalb mit genau dieser
  Begründung ab, statt ein leeres Ergebnis zu melden.
- **Bewusst rein lesend.** Publikations- und Einreiche-Endpoints existieren in der
  simap-API, werden aber bewusst nicht gekapselt.
- **Zuschlagsabdeckung ist ungleich** über die Kantone; einige publizieren
  Zuschläge konsequent, andere selten. Das Fehlen eines Zuschlags ist kein Beweis,
  dass keiner erfolgt ist.
- **Keine Auftragswerte in den Suchresultaten.** Beträge liegen, wo publiziert, im
  Statistikteil des Detaildatensatzes und variieren je nach Verfahren.
- **Inoffizieller Client.** Verbindlich bleiben die Publikationen auf simap.ch.

---

## Projektstruktur

```
swiss-procurement-mcp/
├── src/swiss_procurement_mcp/
│   ├── server.py      # FastMCP-Tools (9, rein lesend)
│   ├── client.py      # simap.ch-HTTP-Client + Retry + Normalisierung
│   ├── constants.py   # probe-abgeleitete Lookup-Tabellen (Kantone, Pub-Typen, Codes)
│   ├── models.py      # Pydantic-v2-Envelopes (source + provenance)
│   └── __main__.py    # Dual-Transport-Einstieg (stdio / SSE / streamable-http)
├── tests/             # respx-gemockt + @pytest.mark.live
└── .github/workflows/ # CI + OIDC-Publish (PyPI / MCP-Registry)
```

---

## Reifegrad & Updates

**Phase 1 — rein lesend** (siehe [ROADMAP.md](ROADMAP.md) für den
phasenspezifischen Backlog und die Voraussetzungen eines Phasenwechsels).
Dieser Server kapselt nur die öffentlichen
Lese-Endpoints; die schreibenden / OIDC-geschützten simap-Endpoints sind bewusst
ausserhalb des Umfangs. Die Bedingungen für einen Übergang zu einer Schreib-Phase
stehen als Re-Evaluierungs-Auslöser in [SECURITY.de.md](SECURITY.de.md).

Der Server zielt auf die als `MCP_PROTOCOL_VERSION` gepinnte MCP-Spec-Version —
der aktuelle Wert und die Durchsetzung des Pins stehen oben im Abschnitt
[MCP Protocol Version](#mcp-protocol-version). SDK- und Abhängigkeits-Updates
kommen als [Dependabot](.github/dependabot.yml)-PRs, damit eine brechende
Protokoll- oder SDK-Änderung bewusst geprüft wird statt still zu driften.

## Mitwirken

Beiträge sind willkommen — siehe [CONTRIBUTING.de.md](CONTRIBUTING.de.md), wie Sie
Fehler melden, einen neuen Endpoint vorschlagen oder Code einreichen.

## Sicherheit

Dies ist ein rein lesender, PII-freier Public-Open-Data-Server. Geprüft gegen den
Portfolio-MCP-Best-Practice-Katalog (**15 pass / 16 partial / 1 fail** über 32
anwendbare Checks, produktionsreif). Siehe [SECURITY.de.md](SECURITY.de.md) für
die Sicherheitslage und die Meldung von Schwachstellen sowie [`audits/`](audits/)
für den vollständigen Bericht.

## Lizenz

MIT-Lizenz — siehe [LICENSE](LICENSE). Die Ausschreibungen sind amtliche
Beschaffungspublikationen; simap.ch veröffentlicht keine explizite Open-Data-Lizenz,
die Weiterverwendung richtet sich daher nach den simap.ch-Bedingungen (siehe Credits).

## Autor

**Hayal Oezkan** · [github.com/malkreide](https://github.com/malkreide)

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md).

---

## Credits

- Daten: [simap.ch](https://www.simap.ch) Lese-API v1.5.1, betrieben vom Verein simap.ch. API-Doku: [simap.ch/api-doc](https://www.simap.ch/api-doc) — maschinenlesbare OpenAPI-Spec unter [`/api/specifications/simap.yaml`](https://www.simap.ch/api/specifications/simap.yaml), gegen die ein Live-Test die Enum-Konstanten prüft. Anleitungen: [kissimap.ch](https://www.kissimap.ch/de/anleitungen).
- Die zugrunde liegenden Ausschreibungen sind amtliche Beschaffungs-Bekanntmachungen Schweizer öffentlicher Stellen. simap.ch veröffentlicht **keine explizite Open-Data-Lizenz**; die Nutzung unterliegt den [simap.ch-Bedingungen](https://www.simap.ch/de/about/legal). Quelle als *simap.ch (Verein simap.ch)* angeben.
- Gebaut nach der Methodik `mcp-data-source-probe`.

Der **Code** in diesem Repository ist MIT-lizenziert; die **Daten** gehören simap.ch und unterliegen deren Bedingungen (siehe oben). Public money, public code.
