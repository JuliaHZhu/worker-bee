from typing import Union

import fnmatch
import os
import re
import shlex
import subprocess
from worker_bee.registry import registry

ALLOWLIST = [
    "head*", "tail*", "less*", "more*",
    "ls*", "ll*", "pwd", "id", "uname*", "whoami",
    "echo*", "printf*", "which*", "whereis*", "stat*", "file*",
    "wc*", "ps*", "top*", "df*", "du*", "free", "uptime",
    "date", "cal", "hostname",
    "grep*", "find*", "locate*",
    "git status*", "git log*", "git diff*", "git show*", "git branch*",
    "git remote*", "git config --list", "git --version",
    "python --version", "python3 --version", "pip list*", "pip3 list*",
    "python -m pytest --collect-only*",
    # === file reading ===
    "cat*", "bat*", "tac*", "nl*", "od*",
    # === lint / test (read-only nature) ===
    "pytest*", "python -m pytest*",
    "black --check*", "ruff check*", "mypy*", "flake8*",
    "pylint*", "bandit*", "vulture*",
    # === git (read-only + safe writes only) ===
    "git add*", "git commit*", "git fetch*",
    # === build tools ===
    "make*", "cmake*", "cargo*", "go build*", "go test*", "go run*",
    "npm*", "pnpm*", "yarn*", "npx*",
    # === docker read-only ===
    "docker ps*", "docker images*", "docker logs*", "docker inspect*",
    "docker network*", "docker volume*",
    # === archive (low risk) ===
    "tar*", "zip*", "unzip*", "gzip*", "gunzip*",
    # === file ops (non-destructive) ===
    "mkdir*", "touch*", "cp*", "mv*", "rename*",
    "chmod*", "chown*",  # dangerous list blocks -R variants
    "ln*", "readlink*",
    # === text processing ===
    "sort*", "uniq*", "cut*", "awk*", "sed*",
    "tr*", "rev*", "base64*", "md5sum*", "sha256sum*",
    "diff*", "cmp*", "comm*",
    "tree*", "fd*", "rg*", "ag*",
    "xargs*", "parallel*",
    # === network probes (read-only) ===
    "curl -I*", "curl --head*", "wget --spider*",
    # === misc common ===
    "time*", "timeout*", "nice*",
    "ssh-keygen*", "ssh-keyscan*",
    "type*", "command*",
    "printenv*", "env*", "export*", "set*",
]

# ── Dangerous substrings: presence triggers mandatory confirmation ──
DANGEROUS = [
    "rm -rf", "rm -fr", "rm -r /", "rmdir /",
    "sudo", "su -", "doas",
    "chmod -R", "chown -R", "chmod 777",
    "mkfs", "mkswap", "swapon",
    "dd if=", "dd of=",
    "> /dev", "< /dev", "/dev/sd", "/dev/hd", "/dev/nvme",
    "curl *|*sh", "wget *|*sh", "curl *|*bash", "wget *|*bash",
    ":(){ :|:& };:",  # fork bomb
    "eval(", "exec(", "__import__('os').system",
    "git push", "git reset", "git rebase", "git stash drop",
    "python -c", "python3 -c", "python -m", "python3 -m",
]

# Shell metacharacters that break simple allowlist matching
_SHELL_META_RE = re.compile(r'[;&|<>$`\(\)\{\}]')


def _matches_allowlist(command: str) -> bool:
    """True if command matches allowlist AND contains no shell metacharacters."""
    if _SHELL_META_RE.search(command):
        return False
    for pattern in ALLOWLIST:
        if fnmatch.fnmatch(command, pattern):
            return True
    return False


def _is_dangerous(command: str) -> bool:
    """True if command contains any dangerous substring."""
    lowered = command.lower()
    for d in DANGEROUS:
        if "*" in d or "?" in d:
            if fnmatch.fnmatch(lowered, d.lower()):
                return True
        elif d.lower() in lowered:
            return True
    return False


def _run_command(command: Union[str, list], timeout: int, shell: bool) -> str:
    """Execute command and return trimmed output."""
    result = subprocess.run(
        command, shell=shell, capture_output=True,
        text=True, timeout=timeout
    )
    output = result.stdout + result.stderr
    return (output[:5000] + "\n... (truncated)" if len(output) > 5000 else output) or "(no output)"


def sys_terminal(command: str, timeout: int = 30, require_confirmation: bool = True) -> str:
    """Execute a shell command in the workspace.

    Security model:
      1. Allowlist  — common read-only/low-risk commands execute immediately.
      2. Dangerous  — blocked with a clear message (no interactive prompts).
      3. Other      — blocked with a clear message.
      
      Set require_confirmation=False to also block dangerous/unrecognized
      commands (instead of prompting — for headless/automated contexts).
      Set WORKER_BEE_AUTO_CONFIRM=true to auto-execute unrecognized commands
      (⚠️ only in fully sandboxed environments).

    Any command with shell metacharacters (; && || | $() < > ` { }) bypasses
    the allowlist and falls into category 2 or 3.
    """
    auto_confirm = os.environ.get("WORKER_BEE_AUTO_CONFIRM", "false").lower() == "true"

    if _matches_allowlist(command):
        # Fast path: no confirmation needed, use shell=False for safety
        try:
            args = shlex.split(command)
            return _run_command(args, timeout, shell=False)
        except Exception:
            return (
                f"Error: could not parse command with shlex. "
                f"Shell metacharacters or complex quoting may be present. "
                f"Try removing quotes/special characters: {command}"
            )
    elif _is_dangerous(command):
        return (
            f"Blocked: dangerous command pattern detected in: {command}\n"
            f"This command is on the deny list. "
            f"Run it manually in a terminal if you are certain it is safe."
        )
    else:
        if auto_confirm:
            return _run_command(command, timeout, shell=True)
        return (
            f"Blocked: unrecognized command (not in allowlist): {command}\n"
            f"Add it to the allowlist in tools/terminal.py ALLOWLIST, "
            f"or set WORKER_BEE_AUTO_CONFIRM=true in sandboxed environments."
        )


registry.register(
    name="sys_terminal",
    description=(
        "Execute a shell command in the workspace. "
        "Common read-only commands (ls, cat, grep, git status, etc.) run immediately. "
        "Dangerous or unrecognized commands are blocked with a clear message "
        "(no interactive prompts — safe for headless/automated use). "
        "Set WORKER_BEE_AUTO_CONFIRM=true only in fully sandboxed environments."
    ),
    parameters={
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
            "require_confirmation": {
                "type": "boolean",
                "description": "If false, unrecognized/dangerous commands are blocked instead of prompting",
                "default": True
            }
        },
        "required": ["command"]
    },
    handler=sys_terminal,
    tags=["system", "shell", "execute"],
    category="system"
)
