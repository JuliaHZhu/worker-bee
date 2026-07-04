#!/usr/bin/env python3
"""
BeeBox Skills Sync — 分体式 Skills 仓库同步到各节点。

用法：
    python scripts/sync_skills.py [--inventory ../inventory.private.yaml] [--skills-repo https://github.com/JuliaHZhu/skills.git]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
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


def local_clone_or_update(skills_url: str, branch: str, local_path: Path) -> None:
    """在本地克隆/更新 skills 仓库。"""
    if (local_path / ".git").exists():
        print(f"[LOCAL] 更新 skills 仓库: {local_path}")
        subprocess.run(["git", "-C", str(local_path), "fetch", "origin"], check=True)
        subprocess.run(["git", "-C", str(local_path), "checkout", branch], check=True)
        subprocess.run(["git", "-C", str(local_path), "pull", "origin", branch], check=True)
    else:
        print(f"[LOCAL] 克隆 skills 仓库到: {local_path}")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--branch", branch, "--depth", "1", skills_url, str(local_path)],
            check=True,
        )


def sync_to_server(
    host: str,
    user: str,
    key_file: str,
    port: int,
    local_skills: Path,
    remote_skills_dir: str,
    required_skills: list[str],
    dry_run: bool,
) -> None:
    """将所需 skills 同步到远程服务器。"""
    if dry_run:
        print(f"  [DRY-RUN] 将要同步 {len(required_skills)} 个 skills 到 {host}")
        return

    # 使用 rsync 同步（比 scp 增量更高效）
    for skill in required_skills:
        src = local_skills / skill
        if not src.exists():
            print(f"  [SKIP] 本地不存在 skill: {skill}")
            continue

        dst = f"{user}@{host}:{remote_skills_dir}/"
        rsync = [
            "rsync",
            "-az",
            "--delete",
            "-e", f"ssh -o StrictHostKeyChecking=accept-new -p {port} -i {os.path.expanduser(key_file)}",
            str(src) + "/",
            dst + skill + "/",
        ]
        print(f"  [SYNC] {skill} -> {host}:{remote_skills_dir}/{skill}")
        result = subprocess.run(rsync, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [WARN] rsync 失败: {result.stderr.strip()}")

    # 远程创建 .skills_index 文件，供各 bee 加载
    index_content = "\n".join(required_skills)
    ssh_cmd(
        host, user, key_file, port,
        f"echo '{index_content}' > {remote_skills_dir}/.index"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="BeeBox Skills 同步工具")
    parser.add_argument("--inventory", default="inventory.yaml")
    parser.add_argument("--bees", default="config/bees.yaml")
    parser.add_argument("--skills-dir", default="skills", help="本地 skills 仓库路径")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    inventory = load_yaml(args.inventory)
    bees_config = load_yaml(args.bees)
    bees_def = {b["role"]: b for b in bees_config.get("bees", [])}
    skills_repo = bees_config.get("skills_repo", {})

    ssh_cfg = inventory.get("ssh", {})
    user = ssh_cfg.get("user", "ubuntu")
    key_file = ssh_cfg.get("key_file", "~/.ssh/id_rsa")
    ssh_port = ssh_cfg.get("port", 22)

    skills_url = skills_repo.get("url", "https://github.com/JuliaHZhu/skills.git")
    skills_branch = skills_repo.get("branch", "main")
    local_skills = Path(args.skills_dir)

    print("=" * 60)
    print("BeeBox Skills Sync — 分体式 Skills 同步")
    print("=" * 60)

    # 1. 本地拉取最新 skills
    local_clone_or_update(skills_url, skills_branch, local_skills)

    # 2. 按节点所需 skills 分发
    for server in inventory.get("servers", []):
        host = server["host"]
        name = server.get("name", host)
        roles = server.get("roles", [])

        # 收集该节点需要的所有 skills
        required_skills: list[str] = []
        for role in roles:
            if role in bees_def:
                required_skills.extend(bees_def[role].get("default_skills", []))
        required_skills = sorted(set(required_skills))

        if not required_skills:
            print(f"\n[{name}] {host} — 无需 skills")
            continue

        print(f"\n[{name}] {host}")
        print(f"  所需 skills: {', '.join(required_skills)}")
        sync_to_server(
            host=host,
            user=user,
            key_file=key_file,
            port=ssh_port,
            local_skills=local_skills,
            remote_skills_dir="~/.beebox/skills",
            required_skills=required_skills,
            dry_run=args.dry_run,
        )

    print("\nSkills 同步完成！")


if __name__ == "__main__":
    main()
