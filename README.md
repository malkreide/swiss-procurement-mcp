> **Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide/swiss-public-data-mcp)** — open-source MCP servers connecting AI agents to Swiss public and open data.
>
> This is a **private project**. It is independent of any employer or institutional affiliation and represents no official position of any authority.

# swiss-procurement-mcp

[![CI](https://github.com/malkreide/swiss-procurement-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/malkreide/swiss-procurement-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/swiss-procurement-mcp)](https://pypi.org/project/swiss-procurement-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/swiss-procurement-mcp)](https://pypi.org/project/swiss-procurement-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-orange.svg)](https://modelcontextprotocol.io/)
[![Portfolio](https://img.shields.io/badge/portfolio-swiss--public--data--mcp-blue)](https://github.com/malkreide/swiss-public-data-mcp)
[![Deutsch](https://img.shields.io/badge/Doku-Deutsch-red.svg)](README.de.md)

MCP server for **Swiss public procurement** — read access to the official simap.ch API, covering all cantons and the Confederation, updated intraday.

---

## 🎯 Anchor demo query

> *«Which school-building tenders did the City of Zurich publish in 2026, which BKP construction categories do they concern, and who are the procuring offices?»*

This chains `search_procurements`, `search_construction_codes` and
`get_procurement_details`, and connects procurement to school-building planning
via the BKP construction codes.

---

## Why this server exists

Swiss public procurement is published on simap.ch. The platform's web UI is
searchable by hand, but the [`amtsblatt-mcp`](https://github.com/malkreide/amtsblatt-mcp)
server only reaches the three cantons (AR, BS, TI) that still mirror tenders to
the Amtsblattportal — Zurich among the missing.

simap closes that gap: it operates a documented **OpenAPI 3 read API (v1.5.1)**
whose search and detail endpoints are marked `security: None` and are callable
**without authentication**. This server wraps exactly those read endpoints.

> **Mnemonic:** *The web UI is the front door; the API is the loading dock. Probe the dock.*

---

## Architecture decision

**Architecture A (live API only, short-lived cache).**

- The public search, detail and reference endpoints are unauthenticated and were
  confirmed working live (2026-07-26).
- Publications change intraday, so the cache TTL is deliberately short (30 min).
- The ~200 write / `my/` / OIDC-protected endpoints (publishing tenders,
  submitting offers) are **out of scope** — this server never writes.

Every response carries `source` and `provenance` (`live_api` / `cached` /
`degraded`). Upstream failure yields a `degraded` envelope, never a silent empty
list.

---

## Live-probe findings (2026-07-26)

| Endpoint | Auth | Result |
|---|---|---|
| `/publications/v2/project/project-search` | none | 20 hits, canton filter, current-day |
| `/publications/v1/.../publication-details/...` | none | full record: criteria, deadlines, codes |
| `/publications/v1/publication/{id}/past-publications` | none | project lifecycle |
| `/codes/v1/cpv/search` | none | CPV full-text search |
| `/codes/v1/{bkp,npk,ebkp-h,ebkp-t,oag,cpc}/search` | none | Swiss construction codes |
| `/procoffices/v1/po/public` | none | ~1 MB office list (client-side filter) |
| `/cantons/v1`, `/countries/v1` | none | reference data |

### Known findings

1. **Wrong host, wrong conclusion.** The read API lives under `www.simap.ch/api`.
   The `simap.ch/de` web UI is a separate SSR app that exposes none of it —
   probing the UI produced an earlier, mistaken "no API" verdict.
2. **`lang` is mandatory** on project-search. Omitting it is HTTP 400
   (errorCode `E0025`), not an empty result. The client injects a default.
3. **Award is not "award".** `newestPubTypes=award` returns HTTP 400. Awards are
   split by procedure: `award_tender`, `award_study_contract`,
   `award_competition`, `direct_award`. The `search_awards` tool queries all four.
4. **Canton ids are bare.** `ZH`, not `CH-ZH`. Passing an ISO subdivision code
   silently matches nothing; this server rejects it with a clear error.
5. **A session cookie is required.** The first request sets it; a persistent
   HTTP client handles this transparently.

---

## Tools

| Tool | Purpose |
|---|---|
| `search_procurements` | Search publications by canton, CPV, process type, date, text |
| `search_awards` | Awarded contracts only (all four award types at once) |
| `get_procurement_details` | Full record for one publication |
| `get_publication_history` | Earlier publications of the same project (tender → award) |
| `search_cpv_codes` | Resolve keywords to CPV classification codes |
| `search_construction_codes` | Swiss construction codes (BKP, NPK, eBKP, OAG, CPC) |
| `find_procurement_office` | Public procurement offices by partial name |
| `source_status` | Reachability and latency of the simap.ch API |

All tools are `readOnlyHint: true`.

---

## Portfolio connections

- A vendor's UID links to [`register-mcp`](https://github.com/malkreide/register-mcp).
- BKP / eBKP construction codes on a tender connect procurement to school-building
  planning and to [`zh-education-mcp`](https://github.com/malkreide/zh-education-mcp).
- Complements [`amtsblatt-mcp`](https://github.com/malkreide/amtsblatt-mcp) with
  national coverage instead of three cantons.

---

## Installation

```bash
uvx swiss-procurement-mcp
```

### Claude Desktop

```json
{
  "mcpServers": {
    "swiss-procurement": {
      "command": "uvx",
      "args": ["swiss-procurement-mcp"]
    }
  }
}
```

### Cloud (Render / Railway)

```bash
MCP_TRANSPORT=sse HOST=0.0.0.0 PORT=8000 python -m swiss_procurement_mcp
```

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio` \| `sse` \| `streamable-http` |
| `MCP_HOST` / `HOST` | `127.0.0.1` | HTTP binding (cloud transports only). Defaults to loopback; set `0.0.0.0` explicitly to expose all interfaces in a cloud deployment. |
| `PORT` / `MCP_PORT` | `8000` | HTTP port (cloud transports only) |

No API keys — the wrapped simap.ch read endpoints are fully public.

---

## Testing

```bash
PYTHONPATH=src pytest tests/ -m "not live"   # offline, respx-mocked
PYTHONPATH=src pytest tests/ -m live         # hits the real API
```

See [EXAMPLES.md](EXAMPLES.md) for use cases grouped by audience (schools,
public, administration, developers) and a tool-selection reference table.

---

## Known limitations

- **Read-only by design.** Publishing and submission endpoints exist in the
  simap API but are deliberately not wrapped.
- **Award coverage is uneven** across cantons; some publish awards diligently,
  others rarely. Absence of an award is not proof none happened.
- **No contract values in search results.** Amounts, where published, live in the
  detail record's statistics section, which varies by procedure.
- **Unofficial client.** Publications remain authoritative on simap.ch itself.

---

## Project structure

```
swiss-procurement-mcp/
├── src/swiss_procurement_mcp/
│   ├── server.py      # FastMCP tools (8, read-only)
│   ├── client.py      # simap.ch HTTP client + retry + normalisation
│   ├── constants.py   # probe-derived lookup tables (cantons, pub types, codes)
│   ├── models.py      # Pydantic v2 envelopes (source + provenance)
│   └── __main__.py    # Dual-transport entry point (stdio / SSE / streamable-http)
├── tests/             # respx-mocked + @pytest.mark.live
└── .github/workflows/ # CI + OIDC PyPI/MCP-registry publish
```

---

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for how to
report bugs, suggest a new endpoint, or submit code.

## Security

This is a read-only, no-PII, public-open-data server. Audited against the
portfolio MCP best-practice catalogue (**15 pass / 16 partial / 1 fail** across
32 applicable checks, production-ready). See [SECURITY.md](SECURITY.md) for the
posture and how to report a vulnerability, and [`audits/`](audits/) for the full
report.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## Credits

- Data: [simap.ch](https://www.simap.ch) read API v1.5.1, operated by the simap.ch association. API docs: [simap.ch/api-doc](https://www.simap.ch/api-doc), guides: [kissimap.ch](https://www.kissimap.ch/de/anleitungen).
- Built following the `mcp-data-source-probe` methodology.

MIT licensed. Public money, public code.
