package main

import (
	"bytes"
	"strings"
	"testing"
)

func invoke(args []string, input string) (int, string, string) {
	var stdout, stderr bytes.Buffer
	code := run(args, strings.NewReader(input), &stdout, &stderr)
	return code, stdout.String(), stderr.String()
}

func TestRunReadsCSVAndWritesTable(t *testing.T) {
	code, stdout, stderr := invoke([]string{"-header", "-align", "lr"}, "name,qty\napple,3\nkiwi,12\n")
	if code != 0 || stderr != "" {
		t.Fatalf("run() code=%d stderr=%q, want 0 and empty stderr", code, stderr)
	}
	want := "name   qty\n-----  ---\napple    3\nkiwi    12\n"
	if stdout != want {
		t.Fatalf("stdout = %q, want %q", stdout, want)
	}
}

func TestRunRejectsBadDelimiter(t *testing.T) {
	code, stdout, stderr := invoke([]string{"-d", "too"}, "a,b\n")
	if code != 2 || stdout != "" || !strings.Contains(stderr, "tablefmt:") {
		t.Fatalf("run() = (%d, %q, %q), want usage error", code, stdout, stderr)
	}
}
