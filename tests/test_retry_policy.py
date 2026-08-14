"""Retry policy: Retry-After, jitter, and the cap.

Adopted together with the hardened retry from the mcp-data-source-probe
reference template. These assert the behaviour, not the constants.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx

from swiss_procurement_mcp import client

# --- Retry policy: Retry-After, jitter, and the cap --------------------------
# Adopted together with the hardened retry from the mcp-data-source-probe
# reference template. These assert the behaviour, not the constants: a
# deterministic ladder and an unread `Retry-After` are what a sweep across
# eleven servers found on 2026-08-03, and every one of them looked fine.


def _retry_after_error(value: str) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.invalid/")
    return httpx.HTTPStatusError(
        "",
        request=request,
        response=httpx.Response(429, headers={"Retry-After": value}, request=request),
    )


def test_retry_after_reads_both_rfc9110_forms() -> None:
    def resp(status: int, headers: dict[str, str]) -> httpx.Response:
        request = httpx.Request("GET", "https://example.invalid/")
        return httpx.Response(status, headers=headers, request=request)

    assert client.parse_retry_after(resp(429, {"Retry-After": "120"})) == 120.0

    later = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=90))
    seconds = client.parse_retry_after(resp(503, {"Retry-After": later}))
    assert seconds is not None and 80 < seconds <= 90

    # A date in the past means "now", never a negative wait.
    past = "Wed, 21 Oct 2020 07:28:00 GMT"
    assert client.parse_retry_after(resp(503, {"Retry-After": past})) == 0.0

    # Unparseable falls back to the curve. It must not crash on the error path,
    # which is the one path already going badly.
    assert client.parse_retry_after(resp(429, {"Retry-After": "bald"})) is None
    assert client.parse_retry_after(resp(429, {})) is None

    # 500 does not carry a meaningful Retry-After.
    assert client.parse_retry_after(resp(500, {"Retry-After": "120"})) is None
    assert client.parse_retry_after(None) is None


def test_backoff_is_jittered() -> None:
    delays = {client.compute_delay(3, None) for _ in range(300)}
    # attempt 3 -> 2 * 2**2 = 8s, spread into [0.5x, 1.5x]
    assert len(delays) > 1, "a deterministic ladder synchronises every client"
    assert min(delays) >= 4.0
    assert max(delays) <= 12.0


def test_cap_binds_after_the_jitter() -> None:
    # Capping first and then multiplying by up to 1.5 would land at 30s, and
    # the constant would claim a ceiling it does not hold.
    deep = {client.compute_delay(9, None) for _ in range(200)}
    assert max(deep) <= client.RETRY_MAX_DELAY

    hinted = _retry_after_error("600")
    assert {client.compute_delay(1, hinted) for _ in range(100)} == {client.RETRY_MAX_DELAY}


def test_retry_after_jitter_is_one_sided() -> None:
    """The source said when. Later is polite; earlier ignores the value read."""
    delays = {client.compute_delay(1, _retry_after_error("4")) for _ in range(300)}
    assert min(delays) >= 4.0, "never earlier than the source asked for"
    assert max(delays) <= 5.0  # 4 * 1.25


# --- The wrapper has to name the type ----------------------------------------


async def test_empty_error_message_still_names_type_and_host(monkeypatch):
    """The case that made the old message stop at the colon.

    ``httpx.ConnectTimeout``, ``ReadTimeout`` and ``ConnectError`` all carry an
    EMPTY ``str()`` in the wild — and they are the only errors a real outage
    produces. The message used to interpolate ``{last_error}`` alone and read
    "Upstream unreachable after 4 attempts: " naming neither the failure mode
    nor the host.
    """

    async def _instant(_seconds):
        return None

    monkeypatch.setattr(client, "_sleep", _instant)

    async with client.SimapClient() as c:
        monkeypatch.setattr(c._http, "get", lambda *a, **k: _raise(httpx.ConnectTimeout("")))
        try:
            await c._fetch_with_retry("/api/anything")
        except client.UpstreamError as exc:
            message = str(exc)
        else:  # pragma: no cover - the call must fail
            raise AssertionError("expected UpstreamError")

    assert "ConnectTimeout" in message, "the failure mode has to be named"
    assert "www.simap.ch" in message, "the host has to be named"
    assert "no further detail" in message, "an empty str() is said, not swallowed"


async def _raise(exc: Exception):
    raise exc


# --- Die Naht, und warum sie nicht `asyncio.sleep` ist -----------------------


def test_der_retry_geht_ueber_den_alias():
    """Sonst patchen die Tests eine Naht, die der Code gar nicht benutzt.

    Umgeht das Modul den Alias, bleibt der Patch wirkungslos und die Suite
    wartet die echte Backoff-Leiter ab. Kein Test faellt dabei — sie wird nur
    um ein Vielfaches langsamer, und eine laengere Laufzeit ist kein Signal,
    das jemand liest. Diese Zusicherung macht daraus einen Fehlschlag.
    """
    quelle = inspect.getsource(client)
    assert "await _sleep(" in quelle, "der Retry ruft den Modul-Alias nicht mehr auf"
    assert "await asyncio.sleep(" not in quelle, "der Retry umgeht den Alias"


def test_kein_test_patcht_die_wartezeit_am_fremden_modul():
    """Die andere Haelfte derselben Naht — und die, die gefehlt hat.

    `test_der_retry_geht_ueber_den_alias` bewacht das Modul: es soll `_sleep`
    aufrufen. Damit war aber nur eine Richtung abgesichert. Drei Testdateien
    nullten die Wartezeit weiter am geteilten `asyncio`-Modul, und seit der
    Alias da ist, trifft dieser Patch nichts mehr: `_sleep` wurde beim Import
    an die echte Funktion gebunden.

    Gefallen ist dabei kein einziger Test. Die Suite lief nur 155 statt 4
    Sekunden — sie wartete die Leiter 2/4/8 an jedem degradierten Pfad wirklich
    ab. Eine laengere Laufzeit ist kein Signal, das jemand liest; diese
    Zusicherung macht daraus einen Fehlschlag.

    Diese Datei nennt das verbotene Muster, um es zu verbieten, und nimmt sich
    deshalb selbst aus.
    """
    from pathlib import Path

    # Zusammengesetzt, damit die Datei das Muster nicht ausgeschrieben traegt
    # und die eigene Ausnahme kleiner bleibt als die Regel.
    verboten = ("client." + "asyncio.sleep", "asyncio, " + '"sleep"')
    hier = Path(__file__)
    schuldig = {
        pfad.name: muster
        for pfad in sorted(hier.parent.glob("test_*.py"))
        if pfad != hier
        for muster in verboten
        if muster in pfad.read_text(encoding="utf-8")
    }
    assert not schuldig, (
        f"patcht die Wartezeit am geteilten Modul statt am Alias: {schuldig}. "
        'Richtig ist `monkeypatch.setattr(_client, "_sleep", _instant)` — der '
        "Patch am fremden Modul trifft den Retry nicht mehr und entschaerft "
        "stattdessen `asyncio.sleep` fuer jeden Importeur im Prozess."
    )
