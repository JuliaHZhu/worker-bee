"""Feishu/Lark tool — thin wrapper around lark-cli.

Safety is a single boolean in config.json (lark_allow_write).
No command prefix lists, no hardcoded blocklists. lark-cli's own
auth and scopes handle actual permission enforcement.
"""
from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

from worker_bee.registry import registry

_LARK_CLI = str(Path.home() / ".local" / "bin" / "lark-cli")
_CONFIG = Path.home() / ".worker-bee" / "config.json"

# ponytail: explicit allowlist of read-only lark-cli subcommands.
# Ceiling: any read-only subcommand not listed here will be blocked when
# lark_allow_write=false. Add new ones as they are discovered.
_READ_SUBCOMMANDS = frozenset({
    # contact
    "+search-user", "+get-user", "+list-user",
    # im
    "+chat-list", "+chat-search", "+chat-messages-list",
    "+messages-list", "+messages-search",
    "+group-info", "+group-list",
    # docs
    "+fetch", "+search", "+list", "+get",
    # drive
    "+download", "+search", "+list", "+get",
    # calendar
    "+agenda", "+event-get", "+list",
    # base / mail / minutes / okr / task
    "+list", "+get", "+search",
    # misc
    "help", "version", "--help", "-h",
})


def _allow_write() -> bool:
    """Check if lark write operations are enabled in config."""
    try:
        cfg = json.loads(_CONFIG.read_text())
        return cfg.get("lark_allow_write", False)
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def feishu_lark(command: str) -> str:
    """Run a lark-cli command and return its output.

    Write operations (send, create, update, delete) require
    lark_allow_write=true in config.json. Set during 'wb setup'.
    """
    cmd = command.strip()

    try:
        args = shlex.split(cmd)
    except ValueError as e:
        return f"Error parsing command: {e}"

    # Check write permission
    if not _allow_write():
        first_word = args[0].lower() if args else ""
        sub = args[1].lower() if len(args) > 1 else ""
        is_read = (
            first_word == "doctor"
            or (first_word == "api" and sub in ("get", "head"))
            or sub in _READ_SUBCOMMANDS
            or first_word not in (
                "calendar", "contact", "docs", "drive", "im", "base",
                "mail", "minutes", "okr", "task", "doctor", "api",
            )
        )
        if not is_read:
            return (
                "Write operations are disabled. "
                "Enable with: wb setup → lark_allow_write: true, "
                "or edit ~/.worker-bee/config.json manually."
            )

    try:
        result = subprocess.run(
            [_LARK_CLI] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return f"lark-cli not found at {_LARK_CLI}. Install: pip install lark-cli"
    except subprocess.TimeoutExpired:
        return f"lark-cli timed out after 30s: {cmd}"

    output = result.stdout
    if result.stderr:
        output += "\n[stderr]\n" + result.stderr

    if len(output) > 4000:
        output = output[:4000] + "\n…(truncated)"

    return output


registry.register(
    name="feishu_lark",
    description=(
        "Execute a Feishu/Lark CLI command via lark-cli. "
        "Read commands (search, fetch, list, agenda) always work. "
        "Write commands (send, create, update) require lark_allow_write=true "
        "in ~/.worker-bee/config.json (set during 'wb setup'). "
        "See the lark skill for command patterns."
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
        },
        "required": ["command"],
    },
    handler=feishu_lark,
    tags=["feishu", "lark", "messaging", "docs", "calendar", "contact"],
    category="feishu",
)
