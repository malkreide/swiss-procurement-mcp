# Use Cases & Examples — swiss-procurement-mcp

Real-world queries by audience. Every tool in this server queries the public
simap.ch read API — **no API key is ever required.** Canton ids are bare
two-letter codes (`ZH`, not `CH-ZH`); resolve category keywords to CPV codes with
`search_cpv_codes` before filtering.

## 🏫 Bildung & Schule

Schulbehörden, Bau- und Liegenschaftsverantwortliche, Fachreferent:innen

### Bauausschreibungen für Schulhäuser (Anchor Query)

«Welche Bauausschreibungen für Schulhäuser hat die Stadt Zürich 2026 publiziert, welche BKP-Kategorien betreffen sie, und wer sind die ausschreibenden Stellen?»

**API-Key nötig:** Nein

→ `search_procurements(query="Schulhaus", canton="ZH", published_from="2026-01-01")`
→ `search_construction_codes(system="bkp", query="Schulhaus")`
→ `get_procurement_details(project_id, publication_id)` für die BKP-Codes und die ausschreibende Stelle

Warum nützlich: Verbindet die Beschaffung über die BKP-Baukosten-Codes mit der Schulraumplanung. Schulbehörden sehen laufende Ausschreibungen mit offiziellen Fristen, statt die Weboberfläche von Hand zu durchsuchen.

### Wer hat einen Schulbau-Auftrag gewonnen?

«Welche Firma hat den Zuschlag für den letzten Schulhaus-Neubau in unserem Kanton erhalten?»

**API-Key nötig:** Nein

→ `search_awards(canton="ZH", published_from="2026-01-01")` (fragt alle vier Zuschlagsarten zusammen ab)
→ `get_procurement_details(project_id, publication_id)` für den vollständigen Datensatz

Warum nützlich: Zuschläge sind nach Verfahren aufgeteilt (`award_tender`, `award_study_contract`, `award_competition`, `direct_award`); `search_awards` bündelt sie. Beachten Sie: Die Zuschlagsabdeckung ist über die Kantone ungleich.

## 👨‍👩‍👧 Eltern & Öffentlichkeit

Interessierte Bürger:innen, Steuerzahlende, lokale Medien

### Verfahrensverlauf einer Beschaffung

«Wie ist eine Ausschreibung von der Publikation bis zum Zuschlag verlaufen?»

**API-Key nötig:** Nein

→ `get_publication_history(publication_id)` (Ausschreibung → Korrektur → Zuschlag)

Warum nützlich: Macht den Lebenszyklus eines Beschaffungsprojekts nachvollziehbar — nützlich für Transparenz und Berichterstattung über öffentliche Ausgaben.

### Beschaffungsstelle finden

«Welche Beschaffungsstelle steht hinter dieser Ausschreibung, und ist sie kantonal, kommunal oder beim Bund?»

**API-Key nötig:** Nein

→ `find_procurement_office(name_contains="Zürich")` liefert Id, Typ und die verknüpfte Institution

Warum nützlich: Ordnet eine Ausschreibung der verantwortlichen öffentlichen Stelle zu — die Brücke zu Register- und Zuständigkeitsfragen.

## 🏛️ Verwaltung & Beschaffungswesen

Öffentliche Einkäufer:innen, Controlling, Rechtsdienste

### Ausschreibungen einer Kategorie beobachten

«Welche offenen Ausschreibungen für IT-Dienstleistungen laufen aktuell?»

**API-Key nötig:** Nein

→ `search_cpv_codes(query="Informatik")` liefert die CPV-Codes
→ `search_procurements(cpv_codes=[...], process_type="open")`

Warum nützlich: CPV ist das internationale Klassifikationssystem, mit dem sich Ausschreibungen nach Kategorie filtern lassen. Ein Marktbeobachtungs-Workflow ohne manuelle Websuche.

### Anbieterfirma zu einem Zuschlag (Portfolio-Kombination)

«Wer ist die Firma hinter diesem Zuschlag, und was ist im Handelsregister zu ihr eingetragen?»

**API-Key nötig:** Nein

→ `search_awards(...)` → `get_procurement_details(...)` liefert die Anbieterfirma und ihre UID
→ UID an [`register-mcp`](https://github.com/malkreide/register-mcp) übergeben für den Handelsregister-Eintrag

Warum nützlich: Die UID verknüpft die Beschaffungswelt mit dem Handelsregister. Ein Agent kombiniert Zuschlag und Firmenprofil über die gemeinsame UID-Brücke.

## 🤖 KI-Interessierte & Entwickler:innen

MCP-Enthusiast:innen, Forscher:innen, Prompt Engineers, öffentliche Verwaltung

### Robuste Filter über CPV- und Baukosten-Codes

«Wie finde ich zuverlässig alle Bauausschreibungen einer bestimmten Kostenkategorie?»

**API-Key nötig:** Nein

→ `search_construction_codes(system="ebkp-h", query="<stichwort>")` → Code
→ `get_procurement_details(...)` und Abgleich der `bkp_codes` / `npk_codes`

Warum nützlich: Die dedizierten Code-Such-Endpoints machen die Schweizer Baukosten-Standards (BKP, NPK, eBKP, OAG, CPC) für Agenten adressierbar, statt zu raten.

### Erreichbarkeit prüfen, bevor eine Abfrage-Kette startet

«Ist die simap.ch-API gerade erreichbar?»

**API-Key nötig:** Nein

→ `source_status()` meldet Erreichbarkeit und Latenz

Warum nützlich: Jede Antwort trägt `source` und `provenance` (`live_api` / `cached` / `degraded`). Ein Upstream-Ausfall liefert einen `degraded`-Envelope statt einer stillschweigend leeren Liste — Agenten können darauf reagieren.

## 🔧 Technische Referenz: Tool-Auswahl nach Anwendungsfall

| Ich möchte… | Tool(s) | Auth nötig? |
|---|---|---|
| Publikationen nach Kanton, CPV, Verfahren, Datum oder Text suchen | `search_procurements` | Nein |
| Nur Zuschläge finden (alle vier Zuschlagsarten) | `search_awards` | Nein |
| Den vollständigen Datensatz einer Publikation abrufen | `get_procurement_details` | Nein |
| Den Verlauf eines Projekts nachvollziehen (Ausschreibung → Zuschlag) | `get_publication_history` | Nein |
| Ein Stichwort zu einem CPV-Code auflösen | `search_cpv_codes` | Nein |
| Schweizer Baukosten-Codes suchen (BKP, NPK, eBKP, OAG, CPC) | `search_construction_codes` | Nein |
| Eine Beschaffungsstelle nach Teilname finden | `find_procurement_office` | Nein |
| Die Erreichbarkeit und Latenz der API prüfen | `source_status` | Nein |

All tools are read-only (`readOnlyHint: true`) and query the live simap.ch API.
