# Holdout-Bewertung

Die öffentliche Suite in diesem Repo ist bewusst nur ein **Smoke-Test**.
Die belastbare Bewertung passiert gegen ein separates, **nicht versioniertes
Holdout-Paket**.

## Warum

Ein Agent, der dieses Repo (oder die Run-Branches) lesen kann, würde sonst
die öffentlichen Testeingaben sehen und sich darauf spezialisieren. Holdout
+ öffentliche Smoke-Tests bilden zusammen die Bewertung: Die sichtbaren Tests
geben dem Agenten ein Ziel, die Holdout-Tests prüfen, ob die Spezifikation
*wirklich* implementiert wurde — auch auf Eingaben, die der Agent nie
gesehen hat.

## Was das Holdout-Paket enthält

Für jede Task zusätzliche Testfälle zur **gleichen Spezifikation**
(`tasks/<id>/README.md`):

- **go-cronparse:** weitere Ranges/Steps/Name-Mappings, Makros, DST- und
  Mitternachts-Grenzfälle in `Next()`
- **go-tablefmt:** Truncation-Ränder (MaxWidth 1), Zentrierung, ragged rows,
  `\|`-Escaping, Delimiter `\t`, ungültige Flags
- **py-semver:** Precedence-Ketten mit Pre-Release/Build, `~`/`^`-Ränder,
  `||`-Priorität, `max_satisfying` mit leeren Mengen
- **py-logstats:** malformed Lines, leere Eingaben, `top`-Begrenzung,
  JSON-Ausgabe-Determinismus
- **sh-logrotate-audit:** mehrere Policy-Einträge, Symlinks, zukünftige
  mtimes, Owner mit Gruppe und fehlerhafte Policy-Zeilen

## Ablauf

1. **Agent läuft** gegen das öffentliche Repo (frische Worktrees, nur
   Smoke-Tests sichtbar).
2. **Run-Branch** wird gepusht (siehe README).
3. **Externer Bewerter** (z. B. der Hermes-Agent im privaten Setup) zieht den
   Branch, spielt das Holdout-Paket in die Workspaces ein und wertet aus:
   Suite-Ergebnisse, Diff-Qualität, Transcript-Verhalten (Tool-Nutzung,
   Doom-Loops, Effizienz).

## Regeln

- Holdout-Dateien **niemals** in dieses Repo committen (`.gitignore` sperrt
  `holdout/`, `**/holdout_*`, `**/*.holdout.*` etc.).
- Die Bewertung wird pro Run-Branch dokumentiert (z. B. Kommentar oder
  `HOLDOUT.md` auf dem Branch), damit jede Behauptung nachprüfbar ist.
- Der Holdout selbst gehört in einen privaten Ort, auf den nur der Bewerter
  Zugriff hat.
