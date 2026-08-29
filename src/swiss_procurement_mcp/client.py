"""HTTP access layer for the simap.ch read API.

Probe-derived design notes (2026-07-26):

* The host requires a session cookie. The first call to any /api path sets it
  via Set-Cookie; httpx keeps it in the client's cookie jar automatically, so a
  single persistent AsyncClient handles this transparently — no manual seed
  request is needed as long as cookies are enabled (they are by default).
* `lang` is mandatory on project-search; omitting it is a 400, not an empty
  result. The client injects a default when the caller forgets.
* Unknown enum values return HTTP 400 with errorCode E0025. These are client
  errors and are not retried.
* `past-publications` needs `lotId` for a publication that has lots (measured
  2026-08-29 over 80 publications: 4 with lots answered 400/E0003 without the
  parameter and 200 with it, 76 without lots answered 200). The spec marks the
  parameter optional, which it is only for the latter group.
"""

from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from ._net import PinnedResolverTransport
from .constants import (
    ALLOWED_HOSTS,
    DEFAULT_LANGUAGE,
    INSTITUTIONS_PATH,
    SIMAP_BASE,
    SUPPORTED_LANGUAGES,
    USER_AGENT,
)

# Eigener Alias, damit Tests die Wartezeit nullen koennen, ohne `asyncio.sleep`
# prozessweit zu entschaerfen. `monkeypatch.setattr(<modul>.asyncio, "sleep", ...)`
# sieht lokal aus, ersetzt `sleep` aber auf dem geteilten Modulobjekt — fuer
# httpx, respx, pytest-asyncio und jeden anderen Importeur im Prozess.
_sleep = asyncio.sleep

MAX_ATTEMPTS = 4
CACHE_TTL_SECONDS = 60 * 30  # publications change intraday; keep it short


class UpstreamError(RuntimeError):
    """Upstream unreachable, or a non-retryable client error (4xx).

    ``status`` carries the HTTP status when there was a response, so a caller
    can tell a refusal it can act on apart from an outage it cannot. It is the
    status alone — never the response body, which OBS-002 keeps away from the
    model.
    """

    def __init__(self, *args: Any, status: int | None = None) -> None:
        super().__init__(*args)
        self.status = status


# --- Retry policy ------------------------------------------------------------
# Adopted from the mcp-data-source-probe reference template (repaired
# 2026-08-07). Three questions: *what* is retried, *how fast*, and *how long*.
# The first is settled in the retry loop (4xx except 429 fails fast); these
# settle the other two.

RETRY_BASE_DELAY = 2.0  # ladder before jitter: 2, 4, 8

# Ceiling on the WHOLE call — every attempt and every wait together. An attempt
# count is not a bound: four attempts against an upstream that takes 30s to time
# out is two minutes inside one tool call, and the number never says so. The
# anchor is measured, not guessed: the Python MCP SDK ships
# MCP_DEFAULT_TIMEOUT = 30.0, so 25s leaves headroom for framing and parsing.
RETRY_TOTAL_BUDGET = 25.0

# Ceiling for a single wait. Bounds the exponential ladder, and bounds a
# `Retry-After` the source may send but we are not obliged to sit through.
RETRY_MAX_DELAY = 20.0

# Jitter spread. Without it every client that hit the same outage retries in
# lockstep, and the load returns as a wave exactly when the source recovers —
# the retry storm extends the outage it was meant to bridge.
RETRY_JITTER_SPREAD = 0.5  # exponential delays land in [0.5x, 1.5x]

# On a `Retry-After`, deliberately one-sided: the source said when to come back,
# so coming back later is fine and coming back earlier is not.
RETRY_AFTER_JITTER = 0.25  # lands in [1.0x, 1.25x]

# Statuses that carry a meaningful `Retry-After` (RFC 9110 section 10.2.3).
RETRY_AFTER_STATUSES = frozenset({429, 503})


