# Task: `logstats` — statistics over structured application logs

Implement `logstats.py`, a command line tool **and** importable module that
reads a line-oriented log format, filters it, and prints a report.

Python 3.9+, **standard library only**. Do not add files outside this
repository, do not install anything, do not access the network.

Everything under `tests/` is read-only. The graders restore it from the
pristine seed before scoring.

---

## 1. The log format

One entry per line, fields separated by one or more spaces or tabs:

```
<timestamp> <LEVEL> <component> <message...>
```

* `<timestamp>` — exactly `YYYY-MM-DDTHH:MM:SSZ` (UTC, no fractional seconds,
  no offset). It must be a real calendar date and time
  (`2026-02-30T00:00:00Z` and `2026-01-01T25:00:00Z` are **not** valid).
* `<LEVEL>` — one of `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`, uppercase.
* `<component>` — a non-empty token without whitespace.
* `<message...>` — the rest of the line; may be empty. Leading and trailing
  whitespace is stripped. Interior whitespace is preserved verbatim.

Example:

```
2026-02-01T08:15:30Z ERROR auth   login failed for user alice
```

A line that does not match these rules is **malformed**: it is counted but
otherwise ignored. A line that is empty or contains only whitespace is
**ignored entirely** — it is neither an entry nor malformed.

## 2. Module API

`logstats.py` must live in the repository root and expose exactly these names.

### `LEVELS`

Tuple of the five level names in **ascending severity**:

```python
("DEBUG", "INFO", "WARN", "ERROR", "FATAL")
```

### `parse_line(line)`

Returns a `dict` for a valid entry, `None` for a malformed or blank line:

```python
{"timestamp": "2026-02-01T08:15:30Z", "level": "ERROR",
 "component": "auth", "message": "login failed for user alice"}
```

The trailing newline of a line read from a file must be tolerated.

### `build_report(entries, malformed, top=None)`

`entries` is an iterable of dicts as returned by `parse_line` (already
filtered by the caller), `malformed` an integer. Returns:

```python
{
  "entries": 12,                       # number of entries passed in
  "malformed": 3,                      # passed through unchanged
  "first": "2026-02-01T08:00:00Z",     # smallest timestamp, None if no entries
  "last":  "2026-02-01T09:30:00Z",     # largest timestamp,  None if no entries
  "levels": {"INFO": 8, "ERROR": 4},   # only levels with a count > 0
  "components": [                      # see ordering below
      {"name": "auth", "count": 7},
      {"name": "db",   "count": 5},
  ],
}
```

* Timestamps in this format sort correctly as plain strings; `first`/`last`
  are the minimum and maximum over the given entries, **not** over the input
  file.
* `components` is sorted by `count` **descending**, ties broken by `name`
  **ascending**.
* `top` truncates `components` to the first `top` items. `None` (or a value
  larger than the number of components) keeps all of them. `top` never
  affects `levels`, `entries` or any other field.

### `render_text(report)`

Returns the text report as a single string ending in `"\n"`. Exactly one
`key=value` line per fact, in this order:

```
entries=12
malformed=3
first=2026-02-01T08:00:00Z
last=2026-02-01T09:30:00Z
level.INFO=8
level.ERROR=4
component.auth=7
component.db=5
```

* `first=` and `last=` are **omitted** when the value is `None`.
* `level.*` lines appear in ascending severity order (`LEVELS` order), only
  for levels present in `report["levels"]`.
* `component.*` lines appear in the order stored in `report["components"]`.
* No padding, no blank lines, no other output.

An empty report therefore renders as exactly:

```
entries=0
malformed=0
```

### `render_json(report)`

Returns

```python
json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
```

i.e. one compact line with sorted object keys, terminated by a newline.
`first` and `last` are JSON `null` when unset.

### `main(argv=None)`

Runs the CLI and **returns** the process exit code (it must not call
`sys.exit` itself). `argv` is the argument list *without* the program name;
`None` means `sys.argv[1:]`.

## 3. Command line

```
logstats.py [--min-level LEVEL] [--component NAME]... [--since TS] [--until TS]
            [--top N] [--json] [FILE...]
```

* `FILE...` — input files, read in the given order. No file, or the single
  file `-`, means standard input. `-` may also be mixed with real paths.
* `--min-level LEVEL` — keep entries whose level is at least `LEVEL` in the
  severity order of `LEVELS`. Default: keep everything.
* `--component NAME` — repeatable; keep only entries of the named components.
  Repeating it means "any of these" (OR). Default: keep everything.
* `--since TS`, `--until TS` — keep entries with `TS <= timestamp` and
  `timestamp <= TS` respectively. Both bounds are **inclusive** and use the
  timestamp format of section 1.
* `--top N` — truncate the component list to `N` entries; `N >= 1`.
* `--json` — print `render_json(report)` instead of `render_text(report)`.

Filters combine with AND. `malformed` counts every malformed line that was
read, regardless of any filter — filters apply to entries only.

### Exit codes

| Code | When |
|---|---|
| `0` | The report was printed (also when it contains zero entries). |
| `2` | Usage error: unknown option, unknown level name, malformed `--since` / `--until` value, `--top` below 1, or an input file that cannot be read. |

On a usage error nothing is written to stdout, and a message that contains
the string `logstats:` is written to stderr.

## 4. Public tests

```
python3 -m unittest -v tests.test_logstats     # module API
python3 -m unittest -v tests.test_cli          # command line
```

Both suites must pass. Hidden tests check the same specification on further
edge cases — implement section 1 to 3, not only what the visible tests
assert.

`samples/app.log` is a small example input for manual experiments; it is not
part of the grading.
