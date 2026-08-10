#!/usr/bin/env python3
"""logstats - statistics over structured application logs.

This is a stub. The public API is declared here so the test suites import
cleanly; the behaviour is specified in TASK.md and not implemented yet.

Standard library only.
"""

from __future__ import annotations

import sys

#: Level names in ascending severity. Do not reorder.
LEVELS = ("DEBUG", "INFO", "WARN", "ERROR", "FATAL")


def parse_line(line):
    """Parse one log line into an entry dict, or return None if malformed."""
    raise NotImplementedError("parse_line is not implemented yet")


def build_report(entries, malformed, top=None):
    """Aggregate parsed entries into the report structure."""
    raise NotImplementedError("build_report is not implemented yet")


def render_text(report):
    """Render a report as key=value lines."""
    raise NotImplementedError("render_text is not implemented yet")


def render_json(report):
    """Render a report as one compact JSON line."""
    raise NotImplementedError("render_json is not implemented yet")


def main(argv=None):
    """Run the command line interface and return the exit code."""
    raise NotImplementedError("main is not implemented yet")


if __name__ == "__main__":
    sys.exit(main())
