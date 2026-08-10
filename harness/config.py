"""Configuration resolution for the benchmark harness.

The harness is configured through environment variables, optionally seeded from
an env file (``config/benchmark.env``). Real environment variables always win
over the env file, so CI can override anything without editing files.

Only the Python standard library is used.
"""

from __future__ import annotations

import json
import os
import shlex
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Values that mean "true" in the env file / environment.
_TRUE = {"1", "true", "yes", "on"}


def parse_env_file(path):
    """Parse a minimal ``KEY=VALUE`` env file.

    Supports ``#`` comments, blank lines, optional ``export`` prefixes and
    quoted values. Deliberately not a shell parser: no interpolation, no
    command substitution.
    """
    values = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            raise ValueError(f"{path}: not a KEY=VALUE line: {raw!r}")
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load_env_file(path, environ=None):
    """Load *path* into *environ* without overriding existing variables."""
    environ = os.environ if environ is None else environ
    if not path:
        return {}
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"env file not found: {path}")
    loaded = parse_env_file(path)
    for key, value in loaded.items():
        environ.setdefault(key, value)
    return loaded


class Config:
    """Resolved run configuration.

    Attributes are intentionally flat and JSON-serialisable so the effective
    configuration can be embedded verbatim in every result file.
    """

    def __init__(self, environ=None):
        env = os.environ if environ is None else environ
        self.env = env

        # --- agent invocation -------------------------------------------
        self.pi_bin = env.get("PI_BIN", "pi")
        self.pi_command = env.get("PI_COMMAND", "").strip()
        self.provider = env.get("PI_PROVIDER", "").strip()
        self.model = env.get("PI_MODEL", "").strip()
        self.base_url = env.get("PI_BASE_URL", "").strip()
        self.api_key = env.get("PI_API_KEY", "").strip()
        self.api_type = env.get("PI_API_TYPE", "openai-completions").strip()
        self.thinking = env.get("PI_THINKING", "").strip()
        self.extra_args = shlex.split(env.get("PI_EXTRA_ARGS", ""))

        # --- model capability hints for generated models.json ------------
        self.context_window = _int(env.get("PI_CONTEXT_WINDOW"), 0)
        self.max_tokens = _int(env.get("PI_MAX_TOKENS"), 0)
        self.reasoning = _bool(env.get("PI_REASONING"), False)
        self.compat = _json_obj(env.get("PI_COMPAT"), {})

        # --- fairness / isolation ---------------------------------------
        self.isolate_pi_config = _bool(env.get("BENCH_ISOLATE_PI_CONFIG"), True)
        self.budget_seconds = _int(env.get("BENCH_BUDGET_SECONDS"), 1200)
        self.test_timeout = _int(env.get("BENCH_TEST_TIMEOUT"), 300)
        self.restore_protected = _bool(env.get("BENCH_RESTORE_PROTECTED"), True)

        # --- output ------------------------------------------------------
        self.results_dir = Path(env.get("BENCH_RESULTS_DIR", REPO_ROOT / "results"))
        self.label = env.get("BENCH_LABEL", "").strip()

    # ------------------------------------------------------------------
    def describe_target(self):
        """Human-readable identifier of the system under test."""
        if self.label:
            return self.label
        if self.pi_command:
            return "custom:PI_COMMAND"
        parts = [p for p in (self.provider, self.model) if p]
        return "/".join(parts) if parts else "pi-default"

    def public_dict(self):
        """Config snapshot for result files. Never contains the API key."""
        return {
            "target": self.describe_target(),
            "pi_bin": self.pi_bin,
            "pi_command": self.pi_command or None,
            "provider": self.provider or None,
            "model": self.model or None,
            "base_url": self.base_url or None,
            "api_type": self.api_type if self.base_url else None,
            "thinking": self.thinking or None,
            "extra_args": self.extra_args,
            "api_key_set": bool(self.api_key),
            "isolate_pi_config": self.isolate_pi_config,
            "budget_seconds": self.budget_seconds,
            "test_timeout": self.test_timeout,
            "restore_protected": self.restore_protected,
        }


def _int(value, default):
    if value is None or str(value).strip() == "":
        return default
    return int(value)


def _bool(value, default):
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in _TRUE


def _json_obj(value, default):
    if not value or not value.strip():
        return default
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("PI_COMPAT must be a JSON object")
    return parsed


# ----------------------------------------------------------------------
# Isolated pi configuration directory
# ----------------------------------------------------------------------
def build_pi_config_dir(cfg, parent_dir):
    """Create a throwaway ``PI_CODING_AGENT_DIR`` for one run.

    Why: pi reads ``~/.pi/agent`` for settings, custom models, extensions and
    skills. Whatever the operator happens to have installed there would leak
    into the benchmark and make runs incomparable between machines. We
    therefore point pi at a generated directory that contains only what the
    benchmark declares.

    ``models.json`` is written in the schema documented by pi
    (``docs/models.md``): ``{"providers": {<name>: {baseUrl, api, apiKey,
    models: [...]}}}``. It is only generated when ``PI_BASE_URL`` is set, i.e.
    when an OpenAI-compatible local endpoint is being benchmarked. If your pi
    version expects a different schema, bypass this entirely with
    ``PI_COMMAND`` (see README).
    """
    config_dir = Path(parent_dir) / "pi-config"
    config_dir.mkdir(parents=True, exist_ok=True)

    settings = {
        "quietStartup": True,
        # Never trust project-local pi settings/extensions: a task seed must not
        # be able to reconfigure the agent that is being measured.
        "defaultProjectTrust": "never",
        "enableInstallTelemetry": False,
        "enableAnalytics": False,
    }
    if cfg.provider:
        settings["defaultProvider"] = cfg.provider
    if cfg.model:
        settings["defaultModel"] = cfg.model
    _write_json(config_dir / "settings.json", settings)

    if cfg.base_url:
        _write_json(config_dir / "models.json", {"providers": {cfg.provider or "local": _provider_entry(cfg)}})

    return config_dir


def _provider_entry(cfg):
    model = {"id": cfg.model or "local-model"}
    if cfg.context_window:
        model["contextWindow"] = cfg.context_window
    if cfg.max_tokens:
        model["maxTokens"] = cfg.max_tokens
    if cfg.reasoning:
        model["reasoning"] = True
    entry = {
        "baseUrl": cfg.base_url,
        "api": cfg.api_type,
        # Keyless local servers still need a placeholder: pi hides models that
        # have no auth configured at all.
        "apiKey": cfg.api_key or "local",
        "models": [model],
    }
    if cfg.compat:
        entry["compat"] = cfg.compat
    return entry


def _write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_scratch_dir(prefix="local-agent-eval-"):
    return Path(tempfile.mkdtemp(prefix=prefix))
