"""One version, one source.

A publish to the MCP registry failed with:

    PyPI package 'swiss-procurement-mcp' exists, but version '0.4.0' was not
    found (status: 404)

`server.json` carried its own hand-maintained copy of the version. It had
drifted to 0.4.0 while `pyproject.toml` moved on to 0.7.0, so PyPI received the
0.7.0 artifact and the registry went looking for a 0.4.0 release that had never
existed. The error message suggests a PyPI propagation delay, which is a
plausible-sounding wrong diagnosis — waiting and retrying would never have
fixed it.

The workflow now derives the version from `pyproject.toml`. This test is what
keeps the committed `server.json` honest in the meantime, so the drift is
visible in a PR rather than at publish time.
"""

from __future__ import annotations

import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    assert m, "no version in pyproject.toml"
    return m.group(1)


def _server_json() -> dict:
    return json.loads((REPO / "server.json").read_text(encoding="utf-8"))


def test_server_json_version_matches_pyproject() -> None:
    assert _server_json()["version"] == _pyproject_version()


def test_server_json_package_version_matches_pyproject() -> None:
    """The registry validates *this* field against PyPI, not the top-level one."""
    packages = _server_json()["packages"]
    assert packages, "server.json declares no packages"
    for pkg in packages:
        assert pkg["version"] == _pyproject_version(), (
            f"package {pkg.get('identifier')!r} pins {pkg['version']}, "
            f"pyproject says {_pyproject_version()}"
        )


def test_server_json_package_identifier_matches_project_name() -> None:
    """A mismatch here fails the same way, one line earlier in the validator."""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^name\s*=\s*"([^"]+)"', text, re.M)
    assert m, "no name in pyproject.toml"
    for pkg in _server_json()["packages"]:
        if pkg.get("registryType") == "pypi":
            assert pkg["identifier"] == m.group(1)
