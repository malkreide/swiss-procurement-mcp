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

    # Beide Achsen pinnen, nicht nur `lotsType`. Diese Zeile nahm die ERSTE
    # Publikation mit Losen, waehrend die Fixture und ihr Test einen ZUSCHLAG
    # mit Losen behaupten. Am 29.8.2026 war die erste eine Abbruchpublikation:
    # die traegt `abandonedLot` statt `lot`, `lot` blieb null, und die
    # Aufzeichnung belegte still einen anderen Fall als den benannten.
    mit_losen = erster(lambda p: p.get("lotsType") == "with" and p.get("pubType") == "award")
    ohne_lose = erster(lambda p: p.get("lotsType") == "without" and p.get("pubType") == "award")
    ausschreibung = erster(lambda p: p.get("pubType") == "tender")
    assert mit_losen, "die Suche traegt keinen Zuschlag mit Losen — Suchbegriff pruefen"
    assert ohne_lose, "die Suche traegt keinen Zuschlag ohne Lose — Suchbegriff pruefen"
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

    # Dieselbe Los-Publikation zweimal: einmal ohne `lotId`, einmal mit. Der
    # Unterschied IST der Befund, deshalb stehen beide Antworten nebeneinander.
    # Eine Aufzeichnung nur des 400ers hat schon einmal die falsche Lehre
    # gestuetzt, die Quelle verweigere Lose.
    pfad = f"/publications/v1/publication/{mit_losen['publicationId']}/past-publications"
    status, fehler = get(pfad, lang=LANG)
    assert status == 400, f"past-publications ohne lotId antwortete {status}, erwartet 400"
    write(
        "past_publications_lot_400.json",
        {k: v for k, v in fehler.items() if k != "timestamp"},
        url_of(pfad, lang=LANG),
        f"vollstaendig bis auf `timestamp` (der aendert sich bei jedem Aufruf und "
        f"erzeugte sonst einen Diff ohne Aussage); Publikation "
        f"{mit_losen['publicationNumber']} mit Losen, OHNE `lotId` — HTTP {status}. "
        "Kein erfundener Fehlerpfad, sondern die Antwort der Quelle auf einen "
        "fehlenden Parameter; siehe Befund oben",
    )

    # `lose[0]` ist NICHT verlaesslich das Los, das antwortet: die Historie wird
    # je Los gefuehrt, und ein Los ohne eigene Vorgaengerpublikation antwortet
    # 404 statt 200 mit leerer Liste. Gemessen am 8.9.2026 an Publikation
    # 32705-42: 1 von 39 Losen antwortete, 38 gaben 404. Genau darauf lief der
    # rote Lauf vom 5.9.2026 — hier wie im Live-Test wurde das erste Los
    # genommen und sein 404 als «der Parameter hilft nicht mehr» gelesen.
    # Was nicht sondiert werden kann, ist nicht «geprueft». Ein Los ohne `lotId`
    # und eine Publikation mit `lotsType: "with"` und leerer `lots`-Liste sind
    # beide genau die Regression, die `_lot_publication_that_answers` im
    # Live-Test bewusst als Fehlschlag behandelt — der Mapper liess `lots` schon
    # einmal fallen. Wer sie hier still ueberspringt, kann anschliessend auf
    # eine luekenhafte Sondierung hin loeschen.
    unsondierbar: list[str] = []
    alle_lose = mit_losen.get("lots") or []
    lose = [lot for lot in alle_lose if lot.get("lotId")]
    assert lose, "der Suchtreffer mit Losen fuehrt keine `lotId`"
    if len(lose) != len(alle_lose):
        unsondierbar.append(
            f"{mit_losen['publicationNumber']}: {len(alle_lose) - len(lose)} Los(e) ohne `lotId`"
        )

    lot_id = None
    mit_lot: Any = None
    stummes_lot = None
    stumme_antwort: Any = None
    # Nur 200 und 404 sind hier eine Auskunft. Jeder andere Status ist eine
    # Stoerung, und eine Stoerung als «antwortet normal» zu zaehlen ist genau
    # der Fehler, den CLAUDE.md am 403 festhaelt: entscheidend ist nicht der
    # Statuscode, sondern ob die Quelle ueberhaupt geantwortet hat. Ein 429
    # oder 500 mitten in der Sondierung liesse `stummes_lot` sonst leer — und
    # das Skript loeschte Aufzeichnung und Befund, ohne je festgestellt zu
    # haben, dass die Lose jetzt antworten.
    unklar: list[int] = []
    for lot in lose:
        status, koerper = get(pfad, lang=LANG, lotId=lot["lotId"])
        if status == 200 and lot_id is None:
            lot_id, mit_lot = lot["lotId"], koerper
        elif status == 404 and stummes_lot is None:
            stummes_lot, stumme_antwort = lot["lotId"], koerper
        elif status not in (200, 404):
            unklar.append(status)
        if lot_id is not None and stummes_lot is not None:
            break

    assert lot_id is not None, (
        f"kein einziges der {len(lose)} Lose von {mit_losen['publicationNumber']} "
        "antwortete mit 200 — dann traegt die Aufzeichnung den Befund nicht mehr"
    )
    write(
        "past_publications_lot.json",
        mit_lot,
        url_of(pfad, lang=LANG, lotId=lot_id),
        f"vollstaendig; dieselbe Publikation {mit_losen['publicationNumber']} wie "
        f"`past_publications_lot_400.json`, nur mit der `lotId` des ersten Loses, "
        f"das antwortet — HTTP 200, {len(mit_lot.get('pastPublications') or [])} "
        "Vorgaenger. Die Gegenprobe zum 400er: derselbe Aufruf, ein Parameter mehr",
    )

    # Findet sich in DIESER Publikation kein stummes Los, ist der Befund damit
    # nicht widerlegt: die Tabelle im Nachweis fuehrt selbst Publikationen, bei
    # denen jedes Los antwortet (36106-03 9 von 9, 43734-01 7 von 7). Aus einer
    # dynamisch gewaehlten Publikation auf die Quelle zu schliessen, waere
    # genau die `lots[0]`-Falle ein drittes Mal — nur mit einem geloeschten
    # richtigen Befund als Folge. Also erst die uebrigen Los-Publikationen der
    # Suchantwort durchgehen.
    stumm_aus = mit_losen
    if stummes_lot is None:
        weitere = [
            pr
            for pr in alle
            if pr.get("lotsType") == "with" and pr["publicationId"] != mit_losen["publicationId"]
        ]
        for projekt in weitere:
            anderer = f"/publications/v1/publication/{projekt['publicationId']}/past-publications"
            kandidaten = [lot for lot in (projekt.get("lots") or []) if lot.get("lotId")]
            if len(kandidaten) != len(projekt.get("lots") or []) or not kandidaten:
                unsondierbar.append(
                    f'{projekt["publicationNumber"]}: `lotsType` "with", aber '
                    f"{len(kandidaten)} von {len(projekt.get('lots') or [])} Los(en) "
                    "mit `lotId`"
                )
            for lot in kandidaten:
                status, koerper = get(anderer, lang=LANG, lotId=lot["lotId"])
                if status == 404:
                    stummes_lot, stumme_antwort, stumm_aus = lot["lotId"], koerper, projekt
                    break
                if status != 200:
                    unklar.append(status)
            if stummes_lot is not None:
                break
        geprueft = 1 + len(weitere)
    else:
        geprueft = 1

    # Eine unvollstaendige Sondierung darf nicht in eine Loeschung muenden.
    # Abbrechen statt weitermachen: ein halber Nachweis ist schlechter als
    # keiner, und die Aufzeichnung bleibt so unangetastet.
    assert stummes_lot is not None or not (unklar or unsondierbar), (
        "die Sondierung der Lose blieb unvollstaendig — damit ist nicht festgestellt, "
        "ob noch ein Los mit 404 antwortet, und eine Loeschung stuende auf einer "
        "Luecke statt auf einer Messung. "
        + (f"unerwartete Statuscodes: {sorted(set(unklar))}. " if unklar else "")
        + (f"nicht sondierbar: {unsondierbar}. " if unsondierbar else "")
        + "Erst wenn jede Los-Referenz erreichbar ist und jede Sonde 200 oder 404 "
        "liefert, traegt das Ergebnis eine Entscheidung"
    )

    # Der dritte Fall, und der Grund, warum es ihn gibt: eine Aufzeichnung nur
    # des 200ers kann nicht zeigen, dass ein 404 hier keine Stoerung ist.
    if stummes_lot is not None:
        stumm_pfad = f"/publications/v1/publication/{stumm_aus['publicationId']}/past-publications"
        woher = (
            f"dieselbe Publikation {mit_losen['publicationNumber']}, ein anderes Los"
            if stumm_aus is mit_losen
            else (
                f"Publikation {stumm_aus['publicationNumber']} aus derselben Suche — "
                f"in {mit_losen['publicationNumber']} lieferte kein sondiertes Los "
                "einen 404"
            )
        )
        write(
            "past_publications_lot_404.json",
            {k: v for k, v in stumme_antwort.items() if k != "requestCorrelator"},
            url_of(stumm_pfad, lang=LANG, lotId=stummes_lot),
            f"vollstaendig bis auf `requestCorrelator` (aendert sich bei jedem "
            f"Aufruf); {woher} — HTTP 404. Kein erfundener Fehlerpfad: die Antwort "
            "der Quelle auf ein Los ohne eigene Vorgaengerpublikation. Denselben "
            "Koerper liefert sie fuer eine erfundene `publicationId` und eine "
            "erfundene `lotId`, sie trennt die Faelle also nicht",
        )
    else:
        # Antwortet kein Los mehr mit 404, ist der Befund weg — und dann muss die
        # Aufzeichnung mit. Bliebe sie liegen, liefe der Fixture-Test weiter
        # gruen gegen eine Datei, die die Quelle nicht mehr hergibt, waehrend der
        # Nachweis das verschwundene Verhalten unveraendert behauptet. Genau die
        # Konstellation, aus der der falsche 400er-Befund entstand: eine
        # Aufzeichnung, der niemand mehr widersprechen kann.
        #
        # Geloescht wird deshalb erst, wenn KEINE der Los-Publikationen dieser
        # Suche ein stummes Los mehr hat — eine reicht dafuer nicht.
        veraltet = FIXTURES / "past_publications_lot_404.json"
        hinweis = f"kein Los aus {geprueft} Los-Publikation(en) antwortete 404"
        if veraltet.exists():
            veraltet.unlink()
            print(f"  weg past_publications_lot_404.json    {hinweis}")
        else:
            print(f"  --  past_publications_lot_404.json  {hinweis}")

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

    befund = (
        _befund(
            mit_losen,
            ohne_lose,
            lot_id,
            len(mit_lot.get("pastPublications") or []),
            mit_404=stummes_lot is not None,
        )
        + _befund_datum()
    )
    _write_provenance(recorded_at, entries, befund)
    print(f"\nPROVENANCE.md geschrieben, Aufzeichnungsdatum {recorded_at}")
    return _warne_bei_ignorierten(entries)


