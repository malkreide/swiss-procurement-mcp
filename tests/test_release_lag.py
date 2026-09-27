"""`scripts/check_release_lag.py` gegen synthetische Git-Repos mit gesetzten Daten.

Gegen die echte Historie ist das Skript im PR belegt, der es einfuehrt: auf
`ac66e63` mit Stichtag 26.9.2026 `finding` (49 Tage seit dem Merge von #39,
Bezug `v0.18.5`, obwohl `v0.19.0` existiert — von dort aus ist er nicht
erreichbar), mit Stichtag 21.8. noch `clear` (13 Tage).

Zu jeder Achse ein Paar, das sich nur in ihr unterscheidet.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_release_lag as crl

JETZT = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)

_CFG = (
    "-c", "user.name=test",
    "-c", "user.email=test@example.invalid",
    "-c", "commit.gpgsign=false",
    "-c", "tag.gpgsign=false",
    "-c", "init.defaultBranch=main",
)  # fmt: skip


def _git(repo: Path, *args: str, vor_tagen: float | None = None) -> str:
    env = dict(os.environ)
    if vor_tagen is not None:
        stempel = (JETZT - timedelta(days=vor_tagen)).isoformat()
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = stempel
    done = subprocess.run(
        ["git", *_CFG, *args], cwd=repo, capture_output=True, text=True, check=True, env=env
    )
    return done.stdout


def _pyproject(deps: str = '"httpx>=0.27"') -> str:
    return f'[project]\nname = "demo"\nversion = "1.0.0"\ndependencies = [\n    {deps},\n]\n'


def _commit(repo: Path, dateien: dict[str, str], vor_tagen: float, nachricht: str = "c") -> None:
    for name, inhalt in dateien.items():
        pfad = repo / name
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(inhalt, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", nachricht, vor_tagen=vor_tagen)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Release v1.0.0 vor 60 Tagen."""
    pfad = tmp_path / "repo"
    pfad.mkdir()
    _git(pfad, "init", "-q")
    _commit(pfad, {"pyproject.toml": _pyproject(), "src/a.py": "A = 1\n"}, 60, "release")
    _git(pfad, "tag", "v1.0.0")
    return pfad


# --- Kein Rueckstand ---------------------------------------------------------


def test_nichts_seit_dem_tag_ist_clear(repo: Path) -> None:
    assert crl.pruefe(repo, JETZT).state == "clear"


def test_alte_aenderungen_ausserhalb_der_auslieferung_zaehlen_nicht(repo: Path) -> None:
    _commit(repo, {"README.md": "x\n", "tests/t.py": "pass\n"}, 40)

    assert crl.pruefe(repo, JETZT).state == "clear"


# --- Das Alter und die Schwelle ------------------------------------------------


def test_eine_junge_aenderung_ist_clear_und_wird_trotzdem_genannt(repo: Path) -> None:
    _commit(repo, {"src/a.py": "A = 2\n"}, 3)

    befund = crl.pruefe(repo, JETZT)

    assert befund.state == "clear"
    assert "seit 3 Tagen" in befund.reason


def test_eine_alte_aenderung_ist_ein_befund(repo: Path) -> None:
    _commit(repo, {"src/a.py": "A = 2\n"}, 20)

    befund = crl.pruefe(repo, JETZT)

    assert befund.state == "finding"
    assert "seit 20 Tagen" in befund.reason


def test_der_merge_zeitpunkt_wird_sekundengenau_gelesen(repo: Path) -> None:
    """Der Zeitpunkt, nicht nur die Tageszahl.

    Die erste Fassung las `%cI` mit `datetime.fromisoformat` und fiel in der
    CI nur in einer Zelle: Python 3.10 kennt das `Z`, das Git 2.55 fuer UTC
    schreibt, nicht. Lokal (Git 2.43 schreibt `+00:00`) war das unsichtbar.
    Jetzt kommt ein Unix-Zeitstempel; dieser Test haelt fest, dass er ohne
    Zeitzonenverschiebung ankommt — ein Fehler um einige Stunden fiele beim
    Vergleich ganzer Tage nicht zuverlaessig auf.
    """
    _commit(repo, {"src/a.py": "A = 2\n"}, 20)

    (commit,) = crl.pruefe(repo, JETZT).ausgeliefert

    assert commit.datum == JETZT - timedelta(days=20)
    assert commit.datum.utcoffset() == timedelta(0)


@pytest.mark.parametrize(("tage", "erwartet"), [(13, "clear"), (14, "finding")])
def test_die_schwelle_gilt_ab_dem_vierzehnten_tag(repo: Path, tage: int, erwartet: str) -> None:
    _commit(repo, {"src/a.py": "A = 2\n"}, tage)

    assert crl.pruefe(repo, JETZT, schwelle_tage=14).state == erwartet


def test_eine_alte_abhaengigkeitsaenderung_ist_ein_befund(repo: Path) -> None:
    _commit(repo, {"pyproject.toml": _pyproject('"httpx>=0.28"')}, 20)

    assert crl.pruefe(repo, JETZT).state == "finding"


def test_das_alter_zaehlt_ab_der_ersten_aenderung_nicht_ab_der_letzten(repo: Path) -> None:
    _commit(repo, {"src/a.py": "A = 2\n"}, 20)
    _commit(repo, {"src/a.py": "A = 3\n"}, 1)

    befund = crl.pruefe(repo, JETZT)

    assert befund.state == "finding"
    assert "seit 20 Tagen" in befund.reason
    assert len(befund.ausgeliefert) == 2


def test_eine_zurueckgenommene_aenderung_hinterlaesst_keinen_rueckstand(repo: Path) -> None:
    _commit(repo, {"src/a.py": "A = 2\n"}, 20)
    _commit(repo, {"src/a.py": "A = 1\n"}, 1, "revert")

    assert crl.pruefe(repo, JETZT).state == "clear"


