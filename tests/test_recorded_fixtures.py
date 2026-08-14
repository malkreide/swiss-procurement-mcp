"""Jeder externe Endpunkt, gefahren aus einer aufgezeichneten Antwort.

Die handgeschriebenen Stubs im Rest der Suite pruefen die *Fehler*-Pfade — ein
Timeout, ein 503, ein maskierter Verbindungsabbruch —, die sich nicht auf Zuruf
aufzeichnen lassen und als Erfindung in Ordnung sind. Was sie nicht koennen: die
Form einer Erfolgs-Antwort belegen. Sie stimmen mit dem ueberein, was ihr Autor
annahm.

Genau daran ist hier etwas vorbeigegangen: `detail_payload` in `conftest.py`
erfand einen `dates`-Block fuer einen Zuschlag. Die Quelle liefert den nur bei
Ausschreibungen, und der Mapper las das Publikationsdatum ausschliesslich dort —
also lieferte `get_procurement_details` fuer jeden Zuschlag `publication_date:
null`, waehrend die Suite gruen blieb.

Herkunft, Datum, Auswahlregel und SHA-256 je Datei stehen in
`tests/fixtures/PROVENANCE.md`; neu aufzeichnen mit
`python scripts/record_fixtures.py`.
"""

from __future__ import annotations

import datetime as dt
import re

import httpx
import pytest
import respx
from fixture_data import fixture_json, provenance, recorded_names

from swiss_procurement_mcp.constants import CANTON_INSTITUTION_IDS, SIMAP_BASE
from swiss_procurement_mcp.inputs import (
    CpvSearchInput,
    HistoryInput,
    OfficeSearchInput,
    ProcurementDetailInput,
    SearchInput,
)
from swiss_procurement_mcp.server import (
    find_procurement_office,
    get_procurement_details,
    get_publication_history,
    search_cpv_codes,
    search_procurements,
)

# Jeder externe Endpunkt dieses Servers und die Fixture dazu. Ein Endpunkt ohne
# Aufzeichnung faellt in `test_jeder_endpunkt_hat_eine_aufzeichnung`.
ENDPUNKTE = {
    "cantons/v1": "cantons.json",
    "publications/v2/project/project-search": "project_search.json",
    "publications/v1/project/{pid}/publication-details/{pubid}": "publication_details.json",
    "publications/v1/publication/{pubid}/past-publications": "past_publications.json",
    "codes/v1/{system}/search": "codes_cpv.json",
    "institutions/v1/institutions": "institutions.json",
    "procoffices/v1/po/public": "procoffices.json",
}

SEARCH_URL = f"{SIMAP_BASE}/publications/v2/project/project-search"


def _projekt(pubtype: str, lots: str) -> dict:
    """Ein Projekt aus der aufgezeichneten Suche, nach seiner Achse gewaehlt."""
    treffer = [
        p
        for p in fixture_json("project_search.json")["projects"]
        if p["pubType"] == pubtype and p["lotsType"] == lots
    ]
    assert treffer, f"keine aufgezeichnete Publikation {pubtype}/{lots} — neu aufzeichnen"
    return treffer[0]


# --------------------------------------------------------------------------
# Herkunft
# --------------------------------------------------------------------------


def test_provenance_nennt_ein_brauchbares_aufnahmedatum():
    """Eine Aufzeichnung ohne Datum ist eine undatierte Behauptung ueber die Quelle."""
    match = re.search(r"Aufgezeichnet am \*\*(\d{4}-\d{2}-\d{2})\*\*", provenance())
    assert match, "PROVENANCE.md nennt kein Aufnahmedatum im erwarteten Format"
    when = dt.date.fromisoformat(match.group(1))
    assert when <= dt.datetime.now(dt.timezone.utc).date(), "Aufnahmedatum liegt in der Zukunft"


def test_jede_fixture_steht_in_der_provenance():
    """Sonst waechst der Ordner und der Nachweis bleibt zurueck."""
    text = provenance()
    fehlend = [n for n in recorded_names() if f"## `{n}`" not in text]
    assert not fehlend, f"ohne Eintrag in PROVENANCE.md: {fehlend}"


def test_jeder_endpunkt_hat_eine_aufzeichnung():
    """Bewacht die Regel selbst: eine aufgezeichnete Antwort je externem Endpunkt."""
    fehlend = sorted(set(ENDPUNKTE.values()) - set(recorded_names()))
    assert not fehlend, f"Endpunkte ohne Aufzeichnung: {fehlend}"


