"""BeeBox shared utilities."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml


def load_yaml(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ssh_cmd(
    host: str,
    user: str,
    key_file: str,
    port: int,
    cmd: str,
    capture: bool = True,
) -> tuple[int, str, str]:
    """Run a command on a remote server via SSH."""
    ssh = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=10",
        "-p", str(port),
        "-i", os.path.expanduser(key_file),
        f"{user}@{host}",
        cmd,
    ]
    if capture:
        result = subprocess.run(ssh, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    result = subprocess.run(ssh)
    return result.returncode, "", ""
