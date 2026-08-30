"""CLAUDE.md must not spell out a pinned version.

`scripts/check_ruff_pin.py` calls pyproject.toml "die einzige Quelle" in its
own docstring, and reads nothing else. So a version written into the prose is
not a convenience — it is a second source, and it drifts silently.

It did. The section was headed "ruff: eine Quelle" and named 0.16.3 while
pyproject.toml had moved on in a merged Dependabot bump. No gate noticed,
because no gate reads the prose.

The assertion is deliberately wider than ruff. An earlier version of this file
looked for a version *near the word* "ruff", and a Codex review on #75 showed
what that buys: the window was one-directional and line-bound, so "`0.16.5` is
the ruff pin", a sentence longer than the window, and a `ruff==` broken across
a line all passed. Every window is a number someone has to guess right.

There is no window here. Measured on this document, all ten three-part numbers
in it are dates; not one is a version. So a non-date three-part number is by
itself the thing worth stopping — whether it names ruff or some other pin, it
is the same second source. That also makes the date filter load-bearing rather
than decorative: without it, every date in the file would trip the assertion.
"""

from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]

# Any three-part number, wherever it stands and whatever precedes it.
_VERSION = re.compile(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)")

# German day.month.year shares that shape (`29.8.2026`) and is legitimate
# prose. The four-digit final part is what separates the two.
_DATE = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$")

# The pin as check_ruff_pin.py reads it: an exact `ruff==X.Y.Z` entry.
_PIN = re.compile(r"""['"]ruff==([0-9][^'"\s;]*)['"]""")


def _spelled_out_versions(text: str) -> list[str]:
    return [v for v in _VERSION.findall(text) if not _DATE.match(v)]


def test_pyproject_still_carries_the_pin() -> None:
    """Positive control: without this, the absence test below measures nothing."""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert _PIN.findall(text), (
        "no exact ruff pin (ruff==X.Y.Z) in pyproject.toml — the absence test "
        "in this file would then pass on a repo that pins nothing at all"
    )


def test_claude_md_does_not_name_a_pinned_version() -> None:
    """A version in the prose is the second source the section warns against."""
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    found = _spelled_out_versions(text)
    assert not found, (
        f"CLAUDE.md spells out the version(s) {found}; point at the file that "
        "pins them instead — pyproject.toml for ruff. A written-out version "
        "goes stale on the next Dependabot bump and no gate reads the prose"
    )


def test_the_guard_catches_a_version_in_any_position() -> None:
    """The counter-check, kept in the suite so it cannot rot unnoticed.

    Without it, a detector that matches nothing would satisfy the test above
    forever — the failure mode this whole file exists to prevent, one level up.

    The first three cases are the ones the previous, window-based detector let
    through. `9.9.9` is used throughout rather than a real ruff release, so
    that this file does not itself become the second source it forbids.
    """
    assert _spelled_out_versions("`9.9.9` is the ruff pin.") == ["9.9.9"]
    assert _spelled_out_versions("Der Pin lautet `ruff==\n9.9.9`.") == ["9.9.9"]
    assert _spelled_out_versions(
        "ruff wird an genau einer Stelle gepinnt, naemlich auf 9.9.9."
    ) == ["9.9.9"]
    assert _spelled_out_versions("Der Pin ist `ruff==9.9.9`.") == ["9.9.9"]


def test_the_date_filter_is_what_spares_dates() -> None:
    """Dates must survive — and be *filtered*, not merely missed.

    The earlier form asserted only that a date produced no finding. It did,
    but for the wrong reason: the detector never matched the date in the first
    place, so `_DATE` was never consulted and could have been deleted with the
    suite staying green. Asserting the raw match first pins down which of the
    two mechanisms is doing the work.
    """
    sentence = "Am 29.8.2026 lief ruff durch."
    assert _VERSION.findall(sentence) == ["29.8.2026"]
    assert _spelled_out_versions(sentence) == []