@pytest.mark.parametrize("name", sorted(ENDPUNKTE.values()))
def test_jede_aufzeichnung_ist_nicht_leer(name):
    """Eine leere Aufzeichnung sieht aus wie eine gueltige und prueft nichts."""
    assert fixture_json(name), f"{name} ist leer — neu aufzeichnen"


# --------------------------------------------------------------------------
# Suche
# --------------------------------------------------------------------------


@respx.mock
async def test_suche_aus_der_aufzeichnung():
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json=fixture_json("project_search.json"))
    )
    ergebnis = await search_procurements(SearchInput(canton="ZH", published_from="2026-08-01"))

    aufgezeichnet = fixture_json("project_search.json")["projects"]
    assert ergebnis.count == len(aufgezeichnet)
    assert all(r.title for r in ergebnis.results), "kein Treffer darf ohne Titel herauskommen"
    assert all(r.project_id and r.publication_id for r in ergebnis.results)


@respx.mock
async def test_die_suche_traegt_publikationen_ohne_strukturierte_adresse():
    """Belegt den Grund, warum dieser Server nicht ueber die Adresse filtert.

    60.6 Prozent der Publikationen tragen `orderAddress.cantonId: null` und sind
    fuer den Adressfilter der Quelle unsichtbar. Ein erfundener Stub setzt dort
    selbstverstaendlich einen Kanton — und verdeckt damit genau den Fall, wegen
    dem `issuedByOrganizations` der Standard ist.
    """
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json=fixture_json("project_search.json"))
    )
    ergebnis = await search_procurements(SearchInput(canton="ZH"))
    assert any(r.canton is None for r in ergebnis.results), (
        "die Aufzeichnung soll eine Publikation ohne strukturierte Adresse enthalten"
    )
    assert any(r.canton for r in ergebnis.results), "und eine mit"


# --------------------------------------------------------------------------
# Detail: drei Formen desselben Endpunkts
# --------------------------------------------------------------------------


@respx.mock
async def test_detail_aus_der_aufzeichnung():
    projekt = _projekt("award", "without")
    respx.get(url__startswith=f"{SIMAP_BASE}/publications/v1/project/").mock(
        return_value=httpx.Response(200, json=fixture_json("publication_details.json"))
    )
    detail = await get_procurement_details(
        ProcurementDetailInput(project_id=projekt["id"], publication_id=projekt["publicationId"])
    )
    assert detail.title, "der Titel darf nicht leer herauskommen"
    assert detail.process_type


@respx.mock
async def test_ein_zuschlag_traegt_trotzdem_ein_publikationsdatum():
    """Der Befund, der diese Aufzeichnung aufgedeckt hat.

    `dates` gibt es nur bei Ausschreibungen — gemessen 40 von 90 Publikationen.
    Der Mapper las das Publikationsdatum ausschliesslich dort und lieferte
    deshalb fuer jeden Zuschlag `null`, obwohl die Quelle es in
    `base.publicationDate` mitschickt (90 von 90).

    Der handgeschriebene Stub hatte ein `dates` erfunden, das es bei einem
    Zuschlag nie gibt; die Suite stimmte damit dem Mapper zu statt der Quelle.
    """
    aufzeichnung = fixture_json("publication_details.json")
    assert "dates" not in aufzeichnung, (
        "die Aufzeichnung soll ein Zuschlag ohne `dates` sein — sonst prueft dieser Test nichts"
    )
    projekt = _projekt("award", "without")
    respx.get(url__startswith=f"{SIMAP_BASE}/publications/v1/project/").mock(
        return_value=httpx.Response(200, json=aufzeichnung)
    )
    detail = await get_procurement_details(
        ProcurementDetailInput(project_id=projekt["id"], publication_id=projekt["publicationId"])
    )
    assert detail.publication_date == aufzeichnung["base"]["publicationDate"]


@respx.mock
async def test_eine_ausschreibung_traegt_ihre_angebotsfrist():
    """`dates` ist die Form der Ausschreibung, und nur dort steht die Frist."""
    aufzeichnung = fixture_json("publication_details_tender.json")
    assert aufzeichnung["dates"]["offerDeadline"], "die Aufzeichnung soll eine Frist tragen"
    projekt = _projekt("tender", "without")
    respx.get(url__startswith=f"{SIMAP_BASE}/publications/v1/project/").mock(
        return_value=httpx.Response(200, json=aufzeichnung)
    )
    detail = await get_procurement_details(
        ProcurementDetailInput(project_id=projekt["id"], publication_id=projekt["publicationId"])
    )
    assert detail.offer_deadline == aufzeichnung["dates"]["offerDeadline"]
    assert detail.publication_date


