import subprocess
from registry import registry


def sys_terminal(command: str, timeout: int = 30) -> str:
    """Execute a shell command in the workspace."""
    dangerous = ["rm -rf", "sudo", "chmod -R", "chown -R", "mkfs", "dd if=", "> /dev"]
    if any(d in command.lower() for d in dangerous):
        confirm = input(f"⚠️ Dangerous command: {command}\nExecute? [y/N]: ")
        if confirm.lower() != "y":
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
