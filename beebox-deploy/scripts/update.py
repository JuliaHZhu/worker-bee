#!/usr/bin/env python3
"""
BeeBox Update — 批量更新已部署的 Agent，并收集更新日志。

用法：
    python scripts/update.py [--inventory ../inventory.private.yaml] [--role worker] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ssh_cmd(host: str, user: str, key_file: str, port: int, cmd: str) -> tuple[int, str, str]:
    ssh = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=10",
        "-p", str(port),
        "-i", os.path.expanduser(key_file),
        f"{user}@{host}",
        cmd,
    ]
    result = subprocess.run(ssh, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def update_bee(
    host: str,
    user: str,
    key_file: str,
    port: int,
    role: str,
    dry_run: bool,
) -> dict:
    """更新单个 bee，返回更新日志条目。"""
    app_dir = f"~/.beebox/apps/{role}"
    venv_dir = f"~/.beebox/venvs/{role}"
    log_dir = "~/.beebox/logs"

    cmd = (
        f"cd {app_dir} && "
        "OLD_HEAD=$(git rev-parse HEAD) && "
        "git fetch origin && "
        "git pull origin $(git rev-parse --abbrev-ref HEAD) && "
        "NEW_HEAD=$(git rev-parse HEAD) && "
        "if [ \"$OLD_HEAD\" != \"$NEW_HEAD\" ]; then "
        "  echo 'CHANGED' && "
        "  echo \"$OLD_HEAD -> $NEW_HEAD\" && "
        "  git log --oneline $OLD_HEAD..$NEW_HEAD; "
        "else "
        "  echo 'NO_CHANGE'; "
        "fi"
    )

    if dry_run:
        print(f"  [DRY-RUN] {role}@{host}: git pull")
        return {"host": host, "role": role, "changed": False, "dry_run": True}

    rc, out, err = ssh_cmd(host, user, key_file, port, cmd)

    changed = "CHANGED" in out
    lines = [l for l in out.splitlines() if l not in ("CHANGED", "NO_CHANGE")]
    commits = [l for l in lines if " -> " not in l]
    head_change = next((l for l in lines if " -> " in l), "")

    if rc != 0:
        print(f"  [ERROR] {role}@{host} 更新失败: {err}")
        return {"host": host, "role": role, "changed": False, "error": err}

    if changed:
        print(f"  [UPDATED] {role}@{host}: {head_change}")
        for c in commits:
            print(f"    {c}")

        # 重新安装依赖
        install_cmd = (
            f"source {venv_dir}/bin/activate && "
            "pip install --upgrade pip -q && "
            f"if [ -f {app_dir}/requirements.txt ]; then pip install -r {app_dir}/requirements.txt -q; fi && "
            f"if [ -f {app_dir}/pyproject.toml ]; then pip install -e {app_dir} -q; fi"
        )
        rc2, out2, err2 = ssh_cmd(host, user, key_file, port, install_cmd)
        if rc2 != 0:
            print(f"  [WARN] {role}@{host} 依赖重装失败: {err2}")
    else:
        print(f"  [OK] {role}@{host}: 已是最新")

    return {
        "host": host,
        "role": role,
        "changed": changed,
        "head_change": head_change,
        "commits": commits,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def save_update_log(log_dir: Path, entries: list[dict]) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"update-{timestamp}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({"timestamp": timestamp, "entries": entries}, f, ensure_ascii=False, indent=2)
    print(f"\n[LOG] 更新日志已保存: {log_file}")
    return log_file


def main() -> None:
    parser = argparse.ArgumentParser(description="BeeBox 批量更新工具")
    parser.add_argument("--inventory", default="inventory.yaml")
    parser.add_argument("--role", help="仅更新指定角色 (如 worker)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    inventory = load_yaml(args.inventory)
    ssh_cfg = inventory.get("ssh", {})
    user = ssh_cfg.get("user", "ubuntu")
    key_file = ssh_cfg.get("key_file", "~/.ssh/id_rsa")
    ssh_port = ssh_cfg.get("port", 22)

    print("=" * 60)
    print("BeeBox Update — 分体式 Agent 批量更新")
    print("=" * 60)

    entries: list[dict] = []
    for server in inventory.get("servers", []):
        host = server["host"]
        name = server.get("name", host)
        roles = server.get("roles", [])

        if args.role and args.role not in roles:
            continue

        print(f"\n[{name}] {host}")
        for role in roles:
            if args.role and role != args.role:
                continue
            entry = update_bee(host, user, key_file, ssh_port, role, args.dry_run)
            entries.append(entry)

    if not args.dry_run:
        save_update_log(Path("logs/updates"), entries)

    changed_count = sum(1 for e in entries if e.get("changed"))
    print(f"\n{'=' * 60}")
    print(f"更新完成: {changed_count}/{len(entries)} 个 bee 有变更")
    print("=" * 60)


if __name__ == "__main__":
    main()
