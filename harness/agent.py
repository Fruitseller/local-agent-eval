"""Invocation of the coding agent under test.

Two invocation modes exist:

``default``
    Build a ``pi`` command line ourselves. pi runs non-interactively
    (``-p``) and emits its event stream as JSON lines (``--mode json``), which
    gives us tokens, cost, turns and tool calls for free.

``PI_COMMAND``
    An arbitrary shell command supplied by the operator. Used when the local
    pi build expects a different provider configuration than the one the
    harness generates, or when a completely different agent is benchmarked.
    The prompt is passed on stdin *and* substituted for ``{prompt_file}`` /
    ``{workspace}`` placeholders if present.

Both modes are killed hard when the wall-clock budget expires.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

#: Flags that make a pi run reproducible: no user extensions, skills, prompt
#: templates, themes or context files, and no trust in project-local config.
ISOLATION_FLAGS = [
    "--no-extensions",
    "--no-skills",
    "--no-prompt-templates",
    "--no-themes",
    "--no-context-files",
    "--no-approve",
]


def build_prompt(agent_prompt_path, task):
    """Compose the prompt: shared agent prompt + task pointer."""
    shared = Path(agent_prompt_path).read_text(encoding="utf-8").strip()
    return (
        f"{shared}\n\n"
        f"---\n\n"
        f"Task id: {task.id}\n"
        f"Title: {task.title}\n\n"
        f"The specification is in `{task.spec_target}` in the repository root. "
        f"Read it now and implement it.\n"
    )


def build_pi_argv(cfg, session_dir, prompt):
    argv = [cfg.pi_bin, "-p", "--mode", "json"]
    if cfg.provider:
        argv += ["--provider", cfg.provider]
    if cfg.model:
        argv += ["--model", cfg.model]
    if cfg.api_key:
        argv += ["--api-key", cfg.api_key]
    if cfg.thinking:
        argv += ["--thinking", cfg.thinking]
    argv += ISOLATION_FLAGS
    argv += ["--session-dir", str(session_dir)]
    argv += cfg.extra_args
    argv.append(prompt)
    return argv


def build_env(cfg, pi_config_dir):
    """Environment for the agent process.

    Keep the operator's HOME intact: pi's binary and provider integrations may
    read runtime state from it before consulting ``PI_CODING_AGENT_DIR``.
    Benchmark-specific pi settings, models and extensions are isolated through
    that variable instead.
    """
    env = dict(os.environ)
    env.update(
        {
            "PI_SKIP_VERSION_CHECK": "1",
            "PI_TELEMETRY": "0",
            "NO_COLOR": "1",
            "TERM": "dumb",
            "CI": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    if pi_config_dir:
        env["PI_CODING_AGENT_DIR"] = str(pi_config_dir)
    if cfg.base_url:
        env["PI_BASE_URL"] = cfg.base_url
    if cfg.api_type:
        env["PI_API_TYPE"] = cfg.api_type
    return env


class AgentResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def to_dict(self):
        return dict(self.__dict__)


def run(cfg, prompt, workspace, run_dir, budget_seconds):
    """Run the agent against *workspace*; return an :class:`AgentResult`."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = run_dir / "prompt.txt"
    prompt_file.write_text(prompt, encoding="utf-8")
    stdout_path = run_dir / "agent.stdout.jsonl"
    stderr_path = run_dir / "agent.stderr.txt"

    pi_config_dir = None
    if cfg.isolate_pi_config:
        from config import build_pi_config_dir

        pi_config_dir = build_pi_config_dir(cfg, run_dir)

    env = build_env(cfg, pi_config_dir)

    if cfg.pi_command:
        command = (
            cfg.pi_command.replace("{prompt_file}", str(prompt_file))
            .replace("{workspace}", str(workspace))
            .replace("{model}", cfg.model)
            .replace("{provider}", cfg.provider)
            .replace("{base_url}", cfg.base_url)
        )
        argv = ["/bin/sh", "-c", command]
        kind = "PI_COMMAND"
        display = command
    else:
        argv = build_pi_argv(cfg, run_dir / "session", prompt)
        kind = "pi"
        display = " ".join(_redact(argv, cfg.api_key))

    started = time.time()
    monotonic = time.monotonic()
    timed_out = False
    # In default mode the prompt is already the positional argument; pi would
    # merge piped stdin into it and receive the prompt twice. Custom commands
    # get it on stdin instead, so they need no placeholder to work.
    stdin_source = open(prompt_file, "rb") if cfg.pi_command else subprocess.DEVNULL
    try:
        with open(stdout_path, "wb") as out, open(stderr_path, "wb") as err:
            proc = subprocess.Popen(
                argv,
                cwd=str(workspace),
                env=env,
                stdin=stdin_source,
                stdout=out,
                stderr=err,
                start_new_session=True,  # own process group, so children die too
            )
            try:
                returncode = proc.wait(timeout=budget_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                returncode = _terminate(proc)
    finally:
        if stdin_source is not subprocess.DEVNULL:
            stdin_source.close()
    elapsed = time.monotonic() - monotonic

    transcript = parse_transcript(stdout_path)
    return AgentResult(
        kind=kind,
        command=display,
        exit_code=returncode,
        timed_out=timed_out,
        elapsed_seconds=round(elapsed, 3),
        started_at=_iso(started),
        finished_at=_iso(time.time()),
        stdout_path=str(stdout_path.relative_to(run_dir)),
        stderr_path=str(stderr_path.relative_to(run_dir)),
        stderr_tail=_tail(stderr_path),
        transcript=transcript,
    )


def _terminate(proc):
    """SIGTERM the whole process group, then SIGKILL what survives."""
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        return proc.returncode if proc.returncode is not None else -1
    for sig, grace in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        try:
            os.killpg(pgid, sig)
        except OSError:
            break
        try:
            return proc.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            continue
    return proc.returncode if proc.returncode is not None else -9


def parse_transcript(path):
    """Extract usage metrics from a pi ``--mode json`` event stream.

    Unknown or non-JSON output is tolerated: a custom ``PI_COMMAND`` agent may
    print anything at all, and the run is still scored on its diff and tests.
    """
    stats = {
        "parsed": False,
        "lines": 0,
        "turns": 0,
        "tool_calls": 0,
        "tool_errors": 0,
        "assistant_messages": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "reasoning_tokens": 0,
        "cost_usd": 0.0,
        "stop_reasons": [],
        "errors": [],
        "final_text": "",
    }
    path = Path(path)
    if not path.exists():
        return stats

    json_lines = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            stats["lines"] += 1
            if not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            json_lines += 1
            etype = event.get("type")
            if etype == "turn_end":
                stats["turns"] += 1
            elif etype == "tool_execution_end":
                stats["tool_calls"] += 1
                if event.get("isError"):
                    stats["tool_errors"] += 1
            elif etype == "message_end":
                message = event.get("message") or {}
                if message.get("role") != "assistant":
                    continue
                stats["assistant_messages"] += 1
                usage = message.get("usage") or {}
                stats["input_tokens"] += _num(usage.get("input"))
                stats["output_tokens"] += _num(usage.get("output"))
                stats["cache_read_tokens"] += _num(usage.get("cacheRead"))
                stats["reasoning_tokens"] += _num(usage.get("reasoning"))
                cost = usage.get("cost") or {}
                stats["cost_usd"] += float(cost.get("total") or 0)
                reason = message.get("stopReason")
                if reason:
                    stats["stop_reasons"].append(reason)
                if message.get("errorMessage"):
                    stats["errors"].append(str(message["errorMessage"])[:500])
                text = "".join(
                    block.get("text", "")
                    for block in message.get("content", [])
                    if isinstance(block, dict) and block.get("type") == "text"
                )
                if text.strip():
                    stats["final_text"] = text.strip()[:4000]

    stats["parsed"] = json_lines > 0
    stats["cost_usd"] = round(stats["cost_usd"], 6)
    return stats


def _num(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _tail(path, limit=2000):
    try:
        data = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return data[-limit:]


def _redact(argv, secret):
    if not secret:
        return list(argv)
    return ["***" if part == secret else part for part in argv]


def _iso(epoch):
    import datetime

    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).isoformat(timespec="seconds")
