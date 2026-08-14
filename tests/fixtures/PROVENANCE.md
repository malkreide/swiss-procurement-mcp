# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-08-14** von der Quelle dieses Servers: `https://www.simap.ch/api`.

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
verschachtelte `lots`-Liste, und `past-publications` verweigert die
Auskunft ganz. Aufgezeichnet ist deshalb je ein Fall von beiden.

## Befund: `past-publications` antwortet auf Lose mit HTTP 400

Die Publikationshistorie ist an `lotsType` gebunden, und zwar
ausnahmslos. Gemessen ueber 74 verschiedene Publikationen aus vier
Suchbegriffen (Bau, Software, Strasse, Reinigung):

| `lotsType` | Antwort auf `past-publications` | Faelle |
|---|---|---|
| `without` | HTTP 200 | 65 |
| `with` | HTTP 400, `errorCode: E0003` | 9 |

Beispiel: 28066-04 (mit Losen) → HTTP 400;
26921-02 (ohne Lose) → HTTP 200.

Wirkung: `get_publication_history` behandelt einen 4xx als
nicht-wiederholbaren Fehler — richtig so — und liefert fuer jede
losbasierte Beschaffung eine degradierte Antwort mit `count: 0`. Der
Docstring des Tools nennt die leere Liste «normal fuer eine erste
Publikation»; bei Losen ist sie das nicht, sondern eine Absage der
Quelle. Das ist der Stand der Quelle an diesem Tag, kein Fehler dieses
Servers — die Aufzeichnung haelt ihn datiert fest.

`past_publications_lot_400.json` haelt den Fehlerkoerper mitsamt
`errorCode`. Antwortet die Quelle wieder mit 200, faellt
`test_die_historie_verweigert_lose` — dann gehoert die Aufzeichnung
erneuert und dieser Befund gestrichen.

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
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; zugleich die Erreichbarkeitsprobe von `get_source_status` und der Aufruf, der die Sitzung eroeffnet
- **Groesse:** 1426 B
- **SHA-256:** `e2cc03b1224f161aa4649c21d5b59fc4ea93cbfc3b873cacfb5e71ec21ee2e43`

## `project_search.json`

- **Quelle:** `https://www.simap.ch/api/publications/v2/project/project-search?lang=de&search=Bau`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** Suche nach 'Bau'; 3 von 20 Projekten der Antwort, kein Feld entfernt: ein Zuschlag mit Losen, ein Zuschlag ohne, eine Ausschreibung, darunter eines ohne strukturierte Adresse (`orderAddress.cantonId: null`). `pagination` unveraendert
- **Groesse:** 4739 B (Quelle: 20 Projekte in der Antwort)
- **SHA-256:** `b512918467dcff895c43b43fcdc8ef0cdf250f580006b745f1e46c9af80fb65a`

## `publication_details.json`

- **Quelle:** `https://www.simap.ch/api/publications/v1/project/47dd2de9-d325-47e4-9ff1-991ecf60079b/publication-details/e8a78435-6e0f-4e5e-ad59-b6f1cfa7f1a4?lang=de`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; Publikation 26921-02 aus `project_search.json` — Zuschlag ohne Lose — kein `dates`, `lot` null
- **Groesse:** 7224 B
- **SHA-256:** `4d2ba6f6bb079be2580cf9895a735ea1114197c99434eb289902bceb91d8c37f`

## `publication_details_lot.json`

- **Quelle:** `https://www.simap.ch/api/publications/v1/project/11d690da-91aa-4023-867e-088f2992d0f6/publication-details/ebadc6da-a432-419c-bab1-b51359aec800?lang=de`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; Publikation 28066-04 aus `project_search.json` — Zuschlag mit Losen — `lot` gefuellt
- **Groesse:** 8927 B
- **SHA-256:** `66b7f6ef8e7082231b45610b413d8d9a01c2ea65bb8f90dce977278b6ea1e019`

## `publication_details_tender.json`

