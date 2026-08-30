"""CLAUDE.md must not spell out the ruff version.

`scripts/check_ruff_pin.py` calls pyproject.toml "die einzige Quelle" in its
own docstring, and reads nothing else. So a version written into the prose is
not a convenience — it is a second source, and it drifts silently.

It did. The section was headed "ruff: eine Quelle" and named 0.16.3 while
pyproject.toml had moved to 0.16.4 in a merged Dependabot bump. No gate
noticed, because no gate reads the prose.

This test asserts the absence. Absence alone is cheap to satisfy by accident —
a repo with no ruff pin at all would pass — so it is paired with a positive
control that pyproject.toml really does carry one.
"""

from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]

# A three-part version near the word "ruff", on the same line. Dates in this
# document share the shape (`29.8.2026`), so the four-digit year is excluded
# rather than relying on distance from the keyword alone.
_RUFF_VERSION = re.compile(
    r"ruff[^\n]{0,40}?(?<!\d)(\d+\.\d+\.\d+)(?!\d)",
    re.IGNORECASE,
)
_DATE = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$")

# The pin as check_ruff_pin.py reads it: an exact `ruff==X.Y.Z` entry.
_PIN = re.compile(r"""['"]ruff==([0-9][^'"\s;]*)['"]""")


def _spelled_out_versions(text: str) -> list[str]:
    return [v for v in _RUFF_VERSION.findall(text) if not _DATE.match(v)]


def test_pyproject_still_carries_the_pin() -> None:
    """Positive control: without this, the absence test below measures nothing."""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert _PIN.findall(text), (
        "no exact ruff pin (ruff==X.Y.Z) in pyproject.toml — the absence test "
        "in this file would then pass on a repo that pins nothing at all"
    )


def test_claude_md_does_not_name_the_ruff_version() -> None:
    """A version in the prose is the second source the section warns against."""
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    found = _spelled_out_versions(text)
    assert not found, (
        f"CLAUDE.md spells out the ruff version {found}; point at "
        "pyproject.toml instead. A written-out version goes stale on the next "
        "Dependabot bump and no gate reads the prose"
    )


def test_the_guard_would_catch_a_reintroduced_version() -> None:
    """The counter-check, kept in the suite so it cannot rot unnoticed.

    Without it, a regex that matches nothing would satisfy the test above
    forever — the failure mode this whole file exists to prevent, one level up.
    """
    assert _spelled_out_versions("Der Pin ist `ruff==0.16.4`.") == ["0.16.4"]
    assert _spelled_out_versions("ruff 0.16.4 meldet sich so.") == ["0.16.4"]
    assert _spelled_out_versions("Am 29.8.2026 lief ruff durch.") == []
