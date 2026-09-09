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

**Ein 4xx ist kein Nein.** Am 29.8.2026 antwortete `past-publications` in
`swiss-procurement-mcp` auf jede Publikation mit Losen mit HTTP 400. Daraus war
geschlossen worden, die Quelle verweigere diese Auskunft; der Befund stand
datiert im Fixture-Nachweis, ein Test bestätigte ihn, alles blieb grün. Die
Spec desselben Endpunkts führt einen als *optional* deklarierten Parameter
`lotId` — für Publikationen mit Losen ist er Pflicht. Mit ihm antwortet
dieselbe Publikation mit 200. Ein Projekt trug sieben Vorgängerpublikationen,
die der Server als «Quelle nicht erreichbar» wegwarf.

Drei Handgriffe daraus:

- **Die Parameterliste der Spec durchgehen, bevor ein Statuscode eingeordnet
  wird.** «Optional» heisst dort oft «optional für die Mehrheit».
- **Einer deterministischen Absage keinen Wiederholungsrat geben.** «Nicht
  erreichbar, bitte später erneut» ist bei einem 400 falsch und liest sich für
  das Modell wie eine Störung. Den Status mitführen und den fehlenden
  Parameter benennen — den Status, nicht den Antwortkörper.
- **Beide Antworten aufzeichnen, mit und ohne den Parameter.** Eine
  Aufzeichnung nur des Fehlschlags kann nicht zeigen, dass er vermeidbar war;
  dass nur der 400er aufgezeichnet war, ist der Grund, warum der falsche
  Befund nicht auffiel.

**Die Korrektur griff dann selbst zu weit.** Aus «`lotId` fehlt» wurde
stillschweigend «mit `lotId` antwortet die Publikation». Für die *Publikation*
stimmt das; für jedes einzelne *Los* nicht. `past-publications` führt die
Historie je Los, und ein Los ohne eigene Vorgängerpublikation antwortet 404 —
nicht 200 mit leerer Liste. Publikation 32705-42 trägt 39 Lose, von denen
genau eines antwortet. Daran lief die Live-Suite am 5.9.2026 rot.

Zwei Dinge daraus, und das zweite wiegt schwerer:

- **Die Gegenprobe zur Gegenprobe.** Vier Publikationen belegten den
  `lotId`-Befund, und alle vier antworteten — mit `lots[0]`. Gemessen war
  damit «mindestens ein Los antwortet», aufgeschrieben «Lose antworten».
  Wer einen Fehlschluss korrigiert, prüft, ob die Korrektur mehr behauptet
  als die Messung.
- **Ein 404 ist auch dann kein Nein, wenn er stimmt.** Der Server verpackte
  ihn in «unreachable … please retry shortly» — denselben Wiederholungsrat,
  gegen den der Absatz oben geschrieben ist, nur eine Statusklasse weiter.
  Die Quelle liefert denselben Körper für ein echtes Los ohne Historie und
  für eine erfundene Id; sie trennt die Fälle nicht, also darf die Antwort
  es auch nicht. «Nicht entscheidbar» ist eine Auskunft, «keine Vorgänger»
  wäre erfunden.

**Und ein 403 ist gar keine Auskunft.** Am 29.8.2026 sollten für 42 Repos die
Dependabot-Labels nachgemessen werden. Alle 13 Abfragen des ersten Stapels
kamen zurück als:

```
Failed to find label: API rate limit already exceeded for user ID 8864492.
```

Der gefährliche Teil steht vorn: Das Werkzeug verpackt eine Sperre als
Fund-Fehlschlag. Wer die Zeile überfliegt oder nur auf ein leeres Ergebnis
prüft, zählt 39 Repos als «Label fehlt» und hat seine eigene Erschöpfung
gemessen. Das Limit hängt am Konto, nicht am Repo — derselbe Vormittag hatte
es mit 42 eröffneten und 42 gemergten PRs verbraucht.

Das ist der Absatz darüber, andersherum gelesen: dort war ein 400 eine echte,
wiederholbare Antwort und galt als Störung; hier ist eine Störung als Antwort
verpackt. Entscheidend ist nie der Statuscode, sondern ob die Quelle überhaupt
geantwortet hat.

- **Positivkontrolle im selben Repo.** Ein «nicht gefunden» wird erst dadurch
  zur Messung, dass eine gleichzeitige Abfrage etwas findet.
- **Die Messung entlang der Sperre teilen.** `raw.githubusercontent.com` ist
  ein CDN und nicht die REST-API. Um 11:19:27 UTC lieferte es für
  `register-mcp` HTTP 200, während die Label-Abfrage desselben Repos in
  derselben Minute die Sperre meldete. Alle 42 `dependabot.yml` kamen so
  durch, während die Label-Hälfte stand.
- **Am Token vorbei geht es nicht.** Beide Umwege enden am Agent-Proxy, und
  jeder mit einer eigenen irreführenden Begründung. `api.github.com` ohne
  Zugangsdaten:

  ```
  GitHub access is not enabled for this session. An org admin must connect
  the Claude GitHub App for this organization.
  ```

  Das ist keine Aussage über die Organisation, sondern das, was ohne Token
  kommt. Wer ihr folgt, sucht einen Admin für ein Problem, das keiner hat.
  Die HTML-Seite `github.com/<owner>/<repo>/labels` fällt ebenfalls, aber
  anders:

  ```
  This GitHub API path is not available: sessions are bound to their
  configured repositories. Use repository-scoped endpoints
  (repos/{owner}/{repo}/...).
  ```

  Der Proxy behandelt also auch `github.com` als API-Pfad; die zweite Meldung
  klingt nach einem Scope-Problem und ist doch nur dieselbe Sackgasse. Den
  Token aus der Umgebung in einen curl-Header zu setzen, blockiert der
  Klassifikator. Ob es überhaupt hülfe, ist offen: die Sperre nennt ein
  Nutzerkonto, und ob der Token zu diesem gehört, wurde nie geprüft.
- **Die Sperre gilt nicht dem Dienst, sondern dem Zugangspfad.** Unmittelbar
  nachdem eine Abfrage der Checks eines PR sauber durchlief, meldete die
  Label-Abfrage weiter die Sperre. Von einem blockierten Werkzeug also nicht
  auf «GitHub ist zu» schliessen — und umgekehrt eine gelungene Abfrage nicht
  als Entwarnung für die gesperrte nehmen. Das ist dieselbe Asymmetrie wie
  bei der verschwundenen Codex-Meldung weiter unten.

Wann die Sperre fällt, geben diese Beobachtungen nicht her. Die Meldung nennt
keinen Zeitpunkt, und die `X-RateLimit`-Kopfzeilen sind hinter dem Proxy nicht
zu sehen. Belegt sind drei gesperrte Zeitpunkte — 11:14, 11:16 und 11:19 UTC.
Wer daraus eine Dauer macht, hat sie erfunden.

**Dieselbe Falle bei einer Konfigurationsoption: die Vorgabe lesen, bevor man
einen Schlüssel für wirkungslos hält.** Am 29.8.2026 fielen die
`labels:`-Zeilen aus den `dependabot.yml` des Portfolios, begründet mit
«Dependabot legt Labels nicht an». Eine Messung danach zeigte, dass
`dependencies` in 36 von 42 Repos sehr wohl existiert, 35 davon mit GitHubs
Standardbeschreibung. Das las sich zuerst wie ein Beleg, dass die Aktion
falsch war.

Die Optionsreferenz kehrt es um:

```
Dependabot creates these default labels automatically, as necessary in
your repository.

If you define more than one package manager, an additional label for the
ecosystem or language is added to each pull request.

The labels specified are used instead of the default labels.
```

Ohne `labels:` vergibt Dependabot also `dependencies` — und, sobald mehr als
ein Paketmanager deklariert ist, zusätzlich ein Ökosystem-Label — und legt sie
selbst an; eine eigene Liste **ersetzt** diesen Satz, und «if any of these
labels is not defined in the repository, it is ignored». Die Zeile war nicht
wirkungslos — sie tauschte einen sich selbst pflegenden Vorgabesatz gegen eine
starre Liste.

**Die Bedingung nicht weglassen.** Bei nur einem Paketmanager steht das
Ökosystem-Label gar nicht zu; wer es dort trotzdem erwartet, schreibt genau
den Fehlbefund auf, gegen den dieser Abschnitt geschrieben ist — der Abschnitt
liefe an sich selbst vorbei. Im Portfolio deklariert jede `dependabot.yml`
zwei (`pip` und `github-actions`), die Bedingung ist hier also überall
erfüllt; anderswo nicht unbedingt. Aufgefallen ist die fehlende Bedingung
nicht beim Schreiben, sondern durch einen Codex-Review auf
`swiss-environment-mcp` PR #113 — vierzehn Sekunden vor dem Merge desselben
PR.

Was das kostet, ist an `openlex-mcp` gemessen: zwei Ökosysteme deklariert,
also stünden `dependencies` **und** ein Ökosystem-Label zu; vorhanden ist nur
das erste, `github-actions` und `github_actions` fehlen beide (Kontrolle `bug`
vorhanden). `register-mcp` ist die Gegenprobe: dort existieren alle vier
deklarierten Namen mit handgeschriebener Beschreibung, die Liste ist gewollt
und vollständig.

