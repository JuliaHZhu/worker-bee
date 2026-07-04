"""BeeBox log collector — gather logs from all nodes (seed mode)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .core import ssh_cmd


def collect_git_logs(host, user, key_file, port, server_name):
    """Collect git log from worker-bee seed on a remote host."""
    app_dir = "~/.beebox/worker-bee"
    cmd = (
        f"if [ -d {app_dir}/.git ]; then cd {app_dir} && git log --oneline -20; "
        f"else echo '(not installed)'; fi"
    )
    rc, out, _ = ssh_cmd(host, user, key_file, port, cmd)
    return out.strip().splitlines() if rc == 0 else []


def collect_pipeline_logs(host, user, key_file, port, server_name, since):
    """Collect pipeline logs from a remote host."""
    cmd = (
        f"journalctl --user -u bee-worker --since '{since}' --no-pager -q 2>/dev/null || "
        f"cat ~/.beebox/logs/worker-bee.log 2>/dev/null || echo '(no log found)'"
    )
    rc, out, _ = ssh_cmd(host, user, key_file, port, cmd)
    return out.strip().splitlines() if rc == 0 else []


def collect_nats_logs(host, user, key_file, port):
    """Collect NATS server logs."""
    cmd = "cat ~/.beebox/nats.log 2>/dev/null | tail -50 || echo '(no nats log)'"
    rc, out, _ = ssh_cmd(host, user, key_file, port, cmd)
    return out.strip().splitlines() if rc == 0 else []


def save(collect_dir: Path, inventory: dict, all_logs: dict, since: str) -> Path:
    collect_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    json_file = collect_dir / f"collected-{timestamp}.json"
    txt_file = collect_dir / f"collected-{timestamp}.txt"

    payload = {
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "since": since,
        "nodes": all_logs,
    }
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(f"BeeBox Log Collection — {payload['collected_at']}\n")
        f.write(f"Since: {since}\n{'=' * 60}\n\n")
        for node_name, node_logs in all_logs.items():
            f.write(f"[{node_name}]\n{'-' * 40}\n")
            if node_logs.get("git_logs"):
                f.write("  [git log] (last 20):\n")
                for line in node_logs["git_logs"]:
                    f.write(f"    {line}\n")
                f.write("\n")
            if node_logs.get("pipeline_logs"):
                f.write("  [pipeline log]:\n")
                for line in node_logs["pipeline_logs"][-20:]:
                    f.write(f"    {line}\n")
                f.write("\n")
            if node_logs.get("nats_logs"):
                f.write("  [NATS] log (last 50):\n")
                for line in node_logs["nats_logs"]:
                    f.write(f"    {line}\n")
                f.write("\n")
            f.write("\n")

    print(f"[LOG] saved:\n  JSON: {json_file}\n  TXT:  {txt_file}")
    return json_file
