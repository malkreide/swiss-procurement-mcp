"""
Release-Drift pruefen: Steht die deklarierte Version schon als Tag, darf sich
das ausgelieferte Artefakt seit diesem Tag nicht veraendert haben.

Anlass, gemessen am 27.9.2026: Der Tag `v0.18.5` zeigte auf einen Commit vom
2.8.2026. `main` trug danach 141 weitere Commits, davon 9 an `src/` mit
+516/-23 Zeilen, und deklarierte weiterhin 0.18.5. Dieselbe Versionsnummer
stand damit fuer zwei verschiedene Codestaende: den publizierten auf PyPI und
den in `main`.

`check_version_sync.py` blieb die ganze Zeit gruen. Er vergleicht die Kopien
der Nummer untereinander (pyproject, server.json, Badges) und war gruen,
*weil* niemand die Nummer angefasst hatte. Konsistenz der Kopien ist nicht
dasselbe wie Uebereinstimmung mit dem Artefakt.

Was als ausgeliefert zaehlt:

  - alles unter `src/` — das Paket selbst
  - die Laufzeit-Abhaengigkeiten, also der `dependencies`-Block unter
    `[project]`. 0.18.5 war ein Release, das nur eine Abhaengigkeitsgrenze
    aenderte; ohne diesen Teil saehe der Check genau diese Klasse nicht.
    Kommentarzeilen im Block zaehlen nicht, das `dev`-Extra ebenfalls nicht.

Nicht dazu zaehlen README, Tests, CI und `server.json`: Sie aendern das Paket
nicht, das ein `pip install` liefert.

**Fail-closed bei flachem Checkout.** `actions/checkout` holt ohne
`fetch-depth: 0` weder Tags noch Historie. Dann gaebe es keinen Tag zur
deklarierten Version, und der Check waere gruen, ohne etwas gesehen zu haben —
genau die Sorte Gruen, gegen die dieses Skript geschrieben ist. Ein flaches
Repo ist deshalb ein Fehler und kein Bestehen.

Nur Standardbibliothek; `git` muss im PATH liegen.

Verwendung:
    python scripts/check_release_drift.py     # exit 1 bei Drift
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Pfade, deren Aenderung das ausgelieferte Paket aendert.
SHIPPED_PATHS = ("src",)


@dataclass(frozen=True)
class Befund:
    ok: bool
    meldung: str


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)


def _project_section(pyproject: str) -> str:
    """Der Text der `[project]`-Tabelle, bis zur naechsten Tabellen-Ueberschrift."""
    match = re.search(r"^\[project\]\s*$(.*?)(?=^\[|\Z)", pyproject, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def declared_version(pyproject: str) -> str | None:
    """`version` unter `[project]`, ohne TOML-Parser — `tomllib` fehlt auf 3.10."""
    match = re.search(r'^version\s*=\s*"([^"]+)"', _project_section(pyproject), re.MULTILINE)
    return match.group(1) if match else None


def runtime_dependencies(pyproject: str) -> list[str]:
    """Die Eintraege des `dependencies`-Blocks unter `[project]`, ohne Kommentare.

    Zeilenweise bis zu einer Zeile, die nur `]` enthaelt. Eine Klammer in einem
    Kommentar beendet den Block deshalb nicht; Kommentare werden vor dem
    Vergleich entfernt, damit eine umformulierte Begruendung keinen Release
    erzwingt.
    """
    eintraege: list[str] = []
    im_block = False
    for zeile in _project_section(pyproject).splitlines():
        roh = zeile.strip()
        if not im_block:
            if re.match(r"^dependencies\s*=\s*\[\s*$", roh):
                im_block = True
            continue
        if roh == "]":
            break
        inhalt = roh.split("#", 1)[0].strip()
        if inhalt:
            eintraege.append(inhalt.rstrip(","))
    return eintraege


def pruefe(repo: Path) -> Befund:
    """Die Pruefung selbst, gegen die Git-Objekte von HEAD — nicht den Arbeitsbaum."""
    flach = _git(repo, "rev-parse", "--is-shallow-repository")
    if flach.returncode != 0:
        return Befund(False, f"kein Git-Repository unter {repo}: {flach.stderr.strip()}")
    if flach.stdout.strip() == "true":
        return Befund(
            False,
            "FLACHER CHECKOUT: Tags und Historie fehlen. Der Check saehe keinen Tag "
            "und waere gruen, ohne etwas geprueft zu haben. In der CI "
            "`fetch-depth: 0` am Checkout setzen.",
        )

    head_pyproject = _git(repo, "show", "HEAD:pyproject.toml")
    if head_pyproject.returncode != 0:
        return Befund(False, "pyproject.toml ist in HEAD nicht lesbar")
    version = declared_version(head_pyproject.stdout)
    if version is None:
        return Befund(False, "pyproject.toml deklariert unter [project] keine `version`")

    anzahl_tags = len(_git(repo, "tag", "--list").stdout.split())
    tag = f"v{version}"
    aufgeloest = _git(repo, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")
    if aufgeloest.returncode != 0:
        return Befund(
            True,
            f"Release-Drift OK: {version} ist noch nicht getaggt "
            f"(geprueft gegen {anzahl_tags} Tags).",
        )
    tag_commit = aufgeloest.stdout.strip()

    geaendert = _git(repo, "diff", "--name-only", tag_commit, "HEAD", "--", *SHIPPED_PATHS)
    dateien = [d for d in geaendert.stdout.splitlines() if d]

    tag_pyproject = _git(repo, "show", f"{tag_commit}:pyproject.toml").stdout
    deps_vorher = runtime_dependencies(tag_pyproject)
    deps_jetzt = runtime_dependencies(head_pyproject.stdout)

    if not dateien and deps_vorher == deps_jetzt:
        return Befund(
            True,
            f"Release-Drift OK: HEAD liefert dasselbe Artefakt wie {tag} ({tag_commit[:7]}).",
        )

    teile = [
        f"RELEASE-DRIFT: pyproject.toml deklariert {version}, und {tag} ist bereits "
        f"getaggt ({tag_commit[:7]}). Seither hat sich das ausgelieferte Artefakt "
        "geaendert — dieselbe Versionsnummer stuende fuer zwei Codestaende.",
    ]
    if dateien:
        teile.append(f"  geaendert unter {', '.join(SHIPPED_PATHS)}/: {len(dateien)} Datei(en)")
        teile.extend(f"    {d}" for d in dateien)
    if deps_vorher != deps_jetzt:
        teile.append(f"  Laufzeit-Abhaengigkeiten: {deps_vorher} -> {deps_jetzt}")
    teile.append(
        "Version in pyproject.toml und server.json auf die naechste, noch nicht "
        "getaggte anheben. Welche, entscheidet der Inhalt; dass es eine andere "
        "sein muss, entscheidet dieser Check."
    )
    return Befund(False, "\n".join(teile))


def main() -> None:
    befund = pruefe(ROOT)
    print(befund.meldung, file=sys.stdout if befund.ok else sys.stderr)
    sys.exit(0 if befund.ok else 1)


if __name__ == "__main__":
    main()
