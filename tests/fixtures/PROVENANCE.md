# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-08-29** von der Quelle dieses Servers: `https://www.simap.ch/api`.

Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht
mehr zu unterscheiden — die Datei sieht gleich aus.

**Ein Teil sind Ausschnitte, keine Vollabzuege.** Die Auswahlregel steht
je Datei dabei; **kein Feld wurde entfernt**, gekuerzt ist nur die Zahl
der Eintraege. Eine Fixture belegt damit die *Form* der Antwort und einen
datierten Ausschnitt ihres Inhalts — nicht den Bestand. Aussagen ueber
Vollstaendigkeit gehoeren in `tests/test_live.py`.

**Die Eintraege sind gewaehlt, nicht genommen.** Die ersten Aemter der
1.1-MB-Liste tragen alle denselben `type`, und die ersten Institutionen
waeren lauter Wurzeln ohne ein einziges Kind. Eine Kopfauswahl haette
beide Formen nie belegt.

**Lose sind die Auswahlachse dieses Servers.** Publikationen mit Losen
(`lotsType: "with"`) verhalten sich an mehreren Endpunkten anders:
`publication-details` fuellt `lot`, der Suchtreffer traegt eine
verschachtelte `lots`-Liste, und `past-publications` verlangt einen
`lotId`. Aufgezeichnet ist deshalb je ein Fall von beiden.

## Befund: `past-publications` braucht bei Losen einen `lotId`

**Dieser Befund ersetzt einen falschen.** Bis zum 29.8.2026 stand hier,
die Quelle «verweigere die Auskunft ganz», wenn eine Publikation Lose
hat. Belegt war dafuer nur ein HTTP 400 — und aus einem 400 folgt eine
Verweigerung nicht. Der Endpunkt fuehrt laut eigener Spec einen
optionalen Parameter `lotId`; er ist bei Losen nicht optional. Mit ihm
antwortet dieselbe Publikation mit 200 und liefert ihre Vorgaenger.

Gemessen am 29.8.2026 ueber 80 Publikationen aus vier Suchbegriffen
(Bau, Software, Strasse, Reinigung), ausnahmslos:

| `lotsType` | ohne `lotId` | mit `lotId` | Faelle |
|---|---|---|---|
| `without` | HTTP 200 | — (404: ein fremdes Los gibt es dort nicht) | 76 |
| `with` | HTTP 400, `errorCode: E0003` | HTTP 200 | 4 |

Beispiel: 29653-03 (mit Losen) → HTTP 400; dieselbe
Publikation mit `lotId=1c0e3d2f-060a-485b-aebd-9bd0084e58b2` → HTTP 200 mit 2 Vorgaenger(n);
24255-02 (ohne Lose) → HTTP 200.

Wirkung des Fehlschlusses: `get_publication_history` gab fuer jede
losbasierte Beschaffung eine degradierte Antwort mit `count: 0` und dem
Hinweis, simap.ch sei «unreachable» — fuer einen Zustand, der weder
voruebergehend noch der Quelle anzulasten war. Ein gemessener Fall trug
sieben Vorgaenger, die der Server samt und sonders wegwarf. Die
Unit-Tests blieben dabei gruen, weil die Aufzeichnung nur den 400er
hielt und der Test ihm zustimmte.

Beide Antworten liegen deshalb jetzt nebeneinander:
`past_publications_lot_400.json` (ohne Parameter) und
`past_publications_lot.json` (mit). Der Unterschied zwischen ihnen ist
der Befund; eine Aufzeichnung allein von einer der beiden Seiten kann
ihn nicht tragen.

## Befund: `dates` gibt es nur bei Ausschreibungen

Der Detail-Endpunkt schneidet seine Bloecke nach Publikationsart zu.
Gemessen ueber 90 verschiedene Publikationen aus fuenf Suchbegriffen:

| Feld | vorhanden |
|---|---|
| `base.publicationDate` | 90 von 90 |
| `dates.publicationDate` | 40 von 90 (nur `tender`, `advance_notice`, `competition`) |
| `dates.offerDeadline` | 38 von 90 |

Wirkung, behoben in diesem Zug: `get_procurement_details` las das
Publikationsdatum ausschliesslich aus `dates` und lieferte deshalb fuer
**jeden Zuschlag** `publication_date: null` — 50 der 90 gemessenen
Publikationen —, obwohl die Quelle das Datum in `base.publicationDate`
mitschickt. Der handgeschriebene Stub `detail_payload` hatte ein `dates`
erfunden, das es bei einem Zuschlag nie gibt; die Suite stimmte damit dem
Mapper zu statt der Quelle und blieb gruen. Dieselbe Form wie der Befund,
der in `i14y-mcp` drei Tools mit leeren Titeln liefern liess.

