# Task: `cronparse` — cron expressions and next run times

Implement the Go package `cronparse`: parse classic five-field cron
expressions and answer two questions about them — does a given time match,
and what is the next matching time?

Go 1.21+, **standard library only**. Do not add a `require` directive, do not
run `go get`, do not access the network. The grading environment is offline.

`parse_test.go` and `schedule_test.go` are read-only; the graders restore
them from the pristine seed before scoring.

---

## 1. Expression syntax

Five fields, separated by one or more spaces or tabs. Leading and trailing
whitespace is ignored.

```
┌─ minute        0-59
│ ┌─ hour        0-23
│ │ ┌─ day of month  1-31
│ │ │ ┌─ month       1-12  or JAN..DEC
│ │ │ │ ┌─ day of week 0-7 or SUN..SAT   (0 and 7 both mean Sunday)
│ │ │ │ │
* * * * *
```

Each field is a comma-separated list of one or more **terms**:

| Term | Meaning |
|---|---|
| `*` | every value of the field |
| `v` | the single value `v` |
| `a-b` | every value from `a` to `b`, inclusive |
| `*/n` | every `n`-th value over the whole field range |
| `a-b/n` | every `n`-th value from `a` to `b` |

* Month names (`JAN`, `FEB`, …, `DEC`) and day names (`SUN`, `MON`, …, `SAT`)
  are accepted in their fields, case-insensitively, including inside ranges
  (`MON-FRI`, `jan-mar`). They are never accepted in the other three fields.
* A step `n` must be `>= 1`. A step is only allowed after `*` or after a
  range: `5/15` is invalid.
* A range must not be reversed: `5-1` is invalid. `5-5` is valid.

### Macros

Instead of five fields the expression may be a single macro,
case-insensitively:

| Macro | Expands to |
|---|---|
| `@yearly`, `@annually` | `0 0 1 1 *` |
| `@monthly` | `0 0 1 * *` |
| `@weekly` | `0 0 * * 0` |
| `@daily`, `@midnight` | `0 0 * * *` |
| `@hourly` | `0 * * * *` |

Any other `@`-expression (including `@reboot`) is an error.

## 2. Package API

Package `cronparse`, module `cronparse`, all in the repository root.

```go
type Schedule struct { /* unexported fields, your choice */ }

func Parse(spec string) (*Schedule, error)
func (s *Schedule) Matches(t time.Time) bool
func (s *Schedule) Next(after time.Time) (time.Time, error)
func (s *Schedule) String() string
```

### `Parse`

Returns a `*Schedule` and a `nil` error for a valid expression. For an
invalid one it returns `nil` and a non-nil error: wrong number of fields, a
value outside the field range, an unknown name, a reversed range, a step
below 1, an empty list item (`1,,2`), or an unknown macro. The error text is
not graded; it should name the offending field.

### `String`

Returns the expression the schedule was parsed from, with macros expanded to
their five-field form and every run of whitespace collapsed to a single
space. The terms themselves are reproduced verbatim, in the order and
spelling they were written:

```go
Parse("@daily").String()            // "0 0 * * *"
Parse("  5,1\t0-2 * * MON ").String() // "5,1 0-2 * * MON"
```

### `Matches`

Reports whether `t` matches the schedule. Only minute, hour, day, month and
weekday are considered; seconds and nanoseconds are ignored. The time is
interpreted in its own location.

**Day rule (this is the classic Vixie cron behaviour):** when *both* the day
of month and the day of week field are restricted (neither is `*`), a day
matches when **either** of them matches. When only one of the two is
restricted, that one alone decides.

### `Next`

Returns the earliest time **strictly after** `after` that matches the
schedule, with seconds and nanoseconds set to zero, in `after`'s location.

If no matching time exists within **five years** after `after`, it returns
the zero `time.Time` and a non-nil error. `0 0 30 2 *` is the canonical
example; `0 0 29 2 *` on the other hand resolves to the next leap year.

`Next` must not mutate the schedule, and must be safe to call repeatedly.
Public and hidden tests only use `time.UTC`.

## 3. Public tests

```
go test -count=1 -run '^TestParse'    ./...
go test -count=1 -run '^TestSchedule' ./...
```

Both suites must pass. Hidden tests check the same specification on further
edge cases — step arithmetic, name ranges, the day rule and month or year
rollovers.

Keep every exported name and signature of section 2 exactly as specified;
they are called directly by the graders. Unexported helpers are yours to
choose.
