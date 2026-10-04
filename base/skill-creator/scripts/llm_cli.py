#!/usr/bin/env python3
"""Which LLM CLI skill-creator shells out to.

Historically every call ran `claude -p`.  This module keeps that path working
but defaults to `pi`, because that is the CLI installed on this machine.

Set `SKILL_CREATOR_CLI=claude` to go back to Claude Code.  Provider and model
come from `--provider`/`--model`, else `PI_PROVIDER`/`PI_MODEL`, else the
defaults below.
"""

from __future__ import annotations

import os
import subprocess

CLI_ENV = "SKILL_CREATOR_CLI"
DEFAULT_CLI = "pi"
DEFAULT_PI_PROVIDER = "opencode-go"


def active_cli() -> str:
    """Return the CLI to shell out to: ``pi`` (default) or ``claude``."""
    value = os.environ.get(CLI_ENV, DEFAULT_CLI).strip().lower()
    return value or DEFAULT_CLI


def pi_provider(explicit: str | None = None) -> str:
    return (explicit or os.environ.get("PI_PROVIDER") or DEFAULT_PI_PROVIDER).strip()


def pi_model(explicit: str | None = None) -> str | None:
    value = explicit or os.environ.get("PI_MODEL")
    return value.strip() if value else None


def pi_launch_args(explicit_provider: str | None = None, explicit_model: str | None = None) -> list[str]:
    """Return the provider/model flags for a pi invocation.

    pi rejects `--provider` without `--model`, so when no model is configured
    we pass neither and let pi use its own default.  Callers that care about
    reproducibility (the trigger eval, which should run on the same model the
    user actually uses) should pass an explicit model.
    """
    model = pi_model(explicit_model)
    if not model:
        return []
    return ["--provider", pi_provider(explicit_provider), "--model", model]


def _clean_env() -> dict[str, str]:
    # claude refuses to nest inside a Claude Code session; the guard is for
    # interactive terminals, so drop it for programmatic subprocess use.
    return {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}


def run_text(
    prompt: str,
    model: str | None = None,
    provider: str | None = None,
    timeout: int = 300,
) -> str:
    """Send *prompt* on stdin and return the model's plain-text answer."""
    cli = active_cli()
    if cli == "claude":
        cmd = ["claude", "-p", "--output-format", "text"]
        if model:
            cmd.extend(["--model", model])
    else:
        cmd = [
            "pi",
            "--print",
            "--no-session",
            "--no-skills",
            "--mode", "text",
        ]
        cmd.extend(pi_launch_args(provider, model))

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            env=_clean_env(),
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"{cmd[0]} is not installed: {exc}") from exc

    if result.returncode != 0:
        raise RuntimeError(f"{cmd[0]} exited {result.returncode}\nstderr: {result.stderr}")
    return result.stdout.strip()
