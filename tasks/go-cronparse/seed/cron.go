// Package cronparse parses classic five-field cron expressions and evaluates
// them against times.
//
// This is a stub: the exported API is declared so the test files compile, the
// behaviour is specified in TASK.md and not implemented yet.
package cronparse

import (
	"errors"
	"time"
)

// errNotImplemented is returned by every stub. Remove it once the package
// does something useful.
var errNotImplemented = errors.New("cronparse: not implemented")

// Schedule is a parsed cron expression. The fields are yours to design.
type Schedule struct {
	spec string
}

// Parse parses a five-field cron expression or a macro such as "@daily".
func Parse(spec string) (*Schedule, error) {
	return nil, errNotImplemented
}

// Matches reports whether t matches the schedule. Seconds are ignored.
func (s *Schedule) Matches(t time.Time) bool {
	return false
}

// Next returns the earliest time strictly after "after" that matches.
func (s *Schedule) Next(after time.Time) (time.Time, error) {
	return time.Time{}, errNotImplemented
}

// String returns the normalised five-field form of the expression.
func (s *Schedule) String() string {
	return s.spec
}