def test_ein_zuschlag_mit_losen_fuellt_lot():
    """Die Achse dieses Servers, an der Aufzeichnung statt an der Annahme.

    Ein losbasierter Zuschlag fuellt `lot`; einer ohne Lose laesst es null. Zwei
    erfundene Fixtures haetten hier leicht dieselbe Form gezeigt.
    """
    mit = fixture_json("publication_details_lot.json")
    ohne = fixture_json("publication_details.json")
    assert isinstance(mit.get("lot"), dict), "der losbasierte Zuschlag traegt `lot`"
    assert mit["lot"].get("lotNumber") is not None
    assert ohne.get("lot") is None, "der Zuschlag ohne Lose laesst `lot` null"


# --------------------------------------------------------------------------
# Historie — und was die Quelle bei Losen antwortet
# --------------------------------------------------------------------------


@respx.mock
async def test_historie_aus_der_aufzeichnung():
    aufzeichnung = fixture_json("past_publications.json")
    assert aufzeichnung["pastPublications"], "die Aufzeichnung soll Vorgaenger tragen"
    respx.get(url__startswith=f"{SIMAP_BASE}/publications/v1/publication/").mock(
        return_value=httpx.Response(200, json=aufzeichnung)
    )
    verlauf = await get_publication_history(
        HistoryInput(publication_id=_projekt("award", "without")["publicationId"])
    )
    assert verlauf.count == len(aufzeichnung["pastPublications"])
    # Die Quelle nennt den Schluessel `id`, nicht `publicationId` — der Mapper
    # liest beide. Eine erfundene Fixture haette den bequemeren Namen gewaehlt.
    assert all("publicationId" not in e for e in aufzeichnung["pastPublications"])
    assert all(e.publication_id for e in verlauf.publications)


def test_die_historie_fuehrt_keinen_titel():
    """Haelt einen Stand fest, den nur eine Aufzeichnung datieren kann.

    Kein einziger der gemessenen Historie-Eintraege traegt `title`, deshalb ist
    `HistoryEntry.title` immer null. Liefert die Quelle wieder Titel, faellt
    dieser Test — dann gehoert das Feld gefuellt und der Befund gestrichen.
    """
    eintraege = fixture_json("past_publications.json")["pastPublications"]
    assert all("title" not in e for e in eintraege)
    assert "fuehrt keinen Titel" in provenance(), (
        "der Befund gehoert datiert in den Nachweis, nicht nur in diesen Test"
    )


@respx.mock
async def test_die_historie_verweigert_lose():
    """Der zweite Befund: bei Losen antwortet die Quelle mit HTTP 400.

    Gemessen ueber 74 Publikationen: alle 9 mit Losen antworten 400/E0003, alle
    65 ohne antworten 200. Das ist kein erfundener Fehlerfall, sondern die
    Antwort der Quelle auf einen ganzen Fall — jede losbasierte Beschaffung.

    Der Server macht daraus richtigerweise eine degradierte Antwort statt eines
    Absturzes. Faellt dieser Test, weil die Quelle wieder 200 liefert, ist das
    eine gute Nachricht — dann gehoert die Aufzeichnung erneuert.
    """
    fehler = fixture_json("past_publications_lot_400.json")
    assert fehler["errorCode"] == "E0003"
    respx.get(url__startswith=f"{SIMAP_BASE}/publications/v1/publication/").mock(
        return_value=httpx.Response(400, json=fehler)
    )
    verlauf = await get_publication_history(
        HistoryInput(publication_id=_projekt("award", "with")["publicationId"])
    )
    assert verlauf.provenance == "degraded"
    assert verlauf.count == 0
    assert not verlauf.publications
    # Der Fehlerkoerper der Quelle bleibt drinnen: der Hinweis an den Nutzer
    # nennt `E0003` nicht. Das ist Absicht und keine Luecke — der Code steht im
    # Nachweis, wo er hingehoert, und nicht in einer Tool-Antwort.
    assert "E0003" not in (verlauf.note or "")


# --------------------------------------------------------------------------
# Nachschlagewerke
# --------------------------------------------------------------------------


@respx.mock
async def test_cpv_suche_aus_der_aufzeichnung():
    respx.get(url__startswith=f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
        return_value=httpx.Response(200, json=fixture_json("codes_cpv.json"))
    )
    ergebnis = await search_cpv_codes(CpvSearchInput(query="Metall"))
    assert ergebnis.count > 0
    assert all(c.code and c.label for c in ergebnis.codes), "kein Code ohne Bezeichnung"


