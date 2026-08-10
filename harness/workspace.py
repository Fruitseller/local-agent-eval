"""Creation and inspection of per-run task worktrees.

Every (task, run) pair gets a *fresh* worktree: the pristine seed is copied to
a scratch directory and initialised as its own git repository with a single
``seed`` commit.

Why a fresh repo instead of ``git worktree add`` on this benchmark repo: a
worktree of this repository would expose every other task, the harness itself
and the git history to the agent under test. That is both a contamination
risk and an unfair advantage for agents that browse the parent repository. The
result is the same thing that matters here - an isolated, throwaway git
working tree per task and run, with a known base commit to diff against.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

#: Committer identity used for the seed and post-agent commits. Fixed so runs
#: are byte-for-byte reproducible and never depend on the operator's gitconfig.
GIT_ENV = {
    "GIT_AUTHOR_NAME": "local-agent-eval",
    "GIT_AUTHOR_EMAIL": "bench@localhost",
    "GIT_COMMITTER_NAME": "local-agent-eval",
    "GIT_COMMITTER_EMAIL": "bench@localhost",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_TERMINAL_PROMPT": "0",
}


def git(args, cwd, check=True, env=None):
    """Run a git command inside *cwd* and return its stdout."""
    full_env = dict(env or {})
    full_env.update(GIT_ENV)
    import os

    merged = dict(os.environ)
    merged.update(full_env)
    # HOME is redirected so a user-level gitconfig cannot change behaviour.
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}:\n{proc.stderr.strip()}")
    return proc.stdout


def create(task, destination):
    """Materialise *task*'s seed into *destination* as a fresh git repo.

    Returns the base commit sha.
    """
    destination = Path(destination)
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(task.seed_dir, destination)

    # The specification the agent must satisfy travels with the worktree so the
    # agent can re-read it at any point during the run.
    spec_target = destination / task.spec_target
    spec_target.write_text(task.spec_file.read_text(encoding="utf-8"), encoding="utf-8")

    git(["init", "-q", "-b", "main"], destination)
    git(["add", "-A"], destination)
    git(["commit", "-q", "-m", "seed"], destination)
    return git(["rev-parse", "HEAD"], destination).strip()


def collect_diff(workspace, base_commit):
    """Stage everything the agent produced and describe the change set.

    Untracked files are staged first so they appear in the diff; the result is
    the complete delta between the seed and whatever the agent left behind.
    """
    workspace = Path(workspace)
    git(["add", "-A"], workspace)
    diff_text = git(["-c", "core.pager=cat", "diff", "--binary", base_commit], workspace)
    numstat = git(["diff", "--numstat", base_commit], workspace)
    names = git(["diff", "--name-status", base_commit], workspace)

    insertions = deletions = 0
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            if parts[0].isdigit():
                insertions += int(parts[0])
            if parts[1].isdigit():
                deletions += int(parts[1])

    changed = []
    for line in names.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            changed.append({"status": parts[0], "path": parts[-1]})

    return {
        "text": diff_text,
        "files_changed": len(changed),
        "insertions": insertions,
        "deletions": deletions,
        "files": changed,
    }


def protected_violations(workspace, base_commit, protected_paths):
    """Return the protected files the agent touched (added/changed/deleted)."""
    if not protected_paths:
        return []
    out = git(
        ["diff", "--name-only", base_commit, "--", *protected_paths],
        workspace,
    )
    return sorted(p for p in out.splitlines() if p.strip())


def restore_protected(workspace, base_commit, protected_paths):
    """Reset protected paths to their pristine seed state before scoring.

    This is the fairness control that makes "make the tests pass" mean
    "implement the specification" rather than "edit the tests".
    """
    if not protected_paths:
        return
    # Remove files the agent may have added inside protected directories.
    for path in protected_paths:
        target = Path(workspace) / path
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    git(["checkout", base_commit, "--", *protected_paths], workspace)
    git(["reset", "-q", base_commit, "--", *protected_paths], workspace, check=False)


def commit_agent_output(workspace, message="agent output"):
    """Commit whatever is staged so the worktree can be published as an artifact."""
    git(["add", "-A"], workspace)
    status = git(["status", "--porcelain"], workspace).strip()
    if not status:
        return None
    git(["commit", "-q", "-m", message], workspace)
    return git(["rev-parse", "HEAD"], workspace).strip()