`offer_deadline` bleibt unveraendert leer, wo `dates` fehlt: ein Zuschlag
hat keine Angebotsfrist. Ein fehlendes Feld ist dort die richtige Antwort
und kein Datenverlust.

## Befund: `pastPublications` fuehrt keinen Titel

Kein einziger der 31 gemessenen Historie-Eintraege traegt `title`. Die
Eintraege fuehren `publicationNumber`, `pubType`, `publicationDate` und
`id`, aber keinen Titel — `HistoryEntry.title` ist deshalb immer `null`.
Nicht stillschweigend entfernt, weil das Feld zur Antwortform gehoert und
die Quelle es jederzeit nachliefern kann; `test_die_historie_fuehrt_keinen_titel` haelt den Stand fest und faellt, wenn sie es tut.

Fehlerpfade — Timeouts, 5xx, ein maskierter Verbindungsabbruch — bleiben
handgeschrieben. Die lassen sich nicht auf Zuruf aufzeichnen. Der eine
aufgezeichnete 400er ist keine Ausnahme davon, sondern ein Befund: er
trifft nicht einen Fehlerfall, sondern jede losbasierte Beschaffung.

## `cantons.json`

- **Quelle:** `https://www.simap.ch/api/cantons/v1?lang=de`
- **Aufgezeichnet:** 2026-08-29
- **Auswahl:** vollstaendig; zugleich die Erreichbarkeitsprobe von `get_source_status` und der Aufruf, der die Sitzung eroeffnet
- **Groesse:** 1426 B
- **SHA-256:** `e2cc03b1224f161aa4649c21d5b59fc4ea93cbfc3b873cacfb5e71ec21ee2e43`

## `project_search.json`

- **Quelle:** `https://www.simap.ch/api/publications/v2/project/project-search?lang=de&search=Bau`
- **Aufgezeichnet:** 2026-08-29
- **Auswahl:** Suche nach 'Bau'; 3 von 20 Projekten der Antwort, kein Feld entfernt: ein Zuschlag mit Losen, ein Zuschlag ohne, eine Ausschreibung, darunter eines ohne strukturierte Adresse (`orderAddress.cantonId: null`). `pagination` unveraendert
- **Groesse:** 4648 B (Quelle: 20 Projekte in der Antwort)
- **SHA-256:** `81962407213edda9d99a14da2404d8ea47c486ffefa12a2876496dd11ef37161`

## `publication_details.json`

- **Quelle:** `https://www.simap.ch/api/publications/v1/project/f82cc889-2095-492a-92b0-54ca898246ef/publication-details/246db041-10e0-4a67-a3dd-ff5cc991c126?lang=de`
- **Aufgezeichnet:** 2026-08-29
- **Auswahl:** vollstaendig; Publikation 24255-02 aus `project_search.json` — Zuschlag ohne Lose — kein `dates`, `lot` null
- **Groesse:** 6470 B
- **SHA-256:** `b59bbbba5e9a764cee5bc2963e8a95db7e84c83be4216b2aeab7d2b8022666a3`

## `publication_details_lot.json`

- **Quelle:** `https://www.simap.ch/api/publications/v1/project/b35fd18a-37df-4d08-bdb0-d0b12a0a02fb/publication-details/85f4c967-6165-42df-a7f4-41f78f497dc8?lang=de`
- **Aufgezeichnet:** 2026-08-29
- **Auswahl:** vollstaendig; Publikation 29653-03 aus `project_search.json` — Zuschlag mit Losen — `lot` gefuellt
- **Groesse:** 12608 B
- **SHA-256:** `8aca64e50b49306f7f631deb0f0290039c064a4c277cd7ea29023516931f63ef`

## `publication_details_tender.json`

- **Quelle:** `https://www.simap.ch/api/publications/v1/project/0aece617-c897-4c4e-8daf-3b85c2f1cc89/publication-details/af304736-43a8-4c42-8f32-500b77235c7c?lang=de`
- **Aufgezeichnet:** 2026-08-29
- **Auswahl:** vollstaendig; Publikation 43130-01 aus `project_search.json` — Ausschreibung — mit `dates`, `criteria` und `terms`
- **Groesse:** 16712 B
- **SHA-256:** `aca1a780693563d307636741c78a5416bd215d2938074326daa44f84682f4196`

## `past_publications.json`

