# tablefmt

Ein CSV-zu-Text-Tabellenformatierer mit einer wiederverwendbaren Go-Bibliothek.
Die vollständige Aufgabenbeschreibung steht in [`TASK.md`](TASK.md).

```text
main.go                 zu implementierende CLI (Stub)
main_test.go            öffentliche CLI-Smoke-Tests, schreibgeschützt
table/table.go          zu implementierende Bibliothek (Stub)
table/table_test.go     öffentliche Bibliotheks-Smoke-Tests, schreibgeschützt
```

Die öffentlichen Tests laufen ohne Netzwerk und ohne externe Abhängigkeiten:

```sh
go test -count=1 ./table
go test -count=1 .
go test -count=1 ./...
```

Go 1.21 oder neuer ist erforderlich. Keine `require`-Direktiven, kein
`go get`; die Standardbibliothek genügt.
