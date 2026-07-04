"""BeeBox update — bulk git pull + dependency reinstall (seed mode)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .core import ssh_cmd


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
    cmd = (
        f"cd {app_dir} && "
        "OLD_HEAD=$(git rev-parse HEAD) && "
        "git fetch origin && "
        "git pull origin $(git rev-parse --abbrev-ref HEAD) && "
        "NEW_HEAD=$(git rev-parse HEAD) && "
        "if [ \"$OLD_HEAD\" != \"$NEW_HEAD\" ]; then "
        "  echo 'CHANGED' && echo \"$OLD_HEAD -> $NEW_HEAD\" && git log --oneline $OLD_HEAD..$NEW_HEAD; "
        "else echo 'NO_CHANGE'; fi"
    )

    if dry_run:
        print(f"  [DRY-RUN] {server_name}@{host}: git pull")
        return {"host": host, "name": server_name, "changed": False, "dry_run": True}

    rc, out, _ = ssh_cmd(host, user, key_file, port, cmd)
    changed = "CHANGED" in out
    lines = [l for l in out.splitlines() if l not in ("CHANGED", "NO_CHANGE")]
    commits = [l for l in lines if " -> " not in l]
    head_change = next((l for l in lines if " -> " in l), "")

    if rc != 0:
        print(f"  [ERROR] {server_name}@{host} update failed")
        return {"host": host, "name": server_name, "changed": False, "error": out}

    if changed:
        print(f"  [UPDATED] {server_name}@{host}: {head_change}")
        for c in commits:
            print(f"    {c}")
        install_cmd = (
            f"source {venv_dir}/bin/activate && "
            "pip install --upgrade pip -q && "
            f"if [ -f {app_dir}/requirements.txt ]; then pip install -r {app_dir}/requirements.txt -q; fi && "
            f"if [ -f {app_dir}/pyproject.toml ]; then pip install -e {app_dir} -q; fi"
        )
        rc2, _, err2 = ssh_cmd(host, user, key_file, port, install_cmd)
        if rc2 != 0:
            print(f"  [WARN] {server_name}@{host} reinstall failed: {err2}")
    else:
        print(f"  [OK] {server_name}@{host}: up to date")

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
    print(f"\n[LOG] update log saved: {log_file}")
    return log_file