# --- First-Parent: der Merge zaehlt, nicht der Branch-Commit ------------------


def test_ein_alter_branch_commit_zaehlt_ab_seinem_merge(repo: Path) -> None:
    """Der Branch-Commit ist 30 Tage alt, in main steht er seit 2 Tagen."""
    _git(repo, "checkout", "-q", "-b", "feature")
    _commit(repo, {"src/a.py": "A = 2\n"}, 30, "alter Branch-Commit")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "-q", "--no-ff", "-m", "Merge feature", "feature", vor_tagen=2)

    befund = crl.pruefe(repo, JETZT)

    assert befund.state == "clear"
    assert "seit 2 Tagen" in befund.reason


# --- Welcher Tag der Bezug ist -------------------------------------------------


def test_der_hoechste_tag_zaehlt_numerisch_nicht_lexikalisch(tmp_path: Path) -> None:
    """`v0.10.0` liegt ueber `v0.9.0`. Lexikalisch waere es umgekehrt, und dann
    saehe das Skript eine 30 Tage alte Aenderung, die laengst ausgeliefert ist."""
    pfad = tmp_path / "numerisch"
    pfad.mkdir()
    _git(pfad, "init", "-q")
    _commit(pfad, {"pyproject.toml": _pyproject(), "src/a.py": "A = 1\n"}, 60)
    _git(pfad, "tag", "v0.9.0")
    _commit(pfad, {"src/a.py": "A = 2\n"}, 30)
    _git(pfad, "tag", "v0.10.0")

    assert crl._neuester_tag(pfad) == "v0.10.0"
    assert crl.pruefe(pfad, JETZT).state == "clear"


def test_ein_tag_auf_einem_seitenzweig_ist_kein_bezug(repo: Path) -> None:
    """Ein hoeherer Tag, der von HEAD aus nicht erreichbar ist, beschreibt nicht,
    was in dieser Linie ausgeliefert wurde — selbst wenn sein Inhalt zufaellig
    mit HEAD uebereinstimmt."""
    _git(repo, "checkout", "-q", "-b", "seite")
    _commit(repo, {"src/a.py": "A = 2\n"}, 25, "seitenzweig")
    _git(repo, "tag", "v2.0.0")
    _git(repo, "checkout", "-q", "main")
    _commit(repo, {"src/a.py": "A = 2\n"}, 20, "dieselbe Aenderung in main")

    assert crl._neuester_tag(repo) == "v1.0.0"
    assert crl.pruefe(repo, JETZT).state == "finding"


# --- unknown statt eines erfundenen Gruens ------------------------------------


def test_ein_flacher_checkout_ist_unknown_und_sagt_warum(repo: Path, tmp_path: Path) -> None:
    """Das Ergebnis haengt NICHT an der Flach-Pruefung, die Diagnose schon.

    Die erste Fassung dieses Tests pruefte nur `unknown` und blieb gruen, als
    die Flach-Pruefung entfernt wurde: Im flachen Klon fehlt der Tag, und der
    Zweig «kein Tag» liefert ebenfalls `unknown`. Das ist kein Zufall. Liegt
    der naechste Tag innerhalb der geholten Tiefe, ist alles zwischen ihm und
    HEAD vorhanden und die Messung stimmt; liegt er ausserhalb, gibt es keinen
    erreichbaren Tag. Einen dritten Fall gibt es nicht.

    Was die Pruefung beitraegt, ist die richtige Begruendung: «flacher
    Checkout» sagt, was im Workflow zu aendern ist; «kein Tag» schickt einen
    auf die Suche nach einem fehlenden Release.
    """
    _commit(repo, {"src/a.py": "A = 2\n"}, 20)
    klon = tmp_path / "flach"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{repo}", str(klon)],
        check=True,
        capture_output=True,
    )

    befund = crl.pruefe(klon, JETZT)

    assert befund.state == "unknown"
    assert "flacher Checkout" in befund.reason


def test_ohne_tag_ist_es_unknown_und_nicht_clear(tmp_path: Path) -> None:
    pfad = tmp_path / "ohne"
    pfad.mkdir()
    _git(pfad, "init", "-q")
    _commit(pfad, {"pyproject.toml": _pyproject(), "src/a.py": "A = 1\n"}, 60)

    assert crl.pruefe(pfad, JETZT).state == "unknown"


# --- Ausgabe --------------------------------------------------------------------


def test_github_output_traegt_genau_zwei_zeilen(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Commit-Betreffe sind fremder Text und gehoeren nur in den Bericht. In
    `$GITHUB_OUTPUT` koennte eine zweite Zeile ein `state=clear` nachschieben."""
    _commit(repo, {"src/a.py": "A = 2\n"}, 20, "fix: a|b state=clear")
    out = tmp_path / "gh_output"
    bericht = tmp_path / "bericht.md"
    monkeypatch.setattr(crl, "ROOT", repo)
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("RELEASE_LAG_DAYS", "14")

    assert crl.main(["--report", str(bericht)]) == 0

    zeilen = out.read_text(encoding="utf-8").splitlines()
    assert len(zeilen) == 2
    assert zeilen[0] == "state=finding"
    assert "state=clear" not in zeilen[1]
    assert "a\\|b" in bericht.read_text(encoding="utf-8")


def test_die_schwelle_kommt_aus_der_umgebung(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _commit(repo, {"src/a.py": "A = 2\n"}, 20)
    out = tmp_path / "gh_output"
    monkeypatch.setattr(crl, "ROOT", repo)
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("RELEASE_LAG_DAYS", "30")

    crl.main([])

    assert out.read_text(encoding="utf-8").splitlines()[0] == "state=clear"
