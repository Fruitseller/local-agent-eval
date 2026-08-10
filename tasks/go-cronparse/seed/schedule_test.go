// Public smoke tests for Matches and Next.
//
// Read-only: the benchmark restores this file before scoring. These tests
// cover a subset of TASK.md; the hidden suite covers the rest.
package cronparse

import (
	"testing"
	"time"
)

func at(text string) time.Time {
	parsed, err := time.Parse(time.RFC3339, text)
	if err != nil {
		panic(err)
	}
	return parsed.UTC()
}

func mustParse(t *testing.T, spec string) *Schedule {
	t.Helper()
	schedule, err := Parse(spec)
	if err != nil {
		t.Fatalf("Parse(%q) returned error: %v", spec, err)
	}
	return schedule
}

func TestScheduleMatches(t *testing.T) {
	cases := []struct {
		spec string
		when string
		want bool
	}{
		{"15 8 * * *", "2026-02-01T08:15:00Z", true},
		{"15 8 * * *", "2026-02-01T08:15:45Z", true}, // seconds are ignored
		{"15 8 * * *", "2026-02-01T08:16:00Z", false},
		{"*/15 * * * *", "2026-02-01T08:30:00Z", true},
		{"*/15 * * * *", "2026-02-01T08:31:00Z", false},
		{"0 0 * * 7", "2026-02-01T00:00:00Z", true}, // 7 is Sunday
		{"0 0 * * SUN", "2026-02-01T00:00:00Z", true},
		{"0 0 * * MON", "2026-02-01T00:00:00Z", false},
		// Day of month and day of week are OR-ed when both are restricted.
		{"0 0 1 * MON", "2026-07-01T00:00:00Z", true}, // the 1st, a Wednesday
		{"0 0 1 * MON", "2026-06-22T00:00:00Z", true}, // a Monday, not the 1st
		{"0 0 1 * MON", "2026-06-23T00:00:00Z", false},
		// Only the day of month is restricted, so the weekday is irrelevant.
		{"0 0 15 * *", "2026-06-15T00:00:00Z", true},
	}
	for _, tc := range cases {
		schedule := mustParse(t, tc.spec)
		if got := schedule.Matches(at(tc.when)); got != tc.want {
			t.Errorf("Parse(%q).Matches(%s) = %v, want %v", tc.spec, tc.when, got, tc.want)
		}
	}
}

func TestScheduleNext(t *testing.T) {
	cases := []struct {
		spec  string
		after string
		want  string
	}{
		{"*/15 * * * *", "2026-02-01T08:07:00Z", "2026-02-01T08:15:00Z"},
		{"0 0 * * *", "2026-02-01T00:00:00Z", "2026-02-02T00:00:00Z"}, // strictly after
		{"30 4 * * *", "2026-02-01T04:30:15Z", "2026-02-02T04:30:00Z"},
		{"0 0 1 * *", "2026-01-31T23:59:00Z", "2026-02-01T00:00:00Z"},
		{"0 0 * * MON", "2026-02-01T00:00:00Z", "2026-02-02T00:00:00Z"},
		{"0 0 1 * MON", "2026-06-15T12:00:00Z", "2026-06-22T00:00:00Z"},
		{"0 0 29 2 *", "2026-02-01T00:00:00Z", "2028-02-29T00:00:00Z"}, // next leap year
	}
	for _, tc := range cases {
		schedule := mustParse(t, tc.spec)
		got, err := schedule.Next(at(tc.after))
		if err != nil {
			t.Errorf("Parse(%q).Next(%s) returned error: %v", tc.spec, tc.after, err)
			continue
		}
		if !got.Equal(at(tc.want)) {
			t.Errorf("Parse(%q).Next(%s) = %s, want %s", tc.spec, tc.after, got.Format(time.RFC3339), tc.want)
		}
	}
}

func TestScheduleNextIsRepeatable(t *testing.T) {
	schedule := mustParse(t, "0 12 * * *")
	start := at("2026-02-01T00:00:00Z")
	first, err := schedule.Next(start)
	if err != nil {
		t.Fatalf("Next returned error: %v", err)
	}
	again, err := schedule.Next(start)
	if err != nil {
		t.Fatalf("second Next returned error: %v", err)
	}
	if !first.Equal(again) {
		t.Errorf("Next is not repeatable: %s then %s", first, again)
	}
	third, err := schedule.Next(first)
	if err != nil {
		t.Fatalf("third Next returned error: %v", err)
	}
	if want := at("2026-02-02T12:00:00Z"); !third.Equal(want) {
		t.Errorf("Next(%s) = %s, want %s", first.Format(time.RFC3339), third.Format(time.RFC3339), want.Format(time.RFC3339))
	}
}

func TestScheduleNextWithoutAnyMatch(t *testing.T) {
	schedule := mustParse(t, "0 0 30 2 *")
	got, err := schedule.Next(at("2026-02-01T00:00:00Z"))
	if err == nil {
		t.Fatalf("Next = %s, want an error", got.Format(time.RFC3339))
	}
	if !got.IsZero() {
		t.Errorf("Next returned %s alongside the error, want the zero time", got.Format(time.RFC3339))
	}
}
