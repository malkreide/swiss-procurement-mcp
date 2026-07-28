"""Entry point: stdio (Claude Desktop) or SSE / streamable-http (cloud)."""

from __future__ import annotations

import os

from starlette.applications import Starlette

from ._cors import apply_cors
from .server import mcp

HTTP_TRANSPORTS = {"sse", "streamable-http", "http"}


def build_http_app(transport: str) -> Starlette:
    """Build the HTTP app with CORS attached (SDK-004).

    The SDK's own `mcp.run(transport=...)` builds this same app and hands it to
    uvicorn with host, port and log level — see `FastMCP.run_sse_async`. It just
    offers no hook for adding middleware, so the app is built here instead.
    Nothing about the session-manager lifecycle changes.
    """
    app = mcp.sse_app() if transport == "sse" else mcp.streamable_http_app()
    return apply_cors(app)


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport in HTTP_TRANSPORTS:
        import uvicorn

        # Bind to loopback by default; exposing all interfaces must be an
        # explicit opt-in (MCP_HOST/HOST=0.0.0.0) rather than the default, so a
        # local run is not silently reachable from the network (SEC-016).
        mcp.settings.host = os.environ.get("MCP_HOST", os.environ.get("HOST", "127.0.0.1"))
        mcp.settings.port = int(os.environ.get("PORT", os.environ.get("MCP_PORT", "8000")))
        uvicorn.run(
            build_http_app(transport),
            host=mcp.settings.host,
            port=mcp.settings.port,
            log_level=mcp.settings.log_level.lower(),
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
