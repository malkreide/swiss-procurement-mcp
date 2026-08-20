#!/usr/bin/env bash
#
# SessionStart-Hook — meldet, wie viele Commits der ausgecheckte Stand hinter
# origin/<Default-Branch> liegt. Bei 0 schweigt er.
#
# GRUND: Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt,
# deren Ursache nicht im Diff stand — die fehlenden Commits waren jeweils
# genau die, die das Gate einfuehrten, an dem der Branch scheiterte. Die
# Pruefung kostet eine Sekunde und ersetzt eine Fehlersuche in den falschen
# Dateien.
#
# ERSTE ANFORDERUNG, vor allen anderen: Der Hook blockiert die Session
# NIEMALS. Kein Netz, kein Remote, detached HEAD, frisches Repo ohne Commit,
# flatterndes DNS — jeder dieser Faelle geht still durch. Ein Hook, der bei
# Netzproblemen die Arbeit anhaelt, wird nach dem zweiten Mal abgeschaltet
# und schuetzt danach gar nichts.
#
# Daraus folgen drei Entscheidungen, die wie Nachlaessigkeit aussehen und
# keine sind:
#
#   1. Kein `set -e`, kein `set -o pipefail`. Beide machen aus einem
#      fehlgeschlagenen `git`-Aufruf einen Abbruch mit Exit != 0 — also aus
#      "kein Netz" ein Hook-Versagen, das der Sessionstart meldet. Jeder
#      Aufruf wird stattdessen einzeln geprueft; das Skript endet auf jedem
#      Pfad mit `exit 0`.
#   2. stdin wird nicht gelesen. Der Hook bekommt zwar JSON (u.a. `source`),
#      aber ein Lesen von einem offenen, leeren stdin haengt — genau das,
#      was hier nicht passieren darf. Der Preis: der Hook laeuft auch bei
#      `resume`/`compact`. Da er bei 0 schweigt, kostet das nichts.
#   3. Netz nur mit Deckel (siehe `run_capped`) und nur nicht-interaktiv.
#
set -u

# Wenige Sekunden, nicht mehr: der Sessionstart wartet darauf.
FETCH_TIMEOUT="${CLAUDE_STALENESS_FETCH_TIMEOUT:-5}"

# Nichts darf auf eine Eingabe warten. Ohne diese drei fragt git bei
# fehlenden Zugangsdaten nach Benutzername/Passwort und haengt am Terminal.
# Der Deckel unten faengt das zwar auch ab — aber erst nach Ablauf, hier
# scheitert es sofort. Vorbelegung nur, wenn die Umgebung nichts sagt.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS="${GIT_ASKPASS:-true}"
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o BatchMode=yes -o ConnectTimeout=5}"

# `timeout(1)` fehlt auf macOS ohne coreutils. Ohne Fallback waere dort gar
# kein Deckel aktiv — also genau auf jenen Rechnern, auf denen niemand danach
# sucht. Der Fallback pollt den Hintergrundprozess und schiesst ihn ab.
run_capped() {
  local secs="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout -k 1 "$secs" "$@"
    return $?
  fi
  "$@" &
  local pid=$!
  local waited=0
  while [ "$waited" -lt "$((secs * 10))" ]; do
    kill -0 "$pid" 2>/dev/null || {
      wait "$pid"
      return $?
    }
    sleep 0.1
    waited=$((waited + 1))
  done
  kill -TERM "$pid" 2>/dev/null
  sleep 0.2
  kill -KILL "$pid" 2>/dev/null
  wait "$pid" 2>/dev/null
  return 124
}

# --- Voraussetzungen. Fehlt eine, ist das kein Fehler, sondern Schweigen. ---
command -v git >/dev/null 2>&1 || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
# Frisch initialisiertes Repo: HEAD zeigt auf nichts, es gibt nichts zu
# vergleichen. `--verify` deckt zugleich einen kaputten HEAD ab.
git rev-parse --verify --quiet HEAD >/dev/null 2>&1 || exit 0
git remote get-url origin >/dev/null 2>&1 || exit 0

# --- Default-Branch ermitteln, nicht annehmen. ---
# Drei Repos im Portfolio heissen ihn `master` (openlex-mcp, swiss-courts-mcp,
# swisstopo-mcp). Ein fest verdrahtetes `main` scheitert dort mit "couldn't
# find remote ref main" — was wie ein Netzproblem aussieht und deshalb
# weggeklickt wird. Genau so wurde ein Branch 15 Commits alt.
default_branch=""
# Zuerst der lokal gecachte Zeiger: kostet kein Netz.
origin_head="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)"
if [ -n "${origin_head}" ]; then
  default_branch="${origin_head#origin/}"
fi
# Sonst beim Remote nachfragen — mit Deckel, wie jeder Netzaufruf hier.
#
# Die Ausgabe geht in eine Datei und nicht in eine Pipe, und das ist der
# Unterschied zwischen "Deckel" und "Deckel, der haelt": `timeout` schiesst
# nur das direkte Kind ab. Ein `ssh`, das git gestartet hat, ueberlebt das
# und haelt das Schreibende der Pipe offen — `sed` sieht dann kein EOF und
# die Kommandosubstitution wartet weiter. Der Hook haenge genau dort, wo er
# nie haengen darf. Eine Datei hat kein EOF-Problem.
if [ -z "${default_branch}" ]; then
  ls_remote_out="$(mktemp 2>/dev/null)" || ls_remote_out=""
  if [ -n "${ls_remote_out}" ]; then
    run_capped "${FETCH_TIMEOUT}" git ls-remote --symref origin HEAD \
      >"${ls_remote_out}" 2>/dev/null
    default_branch="$(
      sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p' "${ls_remote_out}" | head -n 1
    )"
    rm -f "${ls_remote_out}"
  fi
fi
[ -n "${default_branch}" ] || exit 0

# --- Abstand messen. ---
note=""
if run_capped "${FETCH_TIMEOUT}" git fetch --quiet origin "${default_branch}" >/dev/null 2>&1; then
  behind="$(git rev-list --count HEAD..FETCH_HEAD 2>/dev/null)"
else
  # Netz weg, Remote weg, DNS flattert: kein Grund, laut zu werden. Der
  # zuletzt bekannte Stand von origin/<Branch> liegt aber schon auf der
  # Platte und kann eine Luecke zeigen. Dann sagen wir sie — mit dem
  # Hinweis, dass sie nur eine Untergrenze ist.
  git rev-parse --verify --quiet "refs/remotes/origin/${default_branch}" >/dev/null 2>&1 || exit 0
  behind="$(git rev-list --count "HEAD..refs/remotes/origin/${default_branch}" 2>/dev/null)"
  note=" — fetch fehlgeschlagen, Zahl aus dem zuletzt bekannten Stand; die echte Luecke kann groesser sein"
fi

# Alles, was keine Zahl ist, ist keine Meldung wert. `0` ebenso wenig: der
# Hook schweigt, wenn nichts fehlt.
case "${behind}" in
'' | *[!0-9]*) exit 0 ;;
0) exit 0 ;;
esac

printf 'Klon veraltet: %s Commit(s) hinter origin/%s%s\n' "${behind}" "${default_branch}" "${note}"
printf 'Aufholen: git fetch origin %s && git merge FETCH_HEAD\n' "${default_branch}"
printf 'Warum das zaehlt: fehlende Commits erzeugen eine rote CI, deren Ursache nicht im Diff steht.\n'

exit 0
