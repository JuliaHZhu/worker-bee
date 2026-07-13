#!/usr/bin/env python3
"""生成 NATS 集群配置 + 分发到 8 台机。

用法：
    1. 改下面 IPS 为 8 台机的实际内网 IP
    2. python3 beebox/setup_nats.py

会在每台机上安装 nats-server、写配置、启动集群。
"""

import subprocess, sys, os
from pathlib import Path

# Load IPs from beebox.nodes configuration (env -> yaml -> fallback)
def _load_ips() -> list[str]:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from beebox.nodes import all_nodes
    ips = [ip for _role, ip in all_nodes()]
    # Filter out duplicates and loopback unless it's the only node
    unique = []
    seen = set()
    for ip in ips:
        if ip not in seen:
            seen.add(ip)
            unique.append(ip)
    # If all are 127.0.0.1, user hasn't configured nodes yet
    if set(unique) <= {"127.0.0.1"}:
        env_ips = os.getenv("NATS_CLUSTER_IPS", "").strip()
        if env_ips:
            return [ip.strip() for ip in env_ips.split(",") if ip.strip()]
        print("⚠️  未配置集群 IP。请选择一种方式：")
        print("  1. 设置环境变量 NATS_CLUSTER_IPS=192.168.1.101,192.168.1.102,...")
        print("  2. 创建 ~/.worker-bee/nodes.yaml （参考 config/nodes.yaml.sample）")
        sys.exit(1)
    return unique


IPS = _load_ips()
SSH_USER = "ubuntu"

def _load_nats_auth() -> tuple[str | None, str | None]:
    """Read NATS credentials from config.yaml or env vars."""
    import yaml
    for p in [Path("config.yaml"), Path.home() / ".worker-bee" / "config.yaml"]:
        if not p.exists():
            continue
        try:
            with open(p) as f:
                cfg = yaml.safe_load(f) or {}
            auth = cfg.get("nats_auth", {})
            user = auth.get("user", "")
            password = auth.get("password", "")
            if user:
                return user, password
        except Exception:
            pass
    user = os.getenv("NATS_USER", "")
    password = os.getenv("NATS_PASSWORD", "")
    if user:
        return user, password
    return None, None


def gen_config(node_name: str, node_ip: str, all_ips: list[str]) -> str:
    routes = ",\n    ".join(f"nats://{ip}:6222" for ip in all_ips)
    nats_user, nats_pass = _load_nats_auth()
    auth_block = ""
    if nats_user and nats_pass:
        auth_block = f"""authorization {{
  user: {nats_user}
  password: {nats_pass}
  timeout: 2
}}

"""
    return f"""# NATS 集群 — {node_name}
server_name: "{node_name}"
port: 4222
http_port: 8222
max_payload: 1MB
max_pending: 10MB

{auth_block}cluster {{
  name: worker-bee-cluster
  listen: 0.0.0.0:6222
  routes = [
    {routes}
  ]
}}

jetstream {{
  store_dir: "~/.worker-bee/nats-jetstream"
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
