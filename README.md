# local-agent-eval

Dieses öffentliche Repository ist eine kleine, reproduzierbare Benchmark-Suite
für lokale Coding-Agenten. Fünf absichtlich unvollständige Seeds messen
Python-, Go- und Shell-Arbeit: SemVer, Logstatistiken, Cron-Auswertung,
Tabellenformatierung und ein Logrotate-Audit. Der Harness gibt jedem Lauf ein
frisches Git-Repository, denselben Prompt und ein hartes Zeitbudget von
**20 Minuten (1200 Sekunden) pro Aufgabe**.

## Faire Modellvergleiche

Vergleiche benötigen denselben Commit, dieselben öffentlichen Tasks, Hardware,
Toolchain, Agent-Version und Agent-Flags. Nutze identische Kontext- und
Ausgabelimits, ändere das Zeitbudget nicht und wiederhole Läufe bei Bedarf mit
`--repeat`. Der Harness isoliert Pi-Konfiguration und Benutzerdateien, schützt
öffentliche Tests vor Änderungen und protokolliert Laufzeit, Diff, Test-Suites,
Token/Kosten (wenn Pi sie meldet) und Timeouts.

## Konfiguration und Start

Voraussetzungen sind Python 3.9+, Go 1.21+, Bash, Git und ein installierter
Coding-Agent. `pi` ist der Standard. Für lokale OpenAI-kompatible Endpunkte
kann die konkrete Invocation über `PI_COMMAND` frei gesetzt werden; der Prompt
liegt auf stdin, zusätzlich stehen `{prompt_file}`, `{workspace}`, `{model}`,
`{provider}` und `{base_url}` als Platzhalter bereit.

```sh
cp config.example config.local
# config.local an Endpoint, Modell und PI_COMMAND anpassen

python3 harness/run.py --list
python3 harness/run.py --all --env-file config.local --label mein-modell
python3 harness/run.py --task go-tablefmt --env-file config.local --label mein-modell
python3 harness/run.py --all --env-file config.local --label mein-modell --repeat 3
```

Ein direktes Beispiel ohne Konfigurationsdatei:

```sh
PI_BASE_URL=http://127.0.0.1:8000/v1 \
PI_API_KEY=local PI_PROVIDER=local PI_MODEL=my-model \
PI_COMMAND='pi -p --mode json --provider {provider} --model {model}' \
python3 harness/run.py --all --label my-model
```

Repository und öffentliche Tests lassen sich so prüfen; der Baseline-Lauf
führt alle Testkommandos gegen die absichtlich ungelösten Seeds aus:

```sh
make check
make test
python3 harness/run.py --baseline --all --run-id baseline
```

## Ergebnisse und Holdout-Protokoll

Läufe landen unter `results/<run-id>/`: `summary.json`/`summary.md` enthalten
den Gesamtstand, pro Task gibt es Ergebnis, Logs, Agent-Transkript, Diff und
optional den Workspace. `results/` wird nicht versioniert.

`main` enthält ausschließlich Spezifikationen, Seeds und öffentliche
Smoke-Tests. Verdeckte Holdout-Tests und Referenzlösungen bleiben in einem
separaten privaten Repository und werden erst nach Abschluss eines Laufs auf
dessen unveränderten Diff angewandt. Sie dürfen weder in Git noch in
`.holdout/` dieses öffentlichen Arbeitsbaums abgelegt werden. Veröffentlichte
Vergleiche nennen Benchmark-Commit, Modell/Endpoint, Agent-Version, Hardware,
Konfiguration, Wiederholungszahl sowie öffentlichen und externen
Holdout-Score getrennt.
