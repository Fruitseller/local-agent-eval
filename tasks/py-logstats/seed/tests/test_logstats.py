"""Public smoke tests for the logstats module API.

Read-only: the benchmark restores this directory before scoring. These tests
cover a subset of TASK.md; the hidden suite covers the rest.
"""

import json
import unittest

import logstats


ENTRY = "2026-02-01T08:15:30Z ERROR auth login failed for user alice"


def entry(timestamp, level, component, message=""):
    return {"timestamp": timestamp, "level": level, "component": component, "message": message}


class ParseLineTest(unittest.TestCase):
    def test_levels_constant(self):
        self.assertEqual(logstats.LEVELS, ("DEBUG", "INFO", "WARN", "ERROR", "FATAL"))

    def test_valid_line(self):
        self.assertEqual(
            logstats.parse_line(ENTRY),
            entry("2026-02-01T08:15:30Z", "ERROR", "auth", "login failed for user alice"),
        )

    def test_trailing_newline_and_padding(self):
        self.assertEqual(
            logstats.parse_line("  2026-02-01T08:15:30Z\tINFO   db\tmigration applied  \n"),
            entry("2026-02-01T08:15:30Z", "INFO", "db", "migration applied"),
        )

    def test_message_may_be_empty(self):
        self.assertEqual(
            logstats.parse_line("2026-02-01T08:15:30Z WARN core"),
            entry("2026-02-01T08:15:30Z", "WARN", "core", ""),
        )

    def test_blank_line_is_not_an_entry(self):
        self.assertIsNone(logstats.parse_line("   \n"))

    def test_unknown_level_is_malformed(self):
        self.assertIsNone(logstats.parse_line("2026-02-01T08:15:30Z TRACE core hello"))

    def test_bad_timestamp_is_malformed(self):
        self.assertIsNone(logstats.parse_line("2026-02-01 08:15:30 INFO core hello"))


class BuildReportTest(unittest.TestCase):
    def setUp(self):
        self.entries = [
            entry("2026-02-01T09:00:00Z", "INFO", "db"),
            entry("2026-02-01T08:00:00Z", "ERROR", "auth"),
            entry("2026-02-01T08:30:00Z", "INFO", "auth"),
            entry("2026-02-01T10:00:00Z", "INFO", "core"),
            entry("2026-02-01T09:30:00Z", "ERROR", "auth"),
        ]

    def test_counts_and_range(self):
        report = logstats.build_report(self.entries, malformed=2)
        self.assertEqual(report["entries"], 5)
        self.assertEqual(report["malformed"], 2)
        self.assertEqual(report["first"], "2026-02-01T08:00:00Z")
        self.assertEqual(report["last"], "2026-02-01T10:00:00Z")
        self.assertEqual(report["levels"], {"INFO": 3, "ERROR": 2})

    def test_components_sorted_by_count_then_name(self):
        report = logstats.build_report(self.entries, malformed=0)
        self.assertEqual(
            report["components"],
            [{"name": "auth", "count": 3}, {"name": "core", "count": 1}, {"name": "db", "count": 1}],
        )

    def test_top_truncates_components_only(self):
        report = logstats.build_report(self.entries, malformed=0, top=1)
        self.assertEqual(report["components"], [{"name": "auth", "count": 3}])
        self.assertEqual(report["entries"], 5)
        self.assertEqual(report["levels"], {"INFO": 3, "ERROR": 2})

    def test_empty_input(self):
        report = logstats.build_report([], malformed=0)
        self.assertEqual(report["entries"], 0)
        self.assertIsNone(report["first"])
        self.assertIsNone(report["last"])
        self.assertEqual(report["levels"], {})
        self.assertEqual(report["components"], [])


class RenderTest(unittest.TestCase):
    def report(self):
        return logstats.build_report(
            [
                entry("2026-02-01T08:00:00Z", "ERROR", "auth"),
                entry("2026-02-01T09:00:00Z", "INFO", "db"),
                entry("2026-02-01T10:00:00Z", "INFO", "auth"),
            ],
            malformed=1,
        )

    def test_render_text(self):
        self.assertEqual(
            logstats.render_text(self.report()),
            "entries=3\n"
            "malformed=1\n"
            "first=2026-02-01T08:00:00Z\n"
            "last=2026-02-01T10:00:00Z\n"
            "level.INFO=2\n"
            "level.ERROR=1\n"
            "component.auth=2\n"
            "component.db=1\n",
        )

    def test_render_text_of_empty_report(self):
        self.assertEqual(
            logstats.render_text(logstats.build_report([], malformed=0)),
            "entries=0\nmalformed=0\n",
        )

    def test_render_json_is_one_compact_line(self):
        rendered = logstats.render_json(self.report())
        self.assertTrue(rendered.endswith("\n"))
        self.assertNotIn("\n", rendered[:-1])
        self.assertNotIn(", ", rendered)
        self.assertEqual(json.loads(rendered), self.report())

    def test_render_json_uses_null_for_missing_range(self):
        payload = json.loads(logstats.render_json(logstats.build_report([], malformed=4)))
        self.assertIsNone(payload["first"])
        self.assertIsNone(payload["last"])
        self.assertEqual(payload["malformed"], 4)


if __name__ == "__main__":
    unittest.main()
