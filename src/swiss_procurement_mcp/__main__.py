"""Entry point: stdio (Claude Desktop) or SSE / streamable-http (cloud)."""

from __future__ import annotations

import os

from .server import mcp


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport in {"sse", "streamable-http", "http"}:
        mcp.settings.host = os.environ.get("MCP_HOST", "0.0.0.0")
        mcp.settings.port = int(os.environ.get("PORT", os.environ.get("MCP_PORT", "8000")))
        mcp.run(transport="sse" if transport == "sse" else "streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
