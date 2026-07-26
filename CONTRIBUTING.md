# Contributing to swiss-procurement-mcp

[🇩🇪 Deutsche Version](CONTRIBUTING.de.md)

Thank you for your interest in contributing to `swiss-procurement-mcp`! This project is part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide).

---

## Ways to Contribute

### Report a Bug

Open a [GitHub Issue](https://github.com/malkreide/swiss-procurement-mcp/issues) and include:

- A clear description of the problem
- Steps to reproduce (ideally with the canton, CPV code or publication id involved)
- Expected vs. actual behaviour
- Python version and OS

### Suggest a New Endpoint or Field

The simap.ch read API exposes more reference data than this server currently
wraps. If you find a read endpoint that deserves a dedicated tool:

1. Open an issue with the title `[Endpoint] <path>: <short description>`
2. Include the endpoint path, a sample `www.simap.ch/api` call, and a description of the data it returns
3. Confirm it is marked `security: None` (unauthenticated) and verify it against the live API before submitting

> **Out of scope:** the ~200 write / `my/` / OIDC-protected endpoints (publishing
> tenders, submitting offers) are deliberately never wrapped. This server is
> read-only by design.

### Improve Documentation

Typos, unclear explanations, or missing examples are always welcome as pull requests — no issue needed.

### Contribute Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Follow the code style (Ruff for linting/formatting)
4. Add or update tests in `tests/`
5. Run the test suite before submitting: `PYTHONPATH=src pytest tests/ -m "not live"`
6. Submit a pull request with a clear description of your changes

---

## Development Setup

```bash
git clone https://github.com/malkreide/swiss-procurement-mcp.git
cd swiss-procurement-mcp
pip install -e ".[dev]"
```

**Run tests:**

```bash
# Unit tests (no network required, respx-mocked)
PYTHONPATH=src pytest tests/ -m "not live"

# Integration tests (live simap.ch API)
PYTHONPATH=src pytest tests/ -m "live"
```

**Lint and format:**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

---

## Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | When to use |
|---|---|
| `feat:` | New tool or new simap endpoint |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `test:` | Adding or updating tests |
| `refactor:` | Code restructuring without behaviour change |
| `chore:` | Build, dependencies, CI |

---

## Code of Conduct

Be respectful and constructive. This is a small open-source project maintained in spare time — patience is appreciated.

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