**Dreimal falsch eingeordnet, in drei Richtungen.** Erst die Zeile für bloss
wirkungslos gehalten. Dann die gefundenen Labels für einen Widerspruch. Dann,
auf denselben Fund gestützt, einen richtigen PR geschlossen mit dem Argument,
das Label existiere ja — obwohl es existiert, *weil* die Vorgabe es anlegt.
Der dritte Fehler ist der teuerste, weil er wie eine Messung aussah.

Was die Messung **nicht** hergibt: wer die 36 Labels angelegt hat. Die
Referenz sagt, Dependabot tue es; die Objekt-IDs liegen aber so dicht
beieinander, dass sie eher aus einem Stapellauf stammen. Beides passt zum
Befund, keines ist belegt — die Herkunft blieb ungemessen.

Beim Aufräumen gilt deshalb dieselbe Frage wie bei `lotId`: Was ist die
*Vorgabe*, wenn man das Ding weglässt — nicht bloss, ob der aktuelle Wert
etwas bewirkt.

**`results[0]` ist nur so verlässlich wie die Zusicherung danach.** Pinnt die
Abfrage einen bekannten Datensatz, ist der erste Treffer eine Drift-Wache und
in Ordnung. Hängt die Zusicherung dagegen davon ab, *welche* Variante die
Quelle heute zuoberst hat, prüft der Test den Tag: am 25.8.2026 rot, weil die
neueste Zürcher Publikation zufällig Lose hatte, am 26.8. grün, ohne dass sich
etwas geändert hätte. Den Fall gezielt wählen und beide Zweige fahren.

**Und die Ebene darunter zählt mit.** Derselbe Test war gegen `results[0]`
gehärtet und fiel am 5.9.2026 trotzdem — die Annahme war nach `lots[0]`
gewandert und dort unbemerkt geblieben. Eine Härtung gilt für den Index, den
sie anfasst, nicht für die Datei.

**Was ein Mapper verwirft, muss er zählen.** `_to_lots` überspringt ein Los
ohne `lotId` — richtig, denn die Id ist der einzige Griff, den der
Historie-Endpunkt annimmt. Still zu sein war es nicht: Im gemappten Modell
fehlt das Los danach einfach, und von aussen ist ein Teilverlust nicht von
einer Publikation mit weniger Losen zu unterscheiden. Keine Prüfung konnte das
sehen — die Fixture-Tests vergleichen die gemappte Liste mit der Aufzeichnung
und fangen damit eine Regression des Mappers, aber nicht die Quelle, die
anfängt, solche Datensätze zu liefern; dann stimmen Aufzeichnung und Mapper
weiter überein und sind beide unvollständig. Die Live-Suite sah ohnehin nur die
gemappte Seite.

Ein Zähler in der Antwort ist die fehlende Spur, und er ist zugleich das, was
die Live-Suite messen kann. Die Regel ist nicht auf Lose beschränkt: Jedes
`continue` in einem Mapper wirft etwas weg, und was weggeworfen wird, ohne
gezählt zu werden, ist hinterher nicht von «gab es nicht» zu unterscheiden.

Gefunden hat das ein Codex-Review, und zwar erst in der achten Runde auf
demselben PR — nachdem sieben Runden lang Zusicherungen *über* die Lose
geschärft worden waren, ohne dass jemand fragte, ob die Liste überhaupt
vollständig ankommt.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

### Wenn Codex gar nicht erst hinsieht

Die Zeile oben unterstellt, dass es einen Befund geben *kann*. Das ist nicht
immer so, und man sieht es dem PR nicht an.

Am 21.8.2026 war das Code-Review-Kontingent zwischen 08:41 und 09:48
aufgebraucht — davor echte Reviews, danach in 30 Repos nur noch:

```
You have reached your Codex usage limits for code reviews.
```

Wie lange die Sperre dauerte, geben die Beobachtungen nur als Spanne her. Vier
Zeitpunkte sind belegt: letzter gelungener Review am 21.8. um 08:41, erste
Limit-Meldung um 09:48, letzte beobachtete Limit-Meldung am 22.8. um 11:03,
erste *andere* Meldung am 23.8. um 08:22.

Zwischen erster und letzter Limit-Meldung liegen **25 h 15 min**. Das ist der
Abstand zweier Fehlschläge, nicht die Dauer einer Sperre. Wer ihn Untergrenze
nennt, hat die durchgehende Erschöpfung schon vorausgesetzt, die er belegen
soll: Öffnete sich das Fenster zwischendurch und schloss es sich durch neue
Auslöser wieder, waren es zwei kurze Sperren und nie eine von 25 Stunden.
Untergrenze einer *einzelnen* Sperre sind die 25 h 15 min nur unter genau dieser
Annahme — und die ist unbelegt.

Nach oben trägt die Rechnung nur mit einer Zusatzannahme. Die längste mit den
Beobachtungen verträgliche Sperre reicht vom letzten Erfolg um 08:41 bis zur
abweichenden Meldung um 08:22, also **47 h 41 min**. Dass jene Meldung das Ende
der Sperre markiert, folgt aber allein daraus, dass an ihrer Stelle keine
Kontingent-Meldung mehr stand — und das setzt die Reihenfolge der Prüfungen
voraus, deren Beweis weiter unten selbst auf einer ungeprüften Annahme steht.
Läuft die Environment-Prüfung zuerst, kann ihre Meldung erscheinen, während das
Kontingent noch weg ist; dann begrenzt sie gar nichts.

Sauber wäre die Obergrenze über einen **gelungenen** Review am 23.8. — davon gab
es 42 —, denn ein durchgelaufener Review belegt das Kontingent unmittelbar und
braucht keine Reihenfolge. Das ist dieselbe Asymmetrie wie bei der Environment
weiter unten: Der Lauf trägt, die Meldung nicht. Die Uhrzeit des ersten dieser
42 hat hier aber niemand festgehalten; solange sie fehlt, ist die Obergrenze so
gut wie die Annahme, auf der sie steht.
Wer stattdessen ab der ersten Limit-Meldung rechnet, unterschlägt die 67
Minuten, in denen das Kontingent schon weg gewesen sein kann, und nennt die
Spanne zwischen zwei Beobachtungen eine Obergrenze.

Beobachtungspunkte sind keine Messreihe — die 21 Stunden vor der abweichenden
Meldung liefen ganz ohne Codex-Auslöser, dort hat niemand gemessen.

In der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden,
ohne dass jemand hineingesehen hat, und am 22.8. noch einmal 43.

**Am 29.8.2026 war das Kontingent wieder weg.** Das ist eine zweite Sperre und
nicht die Fortsetzung der ersten: am 23.8. liefen 42 Reviews durch. Was in den
sechs Tagen dazwischen war, hat niemand gemessen — die Sperren wiederholen sich
also, aber ihre Frequenz gibt keine dieser Beobachtungen her.

Gemessen an `swiss-procurement-mcp` PR #68: als Draft angelegt um 09:23:59, in
dieser Zeit kein Kommentar, auf ready umgestellt, gemergt um 09:28:42.
`get_reviews` liefert `[]`, und der einzige Kommentar steht um 09:28:42:

```
You have reached your Codex usage limits for code reviews. You can see your
limits in the [Codex usage dashboard](https://chatgpt.com/codex/cloud/settings/usage).
```

**Der Text ist gewachsen.** Die Fassung vom 21.8. endete nach dem ersten Satz;
seit dem 29.8. hängt ein Verweis aufs Dashboard daran. Wer auf den ganzen Satz
vergleicht statt auf seinen Anfang, hält die neue Fassung für einen unbekannten
weiteren Fall — und wer den Abschnitt danach umschreibt, hat aus einer
Textänderung einen Befund gemacht.

**Und die Meldung sagt nichts über die Environment.** Sie erwähnt sie nicht,
und keine Beobachtung verbindet die beiden — das allein genügt schon, um aus
einer Kontingent-Meldung nichts über die Konfiguration zu schliessen. Die
Reihenfolge der Prüfungen (Kontingent zuerst) macht es zusätzlich plausibel,
trägt hier aber nichts: Ihr Beweis steht selbst auf einer ungeprüften Annahme,
wie unten beim vierten Grund vermerkt. Für `swiss-procurement-mcp` blieb
damit offen, ob eine da ist. Das ist die Umkehrung der Regel weiter unten: Wie
eine verschwundene Limit-Meldung keine Entwarnung ist, ist eine vorhandene kein
Nachweis, dass danach alles stünde.

**Am 30.8.2026 war das Kontingent wieder offen.** Auf `swiss-procurement-mcp`
PR #75 lief um 09:09:18 ein Review an, keine 24 Stunden nach der Absage auf #68.
Die zweite Sperre hat sich also gelöst wie die erste; wie lange sie stand, sagen
diese zwei Beobachtungen nicht — es sind zwei Zeitpunkte, keine Messreihe.

Nebenbei beantwortet derselbe Lauf die Frage darüber — in der Richtung, die
trägt. Die beiden Belege sind nicht gleich stark: Eine Environment-Meldung
belegt keine fehlende Environment (unten gemessen), ein durchgelaufener Review
aber eine vorhandene. Für dieses Repo sind es an jenem Tag zwei.

