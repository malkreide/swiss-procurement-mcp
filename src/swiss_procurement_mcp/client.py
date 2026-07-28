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
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

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

MAX_ATTEMPTS = 4
CACHE_TTL_SECONDS = 60 * 30  # publications change intraday; keep it short


class UpstreamError(RuntimeError):
    """Upstream unreachable, or a non-retryable client error (4xx)."""


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

        for attempt in range(MAX_ATTEMPTS):
            if attempt > 0:
                await asyncio.sleep(2**attempt)  # 2s, 4s, 8s
            try:
                response = await self._http.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                if 400 <= status < 500 and status != 429:
                    body = exc.response.text[:300]
                    raise UpstreamError(f"HTTP {status} from {path}: {body}") from exc
            except (httpx.RequestError, ValueError) as exc:
                last_error = exc

        raise UpstreamError(f"Upstream unreachable after {MAX_ATTEMPTS} attempts: {last_error}")

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

    async def past_publications(self, publication_id: str, language: str) -> tuple[Any, str, str]:
        return await self._cached(
            f"past:{publication_id}:{language}",
            f"/publications/v1/publication/{publication_id}/past-publications",
            {"lang": language},
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
