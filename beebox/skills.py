"""BeeBox skills sync — distribute skills from standalone repo to nodes."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .core import ssh_cmd


def local_clone_or_update(url: str, branch: str, local_path: Path) -> None:
    if (local_path / ".git").exists():
        print(f"[LOCAL] updating skills: {local_path}")
        subprocess.run(["git", "-C", str(local_path), "fetch", "origin"], check=True)
        subprocess.run(["git", "-C", str(local_path), "checkout", branch], check=True)
        subprocess.run(["git", "-C", str(local_path), "pull", "origin", branch], check=True)
    else:
        print(f"[LOCAL] cloning skills to: {local_path}")
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
    required_skills: list[str],
    dry_run: bool,
) -> None:
    if dry_run:
        print(f"  [DRY-RUN] sync {len(required_skills)} skills to {host}")
        return

    remote_dir = "~/.beebox/skills"
    for skill in required_skills:
        src = local_skills / skill
        if not src.exists():
            print(f"  [SKIP] local skill missing: {skill}")
            continue
        dst = f"{user}@{host}:{remote_dir}/"
        rsync = [
            "rsync", "-az", "--delete",
            "-e", f"ssh -o StrictHostKeyChecking=accept-new -p {port} -i {os.path.expanduser(key_file)}",
            str(src) + "/",
            dst + skill + "/",
        ]
        print(f"  [SYNC] {skill} -> {host}:{remote_dir}/{skill}")
        result = subprocess.run(rsync, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [WARN] rsync failed: {result.stderr.strip()}")

    index = "\n".join(required_skills)
    ssh_cmd(host, user, key_file, port, f"echo '{index}' > {remote_dir}/.index")
