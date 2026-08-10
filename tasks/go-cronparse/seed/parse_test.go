// Public smoke tests for expression parsing.
//
// Read-only: the benchmark restores this file before scoring. These tests
// cover a subset of TASK.md; the hidden suite covers the rest.
package cronparse

import "testing"

func TestParseAcceptsValidExpressions(t *testing.T) {
	specs := []string{
		"* * * * *",
		"0 0 * * *",
		"*/15 * * * *",
		"5-55/10 0-6 1,15 JAN-MAR MON-FRI",
		"0 0 * * 7",
		"  0   0  *  *  *  ",
		"@daily",
		"@YEARLY",
	}
	for _, spec := range specs {
		if _, err := Parse(spec); err != nil {
			t.Errorf("Parse(%q) returned error: %v", spec, err)
		}
	}
}

func TestParseRejectsInvalidExpressions(t *testing.T) {
	specs := []string{
		"",
		"* * * *",
		"* * * * * *",
		"60 * * * *",
		"* 24 * * *",
		"* * 0 * *",
		"* * 32 * *",
		"* * * 13 *",
		"* * * * 8",
		"5-1 * * * *",
		"*/0 * * * *",
		"5/15 * * * *",
		"1,,2 * * * *",
		"* * * * MONDAY",
		"MON * * * *",
		"@reboot",
		"@weird",
	}
	for _, spec := range specs {
		got, err := Parse(spec)
		if err == nil {
			t.Errorf("Parse(%q) = %v, want an error", spec, got)
		}
	}
}

func TestParseString(t *testing.T) {
	cases := []struct {
		spec string
		want string
	}{
		{"@daily", "0 0 * * *"},
		{"@HOURLY", "0 * * * *"},
		{"@weekly", "0 0 * * 0"},
		{"  5,1\t0-2 * * MON ", "5,1 0-2 * * MON"},
		{"* * * * *", "* * * * *"},
	}
	for _, tc := range cases {
		schedule, err := Parse(tc.spec)
		if err != nil {
			t.Fatalf("Parse(%q) returned error: %v", tc.spec, err)
		}
		if got := schedule.String(); got != tc.want {
			t.Errorf("Parse(%q).String() = %q, want %q", tc.spec, got, tc.want)
		}
	}
}