def _befund(
    mit_losen: dict[str, Any],
    ohne_lose: dict[str, Any],
    lot_id: str,
    vorgaenger: int,
    *,
    mit_404: bool,
) -> list[str]:
    """`mit_404` haelt den Nachtrag an seinen Beleg.

    Antwortet kein Los mehr mit 404, ist die Aufzeichnung dazu geloescht — dann
    darf der Nachweis das Verhalten nicht weiter behaupten. Ein Befund, der
    seine Aufzeichnung ueberlebt, ist wieder eine undatierte Behauptung ueber
    die Quelle.
    """
    return [
        "## Befund: `past-publications` braucht bei Losen einen `lotId`",
        "",
        "**Dieser Befund ersetzt einen falschen.** Bis zum 29.8.2026 stand hier,",
        "die Quelle «verweigere die Auskunft ganz», wenn eine Publikation Lose",
        "hat. Belegt war dafuer nur ein HTTP 400 — und aus einem 400 folgt eine",
        "Verweigerung nicht. Der Endpunkt fuehrt laut eigener Spec einen",
        "optionalen Parameter `lotId`; er ist bei Losen nicht optional. Mit ihm",
        "antwortet dieselbe Publikation mit 200 und liefert ihre Vorgaenger.",
        "",
        "Gemessen am 29.8.2026 ueber 80 Publikationen aus vier Suchbegriffen",
        "(Bau, Software, Strasse, Reinigung), ausnahmslos:",
        "",
        "| `lotsType` | ohne `lotId` | mit `lotId` | Faelle |",
        "|---|---|---|---|",
        "| `without` | HTTP 200 | — (404: ein fremdes Los gibt es dort nicht) | 76 |",
        "| `with` | HTTP 400, `errorCode: E0003` | HTTP 200 | 4 |",
        "",
        f"Beispiel: {mit_losen['publicationNumber']} (mit Losen) → HTTP 400; dieselbe",
        f"Publikation mit `lotId={lot_id}` → HTTP 200 mit {vorgaenger} Vorgaenger(n);",
        f"{ohne_lose['publicationNumber']} (ohne Lose) → HTTP 200.",
        "",
        "Wirkung des Fehlschlusses: `get_publication_history` gab fuer jede",
        "losbasierte Beschaffung eine degradierte Antwort mit `count: 0` und dem",
        "Hinweis, simap.ch sei «unreachable» — fuer einen Zustand, der weder",
        "voruebergehend noch der Quelle anzulasten war. Ein gemessener Fall trug",
        "sieben Vorgaenger, die der Server samt und sonders wegwarf. Die",
        "Unit-Tests blieben dabei gruen, weil die Aufzeichnung nur den 400er",
        "hielt und der Test ihm zustimmte.",
        "",
        "Beide Antworten liegen deshalb jetzt nebeneinander:",
        "`past_publications_lot_400.json` (ohne Parameter) und",
        "`past_publications_lot.json` (mit). Der Unterschied zwischen ihnen ist",
        "der Befund; eine Aufzeichnung allein von einer der beiden Seiten kann",
        "ihn nicht tragen.",
        "",
    ] + (
        []
        if not mit_404
        else [
            "### Nachtrag 8.9.2026: der Parameter allein genuegt nicht",
            "",
            "Die Tabelle oben liest sich, als antworte jede Los-Publikation mit",
            "`lotId` mit 200. Das gilt fuer die Publikation, nicht fuer jedes Los.",
            "Die Historie wird **je Los** gefuehrt, und ein Los ohne eigene",
            "Vorgaengerpublikation antwortet 404 — nicht 200 mit leerer Liste.",
            "",
            "| Publikation | Lose | davon HTTP 200 | davon HTTP 404 |",
            "|---|---|---|---|",
            "| 32705-42 | 39 | 1 | 38 |",
            "| 39386-02 | 4 | 1 | 3 |",
            "| 36106-03 | 9 | 9 | 0 |",
            "| 43734-01 | 7 | 7 (je 0 Vorgaenger) | 0 |",
            "",
            "43734-01 ist die Zeile, die eine einfache Regel verbietet: dort ist die",
            "leere Historie ein 200 mit `pastPublications: []`, kein 404. Was den",
            "einen Fall vom anderen trennt, ist damit **nicht gemessen** — nur, dass",
            "beide vorkommen.",
            "",
            "Wirkung: der geplante Live-Lauf vom 5.9.2026 lief rot, weil Test und",
            "Recorder `lots[0]` nahmen und dessen 404 als «der Parameter hilft nicht",
            "mehr» lasen. Das ist dieselbe Falle wie `results[0]` — eine Zusicherung",
            "ueber den Tag statt ueber den Server. Produktiv wog schwerer, dass der",
            "404 in den generischen Hinweis fiel: «unreachable ... please retry",
            "shortly», fuer eine Absage, die sich bei jeder Wiederholung wiederholt.",
            "",
            "Die Quelle trennt die Ursachen nicht. Denselben Koerper",
            "(`Document not found.`) liefert sie fuer ein echtes Los ohne Historie,",
            "eine erfundene `lotId` und eine erfundene `publicationId` — gemessen am",
            "8.9.2026. Der Server darf den 404 deshalb **nicht** als leere Historie",
            "ausgeben: bei einer vertippten Id behauptete er sonst «keine",
            "Vorgaenger», wo die Publikation gar nicht existiert. Er bleibt",
            "degradiert und nennt beide Moeglichkeiten, ohne zwischen ihnen zu",
            "entscheiden.",
            "",
            "`past_publications_lot_404.json` haelt diese dritte Antwort fest. Aus",
            "welcher Publikation das stumme Los stammt, sagt die Auswahlregel jener",
            "Datei: dieselbe wie die beiden anderen Aufzeichnungen, wenn dort eines",
            "zu finden war, sonst eine weitere Los-Publikation derselben Suche.",
            "",
        ]
    )


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
        "verschachtelte `lots`-Liste, und `past-publications` verlangt einen",
        "`lotId`. Aufgezeichnet ist deshalb je ein Fall von beiden.",
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
