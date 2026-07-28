# Secret management (SEC-013)

## Position: Stufe 1, and that is the whole story

**This server holds no secrets.** The simap.ch read endpoints it wraps are
public and unauthenticated: there is no API key, no token, no password, no
connection string. `ALLOWED_HOSTS` pins egress to `www.simap.ch`, and nothing
in the request path carries a credential.

SEC-013 permits Stufe 1 (plain environment variables) for `Public Open Data`
provided the position is written down. This document is that record. It exists
so a reader auditing the server does not have to infer the absence of secrets
from the absence of code handling them — an absence that looks identical to an
oversight.

## What the environment variables are

Every variable in [`.env.example`](../.env.example) is operational, not secret:
transport selection, bind address and port, CORS origins, log level. Leaking
the full set discloses nothing an attacker could use for authentication,
because there is nothing to authenticate to.

The one variable worth care is `MCP_CORS_ORIGINS`, and its risk is not
confidentiality: setting it to `*` widens who may call an exposed HTTP
transport from a browser. It is fail-closed by default and logs a warning when
set to a wildcard.

## The session cookie is not a secret

`simap.ch` sets a session cookie on the first `/api` call. `httpx` keeps it in
the shared client's cookie jar (see `client.py`), so it is never written to
disk, never logged, and never surfaces in a tool response. It authenticates
nothing — it is a load-balancer affinity token issued to anonymous callers. It
is mentioned here only because "a cookie is involved" invites the assumption
that a credential is involved.

## Container images carry no secrets

The `Dockerfile` copies source and a virtualenv, and sets no `ENV` carrying a
credential. `docker history` on the built image shows no secret layer, and the
CI image build would have nothing to redact.

## What would change this

Each of these moves the server off Stufe 1 and requires this document to be
rewritten before the change ships:

- **Wrapping any authenticated simap endpoint.** The ~200 write / `my/` /
  OIDC-protected endpoints are deliberately out of scope; reaching them means
  holding an OAuth client secret, which is Stufe 3 (secret manager) territory,
  not an environment variable.
- **Adding a second upstream that requires a key.** Same conclusion.
- **Adding auth in front of the HTTP transports.** The sister server
  (`amtsblatt-mcp`) does this and holds an `MCP_API_KEY`; if this server
  follows, the key must be a `SecretStr`, never logged, and this document must
  state its rotation procedure.

## Rotation

Not applicable while no secret exists. If one is introduced, rotation must be
possible without a code change — read at startup from the environment or a
secret manager, with a documented restart or reload path.

## Relationship to the sister server

`amtsblatt-mcp` is the contrasting case in the portfolio: it holds a real
`MCP_API_KEY` for its SSE transport, held as a `SecretStr` so an accidental
`repr()` or f-string renders `**********`. Its own `docs/secret-management.md`
covers that. The two servers are deliberately different here, and neither
document should be copied onto the other.
