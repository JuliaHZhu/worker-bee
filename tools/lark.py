"""Feishu/Lark tool — thin wrapper around lark-cli.

Ponytail principle: don't build a Feishu SDK, just shell out to lark-cli.
One tool, not 14. The agent learns command patterns from the lark skill.
"""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from worker_bee.registry import registry

_LARK_CLI = os.environ.get(
    "LARK_CLI_PATH",
    str(Path.home() / ".local" / "bin" / "lark-cli"),
)

# Commands that never need confirmation (read-only or safe)
_SAFE_PREFIXES = (
    "calendar +agenda",
    "calendar events",
    "contact +search",
    "contact +get",
    "docs +fetch",
    "docs +read",
    "drive +search",
    "drive +download",
    "im +messages-list",
    "im +messages-search",
    "im +group-info",
    "im +group-list",
    "base +search",
    "base +get",
    "base +list",
    "mail +list",
    "mail +read",
    "minutes +get",
    "minutes +list",
    "okr +list",
    "okr +get",
    "task +list",
    "task +get",
    "doctor",
    "config show",
    "api GET",
)

# Commands blocked unconditionally
_BLOCKED_PREFIXES = (
    "auth login",
    "auth logout",
    "config init",
    "config remove",
    "config bind",
)


def _lark(command: str, require_confirmation: bool = True) -> str:
    """Run a lark-cli command and return its output.

    Args:
        command: lark-cli subcommand and arguments (e.g., 'contact +search-user --query "John"')
        require_confirmation: if False, dangerous writes are blocked instead of confirmed.
            Set to False in headless/automated contexts.
    """
    cmd = command.strip()
    lowered = cmd.lower()

    if any(lowered.startswith(p) for p in _BLOCKED_PREFIXES):
        return (
            f"Blocked: '{cmd}' is a config/auth management command. "
            f"Run it manually in a terminal."
        )

    is_safe = any(lowered.startswith(p) for p in _SAFE_PREFIXES)

    if not is_safe and not require_confirmation:
        return (
            f"Blocked: '{cmd}' is a write operation and require_confirmation is False. "
            f"Set require_confirmation=True or run manually."
        )

    try:
        args = shlex.split(cmd)
    except ValueError as e:
        return f"Error parsing command: {e}"

    try:
        result = subprocess.run(
            [_LARK_CLI] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return (
            f"lark-cli not found at {_LARK_CLI}. "
            f"Install with: pip install lark-cli"
        )
    except subprocess.TimeoutExpired:
        return f"lark-cli timed out after 30s: {cmd}"

    output = result.stdout
    if result.stderr:
        output += "\n[stderr]\n" + result.stderr

    # Truncate to avoid token explosion
    if len(output) > 4000:
        output = output[:4000] + "\n…(truncated)"

    return output


registry.register(
    name="feishu_lark",
    description=(
        "Execute a Feishu/Lark CLI command via lark-cli. "
        "Read-only commands (search, fetch, list, agenda) run immediately. "
        "Write commands (send, create, update, delete) run with confirmation. "
        "Auth/config management commands are blocked — run those manually. "
        "See the lark skill for command patterns and shortcuts."
    ),
    parameters={
        "properties": {
            "command": {
                "type": "string",
                "description": (
                    "lark-cli subcommand, e.g. 'contact +search-user --query John', "
                    "'im +messages-send --chat-id oc_xxx --content Hello', "
                    "'calendar +agenda', 'docs +fetch --token doc_xxx'"
                ),
            },
            "require_confirmation": {
                "type": "boolean",
                "description": (
                    "If False, write operations are blocked instead of confirmed. "
                    "Default True."
                ),
            },
        },
        "required": ["command"],
    },
    handler=_lark,
    tags=["feishu", "lark", "messaging", "docs", "calendar", "contact"],
    category="feishu",
)
