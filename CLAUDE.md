# CLAUDE.md

## Teil 1 — Portfolio-Konventionen

### Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen:

```bash
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

### Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.

Zwei Fallen, die beide grün blieben:

- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
  echte Zeit nicht widerlegen.
- `monkeypatch.setattr(modul.asyncio, "sleep", ...)` greift ins Modul
  `asyncio` selbst und entschärft die Mechanik im ganzen Prozess. Patche
  einen Modul-Alias (`_sleep = asyncio.sleep`), nicht das fremde Modul.

Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

### Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

### Wenn zwei Agenten dasselbe tun

Vor dem Anlegen eines Branches mit vorgegebenem Namen prüfen, ob es ihn schon
gibt:

```bash
git ls-remote --heads origin claude/<name> | wc -l
```

Steht dort `1`, arbeitet jemand anderes daran — mit Schreibrecht auf denselben
Ref.

Ein PR mit leerem Diff wird geschlossen, nicht gemergt. Der Test ist
`get_files` auf dem PR: kommt `[]` zurück, ändert er nichts. Ein grüner Check
sagt dazu nichts — die CI prüft den Head, nicht die Differenz zur Basis.

Am 21.8.2026 liefen zwei Sessions dieselbe Aufgabe über 45 Repos, auf den
Branches `claude/codex-review-audit-templates-9sn6mx` und
`claude/codex-review-audit-7ioh56`. Wo die eine zuerst nach `main` kam, wurde
`main` in den Branch der anderen gemergt und der add/add-Konflikt zugunsten
von `main` aufgelöst. Übrig blieben 14 PRs, die durch sämtliche Gates grün
liefen und nichts enthielten; sie wurden gemergt und hinterliessen leere
Merge-Commits. Mit den zwei Folge-PRs, die aus demselben Grund gegenstandslos
waren, waren 16 der 59 PRs jenes Tages reine Reibung.

Dieselbe Klasse wie der handgeschriebene Stub, der denselben Feldnamen annahm
wie der Code: Nichts ist rot, weil nichts geprüft wird, worauf es ankommt.

## Teil 2 — Dieses Repo


**ruff: eine Quelle.** `pyproject.toml`, `dev`-Extra, `ruff==0.16.1`. Die CI
hat keinen eigenen Pin-Schritt — der Install über `ci.yml` genügt, lokal wie
dort. Eine `.pre-commit-config.yaml` gibt es nicht; wenn eine dazukommt, muss
sie dieselbe Version aus `pyproject.toml` beziehen und keine zweite nennen.

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet.

**Gates, wörtlich aus `ci.yml`** (Matrix: Python 3.10 / 3.11 / 3.12):

```
python -m py_compile src/swiss_procurement_mcp/server.py src/swiss_procurement_mcp/client.py
python -c "from swiss_procurement_mcp.server import mcp; print('Import OK')"
pytest -m "not live" -v
python scripts/check_version_sync.py
python scripts/check_ruff_pin.py
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
pytest tests/ -m live -v --junitxml=live-report.xml 2>&1 | tee live-output.txt
```

Syntax-Prüfung und Import-Test fehlten hier, obwohl der Block «wörtlich»
heisst — sie stehen in `ci.yml` vor den Unit-Tests. Die letzte Zeile ist
kein PR-Gate: sie gehört dem geplanten Live-Lauf.

**Die vier Jobs sind ungleich zugeschnitten.** `test` fährt die Matrix
3.10/3.11/3.12, `lint` läuft ohne Matrix auf **3.10** — nicht auf 3.11 wie in
den meisten Schwester-Servern. Ein `fail-fast: false` steht nicht da.

**Die Matrix fährt kein 3.13.** Damit ist dies einer von zwei Servern im
Portfolio (mit `swiss-holidays-mcp`), die das aktuellste Feld nicht testen.

**Ein vierter Job gatet mit: `docker`** («Docker build», `needs: [test]`). Er
stand in keiner Liste. Sein `permissions`-Block hebt `actions: write` an, weil
der GHA-Cache-Backend das braucht — ein rotes `test` heisst hier ausserdem,
dass `docker` gar nie lief.

**`scripts/` liegt seit diesem Commit im ruff-Scope.** Die drei Dateien dort
— `check_version_sync.py`, `classify_live_run.py`, `record_fixtures.py` —
bestanden ruff schon vorher, der erste Lauf war also grün. Das ist kein
Argument gegen die Erweiterung, sondern der Grund, warum die Lücke so lange
offenblieb: sie biss noch nicht. `check_version_sync.py` ist selbst ein Gate,
`record_fixtures.py` erzeugt die Fixtures der Unit-Tests, und
`classify_live_run.py` entscheidet über die Einordnung eines Live-Laufs.

Seither ist `check_ruff_pin.py` dazugekommen — vier Dateien, gleicher Scope.

**Live-Tests: geplanter Workflow vorhanden.** `.github/workflows/ci.yml`,
`cron: "23 3 * * *"` plus `workflow_dispatch`. Die Live-Suite ist also nicht bloss
per `-m "not live"` ausgeschlossen — DRIFT-005 ist hier erfüllt. `schedule`
greift nur auf dem Default-Branch (`main`): Änderungen am Workflow wirken erst
nach dem Merge, vorher von Hand per `workflow_dispatch`.

**Ein fünftes Gate steht ausserhalb `ci.yml`.**
`.github/workflows/security.yml` hängt am selben PR-Trigger: gitleaks über die
ganze Historie (`fetch-depth: 0`). Wer nur `ci.yml` liest, hält den PR für
vollständig geprüft.

**Beide Workflows gaten nur `pull_request: branches: [main]`.** Ein PR mit
einer anderen Basis bekommt keinen einzigen Check — der `push`-Trigger nennt
zusätzlich `develop`, der `pull_request`-Trigger nicht. Das ist der zweite
Fall der Teil-1-Regel «PR ohne jeden Check»: nicht immer ein Merge-Konflikt,
hier eine Basis ausserhalb des Triggers.
