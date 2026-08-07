"""Retry policy: Retry-After, jitter, and the cap.

Adopted together with the hardened retry from the mcp-data-source-probe
reference template. These assert the behaviour, not the constants.
"""

from __future__ import annotations

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

    monkeypatch.setattr(client.asyncio, "sleep", _instant)

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
