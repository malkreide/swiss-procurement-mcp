# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- **Der Backoff-Schlaf wird ueber einen Modul-Alias gepatcht, nicht ueber
  `asyncio.sleep`.** Die Tests nullten die Wartezeit mit
  `monkeypatch.setattr(<modul>.asyncio, "sleep", ...)`. Das liest sich lokal,
  ersetzt `sleep` aber auf dem geteilten Modulobjekt — fuer httpx, respx,
  pytest-asyncio und jeden anderen Importeur im Prozess. Das Modul legt die
  Naht jetzt als `_sleep = asyncio.sleep` offen; gepatcht wird diese.
  `test_der_retry_geht_ueber_den_alias` haelt sie: umgeht der Retry den Alias,
  faellt der Test in Sekundenbruchteilen. Ohne ihn fiel gar nichts — die Suite
  wurde nur ein Vielfaches langsamer, und eine laengere Laufzeit ist kein
  Signal, das jemand liest.

### Fixed

- **The retry had six defects, all inherited from the shared template.** This
  server copied its retry from `reference/retry_backoff.py` in
  [mcp-data-source-probe-skill](https://github.com/malkreide/mcp-data-source-probe-skill),
  and the template shipped these until 2026-08-07. A sweep across eleven
  servers found that none read `Retry-After` and none jittered — one template,
  eleven copies, not eleven independent omissions.
  1. **No jitter.** The ladder was deterministic, so every client that hit the
     same outage retried in lockstep and the load returned as a wave exactly
     when the source recovered — the retry storm extending the outage it was
     meant to bridge. Now spread into `[0.5x, 1.5x]`.
  2. **`Retry-After` was never read.** A 429 or 503 answers the very question
     the backoff curve guesses at. Both RFC 9110 §10.2.3 forms are now read
     (delta-seconds and HTTP-date); an unparseable header yields `None` and
     falls back to the curve — it must never crash on the error path. The
     jitter on top is one-sided `[1.0x, 1.25x]`: the source said *when*, so
     later is polite and earlier ignores the value just read.
  3. **No cap on a single wait**, and the cap now binds *after* the jitter.
     `min(cap, base) * jitter` and `min(cap, base * jitter)` both contain a cap
     and a jitter; only the second is bounded — 20s times 1.5 is 30s.
  4. **The budget counted attempts, not seconds.** Four attempts against an
     upstream that takes 30s to time out is two minutes inside one tool call,
     and an attempt count never says so. Now 25s for the whole call, anchored
     on the MCP SDK's `MCP_DEFAULT_TIMEOUT = 30.0`.
  5. **Nothing held that budget.** It is now an `asyncio.timeout` wall-clock
     deadline rather than an httpx timeout: httpx bounds each *operation*, and
     its read timeout restarts with every chunk, so a slowly trickling response
     outlived the budget without any single read expiring.
  6. **The wrapper hid the failure mode.** `UpstreamError` stays — callers
     branch on it and the 4xx path raises the same type. What changed is what
     the message carries: it interpolated `{last_error}` alone, and
     `httpx.ConnectTimeout`, `ReadTimeout` and `ConnectError` all have an
     **empty** `str()`, precisely the set an outage produces. The sentence read
     `Upstream unreachable after 4 attempts: ` and stopped there. It now names
     the exception type, the host, and which of the two limits ran out.

  `asyncio.wait_for` rather than `asyncio.timeout`, because this package
  supports Python 3.10 (`requires-python = ">=3.10"`) and `asyncio.timeout`
  needs 3.11. Verified against 3.10 locally, not only against the newest
  interpreter in the matrix.

  New `tests/test_retry_policy.py`: `Retry-After` in both forms plus the
  refusal cases, the jitter spread, that the cap binds after jittering, the
  one-sided `Retry-After` jitter, and that an empty `str()` still yields a
  message naming type and host.

## [0.18.5] - 2026-08-02

### Fixed

- **`structlog` carried no upper bound, and the index already serves a major past
  the floor.** The declared range was `structlog>=24.1`; PyPI has been serving
  `26.1.0`. The artefact does not change — the resolver's answer to the next
  fresh install does, and that is exactly how `swiss-energy-mcp` 0.3.3 became
  uninstallable when `mcp` 2.0.0 removed the module it imported.

  Now `structlog>=24.1,<27`. The bound is measured rather than guessed: this package
  installs and imports against `structlog 26.1.0` today, so the cap admits what
  demonstrably works and stops only the next, unknown major.

- **`starlette` carried no upper bound, and the index already serves a major past
  the floor.** The declared range was `starlette>=0.37`; PyPI has been serving
  `1.3.1`. The artefact does not change — the resolver's answer to the next
  fresh install does, and that is exactly how `swiss-energy-mcp` 0.3.3 became
  uninstallable when `mcp` 2.0.0 removed the module it imported.

  Now `starlette>=0.37,<2`. The bound is measured rather than guessed: this package
  installs and imports against `starlette 1.3.1` today, so the cap admits what
  demonstrably works and stops only the next, unknown major.

A dependency range only reaches users through a new release, hence the
version bump. No code changed.

## [0.18.4] — 2026-08-02

### Fixed

- **Every request to simap.ch announced `swiss-procurement-mcp/0.4.0`.** The
  package on PyPI was `0.18.3`; the User-Agent had been fourteen minor versions
  stale for months. Measured at the installed artefact, not in the source tree.

  The cause is worth recording, because it was an earlier repair of this same
  bug. `constants.py` carried

  ```python
  # Single source of truth for the version string; `__init__` re-exports it, so
  # the User-Agent cannot drift from the packaged version again (it said 0.3.0
  # while the package was already 0.3.1).
  VERSION = "0.4.0"
  ```

  A hand-written constant is not a source of truth for a number the build
  decides — it is a second copy, and second copies drift. The comment promised
  the drift could not happen while sitting on top of the mechanism that caused
  it, and `__init__` re-exported the wrong value as `__version__`, so anything
  introspecting the package got it too.

  `VERSION` now comes from `importlib.metadata`, which is written at install
  time by the thing that sets the version and therefore cannot disagree with
  the artefact it describes. The fallback for an uninstalled source tree is
  `0.0.0+source` — a PEP 440 local segment that cannot be read as a release.

- **Nothing in this repository ever asserted anything about the version.**
  `tests/test_version_identity.py` now checks that `VERSION` equals the
  installed distribution, that `__version__` re-exports it, that the
  User-Agent carries it, and that no version literal returns under `src/`.

  The scan is semantic rather than shape-based: this package is full of IP
  literals (`127.0.0.1`, `10.0.0.0/8`) that look exactly like version numbers.
  It matches a version-shaped literal assigned to a version-named constant, or
  one riding inside this package's own User-Agent token. Two further tests
  assert that it fires on both shapes that actually shipped and stays quiet on
  the addresses, the protocol date pin and the fallback marker.

  Worth noting for the portfolio: the standard `scripts/check_version_sync.py`
  would **not** have caught this. It looks for hardcoded versions inside
  User-Agent-shaped strings (`name/version`), and here the literal was a bare
  constant feeding an f-string. Run against this repository in its broken state
  it reported `Versions-Sync OK`.

## [0.18.3] — 2026-07-30

Moves the `ARCH-011` deviation rationale into `README.md`, where the criterion
looks for it. Documentation only.

The 2026-07-30 re-audit found the 0.18.2 record was in the wrong file. The check
asks that "Abweichungen vom Standard sind im README begründet"; the argument sat
in `SECURITY.md`. That is one of the finding's two open criteria — the other is
the missing `tools/` package at nine tools, which stays open by decision — so
`ARCH-011` remains `partial`. Half a finding, closed where it was cheap.

`SECURITY.md` keeps the audit-side facts and links to the README section rather
than repeating the argument. Two copies of the same rationale drift, which this
document already says about parallel chronicles.

### A stale tree, found on the way

Both project-structure trees were out of date, and the German one more so: it was
missing `inputs.py`, `_log.py`, `_fuzzy.py`, `_net.py` and `_cors.py`, the English
one the last three. A structure section that does not list the modules is a poor
argument for the structure being fine, so both now match the package.

## [0.18.2] — 2026-07-30

Records **`ARCH-011`** as a deliberate deviation rather than leaving it looking
like deferred work. Documentation only.

The finding's gap is worded literally: "no `tools/` package — all 9 handlers in
`server.py`". That is accurate, and it is also the whole of it. `server.py` is 902
lines, and `_net`, `_cors`, `_log`, `_fuzzy`, `client`, `constants`, `inputs` and
`models` are already separate modules, so the intent of the check — a codebase
navigable without scrolling an omnibus file — is met.

The companion server was the opposite case and got the opposite treatment: its
`server.py` was 2477 lines holding HTTP plumbing, XML parsing, the taxonomy
cache, the input models and every handler, and `amtsblatt-mcp` 0.21.0 split it.

That refactor is also the argument against doing this one. It introduced a bug —
an extracted module captured a cache global by value, so a tool silently reported
stale state — and the entire suite stayed green, because no test covered the one
path that broke. It was caught by reading the diff, not by CI. Moving nine
handlers to satisfy the literal wording of a criterion whose intent is already met
would take that risk for no navigational gain.

Written down on the same basis as the `SEC-022` namespace criterion in the sister
server: intent met, wording not, recorded as a decision. Revisit if `server.py`
passes roughly 1500 lines.

## [0.18.1] — 2026-07-29

Hardens `tests/test_security_doc.py`. No behaviour change.

Porting this guard to `amtsblatt-mcp` showed the count assertion here was
hollow. It searched the whole document for "29 pass", so any coincidental
mention satisfied it — over there a *historical* sentence ("the estimate
recorded at the time — ~32 pass / 8 partial / 6 fail") did exactly that, and
rewriting the real posture line to a wrong number left the suite green. This
repo does not currently quote its counts twice, so the hole was latent rather
than active, but a guard that depends on prose never repeating a number is not
a guard. The counts are now anchored to a window after the run citation,
because the claim being asserted is that the summary states *this run's*
numbers.

`fail` is checked as well. Leaving it out meant the posture section could
quietly stop naming the two fails this server has while staying green — and the
fails are the part a reader is most likely looking for.

Mutation-tested: each of the three counts, changed in the posture line, fails
the test independently. One of those mutations was wrong on the first attempt —
the prose wraps as `5\npartial`, so a literal "5 partial" replacement was a
no-op that looked like a surviving mutant. The test was already correct; the
mutation was not.

## [0.18.0] — 2026-07-29

Closes **`ARCH-003`**: an empty taxonomy lookup now widens, visibly, and a tender
search still does not.

### The split is the point

The check permits — and this release takes — different behaviour for sensitive
and non-sensitive search tools.

`search_cpv_codes`, `search_construction_codes` and `find_procurement_office`
retry with broader terms when the caller's term finds nothing, and return
`match_type="fuzzy"` with a note naming *both* terms. "No such CPV code" is
rarely the answer anyone wants, and the taxonomy is a closed set the caller can
check against.

`search_procurements`, `search_awards` and `search_procurements_detailed` are
unchanged and stay exact. Broadening a procurement query can surface tenders that
do not answer the question and present them as though they do; "no tender
matched" is a real answer. `test_a_tender_search_never_widens` asserts the
upstream request count, because that is what a widening implementation would
change.

### Silent widening would be worse than the empty result

Every widened response names the original term and the one that produced the
hits. A model seeing only results cannot tell the question was changed under it,
and a bare `match_type: fuzzy` does not let it warn anyone which term the answer
is really about. `match_type` gains `fuzzy` alongside `exact` and `none`.

Every `none` now carries an actionable note: what was tried, what to do next, and
a pointer to `source_status` — an upstream outage looks exactly like an empty
result from the caller's side.

### Measured before it was written

`Schulhausneubau` returns nothing from the live CPV search while `Schul` returns
eighteen codes. `Betonsanierungsarbeiten` nothing while `Beto` returns five. The
upstream matches prefixes, which is why prefix-shortening is the strategy and why
no stemmer is involved — guessing at German morphology would invent terms the
caller never used.

A first implementation stepped down by a fixed 30% per candidate. It looked
reasonable and was wrong: from `Betonsanierungsarbeiten` it reached seven
characters and stopped, three short of the term that works. The schedule is now
geometric between the full word and the floor, so the last attempt is always the
widest one.

`find_procurement_office` widens without a second request — its list is already
in memory, and a re-fetch would multiply traffic against a ~1 MB endpoint. There
is a test asserting the request count for exactly that reason.

Mutation-tested four ways: labelling widened results as exact fails 1, dropping
the empty-result note fails 1, letting a tender search widen fails 2, and
flattening the prefix schedule fails 2.

254 tests pass, `ruff check` and `ruff format` clean.

## [0.17.0] — 2026-07-29

Migrates to **`mcp` 2.x**, which closes the `OBS-001` criterion that 0.16.0 had
to leave open. Protocol version moves from `2025-11-25` to `2026-07-28`.

### The pinned tests did their job

0.16.0 shipped two tests asserting that protocol errors carry **code 0**, with a
stated purpose: *"when the SDK starts emitting a real code this test fails,
which is the point."* It fails now.

Under 2.0 a protocol error carries a real JSON-RPC code — `resources/read` on a
missing resource answers `-32602` (INVALID_PARAMS), `prompts/get` answers
`-32603`. The spec made the same correction independently: `2026-07-28` moved
resource-not-found from `-32002` to `-32602` to align with JSON-RPC and
partitioned the server-error range, reserving `-32020`…`-32099` for MCP.

Both tests were rewritten from pins into assertions, plus a range check so a
regression to `0` cannot pass unnoticed. **`OBS-001` criterion 3 is met.**

Unchanged, and still pinned: an unknown *tool* is delivered as a tool result with
`is_error: true` rather than as a protocol error. And `mask_error_details` does
not exist in 2.0 either, so `OBS-002` stays test-enforced rather than configured.
One thing did improve there — `prompts/get` used to echo the raw `ValueError`
("Unknown prompt: nope") and now answers "Internal server error", keeping the
detail server-side.

### API changes, and why they are small

The SDK surface this server touches turned out to be two imports:

- `mcp.server.fastmcp.FastMCP` → `mcp.server.mcpserver.MCPServer`. Same
  constructor kwargs; `@mcp.tool(annotations=…)`, `mcp.run()`, `sse_app()` and
  `streamable_http_app()` are unchanged.
- `mcp.settings.host` / `.port` / `.stateless_http` are gone. Host and port now
  go straight from the environment to uvicorn, which is where they were always
  headed — the settings object was a detour. `stateless_http` became an argument
  of `streamable_http_app()`, which is better: the mode is a property of the app
  being built rather than global state a later reader has to hunt for.

Tests needed more, all in one file plus three renames: `McpError` → `MCPError`,
`create_connected_server_and_client_session` → `mcp.Client(server)`, and
camelCase → snake_case throughout (`isError` → `is_error`, `inputSchema` →
`input_schema`). The `MCP_STATELESS` tests moved from reading a global to
recording what actually reaches the SDK — a better assertion than the one they
replaced. Mutation-tested: dropping the flag fails 2 tests, routing SSE through
the streamable builder fails 1, dropping the lifespan fails 1.

### What the new spec means for the accepted risks

`2026-07-28` **removes protocol-level sessions**: no `initialize` handshake, no
`Mcp-Session-Id`, no SSE stream resumability. It also reclassifies HTTP+SSE as
Deprecated with a twelve-month removal window.

Nothing breaks today — the SDK still ships the legacy transports, and `_cors.py`
was re-verified against the `starlette` 1.3.1 that `mcp` 2.0 pulls in (preflight
200, session header allowed and exposed, `DELETE` allowed). But it changes what
`SEC-009` and `SCALE-002` are *about*: they move from controls this server has
not implemented toward controls the protocol no longer defines. They stay `fail`
until the audit catalogue catches up, because reclassifying a finding on our own
authority is exactly the kind of quiet drift these documents exist to prevent.
`ROADMAP.md` now carries retiring SSE as dated work rather than a someday.

232 tests pass (one more than 0.16.0 — a negative control for the stateless
flag), `ruff check` and `ruff format` clean.

## [0.16.0] — 2026-07-28

Closes **OBS-001** as far as this repository reaches.

### A client-level test of the error paths

The gap was precise: no test distinguished the protocol-error path from the
execution-error path. Every existing test called the tool functions directly,
where `isError` is not observable at all — the distinction the check is about
was invisible to the entire suite.

`tests/test_error_paths.py` drives a real `ClientSession` over an in-memory
transport instead. Nine tests, covering:

- **Execution errors** — an over-long query and an unknown field both arrive as
  a tool result with `isError: true`, carrying no traceback and no filesystem
  path.
- **The `degraded` envelope** — an upstream outage stays a *result*, with
  `provenance="degraded"` and `count == 0`, and is asserted to be
  distinguishable from a genuinely empty answer. That is a deliberate deviation
  from the check, defended in the test's own docstring: the envelope carries the
  source, the retrieval time and a note, where raising would collapse all of it
  into one line and lose the difference between "nothing matched" and "I could
  not ask".
- **Protocol errors** — a request for a method the server does not implement
  raises `McpError` rather than returning a result.

Mutation-tested: making the degraded path raise fails 2 tests.

Two things went wrong while writing this and are worth naming. The
degraded-versus-empty test used the same query twice, so the shared client cache
(see `SDK-001`) served the second call as `cached` and the test asserted nothing
about degradation at all. And the file cost 28 seconds until the real 2s/4s/8s
retry backoff was stubbed out — the timing is tested in `test_resilience.py`, and
paying for it again here bought nothing.

### Two SDK limits pinned rather than papered over

- Protocol errors carry **code 0**, not the `-32601` the check asks for, even
  though `mcp.types` defines `METHOD_NOT_FOUND` and friends. That is above the
  tool layer; nothing here can change it.
- An unknown **tool** is reported as `isError` inside a tool result rather than
  as a protocol error, so "no such tool" and "the tool failed" are
  indistinguishable to a client without reading the text.

Both are asserted as they are, so an SDK change arrives as a failing test rather
than as a surprise. `OBS-001` therefore stays `partial` — for a reason that is
now written down instead of unknown.

### Documentation caught up with the code

`ROADMAP.md` still listed `SEC-004`, `SEC-005` and `ARCH-002` as open work; all
three were closed in 0.13.0 and 0.14.0, within twenty minutes of the table being
written. `SECURITY.md` still described the `ARCH-012` README contradiction as
live, though it was fixed in 0.11.1 with a parametrised guard over both language
files.

`SECURITY.de.md` was the worse case. Its accepted-risk section had not been
updated since 0.2.0 and still told a German reader that the HTTP transports "run
stateless, so a second instance would not break sessions" — the exact claim the
English file corrects as **wrong**. Both assessments are rewritten to match, and
the stale release chronicle above them now says so rather than reading as
current. A wrong reassurance in a security document is worse than an open
finding.

### `mcp` constrained below 2.0

`mcp` 2.0.0 was published and removed `mcp.server.fastmcp` outright — the API
moved to `mcp.server.mcpserver`. The dependency was an unbounded `>=1.28.1`, so
CI resolved to it and every job died on `ModuleNotFoundError` at import: `main`
as well as open branches, with nothing in any diff to explain it.

Now `>=1.28.1,<2`. Verified rather than assumed: the full suite runs green
against 1.29.0 and `LATEST_PROTOCOL_VERSION` is unchanged at `2025-11-25`, so
the bound admits the newest compatible release and excludes only the break.

Migrating to the 2.x API is real work and a decision to take deliberately. A
resolver picking a major version on publication day is not that decision.

### CI — the MCP registry publish is idempotent

The PyPI step carries `skip-existing: true`; the registry step had no
equivalent, so a second trigger for a version already published turned a
completed release into a red build.

Not hypothetical: it happened three times (publish runs #1, #3, #7), always the
same way — a `workflow_dispatch` publishes successfully, then the tag push for
the same version arrives minutes later and is rejected as a duplicate. This
workflow declares both triggers and both are legitimate, so the collision is
designed in rather than a release mistake.

A duplicate means the desired end state already holds, so it is now treated as
success. **Every other failure still fails the job** — the point of a red
publish build is that a real failure gets noticed, and it will not be if the
usual outcome is also red. The historical PyPI-404 case (registry looking for a
release that never reached PyPI) still fails, which was verified rather than
assumed: the step's shell was extracted and run against four outcomes — success,
duplicate, 404, and a non-1 exit code.

No package change of its own; it ships with this release.

## [0.15.0] — 2026-07-28

**SEC-009** and **SCALE-002**: addressed as far as the SDK and the absence of an
identity provider allow. Neither flips to `pass`, and the reasons are now written
down precisely rather than as "accepted risk".

### `MCP_STATELESS`

Opt-in session-free operation for the streamable-http transport. With no session
tracking there is no session id to bind to a user and none to route consistently
to an instance — both problems are removed rather than solved.

Opt-in rather than default because it is not free: a stateless server cannot
resume an interrupted SSE stream or deliver server-initiated notifications, both
of which need a session to belong to. Requesting it on the legacy SSE transport
logs a warning and changes nothing, because leaving the flag set there would tell
an operator they are session-free when they are not.

### `docs/load-balancing.md`

nginx and Kubernetes Ingress configurations keyed on `Mcp-Session-Id`, with the
buffering and timeout settings the long-lived transports need — plus the honest
part: **affinity prevents misrouting, not loss.** If the instance holding a
session dies, the session dies with it and a correct client re-initializes.

### Two limits found by reading the SDK rather than assuming

- **No explicit session TTL is settable.** `session_idle_timeout` exists on
  `StreamableHTTPSessionManager`, but FastMCP passes it through neither
  `Settings` nor its constructor. Same class of limitation as
  `mask_error_details`, and the reason `SCALE-002` still cannot pass.
- **`SEC-009` is unreachable, not merely unimplemented.** It requires a user id
  from a validated OAuth `sub` claim. This server has no authentication at all,
  so there is no identity to bind to.

### A false claim corrected

The previous SECURITY.md stated the HTTP transports "run stateless, so a second
instance would not break sessions". That was wrong — `stateless_http` defaults to
`False`, so streamable-http did keep per-client sessions in memory. The
correction is stated explicitly rather than quietly removed: a wrong reassurance
is worse than an open finding.

## [0.14.0] — 2026-07-28

Closes **ARCH-002**: every tool description carries a `<use_case>` tag.

The description is what the model reads when choosing between tools, and naming
the *function* is not the same as naming the *occasion*. All 9 tools now
open with a `<use_case>` block stating when to reach for them — including the
distinctions that are invisible from the name, such as when the aggregated
search is preferable to a search followed by N detail calls.

`test_tools_carry_a_use_case_tag` enforces the 80% floor and
`test_no_description_is_too_short` a 100-character minimum. Mutation-tested:
stripping the tag from three tools fails the coverage guard.

## [0.13.0] — 2026-07-28

Closes **SEC-004** and **SEC-005**: resolved-address blocklist and DNS pinning.

### What the host allow-list could not do

The allow-list answers "is this the name we meant?". It cannot answer "is this
the *machine* we meant?" — a name resolves to an address, and nothing about an
allow-listed hostname stops that address being `169.254.169.254` or `127.0.0.1`.
DNS is controlled by whoever runs the zone.

`_net.py` adds both halves, and they only work together:

- **Blocklist** — the resolved address is checked against loopback, private,
  CGNAT, link-local, unique-local, benchmarking and unspecified ranges, IPv4 and
  IPv6. A name resolving to a *mix* of public and internal addresses is refused
  rather than filtered: a zone answering both is not a configuration to paper
  over by picking the good one.
- **Pinning** — validating an address and then connecting *by hostname* is a
  time-of-check/time-of-use bug. The second lookup can answer differently; that
  is DNS rebinding, and it defeats a blocklist entirely.

### Pinned via a custom resolver, not by rewriting the URL

The first implementation rewrote the request URL to the literal IP and carried
the hostname in `Host` and `sni_hostname`. It worked against the live API — but
it changes what every layer above the socket sees, and it broke 66 respx-based
tests whose routes match on the URL.

Gating that on a test flag would have been the "control that holds in one path
but not the other" problem this codebase keeps finding. The check catalogue
names a *custom resolver* as an accepted implementation, so pinning now happens
in a network backend: only the address the socket opens to is substituted, and
the hostname stays intact all the way down. `Host` and TLS SNI are derived from
the name as usual, so certificate validation still runs against it — verified
against the live API, not assumed.

### Tests

`tests/test_ssrf.py`. The load-bearing one is
`test_rebinding_second_lookup_is_never_used`: a zone answering public once and
internal immediately after must never reach the internal address. It is the only
test that fails if an address is validated and the connection then made by
hostname anyway.

`test_resolution_happens_exactly_once_per_connect` covers the "1 DNS call per
request" criterion directly.

Mutation-tested: connecting by hostname fails 2 tests, removing link-local from
the blocklist fails 3, filtering a mixed answer instead of refusing it fails 2,
and dropping the backend installation fails 1.

## [0.12.0] — 2026-07-28

Tier-A audit remediation: **ARCH-005, SEC-004, SEC-013, OPS-003, SDK-002,
OPS-002**.

### ARCH-005 — `.env.example`

The server holds no secrets, but it does honour seven environment variables, and
they were documented nowhere as a set. The file is the configuration surface in
one place. `test_env_example_documents_every_environment_variable` scans `src/`
for `environ.get(...)` and fails on anything the template omits — a stale
`.env.example` is worse than none, because it reads as authoritative.

### SEC-004 — HTTPS is now enforced, not assumed

`_assert_host_allowed` checked the host and not the scheme, which left a gap
that read as covered: `http://www.simap.ch/...` passes a hostname allow-list
while sending the request in the clear. Checked first, so a plaintext URL
reports the scheme rather than the host.

Still open: resolved-IP blocklist and DNS pinning. `SEC-004` stays `partial`.

### SDK-002 — `match_type` is a `Literal`

Typed as `str`, the schema advertised "any string" for a field that only ever
takes `exact` or `none`, so a model had no way to know what to expect back —
the same class of mismatch as a tool schema advertising a value the tool
rejects. Now `MatchType = Literal["exact", "none"]`, derived once and used by
all four response models.

### SEC-013 — `docs/secret-management.md`

Records the Stufe-1 position and, more usefully, that there is nothing to
protect: the wrapped endpoints are public and the server holds no credential.
An absence of secret-handling code looks identical to an oversight unless it is
written down. Also states that the simap session cookie is not a credential —
it authenticates nothing — because "a cookie is involved" invites the opposite
assumption.

### OPS-003 — `ROADMAP.md`

Phase-specific backlog, linked from both READMEs. `ARCH-003` is recorded as
needing a design decision before code: fuzzy matching is right for the code
lookups and questionable for tender search, where silently widening terms can
imply a tender exists when none does.

### OPS-002 — README parity

`README.de.md` gains *MCP Protocol Version* and *Primitive: nur Tools*. Both
files now carry 19 top-level sections.

All new guards mutation-tested: dropping the scheme check fails 4 tests,
deleting `.env.example` fails 3, adding an undocumented environment variable to
the code fails 1.

## [0.11.1] — 2026-07-28

Closes **ARCH-012**: the README no longer contradicts itself about the protocol
version.

Two consecutive audits reported this and it went unfixed both times. The *MCP
Protocol Version* section stated the version is pinned as an explicit constant,
while *Maturity & updates* further down still said it was "negotiated by the
pinned `mcp` SDK" — the opposite claim, and the one a reader skimming for the
update policy hits first. `README.de.md` carried the same contradiction.

Both now point at the pinned constant. `test_readme_does_not_contradict_the_pin`
is parametrised over both files, so the sentence cannot come back in either
language: prose drifts away from the code it describes unless something fails
when it does. Mutation-tested by restoring the sentence.

## [0.11.0] — 2026-07-28

Closes **SDK-004**: CORS exposing and accepting `Mcp-Session-Id`.

### The defect

MCP over Streamable HTTP or SSE carries the session in the `Mcp-Session-Id`
header. A browser cannot *read* a response header the server does not name in
`Access-Control-Expose-Headers`, and cannot *send* it back unless the server
names it in `Access-Control-Allow-Headers`. There was no CORS layer at all, so a
browser-based MCP client completed the initialize handshake and then lost the
session on the very next call — a failure that looks like a broken server rather
than a missing header.

### The change

`FastMCP.run(transport=...)` offers no hook for adding middleware, so
`__main__.py` now builds the Starlette app itself and runs uvicorn. That is
exactly what the SDK does internally — see `FastMCP.run_sse_async`, which builds
the same app and passes host, port and log level to uvicorn — so no part of the
session-manager lifecycle changes.

`_cors.py` attaches `CORSMiddleware` with `Mcp-Session-Id` in both
`expose_headers` and `allow_headers`, `Last-Event-ID` for SSE stream resumption,
and `DELETE` among the allowed methods so a browser client can terminate a
session rather than only opening them.

### Origins are fail-closed

`MCP_CORS_ORIGINS` is unset by default, meaning no cross-origin browser access.
That is the right default for a server whose primary transport is stdio. `*` is
honoured but logs a WARNING and forces `allow_credentials=False` — browsers
reject a wildcard origin together with credentials, so accepting both would ship
a config that fails at request time rather than at startup.

`tests/test_cors.py`, 10 tests, driving real requests through the assembled app
rather than inspecting the middleware stack — asserting that a `CORSMiddleware`
object exists would pass with an empty `expose_headers`, which is the defect
itself. Mutation-tested against five reversions; each is caught by the test
written for it.

`starlette` and `uvicorn` are now declared dependencies. Both arrived
transitively via `mcp`, but this module imports them directly.

## [0.10.0] — 2026-07-28

Closes **SDK-001**: one pooled HTTP client behind the server lifespan.

### The defect

Every one of the nine tools opened its own `httpx.AsyncClient` through
`async with SimapClient()`, and `FastMCP` was constructed with no `lifespan`.

The connection cost was the obvious half — a TCP handshake and TLS negotiation
on every tool call. The half that made this a correctness bug is that `_cache`
and the session cookie jar live on the `SimapClient` instance. A client that is
discarded when the tool returns can never serve a cache hit and re-acquires the
session cookie every time, so `_cached` was dead code wearing the shape of a
working cache. The 30-minute TTL had never once been reached.

### The change

- `client.get_client()` returns a process-wide `SimapClient`, built lazily on
  first use and rebuilt if the underlying client was closed.
- `client.close_client()` releases it; a `_lifespan` async context manager
  passed to `FastMCP` calls it on shutdown.
- The nine tool bodies take `client = get_client()` instead of opening one.
- `SimapClient.__aenter__` / `__aexit__` are unchanged, so the context-manager
  form still works for the live tests and for any caller that wants an
  isolated client.

`tests/test_client_pooling.py` (8 tests) covers it. The one that would have
caught the original defect is `test_repeat_search_hits_the_api_once`: two
identical searches must produce exactly one upstream request, and the second
response must report `provenance == "cached"`. Both halves of the fix were
mutation-tested — restoring per-call construction fails 4 tests, dropping the
`lifespan=` argument fails the lifespan assertion.

### Test isolation

A shared cache across tool calls is also a shared cache across *tests*: one
case could serve another case's assertion out of `_cache` and pass without
touching the API. `tests/conftest.py` gains an autouse fixture that drops the
shared client around every test. Autouse rather than opt-in, because the
failure mode is silent.

## [0.9.0] — 2026-07-28

Closes OPS-001. Two real bugs surfaced while writing the tests — which is the
argument for the finding, not a side note.

### The gap

OPS-001 asks for at least 5 unit tests and 1 live test per tool. Counted rather
than estimated, seven of the nine tools were short, four of them sitting at
exactly one unit test:

| Tool | before | after |
|---|---|---|
| `get_procurement_details` | 1 / 0 | 6 / 2 |
| `get_publication_history` | 1 / 0 | 6 / 1 |
| `find_procurement_office` | 1 / 0 | 6 / 1 |
| `source_status` | 1 / 1 | 6 / 1 |
| `search_awards` | 2 / 1 | 6 / 1 |
| `search_construction_codes` | 2 / 0 | 6 / 1 |
| `search_procurements_detailed` | 3 / 0 | 5 / 1 |

That distribution is where a silently broken tool survives a green suite. It did.

### Fixed — `find_procurement_office` crashed on a bare-list payload

The tool probes three payload shapes because the upstream has been observed
returning the office list under different keys. The list branch was unreachable:
it sat last, after two `payload.get(...)` calls that raise `AttributeError` on a
list. So the shape the code claimed to handle was the one shape that crashed it.

Reordered to check `isinstance(payload, list)` first. Each of the shapes now has
its own test.

### Fixed — the tool schema advertised a value the tool rejected

`ConstructionCodeInput.system` was typed against the full `CODE_SYSTEMS`, which
includes `cpv` — and `search_construction_codes` then raised `ValueError` on
`cpv`, pointing at `search_cpv_codes`.

A model trusting the tool schema was *guaranteed* to hit that error. The Literal
is now derived as `CODE_SYSTEMS` minus `cpv`, so the schema states what the tool
accepts. A parametrised test asserts every advertised system is actually
accepted — the general form of this bug.

### Added

- `tests/test_tool_coverage.py` — 40 tests targeting the paths that break
  quietly: payload-shape fallbacks, degraded envelopes, language selection,
  client-side filtering and truncation
- Five live tests, one per previously-uncovered tool. Mocked tests cannot catch
  an upstream shape change; a fixture keeps passing against a shape the API no
  longer returns.
- A coverage-floor guard, so a new tool cannot arrive under-tested and
  rediscover this finding at the next audit. Mutation-tested by raising the
  floor.

### Note on suite runtime

The seven degraded-path tests initially cost ~115s, because each one waits out
three real retries at 2s/4s/8s. They now reuse the `no_backoff_delay` fixture
pattern already established in `test_resilience.py`: 115s → 4s. The retry logic
itself is still tested there; these tests only care about the envelope.

## [0.8.1] — 2026-07-28

Documentation only. Records SEC-009 and SCALE-002 as accepted risks, and repairs
drift in `SECURITY.md` that had been there for four audit runs.

### SEC-009 and SCALE-002 — accepted, with the condition that ends each

Both were going to be closed by removing the HTTP transports, which would have
made them non-applicable. Measuring that change first showed it also drops
**SEC-005** and **SEC-016** from the applicable set — and both of those *pass*.
SEC-016 is `critical` and was closed with real work in v0.1.1 (the loopback
default bind).

So the scope reduction would have traded two documented partials for two earned
passes, and made the server no safer. The transports stay; the two findings are
recorded as accepted risks instead, each with the condition that would end the
acceptance:

- **SEC-009** becomes real the moment the server gains authentication, per-user
  state, or any endpoint whose response depends on who is asking.
- **SCALE-002** becomes real when multi-instance deployment and session state
  exist *together*. Either alone is survivable.

### Fixed — SECURITY.md described a server that no longer existed

The document still cited **15 pass / 16 partial / 1 fail** from the first audit,
four runs stale, and listed *container sandboxing* and *structured logging* as
accepted risks — long after both were implemented and had flipped to `pass`.

That is worse than an omission. A stale acceptance reads as a considered
decision, so a reader auditing this server would have concluded it ships no
container and no structured logging. Both are removed from the list rather than
edited in place, with a note saying they were closed rather than dropped.

Same corrections applied to `SECURITY.de.md`.

### Added

- `tests/test_security_doc.py` — asserts SECURITY.md cites the newest audit run,
  quotes that run's counts, and never lists a check as an accepted risk while
  the latest audit has it passing. Mutation-tested by re-adding a closed check
  to the list.

## [0.8.0] — 2026-07-28

Closes ARCH-009, ARCH-008 and ARCH-012 from the 2026-07-28 re-audit. One
annotation, one constant, and documentation — no behaviour changes.

### ARCH-009 — `destructiveHint` set explicitly

`READ_TOOL` declared `readOnlyHint`, `idempotentHint` and `openWorldHint` but
omitted `destructiveHint`, leaving it to the client's default. The check asks
for explicit annotations, and a default by omission is not the same statement as
"these tools destroy nothing" — the companion `amtsblatt-mcp` has set it
explicitly all along.

One line, and it was carrying a `high` severity.

### ARCH-012 — MCP protocol version pinned

**Spec version `2025-11-25`** is now pinned as `MCP_PROTOCOL_VERSION` in
`server.py`, with a new *MCP Protocol Version* section in the README stating the
version, where it lives, and the update policy.

The SDK offers no way to configure this — negotiation happens in the session
layer, and neither `FastMCP.__init__` nor `Settings` takes the parameter. So the
pin is a declared constant plus detection: a mismatch logs
`protocol_version_drift` at `WARNING` at runtime, and
`tests/test_protocol_version.py` fails in CI.

That split is deliberate. An SDK bump should break *our* build, not the runtime
of someone who upgraded `mcp` downstream.

Future protocol-version bumps get their own CHANGELOG line rather than being
folded into a dependency-bump entry.

### ARCH-008 — tools-only rationale documented

The check accepts either two of the three primitives or a documented reason for
using one. The README now carries the reason.

Two tools were checked concretely for resource-migration potential and rejected
with specific reasons rather than by blanket policy: `source_status` is
resource-shaped but exists to be *called* when a result looks wrong, and a
resource the model must remember to re-read is worse at that job; the CPV
catalogue is enumerable but ~10k entries, and pushing it into the context window
defeats the point of a server-side lookup.

Resources and prompts will be revisited if this server ever gains a genuinely
enumerable, slow-changing dataset. simap is the opposite — every useful call is
a filtered query over a corpus that changes intraday.

### Added

- `tests/test_protocol_version.py` — 4 tests: the pin matches the installed SDK,
  it is a dated spec version rather than a moving target, and the README names
  both the version and an update policy

## [0.7.0] — 2026-07-27

Closes the two findings the 2026-07-27 re-audit left open. No tool, argument or
return shape changed.

### SEC-007 — container hardening

`useradd --system` picked a UID from the 100–999 range, which the check rejects.
That range is reserved for host system accounts, so under a bind mount the
container user can inherit a real host user's ownership — and the exact number
depends on package install order, so it moved between rebuilds. Now an explicit
`10001`, with a numeric `USER 10001:10001` and a matching `user:` in compose.

**seccomp:** Docker already applies its built-in profile — the equivalent of
Kubernetes' `RuntimeDefault` — and Compose has no syntax that names it. The
obvious-looking line is actively harmful:

```yaml
security_opt: [seccomp:unconfined]   # WRONG — this DISABLES seccomp
```

So the posture is stated in a comment and in `docs/container-hardening.md`
rather than "fixed" with a line that makes things worse.

CI asserts both rather than trusting the Dockerfile: uid ≥ 10000 (not merely
non-zero) and `Seccomp: 2` in `/proc/self/status`. The probe runs through
`python` rather than `grep -oP`, because PCRE support in the base image is an
assumption and the interpreter is not.

### OBS-003 — structured logging

Moved to [structlog](https://www.structlog.org/). The previous implementation
was stdlib `logging` with a hand-rolled JSON formatter: structured output, but
no logging library in `dependencies`, only two severity levels ever emitted, and
nothing correlating the events of one call.

This was flagged before starting as the one item where the obvious fix would be
cosmetic — adding a dependency for a checkbox, emitting `DEBUG` to reach a
count. What settled it was the third gap. `structlog.contextvars` binds context
to the async task, so an event emitted deep inside the HTTP client carries the
surrounding call's `correlation_id` without being threaded through every
signature. That is a capability, not a formality, and it is the one gap that
could not be closed by hand.

The four levels sit where they carry operational meaning:

| Level | Emitted when |
|---|---|
| `DEBUG` | tool entry — tells you whether a hung call was ever entered |
| `INFO` | tool finished cleanly, with latency |
| `WARNING` | upstream degraded |
| `ERROR` | the tool raised; exception **type** only, never the message |

`log_event` keeps its int-based signature, so no call site outside `_log.py`
changed.

#### What the tests had to work around

`structlog.testing.capture_logs` replaces the entire processor chain, which
silently drops `merge_contextvars`. Every correlation assertion would have
passed vacuously, and the context-leak test would have proven nothing at all —
the id it checks for absence of is *always* absent under `capture_logs`.

So `configure_logging` grew test-only keyword arguments and the chain is exposed
as `processor_chain()`, letting the tests drive the production pipeline into a
`StringIO` rather than a copy of it. The stdout test runs in a subprocess for
the same reason: in-process, pytest replaces the streams, so a logger holding
the wrong one would still look correct.

### Added

- `docs/container-hardening.md` — incl. the Kubernetes `securityContext`
  equivalent and how to verify seccomp on a running container
- `structlog>=24.1` dependency

## [0.6.0] — 2026-07-27

Closes the last two open `high` findings, SEC-018 and SEC-007. **Breaking: every
tool now takes a single argument object.**

### Breaking — tool arguments move into one validated object

Tools used to take flat keyword arguments. They now take one input model each:

```diff
- search_procurements(canton="ZH", query="Schulhaus", limit=20)
+ search_procurements({"canton": "ZH", "query": "Schulhaus", "limit": 20})
```

This is the shape SEC-018 requires and the shape the companion `amtsblatt-mcp`
already uses, so the two servers now read the same way. No tool was renamed, no
argument was renamed, removed or given a different meaning, and no return shape
changed — only the nesting.

### SEC-018 — validation moves from the tool body to the boundary

Bounds used to be enforced imperatively inside the tools by `_check_limit` and
`_check_text`, which meant the model could not see them: the tool schema
advertised a bare `integer` and the rejection only happened after the call.

`inputs.py` now declares them, so they appear in the tool list:

| | before | after |
|---|---|---|
| `limit` | `{"type": "integer"}` | `{"type": "integer", "minimum": 1, "maximum": 100}` |
| `query` | `{"type": "string"}` | `minLength` 2, `maxLength` 200, whitelist `pattern` |
| `canton` | `{"type": "string"}` | enum of the 26 ids |

Every model sets `strict=True` and `extra="forbid"`:

- **`strict=True`** — no coercion. `limit="10"` is now an error rather than
  silently becoming `10`, so type confusion is reported instead of hidden.
- **`extra="forbid"`** — an unknown field is rejected rather than dropped. A
  silently-ignored field looks accepted, which is prompt-injection surface.

The allow-lists (cantons, process types, publication types, code systems,
languages) are **derived from `constants.py`** rather than restated, so a probe
that updates those tables cannot leave a stale copy behind in the schema. A
parametrised test asserts the derivation still holds.

`_check_limit` and `_check_text` are gone; the schema does their work.

#### One deliberate tightening

Under `strict=True`, `language="DE"` is now rejected instead of being
lower-cased to `"de"`. Silent normalisation is exactly what strict mode exists
to prevent, so this is intended rather than incidental.

#### One thing the new tests caught

The first draft of the free-text whitelist used `\s` for whitespace. `\s`
matches CR and LF, so `query="a\r\nX-Injected: 1"` passed the filter — a
whitelist with a hole in it. The pattern now uses a literal space; a
procurement keyword never needs a line break. The test that found it is in
`tests/test_input_models.py` and is still there.

#### Where validation now happens

Schema violations are rejected *before* the tool body runs, so they no longer
produce a `tool_call` log record — there is no call to account for. Errors
raised inside a tool body still log with `status="error"` as before. Both
behaviours are pinned by tests.

### SEC-007 — hardened container

Ported from `amtsblatt-mcp`: multi-stage `Dockerfile`, non-root system user,
plus a `compose.yaml` with a read-only root filesystem, `cap_drop: [ALL]`,
`no-new-privileges`, and memory/CPU/PID limits. No runtime secret — the wrapped
endpoints are public.

Pinned to `python:3.12-slim` rather than the newest interpreter, because CI
tests 3.10–3.12; shipping an image on a version no test runs against would put
the container outside the evidence the rest of this repo relies on.

CI gained a `Docker build` job that does more than build: it asserts the image
does not run as uid 0, and that the server still imports under
`--read-only --cap-drop ALL`. A Dockerfile that builds but runs as root would
otherwise pass silently while failing the check it was written for.

### Added

- `src/swiss_procurement_mcp/inputs.py` — nine strict input models
- `tests/test_input_models.py` — 40 tests, one group per SEC-018 pass criterion,
  including the allow-list drift guard and the whitelist-pattern cases
- `Dockerfile`, `compose.yaml`, `.dockerignore`, and the `Docker build` CI job

## [0.5.0] — 2026-07-27

Closes OBS-003, the only `fail` in either server's audit. No behaviour changes.

### The gap

The 2026-07-27 re-audit graded OBS-003 down from `partial` to `fail` on unchanged
code: this server had no logging at all — no mechanism, no output format, no
severity levels, no per-call context. Exactly one of five criteria was met, and
that one was "does not use `print()`", which it met by having no output at all.

An operator running this server could not answer "is it being called, is it
slow, is simap.ch up" from anything the process emitted.

### Added

- **`_log.py`** — structured JSON to stderr, ported from the companion
  `amtsblatt-mcp`. One change was needed: the tools here take ordinary keyword
  arguments and return Pydantic models, where the original assumed a single
  `params` model and a `str` return, so `logged_tool` now wraps
  `*args, **kwargs` generically.
- **One `tool_call` record per call** on all nine tools, carrying tool name,
  `ok`/`error` status and latency in milliseconds. Rejected inputs count as
  `error` rather than going unrecorded.
- **`upstream_degraded` at `WARNING`** on simap.ch failures, carrying the
  exception *type*. `_degraded()` is the single funnel for all eight upstream
  failure paths, so one call site covers every one of them.
- **`LOG_LEVEL`** (default `INFO`), documented in the README's configuration
  table alongside a sample record.

### Why stderr, specifically

On a stdio transport stdout carries the MCP protocol; one stray line there
corrupts the session. The logger writes to stderr and sets `propagate = False`
so records cannot reach root handlers, which commonly target stdout.
`tests/test_logging.py` asserts both, and asserts them against the constructor
path rather than the import-time handle that pytest's capture replaces.

### The risk this port carried

`logged_tool` wraps `*args, **kwargs`, and FastMCP derives each tool's argument
schema from the function signature. Had `functools.wraps` not set `__wrapped__`
for `inspect.signature` to follow, every tool would have silently degraded to
"no arguments" — a regression no existing test would have caught, since the
functions stay directly callable and the whole suite calls them directly.
`test_decorator_preserves_the_tool_argument_schema` goes through
`mcp.list_tools()` and pins the real parameters instead of assuming.

### Not changed

OBS-002 still holds: the sanitised note the model sees never carries the
exception message or an upstream response body, and the new `WARNING` record
carries only the exception type — asserted by a test that feeds a URL with a
token in it and checks it does not appear in the log.

## [0.4.0] — 2026-07-27

Correctness release. The canton filter was measurably wrong, and the fix changes
what `canton=` means — see *Breaking* below.

### Breaking

- **`canton=` now matches the PROCURING BODY, not the place of delivery.**

  simap offers exactly one geographic filter, `orderAddressCantons`, and the
  OpenAPI spec describes it as the canton the project *takes place* in. When a
  procuring office files a free-text address (`orderAddressOnlyDescription:
  "yes"`) the structured `orderAddress.cantonId` is `null` and the publication is
  invisible to that filter. Measured CH-wide over 500 projects published since
  2026-07-01: **303 (60.6%) carry no canton** — among them the Amt für Hochbauten
  Zürich, Grün Stadt Zürich, Universitätsspital Zürich, BBL and SBB.

  `issuedByOrganizations` is the remedy: the spec states it matches publications
  issued by an organisation *or as a child of it*, so one root institution id
  covers a canton's whole tree of procurement offices. `/institutions/v1/institutions`
  is public and returns 28 roots — the 26 cantons plus Bund and Ausland.

  Measured for ZH over 2026-07-01…27, both filters fully paginated:

  | Filter | Projects |
  |---|---|
  | `orderAddressCantons=ZH` (old behaviour) | 263 |
  | `issuedByOrganizations=<Zürich>` (new default) | **410** |
  | union | 441 |

  The 31 projects only the address filter finds are federal bodies procuring in
  Zurich (ETH, Empa, Flughafen Zürich AG) — a different question, not a gap.
  Hence three explicit semantics via the new `canton_match` argument
  (`procuring_body` default, `place_of_delivery`, `both`) rather than a silent
  union, and every response states in `note` which one was applied.

  To keep the previous behaviour, pass `canton_match="place_of_delivery"`.

- **A filterless `search_procurements()` now raises instead of returning empty.**
  simap answers an unfiltered project-search with zero projects, not with
  everything. The old code reported that as "No publications matched. Widen the
  date range" — a misdiagnosis, since nothing had been narrowed. It now says
  that at least one filter is required.

### Fixed

- **`mcp>=1.28.1`** (was `>=1.2.0`), matching the CVE-2026-59950 floor already
  set in the companion server `amtsblatt-mcp`.
- **User-Agent no longer drifts from the package version.** It advertised 0.3.0
  while the package was 0.3.1; `VERSION` in `constants.py` is now the single
  source and `__init__.__version__` re-exports it (it had been pinned at 0.1.0).

### Added

- `canton_match` on `search_procurements`, `search_procurements_detailed` and
  `search_awards`; `CANTON_INSTITUTION_IDS` (26 pinned root institution ids) and
  `SimapClient.institutions()`.
- **Live drift guards.** One verifies all 26 pinned institution ids are still
  root institutions and that exactly 28 roots exist; another checks
  `PUB_TYPES`, `PROCESS_TYPES` and `PROJECT_SUB_TYPES` against the machine-readable
  spec at `https://www.simap.ch/api/specifications/simap.yaml` (13/13, 5/5, 10/10
  — currently exact). A third asserts `procuring_body` keeps finding at least as
  much as `place_of_delivery`.

### Changed

- Documented that `project-search` indexes **projects**, not publications: each
  hit is a project represented by its newest publication. `search_awards`
  consequently only finds projects whose *newest* publication is an award — a
  later correction hides it, and `get_publication_history` is the way back.
  Tool descriptions and README updated; no behavioural change.

## [0.3.1] — 2026-07-27

Release-plumbing only — no functional change to the server or its tools.

### Fixed

- **MCP Registry publish.** The registry rejected `server.json` with a `422`
  because `description` exceeded the 100-character limit (it was 217). Shortened
  to 97 characters, keeping the searchable domain terms and the scope claim
  (all cantons + federal).
- **PyPI package ownership validation.** The registry verifies ownership of a
  PyPI package by looking for an `mcp-name: <server-name>` marker in the
  published package README. It was missing, so the registry could not attribute
  the package to `io.github.malkreide/swiss-procurement-mcp`. Added as an HTML
  comment at the top of `README.md` (the package `long_description`), which
  keeps it invisible in the rendered README. Because PyPI releases are
  immutable, the marker can only reach PyPI via a new version — hence 0.3.1.

## [0.3.0] — 2026-07-26

Closes the last two open audit findings from the 0.2.0 hardening pass.

### Added

- **`search_procurements_detailed`** — aggregated tool that runs a search and
  fetches the full detail record for the top *n* hits in parallel
  (`asyncio.gather`), so the anchor query is answered in a single call instead of a
  search-then-N-details chain (ARCH-007). Bounded by `top_n` (1–5).
- `EnrichedSearchResponse` model (`count`, `total_matched`, `match_type`,
  `results: list[ProcurementDetail]`).

### Changed

- Attribution now states the data-reuse basis: the tenders are official
  public-procurement announcements and simap.ch publishes no explicit open-data
  licence, so reuse follows the simap.ch terms. Source/operator/terms are named in
  `ATTRIBUTION`, the README Credits and every response's `source` (CH-004).
- Refactored shared search-param building and detail mapping into `_build_search_params`
  and `_detail_from_payload` (used by both the single and aggregated tools).

## [0.2.0] — 2026-07-26

Audit-driven hardening following the `mcp-audit` run
(`audits/2026-07-26T131630-Z-swiss-procurement-mcp/`). No breaking change to
tool names or arguments; response models gain a `match_type` field.

### Added

- `match_type` (`exact` / `none`) on search, code and office responses (ARCH-003).
- Explicit egress allow-list: `ALLOWED_HOSTS` frozenset + `_assert_host_allowed`
  guard before every request, plus `docs/network-egress.md` (SEC-021).
- Input bounds at the tool boundary: `limit` restricted to 1–100 and free-text
  params length-capped (SEC-018), with tests.
- `openWorldHint` and `idempotentHint` on every tool via a shared `READ_TOOL`
  annotation (ARCH-009).
- `.github/workflows/security.yml` — gitleaks secret scan on push/PR (ARCH-005).
- `.github/dependabot.yml` — weekly pip + github-actions update PRs (ARCH-012).
- Tests for `get_publication_history`, `search_construction_codes` and
  `find_procurement_office`, previously uncovered (OPS-001).
- README "Maturity & updates" section (Phase 1 read-only, SDK-update policy)
  (OPS-003, ARCH-012); lethal-trifecta assessment in `SECURITY.md` (SEC-019).

### Changed

- The `degraded` envelope note is now a fixed, sanitised message and no longer
  embeds the raw exception or upstream response body (OBS-002).

## [0.1.0] — 2026-07-26

### Added

- Eight read-only tools over the simap.ch public procurement API (v1.5.1),
  covering all cantons and the Confederation.
- `search_procurements`, `search_awards`, `get_procurement_details`,
  `get_publication_history`, `search_cpv_codes`, `search_construction_codes`,
  `find_procurement_office`, `source_status`.
- Dual transport: stdio (Claude Desktop) and SSE / streamable-http (cloud).
- Pydantic v2 response envelope with `source`, `provenance`, `retrieved_at`.
- Retry with exponential backoff (2s / 4s / 8s); 4xx except 429 not retried.
- Graceful degradation instead of silent empty lists.

### Security

- HTTP transports (`MCP_TRANSPORT=sse|streamable-http`) bind to loopback
  (`127.0.0.1`) by default; exposing all interfaces now requires an explicit
  `MCP_HOST`/`HOST=0.0.0.0` opt-in (SEC-016). stdio (the default) does not bind.

### Known findings (live probe, 2026-07-26)

- **Read API lives under `www.simap.ch/api`**, not the `simap.ch/de` web UI.
  Probing the UI produced an earlier, mistaken "no API" conclusion. The search
  and detail endpoints are `security: None` and callable without authentication.
- **`lang` is mandatory** on project-search; omitting it is HTTP 400 (E0025),
  not an empty result. The client injects a default.
- **Award is not "award".** The value is split by procedure: `award_tender`,
  `award_study_contract`, `award_competition`, `direct_award`. `search_awards`
  queries all four.
- **Canton ids are bare** (`ZH`, not `CH-ZH`); an ISO code matches nothing and is
  rejected with a clear error.
- **Code fields are objects**, not strings: `cpvCode` and `bkpCodes` come back as
  `{code, label}`. Caught by a live test that a mocked fixture had missed —
  normalised centrally.
- **A session cookie is required**; a persistent HTTP client handles it.

### Scope

- Read-only. The ~200 write / OIDC-protected endpoints (publishing, submissions)
  are deliberately not wrapped.
