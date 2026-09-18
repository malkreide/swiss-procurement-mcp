"""Die Aera 2026-07-28, gefahren statt behauptet.

`tests/test_protocol_version.py` haelt den Pin `MCP_PROTOCOL_VERSION` gegen die
Konstanten des SDK und faehrt einen echten `initialize` durch den ASGI-Stack.
Was es faehrt, ist damit ausschliesslich die **Handshake**-Aera — und die
deckelt bei `2025-11-25`. Der Pin nennt eine Revision, die keine einzige
Zusicherung dieses Repos je angesprochen hat.

Das ist dieselbe Klasse wie der handgeschriebene Stub, der die Annahme seines
Autors bestaetigt: nichts war rot, weil nichts geprueft wurde, worauf es
ankommt. Ein Server kann eine Revision pinnen, deren Anfragen er mit 400
beantwortet, und gruen bleiben.

Hier faehrt jede Zusicherung eine echte 2026-07-28-Anfrage: Envelope in
`params._meta`, Routing-Header, eine Antwort pro Anfrage, kein Handshake und
keine Session. Gemessen am 18.9.2026 gegen `mcp` 2.2.0.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib.metadata import version as pkg_version
from typing import Any

import httpx
import pytest
import respx
from fixture_data import fixture_json
from mcp.server.mcpserver import MCPServer
from mcp.shared.inbound import (
    MCP_METHOD_HEADER,
    MCP_NAME_HEADER,
    MCP_PROTOCOL_VERSION_HEADER,
)
from mcp_types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    HEADER_MISMATCH,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    PROTOCOL_VERSION_META_KEY,
    UNSUPPORTED_PROTOCOL_VERSION,
)
from mcp_types.version import LATEST_MODERN_VERSION, MODERN_PROTOCOL_VERSIONS

from swiss_procurement_mcp.__main__ import build_http_app
from swiss_procurement_mcp.constants import SIMAP_BASE
from swiss_procurement_mcp.server import INSTRUCTIONS, LIST_CACHE_TTL_MS, MCP_PROTOCOL_VERSION

SERVER_INFO_META_KEY = "io.modelcontextprotocol/serverInfo"

_BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Host": "127.0.0.1:8000",
}


def _envelope() -> dict[str, Any]:
    """Der Pro-Request-Envelope, ohne den eine 2026-07-28-Anfrage abgelehnt wird.

    Alle drei Schluessel aus dem SDK bezogen statt abgeschrieben: eine
    Umbenennung faellt hier als ImportError auf und nicht als Anfrage, die im
    Feld still mit 400 beantwortet wird.
    """
    return {
        PROTOCOL_VERSION_META_KEY: MCP_PROTOCOL_VERSION,
        CLIENT_INFO_META_KEY: {"name": "modern-era-test", "version": "1"},
        CLIENT_CAPABILITIES_META_KEY: {},
    }


async def _post(
    method: str,
    *,
    params: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    app=None,
) -> tuple[int, dict[str, Any]]:
    """Eine Anfrage durch den echten ASGI-Stack. Gibt (HTTP-Status, JSON) zurueck.

    Der Status wird mitgegeben, weil die Revision ihn als Teil der Antwort
    fuehrt: eine Ablehnung ist nicht nur ein JSON-RPC-Fehlerobjekt, sondern
    auch ein bestimmter HTTP-Code.
    """
    app = app if app is not None else build_http_app("streamable-http")
    body_params: dict[str, Any] = {"_meta": _envelope() if meta is None else meta}
    if params:
        body_params.update(params)

    request_headers = dict(_BASE_HEADERS)
    request_headers[MCP_PROTOCOL_VERSION_HEADER] = MCP_PROTOCOL_VERSION
    request_headers[MCP_METHOD_HEADER] = method
    if params and "name" in params:
        request_headers[MCP_NAME_HEADER] = params["name"]
    if headers:
        request_headers.update(headers)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as c:
            response = await c.post(
                "/mcp",
                headers=request_headers,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": body_params},
            )

    text = response.text
    for line in text.splitlines():  # SSE-Rahmen abstreifen, falls vorhanden
        if line.startswith("data: "):
            text = line[len("data: ") :]
    return response.status_code, json.loads(text)


# --------------------------------------------------------------------------
# Die Aera antwortet ueberhaupt
# --------------------------------------------------------------------------


async def test_discover_beantwortet_eine_echte_envelope_anfrage() -> None:
    """Der lasttragende Fall: ohne ihn sagt der Pin nichts ueber Verhalten.

    `server/discover` ersetzt in dieser Revision den Handshake. Antwortet er
    nicht, ist der Server fuer einen nativen Client nicht erreichbar — und
    genau das haette bisher keine Zusicherung bemerkt.
    """
    status, body = await _post("server/discover")

    assert status == 200, body
    assert "error" not in body, body["error"]
    assert body["result"]["supportedVersions"] == list(MODERN_PROTOCOL_VERSIONS)


async def test_die_gemeldete_revision_ist_die_gepinnte() -> None:
    """Sonst pinnt `MCP_PROTOCOL_VERSION` eine Revision, die der Server nicht bedient."""
    _, body = await _post("server/discover")

    assert MCP_PROTOCOL_VERSION in body["result"]["supportedVersions"]
    assert MCP_PROTOCOL_VERSION == LATEST_MODERN_VERSION


async def test_ohne_envelope_lehnt_der_server_ab() -> None:
    """Die Gegenprobe zu allem darueber.

    Ohne diesen Fall waeren die Zusicherungen oben auch gegen einen Server
    gruen, der den Envelope gar nicht liest und jede Anfrage gleich behandelt.
    """
    status, body = await _post("server/discover", meta={})

    assert status == 400
    assert body["error"]["code"] == INVALID_PARAMS
    assert "envelope" in body["error"]["message"]


async def test_ueber_http_ist_initialize_gar_keine_methode() -> None:
    """Die beiden Aeren mischen sich nicht — ueber HTTP aber anders als ueber stdio.

    Erwartet worden war hier `UNSUPPORTED_PROTOCOL_VERSION` (-32022), der Code,
    den `runner.py` fuer eine moderne Verbindung vorsieht. Gemessen am
    18.9.2026 antwortet der HTTP-Eingang stattdessen `METHOD_NOT_FOUND` mit
    HTTP 404, und das ist nicht der Fehler, sondern der Unterschied: eine
    2026-07-28-Anfrage ueber HTTP ist ein einzelner, in sich geschlossener
    POST. Es gibt keine Verbindung, die eine Aera «bediente» — es gibt nur
    eine Methodentabelle, und `initialize` steht in dieser Revision nicht
    darin. `test_stdio_lehnt_den_handshake_mit_der_aera_ab` faehrt die andere
    Seite; die beiden Codes nebeneinander sind der eigentliche Befund.
    """
    status, body = await _post("initialize")

    assert status == 404
    assert body["error"]["code"] == METHOD_NOT_FOUND


async def test_ein_falscher_name_header_schlaegt_fehl() -> None:
    """Die Revision routet ueber Header; Header und Rumpf muessen uebereinstimmen.

    Wichtiger als der Code ist, dass die Anfrage **nicht** ausgefuehrt wird:
    ein Server, der dem Rumpf folgt und den Header ignoriert, laesst einen
    Proxy, der nur Header liest, ueber das falsche Werkzeug entscheiden.
    """
    status, body = await _post(
        "tools/call",
        params={"name": "search_cpv_codes", "arguments": {"args": {"query": "bau"}}},
        headers={MCP_NAME_HEADER: "source_status"},
    )

    assert status == 400
    assert body["error"]["code"] == HEADER_MISMATCH


# --------------------------------------------------------------------------
# Identitaet: was ein nativer Client ueber diesen Server erfaehrt
# --------------------------------------------------------------------------


async def test_discover_nennt_die_installierte_version() -> None:
    """`tests/test_version_identity.py` oeffnet mit «die Version, die dieser
    Server ankuendigt, muss die sein, die er ist» — und hielt das fuer den
    User-Agent, den simap.ch sieht.

    Die Version, die *MCP-Clients* sehen, hielt nichts. Gemessen am 18.9.2026
    stand dort der leere String, in beiden Aeren, waehrend das Paket auf 0.18.5
    stand. In dieser Revision gibt es keinen Handshake, `server/discover` ist
    die einzige Stelle, an der ein nativer Client fragen kann.

    Kein erwarteter Wert steht hier — geprueft wird die Eigenschaft gegen die
    Metadaten der installierten Distribution, wie im Nachbarfile.
    """
    _, body = await _post("server/discover")
    server_info = body["result"]["_meta"][SERVER_INFO_META_KEY]

    assert server_info["version"] == pkg_version("swiss-procurement-mcp")


async def test_discover_nennt_titel_und_projektadresse() -> None:
    """Der Rest der Identitaet, die `Implementation` fuehrt.

    Der Titel ist das, was ein Client einem Menschen zeigt; die Adresse ist,
    wohin er schaut, wenn dieser Server etwas Unerwartetes tut. `icons` fehlt
    bewusst — dieses Repo liefert keines, und eine erfundene URL waere genau
    der Fehler, den die Version gemacht hat, nur in einem Feld, das niemand
    nachschlaegt.
    """
    _, body = await _post("server/discover")
    server_info = body["result"]["_meta"][SERVER_INFO_META_KEY]

    assert server_info["title"]
    assert server_info["websiteUrl"].startswith("https://github.com/malkreide/")
    assert "icons" not in server_info


async def test_ein_server_ohne_version_meldet_den_leeren_string() -> None:
    """Die Negativkontrolle: dasselbe SDK, derselbe Aufruf, kein `version=`.

    Faellt sie eines Tages aus, weil das SDK selbst eine Version einsetzt, dann
    beweist der Test darueber nicht mehr, dass *wir* sie setzen.
    """
    kontrolle = MCPServer("control")
    _, body = await _post("server/discover", app=kontrolle.streamable_http_app())

    assert body["result"]["_meta"][SERVER_INFO_META_KEY]["version"] == ""


async def test_discover_traegt_die_server_instruktionen() -> None:
    """Die zweite Haelfte derselben Luecke.

    `DiscoverResult.instructions` ist in dieser Revision die einzige
    Server-Ebene, auf der ein Modell Orientierung bekommt, bevor es ein
    Werkzeug waehlt. Sie war leer.
    """
    _, body = await _post("server/discover")

    assert body["result"].get("instructions") == INSTRUCTIONS


@pytest.mark.parametrize(
    "aussage",
    [
        "simap.ch",
        "at least one filter",
        "projects",
    ],
)
def test_die_instruktionen_sagen_das_noetigste(aussage: str) -> None:
    """Ein nicht-leerer String haette den Test darueber auch bestanden.

    Die drei Punkte sind die, an denen ein Modell ohne Vorwissen scheitert:
    woher die Daten kommen, dass eine filterlose Suche nichts liefert, und dass
    ein Treffer ein Projekt und keine Publikation ist.
    """
    assert aussage in INSTRUCTIONS


async def test_beide_aeren_nennen_dieselbe_version() -> None:
    """Die Eigenschaft gilt fuer den Server, nicht fuer eine Aera.

    Ohne diesen Fall koennte die Handshake-Aera wieder auf den leeren String
    zurueckfallen, ohne dass etwas rot wird — dort sitzen heute alle Clients.
    """
    app = build_http_app("streamable-http")
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as c:
            response = await c.post(
                "/mcp",
                headers=_BASE_HEADERS,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "legacy", "version": "1"},
                    },
                },
            )
    text = response.text
    for line in text.splitlines():
        if line.startswith("data: "):
            text = line[len("data: ") :]
    handshake = json.loads(text)["result"]["serverInfo"]

    assert handshake["version"] == pkg_version("swiss-procurement-mcp")


# --------------------------------------------------------------------------
# SEP-2549 auf dem echten Draht
# --------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["tools/list", "server/discover"])
async def test_die_cache_hinweise_stehen_auf_dem_draht(method: str) -> None:
    """`tests/test_cache_hints.py` misst ueber einen In-Process-`Client`.

    Hier steht dieselbe Zusicherung am HTTP-Rand: ein Hinweis, der die
    Serialisierung nicht ueberlebt, erreicht keinen Client.
    """
    _, body = await _post(method)

    assert body["result"]["ttlMs"] == LIST_CACHE_TTL_MS
    assert body["result"]["cacheScope"] == "public"


async def test_jedes_ergebnis_traegt_seinen_resulttype() -> None:
    """Spec 2026-07-28 macht `Result.resultType` zur Pflicht — ein Client darf
    ein Teilergebnis nicht fuer ein vollstaendiges halten."""
    for method in ("server/discover", "tools/list"):
        _, body = await _post(method)
        assert body["result"]["resultType"] == "complete", method


# --------------------------------------------------------------------------
# Ein Werkzeugaufruf, Ende zu Ende
# --------------------------------------------------------------------------


@respx.mock
async def test_ein_werkzeugaufruf_laeuft_ueber_den_envelope_durch() -> None:
    """Werkzeuge listen ist das eine; eines aufrufen das andere.

    Gefahren gegen eine aufgezeichnete Antwort, damit der Fall die Form der
    Quelle belegt und nicht die Annahme des Autors — dieselbe Regel wie in
    `tests/test_recorded_fixtures.py`.
    """
    respx.get(url__startswith=f"{SIMAP_BASE}/codes/v1/cpv/search").mock(
        return_value=httpx.Response(200, json=fixture_json("codes_cpv.json"))
    )

    status, body = await _post(
        "tools/call",
        params={"name": "search_cpv_codes", "arguments": {"args": {"query": "bau", "limit": 3}}},
    )

    assert status == 200, body
    assert body["result"].get("isError") is not True, body["result"]
    nutzlast = body["result"]["structuredContent"]
    assert nutzlast["codes"], "der Aufruf lief durch, lieferte aber nichts"
    assert nutzlast["provenance"] == "live_api"


async def test_ein_unbekanntes_werkzeug_ist_ein_werkzeugfehler_kein_protokollfehler() -> None:
    """Die Grenze, die ein Client braucht: der Transport hat funktioniert.

    Ein unbekannter Name kommt als `isError` im Ergebnis zurueck, nicht als
    JSON-RPC-Fehler — ein Client, der auf Protokollfehler neu verbindet, wuerde
    sonst wegen eines Tippfehlers die Verbindung neu aufbauen.
    """
    status, body = await _post(
        "tools/call", params={"name": "gibt_es_nicht", "arguments": {"args": {}}}
    )

    assert status == 200
    assert "error" not in body
    assert body["result"]["isError"] is True


# --------------------------------------------------------------------------
# stdio — der Transport, mit dem dieser Server ausgeliefert wird
# --------------------------------------------------------------------------


def _stdio_roundtrip(*requests: dict[str, Any]) -> list[dict[str, Any]]:
    """Die Anfragen durch einen echten `python -m swiss_procurement_mcp` schicken.

    Ein Unterprozess und keine In-Process-Abkuerzung: geprueft werden soll der
    Weg, den Claude Desktop nimmt, samt Einsprungpunkt und Stream-Aufbau. Eine
    Abkuerzung wuerde genau die Schicht ueberspringen, in der ein Fehler sitzen
    koennte.

    stdin bleibt offen, bis so viele Antworten gelesen sind wie Anfragen
    gestellt wurden. Der erste Anlauf schrieb alles auf einmal und schloss
    stdin sofort — zurueck kam nur die erste Antwort, weil das EOF die
    laufende Arbeit abraeumt. Das sah aus wie ein Server, der die zweite
    Anfrage nicht beantwortet, und war ein Test, der ihm nicht zuhoerte.
    """
    proc = subprocess.Popen(
        [sys.executable, "-m", "swiss_procurement_mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env={**os.environ, "MCP_TRANSPORT": "stdio"},
    )
    assert proc.stdin is not None and proc.stdout is not None
    antworten: list[dict[str, Any]] = []
    try:
        for request in requests:
            proc.stdin.write(json.dumps(request) + "\n")
            proc.stdin.flush()
        for _ in requests:
            line = proc.stdout.readline()
            if not line:  # Prozess ist gegangen, bevor er geantwortet hat
                break
            antworten.append(json.loads(line))
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:  # pragma: no cover - nur bei Haenger
            proc.kill()
            proc.wait(timeout=10)
    return antworten


def _stdio_request(rid: int, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"_meta": _envelope()}
    if params:
        body.update(params)
    return {"jsonrpc": "2.0", "id": rid, "method": method, "params": body}


def test_stdio_bedient_die_moderne_aera() -> None:
    """Der Transport, den die READMEs als primaeren nennen — und der in keiner
    Zusicherung dieses Repos vorkam.

    Alles andere hier faehrt ueber HTTP. Waere die moderne Aera nur dort
    erreichbar, bliebe der ausgelieferte Standardpfad ungeprueft, und der Pin
    beschriebe eine Revision, die der Server im Normalbetrieb nicht spricht.
    """
    antworten = _stdio_roundtrip(
        _stdio_request(1, "server/discover"),
        _stdio_request(2, "tools/list"),
    )

    nach_id = {a["id"]: a for a in antworten}
    assert set(nach_id) == {1, 2}, antworten

    discover = nach_id[1]["result"]
    assert discover["supportedVersions"] == list(MODERN_PROTOCOL_VERSIONS)
    assert discover["_meta"][SERVER_INFO_META_KEY]["version"] == pkg_version(
        "swiss-procurement-mcp"
    )
    assert discover["instructions"] == INSTRUCTIONS
    assert nach_id[2]["result"]["ttlMs"] == LIST_CACHE_TTL_MS


def test_stdio_lehnt_den_handshake_mit_der_aera_ab() -> None:
    """Die Gegenseite zu `test_ueber_http_ist_initialize_gar_keine_methode`.

    stdio traegt eine Verbindung, und die entscheidet ihre Aera mit der ersten
    Anfrage. Ein spaeteres `initialize` ist deshalb nicht «unbekannt», sondern
    aus der falschen Aera — und die Absage sagt das mit einem anderen Code als
    ueber HTTP. Wer nur den einen Transport prueft, schreibt die halbe Wahrheit
    auf.
    """
    antworten = _stdio_roundtrip(
        _stdio_request(1, "server/discover"),
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "modern-era-test", "version": "1"},
            },
        },
    )

    absage = next(a for a in antworten if a["id"] == 2)
    assert absage["error"]["code"] == UNSUPPORTED_PROTOCOL_VERSION
    assert absage["error"]["data"]["supported"] == list(MODERN_PROTOCOL_VERSIONS)
