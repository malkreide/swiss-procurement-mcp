"""CORS for the HTTP transports (SDK-004).

MCP over Streamable HTTP or SSE carries the session in the `Mcp-Session-Id`
header. A browser-based client cannot *read* a response header unless the server
names it in `Access-Control-Expose-Headers`, and cannot *send* it on the next
request unless the server names it in `Access-Control-Allow-Headers`. Without
both, a browser client completes the initialize handshake and then loses the
session on the very next call — the failure looks like a broken server rather
than a missing header.

Origins are fail-closed. `MCP_CORS_ORIGINS` is unset by default, which means no
cross-origin browser access at all. That is the right default for a server whose
primary transport is stdio: an operator who wants browser clients names the
origins, and nobody gets a permissive default they did not ask for.

`*` is accepted but never silently: it logs a WARNING and forces
`allow_credentials=False`. That combination is not a policy choice — browsers
reject `Access-Control-Allow-Origin: *` together with credentials, so honouring
the request as asked would produce a config that fails at runtime instead of at
startup.
"""

from __future__ import annotations

import logging
import os

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware

from ._log import log_event

SESSION_HEADER = "Mcp-Session-Id"

# `Last-Event-ID` is how an SSE client resumes a dropped stream; omitting it
# would make reconnection fail only under packet loss, which is the worst kind
# of bug to find in production.
ALLOW_HEADERS = ["Content-Type", "Authorization", SESSION_HEADER, "Last-Event-ID"]

# DELETE terminates a Streamable HTTP session. Without it a browser client can
# open sessions but never close them.
ALLOW_METHODS = ["GET", "POST", "DELETE", "OPTIONS"]

EXPOSE_HEADERS = [SESSION_HEADER]


def configured_origins() -> list[str]:
    """Parse `MCP_CORS_ORIGINS`. Empty by default — no cross-origin access."""
    raw = os.environ.get("MCP_CORS_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


def apply_cors(app: Starlette) -> Starlette:
    """Attach CORS to an MCP HTTP app and return it."""
    origins = configured_origins()
    wildcard = "*" in origins

    if wildcard:
        log_event(
            logging.WARNING,
            "cors_wildcard_origin",
            hint=(
                "MCP_CORS_ORIGINS contains '*'; any site can call this server. "
                "Credentials are disabled as a result — browsers reject "
                "wildcard origin together with credentials. Name explicit "
                "origins for a production deployment."
            ),
        )
    elif not origins:
        log_event(
            logging.INFO,
            "cors_no_origins",
            hint=(
                "MCP_CORS_ORIGINS is unset, so browser-based MCP clients are "
                "not permitted. Set it to a comma-separated origin list to "
                "enable them. stdio and non-browser HTTP clients are unaffected."
            ),
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=ALLOW_METHODS,
        allow_headers=ALLOW_HEADERS,
        expose_headers=EXPOSE_HEADERS,
        # Only with an explicit origin list. With `*` the browser refuses the
        # combination outright; with no origins there is nothing to credential.
        allow_credentials=bool(origins) and not wildcard,
    )
    return app
