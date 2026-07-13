"""BeeBox shared utilities."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


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
    strict_host_key_checking: str = "accept-new",
    known_hosts_file: str = "",
) -> tuple[int, str, str]:
    """Run a command on a remote server via SSH.

    Security note: default ``accept-new`` allows MITM on first connection.
    For production, set ``strict_host_key_checking='yes'`` and provide
    a ``known_hosts_file``.
    """
    ssh = [
        "ssh",
        "-o", f"StrictHostKeyChecking={strict_host_key_checking}",
        "-o", "ConnectTimeout=10",
        "-p", str(port),
        "-i", os.path.expanduser(key_file),
    ]
    if known_hosts_file:
        ssh.extend(["-o", f"UserKnownHostsFile={os.path.expanduser(known_hosts_file)}"])
    ssh.extend([f"{user}@{host}", cmd])
    if capture:
        result = subprocess.run(ssh, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    result = subprocess.run(ssh)
    return result.returncode, "", ""
