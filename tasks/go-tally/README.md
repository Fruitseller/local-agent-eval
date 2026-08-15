# Task: `tally` — wc-style line, word, character and byte counting

Implement the Go package `tally`: count lines, words, characters and bytes in a
string, mirroring the classic `wc -l -w -m -c` semantics.

Go 1.21+, **standard library only**. Do not add a `require` directive, do not
run `go get`, do not access the network. The grading environment is offline.

`tally_test.go` is read-only; the graders restore it from the pristine seed
before scoring.

---

## 1. Package API

Module `tally`, package `tally`, all in the repository root.

```go
type Counts struct {
    Lines int // number of '\n' characters in the input
    Words int // number of whitespace-separated words
    Chars int // number of Unicode code points
    Bytes int // number of bytes
}

func Tally(input string) Counts
```

## 2. Semantics (wc-compatible)

Given the input string `s`:

* **Lines** — the number of `'\n'` characters in `s`. A final newline counts,
  a line without a trailing newline still ends at end of input. Examples:
  `"a\nb"` → 1, `"a\nb\n"` → 2, `""` → 0.
* **Words** — the number of maximal runs of non-whitespace characters.
  Whitespace is any rune for which `unicode.IsSpace` is true. Leading and
  trailing whitespace is ignored, runs of whitespace collapse into one
  separator. Examples: `""` → 0, `"   "` → 0, `"hello world"` → 2,
  `"  a\tb\n c  "` → 3.
* **Chars** — the number of Unicode code points (`utf8.RuneCountInString`),
  *not* bytes and *not* grapheme clusters. `"héllo"` → 5, `"😀"` → 1.
* **Bytes** — `len(s)`.

All four counts are computed from the same input in a single pass; the result
must be deterministic for every input, including empty input and input with
only whitespace.

## 3. Public tests

```
go test -count=1 ./...
```

The suite must pass. Hidden tests check the same specification on further edge
cases — CRLF inputs, tabs, Unicode combining characters, multi-byte emoji,
inputs with no trailing newline, and inputs that are only newlines.

Keep the exported name and signature exactly as specified above; they are
called directly by the graders. Unexported helpers are yours to choose.
