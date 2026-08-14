#!/usr/bin/env python3
"""Zeichnet echte simap.ch-Antworten nach `tests/fixtures/` auf.

Warum: eine handgeschriebene Fixture kodiert die Annahme ihres Autors und kann
sie deshalb nicht widerlegen. In `i14y-mcp` blieb genau deshalb eine ganze Suite
gruen, waehrend drei Tools produktiv leere Titel lieferten — die Stubs hatten
einen Schluessel erfunden und stimmten dem Mapper zu statt der Quelle.

Zwei Eigenheiten der Quelle bestimmen den Aufbau:

* **Die Sitzung ist Pflicht.** Der erste Aufruf setzt ein Cookie; ohne Cookie-Jar
  antwortet jeder `/api`-Pfad mit einer Cookie-Pruefseite statt mit JSON. Der
  Recorder faehrt deshalb wie der Client ueber eine Sitzung.
* **Lose sind die Trennlinie.** Publikationen mit Losen (`lotsType: "with"`)
  verhalten sich an mehreren Endpunkten anders als die ohne. Aufgezeichnet wird
  deshalb je ein Fall von beiden — die Auswahlachse dieses Servers.

Grosse Antworten sind Ausschnitte: **Feldbestand unveraendert, Zeilen gewaehlt
statt genommen.** Die Ämterliste ist 1.1 MB und die ersten Eintraege zeigen nur
einen von acht `type`-Werten; die Institutionsliste traegt 463 Eintraege, von
denen die 28 Wurzeln der Grund sind, warum es sie hier gibt.

Herkunft, Datum, Auswahlregel und SHA-256 je Datei schreibt dieses Skript nach
`tests/fixtures/PROVENANCE.md`. Neu aufzeichnen:

    python scripts/record_fixtures.py

Braucht Netzzugang zu `www.simap.ch`. Entwicklungswerkzeug; weder das Paket noch
die Testsuite importieren es.
"""

from __future__ import annotations

import hashlib
import http.cookiejar
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

BASE = "https://www.simap.ch/api"

# Fest gewaehlt, nicht «irgendeiner»: eine vom Lauf abhaengige Suche erzeugt bei
# jedem Aufzeichnen einen anderen Diff. Der Begriff ist breit genug, dass beide
# `lotsType`-Werte und beide `pubType`-Werte in einer einzigen Antwort vorkommen
# — die Aufzeichnung bleibt damit *eine* Antwort und nicht eine Collage.
SEARCH_TERM = "Bau"
LANG = "de"

# Je ein Code-System mit flacher und mit verschachtelter Antwort. Beide fahren
# ueber denselben Endpunkt `/codes/v1/{system}/search`; die Verschachtelung ist
# der Unterschied, den eine erfundene Fixture flach geraten haette.
CODE_QUERIES = (("cpv", "Metall"), ("bkp", "Fassade"))

# Je Ausschnitt: wie viele Eintraege ueber die gezielte Auswahl hinaus.
BEISPIELE_JE_TYP = 1


def _opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [
        ("User-Agent", "swiss-procurement-mcp-recorder"),
        ("Accept", "application/json"),
    ]
    return op


OPENER = _opener()


