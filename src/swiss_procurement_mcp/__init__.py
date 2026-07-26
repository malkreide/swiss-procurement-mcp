"""Swiss Procurement MCP — read access to the simap.ch public procurement API."""

__version__ = "0.1.0"

from .server import mcp

__all__ = ["mcp", "__version__"]