**Fünf** Gründe, warum Codex schweigt, und nur einer davon ist harmlos:

- **Kein Befund** — dann schreibt er einen gewöhnlichen Issue-Kommentar:

  ```
  Codex Review: Didn't find any major issues. Swish!
  ```

  Der Schlusssatz wechselt bei jedem Lauf («Delightful!», «Keep it up!»,
  «More of your lovely PRs please.»); stabil ist nur der Satz davor.
- **Der PR ist ein Draft** — die *automatischen* Auslöser greifen dort nicht.
  Von Hand angestossen läuft Codex sehr wohl auf einem Draft: am 29.8.2026 auf
  `swiss-efv-mcp#64`, 16 Sekunden nach dem Anlegen, Auslöser «Manual request».
  Das ist zugleich der Weg, einen Draft prüfen zu lassen, **bevor** man ihn auf
  ready stellt — und damit das Gegenmittel zu den Sekunden zwischen «ready» und
  Merge weiter unten.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben.
- **Codex meldet eine fehlende Environment** — dann schreibt er:

  ```
  To use Codex here, create an environment for this repo.
  ```

  «Meldet», nicht «fehlt»: Der Text ist keine verlässliche Auskunft über die
  Konfiguration — am 29.8.2026 stand er in einem Repo, das eine hatte, und war
  eine Minute später weg. Eher wiederholen als konfigurieren — aber **nicht
  sofort**: Die Meldung kann einem verzögert startenden Lauf vorausgehen, und
  ein zweiter Auslöser verdrängt dann den ersten. Die Messungen dazu stehen
  unten im Abschnitt über die Environment.
- **Es lief gar kein Auslöser** — und ein Push ist keiner. Codex zählt sie
  selbst im Infokasten auf: einen PR zum Review öffnen, einen Draft auf ready
  stellen, «@codex review» kommentieren. Wer einen Befund behebt und pusht,
  bekommt deshalb keinen zweiten Lauf, sondern gar nichts.

Der vierte kam erst zum Vorschein, als der dritte wegfiel, und das ist kein
Zufall: Die Prüfungen liegen hintereinander. Dass es diese Reihenfolge ist und
nicht die umgekehrte, lässt sich an einem einzigen Repo ablesen — in
`swiss-public-data-mcp` bekam PR #54 am 22.8. um 10:56:55 die Kontingent-Meldung
und PR #56 am 23.8. um 08:22:20 die Environment-Meldung. Läge die
Environment-Prüfung vorn, hätte #54 sie schon am Vortag gesehen; die Environment
fehlte ja bereits. Zwei Meldungen aus demselben Repo schlagen hier jede
Vermutung über die Reihenfolge.

Diese Ableitung hat eine Voraussetzung, die seit dem 29.8.2026 nicht mehr
sicher ist: dass die Environment am 22.8. schon fehlte. Geschlossen wurde das
aus der Meldung vom 23.8. — und die Meldung ist, wie unten gemessen, kein
verlässlicher Beleg für eine fehlende Environment. Die Reihenfolge kann
weiterhin stimmen; ihr Beweis steht auf einer Annahme, die niemand geprüft hat.

Praktisch heisst das: **Eine verschwundene Limit-Meldung ist keine Entwarnung.**
Sie kann bedeuten, dass das Kontingent wieder da ist — und dass jetzt etwas
anderes den Review verhindert. Belegt ist eine Prüfung erst durch einen
Statusbericht auf `✅ Completed`, ein Review-Objekt **oder** eine
Befundlos-Meldung — **und alle drei zählen nur für den Commit, den sie selbst
nennen** (weiter unten, «Nennt das jüngste Codex-Ergebnis den aktuellen Head»).
Der Bericht steht dabei zuerst und nicht bloss der Vollständigkeit halber: Er
ist der einzige der drei, den es auch dann gibt, wenn kein Ergebnis mehr
gepostet wird — der Fall des geschlossenen PR weiter unten hat genau ihn und
sonst nichts. Er belegt «geprüft», nicht «sauber». Wer nur das Objekt gelten
lässt, zählt
jeden befundlosen Review als ungeprüft — und baut sich denselben Fehlalarm ein,
den dieser Abschnitt verhindern soll, nur in die andere Richtung.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein Review **mit** Befund ist ein Review-Objekt
(«💡 Codex Review», mit Commit-Angabe); ein Review **ohne** Befund ist ein
gewöhnlicher Issue-Kommentar.

**Die Ausfallmeldungen sind in der Form nicht festgelegt.** Hier stand, auch
sie seien Issue-Kommentare; am 9.9.2026 kam die Environment-Meldung auf `#87`
zweimal als **Review-Kommentar in einem Thread**. Beide Formen also, und wer
nur eine abfragt, übersieht sie. Beim Draft greift ohne
manuellen Anstoss kein Auslöser, dort steht dann überhaupt nichts; ein
kommentarloser Draft ist deshalb kein Beleg, sondern ein nicht durchgeführter
Test. Ein von Hand angestossener Lauf hinterlässt dagegen auch auf einem Draft
dieselben Spuren wie sonst — Statusbericht, Review-Objekt oder
Befundlos-Meldung —, und die zählen dort genauso.

Der fünfte Grund ist der gefährlichste, weil er nicht wie eine Lücke aussieht,
sondern wie ein Beleg: Nach einem Push steht das Review-Objekt des *vorigen*
Commits weiter im PR. Am 29.8.2026 auf `swiss-efv-mcp#62` — Review auf
`cd2046c` um 11:58:08 (Auslöser «Draft marked ready») mit einem P2-Befund; Fix
als `ca00672` gepusht, dessen CI um 12:01:47 durch war; um 12:02 nannte die
Zusammenfassung weiterhin nur `cd2046c` und war seit 11:58:12 nicht angefasst.
Erst ein «@codex review» von Hand erzeugte um 12:02:55 den zweiten Lauf, der um
12:05:23 befundlos endete. Ohne ihn wäre ausgerechnet der Fix-Commit ungeprüft
geblieben, während im PR ein echtes Review stand und das Häkchen erfüllt
aussah — dieselbe Klasse wie die drei bis fünf Sekunden zwischen «ready» und
Merge weiter unten, nur schwerer zu bemerken, weil hier etwas *da* ist.

Die richtige Frage ist deshalb nie «steht ein Review im PR», sondern **«nennt
das jüngste Codex-Ergebnis den aktuellen Head»**. Wer nach einem Push
weiterarbeiten will, kommentiert «@codex review» — sonst gilt der eigene Fix als
geprüft, ohne es zu sein.

**In einem zweiten Repo bestätigt.** Am 30.8.2026 auf `swiss-procurement-mcp#75`
bekam der Fix-Commit `a1984c6` nach dem Push keinen Lauf; der Statusbericht
nannte weiter den Commit davor. Erst ein «@codex review» von Hand erzeugte um
09:14:48 den zweiten Lauf, der um 09:16:39 befundlos endete. Zwei Repos, zwei
Fix-Commits, derselbe Ablauf — das ist kein Einzelfall eines Repos.

Nur gegen das Review-**Objekt** zu prüfen reicht dafür nicht, und zwar in beide
Richtungen falsch:

- Ein befundloser Lauf erzeugt gar kein Review-Objekt, sondern einen
  Issue-Kommentar. Nach einem befundlosen Wiederholungslauf zeigt das noch
  vorhandene Objekt weiter auf den **alten** Commit — der Head ist geprüft, die
  Prüfung meldet Fehlalarm. Genau so lag es auf `swiss-efv-mcp#62`: Objekt auf
  `cd2046c`, befundloser Lauf auf `ca00672` nur als Kommentar.
- Umgekehrt bleibt eine ältere Befundlos-Meldung nach dem nächsten Push
  einfach stehen. «Es gibt eine Befundlos-Meldung» belegt damit gar nichts.

Zwei Anker, in dieser Reihenfolge:

1. **Der Statusbericht.** Seine Zeile `✅ Completed` nennt den geprüften Commit
   und ist das einzige Objekt, das beide Ausgänge gleich behandelt. Stimmt der
   Commit mit dem Head, ist der Head geprüft — geprüft, nicht notwendig sauber:
   Den Ausgang nennt der Bericht nicht.
2. **Fehlt der Bericht**, trägt jedes Codex-Ergebnis seinen Commit selbst — das
   Review-Objekt wie die Befundlos-Meldung, beide als «Reviewed commit». Dann
   das **jüngste** von beiden nehmen und dessen Commit vergleichen; das ältere
   sagt nichts über den Head.

Was in keinem Fall trägt: die blosse Anwesenheit eines Review-Objekts oder
einer Befundlos-Meldung, ohne den Commit darin zu lesen.

**Ist der PR schon geschlossen, wenn der Lauf beginnt, entfällt das Ergebnis.**
Am
30.8.2026 auf `swiss-efv-mcp#68`: «ready for review» um 08:13:31, Merge um
08:13:34, und der dadurch ausgelöste Lauf startete um 08:13:35 — eine Sekunde
*nach* dem Merge. Um 08:14:41 stand `✅ Completed` auf `34021a9`. Ein
Review-Objekt gibt es nicht, eine Befundlos-Meldung auch nicht: Auf einem
geschlossenen PR postet Codex sie nicht mehr.