- **Quelle:** `https://www.simap.ch/api/publications/v1/publication/246db041-10e0-4a67-a3dd-ff5cc991c126/past-publications?lang=de`
- **Aufgezeichnet:** 2026-08-29
- **Auswahl:** vollstaendig; Publikation 24255-02 (1 Vorgaenger)
- **Groesse:** 351 B
- **SHA-256:** `f1314be4045362ebb6e4a0e77daf48d3f13152fc3adb289d8002285de59d9ee9`

## `past_publications_lot_400.json`

- **Quelle:** `https://www.simap.ch/api/publications/v1/publication/85f4c967-6165-42df-a7f4-41f78f497dc8/past-publications?lang=de`
- **Aufgezeichnet:** 2026-08-29
- **Auswahl:** vollstaendig bis auf `timestamp` (der aendert sich bei jedem Aufruf und erzeugte sonst einen Diff ohne Aussage); Publikation 29653-03 mit Losen, OHNE `lotId` — HTTP 400. Kein erfundener Fehlerpfad, sondern die Antwort der Quelle auf einen fehlenden Parameter; siehe Befund oben
- **Groesse:** 200 B
- **SHA-256:** `942a00cde06593902fa6c7b3c64f3d338cd92fa283a2bb77f830aaab95a0d3e6`

## `past_publications_lot.json`

- **Quelle:** `https://www.simap.ch/api/publications/v1/publication/85f4c967-6165-42df-a7f4-41f78f497dc8/past-publications?lang=de&lotId=1c0e3d2f-060a-485b-aebd-9bd0084e58b2`
- **Aufgezeichnet:** 2026-08-29
- **Auswahl:** vollstaendig; dieselbe Publikation 29653-03 wie `past_publications_lot_400.json`, nur mit `lotId` des ersten Loses — HTTP 200, 2 Vorgaenger. Die Gegenprobe zum 400er: derselbe Aufruf, ein Parameter mehr
- **Groesse:** 669 B
- **SHA-256:** `c22bede7335ec13a0f4f8c48790e782cf48cebad1573e3d79bf82b2134634d78`

## `codes_cpv.json`

- **Quelle:** `https://www.simap.ch/api/codes/v1/cpv/search?lang=de&query=Metall&limit=10`
- **Aufgezeichnet:** 2026-08-29
- **Auswahl:** vollstaendig; Suche nach 'Metall', limit 10
- **Groesse:** 53297 B
- **SHA-256:** `8ab1465aa98363eb1cd54ef5b79dbae761ccec8da6871d14f0136bb30fe147fa`

## `codes_bkp.json`

- **Quelle:** `https://www.simap.ch/api/codes/v1/bkp/search?lang=de&query=Fassade&limit=10`
- **Aufgezeichnet:** 2026-08-29
- **Auswahl:** vollstaendig; Suche nach 'Fassade', limit 10
- **Groesse:** 7426 B
- **SHA-256:** `89f0332767a9312b2a37f62c3ac9e9bdf35244eaea9afe892fab27d0f9fd6995`

## `institutions.json`

- **Quelle:** `https://www.simap.ch/api/institutions/v1/institutions?lang=de`
- **Aufgezeichnet:** 2026-08-29
- **Auswahl:** 40 von 463 Eintraegen, kein Feld entfernt: **alle 28 Wurzeln** (`parentInstitutionId: null`) — an ihnen haengt `CANTON_INSTITUTION_IDS` — dazu die vollstaendige Ahnenkette jedes Amtes aus `procoffices.json`, bis zu 4 Ebenen tief. Damit ist die Baumform belegt und die beiden Ausschnitte zeigen nicht aneinander vorbei
- **Groesse:** 21897 B (Quelle: 463 Eintraege)
- **SHA-256:** `c864424ddb048088a9b222ed3c32461ab36e65d53ea11263c194cf00f3c345ea`

## `procoffices.json`

- **Quelle:** `https://www.simap.ch/api/procoffices/v1/po/public?lang=de`
- **Aufgezeichnet:** 2026-08-29
- **Auswahl:** 8 von 4921 Aemtern, kein Feld entfernt: je eines pro `type` (cantonal, central_federation, communal, decentral_federation, foreign, other_cantonal, other_communal, other_federation). Die ersten Eintraege der Liste tragen alle denselben Typ, eine Kopfauswahl haette die anderen sieben nie belegt
- **Groesse:** 2162 B (Quelle: 4921 Aemter, 1169387 B)
- **SHA-256:** `f21a52815e43a65900d84db5344783eac0197ca644f2d2f767addbef70f358e2`
