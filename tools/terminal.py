import re
import subprocess
from registry import registry


def sys_terminal(command: str, timeout: int = 30) -> str:
    """Execute a shell command in the workspace."""
    # Blocklist of dangerous command patterns (case-insensitive, covers variants)
    _DANGEROUS_PATTERNS = [
        # Destructive file operations
        r"\brm\b.*-(r|R|\-[\w]*f)",       # rm -rf, rm -Rf, rm --recursive --force
        r"\brm\b.+/(bin|boot|dev|etc|home|lib|proc|root|sbin|sys|tmp|usr|var)\b",
        # Privilege escalation
        r"\bsudo\b",
        r"\bsu\s+-",
        # Permission changes on system dirs
        r"\bchmod\s+-R",
        r"\bchown\s+-R",
        # Disk/format destruction
        r"\bmkfs\.?",
        r"\bdd\b.*if=",
        r"\b(fdisk|parted|gparted)\b",
        # Dangerous redirects
        r">\s*/dev/[sh]d[a-z]",
        r">\s*/dev/null",                  # sometimes used maliciously to silence rm
        # Remote code execution
        r"\bcurl\b.*\|\s*(ba)?sh\b",
        r"\bwget\b.*\|\s*(ba)?sh\b",
        r"\beval\s*\$",
        r"\beval\s*\`",
        # Reverse shells
        r"\b(nc|netcat|ncat)\b.*-e\s+(ba)?sh",
        r"\bbash\b.*-i\b.*>&\s*/dev/tcp",
        r"\bpython\d?\b.*-c.*socket.*connect",
    ]

    lowered = command.lower()
    matched = []
    for pat in _DANGEROUS_PATTERNS:
        if re.search(pat, lowered):
            matched.append(pat)
    if matched:
        confirm = input(
            f"⚠️ Dangerous command detected:\n  {command}\n"
            f"Patterns matched: {len(matched)}\nExecute? [y/N]: "
        )
        if confirm.strip().lower() != "y":
            return "Cancelled by user."

    result = subprocess.run(
        command, shell=True, capture_output=True,
        text=True, timeout=timeout
    )
    output = result.stdout + result.stderr
    return (output[:5000] + "\n... (truncated)" if len(output) > 5000 else output) or "(no output)"


registry.register(
    name="sys_terminal",
    description=(
        "Execute a shell command in the workspace. "
        "Use carefully — dangerous commands require confirmation. "
        "Prefer fs_read_file or fs_search_files for code inspection before editing."
    ),
    parameters={
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30}
        },
        "required": ["command"]
    },
    handler=sys_terminal,
    tags=["system", "shell", "execute"],
    category="system"
)
