"""SDK-004: CORS must accept the headers MCP routes by, and expose the session one.

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


@pytest.mark.parametrize("header", _cors.ROUTING_HEADERS)
def test_preflight_allows_each_routing_header(monkeypatch: pytest.MonkeyPatch, header: str) -> None:
    """Spec 2026-07-28 routes a streamable-http request by header.

    One header per request on purpose: Starlette refuses a preflight naming a
    header it does not allow with 400 and no `Access-Control-Allow-Origin`, so
    the list under test has to ride on the request rather than be read off the
    response — and announcing all three at once would not say which of them is
    missing.
    """
    resp = _preflight(_app(monkeypatch, ORIGIN), header=header)
    assert resp.status_code == 200, f"preflight announcing {header} was refused"
    assert header.lower() in resp.headers["access-control-allow-headers"].lower()


def test_preflight_allows_the_routing_headers_together(monkeypatch: pytest.MonkeyPatch) -> None:
    """What a browser actually sends: all of them, on the same request."""
    announced = ", ".join(h.lower() for h in _cors.ROUTING_HEADERS)
    resp = _preflight(_app(monkeypatch, ORIGIN), header=announced)
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == ORIGIN


def test_a_header_nobody_allow_listed_is_still_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The negative control. Without it the two tests above would pass just as
    well against a CORS layer that waves every header through — a different bug,
    not a fix."""
    resp = _preflight(_app(monkeypatch, ORIGIN), header="x-not-allowed")
    assert resp.status_code == 400


def test_cors_names_every_routing_header_the_sdk_reads() -> None:
    """Held against the SDK's own constants rather than a copy of the spec text.
    `mcp.shared.inbound` is what the server reads a request with, so a rename
    there becomes a failing test here instead of a browser client that stops
    connecting for no visible reason."""
    from mcp.shared.inbound import (
        MCP_METHOD_HEADER,
        MCP_NAME_HEADER,
        MCP_PROTOCOL_VERSION_HEADER,
    )

    allowed = {h.lower() for h in _cors.ALLOW_HEADERS}
    required = {MCP_METHOD_HEADER, MCP_NAME_HEADER, MCP_PROTOCOL_VERSION_HEADER}
    assert required <= allowed, f"not allow-listed: {sorted(required - allowed)}"


async def test_no_tool_schema_declares_an_mcp_param_header() -> None:
    """`Mcp-Param-*` carries a tool argument as an HTTP header, opted into by an
    `x-mcp-header` annotation on the input schema. CORS has no prefix wildcard,
    so the first tool to use one must name that exact header in `ALLOW_HEADERS`.
    None does yet; this is the reminder for the day one does."""
    from swiss_procurement_mcp.server import mcp

    offenders = [t.name for t in await mcp.list_tools() if "x-mcp-header" in str(t.input_schema)]
    assert not offenders, f"{offenders} declare an Mcp-Param-* header — add it to ALLOW_HEADERS"


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


def _record_stateless(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Capture what `build_http_app` actually asks the SDK for.

    `mcp` 2.0 turned `stateless_http` from a mutable setting into an argument of
    `streamable_http_app()`. There is no global left to read afterwards, so the
    assertion moves to the call itself — which is the better place anyway: it
    checks the value that reaches the SDK rather than a flag someone set.
    """
    from swiss_procurement_mcp.server import mcp

    seen: dict = {}
    real = mcp.streamable_http_app

    def _spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(mcp, "streamable_http_app", _spy)
    return seen


def test_stateless_reaches_the_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reading the env var and never applying it is the failure this catches."""
    monkeypatch.setenv("MCP_STATELESS", "1")
    seen = _record_stateless(monkeypatch)
    main = importlib.import_module("swiss_procurement_mcp.__main__")
    main.build_http_app("streamable-http")
    assert seen.get("stateless_http") is True


def test_stateless_is_off_unless_asked_for(monkeypatch: pytest.MonkeyPatch) -> None:
    """The negative control: without the env var the flag must not ride along."""
    monkeypatch.delenv("MCP_STATELESS", raising=False)
    seen = _record_stateless(monkeypatch)
    main = importlib.import_module("swiss_procurement_mcp.__main__")
    main.build_http_app("streamable-http")
    assert seen.get("stateless_http") is False


def test_stateless_does_not_silently_apply_to_sse(monkeypatch: pytest.MonkeyPatch) -> None:
    """The legacy SSE transport has no stateless mode.

    Building the SSE app as if it were session-free would tell an operator they
    are running without sessions when they are not — worse than refusing,
    because it reads as enforced. `sse_app()` takes no such argument, so the
    check is that the streamable-http builder is never reached at all.
    """
    from swiss_procurement_mcp.server import mcp

    monkeypatch.setenv("MCP_STATELESS", "1")
    called = False

    def _explode(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("SSE must not be built through streamable_http_app")

    monkeypatch.setattr(mcp, "streamable_http_app", _explode)
    main = importlib.import_module("swiss_procurement_mcp.__main__")
    main.build_http_app("sse")
    assert called is False
