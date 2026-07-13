"""BeeBox update — bulk git pull + dependency reinstall (seed mode)."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from .core import ssh_cmd

logger = logging.getLogger(__name__)


def update_bee(
    host: str,
    user: str,
    key_file: str,
    port: int,
    server_name: str,
    dry_run: bool,
) -> dict:
    """Update worker-bee seed on a remote host. All servers run the same code."""
    app_dir = "~/.beebox/worker-bee"
    venv_dir = "~/.beebox/venv"
    # Capture OLD_HEAD in Python so rollback can use it later
    old_head_cmd = f"cd {app_dir} && git rev-parse HEAD"
    rc0, old_head, _ = ssh_cmd(host, user, key_file, port, old_head_cmd)
    old_head = old_head.strip() if rc0 == 0 else ""

    cmd = (
        f"cd {app_dir} && "
        "git fetch origin && "
        "git pull origin $(git rev-parse --abbrev-ref HEAD) && "
        "NEW_HEAD=$(git rev-parse HEAD) && "
        f"if [ \"{old_head}\" != \"$NEW_HEAD\" ]; then "
        f"  echo 'CHANGED' && echo \"{old_head} -> $NEW_HEAD\" && git log --oneline {old_head}..$NEW_HEAD; "
        "else echo 'NO_CHANGE'; fi"
    )

    if dry_run:
        logger.info("  [DRY-RUN] %s@%s: git pull", server_name, host)
        return {"host": host, "name": server_name, "changed": False, "dry_run": True}

    rc, out, _ = ssh_cmd(host, user, key_file, port, cmd)
    changed = "CHANGED" in out
    lines = [l for l in out.splitlines() if l not in ("CHANGED", "NO_CHANGE")]
    commits = [l for l in lines if " -> " not in l]
    head_change = next((l for l in lines if " -> " in l), "")

    if rc != 0:
        logger.error("  [ERROR] %s@%s update failed", server_name, host)
        return {"host": host, "name": server_name, "changed": False, "error": out}

    if changed:
        logger.info("  [UPDATED] %s@%s: %s", server_name, host, head_change)
        for c in commits:
            logger.info("    %s", c)
        install_cmd = (
            f"source {venv_dir}/bin/activate && "
            "pip install --upgrade pip -q && "
            f"if [ -f {app_dir}/requirements.txt ]; then pip install -r {app_dir}/requirements.txt -q; fi && "
            f"if [ -f {app_dir}/pyproject.toml ]; then pip install -e {app_dir} -q; fi"
        )
        rc2, _, err2 = ssh_cmd(host, user, key_file, port, install_cmd)
        if rc2 != 0:
            logger.warning("  [WARN] %s@%s reinstall failed: %s", server_name, host, err2)
            # Rollback to previous commit on install failure
            rollback_cmd = f"cd {app_dir} && git checkout {old_head}"
            ssh_cmd(host, user, key_file, port, rollback_cmd)
            logger.warning("  [ROLLBACK] %s@%s reverted to %s", server_name, host, old_head)
            return {
                "host": host,
                "name": server_name,
                "changed": False,
                "error": f"install failed: {err2}",
                "rollback": True,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
    else:
        logger.info("  [OK] %s@%s: up to date", server_name, host)

    return {
        "host": host,
        "name": server_name,
        "changed": changed,
        "head_change": head_change,
        "commits": commits,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def save_log(log_dir: Path, entries: list[dict]) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"update-{timestamp}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({"timestamp": timestamp, "entries": entries}, f, ensure_ascii=False, indent=2)
    logger.info("[LOG] update log saved: %s", log_file)
    return log_file
