#!/usr/bin/env python3
"""
BeeBox Log Collector — 从所有节点收集运行日志和更新日志。

收集内容：
  1. 各 bee 的 git 更新历史（update log）
  2. systemd / journalctl 运行日志（pipeline log）
  3. NATS 服务日志
  4. 本地合并后按时间归档

用法：
    python scripts/collect_logs.py [--inventory ../inventory.private.yaml] [--since "1 hour ago"]
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


def collect_git_logs(host: str, user: str, key_file: str, port: int, roles: list[str]) -> dict:
    """收集各 bee 的 git log。"""
    logs = {}
    for role in roles:
        app_dir = f"~/.beebox/apps/{role}"
        cmd = (
            f"if [ -d {app_dir}/.git ]; then "
            f"  cd {app_dir} && git log --oneline -20; "
            f"else echo '(not installed)'; fi"
        )
        rc, out, _ = ssh_cmd(host, user, key_file, port, cmd)
        logs[role] = out.strip().splitlines() if rc == 0 else [f"error: rc={rc}"]
    return logs


def collect_pipeline_logs(host: str, user: str, key_file: str, port: int, roles: list[str], since: str) -> dict:
    """收集 systemd / journalctl 运行日志。"""
    logs = {}
    for role in roles:
        # 尝试 journalctl
        cmd = (
            f"journalctl --user -u bee-{role} --since '{since}' --no-pager -q 2>/dev/null || "
            f"cat ~/.beebox/logs/{role}.log 2>/dev/null || "
            f"echo '(no log found)'"
        )
        rc, out, _ = ssh_cmd(host, user, key_file, port, cmd)
        logs[role] = out.strip().splitlines() if rc == 0 else []
    return logs


def collect_nats_logs(host: str, user: str, key_file: str, port: int) -> list[str]:
    cmd = "cat ~/.beebox/nats.log 2>/dev/null | tail -50 || echo '(no nats log)'"
    rc, out, _ = ssh_cmd(host, user, key_file, port, cmd)
    return out.strip().splitlines() if rc == 0 else []


def save_logs(collect_dir: Path, inventory: dict, all_logs: dict, since: str) -> Path:
    collect_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_file = collect_dir / f"collected-{timestamp}.json"

    payload = {
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "since": since,
        "nodes": all_logs,
    }
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # 同时输出一份可读文本
    text_file = collect_dir / f"collected-{timestamp}.txt"
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(f"BeeBox Log Collection — {payload['collected_at']}\n")
        f.write(f"Since: {since}\n")
        f.write("=" * 60 + "\n\n")
        for node_name, node_logs in all_logs.items():
            f.write(f"[{node_name}]\n")
            f.write("-" * 40 + "\n")
            for role, entries in node_logs.get("git_logs", {}).items():
                f.write(f"  [{role}] git log (last 20):\n")
                for line in entries:
                    f.write(f"    {line}\n")
                f.write("\n")
            for role, entries in node_logs.get("pipeline_logs", {}).items():
                if entries:
                    f.write(f"  [{role}] pipeline log:\n")
                    for line in entries[-20:]:
                        f.write(f"    {line}\n")
                    f.write("\n")
            if node_logs.get("nats_logs"):
                f.write("  [NATS] log (last 50):\n")
                for line in node_logs["nats_logs"]:
                    f.write(f"    {line}\n")
                f.write("\n")
            f.write("\n")

    print(f"[LOG] 日志已保存:\n  JSON: {log_file}\n  TXT:  {text_file}")
    return log_file


def main() -> None:
    parser = argparse.ArgumentParser(description="BeeBox 日志收集工具")
    parser.add_argument("--inventory", default="inventory.yaml")
    parser.add_argument("--since", default="1 hour ago", help="journalctl --since 参数")
    parser.add_argument("--output", default="logs/collected", help="本地收集目录")
    args = parser.parse_args()

    inventory = load_yaml(args.inventory)
    ssh_cfg = inventory.get("ssh", {})
    user = ssh_cfg.get("user", "ubuntu")
    key_file = ssh_cfg.get("key_file", "~/.ssh/id_rsa")
    ssh_port = ssh_cfg.get("port", 22)

    print("=" * 60)
    print("BeeBox Log Collector — 分体式 Agent 日志收集")
    print("=" * 60)

    all_logs: dict[str, dict] = {}
    for server in inventory.get("servers", []):
        host = server["host"]
        name = server.get("name", host)
        roles = server.get("roles", [])

        print(f"\n[{name}] {host} ...")
        git_logs = collect_git_logs(host, user, key_file, ssh_port, roles)
        pipeline_logs = collect_pipeline_logs(host, user, key_file, ssh_port, roles, args.since)
        nats_logs = collect_nats_logs(host, user, key_file, ssh_port)

        all_logs[name] = {
            "host": host,
            "git_logs": git_logs,
            "pipeline_logs": pipeline_logs,
            "nats_logs": nats_logs,
        }

        total_lines = sum(len(v) for v in git_logs.values())
        total_lines += sum(len(v) for v in pipeline_logs.values())
        total_lines += len(nats_logs)
        print(f"  收集到 {total_lines} 行日志")

    save_logs(Path(args.output), inventory, all_logs, args.since)
    print("\n收集完成！")


if __name__ == "__main__":
    main()
