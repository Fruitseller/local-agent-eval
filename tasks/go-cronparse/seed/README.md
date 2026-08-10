# cronparse

A parser and evaluator for classic five-field cron expressions.

**The full specification is in [`TASK.md`](TASK.md).** This file only
describes the layout of the repository.

```
go.mod               module cronparse (no dependencies)
cron.go              the package you implement (stub)
parse_test.go        public smoke tests - read-only
schedule_test.go     public smoke tests - read-only
```

## Running the tests

```sh
go test -count=1 -run '^TestParse'    ./...
go test -count=1 -run '^TestSchedule' ./...

go test ./...          # both at once, while you work
go vet ./...
```

The module has no dependencies and must keep it that way: standard library
only, no `go get`, no network.