**Die Überschrift sagte bewusst «beginnt», nicht «endet» — inzwischen ist auch
das andere gemessen.** Zwei Fassungen lang stand hier, ob ein Merge einen
bereits *laufenden* Review unterbricht, habe niemand gemessen. Am 9.9.2026 auf
`#86` ist es passiert: Lauf gestartet um 04:04:31 auf `26e3c55`, Merge um
04:05:16 — der Lauf war 45 Sekunden alt —, und um **04:07:08** stand
`✅ Completed` auf demselben Commit. Der Merge bricht den Lauf also **nicht**
ab; er lief 112 Sekunden über den Merge hinaus zu Ende.

Am Ergebnis ändert das nichts: Weder Review-Objekt noch Befundlos-Meldung
erschienen, `get_reviews` nannte weiter nur den Commit davor. Beide Wege enden
gleich — der Lauf, der nach dem Merge beginnt, und der, den der Merge
überrascht —, aber aus verschiedenen Gründen, und nur der zweite war offen.
Die Vorsicht bleibt dieselbe wie vorher, jetzt für beide Fälle belegt: Wer
mergt, während etwas läuft, verliert das Ergebnis.

**Am 9.9.2026 nachgemessen — und die Antwort ist zum Teil eine andere Frage.**
Auf `#81` liefen zwei Reviews auf demselben Commit `a1f3d9d`:

| Zeit (UTC) | Ereignis |
|---|---|
| 03:17:40 | «@codex review» kommentiert |
| 03:17:53 | Lauf 1 startet, Auslöser «Manual request» |
| 03:17:55 | Statusbericht angelegt, Lauf 1 «Running» |
| 03:19:19 | «ready for review» |
| 03:19:22 | Merge |
| 03:19:25 | Lauf 2 startet, Auslöser «Draft marked ready» |
| 03:19:27 | Bericht editiert: Lauf 2 «Running» — Lauf 1 kommt darin nicht mehr vor |
| 03:20:41 | Bericht editiert: «✅ Completed», Lauf 2, Commit `a1f3d9d` |

Drei Beobachtungen, und die mittlere wiegt am schwersten:

- **Ein geschlossener PR hält den Lauf nicht auf.** Lauf 2 startete drei
  Sekunden *nach* dem Merge und lief bis `✅ Completed` durch. Für die Frage
  von oben gab diese Beobachtung noch nichts her: gemessen ist wieder nur ein
  Lauf, der nach dem Merge *begann*. Was mit Lauf 1 geschah, der zum
  Merge-Zeitpunkt lief, sagt sie gerade nicht — siehe die nächste Zeile.
  Beantwortet wurde die Frage erst auf `#86`, oben im vorigen Abschnitt.
- **Der Statusbericht hält nur den jüngsten Lauf.** Lauf 1 verschwand beim
  ersten Edit spurlos; ob er endete und wie, ist nirgends feststellbar. Der
  Bericht belegt damit «dieser Commit wurde geprüft» — nicht «jeder Lauf auf
  diesem Commit ist ausgewertet». Das ist keine Haarspalterei: derselbe Text
  bekam am 23.8. in 42 Läufen 36-mal einen Befund und 6-mal keinen, zwei Läufe
  auf demselben Commit können also gegenteilig ausgehen.
- **Ein Ergebnis kam keines** — weder Review-Objekt noch Befundlos-Meldung.
  Das bestätigt die Regel oben ein zweites Mal.

**Und die 👀 blieb stehen.** Der auslösende `@codex review`-Kommentar trägt sie
noch, obwohl beide Läufe vorbei sind — anders als auf `#64`, wo sie nach dem
Lauf entfernt wurde. Eine stehengebliebene 👀 belegt also keinen laufenden
Review; sie ist so wenig eine Auskunft wie ihre Abwesenheit.

**Auf `#86` zerfiel sie sogar innerhalb desselben PR in zwei Antworten.**
Während Lauf 3 lief, trug der PR `eyes: 1`; nach `✅ Completed` um 04:07:08
stand dort `total_count: 0` — zurückgenommen, und **ohne** dass ein 👍 an seine
Stelle trat. Der Kommentar, der Lauf 2 ausgelöst hatte, trug seine 👀 zur
selben Zeit unverändert weiter.

**Welche Reaktion zu welchem Lauf gehört, ist daraus aber nicht ablesbar** —
und der Versuch stand hier eine Fassung lang. «Am PR hing sie an Lauf 3, am
Kommentar an Lauf 2» ordnet nach dem *Ort* zu, und genau das widerlegt die
Beobachtung auf `#83` zwei Absätze weiter oben: Dort setzte ein einziger, per
Kommentar ausgelöster Lauf die 👀 an **beide** Stellen. Auf `#86` überlappten
Lauf 2 und Lauf 3; Lauf 2 allein kann also beide Reaktionen erklären. Ein
Codex-Review hat den Fehlschluss gefunden, und er ist derselbe, den derselbe
Abschnitt zwei Absätze vorher benennt.

Übrig bleibt die Beobachtung ohne die Zuordnung, und die genügt für den
Handgriff: **Nach `✅ Completed` war die eine Stelle geräumt und die andere
nicht.** Wer nur eine von beiden abfragt, bekommt je nach Wahl «läuft noch»
oder «nichts läuft» — über denselben PR, in derselben Sekunde. Beide lesen,
keiner von beiden mehr abgewinnen als das.

Dass eine 👀 gerade dort stehenblieb, wo ein Lauf aus dem Bericht verschwand,
sieht auf `#81` und `#86` gleich aus, ist aber dieselbe Zuordnung noch einmal:
Sie unterstellt, dass die stehengebliebene Reaktion dem verschwundenen Lauf
gehört. Als Vermutung notiert, nicht als Handgriff.

**Und ein ausbleibendes 👍 ist kein Befund-Indiz.** Auf `#64` fiel die
Rücknahme ohne 👍 mit einem Befund zusammen; auf `#86` mit einem Lauf, dessen
Ergebnis mangels offenem PR gar nicht gepostet werden konnte. Dieselbe
Beobachtung, zwei unvereinbare Ursachen — sie trennt die Fälle nicht.

Die 👍 am PR (`+1: 1`) trägt hier nichts — und, anders als hier zwei Fassungen
lang stand, auch auf `#68` nicht: Jene Ausnahme ist weiter unten zurückgenommen.
`reactions` bleibt eine Summe ohne Urheber, und selbst wenn die Reaktion von
Codex stammte, sagt sie nicht, welchem der beiden Läufe sie gälte.

**Der Übergang selbst ist inzwischen beobachtet — er trägt aber keine
Zuordnung.** Auf `#82` stand am PR zum Merge-Zeitpunkt `eyes: 1`; um
**03:30:14** wechselte er auf `+1: 1`, und der Statusbericht ging in
**derselben Sekunde** auf `✅ Completed`.

Daraus wurde hier eine Fassung lang ein Kriterium gemacht: Wechsel
sekundengleich mit dem Bericht-Edit *und* kein menschlicher Eingriff dazwischen
— dann gehöre die Reaktion diesem Lauf. **Das ist ein Zirkelschluss**, und ein
Codex-Review hat ihn benannt, vier Sekunden bevor der PR mit ihm gemergt wurde.
Die zweite Bedingung ist aus diesen Daten nicht feststellbar: Eine 👍 von Hand
*ist* der Eingriff, den sie ausschliessen soll, und sie erzeugt in der Summe
denselben Übergang — auch auf die Sekunde genau. Wer so zuordnet, kann einem
Lauf ein sauberes Ergebnis zuschreiben, das ein Mensch gesetzt hat.

Zuordnen liesse sich die Reaktion nur über Urheberdaten, und die liefert hier
kein Werkzeug: `/issues/{n}/reactions` ist aus den Agent-Sessions gesperrt,
`reactions` bleibt eine Summe. Die Koinzidenz der Zeitstempel steht deshalb nur
noch als Indiz da — mit dem Vermerk, warum sie nicht trägt.

**Auch «der jüngste Lauf war sauber» stimmt nicht.** Reaktionen an
verschiedenen Stellen überschreiben einander nicht: Auf `#82` überlebte die
Kommentar-Reaktion den später gestarteten PR-getriggerten Lauf. Zwei Stellen
können also gleichzeitig Gegensätzliches anzeigen, und die jüngere räumt die
ältere nicht weg.

Hier stand daraus die Folgerung, die Reaktion gelte dem jüngsten Lauf «ihres
eigenen Auslöser-Objekts». **Das ist dieselbe Zuordnung nach dem Ort, die der
Absatz gleich darunter widerlegt** — ein Lauf kann beide Stellen anfassen, also
sagt die Stelle nicht, welcher Lauf sie gesetzt hat. Was bleibt, ist die
Verneinung ohne den Ersatz: «der jüngste Lauf» stimmt nicht, und ein anderer
Lauf lässt sich der Reaktion auch nicht zuweisen.