- **Quelle:** `https://www.simap.ch/api/publications/v1/project/dc46405e-c5f2-47e2-9670-2d2d1f1a3418/publication-details/8b42d7d3-7939-4c85-b1dc-59754c006a62?lang=de`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; Publikation 34121-04 aus `project_search.json` — Ausschreibung — mit `dates`, `criteria` und `terms`
- **Groesse:** 30570 B
- **SHA-256:** `3c2d559bbcc255253560dbcae3cd3d7206fb2bb2d41bfa2764d64f2d636a901b`

## `past_publications.json`

- **Quelle:** `https://www.simap.ch/api/publications/v1/publication/e8a78435-6e0f-4e5e-ad59-b6f1cfa7f1a4/past-publications?lang=de`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; Publikation 26921-02 (1 Vorgaenger)
- **Groesse:** 351 B
- **SHA-256:** `8d41674158ae8fb5887ce5eea306af60c59565f7429443f2b23bdb767ffbe520`

## `past_publications_lot_400.json`

- **Quelle:** `https://www.simap.ch/api/publications/v1/publication/ebadc6da-a432-419c-bab1-b51359aec800/past-publications?lang=de`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig bis auf `timestamp` (der aendert sich bei jedem Aufruf und erzeugte sonst einen Diff ohne Aussage); Publikation 28066-04 mit Losen — HTTP 400. Kein erfundener Fehlerpfad, sondern die Antwort der Quelle auf einen ganzen Fall; siehe Befund oben
- **Groesse:** 200 B
- **SHA-256:** `24696c79a202846f9dc3ae283b814d719478ad380eed0dc55dc457914df7b3d4`

## `codes_cpv.json`

- **Quelle:** `https://www.simap.ch/api/codes/v1/cpv/search?lang=de&query=Metall&limit=10`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; Suche nach 'Metall', limit 10
- **Groesse:** 53297 B
- **SHA-256:** `8ab1465aa98363eb1cd54ef5b79dbae761ccec8da6871d14f0136bb30fe147fa`

## `codes_bkp.json`

- **Quelle:** `https://www.simap.ch/api/codes/v1/bkp/search?lang=de&query=Fassade&limit=10`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** vollstaendig; Suche nach 'Fassade', limit 10
- **Groesse:** 7426 B
- **SHA-256:** `89f0332767a9312b2a37f62c3ac9e9bdf35244eaea9afe892fab27d0f9fd6995`

## `institutions.json`

- **Quelle:** `https://www.simap.ch/api/institutions/v1/institutions?lang=de`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** 40 von 463 Eintraegen, kein Feld entfernt: **alle 28 Wurzeln** (`parentInstitutionId: null`) — an ihnen haengt `CANTON_INSTITUTION_IDS` — dazu die vollstaendige Ahnenkette jedes Amtes aus `procoffices.json`, bis zu 4 Ebenen tief. Damit ist die Baumform belegt und die beiden Ausschnitte zeigen nicht aneinander vorbei
- **Groesse:** 21897 B (Quelle: 463 Eintraege)
- **SHA-256:** `c864424ddb048088a9b222ed3c32461ab36e65d53ea11263c194cf00f3c345ea`

## `procoffices.json`

- **Quelle:** `https://www.simap.ch/api/procoffices/v1/po/public?lang=de`
- **Aufgezeichnet:** 2026-08-14
- **Auswahl:** 8 von 4882 Aemtern, kein Feld entfernt: je eines pro `type` (cantonal, central_federation, communal, decentral_federation, foreign, other_cantonal, other_communal, other_federation). Die ersten Eintraege der Liste tragen alle denselben Typ, eine Kopfauswahl haette die anderen sieben nie belegt
- **Groesse:** 2162 B (Quelle: 4882 Aemter, 1160159 B)
- **SHA-256:** `f21a52815e43a65900d84db5344783eac0197ca644f2d2f767addbef70f358e2`
