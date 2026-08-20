"""Tests fuer .claude/hooks/session-start-staleness.sh — die Klon-Aktualitaet.

Der Hook meldet beim Sessionstart, wie viele Commits der ausgecheckte Stand
hinter `origin/<Default-Branch>` liegt. Er existiert, weil ein veralteter Klon
am 3.8.2026 zweimal eine rote CI erzeugt hat, deren Ursache nicht im Diff
stand: die fehlenden Commits waren jeweils genau die, die das Gate einfuehrten,
an dem der Branch scheiterte.

Seine erste Zusicherung ist nicht "meldet richtig", sondern "blockiert nie".
Deshalb pruefen die meisten Faelle hier ein Schweigen mit Exit 0 — und zwei
pruefen eine Zeitspanne, weil ein Deckel, den niemand misst, eine Behauptung
ist. Die beiden `..._wird_abgeschnitten` lassen den Remote 30 Sekunden haengen
und bestehen nur, wenn der Hook lange vorher zurueck ist.

Gegenprobe (was faellt, wenn man die Zusicherung entfernt):

  * `exit 0` am Ende bzw. die `|| exit 0`-Wachen  -> kein_remote, toter_remote,
    kein_git_repo, haengendes_* schlagen fehl (Exit != 0).
  * das `0) exit 0` im `case`                     -> aktueller_klon schlaegt
    fehl (Ausgabe statt Schweigen).
  * die Ermittlung des Default-Branchs, ersetzt   -> master_wird_erkannt
    durch ein festverdrahtetes "main"                schlaegt fehl.
  * der `run_capped`-Deckel                       -> haengendes_ls_remote und
                                                     haengendes_fetch laufen in
                                                     die 30 Sekunden.
  * der Rueckfall auf den zuletzt bekannten Stand -> fetch_kaputt_meldet_
                                                     untergrenze schweigt.

Alle Repositories sind lokal, kein Test geht ins Netz.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "session-start-staleness.sh"

# Eine Identitaet fuer die Wegwerf-Repos: ohne sie scheitert `git commit` auf
# einem Rechner ohne globale Konfiguration, und der Test waere rot aus einem
# Grund, der nichts mit dem Hook zu tun hat.
GIT_ENV = {
    "GIT_AUTHOR_NAME": "hook test",
    "GIT_AUTHOR_EMAIL": "hook@example.invalid",
    "GIT_COMMITTER_NAME": "hook test",
    "GIT_COMMITTER_EMAIL": "hook@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def git(cwd: Path, *args: str) -> str:
    """Ein git-Aufruf, der bei Fehlschlag den Test mit der Meldung abbricht."""
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env={**os.environ, **GIT_ENV},
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} -> {proc.returncode}\n{proc.stderr}")
    return proc.stdout


def commit(repo: Path, message: str) -> None:
    (repo / "datei.txt").write_text(message + "\n", encoding="utf-8")
    git(repo, "add", "datei.txt")
    git(repo, "commit", "-m", message)


def make_origin(tmp_path: Path, branch: str = "main", commits: int = 1) -> Path:
    """Ein bares Repo als Remote, bespielt aus einem Arbeits-Klon daneben.

    Bar, weil der Hook dem HEAD des Remotes folgt: in einem nicht-baren Repo
    zeigt der auf den dort ausgecheckten Branch, und die Fixture wuerde einen
    Default-Branch behaupten, den niemand so nennt.
    """
    origin = tmp_path / "origin"
    git(tmp_path, "init", "--bare", "--quiet", "--initial-branch", branch, str(origin))
    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "-c", f"init.defaultBranch={branch}", "init", "--quiet")
    git(seed, "remote", "add", "origin", str(origin))
    for i in range(commits):
        commit(seed, f"origin {i}")
    git(seed, "push", "--quiet", "origin", f"HEAD:refs/heads/{branch}")
    return origin


def clone(tmp_path: Path, origin: Path, name: str = "klon") -> Path:
    target = tmp_path / name
    git(tmp_path, "clone", "--quiet", str(origin), str(target))
    return target


def advance_origin(origin: Path, branch: str, n: int) -> None:
    seed = origin.parent / "seed"
    for i in range(n):
        commit(seed, f"neu {i}")
    git(seed, "push", "--quiet", "origin", f"HEAD:refs/heads/{branch}")


def run_hook(cwd: Path, timeout_s: str = "5", **extra_env: str) -> subprocess.CompletedProcess:
    env = {**os.environ, **GIT_ENV, "CLAUDE_STALENESS_FETCH_TIMEOUT": timeout_s, **extra_env}
    return subprocess.run(
        ["bash", str(HOOK)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        # Grosszuegig, aber endlich: ein Hook, der hier in den Timeout laeuft,
        # haette die Session angehalten. Der Fehler ist dann dieser Timeout.
        timeout=60,
    )


pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git nicht vorhanden")


def test_hook_ist_ausfuehrbar_und_registriert() -> None:
    """Ein Skript ohne x-Bit und ohne Eintrag laeuft nie — und faellt nie auf."""
    import json

    assert HOOK.exists(), f"{HOOK} fehlt"
    assert os.access(HOOK, os.X_OK), f"{HOOK} ist nicht ausfuehrbar"
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = [
        entry["command"]
        for matcher in settings["hooks"]["SessionStart"]
        for entry in matcher["hooks"]
    ]
    assert any(HOOK.name in c for c in commands), (
        f"{HOOK.name} steht in keinem SessionStart-Eintrag"
    )


def test_aktueller_klon_schweigt(tmp_path: Path) -> None:
    """Bei 0 fehlenden Commits keine Ausgabe — sonst liest sie nach einer Woche niemand."""
    origin = make_origin(tmp_path)
    klon = clone(tmp_path, origin)

    result = run_hook(klon)

    assert result.returncode == 0
    assert result.stdout == "", f"unerwartete Ausgabe: {result.stdout!r}"


def test_zurueckliegender_klon_meldet_die_zahl(tmp_path: Path) -> None:
    origin = make_origin(tmp_path)
    klon = clone(tmp_path, origin)
    advance_origin(origin, "main", 3)

    result = run_hook(klon)

    assert result.returncode == 0
    assert "3" in result.stdout
    assert "origin/main" in result.stdout


def test_master_wird_erkannt_nicht_main_angenommen(tmp_path: Path) -> None:
    """Drei Repos im Portfolio heissen ihren Default-Branch `master`.

    Genau die Annahme `main` hat einen Branch 15 Commits alt werden lassen:
    `git fetch origin main` scheitert dort mit "couldn't find remote ref main",
    was wie ein Netzproblem aussieht und weggeklickt wird.
    """
    origin = make_origin(tmp_path, branch="master")
    klon = clone(tmp_path, origin)
    advance_origin(origin, "master", 2)

    result = run_hook(klon)

    assert result.returncode == 0
    assert "origin/master" in result.stdout
    assert "2" in result.stdout


def test_detached_head_geht_durch(tmp_path: Path) -> None:
    """Detached HEAD ist ein Arbeitszustand, kein Fehler — und blockiert nichts."""
    origin = make_origin(tmp_path, commits=2)
    klon = clone(tmp_path, origin)
    advance_origin(origin, "main", 1)
    git(klon, "checkout", "--quiet", "--detach", "HEAD~1")

    result = run_hook(klon)

    assert result.returncode == 0
    # HEAD~1 plus der neue Commit im Origin: zwei fehlende Commits.
    assert "2" in result.stdout


def test_frisches_repo_ohne_commit_schweigt(tmp_path: Path) -> None:
    """`git rev-list HEAD..X` hat ohne HEAD nichts zu zaehlen."""
    leer = tmp_path / "leer"
    leer.mkdir()
    git(leer, "init", "--quiet")

    result = run_hook(leer)

    assert result.returncode == 0
    assert result.stdout == ""


def test_kein_remote_schweigt(tmp_path: Path) -> None:
    solo = tmp_path / "solo"
    solo.mkdir()
    git(solo, "init", "--quiet")
    commit(solo, "allein")

    result = run_hook(solo)

    assert result.returncode == 0
    assert result.stdout == ""


def test_kein_git_repo_schweigt(tmp_path: Path) -> None:
    irgendwo = tmp_path / "irgendwo"
    irgendwo.mkdir()

    result = run_hook(irgendwo)

    assert result.returncode == 0
    assert result.stdout == ""


def test_toter_remote_ohne_bekannten_stand_schweigt(tmp_path: Path) -> None:
    """Remote weg und nichts lokal gecacht: kein Grund, laut zu werden."""
    solo = tmp_path / "solo"
    solo.mkdir()
    git(solo, "init", "--quiet")
    commit(solo, "allein")
    git(solo, "remote", "add", "origin", str(tmp_path / "gibt-es-nicht"))

    result = run_hook(solo, timeout_s="2")

    assert result.returncode == 0
    assert result.stdout == ""


def test_kaputtes_fetch_meldet_die_untergrenze(tmp_path: Path) -> None:
    """Scheitert das fetch, zaehlt der zuletzt bekannte Stand — als Untergrenze.

    Eine stille 0 aus einem gescheiterten fetch waere die Beruhigung, gegen
    die dieser Hook gebaut ist.
    """
    origin = make_origin(tmp_path)
    klon = clone(tmp_path, origin)
    advance_origin(origin, "main", 4)
    # Der Klon kennt den neuen Stand bereits, hat ihn aber nicht eingespielt.
    git(klon, "fetch", "--quiet", "origin", "main")
    # Erst danach den Remote unerreichbar machen.
    git(klon, "remote", "set-url", "origin", str(tmp_path / "weg"))

    result = run_hook(klon, timeout_s="2")

    assert result.returncode == 0
    assert "4" in result.stdout
    assert "Untergrenze" in result.stdout or "groesser" in result.stdout


# Ein Remote, der weder antwortet noch abbricht. `sh -c` ist hier keine
# Verzierung: git haengt dem SSH-Kommando Host und `git-upload-pack ...` an,
# und ein blankes `sleep 30` stirbt daran sofort ("invalid time interval").
# Genau daran war die erste Fassung dieses Tests gruen, ohne je etwas zu
# messen. `sh -c` schluckt die Argumente als $0/$1 und schlaeft wirklich.
HAENGENDER_SSH = "sh -c 'sleep 30'"
HAENGENDE_URL = "ssh://git@example.invalid/repo.git"


def test_haengendes_ls_remote_wird_abgeschnitten(tmp_path: Path) -> None:
    """Der Deckel als Zeitmessung, nicht als Behauptung — Pfad `ls-remote`.

    Kein lokal gecachtes `origin/HEAD`, also fragt der Hook den Remote nach
    dem Default-Branch. Ohne `run_capped` wartet er die vollen 30 Sekunden ab
    — und mit ihm der Sessionstart.
    """
    solo = tmp_path / "solo"
    solo.mkdir()
    git(solo, "init", "--quiet")
    commit(solo, "allein")
    git(solo, "remote", "add", "origin", HAENGENDE_URL)

    start = time.monotonic()
    result = run_hook(solo, timeout_s="1", GIT_SSH_COMMAND=HAENGENDER_SSH)
    dauer = time.monotonic() - start

    assert result.returncode == 0
    assert result.stdout == ""
    assert dauer < 15, f"Hook brauchte {dauer:.1f}s — der Deckel greift nicht"


def test_haengendes_fetch_wird_abgeschnitten(tmp_path: Path) -> None:
    """Derselbe Deckel auf dem zweiten Netzaufruf — dem eigentlichen fetch.

    Hier ist `origin/HEAD` aus dem Klon bekannt, der Default-Branch kostet
    also kein Netz; haengen kann nur noch das fetch. Ein Deckel, der bloss
    auf dem ersten Aufruf sitzt, faellt genau hier auf.
    """
    origin = make_origin(tmp_path)
    klon = clone(tmp_path, origin)
    git(klon, "remote", "set-url", "origin", HAENGENDE_URL)

    start = time.monotonic()
    result = run_hook(klon, timeout_s="1", GIT_SSH_COMMAND=HAENGENDER_SSH)
    dauer = time.monotonic() - start

    assert result.returncode == 0
    # Der zuletzt bekannte Stand ist der aktuelle: nichts zu melden.
    assert result.stdout == ""
    assert dauer < 15, f"Hook brauchte {dauer:.1f}s — der Deckel greift nicht"
