import logging

"""BeeBox skills sync — distribute skills from standalone repo to nodes (seed mode)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .core import ssh_cmd

logger = logging.getLogger(__name__)


def local_clone_or_update(url: str, branch: str, local_path: Path) -> None:
    if (local_path / ".git").exists():
        logger.info("[LOCAL] updating skills: %s", local_path)
        subprocess.run(["git", "-C", str(local_path), "fetch", "origin"], check=True)
        subprocess.run(["git", "-C", str(local_path), "checkout", branch], check=True)
        subprocess.run(["git", "-C", str(local_path), "pull", "origin", branch], check=True)
    else:
        logger.info("[LOCAL] cloning skills to: %s", local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--branch", branch, "--depth", "1", url, str(local_path)],
            check=True,
        )


def sync_to_server(
    host: str,
    user: str,
    key_file: str,
    port: int,
    local_skills: Path,
    server_name: str,
    dry_run: bool,
) -> None:
    """Sync all skills to a remote server (seed mode — no per-role filtering)."""
    if dry_run:
        logger.info("[DRY-RUN] sync skills to %s@%s", server_name, host)
        return

    remote_dir = "~/.beebox/skills"

    # Sync entire skills directory
    src = str(local_skills) + "/"
    dst = f"{user}@{host}:{remote_dir}/"
    rsync = [
        "rsync", "-az", "--delete",
        "-e", f"ssh -o StrictHostKeyChecking=accept-new -p {port} -i {os.path.expanduser(key_file)}",
        src,
        dst,
    ]
    logger.info("[SYNC] skills → %s@%s:%s", server_name, host, remote_dir)
    result = subprocess.run(rsync, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning("[WARN] rsync failed: %s", result.stderr.strip())

    # Write index
    skill_files = sorted(
        [p.name for p in local_skills.glob("*.md") if not p.name.startswith(".")]
    )
    index = "\n".join(skill_files)
    ssh_cmd(host, user, key_file, port, f"echo '{index}' > {remote_dir}/.index")
