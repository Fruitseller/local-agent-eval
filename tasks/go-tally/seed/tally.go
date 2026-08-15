// Package tally counts lines, words, characters and bytes in a string,
// mirroring the classic wc -l -w -m -c semantics.
package tally

// Counts holds the four counts computed from one input string.
type Counts struct {
	Lines int // number of '\n' characters in the input
	Words int // number of whitespace-separated words
	Chars int // number of Unicode code points
	Bytes int // number of bytes
}

// Tally computes all four counts for the input string.
//
// TODO: implement per the specification in TASK.md.
func Tally(input string) Counts {
	return Counts{}
}