def get(path: str, **params: Any) -> tuple[int, Any]:
    """Holt einen Pfad und liefert (Status, geparstes JSON) — auch bei 4xx.

    Der Fehlerkoerper wird mitgeliefert, weil einer davon aufgezeichnet wird:
    die Quelle antwortet auf einen ganzen Fall mit HTTP 400, und das ist ein
    Befund und keine Panne des Recorders.
    """
    url = path if path.startswith("http") else f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    try:
        # Die Basis ist eine feste https-URL, `path` kommt aus diesem Modul.
        with OPENER.open(url, timeout=180) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries: list[dict[str, Any]] = []
    print(f"Zeichne auf von {BASE}")

    def write(name: str, payload: Any, url: str, rule: str, total: str | None = None) -> None:
        blob = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        (FIXTURES / name).write_bytes(blob)
        entries.append(
            {
                "name": name,
                "url": url,
                "rule": rule,
                "bytes": len(blob),
                "total": total,
                "sha256": hashlib.sha256(blob).hexdigest(),
            }
        )
        print(f"  ok  {name:<32} {len(blob):>8} B")

    def url_of(path: str, **params: Any) -> str:
        return f"{BASE}{path}" + (
            "?" + urllib.parse.urlencode(params, doseq=True) if params else ""
        )

    # --- Sitzung: erst das Cookie, dann alles andere ---------------------
    # Derselbe Pfad, den `get_source_status` als Erreichbarkeitsprobe faehrt.
    status, cantons = get("/cantons/v1", lang=LANG)
    assert status == 200, f"cantons/v1 antwortete {status}"
    write(
        "cantons.json",
        cantons,
        url_of("/cantons/v1", lang=LANG),
        "vollstaendig; zugleich die Erreichbarkeitsprobe von `get_source_status` "
        "und der Aufruf, der die Sitzung eroeffnet",
    )

    # --- project-search --------------------------------------------------
    such_url = url_of("/publications/v2/project/project-search", lang=LANG, search=SEARCH_TERM)
    status, suche = get("/publications/v2/project/project-search", lang=LANG, search=SEARCH_TERM)
    assert status == 200, f"project-search antwortete {status}"
    alle = suche.get("projects", [])

    def erster(pruef) -> dict[str, Any] | None:
        return next((p for p in alle if pruef(p)), None)

    mit_losen = erster(lambda p: p.get("lotsType") == "with")
    ohne_lose = erster(lambda p: p.get("lotsType") == "without" and p.get("pubType") == "award")
    ausschreibung = erster(lambda p: p.get("pubType") == "tender")
    assert mit_losen and ohne_lose, "die Suche traegt nicht beide `lotsType`-Werte"
    assert ausschreibung, "die Suche traegt keine Ausschreibung — nur sie fuehrt `dates`"
    gewaehlt: list[dict[str, Any]] = [mit_losen, ohne_lose, ausschreibung]
    # Dritte Achse: eine Publikation ohne strukturierte Adresse. 60.6 Prozent
    # tragen `cantonId: null` und sind damit fuer den Adressfilter unsichtbar —
    # der Grund, warum dieser Server ueber `issuedByOrganizations` filtert. Nur
    # dazunehmen, wenn die beiden ersten die Achse nicht schon abdecken.
    ohne_kanton = erster(
        lambda p: (p.get("orderAddress") or {}).get("cantonId") is None and p not in gewaehlt
    )
    if ohne_kanton is not None and not any(
        (p.get("orderAddress") or {}).get("cantonId") is None for p in gewaehlt
    ):
        gewaehlt.append(ohne_kanton)
    achsen = [
        "ein Zuschlag mit Losen, ein Zuschlag ohne, eine Ausschreibung",
        (
            "darunter eines ohne strukturierte Adresse (`orderAddress.cantonId: null`)"
            if any((p.get("orderAddress") or {}).get("cantonId") is None for p in gewaehlt)
            else "keines ohne strukturierte Adresse in dieser Antwort"
        ),
    ]

    write(
        "project_search.json",
        {**suche, "projects": gewaehlt},
        such_url,
        f"Suche nach {SEARCH_TERM!r}; {len(gewaehlt)} von {len(alle)} Projekten der "
        f"Antwort, kein Feld entfernt: {', '.join(achsen)}. `pagination` unveraendert",
        f"{len(alle)} Projekte in der Antwort",
    )

    # --- publication-details: drei Formen desselben Endpunkts ------------
    # Der Endpunkt liefert je nach Publikationsart verschiedene Bloecke. Ein
    # Zuschlag hat kein `dates`, eine Ausschreibung schon; ein losbasierter
    # Zuschlag fuellt zusaetzlich `lot`. Genau diese Unterschiede haette eine
    # erfundene Fixture nicht kennen koennen — die handgeschriebene im Repo
    # erfand ein `dates` fuer einen Zuschlag, den es dort nie gibt.
    for etikett, projekt, warum in (
        ("", ohne_lose, "Zuschlag ohne Lose — kein `dates`, `lot` null"),
        ("_lot", mit_losen, "Zuschlag mit Losen — `lot` gefuellt"),
        ("_tender", ausschreibung, "Ausschreibung — mit `dates`, `criteria` und `terms`"),
    ):
        pfad = (
            f"/publications/v1/project/{projekt['id']}"
            f"/publication-details/{projekt['publicationId']}"
        )
        status, detail = get(pfad, lang=LANG)
        assert status == 200, f"publication-details antwortete {status}"
        write(
            f"publication_details{etikett}.json",
            detail,
            url_of(pfad, lang=LANG),
            f"vollstaendig; Publikation {projekt['publicationNumber']} aus "
            f"`project_search.json` — {warum}",
        )

    # --- past-publications: der 200er und der Befund ---------------------
    pfad = f"/publications/v1/publication/{ohne_lose['publicationId']}/past-publications"
    status, historie = get(pfad, lang=LANG)
    assert status == 200, f"past-publications antwortete {status}"
    write(
        "past_publications.json",
        historie,
        url_of(pfad, lang=LANG),
        f"vollstaendig; Publikation {ohne_lose['publicationNumber']} "
        f"({len(historie.get('pastPublications') or [])} Vorgaenger)",
    )

    pfad = f"/publications/v1/publication/{mit_losen['publicationId']}/past-publications"
    status, fehler = get(pfad, lang=LANG)
    write(
        "past_publications_lot_400.json",
        {k: v for k, v in fehler.items() if k != "timestamp"},
        url_of(pfad, lang=LANG),
        f"vollstaendig bis auf `timestamp` (der aendert sich bei jedem Aufruf und "
        f"erzeugte sonst einen Diff ohne Aussage); Publikation "
        f"{mit_losen['publicationNumber']} mit Losen — HTTP {status}. Kein "
        "erfundener Fehlerpfad, sondern die Antwort der Quelle auf einen ganzen "
        "Fall; siehe Befund oben",
    )

    # --- Code-Suche: flach und verschachtelt -----------------------------
    for system, frage in CODE_QUERIES:
        pfad = f"/codes/v1/{system}/search"
        params = {"lang": LANG, "query": frage, "limit": 10}
        status, codes = get(pfad, **params)
        assert status == 200, f"codes/{system} antwortete {status}"
        write(
            f"codes_{system}.json",
            codes,
            url_of(pfad, **params),
            f"vollstaendig; Suche nach {frage!r}, limit 10",
        )

    # --- Institutionen und Beschaffungsstellen ---------------------------
    # Die beiden gehoeren zusammen: ein Amt zeigt ueber `institutionId` in den
    # Institutionsbaum, und genau diese Verbindung traegt den Kantonsfilter
    # dieses Servers (`issuedByOrganizations`). Deshalb erst die Aemter waehlen,
    # dann zu jedem gewaehlten Amt die ganze Ahnenkette aufnehmen — sonst zeigen
    # zwei Ausschnitte aneinander vorbei und keine Fixture merkt es.
    status, inst = get("/institutions/v1/institutions", lang=LANG)
    assert status == 200
    institutionen = inst["institutions"]
    nach_id = {i["id"]: i for i in institutionen}
    wurzeln = [i for i in institutionen if i.get("parentInstitutionId") is None]

    status, po = get("/procoffices/v1/po/public", lang=LANG)
    assert status == 200
    aemter = po["procOffices"]
    je_typ: dict[str, list[dict[str, Any]]] = {}
    for amt in aemter:
        je_typ.setdefault(amt.get("type") or "", []).append(amt)
    amt_auswahl = [a for typ in sorted(je_typ) for a in je_typ[typ][:BEISPIELE_JE_TYP]]

    def kette(institution_id: str | None) -> list[dict[str, Any]]:
        """Die Institution und alle ihre Vorfahren bis zur Wurzel."""
        aus: list[dict[str, Any]] = []
        knoten = nach_id.get(institution_id or "")
        while knoten is not None:
            aus.append(knoten)
            knoten = nach_id.get(knoten.get("parentInstitutionId") or "")
        return aus

    inst_auswahl = list(wurzeln)
    for amt in amt_auswahl:
        for knoten in kette(amt.get("institutionId")):
            if knoten not in inst_auswahl:
                inst_auswahl.append(knoten)
    tiefe = max(len((i.get("path") or "").split(".")) for i in inst_auswahl)

    write(
        "institutions.json",
        {**inst, "institutions": inst_auswahl},
        url_of("/institutions/v1/institutions", lang=LANG),
        f"{len(inst_auswahl)} von {len(institutionen)} Eintraegen, kein Feld "
        f"entfernt: **alle {len(wurzeln)} Wurzeln** (`parentInstitutionId: null`) "
        "— an ihnen haengt `CANTON_INSTITUTION_IDS` — dazu die vollstaendige "
        "Ahnenkette jedes Amtes aus `procoffices.json`, bis zu "
        f"{tiefe} Ebenen tief. Damit ist die Baumform belegt und die beiden "
        "Ausschnitte zeigen nicht aneinander vorbei",
        f"{len(institutionen)} Eintraege",
    )
    write(
        "procoffices.json",
        {**po, "procOffices": amt_auswahl},
        url_of("/procoffices/v1/po/public", lang=LANG),
        f"{len(amt_auswahl)} von {len(aemter)} Aemtern, kein Feld entfernt: je "
        f"eines pro `type` ({', '.join(sorted(je_typ))}). Die ersten Eintraege der "
        "Liste tragen alle denselben Typ, eine Kopfauswahl haette die anderen "
        "sieben nie belegt",
        f"{len(aemter)} Aemter, {len(json.dumps(po))} B",
    )

    befund = _befund(mit_losen, ohne_lose, status_400=400) + _befund_datum()
    _write_provenance(recorded_at, entries, befund)
    print(f"\nPROVENANCE.md geschrieben, Aufzeichnungsdatum {recorded_at}")
    return _warne_bei_ignorierten(entries)


