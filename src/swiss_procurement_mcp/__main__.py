"""Entry point: stdio (Claude Desktop) or SSE / streamable-http (cloud)."""

from __future__ import annotations

import os

from .server import mcp


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport in {"sse", "streamable-http", "http"}:
        # Bind to loopback by default; exposing all interfaces must be an
        # explicit opt-in (MCP_HOST/HOST=0.0.0.0) rather than the default, so a
        # local run is not silently reachable from the network (SEC-016).
        mcp.settings.host = os.environ.get("MCP_HOST", os.environ.get("HOST", "127.0.0.1"))
        mcp.settings.port = int(os.environ.get("PORT", os.environ.get("MCP_PORT", "8000")))
        mcp.run(transport="sse" if transport == "sse" else "streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
