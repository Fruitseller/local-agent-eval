package table

import "testing"

func TestRenderPlainHeaderAndAlignment(t *testing.T) {
	got, err := Render([][]string{{"name", "qty"}, {"apple", "3"}, {"kiwi", "12"}}, Options{Header: true, Align: "lr"})
	if err != nil {
		t.Fatalf("Render returned error: %v", err)
	}
	want := "name   qty\n-----  ---\napple    3\nkiwi    12\n"
	if got != want {
		t.Fatalf("Render() = %q, want %q", got, want)
	}
}

func TestRenderTruncatesByRunes(t *testing.T) {
	got, err := Render([][]string{{"éclair", "toolong"}}, Options{MaxWidth: 4})
	if err != nil {
		t.Fatalf("Render returned error: %v", err)
	}
	want := "écl…  too…\n"
	if got != want {
		t.Fatalf("Render() = %q, want %q", got, want)
	}
}

func TestRenderMarkdown(t *testing.T) {
	got, err := Render([][]string{{"name", "qty"}, {"a|b", "3"}}, Options{Markdown: true, Align: "lr"})
	if err != nil {
		t.Fatalf("Render returned error: %v", err)
	}
	want := "| name | qty |\n| :--- | --: |\n| a\\|b |   3 |\n"
	if got != want {
		t.Fatalf("Render() = %q, want %q", got, want)
	}
}

func TestRenderRejectsBadOptions(t *testing.T) {
	for _, opts := range []Options{{MaxWidth: -1}, {Align: "x"}} {
		if _, err := Render([][]string{{"x"}}, opts); err == nil {
			t.Fatalf("Render(%+v) returned nil error", opts)
		}
	}
}
