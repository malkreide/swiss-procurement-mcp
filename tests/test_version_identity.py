"""The version this server announces must be the version it actually is.

Nothing in this repository asserted anything about the version before, and the
consequence was measurable: the published 0.18.3 announced itself to simap.ch
as `swiss-procurement-mcp/0.4.0` — fourteen minor versions stale, for months,
without a single test going red.

The literal that caused it sat under a comment promising it was "a single
source of truth for the version string, so the User-Agent cannot drift from the
packaged version again". It was not a source of truth; it was a second copy of
a number the build decides, and second copies drift. That is the failure these
tests are written against, so they check the property rather than the value:
no expected version number appears anywhere below.
"""

from __future__ import annotations

import re
from importlib.metadata import version as pkg_version
from pathlib import Path

import swiss_procurement_mcp
from swiss_procurement_mcp.constants import USER_AGENT, VERSION

SRC = Path(__file__).parent.parent / "src" / "swiss_procurement_mcp"


def test_version_comes_from_the_installed_distribution() -> None:
    """`VERSION` must equal what the package was installed as."""
    assert pkg_version("swiss-procurement-mcp") == VERSION


def test_dunder_version_reexports_the_same_value() -> None:
    assert swiss_procurement_mcp.__version__ == VERSION


def test_user_agent_carries_that_version() -> None:
    """This is the string simap.ch sees; it is the whole point."""
    assert USER_AGENT.startswith(f"swiss-procurement-mcp/{VERSION} ")


# Two shapes, because the drift has appeared in both. `VERSION = "0.4.0"` is
# the one that bit here; `"swiss-procurement-mcp/0.3.0"` is the one it bit
# before, recorded in the comment that the constant then replaced.
#
# Matching on shape alone does not work: this package is full of IP literals
# (`127.0.0.1`, `10.0.0.0/8`) that look exactly like version numbers. So the
# rule is semantic — a version-shaped literal assigned to a version-named
# constant, or one riding inside this package's own User-Agent token.
_VERSION_ASSIGNMENT = re.compile(
    r"""^\s*[A-Za-z_]*VERSION[A-Za-z_]*\s*(?::\s*[^=]+)?=\s*["'](\d+\.\d+[^"']*)["']""",
    re.IGNORECASE,
)
_UA_LITERAL = re.compile(r"""swiss-procurement-mcp/(\d+\.\d+[^\s"']*)""")


def test_no_version_literal_in_the_package() -> None:
    """A hand-written release number under src/ is the bug coming back.

    The fallback `0.0.0+source` is deliberately exempt and deliberately
    unmistakable: a PEP 440 local segment after `+` cannot be read as a
    release, unlike a plausible-looking bare `0.0.0`.
    """
    offenders: list[str] = []

    for path in sorted(SRC.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue  # prose about the incident is not the incident
            for pattern in (_VERSION_ASSIGNMENT, _UA_LITERAL):
                match = pattern.search(line)
                if match and "+" not in match.group(1):
                    offenders.append(f"{path.name}:{lineno}: {line.strip()}")

    assert not offenders, (
        "version literal(s) under src/ — read the version from the installed "
        "metadata instead:\n  " + "\n  ".join(offenders)
    )


def _flags(line: str) -> bool:
    """The decision the scan above makes, for one line."""
    if line.lstrip().startswith("#"):
        return False
    return any(
        (m := pattern.search(line)) is not None and "+" not in m.group(1)
        for pattern in (_VERSION_ASSIGNMENT, _UA_LITERAL)
    )


def test_that_scan_actually_catches_the_regression() -> None:
    """A check that can only pass proves nothing. These are the shapes that shipped."""
    assert _flags('VERSION = "0.4.0"')  # what 0.18.3 announced itself as
    assert _flags('_version: str = "1.2.3"')
    assert _flags('"swiss-procurement-mcp/0.3.0 (+https://example)"')  # the drift before it


def test_that_scan_does_not_fire_on_what_this_package_legitimately_contains() -> None:
    assert not _flags('    VERSION = "0.0.0+source"')  # the fallback marker
    assert not _flags('MCP_PROTOCOL_VERSION = "2026-07-28"')  # a date pin, not our version
    assert not _flags('    ipaddress.ip_network("10.0.0.0/8"),')  # a CIDR, not a version
    assert not _flags('return os.environ.get("MCP_HOST", "127.0.0.1")')  # an address
    assert not _flags("# it said 0.3.0 while the package was already 0.3.1")  # prose
