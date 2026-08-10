package main

import (
	"io"
	"os"
)

// run executes tablefmt without touching process-global standard streams.
// TODO: implement the behaviour specified in TASK.md.
func run(args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	return 0
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr))
}