**Und sie sitzt nicht nur an einer Stelle.** Am 9.9.2026 um 03:37 trug `#83`
während eines einzigen, per Kommentar ausgelösten Laufs `eyes: 1` **sowohl** am
auslösenden Kommentar **als auch** am PR. Die frühere Fassung — «beim
ready-Auslöser am PR, beim Kommentar-Auslöser am Kommentar» — stammt aus einer
Beobachtung, die nur eine der beiden Stellen abfragte. Dieselbe Falle wie
damals bei den Kommentaren, nur andersherum, und sie hat hier zwei Fassungen
überlebt.

Also beide Stellen lesen — und keiner von beiden irgendetwas abgewinnen. Hier
stand einmal «wenigstens: hier lief etwas»; auch das ist zu viel, denn eine
Reaktion von Hand belegt keinen Lauf, und ob eine von Hand kam, sagt die Summe
nicht. Die ausführliche Rücknahme steht weiter unten bei der Beweisregel.

**Das Muster ist viermal in Folge aufgetreten, an jedem PR dieser Serie, bei
dem nicht gewartet wurde.** Jedes Mal derselbe Ablauf: ein Lauf per
`@codex review` angestossen, dann «ready», dann binnen zwei bis fünf Sekunden
der Merge, dann ein zweiter Lauf aus dem ready-Auslöser — und der Bericht, der
nur den jüngsten hält, überschrieb den ersten.

| PR | Lauf 1 | ready | Merge | Lauf 2 | Bericht überschrieben |
|---|---|---|---|---|---|
| `#81` | 03:17:53 | 03:19:19 | 03:19:22 | 03:19:25 | 03:19:27 |
| `#82` | 03:26:13 | 03:28:50 | 03:28:52 | 03:28:54 | 03:28:56 |
| `#84` | 03:41:41 | 03:43:04 | 03:43:08 | 03:43:11 | 03:43:14 |
| `#85` | 03:48:15 | 03:49:35 | 03:49:40 | 03:49:42 | 03:49:43 |

Was das kostet, ist an `#83` abzulesen: Dort meldete Codex zwei P2-Befunde —
darunter einen Zirkelschluss im Text selbst — **vier Sekunden bevor** der PR mit
ihnen gemergt wurde. Beide waren richtig, beide mussten in einem Folge-PR
nachgezogen werden. Der Review hatte gearbeitet; nur hingesehen hatte niemand
mehr.

**Und auf `#84` griff die Regel von oben zum ersten Mal.** Der Bericht stand auf
`✅ Completed` für `3842efe`, die 👍 kam eine Sekunde später — nach der alten
Fassung hätte das «Lauf sauber» geheissen. Feststellbar ist es nicht: kein
Review-Objekt, keine Befundlos-Meldung (der PR war seit 92 Sekunden zu), und die
Reaktion trennt Codex nicht von einem Menschen. Beide Läufe auf `3842efe` sind
damit *geprüft, Ausgang offen* — und das ist die richtige Auskunft, nicht die
bequeme.

**Ein eigener PR dafür genügt nicht.** `#85` wurde genau zu dem Zweck geöffnet,
einen feststellbaren Ausgang zu bekommen, und trug die Bitte zu warten im
eigenen Text. Er wurde fünf Sekunden nach «ready» gemergt; Lauf 2 begann zwei
Sekunden danach und endete um 03:50:54 wieder mit `✅ Completed` und ohne
Ergebnis. Der Versuch, das Problem durch einen weiteren PR zu lösen, reproduziert
es also bloss.

Praktisch folgt daraus nur eines, und es steht schon oben: Den Draft von Hand
prüfen lassen **und das Ergebnis abwarten**, bevor man auf ready stellt.

**Was «abwarten» heisst, hat sechs Fassungen und sechs Codex-Befunde
gebraucht** — und die ersten fünf sind an derselben Sache gescheitert.
Nacheinander stand hier: eine Frist von zwei Minuten; «bis der Bericht nicht
mehr ‹Running› sagt»; «Ergebnisobjekt **oder** eine Ausfallmeldung»;
«Ergebnisobjekt zum aktuellen Head»; «Ergebnis, entstanden nach dem eigenen
Auslöser». Jede war enger als die vorige, und jede versuchte dasselbe: **einem
Ergebnis anzusehen, zu welchem Lauf es gehört.**

**Das gibt der Mechanismus nicht her.** Der Bericht hält nur den jüngsten Lauf;
das Ergebnisobjekt nennt den Commit und nicht den Lauf; Läufe können sich
überlappen und auf demselben Commit gegensätzlich urteilen. Bei zwei
gleichzeitigen Läufen kann ein Ergebnis, das nach dem eigenen Auslöser
erscheint, vom anderen stammen — und ist der eigene Lauf aus dem Bericht
verdrängt, sieht das genauso aus, als hätte er nie begonnen.

Die Regel muss deshalb dort ansetzen, wo man noch etwas in der Hand hat, und
das ist nicht die Auswertung, sondern die **Voraussetzung**:

> **Immer nur ein Lauf offen.** Keinen zweiten `@codex review` anstossen,
> solange einer läuft; nicht auf ready stellen und nicht mergen, solange einer
> läuft. Erst das Ergebnis, dann der nächste Schritt.

Ist das eingehalten, ist die Zuordnung eindeutig, und der Bericht sagt, wo man
steht:

- **`🔄 Running`** — weiterwarten, egal was sonst im PR erscheint. Auch eine
  Ausfallmeldung ändert daran nichts: Auf `#76` stand die Environment-Meldung
  in **derselben Sekunde**, in der ein Review anlief, auf `#87` zwanzig
  Sekunden davor.
- **`✅ Completed` für den eigenen Lauf, und ein Ergebnis ist da, das nach dem
  eigenen Auslöser entstanden ist** — fertig. Der Zusatz ist nötig, auch wenn
  die Voraussetzung eingehalten ist: Auf demselben Head kann das Ergebnis eines
  **früheren, abgeschlossenen** Laufs stehen, und das erfüllt «ein Ergebnis ist
  da», ohne über den neuen Lauf etwas zu sagen — der gegenteilig urteilen kann.
  Die Voraussetzung schliesst Überlappung aus, nicht Vorgeschichte.
  In allen acht Läufen an offenen PRs, bei denen beides ablesbar war, stand das
  Ergebnis sogar schon vor dem Wechsel da: **zwei bis drei Sekunden** davor.
- **Der eigene Lauf stand im Bericht und ist daraus verschwunden** — dann war
  die Voraussetzung verletzt, ein zweiter Lauf hat ihn verdrängt. Sein Ausgang
  ist nicht mehr feststellbar und wird es auch nicht mehr.

**Zwei Zustände bleiben offen, und beide haben dieselbe Form: Es ist nichts
da.** `✅ Completed`, aber kein Ergebnis. Oder eine Ausfallmeldung, aber im
Bericht noch kein Lauf zum eigenen Auslöser. In beiden Fällen ist die Frage
dieselbe — kommt noch etwas? —, und **beantworten lässt sie sich nicht.**

Der Versuch, sie über eine Wartezeit zu beantworten, ist genau der Fehler, den
dieser Abschnitt sechs Fassungen lang gemacht hat. Was die Messungen dazu
hergeben, sind Anhaltspunkte und keine Schranken: Ein Ergebnis, das nach
`✅ Completed` kam, wurde nie beobachtet — und «Completed ohne Ergebnis» an
einem **offenen** PR mit nur einem Lauf auch nicht. Am geschlossenen PR ist
dieser Zustand dagegen bekannt und terminal: `#68` und Lauf 3 auf `#86` sind
oben beschrieben, dort kommt nichts mehr. Der Fall, um den es hier geht, ist
also allein der offene PR. Und zwischen Environment-Meldung und Start des Laufs
lagen 0 Sekunden (`#76`) sowie 20 und 21 Sekunden (`#87`, 9.9.2026, zweimal
nacheinander). Wer daraus eine Frist macht, hat sie erfunden.

Praktisch folgt daraus nicht «länger warten», sondern:

- **Aus dem Nichts nichts schliessen.** «Es steht nichts da» ist nie «sauber»
  und nie «gescheitert». Auf ready stellen oder mergen ist in beiden Zuständen
  falsch — dieselbe Regel wie beim 403 weiter oben: Entscheidend ist nicht,
  was fehlt, sondern ob die Quelle geantwortet hat.
- **Nicht sofort wiederholen.** Ein zweiter Auslöser im Zwischenzustand erzeugt
  genau die Überlappung, die die Voraussetzung verhindern soll — und macht den
  eigenen Ausgang unfeststellbar. Auf `#87` wäre das zweimal passiert: Beide
  Male stand die Environment-Meldung da, beide Male kam der Lauf gut zwanzig
  Sekunden später doch.
- **Bleibt es dabei, hilft nur ein neuer Lauf** — und **er ist nicht sicher.**
  Hier stand «abwarten, bis im Bericht nichts mehr läuft, dann einen Lauf
  anstossen». Das ist im gefährlichsten Fall sofort erfüllt: Wenn der eigene
  Lauf verzögert startet, steht im Bericht ja gerade noch nichts. Wer dann
  anstösst, erzeugt genau die Überlappung, die er vermeiden wollte.

