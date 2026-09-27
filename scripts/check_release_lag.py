"""
Release-Rueckstand melden: Wie lange liegen ausgelieferte Aenderungen schon
unveroeffentlicht in `main`?

Anlass, gemessen am 27.9.2026: Zwischen dem Merge von #39 am 7.8.2026 und dem
Release 0.19.0 lagen 51 Tage. In dieser Zeit war `get_publication_history` fuer
jede losbasierte Beschaffung in der publizierten Version defekt, obwohl die
Korrektur laengst in `main` stand. Niemand hat es gesehen, weil nichts danach
fragte.

`check_release_drift.py` schliesst die Nachbarluecke — dieselbe Nummer fuer
zwei Codestaende — und ist nach dem ersten Versionssprung gruen, egal wie
lange das naechste Release dauert. Dieses Skript misst genau das, was jener
Check nicht sieht: die Dauer.

Gemessen wird:

  - **Bezug:** der neueste Versions-Tag (`vX.Y.Z`), der von HEAD aus
    erreichbar ist. Nicht der neueste ueberhaupt: ein Tag auf einem
    Seitenzweig beschreibt nicht, was in dieser Linie zuletzt ausgeliefert
    wurde.
  - **Was zaehlt:** dieselbe Flaeche wie in `check_release_drift.py` —
    `src/` und die Laufzeit-Abhaengigkeiten. Die Definition wird von dort
    importiert und nicht wiederholt, sonst driften zwei Kopien auseinander.
  - **Ab wann:** ab dem ersten Commit der First-Parent-Linie seit dem Tag, der
    diese Flaeche aendert. First-Parent heisst: der Merge in `main`, nicht der
    Commit auf dem Branch. Ein Branch-Commit kann Wochen aelter sein als der
    Moment, in dem seine Aenderung auslieferbar wurde.
  - **Netto:** Ist die Flaeche zwischen Tag und HEAD insgesamt unveraendert
    (etwa weil eine Aenderung zurueckgenommen wurde), gibt es keinen
    Rueckstand, egal was dazwischen geschah.

Die Schwelle von 14 Tagen ist eine Setzung, keine Messung. Aendern ueber
`RELEASE_LAG_DAYS`.

Ausgabe wie `classify_live_run.py`: `state` (`clear` / `finding` /
`unknown`) und `reason` auf stdout und in `$GITHUB_OUTPUT`, dazu mit
`--report` ein Markdown-Bericht fuer das Issue. Der Exit-Code ist immer 0 —
ueber rot oder gruen entscheidet der Workflow.

Verwendung:
    python scripts/check_release_lag.py [--report bericht.md]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_release_drift import SHIPPED_PATHS, _git, runtime_dependencies

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DAYS = 14
_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class Commit:
    sha: str
    datum: datetime
    betreff: str


@dataclass(frozen=True)
class Befund:
    state: str
    reason: str
    bericht: str = ""
    ausgeliefert: list[Commit] = field(default_factory=list)


def _neuester_tag(repo: Path) -> str | None:
    """Der hoechste `vX.Y.Z`-Tag, der von HEAD aus erreichbar ist.

    Numerisch sortiert: `v0.10.0` liegt ueber `v0.9.0`, auch wenn ein
    lexikalischer Vergleich es umgekehrt saehe.
    """
    tags = _git(repo, "tag", "--merged", "HEAD", "--list", "v*").stdout.split()
    versionen = [(tuple(int(x) for x in m.groups()), t) for t in tags if (m := _TAG.match(t))]
    return max(versionen)[1] if versionen else None


def _pyproject(repo: Path, ref: str) -> str:
    return _git(repo, "show", f"{ref}:pyproject.toml").stdout


def _aendert_auslieferung(repo: Path, vorher: str, nachher: str) -> bool:
    geaendert = _git(repo, "diff", "--name-only", vorher, nachher, "--", *SHIPPED_PATHS)
    if geaendert.stdout.strip():
        return True
    return runtime_dependencies(_pyproject(repo, vorher)) != runtime_dependencies(
        _pyproject(repo, nachher)
    )


def pruefe(repo: Path, jetzt: datetime, schwelle_tage: int = DEFAULT_DAYS) -> Befund:
    # Fuer das Ergebnis nicht noetig — ohne Historie findet `_neuester_tag`
    # keinen Tag, und das ist ebenfalls `unknown`. Die Pruefung liefert die
    # richtige Begruendung: «flacher Checkout» sagt, was zu aendern ist.
    if _git(repo, "rev-parse", "--is-shallow-repository").stdout.strip() != "false":
        return Befund(
            "unknown",
            "flacher Checkout oder kein Git-Repository: ohne Historie und Tags "
            "ist kein Rueckstand messbar (fetch-depth: 0 setzen)",
        )

    tag = _neuester_tag(repo)
    if tag is None:
        return Befund(
            "unknown",
            "kein vX.Y.Z-Tag von HEAD aus erreichbar: ohne Release gibt es "
            "keinen Bezugspunkt, und ein fehlender Tag sieht aus wie ein "
            "Checkout ohne Tags",
        )
    tag_commit = _git(repo, "rev-parse", f"{tag}^{{commit}}").stdout.strip()

    if not _aendert_auslieferung(repo, tag_commit, "HEAD"):
        return Befund("clear", f"seit {tag} ist nichts Ausgeliefertes veraendert")

    linie = _git(
        repo,
        "log",
        "--first-parent",
        "--reverse",
        "--format=%H%x00%cI%x00%s",
        f"{tag_commit}..HEAD",
    ).stdout.splitlines()
    ausgeliefert: list[Commit] = []
    for zeile in linie:
        sha, datum, betreff = zeile.split("\x00", 2)
        if _aendert_auslieferung(repo, f"{sha}^1", sha):
            ausgeliefert.append(Commit(sha, datetime.fromisoformat(datum), betreff))

    if not ausgeliefert:
        # Netto veraendert, aber kein einzelner First-Parent-Commit zeigt es —
        # das duerfte nicht vorkommen. Nicht als «kein Rueckstand» ausgeben.
        return Befund(
            "unknown",
            f"die Auslieferung weicht von {tag} ab, aber kein Commit der "
            "First-Parent-Linie aendert sie",
        )

    erster = ausgeliefert[0]
    tage = (jetzt - erster.datum).days
    kopf = (
        f"{len(ausgeliefert)} ausgelieferte Aenderung(en) seit {tag}, die erste "
        f"seit {tage} Tagen in main ({erster.sha[:7]}, {erster.datum.date()})"
    )
    bericht = _bericht(tag, tag_commit, ausgeliefert, jetzt, tage, schwelle_tage)
    if tage < schwelle_tage:
        return Befund("clear", f"{kopf}; Schwelle {schwelle_tage} Tage", bericht, ausgeliefert)
    return Befund("finding", f"{kopf}; Schwelle {schwelle_tage} Tage", bericht, ausgeliefert)


def _bericht(
    tag: str, tag_commit: str, commits: list[Commit], jetzt: datetime, tage: int, schwelle: int
) -> str:
    zeilen = [
        f"Seit **{tag}** (`{tag_commit[:7]}`) liegen ausgelieferte Aenderungen in "
        f"`main`, die noch in keinem Release stehen. Die erste ist seit **{tage} Tagen** "
        f"dort; die Schwelle ist {schwelle} Tage.",
        "",
        "Ausgeliefert heisst hier: `src/` oder die Laufzeit-Abhaengigkeiten in "
        "`pyproject.toml`. Gezaehlt wird ab dem Merge in `main`, nicht ab dem "
        "Branch-Commit.",
        "",
        "| Commit in main | seit | Betreff |",
        "|---|---|---|",
    ]
    for c in commits:
        # Betreff ist fremder Text: Pipes wuerden die Tabelle brechen.
        betreff = c.betreff.replace("|", "\\|")
        zeilen.append(f"| `{c.sha[:7]}` | {(jetzt - c.datum).days} Tage | {betreff} |")
    zeilen += [
        "",
        "Dieser Hinweis erzwingt kein Release. Er macht sichtbar, wie lange die "
        "publizierte Version hinter `main` zurueckliegt — vom 7.8. bis 27.9.2026 "
        "waren es 51 Tage, und in der publizierten Version war "
        "`get_publication_history` fuer losbasierte Beschaffungen die ganze Zeit "
        "defekt.",
    ]
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="check_release_lag")
    ap.add_argument("--report", type=Path, default=None, help="Markdown-Bericht hierhin")
    args = ap.parse_args(argv)

    try:
        schwelle = int(os.environ.get("RELEASE_LAG_DAYS", DEFAULT_DAYS))
    except ValueError:
        schwelle = DEFAULT_DAYS
    befund = pruefe(ROOT, datetime.now(timezone.utc), schwelle)

    print(f"state={befund.state}")
    print(f"reason={befund.reason}")
    if args.report is not None:
        args.report.write_text(befund.bericht, encoding="utf-8")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        # Wie in classify_live_run.py: Zeilenumbrueche raus, damit ein Grund
        # kein zweites `state=` nachschieben kann. Commit-Betreffe gehen
        # deshalb nur in den Bericht, nie in `$GITHUB_OUTPUT`.
        flat = " ".join(befund.reason.split())
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"state={befund.state}\n")
            fh.write(f"reason={flat}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
