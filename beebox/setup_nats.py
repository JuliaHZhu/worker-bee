#!/usr/bin/env python3
"""生成 NATS 集群配置 + 分发到 8 台机。

用法：
    1. 改下面 IPS 为 8 台机的实际内网 IP
    2. python3 beebox/setup_nats.py

会在每台机上安装 nats-server、写配置、启动集群。
"""

import subprocess, sys, os

# ═══════════════════════════════════════════
# 改这行：8 台机的内网 IP
IPS = [
    "192.168.1.101",
    "192.168.1.102",
    "192.168.1.103",
    "192.168.1.104",
    "192.168.1.105",
    "192.168.1.106",
    "192.168.1.107",
    "192.168.1.108",
]
# ═══════════════════════════════════════════

SSH_USER = "ubuntu"

def gen_config(node_name: str, node_ip: str, all_ips: list[str]) -> str:
    routes = ",\n    ".join(f"nats://{ip}:6222" for ip in all_ips)
    return f"""# NATS 集群 — {node_name}
server_name: "{node_name}"
port: 4222
http_port: 8222
max_payload: 1MB
max_pending: 10MB

cluster {{
  name: worker-bee-cluster
  listen: 0.0.0.0:6222
  routes = [
    {routes}
  ]
}}

jetstream {{
  store_dir: "/home/ubuntu/.worker-bee/nats-jetstream"
  max_memory_store: 256MB
  max_file_store: 2GB
}}

debug: false
trace: false
logtime: true
"""


def run_ssh(ip: str, cmd: str) -> str:
    """Run a command on a remote machine via SSH."""
    full = f"ssh -o StrictHostKeyChecking=no {SSH_USER}@{ip} '{cmd}'"
    print(f"  [{ip}] {cmd[:80]}...")
    r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"  ❌ [{ip}] FAILED: {r.stderr.strip()}")
    else:
        print(f"  ✅ [{ip}] OK")
    return r.stdout.strip()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        # 只生成配置，不执行
        for i, ip in enumerate(IPS):
            name = f"bee-{i+1:02d}"
            print(f"\n{'='*60}\n{name} ({ip})\n{'='*60}")
            print(gen_config(name, ip, IPS))
        return

    print(f"即将配置 {len(IPS)} 台 NATS Server:\n  " + "\n  ".join(IPS))
    ans = input("继续？[y/N] ").strip().lower()
    if ans != "y":
        print("取消")
        return

    for i, ip in enumerate(IPS):
        name = f"bee-{i+1:02d}"
        config = gen_config(name, ip, IPS)
        print(f"\n── {name} ({ip}) ──")

        # 1. 安装 nats-server（官方 release + SHA256 校验）
        NATS_VERSION = "2.10.24"
        # nats-server-v2.10.24-linux-amd64.tar.gz SHA256
        # Verify at: https://github.com/nats-io/nats-server/releases/tag/v2.10.24
        NATS_SHA256 = "ee6500f364e3a741b496ae0296c04f2a9d53bbaabac457104ac74596b4a59d85"

        checksum_cmd = (
            f"echo '{NATS_SHA256}  /tmp/nats-server.tar.gz' | sha256sum -c - && "
            if NATS_SHA256 and NATS_SHA256 != "REPLACE_WITH_ACTUAL_SHA256"
            else "echo '[WARN] Skipping SHA256 verification (supply-chain risk)' && "
        )
        install_cmds = (
            f"set -e && "
            f"curl -sfL 'https://github.com/nats-io/nats-server/releases/download/v{NATS_VERSION}/nats-server-v{NATS_VERSION}-linux-amd64.tar.gz' "
            f"-o /tmp/nats-server.tar.gz && "
            f"{checksum_cmd}"
            f"tar -xzf /tmp/nats-server.tar.gz -C /tmp --strip-components=1 && "
            f"sudo mv /tmp/nats-server /usr/local/bin/nats-server && "
            f"sudo chmod +x /usr/local/bin/nats-server && "
            f"nats-server --version"
        )
        run_ssh(ip, install_cmds)

        # 2. 写配置
        cfg_escaped = config.replace("'", "'\\''")
        run_ssh(ip, f"mkdir -p ~/.worker-bee && echo '{cfg_escaped}' > ~/.worker-bee/nats-server.conf")

        # 3. 杀掉旧进程，启动新的
        run_ssh(ip, "pkill nats-server 2>/dev/null; sleep 1; nohup nats-server -c ~/.worker-bee/nats-server.conf > ~/.worker-bee/nats.log 2>&1 &")
        import time
        time.sleep(2)

        # 4. 验证
        run_ssh(ip, "nats server report --host localhost:8222 2>/dev/null | head -5")

    print(f"\n✅ 完成。验证集群：ssh ubuntu@{IPS[0]} 'nats server list cluster' 2>/dev/null")


if __name__ == "__main__":
    main()