**Ein garantiert sauberer Neustart ist nicht feststellbar.** Das ist keine
Lücke dieser Notiz, sondern eine Eigenschaft des Mechanismus: Der Bericht zeigt
nur den jüngsten Lauf, und ein noch nicht erschienener Lauf sieht aus wie
keiner. Wer aus diesem Zustand herauswill, wählt zwischen zwei Risiken —
weiterwarten auf ein Ergebnis, das vielleicht nie kommt, oder anstossen und
den eigenen Ausgang vielleicht verdrängen. Beides bewusst wählen, keines für
den sicheren Weg halten.

Genau deshalb steht die **Voraussetzung** oben und nicht die Auswertung: Sie
ist das Einzige, was diesen Zustand vermeidet. Ist sie eingehalten, kommt man
kaum hinein; ist sie verletzt, führt kein Lesen und keine Regel zuverlässig
heraus.

**Und die Ausfallmeldung ist nicht zuverlässig ein Issue-Kommentar.** Weiter
unten steht, die beiden Ausfallmeldungen seien gewöhnliche Issue-Kommentare;
am 9.9.2026 kam die Environment-Meldung auf `#87` als **Review-Kommentar in
einem Thread**. Wer sie nur mit `get_comments` sucht, findet sie dort nicht —
und der Kommentarzähler bewegt sich nicht.

Eine Frist taugt dafür ohnehin nicht: Die siebzehn Läufe mit ablesbarem Anfang
und Ende brauchten zwischen 103 und 316 Sekunden.

Aus der Tabelle oben folgt das allerdings nicht: In allen vier Fällen fehlte
die Pause, es gibt dort also keine Variation, aus der sich eine Ursache
ableiten liesse. Die Variation liefert erst der Absatz darunter — und auch der
nur einmal je Zweig.

**Die Gegenprobe ist versucht worden — und sie hat nicht gemessen, was sie
messen sollte.** Auf `#86`, dem PR, der diesen Absatz einführte:

| Zeit (UTC) | Ereignis | Ausgang |
|---|---|---|
| 03:57:31 | Lauf 1, «Manual request», `009f570` — **gewartet** | 03:59:52 `✅ Completed` **und** Review-Objekt mit zwei Befunden |
| 04:03:29 | Lauf 2, «Manual request», `26e3c55` | verschwand um 04:04:34 aus dem Bericht |
| 04:04:23 | ready gestellt, während Lauf 2 lief | — |
| 04:04:31 | Lauf 3, «Draft marked ready», `26e3c55` | 04:07:08 `✅ Completed`, **kein Ergebnis** |
| 04:05:16 | Merge, 45 s nach Beginn von Lauf 3 | — |

Hier stand, das sei die Variation, die den vier Fällen der Tabelle oben fehle:
gleicher PR, gleiches Repo, einmal mit und einmal ohne Pause, und der
Unterschied im Ausgang genau der erwartete. **Das trägt nicht, und der Grund
steht zwei Abschnitte weiter oben in diesem Dokument.**

Die beiden Zweige unterscheiden sich nicht nur in der Pause: Lauf 1 endete bei
**offenem** PR, Lauf 3 endete 112 Sekunden **nach dem Merge**. Und ein
geschlossener PR unterdrückt das Ergebnis — das ist oben gemessen und in
diesem PR neu aufgeschrieben worden. Der Unterschied «Review-Objekt» gegen
«kein Ergebnis» ist damit **schon vollständig erklärt**, ohne dass die Pause
etwas dazu beitragen müsste.

Eine Gegenprobe, die zwei Grössen zugleich verändert, misst keine von beiden.
Für die Pause bräuchte es zwei Läufe, die **beide bei offenem PR enden** — den
gibt es hier nicht. Was von `#86` bleibt, ist der Mechanismus und nicht die
Messung: ready stellen startet einen zweiten Lauf, der den Bericht überschreibt,
und mergen unterdrückt das Ergebnis. Beides ist einzeln belegt, beides spricht
für die Pause — belegt ist die Pause damit trotzdem nicht.

Aufgefallen ist das einem Codex-Review, in der sechsten Runde auf demselben PR,
in dem der konfundierte Absatz entstand. Fünf Runden lang stand hier eine
Gegenprobe, die keine war, und sie las sich überzeugender als die
Vorsichtsklausel darunter.

Zwei Dinge, die dieser Ablauf zusätzlich trennt:

- **Warten bis zum Ergebnis genügt nicht, wenn danach während des nächsten
  Laufs ready gestellt wird.** Lauf 1 war sauber abgewartet; der Fix danach
  brauchte einen eigenen Lauf, und für den war nach 54 Sekunden ready gestellt.
  Überholt wurde er dadurch aber erst später: Lauf 3 startete nach 62 Sekunden,
  und aus dem Bericht verdrängt war Lauf 2 nach 65. Die Pause gilt jedem Lauf,
  nicht dem PR.
- **Das Überschreiben des Berichts hängt nicht am Merge.** Lauf 3 überschrieb
  Lauf 2 um 04:04:34 — 42 Sekunden **vor** dem Merge, bei offenem PR. In den
  vier Fällen der Tabelle fielen beide immer zusammen; hier sind sie getrennt,
  und die Ursache ist der zweite Lauf.

**Die vorige Fassung dieses Absatzes ist so in `main` gelandet.** Unmittelbar
nach Lauf 1 notierte sie «Kein zweiter Lauf, kein überschriebener Bericht, ein
bindender Ausgang» und wurde drei Minuten später mitgemergt — da lief Lauf 3
bereits. Für Lauf 1 stimmte der Satz; für den PR, der danach zwei weitere Läufe
und einen überschriebenen Bericht bekam, nicht mehr. Ein Vorgang, der noch
läuft, ergibt einen Zwischenstand, und der gehört als solcher aufgeschrieben —
sonst altert er zwischen Commit und Merge.

Übrig bleibt der Statusbericht. Er nennt den geprüften Commit — der Head wurde
also geprüft —, sagt aber nichts über den Ausgang. **Der Ausgang ist damit von aussen
nicht feststellbar**. Eine Ausnahme für `#68` stand hier zwei
Fassungen lang; warum sie gefallen ist, steht gleich darunter.

Naheliegend wäre, ihn aus der 👍-Reaktion am PR zu lesen. Das trägt nicht:

- Das Feld `reactions` aus `issue_read` ist eine **Summe ohne Urheber**. Ein
  Mensch, der die PR-Beschreibung mit 👍 quittiert, erzeugt dasselbe `+1: 1`.
  Zusammen mit `✅ Completed` liesse sich daraus «sauber» ableiten, auch wenn
  Codex einen Befund hatte, der nach dem Merge nicht mehr gepostet wurde.
- Den Urheber nachzuschlagen geht aus den Agent-Sessions nicht: Der
  REST-Endpunkt `/issues/{n}/reactions` ist dort gesperrt, und kein
  MCP-Werkzeug liefert ihn.

**Auf `#68` stand hier eine Ausnahme — sie ist zurückgenommen.** Sie lautete:
Der PR trage `+1: 1` und sonst nichts, ausser Codex habe ihn niemand angefasst,
und der Zeitstempel binde die Reaktion an den Lauf (fertig um 08:14:41, PR
zuletzt verändert um 08:14:44, drei Sekunden). Daraus wurde «jener Lauf hatte
keinen Befund».

Das ist **derselbe Zirkelschluss**, der zwei Abschnitte weiter oben für `#82`
schon einmal aufgeschrieben und verworfen wurde: «Ausser Codex hat ihn niemand
angefasst» ist aus einer Summe ohne Urheber nicht feststellbar — eine 👍 von
Hand hinterlässt genau diese Summe und keine andere Spur. Und der
Sekundenabstand schliesst sie nicht aus, sondern sieht bei ihr gleich aus. Die
Ausnahme hat den Widerruf nur überlebt, weil sie älter war als er und niemand
sie mitgezogen hat; gefunden hat sie ein Codex-Review, das vom Widerruf auf sie
zurückschloss.

**Damit ist der Ausgang eines solchen Laufs von aussen nicht feststellbar** —
auf `#68` so wenig wie sonst. Ein neuer Lauf holt ihn auch nicht zurück: Er
fällt ein eigenes, unabhängiges Urteil — dasselbe Argument wie weiter unten, wo
derselbe Text in 42 Läufen 36-mal einen Befund und 6-mal keinen bekam. Was
bleibt, ist ein Ersatz, keine Rekonstruktion: eine frische Prüfung auf dem
Merge-Commit oder in einem Folge-PR, deren Ergebnis für sich steht.

Ein Statusbericht ohne Ergebnis heisst also «geprüft, Ausgang offen» — offen,
bis etwas anderes ihn bindet, und das ist eine ehrlichere Auskunft als eine
Summe, die zwei Urheber nicht trennt.

**Dieselbe Stelle ist zweimal falsch gewesen, in entgegengesetzte Richtungen.**
Zuerst stand hier «der Ausgang bleibt dauerhaft unbekannt», zwei Zeilen unter
dem Satz, die Reaktion auf `#68` sei eindeutig — ein offener Widerspruch, den
ein Codex-Review fand. Aufgelöst wurde er damals zugunsten der Ausnahme, und
zwar mit einer Abfrage statt mit Nachdenken: `issue_read` auf `#68`.

