"""Execution and scoring of the public test suites.

Scoring is deliberately coarse: every task declares a handful of named suites,
each suite is a command that exits 0 on success. The public score is the
weighted fraction of suites that pass.

Why not per-test-case parsing: it would require a different output parser per
language (unittest, go test, bash) and those parsers break silently on
crashes, panics and timeouts - exactly the situations a benchmark must record
correctly. A suite either passes or it does not, in every language, forever.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

MAX_CAPTURE = 20000


def run_suites(task, workspace, timeout, env=None, log_dir=None):
    """Run every suite of *task* inside *workspace*."""
    results = []
    for suite in task.suites:
        results.append(run_suite(suite, workspace, suite.timeout or timeout, env=env, log_dir=log_dir))
    return results


def run_suite(suite, workspace, timeout, env=None, log_dir=None):
    proc_env = dict(os.environ)
    proc_env.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "NO_COLOR": "1",
            "TERM": "dumb",
            "LC_ALL": "C",
        }
    )
    proc_env.update(env or {})

    started = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.Popen(
            suite.cmd,
            cwd=str(workspace),
            env=proc_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        return {
            "name": suite.name,
            "weight": suite.weight,
            "passed": False,
            "exit_code": None,
            "timed_out": False,
            "elapsed_seconds": 0.0,
            "output": f"command not found: {exc}",
            "error": "command_not_found",
        }

    try:
        output = proc.communicate(timeout=timeout)[0]
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_group(proc)
        output = proc.communicate()[0] or ""
    elapsed = time.monotonic() - started
    exit_code = proc.returncode
    output = output or ""

    if log_dir:
        log_path = Path(log_dir) / f"suite-{suite.name}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(output, encoding="utf-8", errors="replace")

    return {
        "name": suite.name,
        "weight": suite.weight,
        "passed": (exit_code == 0) and not timed_out,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "elapsed_seconds": round(elapsed, 3),
        "output": _trim(output),
    }


def _kill_group(proc):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except OSError:
        proc.kill()


def _trim(text):
    """Keep head and tail of long output; the middle is never the interesting part."""
    if len(text) <= MAX_CAPTURE:
        return text
    half = MAX_CAPTURE // 2
    return f"{text[:half]}\n...[{len(text) - MAX_CAPTURE} characters omitted]...\n{text[-half:]}"


def score(suite_results, protected_violations=()):
    """Aggregate suite results into the public score.

    ``public_ratio`` is the headline number in [0, 1]. ``valid`` is False when
    the agent modified protected test files: the run still gets its score (the
    tests were restored before scoring, so the number is meaningful) but the
    violation is recorded and reported.
    """
    earned = sum(r["weight"] for r in suite_results if r["passed"])
    total = sum(r["weight"] for r in suite_results)
    return {
        "suites_passed": sum(1 for r in suite_results if r["passed"]),
        "suites_total": len(suite_results),
        "public_points": round(earned, 3),
        "public_max": round(total, 3),
        "public_ratio": round(earned / total, 4) if total else 0.0,
        "protected_violations": list(protected_violations),
        "valid": not protected_violations,
    }
