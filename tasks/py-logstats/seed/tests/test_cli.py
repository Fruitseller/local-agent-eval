"""Public smoke tests for the logstats command line.

Read-only: the benchmark restores this directory before scoring.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "logstats.py")

LOG = """\
2026-02-01T08:00:00Z INFO  auth service started
2026-02-01T08:15:30Z ERROR auth login failed for user alice
garbage
2026-02-01T09:05:12Z ERROR db   deadlock detected
2026-02-01T09:30:00Z FATAL core shutting down
"""


def run(args, stdin=""):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        cwd=ROOT,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


class CliTest(unittest.TestCase):
    def test_reads_stdin_and_reports(self):
        proc = run([], stdin=LOG)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            proc.stdout,
            "entries=4\n"
            "malformed=1\n"
            "first=2026-02-01T08:00:00Z\n"
            "last=2026-02-01T09:30:00Z\n"
            "level.INFO=1\n"
            "level.ERROR=2\n"
            "level.FATAL=1\n"
            "component.auth=2\n"
            "component.core=1\n"
            "component.db=1\n",
        )

    def test_reads_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "app.log")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(LOG)
            proc = run([path])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("entries=4\n", proc.stdout)

    def test_min_level_filters_entries_but_not_malformed(self):
        proc = run(["--min-level", "ERROR"], stdin=LOG)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("entries=3\n", proc.stdout)
        self.assertIn("malformed=1\n", proc.stdout)
        self.assertNotIn("level.INFO", proc.stdout)

    def test_component_filter_is_repeatable(self):
        proc = run(["--component", "db", "--component", "core"], stdin=LOG)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("entries=2\n", proc.stdout)
        self.assertNotIn("component.auth", proc.stdout)

    def test_json_output(self):
        proc = run(["--json", "--top", "1"], stdin=LOG)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["entries"], 4)
        self.assertEqual(payload["components"], [{"name": "auth", "count": 2}])

    def test_empty_input_is_not_an_error(self):
        proc = run([], stdin="")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "entries=0\nmalformed=0\n")

    def test_unknown_level_is_a_usage_error(self):
        proc = run(["--min-level", "LOUD"], stdin=LOG)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        self.assertIn("logstats", proc.stderr)

    def test_missing_file_is_a_usage_error(self):
        proc = run(["/nonexistent/does-not-exist.log"])
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")


if __name__ == "__main__":
    unittest.main()
