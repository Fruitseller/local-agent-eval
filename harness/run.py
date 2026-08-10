#!/usr/bin/env python3
"""local-agent-eval - benchmark runner.

Runs one or more benchmark tasks against a coding agent (``pi`` by default),
in a fresh git worktree per task and run, under a hard wall-clock budget, and
records transcript, elapsed time, diff and public test results as JSON
artifacts.

Standard library only. Python 3.9+.

Examples
--------
    ./harness/run.py --list
    ./harness/run.py --baseline
    ./harness/run.py --task py-logstats --label qwen3-coder-30b
    ./harness/run.py --all --env-file config/benchmark.env
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS_DIR))

import agent  # noqa: E402
import scoring  # noqa: E402
import tasks as task_mod  # noqa: E402
import workspace as ws  # noqa: E402
from config import REPO_ROOT, Config, load_env_file  # noqa: E402

AGENT_PROMPT = HARNESS_DIR / "prompts" / "agent_prompt.md"
RESULT_SCHEMA = 1


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Run local-agent-eval benchmark tasks against a coding agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--task", "-t", action="append", default=[], help="task id (repeatable); default: all")
    parser.add_argument("--all", action="store_true", help="run every task (default when --task is omitted)")
    parser.add_argument("--list", action="store_true", help="list available tasks and exit")
    parser.add_argument("--env-file", default=None, help="KEY=VALUE file with defaults (real env wins)")
    parser.add_argument("--label", default=None, help="label for this run, e.g. the model name")
    parser.add_argument("--run-id", default=None, help="run id (default: UTC timestamp + label)")
    parser.add_argument("--out", default=None, help="results directory (default: ./results)")
    parser.add_argument("--budget", type=int, default=None, help="wall-clock budget per task in seconds")
    parser.add_argument("--test-timeout", type=int, default=None, help="timeout per test suite in seconds")
    parser.add_argument("--repeat", type=int, default=1, help="run each task N times (variance measurement)")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="do not invoke an agent; score the pristine seed (sanity check for tasks and harness)",
    )
    parser.add_argument("--dry-run", action="store_true", help="print the resolved configuration and command, run nothing")
    parser.add_argument("--keep-workspace", dest="keep_workspace", action="store_true", default=True,
                        help="keep the task worktree as an artifact (default)")
    parser.add_argument("--no-keep-workspace", dest="keep_workspace", action="store_false",
                        help="delete the worktree after scoring")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    env_file = args.env_file
    if env_file is None:
        default_env = REPO_ROOT / "config" / "benchmark.env"
        env_file = str(default_env) if default_env.exists() else None
    if env_file:
        load_env_file(env_file)

    if args.label:
        os.environ["BENCH_LABEL"] = args.label
    cfg = Config()
    if args.budget:
        cfg.budget_seconds = args.budget
    if args.test_timeout:
        cfg.test_timeout = args.test_timeout
    if args.out:
        cfg.results_dir = Path(args.out)

    try:
        selected = task_mod.select([] if args.all else args.task)
    except task_mod.TaskError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.list:
        for task in selected:
            suites = ", ".join(s.name for s in task.suites)
            print(f"{task.id:<18} {task.language:<7} {task.title}")
            print(f"{'':<18} suites: {suites}")
        return 0

    run_id = args.run_id or default_run_id(cfg.label, args.baseline)
    run_dir = Path(cfg.results_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        return dry_run(cfg, selected, run_dir, args)

    print(f"run id      : {run_id}")
    print(f"target      : {'BASELINE (no agent)' if args.baseline else cfg.describe_target()}")
    print(f"budget/task : {cfg.budget_seconds}s")
    print(f"results     : {run_dir}")
    print()

    results = []
    for task in selected:
        for attempt in range(1, max(1, args.repeat) + 1):
            suffix = "" if args.repeat == 1 else f".{attempt}"
            results.append(run_one(cfg, task, run_dir, run_id, args, suffix))

    summary = write_summary(cfg, run_dir, run_id, results, args)
    print_summary(summary)
    return 0 if all(r["score"]["valid"] for r in results) else 1


# ----------------------------------------------------------------------
# One task
# ----------------------------------------------------------------------
def run_one(cfg, task, run_dir, run_id, args, suffix=""):
    task_dir = run_dir / f"{task.id}{suffix}"
    task_dir.mkdir(parents=True, exist_ok=True)
    work = task_dir / "workspace"
    budget = args.budget or task.budget_seconds or cfg.budget_seconds
    test_timeout = args.test_timeout or task.test_timeout or cfg.test_timeout

    print(f"--- {task.id}{suffix} [{task.language}] budget={budget}s")
    base_commit = ws.create(task, work)

    if args.baseline:
        agent_result = None
        diff = {"text": "", "files_changed": 0, "insertions": 0, "deletions": 0, "files": []}
        violations = []
    else:
        prompt = agent.build_prompt(AGENT_PROMPT, task)
        agent_result = agent.run(cfg, prompt, work, task_dir, budget)
        status = "TIMEOUT" if agent_result.timed_out else f"exit={agent_result.exit_code}"
        print(f"    agent    : {status} in {agent_result.elapsed_seconds:.1f}s")
        diff = ws.collect_diff(work, base_commit)
        (task_dir / "agent.diff").write_text(diff["text"], encoding="utf-8", errors="replace")
        violations = ws.protected_violations(work, base_commit, task.protected_paths)
        if violations:
            print(f"    WARNING  : agent modified protected paths: {', '.join(violations)}")
        if cfg.restore_protected:
            ws.restore_protected(work, base_commit, task.protected_paths)

    suite_results = scoring.run_suites(task, work, test_timeout, log_dir=task_dir / "logs")
    for suite in suite_results:
        mark = "PASS" if suite["passed"] else ("TIMEOUT" if suite["timed_out"] else "FAIL")
        print(f"    {suite['name']:<14} {mark} ({suite['elapsed_seconds']:.1f}s)")
    score = scoring.score(suite_results, violations)
    print(f"    score    : {score['public_points']}/{score['public_max']} = {score['public_ratio']:.2f}")

    ws.commit_agent_output(work, "agent output (protected paths restored)")

    result = {
        "schema": RESULT_SCHEMA,
        "run_id": run_id,
        "task": {
            "id": task.id,
            "title": task.title,
            "language": task.language,
            "seed_digest": digest_tree(task.seed_dir),
            "spec_digest": digest_file(task.spec_file),
        },
        "mode": "baseline" if args.baseline else "agent",
        "config": cfg.public_dict(),
        "budget_seconds": budget,
        "base_commit": base_commit,
        "agent": strip_output(agent_result),
        "diff": {k: v for k, v in diff.items() if k != "text"},
        "suites": [{k: v for k, v in s.items() if k != "output"} for s in suite_results],
        "score": score,
        "environment": environment_info(),
        "artifacts": {
            "workspace": "workspace",
            "diff": "agent.diff",
            "logs": "logs",
            "transcript": None if agent_result is None else agent_result.stdout_path,
        },
    }
    (task_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if not args.keep_workspace:
        import shutil

        shutil.rmtree(work, ignore_errors=True)
        result["artifacts"]["workspace"] = None
    return result


def strip_output(agent_result):
    if agent_result is None:
        return None
    data = agent_result.to_dict()
    return data


# ----------------------------------------------------------------------
# Summaries
# ----------------------------------------------------------------------
def write_summary(cfg, run_dir, run_id, results, args):
    summary = {
        "schema": RESULT_SCHEMA,
        "run_id": run_id,
        "mode": "baseline" if args.baseline else "agent",
        "target": "baseline" if args.baseline else cfg.describe_target(),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "config": cfg.public_dict(),
        "environment": environment_info(),
        "totals": totals(results),
        "tasks": [
            {
                "task": r["task"]["id"],
                "score": r["score"]["public_ratio"],
                "points": r["score"]["public_points"],
                "max": r["score"]["public_max"],
                "suites": {s["name"]: s["passed"] for s in r["suites"]},
                "elapsed_seconds": (r["agent"] or {}).get("elapsed_seconds"),
                "timed_out": (r["agent"] or {}).get("timed_out"),
                "cost_usd": ((r["agent"] or {}).get("transcript") or {}).get("cost_usd"),
                "valid": r["score"]["valid"],
                "protected_violations": r["score"]["protected_violations"],
            }
            for r in results
        ],
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (run_dir / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
    return summary


def totals(results):
    points = sum(r["score"]["public_points"] for r in results)
    maximum = sum(r["score"]["public_max"] for r in results)
    elapsed = [(r["agent"] or {}).get("elapsed_seconds") or 0 for r in results]
    cost = sum(((r["agent"] or {}).get("transcript") or {}).get("cost_usd") or 0 for r in results)
    return {
        "tasks": len(results),
        "points": round(points, 3),
        "max": round(maximum, 3),
        "ratio": round(points / maximum, 4) if maximum else 0.0,
        "elapsed_seconds": round(sum(elapsed), 1),
        "cost_usd": round(cost, 6),
        "timeouts": sum(1 for r in results if (r["agent"] or {}).get("timed_out")),
        "invalid": sum(1 for r in results if not r["score"]["valid"]),
    }


def render_markdown(summary):
    lines = [
        f"# Run `{summary['run_id']}`",
        "",
        f"* Ziel / target: **{summary['target']}**",
        f"* Modus: `{summary['mode']}`",
        f"* Erstellt: {summary['created_at']}",
        f"* Gesamt: **{summary['totals']['points']}/{summary['totals']['max']}** "
        f"({summary['totals']['ratio']:.2%}), {summary['totals']['timeouts']} Timeout(s)",
        "",
        "| Task | Score | Punkte | Zeit (s) | Kosten (USD) | Timeout | Gueltig |",
        "|---|---:|---:|---:|---:|:--:|:--:|",
    ]
    for task in summary["tasks"]:
        lines.append(
            "| `{task}` | {ratio:.2f} | {pts}/{mx} | {sec} | {cost} | {to} | {valid} |".format(
                task=task["task"],
                ratio=task["score"],
                pts=task["points"],
                mx=task["max"],
                sec="-" if task["elapsed_seconds"] is None else f"{task['elapsed_seconds']:.0f}",
                cost="-" if not task["cost_usd"] else f"{task['cost_usd']:.4f}",
                to="ja" if task["timed_out"] else "nein",
                valid="ja" if task["valid"] else "NEIN",
            )
        )
    lines += ["", "## Suites", "", "| Task | Suite | Ergebnis |", "|---|---|:--:|"]
    for task in summary["tasks"]:
        for name, passed in task["suites"].items():
            lines.append(f"| `{task['task']}` | `{name}` | {'PASS' if passed else 'FAIL'} |")
    lines += [
        "",
        "> Nur oeffentliche Smoke-Tests. Die Holdout-Bewertung erfolgt extern, "
        "siehe `docs/holdout.md`.",
        "",
    ]
    return "\n".join(lines)


def print_summary(summary):
    totals_ = summary["totals"]
    print()
    print(f"total: {totals_['points']}/{totals_['max']} ({totals_['ratio']:.2%}) "
          f"over {totals_['tasks']} run(s), timeouts={totals_['timeouts']}, invalid={totals_['invalid']}")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def dry_run(cfg, selected, run_dir, args):
    print(json.dumps(cfg.public_dict(), indent=2))
    print()
    for task in selected:
        budget = args.budget or task.budget_seconds or cfg.budget_seconds
        if cfg.pi_command:
            command = cfg.pi_command
        else:
            command = " ".join(agent.build_pi_argv(cfg, run_dir / task.id / "session", "<prompt>"))
        print(f"{task.id}: budget={budget}s")
        print(f"  cwd     : {run_dir / task.id / 'workspace'}")
        print(f"  command : {command}")
        for suite in task.suites:
            print(f"  suite {suite.name}: {' '.join(suite.cmd)}")
    return 0


def default_run_id(label, baseline):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = "baseline" if baseline else (label or "run")
    safe = "".join(c if c.isalnum() or c in "-_." else "-" for c in tag)
    return f"{stamp}-{safe}"


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def digest_tree(root):
    """Stable digest over a directory's relative paths and contents."""
    root = Path(root)
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def environment_info():
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "go": _tool_version(["go", "version"]),
        "git": _tool_version(["git", "--version"]),
        "bash": _tool_version(["bash", "--version"]),
        "pi": _tool_version([os.environ.get("PI_BIN", "pi"), "--version"]),
    }


def _tool_version(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr).strip() else None


if __name__ == "__main__":
    sys.exit(main())
