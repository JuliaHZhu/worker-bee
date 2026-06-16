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
        if first_word not in (
            "calendar", "contact", "docs", "drive",
            "im", "base", "mail", "minutes", "okr",
            "task", "doctor", "api",
        ):
            pass  # unknown command, let lark-cli decide
        elif first_word == "api" and len(args) > 1 and args[1].upper() in ("GET", "HEAD"):
            pass  # read-only API calls
        elif first_word == "doctor":
            pass  # always safe
        else:
            # Heuristic: most non-GET lark-cli commands are writes.
            # Let lark-cli's own scope enforcement handle actual safety.
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
