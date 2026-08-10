# logrotate-audit

Ein Offline-Auditor für rotierende Logdateien. Die vollständige Spezifikation
steht in [`TASK.md`](TASK.md).

```text
logrotate-audit.sh    zu implementierendes Bash-Programm (Stub)
tests/run.sh          öffentliche Smoke-Tests, schreibgeschützt
```

Tests vom Repository-Wurzelverzeichnis des Seeds starten:

```sh
bash tests/run.sh
bash -n logrotate-audit.sh tests/run.sh
```

Es sind keine Netzwerkzugriffe oder zusätzlichen Abhängigkeiten erlaubt.