def _befund(mit_losen: dict[str, Any], ohne_lose: dict[str, Any], status_400: int) -> list[str]:
    return [
        f"## Befund: `past-publications` antwortet auf Lose mit HTTP {status_400}",
        "",
        "Die Publikationshistorie ist an `lotsType` gebunden, und zwar",
        "ausnahmslos. Gemessen ueber 74 verschiedene Publikationen aus vier",
        "Suchbegriffen (Bau, Software, Strasse, Reinigung):",
        "",
        "| `lotsType` | Antwort auf `past-publications` | Faelle |",
        "|---|---|---|",
        "| `without` | HTTP 200 | 65 |",
        f"| `with` | HTTP {status_400}, `errorCode: E0003` | 9 |",
        "",
        f"Beispiel: {mit_losen['publicationNumber']} (mit Losen) → HTTP {status_400};",
        f"{ohne_lose['publicationNumber']} (ohne Lose) → HTTP 200.",
        "",
        "Wirkung: `get_publication_history` behandelt einen 4xx als",
        "nicht-wiederholbaren Fehler — richtig so — und liefert fuer jede",
        "losbasierte Beschaffung eine degradierte Antwort mit `count: 0`. Der",
        "Docstring des Tools nennt die leere Liste «normal fuer eine erste",
        "Publikation»; bei Losen ist sie das nicht, sondern eine Absage der",
        "Quelle. Das ist der Stand der Quelle an diesem Tag, kein Fehler dieses",
        "Servers — die Aufzeichnung haelt ihn datiert fest.",
        "",
        "`past_publications_lot_400.json` haelt den Fehlerkoerper mitsamt",
        "`errorCode`. Antwortet die Quelle wieder mit 200, faellt",
        "`test_die_historie_verweigert_lose` — dann gehoert die Aufzeichnung",
        "erneuert und dieser Befund gestrichen.",
        "",
    ]


