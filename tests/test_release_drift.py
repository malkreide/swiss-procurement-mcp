"""`scripts/check_release_drift.py` gegen synthetische Git-Repos.

Synthetisch, weil der Checkout der Test-Matrix flach ist: ein Test gegen die
Historie dieses Repos saehe dort keinen einzigen Tag. Gegen die echte Historie
ist der Check im PR belegt, der ihn einfuehrt — rot auf `ac66e63` (deklariert
0.18.5, fuenf geaenderte Dateien seit `v0.18.5`), gruen auf `4d06a1d` und auf
`26259be`.

Jeder Fall prueft genau eine Achse, und zu jedem roten Fall gehoert ein gruener
daneben, der sich nur in dieser Achse unterscheidet. Ein Check, der immer rot
ist, bestaende sonst dieselben Tests wie einer, der richtig misst.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_release_drift as crd

_GIT_ENV_ARGS = (
    "-c", "user.name=test",
    "-c", "user.email=test@example.invalid",
    "-c", "commit.gpgsign=false",
    "-c", "tag.gpgsign=false",
    "-c", "init.defaultBranch=main",
)  # fmt: skip


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *_GIT_ENV_ARGS, *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return done.stdout


def _pyproject(
    version: str, deps: tuple[str, ...] = ('"httpx>=0.27"',), kommentar: str = ""
) -> str:
    zeilen = "\n".join(f"    {d}," for d in deps)
    return (
        "[project]\n"
        'name = "demo"\n'
        f'version = "{version}"\n'
        "dependencies = [\n"
        f"    # {kommentar or 'Begruendung'}\n"
        f"{zeilen}\n"
        "]\n\n"
        "[project.optional-dependencies]\n"
        'dev = ["ruff==0.1.0"]\n'
    )


def _commit(repo: Path, dateien: dict[str, str], nachricht: str) -> None:
    for name, inhalt in dateien.items():
        pfad = repo / name
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(inhalt, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", nachricht)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Ein Repo mit einem Release: 1.0.0, getaggt als v1.0.0."""
    pfad = tmp_path / "repo"
    pfad.mkdir()
    _git(pfad, "init", "-q")
    _commit(
        pfad,
        {"pyproject.toml": _pyproject("1.0.0"), "src/demo/core.py": "X = 1\n", "README.md": "a\n"},
        "release 1.0.0",
    )
    _git(pfad, "tag", "v1.0.0")
    return pfad


# --- Der Fall, der passiert ist, und sein Gegenstueck ------------------------


def test_geaenderter_code_unter_derselben_version_ist_rot(repo: Path) -> None:
    """Die gemessene Drift: Code aendert sich, die Nummer bleibt."""
    _commit(repo, {"src/demo/core.py": "X = 2\n"}, "fix")

    befund = crd.pruefe(repo)

    assert not befund.ok
    assert "RELEASE-DRIFT" in befund.meldung
    assert "src/demo/core.py" in befund.meldung


def test_derselbe_code_mit_angehobener_version_ist_gruen(repo: Path) -> None:
    """Dieselbe Aenderung, nur mit neuer Nummer — der Ausweg, den die Meldung nennt."""
    _commit(repo, {"src/demo/core.py": "X = 2\n", "pyproject.toml": _pyproject("1.0.1")}, "fix")

    assert crd.pruefe(repo).ok


def test_der_getaggte_commit_selbst_ist_gruen(repo: Path) -> None:
    assert crd.pruefe(repo).ok


def test_ein_neuer_file_unter_src_zaehlt(repo: Path) -> None:
    _commit(repo, {"src/demo/neu.py": "Y = 1\n"}, "neues Modul")

    assert not crd.pruefe(repo).ok


# --- Was NICHT als Auslieferung zaehlt ---------------------------------------


def test_readme_und_tests_erzwingen_keinen_release(repo: Path) -> None:
    _commit(repo, {"README.md": "b\n", "tests/test_x.py": "def test(): pass\n"}, "docs")

    assert crd.pruefe(repo).ok


def test_das_dev_extra_erzwingt_keinen_release(repo: Path) -> None:
    """Ein Dependabot-Bump des ruff-Pins aendert das Paket nicht."""
    text = _pyproject("1.0.0").replace("ruff==0.1.0", "ruff==0.2.0")
    _commit(repo, {"pyproject.toml": text}, "ruff bump")

    assert crd.pruefe(repo).ok


def test_ein_umformulierter_kommentar_im_abhaengigkeitsblock_zaehlt_nicht(repo: Path) -> None:
    _commit(repo, {"pyproject.toml": _pyproject("1.0.0", kommentar="neue Begruendung")}, "doc")

    assert crd.pruefe(repo).ok


# --- Laufzeit-Abhaengigkeiten: 0.18.5 war genau so ein Release --------------


