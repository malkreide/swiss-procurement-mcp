# Network egress

`swiss-procurement-mcp` makes outbound HTTPS requests to exactly **one** host.

| Host | Purpose |
|---|---|
| `www.simap.ch` | The public simap.ch read API (`/api/...`) — search, detail, reference and code endpoints |

## Code-layer enforcement (SEC-021)

The allow-list is a `frozenset` in
[`constants.py`](../src/swiss_procurement_mcp/constants.py):

```python
ALLOWED_HOSTS = frozenset({"www.simap.ch"})
```

Every outbound request passes through `_assert_host_allowed()` in
[`client.py`](../src/swiss_procurement_mcp/client.py) before it is sent. A request
to any host outside the allow-list raises `UpstreamError` instead of leaving the
process. Because the base URL is hardcoded and no user input reaches the host
component, this can only ever trip on a future refactor that introduces a foreign
host — which is exactly the regression it guards against.

## Changing the allow-list

To add or change an upstream host:

1. Add the host to `ALLOWED_HOSTS` in `constants.py`.
2. If it is a different base than `SIMAP_BASE`, thread the new base URL through the
   client explicitly (do not derive it from user input).
3. Add a row to the table above and note the change in `CHANGELOG.md`.
4. Update `SECURITY.md` if the new host changes the data classification or the
   lethal-trifecta assessment.

## Network-layer enforcement

None is shipped — the server runs as a local stdio process, so there is no
container or cluster network policy. If the server is ever deployed to a
persistent cloud service, add an egress `NetworkPolicy` (Kubernetes) or a security
group restricting outbound traffic to `www.simap.ch:443`, mirroring the
code-layer allow-list.
