"""SDK-004: CORS must expose and accept `Mcp-Session-Id`.

These tests drive the assembled Starlette app through real requests rather than
inspecting the middleware stack. Asserting that a `CORSMiddleware` object is
present would pass even if `expose_headers` were empty — and an empty
`expose_headers` is exactly the defect: the browser completes initialize, cannot
read the session header, and loses the session on the next call.
"""

from __future__ import annotations

import importlib

import pytest
from starlette.testclient import TestClient

from swiss_procurement_mcp import _cors

ORIGIN = "https://client.example"


def _app(monkeypatch: pytest.MonkeyPatch, origins: str | None) -> TestClient:
    if origins is None:
        monkeypatch.delenv("MCP_CORS_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("MCP_CORS_ORIGINS", origins)
    main = importlib.import_module("swiss_procurement_mcp.__main__")
    return TestClient(main.build_http_app("streamable-http"))


def _preflight(client: TestClient, origin: str = ORIGIN, header: str = "mcp-session-id"):
    return client.options(
        "/mcp",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": header,
        },
    )


def test_preflight_allows_the_session_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without this the browser cannot *send* Mcp-Session-Id on follow-up calls."""
    resp = _preflight(_app(monkeypatch, ORIGIN))
    assert resp.status_code == 200
    allowed = resp.headers["access-control-allow-headers"].lower()
    assert "mcp-session-id" in allowed


def test_actual_response_exposes_the_session_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without this the browser cannot *read* Mcp-Session-Id off the response.

    Asserted on a real request, not on the preflight: `Access-Control-Expose-
    Headers` is only ever sent on actual responses. The status does not matter —
    what matters is that the CORS layer runs and names the header.
    """
    # As a context manager, so the streamable-http session manager's lifespan
    # is running — without it the app raises before any response is produced.
    with _app(monkeypatch, ORIGIN) as client:
        resp = client.get("/mcp", headers={"Origin": ORIGIN}, follow_redirects=True)
    exposed = resp.headers["access-control-expose-headers"].lower()
    assert "mcp-session-id" in exposed
    assert resp.headers["access-control-allow-origin"] == ORIGIN


def test_preflight_allows_delete_for_session_termination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resp = _preflight(_app(monkeypatch, ORIGIN))
    assert "DELETE" in resp.headers["access-control-allow-methods"]


def test_configured_origin_is_echoed_back(monkeypatch: pytest.MonkeyPatch) -> None:
    resp = _preflight(_app(monkeypatch, ORIGIN))
    assert resp.headers["access-control-allow-origin"] == ORIGIN
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_unconfigured_origin_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The allow-list is a list, not decoration."""
    resp = _preflight(_app(monkeypatch, ORIGIN), origin="https://evil.example")
    assert "access-control-allow-origin" not in resp.headers


def test_default_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """MCP_CORS_ORIGINS unset must not mean 'any origin'."""
    resp = _preflight(_app(monkeypatch, None))
    assert "access-control-allow-origin" not in resp.headers


def test_wildcard_disables_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Browsers reject `*` together with credentials, so honouring both would
    ship a config that fails at request time instead of at startup."""
    resp = _preflight(_app(monkeypatch, "*"))
    assert resp.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in resp.headers


def test_origins_are_parsed_as_a_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_CORS_ORIGINS", " https://a.example , https://b.example ,, ")
    assert _cors.configured_origins() == ["https://a.example", "https://b.example"]


def test_second_origin_in_the_list_also_works(monkeypatch: pytest.MonkeyPatch) -> None:
    """A list that only ever honours its first entry would pass every test above."""
    client = _app(monkeypatch, f"https://a.example,{ORIGIN}")
    resp = _preflight(client)
    assert resp.headers["access-control-allow-origin"] == ORIGIN


def test_sse_app_gets_the_same_treatment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both HTTP transports are advertised; a control on only one of them is
    worse than none, because it looks enforced."""
    monkeypatch.setenv("MCP_CORS_ORIGINS", ORIGIN)
    main = importlib.import_module("swiss_procurement_mcp.__main__")
    client = TestClient(main.build_http_app("sse"))
    resp = client.options(
        "/sse",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "mcp-session-id",
        },
    )
    assert resp.status_code == 200
    assert "mcp-session-id" in resp.headers["access-control-allow-headers"].lower()
    assert resp.headers["access-control-allow-origin"] == ORIGIN


# ---------------------------------------------------------------------------
# SEC-009 / SCALE-002: opt-in stateless mode
# ---------------------------------------------------------------------------


def test_stateless_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sessions cost nothing on a single instance, and stateless mode gives up
    SSE resumption and server-initiated notifications. Opt-in, not default."""
    monkeypatch.delenv("MCP_STATELESS", raising=False)
    main = importlib.import_module("swiss_procurement_mcp.__main__")
    assert main._stateless_requested() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes"])
def test_stateless_env_is_accepted(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("MCP_STATELESS", value)
    main = importlib.import_module("swiss_procurement_mcp.__main__")
    assert main._stateless_requested() is True


@pytest.mark.parametrize("value", ["0", "false", "no", ""])
def test_stateless_rejects_non_affirmative_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """`MCP_STATELESS=0` must mean off. A truthiness check on the raw string
    would turn "0" and "false" into on, which is the wrong direction to fail."""
    monkeypatch.setenv("MCP_STATELESS", value)
    main = importlib.import_module("swiss_procurement_mcp.__main__")
    assert main._stateless_requested() is False


def test_stateless_reaches_the_server_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reading the env var and never applying it is the failure this catches."""
    from swiss_procurement_mcp.server import mcp

    monkeypatch.setenv("MCP_STATELESS", "1")
    monkeypatch.setattr(mcp.settings, "stateless_http", False)
    main = importlib.import_module("swiss_procurement_mcp.__main__")
    main.build_http_app("streamable-http")
    assert mcp.settings.stateless_http is True


def test_stateless_does_not_silently_apply_to_sse(monkeypatch: pytest.MonkeyPatch) -> None:
    """The legacy SSE transport has no stateless mode.

    Leaving `stateless_http` set here would tell an operator they are running
    session-free when they are not — worse than refusing, because it reads as
    enforced.
    """
    from swiss_procurement_mcp.server import mcp

    monkeypatch.setenv("MCP_STATELESS", "1")
    monkeypatch.setattr(mcp.settings, "stateless_http", False)
    main = importlib.import_module("swiss_procurement_mcp.__main__")
    main.build_http_app("sse")
    assert mcp.settings.stateless_http is False