def _befund_datum() -> list[str]:
    return [
        "## Befund: `dates` gibt es nur bei Ausschreibungen",
        "",
        "Der Detail-Endpunkt schneidet seine Bloecke nach Publikationsart zu.",
        "Gemessen ueber 90 verschiedene Publikationen aus fuenf Suchbegriffen:",
        "",
        "| Feld | vorhanden |",
        "|---|---|",
        "| `base.publicationDate` | 90 von 90 |",
        "| `dates.publicationDate` | 40 von 90 (nur `tender`, `advance_notice`, `competition`) |",
        "| `dates.offerDeadline` | 38 von 90 |",
        "",
        "Wirkung, behoben in diesem Zug: `get_procurement_details` las das",
        "Publikationsdatum ausschliesslich aus `dates` und lieferte deshalb fuer",
        "**jeden Zuschlag** `publication_date: null` — 50 der 90 gemessenen",
        "Publikationen —, obwohl die Quelle das Datum in `base.publicationDate`",
        "mitschickt. Der handgeschriebene Stub `detail_payload` hatte ein `dates`",
        "erfunden, das es bei einem Zuschlag nie gibt; die Suite stimmte damit dem",
        "Mapper zu statt der Quelle und blieb gruen. Dieselbe Form wie der Befund,",
        "der in `i14y-mcp` drei Tools mit leeren Titeln liefern liess.",
        "",
        "`offer_deadline` bleibt unveraendert leer, wo `dates` fehlt: ein Zuschlag",
        "hat keine Angebotsfrist. Ein fehlendes Feld ist dort die richtige Antwort",
        "und kein Datenverlust.",
        "",
        "## Befund: `pastPublications` fuehrt keinen Titel",
        "",
        "Kein einziger der 31 gemessenen Historie-Eintraege traegt `title`. Die",
        "Eintraege fuehren `publicationNumber`, `pubType`, `publicationDate` und",
        "`id`, aber keinen Titel — `HistoryEntry.title` ist deshalb immer `null`.",
        "Nicht stillschweigend entfernt, weil das Feld zur Antwortform gehoert und",
        "die Quelle es jederzeit nachliefern kann; `test_die_historie_fuehrt_"
        "keinen_titel` haelt den Stand fest und faellt, wenn sie es tut.",
        "",
    ]