Die Abfrage war richtig, die Auflösung falsch. Sie hat die Daten geprüft und
nicht den Schluss: Dass `+1: 1` und drei Sekunden Abstand einen Urheber
benennen, folgte aus keiner der Zahlen. **Eine Messung ersetzt kein Argument** —
und wer den Widerspruch stattdessen ohne Abfrage glattzieht, rät bloss zwischen
drei Auflösungen.

Das sind verschiedene Abfragen — `get_reviews` fürs Objekt, `get_comments` für
die Issue-Kommentare, `get_review_comments` für die Kommentare in den Threads;
wer nur eine nimmt, übersieht den Rest. Genau so ist die Limit-Meldung zuerst
durchgerutscht, und genau so wäre die Environment-Meldung vom 9.9.2026
durchgerutscht: Sie stand als Review-Kommentar in einem Thread, wo
`get_comments` sie nicht findet und wo der Kommentarzähler sich nicht bewegt.
«Alles andere» deckt keine der drei ab: Die Reaktion am PR liegt in keiner — sie steht im Feld
`reactions` von `issue_read`, und weil das eine Summe ohne Urheber ist, taugt
sie ohnehin nicht als Beleg (oben, und weiter unten ausführlicher).

Der Kommentarzähler allein reicht ohnehin nicht: `comments: 1` kann die
Befundlos-, die Kontingent- **oder** die Environment-Meldung sein — und seit dem
29.8.2026 auch einen blossen Statusbericht, der überhaupt kein Ergebnis meldet.
Umgekehrt bewegt er sich nicht, wenn eine Ausfallmeldung als Review-Kommentar
kommt. Er zählt also mal zu viel und mal zu wenig:

```
## Codex Review Summary

| Review         | Status                     | Commit    | Review trigger |
| 📝 Code Review | 🔄 Running since 12:02:55  | ca00672   | Manual request |
```

Vier gegensätzliche Bedeutungen unter derselben Zahl. Den Text lesen, nicht die
Zahl. Und einen unbekannten fünften Text wörtlich zitieren, statt ihn in eine
der bekannten Schubladen zu zwingen: Dieser Abschnitt musste schon zweimal
wachsen — von drei auf vier Gründe und dann auf fünf.

Dieser Bericht trägt den HTML-Marker `codex-pull-request-review-summary` und
wird **an Ort und Stelle aktualisiert**, nicht neu geschrieben. Die
Fertigmeldung («✅ Completed») kam deshalb als `issue_comment.edited`: Wer auf
einen *neuen* Kommentar wartet, verpasst sie, und wer den Zähler beobachtet,
sieht gar nichts, weil er sich nicht ändert. Dass «Running» dort steht, heisst
warten, nicht urteilen — ein Lauf ohne Ergebnis ist weder Befund noch Freispruch.

Sein eigentlicher Wert steht in der Spalte daneben: Der Bericht nennt den
geprüften Commit und den Auslöser, beantwortet also genau die Frage, die der
fünfte Grund oben aufwirft.

**Zur 👍-Reaktion: zwei Fassungen lang wurde am falschen Objekt gemessen.**
Hier stand, der Infokasten sei keine Quelle — belegt mit sechs Repos am 23.8., in
denen die Befundlos-Meldung kam «und in keinem die Reaktion». Gesucht wurde an
den Kommentaren. Dort ist nie eine.

Die Reaktion sitzt **am PR**. Am 29.8.2026 auf `swiss-efv-mcp#64` durchgemessen,
an einem PR, den ausser Codex niemand angefasst hatte:

| Zeitpunkt | Zustand des Laufs | Reaktionen am PR |
|---|---|---|
| 16:54:30 | gestartet | `eyes: 1` |
| 16:56:27 | fertig, **mit** Befund | `total_count: 0` — 👀 wieder entfernt |

Und auf `#62` nach einem befundlosen Lauf: `+1: 1` am PR, `0` an jedem der drei
Kommentare. Codex setzt die Reaktion also, nimmt sie zurück und unterscheidet
die Ausgänge — genau wie der Kasten es beschreibt («reacts with 👀 while any
review is running … reacts with 👍 once all reviews finish with no findings»).

Die alte Zeile war damit nicht vorsichtig, sondern **falsch**: Sie hat aus einer
Messung am falschen Ort auf eine Lüge geschlossen. Dass die Reaktion am PR
sitzt, ist damit belegt, und der Kasten ist als Beschreibung nicht widerlegt.

Ein Urheber steht aber auch hier nicht in den Daten: «Ausser Codex hat ihn
niemand angefasst» ist dieselbe unbelegbare Bedingung wie bei `#68`. Das
Auftauchen und Verschwinden im Takt eines Laufs passt zum Kasten, beweist ihn
aber nicht — und als Auskunft über einen einzelnen Lauf bleibt die Reaktion
unbrauchbar.

**«Am PR» ist nicht die einzige Stelle.** Am 30.8.2026 auf
`swiss-procurement-mcp#76` trug der auslösende `@codex review`-Kommentar selbst
`eyes: 1`, während der Lauf ging. Daraus stand hier eine Weile die Regel «beim
ready-Auslöser am PR, beim Kommentar-Auslöser am Kommentar» — **sie ist
widerlegt**: Auf `#83` setzte ein einziger, per Kommentar ausgelöster Lauf die
👀 an beide Stellen (oben, im Abschnitt zu `#81`). Der Ort trennt die Auslöser
also nicht.

Was bleibt, ist der Messfehler, gegen den die Zeile ursprünglich geschrieben
war: Wer nur eine der beiden Stellen abfragt, misst am falschen Objekt.
Beide lesen. Der Vorbehalt aus demselben Abschnitt gilt weiter, und schärfer
als er hier stand: `reactions` ist eine Summe ohne Urheber. «Eindeutig, wenn
ausser Codex niemand den PR angefasst hat» rettet den Fall nicht — dass niemand
ihn angefasst hat, ist aus einer Summe ohne Urheber gerade nicht feststellbar.
Eindeutig wird ein solcher Fall nie.

Das ändert nichts an der Beweisregel, sondern nur an ihrer Begründung: Belegt
ist eine Prüfung durch einen Statusbericht auf `✅ Completed`, ein
Review-Objekt oder eine Befundlos-Meldung, die jeweils den aktuellen Head
nennen. Die Reaktion taugt dafür nicht, und der Grund ist genau der Commit: Sie
nennt keinen.

Auch «der letzte Lauf war sauber» stand hier noch — dieselbe Zuordnung zu einem
Lauf, die der Abschnitt weiter oben zurücknimmt, und die Behauptung, sie werde
beim nächsten Lauf überschrieben, gehört dazu: Auf `#82` überlebte eine
Reaktion einen späteren Lauf an anderer Stelle.

Der Rest, der davon übrigblieb — «irgendwann lief irgendetwas oder lief ohne
Befund durch» —, war **auch schon zu viel**, und ein Codex-Review hat es in der
nächsten Runde benannt. Stammt die Reaktion von einem Menschen, belegt sie
keinen Lauf, sondern gar nichts; und ob sie von einem Menschen stammt, sagt die
Summe nicht. Zwischen «wenigstens lief etwas» und «beweislos» liegt genau der
Schritt, den `reactions` ohne Urheberdaten nicht hergibt.

**Also: Die Reaktion ist kein Beleg — für nichts.** Der Kasten beschreibt, was
Codex mit ihr *tut*, und das mag zutreffen; als Auskunft über einen Lauf, einen
Commit oder einen Ausgang ist sie unbrauchbar, solange der Urheber fehlt.

Das gilt auch im Fall des geschlossenen PR oben, wo sie als einzige Quelle
für den Ausgang übrig zu bleiben scheint: Die Summe im Feld `reactions` trennt
Codex nicht von einem Menschen, und den Urheber liefert hier kein Werkzeug.
Was dort fehlt, holt man mit einem neuen Lauf, nicht mit einer Reaktion.

Und ein befundloser Lauf ist kein Freispruch. Am 23.8. lief derselbe Text durch
42 Reviews: 36 meldeten denselben P2-Befund, 6 die Befundlos-Meldung — gleiche
Eingabe, gegenteiliges Urteil, alles in denselben neun Minuten. Ein sauberer
Lauf sagt damit etwas über den Lauf, nicht über den Text. Wer sein Häkchen
daran hängt, hängt es an einen Münzwurf.

Portfolio-weit nachsehen:

```
search_pull_requests: user:malkreide commenter:chatgpt-codex-connector[bot] updated:>=<Datum>
```

Findet nur, wo er *kommentiert* hat. Repos ohne PR-Aktivität tauchen nicht auf
— das ist kein Beleg, dass dort geprüft wurde.

Zweiter Weg, den Prüfer zu verlieren, ganz ohne Kontingentproblem: zu schnell
mergen. Am 21./22.8. lagen zwischen «ready for review» und Merge mehrfach drei
bis fünf Sekunden. Codex wird beim Umschalten von Draft auf ready ausgelöst und
braucht danach Zeit; wer sofort mergt, hat das Häkchen gesetzt und den Review
nicht abgewartet.

Bei `swiss-procurement-mcp` PR #68 waren es am 29.8. rund zwei Sekunden. Die
Eile kostete dort nichts, weil die Absage in dieselbe Sekunde fiel wie der
Merge — die Ausfallmeldung kommt binnen Sekunden, ein Review nicht.