def test_bkp_verschachtelt_seine_codes():
    """Derselbe Endpunkt, zwei Formen: CPV ist flach, BKP traegt Unter-Codes."""
    bkp = fixture_json("codes_bkp.json")["codes"]
    assert any(isinstance(c.get("codes"), list) and c["codes"] for c in bkp), (
        "die BKP-Antwort verschachtelt Codes unter `codes`"
    )


@respx.mock
async def test_aemtersuche_aus_der_aufzeichnung():
    aufzeichnung = fixture_json("procoffices.json")
    # Der Name kommt hier als blanker String, nicht als Sprachwoerterbuch wie
    # ueberall sonst. `pick_lang` faengt beides — belegt ist es erst hier.
    assert all(isinstance(a["name"], str) for a in aufzeichnung["procOffices"])
    fragment = aufzeichnung["procOffices"][0]["name"].split()[0]
    respx.get(url__startswith=f"{SIMAP_BASE}/procoffices/v1/po/public").mock(
        return_value=httpx.Response(200, json=aufzeichnung)
    )
    ergebnis = await find_procurement_office(OfficeSearchInput(name_contains=fragment))
    assert ergebnis.count > 0
    assert all(o.name for o in ergebnis.offices)


def test_die_aufgezeichneten_aemter_decken_jeden_typ_ab():
    """Die ersten Eintraege der 1.1-MB-Liste tragen alle denselben `type`."""
    typen = {a["type"] for a in fixture_json("procoffices.json")["procOffices"]}
    assert len(typen) >= 8, f"nur {len(typen)} Amtstypen aufgezeichnet — Auswahlregel pruefen"


# --------------------------------------------------------------------------
# Institutionen: die Ids, an denen der Kantonsfilter haengt
# --------------------------------------------------------------------------


def test_die_gepinnten_kantons_ids_stehen_in_der_aufzeichnung():
    """Bisher belegte das nur der Live-Test — jetzt auch eine datierte Antwort.

    `CANTON_INSTITUTION_IDS` ist ein handgeschriebener Literal-Block von 26
    UUIDs, und der Kantonsfilter dieses Servers haengt vollstaendig daran. Eine
    falsche Id liefert stillschweigend keine Treffer statt eines Fehlers.
    """
    bekannt = {i["id"] for i in fixture_json("institutions.json")["institutions"]}
    fehlend = {k: v for k, v in CANTON_INSTITUTION_IDS.items() if v not in bekannt}
    assert not fehlend, f"nicht in der Aufzeichnung: {fehlend}"


def test_die_aufzeichnung_haelt_alle_wurzeln():
    """28 Wurzeln: 26 Kantone, Bund und Ausland."""
    inst = fixture_json("institutions.json")["institutions"]
    wurzeln = [i for i in inst if i["parentInstitutionId"] is None]
    assert len(wurzeln) == 28, f"{len(wurzeln)} Wurzeln statt 28 — Taxonomie geprueft?"


def test_aemter_und_institutionen_zeigen_nicht_aneinander_vorbei():
    """Zwei Ausschnitte derselben Quelle koennen leicht auseinanderlaufen.

    Jedes aufgezeichnete Amt zeigt ueber `institutionId` in den Baum, und genau
    diese Verbindung traegt den Kantonsfilter (`issuedByOrganizations`). Der
    Recorder nimmt deshalb zu jedem Amt die ganze Ahnenkette auf. Ohne diese
    Zusicherung faellt das beim naechsten Aufzeichnen niemandem auf.
    """
    inst = {i["id"]: i for i in fixture_json("institutions.json")["institutions"]}
    aemter = fixture_json("procoffices.json")["procOffices"]
    for amt in aemter:
        knoten = inst.get(amt["institutionId"])
        assert knoten is not None, f"Amt {amt['name']!r} zeigt auf eine fehlende Institution"
        while knoten["parentInstitutionId"] is not None:
            knoten = inst.get(knoten["parentInstitutionId"])
            assert knoten is not None, f"Ahnenkette von {amt['name']!r} bricht ab"


def test_die_kantonsliste_ist_nicht_iso_kodiert():
    """Probe-Befund, jetzt an der Quelle statt an der Erinnerung: `ZH`, nicht `CH-ZH`."""
    ids = [c["id"] for c in fixture_json("cantons.json")["cantons"]]
    assert len(ids) == 26
    assert all(len(i) == 2 and i.isupper() for i in ids), f"unerwartete Kantons-Ids: {ids[:5]}"
