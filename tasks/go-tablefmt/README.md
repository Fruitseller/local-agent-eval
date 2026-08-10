# Task: `tablefmt` — CSV to aligned text table

Implement a Go module with two parts:

* package `table` — renders rows of cells as an aligned plain-text or
  markdown table;
* package `main` — a small CLI that reads CSV and prints such a table.

Go 1.21+, **standard library only**. No `require` directives, no `go get`, no
network.

`table/table_test.go` and `main_test.go` are read-only; the graders restore
them from the pristine seed before scoring.

---

## 1. Package `table`

```go
package table

type Options struct {
    Header   bool   // the first row is a header
    Align    string // one rune per column: 'l', 'r' or 'c'
    MaxWidth int    // truncate cells to this many runes; 0 means unlimited
    Markdown bool   // render a markdown table
}

func Render(rows [][]string, opts Options) (string, error)
```

### Widths and columns

* The table has as many columns as the **longest** row. Short rows are
  treated as if padded with empty cells.
* A cell's width is its number of **runes** (`utf8.RuneCountInString`), not
  bytes. Wide or combining characters are not special-cased.
* A column's width is the largest cell width in that column, measured
  **after** truncation.

### Truncation

When `MaxWidth > 0`, a cell longer than `MaxWidth` runes is shortened to
`MaxWidth - 1` runes plus `…` (U+2026), so the result is exactly `MaxWidth`
runes wide. With `MaxWidth == 1` the cell becomes `…`. `MaxWidth < 0` is an
error.

### Alignment

The i-th rune of `Align` selects the alignment of column i: `l` left, `r`
right, `c` centred. Columns beyond the end of `Align` are left-aligned; runes
beyond the last column are ignored. Any other rune is an error.

Centred cells put the extra space on the **right**: `"ab"` in a width of 5
becomes `" ab  "`.

### Plain text output

* Columns are joined by exactly **two spaces**.
* Every line is right-trimmed of spaces, so a left-aligned last column
  produces no trailing whitespace.
* Every line, including the last, ends with `\n`.
* With `Header: true` a separator line follows the first row: each column is
  filled with `-` to its column width, joined by two spaces.
* `Render(nil, …)` and `Render([][]string{}, …)` return `""` and a nil error.

```
name   qty
-----  ---
apple    3
kiwi    12
```

### Markdown output

`Markdown: true` implies a header row — the first row is always the header
and the separator row is always emitted; the `Header` field is then ignored.

* A literal `|` in a cell is escaped as `\|`. Escaping happens **before**
  widths are measured and after truncation.
* The effective column width is `max(widest cell, 3)`.
* Rows are `| ` + cells padded to the column width and joined by ` | ` +
  ` |`. Padding follows `Align`, and lines are **not** trimmed.
* The separator segment for a column is exactly as wide as the column and
  carries the alignment: all dashes, with `:` replacing the **first** dash
  for `l`, the **last** dash for `r`, and **both** for `c`. A column that
  `Align` does not mention gets plain dashes. At the minimum width of 3 the
  four cases are `---`, `:--`, `--:` and `:-:`.

```
| name | qty |
| :--- | --: |
| a\|b |   3 |
```

## 2. Package `main`

`main.go` in the module root:

```go
func run(args []string, stdin io.Reader, stdout, stderr io.Writer) int
func main() { os.Exit(run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr)) }
```

`run` must not call `os.Exit` and must not write to the real standard
streams — everything goes to the writers it is given. `args` excludes the
program name.

```
tablefmt [-d DELIM] [-header] [-align SPEC] [-max-width N] [-markdown] [FILE]
```

| Flag | Meaning |
|---|---|
| `-d` | field delimiter, default `,`. Exactly one rune, or the two characters `\t` for a tab. |
| `-header` | sets `Options.Header` |
| `-align` | sets `Options.Align` |
| `-max-width` | sets `Options.MaxWidth`, default `0` |
| `-markdown` | sets `Options.Markdown` |

* Input is CSV read with `encoding/csv`. Records may have differing field
  counts (`FieldsPerRecord = -1`).
* `FILE` is optional; no file, or the single argument `-`, means stdin. More
  than one positional argument is a usage error.
* Empty input produces no output and exit code `0`.

### Exit codes

| Code | When |
|---|---|
| `0` | table written to `stdout` |
| `1` | input could not be read or parsed, or `Render` returned an error |
| `2` | usage error: unknown flag, bad `-d`, more than one `FILE` |

Codes `1` and `2` write a message containing `tablefmt:` to `stderr` and
nothing to `stdout`.

## 3. Public tests

```
go test -count=1 ./table
go test -count=1 .
```

Hidden tests check the same specification on further edge cases —
truncation, centring, ragged rows, escaping and delimiter handling.
Keep the exported names, the `run` signature and the file layout exactly as
specified.
