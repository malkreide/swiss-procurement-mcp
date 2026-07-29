"""Entry point: stdio (Claude Desktop) or SSE / streamable-http (cloud)."""

from __future__ import annotations

import logging
import os

from starlette.applications import Starlette

from ._cors import apply_cors, configured_origins
from ._log import log_event
from .server import mcp

HTTP_TRANSPORTS = {"sse", "streamable-http", "http"}


def _stateless_requested() -> bool:
    """SEC-009 / SCALE-002: opt into session-free HTTP.

    With `stateless_http`, the SDK builds a fresh transport per request and
    tracks no session. That removes both problems rather than solving them:
    there is no session id to bind to a user (SEC-009) and none to route
    consistently to an instance (SCALE-002).

    Opt-in rather than default, because it is not free — a stateless server
    cannot resume an interrupted SSE stream or push server-initiated
    notifications, both of which need a session to belong to. For a read-only
    server with no per-user state that is usually the right trade; for a
    single-instance local run it is unnecessary. The operator decides.
    """
    return os.environ.get("MCP_STATELESS", "").strip().lower() in {"1", "true", "yes"}


def _bind_host() -> str:
    """Loopback unless an operator opts out explicitly (SEC-016).

    Read here rather than round-tripped through `mcp.settings`: `MCPServer`
    dropped the `host` and `port` settings in 2.0, and they were only ever a
    detour — the values come from the environment and go to uvicorn.
    """
    return os.environ.get("MCP_HOST", os.environ.get("HOST", "127.0.0.1"))


def _bind_port() -> int:
    return int(os.environ.get("PORT", os.environ.get("MCP_PORT", "8000")))


def build_transport_security(host: str, port: int, origins=()):
    """Host/Origin allow-list for the HTTP/SSE transport (SEC-005, inbound half).

    Under mcp 2.x this is a per-app kwarg rather than a global setting. Left
    unset, the SDK auto-enables protection only for a loopback bind; a
    0.0.0.0 bind gets nothing, which is exactly how this server is shipped.

    Returns ``None`` when no allow-list can be derived: a non-loopback bind
    with no ``MCP_ALLOWED_HOSTS``. The server is then reached under a service
    or public DNS name this process does not know, and a guessed list would
    reject every real request with HTTP 421. The caller warns instead, and the
    SDK default (no protection on a non-local bind) applies unchanged.
    """
    from mcp.server.transport_security import TransportSecuritySettings

    allowed = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    loopback = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}
    if allowed:
        # Loopback stays reachable for container health checks and debugging.
        hosts = set(allowed) | loopback
    elif host in ("127.0.0.1", "localhost", "::1"):
        hosts = loopback | {f"{host}:{port}"}
    else:
        return None

    # Configured CORS origins must also pass the transport check, or the server
    # rejects exactly the browser clients CORS permits. "*" is matched
    # literally by the SDK (only a trailing ":*" port wildcard exists), so it
    # is not copied across.
    allowed_origins = {o for o in origins if o != "*"}
    allowed_origins |= {f"http://{h}" for h in hosts}
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted(hosts),
        allowed_origins=sorted(allowed_origins),
    )


def build_http_app(transport: str) -> Starlette:
    """Build the HTTP app with CORS attached (SDK-004).

    The SDK's own `mcp.run(transport=...)` builds this same app and hands it to
    uvicorn with host, port and log level. It just offers no hook for adding
    middleware, so the app is built here instead. Nothing about the
    session-manager lifecycle changes.
    """
    # Applies to streamable-http only; the legacy SSE transport has no
    # stateless mode, so requesting it there is a no-op and says so.
    stateless = _stateless_requested()
    if stateless and transport == "sse":
        log_event(
            logging.WARNING,
            "stateless_ignored_on_sse",
            hint="MCP_STATELESS applies to streamable-http only; the legacy "
            "SSE transport always keeps a session. Use "
            "MCP_TRANSPORT=streamable-http to run without sessions.",
        )

    # `mcp` 2.0 moved `stateless_http` from a mutable setting to an argument of
    # `streamable_http_app()`, which is strictly better: the mode is a property
    # of the app being built rather than global state a later reader has to go
    # looking for. `sse_app()` takes no such argument, hence the branch.
    host, port = _bind_host(), _bind_port()
    security = build_transport_security(host, port, configured_origins())
    if security is None:
        log_event(
            logging.WARNING,
            "dns_rebinding_protection_off",
            host=host,
            hint="Set MCP_ALLOWED_HOSTS to the hostnames this server is "
            "reachable under; on a non-loopback bind the SDK does not check "
            "the Host header at all.",
        )
    app = (
        mcp.sse_app(transport_security=security, host=host)
        if transport == "sse"
        else mcp.streamable_http_app(
            stateless_http=stateless, transport_security=security, host=host
        )
    )
    return apply_cors(app)


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport in HTTP_TRANSPORTS:
        import uvicorn

        uvicorn.run(
            build_http_app(transport),
            host=_bind_host(),
            port=_bind_port(),
            log_level=mcp.settings.log_level.lower(),
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
