"""SECURITY.md must describe the server that exists, not an earlier one.

This file exists because the document had drifted badly and nobody noticed:
it cited 15/16/1 from the first audit — four runs stale — and listed container
sandboxing and structured logging as *accepted risks* long after both had been
implemented and had flipped to `pass`.

A stale acceptance is worse than a missing one. It reads as a considered
decision when it is really an out-of-date paragraph, and a reader auditing the
server would have concluded that neither control exists.
"""

from __future__ import annotations

import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
SECURITY = (REPO / "SECURITY.md").read_text(encoding="utf-8")


def _latest_audit_dir() -> pathlib.Path:
    runs = sorted(d for d in (REPO / "audits").iterdir() if d.is_dir())
    assert runs, "no audit runs on disk"
    return runs[-1]


def test_cites_the_latest_audit_run() -> None:
    """A posture section quoting an old run misstates the current posture."""
    latest = _latest_audit_dir().name
    assert latest in SECURITY, (
        f"SECURITY.md does not reference the latest run {latest}; "
        "update the posture summary when a new audit lands"
    )


# How much prose after the run citation counts as "the sentence that cites it".
# Generous enough for a wrapped sentence, tight enough that an unrelated
# paragraph elsewhere in the document cannot stand in for it.
_CITATION_WINDOW = 500


def test_quoted_counts_match_that_run() -> None:
    """All three counts, anchored to the sentence that names the run.

    Both details were found by porting this file to `amtsblatt-mcp`, where the
    original form of the assertion turned out to be hollow.

    A document-wide search lets any coincidental mention satisfy the check. Over
    there a *historical* sentence — "the estimate recorded at the time — ~32 pass
    / 8 partial / 6 fail" — did exactly that, and rewriting the actual posture
    line to a wrong number left the suite green. This repo does not currently
    quote its counts twice, so the hole was latent rather than active here; a
    guard that depends on prose not repeating a number is not a guard. The claim
    being asserted is that the summary states *this run's* numbers, so the
    numbers have to sit next to the run reference.

    `fail` is checked too. Leaving it out meant a posture section could quietly
    stop naming the two fails this server has while staying green — and the
    fails are the part a reader is most likely to be looking for.
    """
    latest = _latest_audit_dir()
    summary = json.loads((latest / "summary.json").read_text())
    by = summary["totals"]["by_status"]

    at = SECURITY.find(latest.name)
    assert at != -1, f"SECURITY.md does not reference {latest.name}"
    window = SECURITY[at : at + _CITATION_WINDOW]

    # `\s+` rather than a literal space: prose wraps, and the count and its
    # label legitimately end up on different lines.
    for label in ("pass", "partial", "fail"):
        assert re.search(rf"{by[label]}\s+{label}", window), (
            f"the passage citing {latest.name} does not state {by[label]} {label}"
        )


def test_does_not_accept_risks_that_are_closed() -> None:
    """The exact drift that prompted this file.

    Anything listed under "Accepted risks" must still be open in the latest
    audit. A check that has flipped to `pass` no longer belongs there.
    """
    results = json.loads((_latest_audit_dir() / "verification-results.json").read_text())["results"]
    section = SECURITY.split("## Accepted risks", 1)[1].split("\n## ", 1)[0]

    # Only look at the "### ... (CHECK-ID)" headings — prose may legitimately
    # mention a closed check to say it *was* closed.
    accepted = set(re.findall(r"^###.*\(([A-Z]+-\d+)\)", section, re.M))
    assert accepted, "no check ids found under Accepted risks — heading format changed?"

    wrongly_accepted = [
        cid for cid in accepted if cid in results and results[cid]["status"] == "pass"
    ]
    assert not wrongly_accepted, (
        f"listed as accepted risk but passing in the latest audit: {sorted(wrongly_accepted)}"
    )


def test_does_not_claim_absent_things_that_exist() -> None:
    """Concrete anti-staleness assertions for the two that actually drifted."""
    if (REPO / "Dockerfile").is_file():
        assert "No `Dockerfile` is shipped" not in SECURITY
    if "structlog" in (REPO / "pyproject.toml").read_text(encoding="utf-8"):
        assert "relies on the host's default logging" not in SECURITY
