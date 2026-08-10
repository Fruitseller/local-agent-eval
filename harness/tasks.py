"""Loading and validation of task definitions.

A task lives in ``tasks/<id>/`` and consists of:

* ``task.json``  - metadata, test suites, protected paths
* ``README.md``  - the specification handed to the agent as ``TASK.md``
* ``seed/``      - the pristine repository the agent starts from
"""

from __future__ import annotations

import json
from pathlib import Path

from config import REPO_ROOT

TASKS_DIR = REPO_ROOT / "tasks"

REQUIRED_FIELDS = ("id", "title", "language", "suites")


class TaskError(Exception):
    pass


class Suite:
    """One scoreable group of public tests."""

    def __init__(self, data, task_id):
        self.name = data.get("name")
        self.cmd = data.get("cmd")
        self.weight = data.get("weight", 1)
        self.timeout = data.get("timeout")
        self.description = data.get("description", "")
        if not self.name:
            raise TaskError(f"{task_id}: suite without a name")
        if not isinstance(self.cmd, list) or not self.cmd or not all(isinstance(c, str) for c in self.cmd):
            raise TaskError(f"{task_id}/{self.name}: 'cmd' must be a non-empty list of strings")
        if not isinstance(self.weight, (int, float)) or self.weight <= 0:
            raise TaskError(f"{task_id}/{self.name}: 'weight' must be a positive number")

    def to_dict(self):
        return {"name": self.name, "cmd": self.cmd, "weight": self.weight, "description": self.description}


class Task:
    def __init__(self, directory):
        self.dir = Path(directory)
        manifest = self.dir / "task.json"
        if not manifest.exists():
            raise TaskError(f"{self.dir}: task.json is missing")
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TaskError(f"{manifest}: invalid JSON: {exc}") from exc

        missing = [f for f in REQUIRED_FIELDS if f not in data]
        if missing:
            raise TaskError(f"{manifest}: missing field(s): {', '.join(missing)}")

        self.data = data
        self.id = data["id"]
        self.title = data["title"]
        self.language = data["language"]
        self.summary = data.get("summary", "")
        self.budget_seconds = data.get("budget_seconds")
        self.test_timeout = data.get("test_timeout")
        self.protected_paths = data.get("protected_paths", [])
        self.spec_target = data.get("spec_target", "TASK.md")
        self.seed_dir = self.dir / data.get("seed", "seed")
        self.spec_file = self.dir / data.get("spec", "README.md")
        self.suites = [Suite(s, self.id) for s in data["suites"]]

        if self.id != self.dir.name:
            raise TaskError(f"{manifest}: id {self.id!r} does not match directory name {self.dir.name!r}")
        if not self.seed_dir.is_dir():
            raise TaskError(f"{self.dir}: seed directory {self.seed_dir} is missing")
        if not self.spec_file.exists():
            raise TaskError(f"{self.dir}: specification {self.spec_file} is missing")
        if not self.suites:
            raise TaskError(f"{self.dir}: at least one test suite is required")
        if len({s.name for s in self.suites}) != len(self.suites):
            raise TaskError(f"{self.dir}: duplicate suite names")
        if not isinstance(self.protected_paths, list):
            raise TaskError(f"{self.dir}: 'protected_paths' must be a list")

    @property
    def total_weight(self):
        return sum(s.weight for s in self.suites)

    def suite(self, name):
        for suite in self.suites:
            if suite.name == name:
                return suite
        raise TaskError(f"{self.id}: unknown suite {name!r}")

    def __repr__(self):
        return f"<Task {self.id}>"


def discover(tasks_dir=None):
    """Return all tasks sorted by id."""
    root = Path(tasks_dir or TASKS_DIR)
    if not root.is_dir():
        raise TaskError(f"tasks directory not found: {root}")
    tasks = [Task(p) for p in sorted(root.iterdir()) if p.is_dir() and (p / "task.json").exists()]
    if not tasks:
        raise TaskError(f"no tasks found in {root}")
    return tasks


def select(names, tasks_dir=None):
    """Resolve a list of task ids (or ``["all"]``) to Task objects."""
    all_tasks = discover(tasks_dir)
    if not names or "all" in names:
        return all_tasks
    by_id = {t.id: t for t in all_tasks}
    unknown = [n for n in names if n not in by_id]
    if unknown:
        raise TaskError(f"unknown task(s): {', '.join(unknown)}. Available: {', '.join(sorted(by_id))}")
    return [by_id[n] for n in names]
