// Package table renders small text tables.
package table

// Options controls the representation returned by Render.
type Options struct {
	Header   bool
	Align    string
	MaxWidth int
	Markdown bool
}

// Render renders rows according to opts.
//
// TODO: implement the behaviour specified in TASK.md.
func Render(rows [][]string, opts Options) (string, error) {
	return "", nil
}