def _warne_bei_ignorierten(entries: list[dict[str, Any]]) -> int:
    """Meldet Aufzeichnungen, die `.gitignore` ausschliesst.

    Eine ignorierte Fixture faellt lokal nicht auf — die Datei liegt ja da und
    die Suite ist gruen. Erst die CI klont ein Repo ohne sie und wird rot, mit
    einer Fehlermeldung, die nach einem Aufzeichnungsproblem aussieht statt nach
    einer Regel in `.gitignore`. In `swiss-housing-mcp` ist genau das passiert.
    """
    pfade = [str(FIXTURES / e["name"]) for e in entries]
    try:
        ergebnis = subprocess.run(
            ["git", "check-ignore", *pfade], capture_output=True, text=True, check=False
        )
    except OSError:
        return 0  # kein git zur Hand — kein Grund, das Aufzeichnen scheitern zu lassen
    ignoriert = [z for z in ergebnis.stdout.splitlines() if z.strip()]
    if ignoriert:
        print("\n!! Diese Aufzeichnungen schliesst .gitignore aus, sie fehlen der CI:")
        for z in ignoriert:
            print(f"     {z}")
        return 1
    return 0


def _write_provenance(recorded_at: str, entries: list[dict[str, Any]], befund: list[str]) -> None:
    lines = [
        "# Herkunft der Fixtures",
        "",
        "**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**",
        "",
        f"Aufgezeichnet am **{recorded_at}** von der Quelle dieses Servers: `{BASE}`.",
        "",
        "Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht",
        "mehr zu unterscheiden — die Datei sieht gleich aus.",
        "",
        "**Ein Teil sind Ausschnitte, keine Vollabzuege.** Die Auswahlregel steht",
        "je Datei dabei; **kein Feld wurde entfernt**, gekuerzt ist nur die Zahl",
        "der Eintraege. Eine Fixture belegt damit die *Form* der Antwort und einen",
        "datierten Ausschnitt ihres Inhalts — nicht den Bestand. Aussagen ueber",
        "Vollstaendigkeit gehoeren in `tests/test_live.py`.",
        "",
        "**Die Eintraege sind gewaehlt, nicht genommen.** Die ersten Aemter der",
        "1.1-MB-Liste tragen alle denselben `type`, und die ersten Institutionen",
        "waeren lauter Wurzeln ohne ein einziges Kind. Eine Kopfauswahl haette",
        "beide Formen nie belegt.",
        "",
        "**Lose sind die Auswahlachse dieses Servers.** Publikationen mit Losen",
        '(`lotsType: "with"`) verhalten sich an mehreren Endpunkten anders:',
        "`publication-details` fuellt `lot`, der Suchtreffer traegt eine",
        "verschachtelte `lots`-Liste, und `past-publications` verweigert die",
        "Auskunft ganz. Aufgezeichnet ist deshalb je ein Fall von beiden.",
        "",
        *befund,
        "Fehlerpfade — Timeouts, 5xx, ein maskierter Verbindungsabbruch — bleiben",
        "handgeschrieben. Die lassen sich nicht auf Zuruf aufzeichnen. Der eine",
        "aufgezeichnete 400er ist keine Ausnahme davon, sondern ein Befund: er",
        "trifft nicht einen Fehlerfall, sondern jede losbasierte Beschaffung.",
        "",
    ]
    for e in entries:
        groesse = f"- **Groesse:** {e['bytes']} B"
        if e["total"]:
            groesse += f" (Quelle: {e['total']})"
        lines += [
            f"## `{e['name']}`",
            "",
            f"- **Quelle:** `{e['url']}`",
            f"- **Aufgezeichnet:** {recorded_at}",
            f"- **Auswahl:** {e['rule']}",
            groesse,
            f"- **SHA-256:** `{e['sha256']}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
