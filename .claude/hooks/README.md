# SessionStart-Hook: Klon-Aktualität

`session-start-staleness.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter `origin/<Default-Branch>` liegt. Liegt er auf dem
Stand, sagt er nichts.

## Grund

Ein veralteter Klon hat am 3.8.2026 **zweimal** eine rote CI erzeugt, deren
Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
die das Gate einführten, an dem der Branch scheiterte. Wer den Fehler im
eigenen Diff sucht, sucht in den falschen Dateien; die Datei, die fehlt, steht
dort nicht drin. Die Prüfung kostet eine Sekunde und ersetzt diese Suche.

Das ist dieselbe Prüfung, die Teil 1 der `CLAUDE.md` unter «Vor der Arbeit»
von Hand verlangt. Von Hand heisst: genau dann vergessen, wenn es eilt.

## Die Reihenfolge der Anforderungen

**1. Der Hook blockiert die Session niemals.** Kein Netz, kein Remote,
detached HEAD, ein frisch initialisiertes Repo ohne Commit, flatterndes DNS —
jeder dieser Fälle geht still durch, Exit-Code 0. Ein Hook, der bei
Netzproblemen die Arbeit anhält, wird nach dem zweiten Mal abgeschaltet und
schützt danach gar nichts. Ein Hook, der eine Warnung verschluckt, schützt
weniger als einer, der sie zeigt — aber ein abgeschalteter Hook schützt gar
nichts, und deshalb steht diese Anforderung vor der Vollständigkeit.

Drei Entscheidungen im Skript folgen daraus und sehen wie Nachlässigkeit aus:

- **Kein `set -e`, kein `set -o pipefail`.** Beide würden aus «kein Netz» ein
  Hook-Versagen mit Exit != 0 machen. Jeder Aufruf wird einzeln geprüft, jeder
  Pfad endet mit `exit 0`.
- **stdin wird nicht gelesen.** Der Hook bekommt JSON (u. a. `source`:
  `startup`/`resume`/`clear`/`compact`), aber ein Lesen von einem offenen,
  leeren stdin hängt. Der Preis: der Hook läuft auch bei `resume` und
  `compact`. Da er bei 0 schweigt, kostet das nichts.
- **`GIT_TERMINAL_PROMPT=0`, `GIT_ASKPASS`, `GIT_SSH_COMMAND`
  (`BatchMode=yes`).** Ohne sie fragt git bei fehlenden Zugangsdaten nach
  Benutzername und Passwort und wartet am Terminal. Vorbelegt wird nur, was
  die Umgebung nicht selbst setzt.

**2. Kurzes Timeout auf das Netz.** Voreinstellung 5 Sekunden, überschreibbar
per `CLAUDE_STALENESS_FETCH_TIMEOUT`. `timeout(1)` fehlt auf macOS ohne
coreutils; dafür gibt es einen Fallback, der den Hintergrundprozess pollt und
abschiesst — ohne ihn wäre ausgerechnet dort kein Deckel aktiv. Zusätzlich
begrenzt `"timeout": 15` in `settings.json` den Hook als Ganzes.

**3. Ausgabe nur, wenn Commits fehlen.** Bei 0 schweigt er. Eine Zeile, die
bei jedem Start erscheint, wird nach einer Woche nicht mehr gelesen.

**4. Der Default-Branch wird ermittelt, nicht angenommen.** Zuerst über den
lokal gecachten Zeiger `refs/remotes/origin/HEAD` (kostet kein Netz), sonst
über `git ls-remote --symref origin HEAD` (mit Deckel). Drei Repos im
Portfolio heissen ihren Default-Branch `master` — `openlex-mcp`,
`swiss-courts-mcp`, `swisstopo-mcp`. Ein fest verdrahtetes `main` scheitert
dort mit «couldn't find remote ref main», was wie ein Netzproblem aussieht und
deshalb weggeklickt wird. Genau diese Annahme hat einen Branch 15 Commits alt
werden lassen.

## Wenn das fetch scheitert

Dann fällt der Hook auf den zuletzt bekannten Stand von
`origin/<Default-Branch>` zurück. Ist der 0, schweigt er; zeigt er eine Lücke,
meldet er sie mit dem Hinweis, dass die Zahl eine **Untergrenze** ist. Eine
stille 0 aus einem gescheiterten fetch als «alles aktuell» zu verkaufen wäre
genau die Beruhigung, gegen die der Hook gebaut ist.

## Gegenprobe

`tests/test_session_start_hook.py` fährt das Skript gegen echte, lokal
angelegte Repositories — ohne Netz. Jeder Fall ist so gebaut, dass er fällt,
wenn die zugehörige Zusicherung aus dem Skript entfernt wird: das Schweigen
bei 0, die Meldung bei n > 0, `master` statt `main`, detached HEAD, kein
Remote, ein toter Remote, und ein Remote, der hängt (`GIT_SSH_COMMAND` auf
`sleep 30`) — letzterer belegt den Deckel als Zeitmessung, nicht als
Behauptung.

## Gültigkeit

Ein Hook wirkt für alle Sessions erst, wenn er auf dem Default-Branch liegt.