**Wie lange ein Review braucht, ist seit dem Statusbericht direkt messbar.** Er
nennt Start und Ende; vorher liess sich nur die Dauer eines ganzen Stapels
ablesen, und die 42 Reviews vom 23.8. über neun Minuten sind kein Wert für einen
einzelnen Lauf. Auf `swiss-procurement-mcp#75` am 30.8.: **103 s**
(09:09:18 → 09:11:01) und **111 s** (09:14:48 → 09:16:39). Auf `#86` am 9.9.:
**141 s** (03:57:31 → 03:59:52) und **157 s** (04:04:31 → 04:07:08); auf `#87`
am selben Tag **169 s** (04:12:00 → 04:14:49), **216 s**
(04:17:33 → 04:21:09), **235 s** (04:23:26 → 04:27:21), **316 s**
(04:30:14 → 04:35:30), **177 s** (04:39:16 → 04:42:13), **259 s**
(04:43:46 → 04:48:05), **209 s** (04:50:45 → 04:54:14) und **228 s**
(04:56:27 → 05:00:15), noch einmal **228 s** (05:02:15 → 05:06:03) und
**218 s** (05:08:30 → 05:12:08), **186 s** (05:14:46 → 05:17:52) und **279 s**
(05:19:28 → 05:24:07) und **223 s** (05:26:05 → 05:29:48).

Siebzehn Läufe sind keine Verteilung, und eine Wartezeit lässt sich daraus nicht
ableiten. Sie reichen aber, um eine Faustregel zu widerlegen: «rund zwei
Minuten» deckt 316 s nicht mehr. Wer zwei Minuten absässe und dann ready
stellte, träfe einen solchen Lauf mitten hinein.

**Auf `#86` ist das nicht passiert, und der Unterschied gehört dazu.** Dort war
schon nach 54 Sekunden ready gestellt — von zwei Minuten Warten kann keine Rede
sein. Belegt ist über die Faustregel deshalb nur das Schwächere: Eine Frist von
zwei Minuten wäre bei jenem 157-Sekunden-Lauf **auch** zu kurz gewesen. Das
genügt, um sie fallenzulassen, und mehr trägt die Beobachtung nicht.

Acht Messungen lang hat **jede neue den Höchstwert angehoben** — 103, 111, 141,
157, 169, 216, 235, 316. Hier stand deshalb, das sei bemerkenswert. Die neunte
lag bei **177 s** und beendete die Reihe.

Das ist die Lehre in Kurzform: Eine Reihe von acht war lang genug, um wie ein
Muster auszusehen, und die neunte Messung hat sie gebrochen. Über die
Verteilung dahinter sagte sie ohnehin nichts — wer aus ihr eine Obergrenze
gebildet hätte, hätte sie erfunden, und genau deshalb taugt keine Frist.

Nicht auf die Uhr sehen, sondern auf den Bericht: Solange dort «Running» steht,
ist nichts entschieden — und wenn er fertig ist, entscheidet das Ergebnisobjekt
und nicht der Bericht. Als Handgriff taugt weiter nur die schwache Richtung: Ein
Kommentar, der binnen Sekunden dasteht, ist eher eine Absage als ein Urteil.
Entschieden wird am Text, nicht an der Uhr.

Das Kontingent hängt am Konto, nicht am Repo, und Code-Reviews haben einen
eigenen Topf — nur GitHub-getriggerte Reviews zählen hinein. ChatGPT-Pläne
fahren ein rollendes Fünf-Stunden-Fenster plus Wochenlimits; welches greift,
steht im Codex-Dashboard. Welches hier griff, ist **offen**. Die Lücke oben
schliesst das Fünf-Stunden-Fenster nicht aus: Es kann sich zwischendurch
geöffnet und durch neue Auslöser wieder erschöpft haben. Das auszuschliessen
bräuchte den Nachweis, dass in der ganzen Spanne kein einziger Review durchlief
— den gibt es nicht, weil nur Fehlschläge beobachtet wurden. Eine lange Reihe
von Fehlschlägen belegt eine lange Reihe von Fehlschlägen, nicht ihre Ursache.

Zeigt das Dashboard freies Kontingent, während Reviews weiter scheitern, ist
das ein bekannter Fehler bei mehreren verbundenen Konten — dann den
GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

Die Environment legt man unter `chatgpt.com/codex/cloud/settings/environments`
an, und zwar **je Repo**. Am 23.8. sah es genau danach aus: In
`swiss-public-data-mcp` kam kein Review, in den übrigen Repos lief Codex am
selben Morgen durch. Eine Environment fürs Konto genügt also nicht — wer eine
anlegt und den Rest für erledigt hält, mergt weiter Ungeprüftes.

**Die Meldung selbst ist aber kein Beleg dafür, dass eine fehlt.** Am
29.8.2026 auf `swiss-efv-mcp#66`:

| Zeit (UTC) | Ereignis |
|---|---|
| 16:56, 17:01, 17:05 | drei Codex-Reviews in diesem Repo, alle durchgelaufen |
| 18:38:34 | «To use Codex here, create an environment for this repo» |
| 18:39:34 | nach «@codex review»: Lauf startet normal, auf demselben Commit |
| 18:44:28 | befundlos fertig |

Sechzig Sekunden zwischen der Meldung und einem gelungenen Lauf, dasselbe Repo,
derselbe Commit, an den Einstellungen nichts geändert. Der Text behauptet eine
Konfigurationslücke; belegt ist nur, dass kein Lauf zustande kam.

Das ist dieselbe Klasse wie der 403 weiter oben — eine Störung, als Auskunft
verpackt —, aber mit der **umgekehrten** Handlungsanweisung als beim 400er:

- Beim 400er war die Absage deterministisch und wiederholbar; ein
  Wiederholungsrat wäre dort falsch gewesen, gesucht werden musste der fehlende
  Parameter.
- Hier kann ein Wiederholungslauf einen einmaligen Aussetzer abtrennen, und er
  verlangt keine Konfigurationsänderung. Umsonst ist er deshalb nicht: Er wird
  per Kommentar ausgelöst und zählt damit ins Kontingent wie jeder
  GitHub-getriggerte Lauf — billiger als eine überflüssige Environment, aber
  nicht gratis. **Eher wiederholen als konfigurieren.** Wer der Meldung sofort
  folgt, legt eine Environment an, die es schon gibt, und hält das Problem
  danach für gelöst.

  **Wiederholen heisst aber nicht sofort wiederholen**, und das stand hier eine
  Fassung lang zu einfach. Am 9.9.2026 ging die Meldung auf `#87` zweimal einem
  Lauf voraus, der 20 beziehungsweise 21 Sekunden später doch startete; auf
  `#76` lief er in derselben Sekunde. Wer in diesem Zustand erneut auslöst,
  erzeugt einen zweiten Lauf, der den ersten aus dem Bericht verdrängt — und
  macht dessen Ausgang unfeststellbar. Zuerst also in den Statusbericht sehen,
  ob ein Lauf erschienen ist. Steht dort keiner, ist die Wiederholung eine
  **bewusst riskante Wahl** und kein sicherer Handgriff: Ein Kriterium, das den
  gescheiterten Auslöser vom verzögerten unterscheidet, gibt es nicht (oben, im
  Abschnitt über das Warten).

Wiederholt sich die Meldung, ist sie **stabil** — mehr nicht. Auch das belegt
keine fehlende Environment: Ein Aussetzer, der zwei Anläufe überdauert, sieht
genauso aus. Die Wiederholung sagt, dass sich ein Blick in die Konfiguration
lohnt; entschieden wird dort und nicht an der Meldung.

**Am 30.8.2026 wurde es noch enger.** Auf `swiss-procurement-mcp#76` stand die
Environment-Meldung um 11:47:50 — in **derselben Sekunde**, in der der Review
auf `c7f750b` anlief, ohne Wiederholung und ohne Eingriff. Auf `swiss-efv-mcp`
lagen noch sechzig Sekunden und ein «@codex review» dazwischen, hier gar nichts.
Meldung und laufender Review schliessen sich also nicht einmal zeitlich aus. Wer
die Meldung für eine Auskunft über die Konfiguration hält, liest ein Ereignis,
das im selben Moment widerlegt wird.

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


**ruff: eine Quelle.** Der Pin steht im `dev`-Extra von `pyproject.toml` und
sonst nirgends — auch nicht hier: **diese Datei nennt die Version bewusst
nicht.** Die CI hat keinen eigenen Pin-Schritt, der Install über `ci.yml`
genügt, lokal wie dort. Eine `.pre-commit-config.yaml` gibt es nicht; wenn eine
dazukommt, muss sie dieselbe Version aus `pyproject.toml` beziehen und keine
zweite nennen.

Bis zum 30.8.2026 stand die Version hier ausgeschrieben — und war nach einem
Dependabot-Bump still falsch, unter der Überschrift «eine Quelle». Kein Gate
merkte es: `check_ruff_pin.py` liest `pyproject.toml`, nicht die Prosa, und
nennt jene im eigenen Docstring die «einzige Quelle». Eine ausgeschriebene
Version in dieser Datei ist deshalb keine Bequemlichkeit, sondern die zweite
Quelle. `tests/test_ruff_pin_doc.py` fängt sie ab.

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