def test_eine_geaenderte_laufzeit_abhaengigkeit_ist_rot(repo: Path) -> None:
    _commit(repo, {"pyproject.toml": _pyproject("1.0.0", deps=('"httpx>=0.28"',))}, "deps")

    befund = crd.pruefe(repo)

    assert not befund.ok
    assert "Laufzeit-Abhaengigkeiten" in befund.meldung


def test_eine_neue_laufzeit_abhaengigkeit_ist_rot(repo: Path) -> None:
    deps = ('"httpx>=0.27"', '"structlog>=24.1"')
    _commit(repo, {"pyproject.toml": _pyproject("1.0.0", deps=deps)}, "deps")

    assert not crd.pruefe(repo).ok


# --- Fail-closed --------------------------------------------------------------


def test_ein_flacher_checkout_ist_rot_und_nicht_gruen(repo: Path, tmp_path: Path) -> None:
    """Das Gruen, gegen das der Check geschrieben ist.

    Im flachen Klon fehlt der Tag. Ohne diesen Zweig hiesse das «noch nicht
    getaggt» und waere gruen — obwohl der Code seit dem Release veraendert ist.
    """
    _commit(repo, {"src/demo/core.py": "X = 2\n"}, "fix")
    klon = tmp_path / "flach"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{repo}", str(klon)],
        check=True,
        capture_output=True,
    )

    befund = crd.pruefe(klon)

    assert not befund.ok
    assert "FLACHER CHECKOUT" in befund.meldung


def test_eine_noch_nicht_getaggte_version_ist_gruen_und_nennt_die_tags(repo: Path) -> None:
    """Die Erfolgsmeldung zaehlt die gesehenen Tags — ein Gruen mit null Tags
    sieht im Log anders aus als eines mit zwanzig."""
    _commit(repo, {"pyproject.toml": _pyproject("2.0.0"), "src/demo/core.py": "X = 3\n"}, "2.0")

    befund = crd.pruefe(repo)

    assert befund.ok
    assert "1 Tags" in befund.meldung


def test_ein_annotierter_tag_nennt_den_commit_und_nicht_das_tag_objekt(tmp_path: Path) -> None:
    """`git tag -a` erzeugt ein Tag-Objekt mit eigener SHA.

    Der Befund selbst haengt NICHT an `^{commit}`: `git diff` und `git show`
    loesen ein Tag-Objekt auch ohne das Suffix auf. Die erste Fassung dieses
    Tests behauptete das Gegenteil und blieb gruen, als das Suffix entfernt
    wurde — sie pruefte den Befund und schrieb den Mechanismus dazu.

    Woran `^{commit}` tatsaechlich haengt, ist die Meldung: ohne das Suffix
    nennt sie die SHA des Tag-Objekts, die in keinem `git log` auftaucht.
    """
    pfad = tmp_path / "annotiert"
    pfad.mkdir()
    _git(pfad, "init", "-q")
    _commit(pfad, {"pyproject.toml": _pyproject("1.0.0"), "src/a.py": "A = 1\n"}, "r")
    _git(pfad, "tag", "-a", "v1.0.0", "-m", "release")
    commit_sha = _git(pfad, "rev-parse", "HEAD").strip()
    tag_objekt_sha = _git(pfad, "rev-parse", "v1.0.0").strip()
    assert commit_sha != tag_objekt_sha  # sonst prueft der Test nichts
    _commit(pfad, {"src/a.py": "A = 2\n"}, "fix")

    befund = crd.pruefe(pfad)

    assert not befund.ok
    assert f"({commit_sha[:7]})" in befund.meldung
    assert tag_objekt_sha[:7] not in befund.meldung


# --- Die Parser, einzeln ------------------------------------------------------


def test_die_version_kommt_aus_der_project_tabelle() -> None:
    text = '[tool.x]\nversion = "9.9.9"\n\n' + _pyproject("1.2.3")
    assert crd.declared_version(text) == "1.2.3"


def test_eine_klammer_im_kommentar_beendet_den_block_nicht() -> None:
    text = _pyproject("1.0.0", kommentar="siehe [PEP 508]")
    assert crd.runtime_dependencies(text) == ['"httpx>=0.27"']


def test_der_echte_abhaengigkeitsblock_wird_vollstaendig_gelesen() -> None:
    """Gegen die pyproject.toml dieses Repos: sechs Laufzeit-Abhaengigkeiten,
    die Kommentarzeilen dazwischen nicht mitgezaehlt."""
    text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    deps = crd.runtime_dependencies(text)

    namen = [d.strip('"').split(">")[0].split("<")[0].split("=")[0] for d in deps]
    assert namen == ["mcp", "httpx", "pydantic", "structlog", "starlette", "uvicorn"]
