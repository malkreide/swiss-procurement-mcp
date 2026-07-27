"""Swiss Procurement MCP — read access to the simap.ch public procurement API."""

from .constants import VERSION as __version__
from .server import mcp

__all__ = ["__version__", "mcp"]
