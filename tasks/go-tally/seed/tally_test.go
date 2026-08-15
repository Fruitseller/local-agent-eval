package tally

import "testing"

func TestTallySmoke(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  Counts
	}{
		{"empty", "", Counts{0, 0, 0, 0}},
		{"single word", "hello", Counts{0, 1, 5, 5}},
		{"two words", "hello world", Counts{0, 2, 11, 11}},
		{"trailing newline", "a\nb\n", Counts{2, 2, 4, 4}},
		{"no trailing newline", "a\nb", Counts{1, 2, 3, 3}},
		{"only whitespace", "   	\n  ", Counts{1, 0, 7, 7}},
		{"collapsed whitespace", "  a	b\n c  ", Counts{1, 3, 10, 10}},
		{"unicode runes", "héllo wörld", Counts{0, 2, 11, 13}},
		{"emoji codepoint", "😀", Counts{0, 1, 1, 4}},
		{"crlf", "a\r\nb\r\n", Counts{2, 2, 6, 6}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := Tally(tt.input)
			if got != tt.want {
				t.Errorf("Tally(%q) = %+v, want %+v", tt.input, got, tt.want)
			}
		})
	}
}
