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

from .constants import DEFAULT_LANGUAGE, SIMAP_BASE, SUPPORTED_LANGUAGES, USER_AGENT

MAX_ATTEMPTS = 4
CACHE_TTL_SECONDS = 60 * 30  # publications change intraday; keep it short


class UpstreamError(RuntimeError):
    """Upstream unreachable, or a non-retryable client error (4xx)."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
        return value.get(language) or value.get("de") or next(
            (v for v in value.values() if v), None
        )
    return str(value)


class SimapClient:
    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self._http = http
        self._owns_http = http is None
        self._cache: dict[str, tuple[float, Any]] = {}
        self._last_success: dict[str, str] = {}

    async def __aenter__(self) -> SimapClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                follow_redirects=True,
            )
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    async def _fetch_with_retry(self, path: str, params: dict[str, Any] | None = None) -> Any:
        assert self._http is not None, "SimapClient must be used as an async context manager"
        url = f"{SIMAP_BASE}{path}"
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
        return await self._cached(
            key, "/publications/v2/project/project-search", params
        )

    async def publication_details(
        self, project_id: str, publication_id: str, language: str
    ) -> tuple[Any, str, str]:
        return await self._cached(
            f"detail:{project_id}:{publication_id}:{language}",
            f"/publications/v1/project/{project_id}/publication-details/{publication_id}",
            {"lang": language},
        )

    async def past_publications(
        self, publication_id: str, language: str
    ) -> tuple[Any, str, str]:
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
        return await self._cached(
            f"po:{language}", "/procoffices/v1/po/public", {"lang": language}
        )

    async def probe(self, name: str, path: str) -> dict[str, Any]:
        assert self._http is not None
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