class UpstreamUnavailableError(UpstreamError):
    """No request was attempted — the budget was gone before the first try.

    A subclass of ``UpstreamError`` so existing handlers keep working, and a
    distinct type so a caller can tell "we never asked" apart from "we asked
    and it failed". Raised only when there is no upstream exception at all.
    """


def parse_retry_after(resp: httpx.Response | None) -> float | None:
    """Seconds to wait per the response's ``Retry-After``, or ``None``.

    RFC 9110 section 10.2.3 allows two forms — delta-seconds (``120``) and an
    HTTP-date (``Wed, 21 Oct 2026 07:28:00 GMT``). Both appear in the wild, so
    both are read. Anything unparseable yields ``None`` and the caller falls
    back to its own curve: a malformed header must not become a crash on the
    error path, which is the one path already going badly.
    """
    if resp is None or resp.status_code not in RETRY_AFTER_STATUSES:
        return None
    raw = (resp.headers.get("retry-after") or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return float(raw)
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:  # RFC 9110 dates are GMT; a naive one means UTC
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def compute_delay(attempt: int, last_error: Exception | None) -> float:
    """Seconds to wait before ``attempt`` (1-based for the first retry).

    The source's own answer beats our guess: a ``Retry-After`` on a 429 or 503
    wins over the exponential curve. Everything is spread, then capped.

    The cap wraps the jitter and not the other way round. ``min(cap, base) *
    jitter`` and ``min(cap, base * jitter)`` both contain a cap and a jitter;
    only the second is bounded — a value capped at 20s and then multiplied by
    up to 1.5 lands at 30s, and the constant would claim a ceiling it does not
    hold.
    """
    hinted = parse_retry_after(getattr(last_error, "response", None))
    if hinted is not None:
        return min(
            hinted * (1.0 + random.random() * RETRY_AFTER_JITTER),
            RETRY_MAX_DELAY,
        )
    return min(
        RETRY_BASE_DELAY
        * 2 ** (attempt - 1)
        * (1.0 - RETRY_JITTER_SPREAD + random.random() * 2 * RETRY_JITTER_SPREAD),
        RETRY_MAX_DELAY,
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _assert_host_allowed(url: str) -> None:
    """SEC-021 / SEC-004: refuse egress outside the allow-list, and refuse plaintext.

    The base URL is hardcoded, so this can only trip on a future refactor that
    lets a foreign host or a plaintext scheme reach here — exactly the
    regression this guards against.

    The scheme is checked as well as the host (SEC-004). Checking only the host
    left a gap that reads as covered: `http://www.simap.ch/...` passes an
    allow-list keyed on hostname while sending the request in the clear.
    """
    parsed = httpx.URL(url)
    if parsed.scheme != "https":
        raise UpstreamError(
            f"Refusing non-HTTPS request to {parsed.host!r} (scheme {parsed.scheme!r})."
        )
    if parsed.host not in ALLOWED_HOSTS:
        raise UpstreamError(f"Refusing request to non-allow-listed host {parsed.host!r}.")


def normalise_language(language: str | None) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    code = language.lower()
    if code not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language {language!r}. Supported: {', '.join(SUPPORTED_LANGUAGES)}."
        )
    return code


def pick_lang(value: Any, language: str) -> str | None:
    """simap returns localised strings as {"de":..,"fr":..,"en":..,"it":..}."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return (
            value.get(language) or value.get("de") or next((v for v in value.values() if v), None)
        )
    return str(value)


def _make_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
        # SEC-004 / SEC-005: resolve once, check the address against the
        # blocklist, then connect to the address that was checked. Installed as
        # a transport so redirects are covered too — httpx builds a fresh
        # request per hop and each one passes through here.
        transport=PinnedResolverTransport(),
    )


class SimapClient:
    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self._http = http
        self._owns_http = http is None
        self._cache: dict[str, tuple[float, Any]] = {}
        self._last_success: dict[str, str] = {}

    async def __aenter__(self) -> SimapClient:
        if self._http is None:
            self._http = _make_http_client()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    async def _fetch_with_retry(self, path: str, params: dict[str, Any] | None = None) -> Any:
        assert self._http is not None, "SimapClient must be used as an async context manager"
        url = f"{SIMAP_BASE}{path}"
        _assert_host_allowed(url)
        last_error: Exception | None = None
        deadline = time.monotonic() + RETRY_TOTAL_BUDGET
        attempts = 0

        for attempt in range(MAX_ATTEMPTS):
            if attempt > 0:
                delay = compute_delay(attempt, last_error)
                # A wait that outlasts the budget is a wait for nobody: the
                # caller has given up by the time it ends. Stop instead.
                if delay >= deadline - time.monotonic():
                    break
                await _sleep(delay)

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            attempts += 1
            try:
                # httpx bounds each operation and restarts its read timeout
                # with every chunk, so a slowly trickling response outlives a
                # per-operation limit without any single read expiring.
                # `asyncio.wait_for` is the wall-clock bound the budget
                # actually promises (`asyncio.timeout` needs 3.11; this repo
                # supports 3.10).
                response = await asyncio.wait_for(self._http.get(url, params=params), remaining)
                response.raise_for_status()
                return response.json()
            except asyncio.TimeoutError as exc:  # budget gone, not just this try
                last_error = exc
                break
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                if 400 <= status < 500 and status != 429:
                    body = exc.response.text[:300]
                    raise UpstreamError(
                        f"HTTP {status} from {path}: {body}", status=status
                    ) from exc
            except (httpx.RequestError, ValueError) as exc:
                last_error = exc

        host = urlsplit(url).hostname
        if last_error is None:
            raise UpstreamUnavailableError(
                f"No request to {path} was attempted: the "
                f"{RETRY_TOTAL_BUDGET:g}s budget was already spent (host={host})."
            )
        # Still an `UpstreamError` — callers branch on it, and the 4xx path
        # above raises the same type. What changed is what the message carries.
        # It interpolated `{last_error}` alone, and `httpx.ConnectTimeout`,
        # `ReadTimeout` and `ConnectError` all have an EMPTY `str()` — precisely
        # the set a real outage produces. The sentence stopped at the colon and
        # named neither the failure mode nor the host. Anyone who wraps has to
        # name the type.
        why = (
            f"all {MAX_ATTEMPTS} attempts used"
            if attempts >= MAX_ATTEMPTS
            else f"the {RETRY_TOTAL_BUDGET:g}s budget ran out after {attempts}"
        )
        detail = str(last_error) or "no further detail"
        raise UpstreamError(
            f"Upstream unreachable for {path} after {attempts} attempt(s) — {why}: "
            f"{type(last_error).__name__}: {detail} (host={host})."
        ) from last_error

    async def _cached(self, key: str, path: str, params: dict[str, Any]) -> tuple[Any, str, str]:
        now = time.monotonic()
        hit = self._cache.get(key)
        if hit is not None and now - hit[0] < CACHE_TTL_SECONDS:
            return hit[1], "cached", self._last_success.get(key, utc_now_iso())
        payload = await self._fetch_with_retry(path, params)
        stamp = utc_now_iso()
        self._cache[key] = (now, payload)
        self._last_success[key] = stamp
        return payload, "live_api", stamp

    # ------------------------------------------------------------- endpoints

    async def project_search(self, params: dict[str, Any]) -> tuple[Any, str, str]:
        params.setdefault("lang", DEFAULT_LANGUAGE)
        key = "search:" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return await self._cached(key, "/publications/v2/project/project-search", params)

    async def publication_details(
        self, project_id: str, publication_id: str, language: str
    ) -> tuple[Any, str, str]:
        return await self._cached(
            f"detail:{project_id}:{publication_id}:{language}",
            f"/publications/v1/project/{project_id}/publication-details/{publication_id}",
            {"lang": language},
        )

    async def past_publications(
        self, publication_id: str, language: str, lot_id: str | None = None
    ) -> tuple[Any, str, str]:
        """Earlier publications of one procurement.

        `lotId` is optional in the spec and mandatory in practice for a
        publication that has lots: without it the endpoint answers HTTP 400
        (`errorCode: E0003`), with it the same publication answers 200. It is
        sent only when the caller supplies one — passing a lot id to a
        publication without lots is a 404, so an unconditional parameter would
        break the 95% case to serve the other 5%.
        """
        params: dict[str, Any] = {"lang": language}
        key = f"past:{publication_id}:{language}"
        if lot_id:
            params["lotId"] = lot_id
            key = f"{key}:{lot_id}"
        return await self._cached(
            key,
            f"/publications/v1/publication/{publication_id}/past-publications",
            params,
        )

    async def code_search(
        self, system: str, query: str, language: str, limit: int
    ) -> tuple[Any, str, str]:
        return await self._cached(
            f"code:{system}:{query}:{language}:{limit}",
            f"/codes/v1/{system}/search",
            {"lang": language, "query": query, "limit": limit},
        )

    async def procurement_offices_public(self, language: str) -> tuple[Any, str, str]:
        return await self._cached(f"po:{language}", "/procoffices/v1/po/public", {"lang": language})

    async def institutions(self, language: str = DEFAULT_LANGUAGE) -> tuple[Any, str, str]:
        """The institution tree: 28 roots (26 cantons + Bund + Ausland).

        Public, no authentication. Used to verify `CANTON_INSTITUTION_IDS`
        against the live taxonomy rather than trusting the pinned ids forever.
        """
        return await self._cached(f"inst:{language}", INSTITUTIONS_PATH, {"lang": language})

    async def probe(self, name: str, path: str) -> dict[str, Any]:
        assert self._http is not None
        _assert_host_allowed(f"{SIMAP_BASE}{path}")
        started = time.perf_counter()
        try:
            response = await self._http.get(f"{SIMAP_BASE}{path}", timeout=10.0)
            return {
                "name": name,
                "base_url": f"{SIMAP_BASE}{path}",
                "reachable": response.status_code < 500,
                "http_status": response.status_code,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
        except httpx.RequestError:
            return {
                "name": name,
                "base_url": f"{SIMAP_BASE}{path}",
                "reachable": False,
                "http_status": None,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }


# SDK-001: one SimapClient — and with it one httpx.AsyncClient — is shared
# across every tool call, rather than constructed per call inside the tool body.
#
# Two things were wrong with per-call construction. The cheap one is that each
# call paid a fresh TCP handshake and TLS negotiation. The expensive one is that
# `_cache` and the session cookie live on the instance: a client that dies when
# the tool returns can never serve a cache hit and re-fetches the session cookie
# every time, so the cache was dead code that looked like a working cache.
#
# Created lazily on first use so that calling a tool function directly in tests
# works without standing up the server lifespan; closed by the lifespan in
# server.py on shutdown.
_shared: SimapClient | None = None


def get_client() -> SimapClient:
    """Return the process-wide SimapClient, (re)creating it if absent or closed."""
    global _shared
    if _shared is None or _shared._http is None or _shared._http.is_closed:
        _shared = SimapClient(http=_make_http_client())
    return _shared


async def close_client() -> None:
    """Close the shared client. Called by the server lifespan on shutdown."""
    global _shared
    if _shared is not None and _shared._http is not None and not _shared._http.is_closed:
        await _shared._http.aclose()
    _shared = None


def reset_client() -> None:
    """Drop the shared client without awaiting a close.

    Tests need a clean cache and a clean cookie jar between cases; a shared
    instance that survives a test would let one case serve another's assertion
    out of `_cache`. Synchronous on purpose so it can run from a plain fixture.
    """
    global _shared
    _shared = None
