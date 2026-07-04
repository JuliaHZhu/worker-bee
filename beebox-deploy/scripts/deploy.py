#!/usr/bin/env python3
"""
BeeBox Deploy — 批量部署分体式 Agent 到多台云服务器。

用法：
    python scripts/deploy.py [--inventory ../inventory.private.yaml] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import yaml


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ssh_cmd(host: str, user: str, key_file: str, port: int, cmd: str, capture: bool = True) -> tuple[int, str, str]:
    """在远程服务器上执行 SSH 命令。"""
    ssh = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=10",
        "-p", str(port),
        "-i", os.path.expanduser(key_file),
        f"{user}@{host}",
        cmd,
    ]
    if capture:
        result = subprocess.run(ssh, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    else:
        result = subprocess.run(ssh)
        return result.returncode, "", ""


def deploy_nats(host: str, user: str, key_file: str, port: int, nats_nodes: list[dict], node_name: str) -> None:
    """在服务器上部署 NATS 服务。"""
    print(f"  [NATS] 部署 NATS 到 {host} ...")
    routes = "\n    ".join(
        f'nats://{n["host"]}:6222' for n in nats_nodes
    )
    conf = textwrap.dedent(f"""\
        server_name: "{node_name}"
        port: 4222
        http_port: 8222
        max_payload: 8MB
        max_pending: 32MB
        cluster {{
          name: beebox-cluster
          listen: 0.0.0.0:6222
          routes = [
            {routes}
          ]
        }}
        jetstream {{
          store_dir: "~/.beebox/nats-jetstream"
          max_memory_store: 256MB
          max_file_store: 2GB
        }}
        debug: false
        trace: false
        logtime: true
    """)
    # 写入远程配置并启动
    cmd = (
        "mkdir -p ~/.beebox/nats-jetstream && "
        f"cat > ~/.beebox/nats-server.conf << 'EOF'\n{conf}\nEOF && "
        "which nats-server || (curl -sfL https://get-nats.io | sh && sudo mv nats-server /usr/local/bin/) && "
        "nohup nats-server -c ~/.beebox/nats-server.conf > ~/.beebox/nats.log 2>&1 &"
    )
    rc, out, err = ssh_cmd(host, user, key_file, port, cmd)
    if rc != 0:
        print(f"  [NATS] 警告: {host} NATS 部署可能失败: {err}")
    else:
        print(f"  [NATS] {host} NATS 已启动")


def deploy_bee(
    host: str,
    user: str,
    key_file: str,
    port: int,
    role: str,
    bee_def: dict,
    env_vars: dict,
    dry_run: bool,
) -> None:
    """在服务器上部署单个 bee。"""
    repo_url = bee_def["repo"]
    branch = bee_def["branch"]
    app_dir = f"~/.beebox/apps/{role}"
    venv_dir = f"~/.beebox/venvs/{role}"

    print(f"  [BEE:{role}] 部署到 {host} ...")

    # 环境变量注入
    env_exports = " ".join(f'export {k}="{v}"; ' for k, v in env_vars.items() if v)

    # 远程部署脚本
    cmd = textwrap.dedent(f"""\
        set -e
        {env_exports}
        mkdir -p ~/.beebox/{{apps,venvs,logs,shared,skills}}

        # 克隆或更新仓库
        if [ -d {app_dir}/.git ]; then
            cd {app_dir} && git fetch origin && git checkout {branch} && git pull origin {branch}
        else
            git clone --branch {branch} --depth 1 {repo_url} {app_dir}
        fi

        # 创建虚拟环境并安装依赖
        python3 -m venv {venv_dir}
        source {venv_dir}/bin/activate
        pip install --upgrade pip -q
        if [ -f {app_dir}/requirements.txt ]; then
            pip install -r {app_dir}/requirements.txt -q
        fi
        if [ -f {app_dir}/pyproject.toml ]; then
            pip install -e {app_dir} -q
        fi

        # 创建 systemd 服务文件（如果用户有 sudo 权限）
        SERVICE_FILE="/tmp/bee-{role}.service"
        cat > $SERVICE_FILE << 'SVCEOF'
[Unit]
Description=BeeBox {role} Agent
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={app_dir}
Environment=HOME=/home/{user}
Environment=PYTHONUNBUFFERED=1
ExecStart={venv_dir}/bin/python -m agent.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF
        echo "[INFO] systemd 服务文件已生成: $SERVICE_FILE"
        echo "[INFO] 如需后台运行，请在服务器上执行: sudo mv $SERVICE_FILE /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now bee-{role}"

        echo "[DONE] {role} 部署完成于 {host}"
    """)

    if dry_run:
        print(f"  [DRY-RUN] 将要执行:\n{textwrap.indent(cmd, '    ')}")
        return

    rc, out, err = ssh_cmd(host, user, key_file, port, cmd)
    print(textwrap.indent(out, "    "))
    if rc != 0:
        print(f"  [ERROR] {role}@{host} 部署失败: {err}")
        sys.exit(1)


def write_deployment_log(log_dir: Path, inventory: dict, bees_def: dict) -> None:
    """记录本次部署的元数据日志。"""
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"deploy-{timestamp}.yaml"
    log_data = {
        "timestamp": timestamp,
        "servers": [
            {
                "host": s["host"],
                "name": s["name"],
                "roles": s["roles"],
            }
            for s in inventory.get("servers", [])
        ],
        "bees": bees_def,
    }
    with open(log_file, "w", encoding="utf-8") as f:
        yaml.dump(log_data, f, allow_unicode=True, sort_keys=False)
    print(f"[LOG] 部署记录已保存: {log_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="BeeBox 批量部署工具")
    parser.add_argument(
        "--inventory",
        default="inventory.yaml",
        help="服务器清单文件 (默认: inventory.yaml)",
    )
    parser.add_argument(
        "--bees",
        default="config/bees.yaml",
        help="Bee 角色定义文件 (默认: config/bees.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将要执行的命令，不实际执行",
    )
    args = parser.parse_args()

    inventory = load_yaml(args.inventory)
    bees_config = load_yaml(args.bees)
    bees_def = {b["role"]: b for b in bees_config.get("bees", [])}
    nats_nodes = inventory.get("nats_nodes", [])

    ssh_cfg = inventory.get("ssh", {})
    user = ssh_cfg.get("user", "ubuntu")
    key_file = ssh_cfg.get("key_file", "~/.ssh/id_rsa")
    ssh_port = ssh_cfg.get("port", 22)

    print("=" * 60)
    print("BeeBox Deploy — 分体式 Agent 批量部署")
    print("=" * 60)

    for server in inventory.get("servers", []):
        host = server["host"]
        name = server.get("name", host)
        roles = server.get("roles", [])
        env_vars = server.get("env", {})

        print(f"\n[{name}] {host}")
        print("-" * 40)

        # 1. 部署 NATS（如标记为 nats_server）
        if server.get("nats_server") and nats_nodes:
            deploy_nats(host, user, key_file, ssh_port, nats_nodes, name)

        # 2. 部署每个 bee 角色
        for role in roles:
            if role not in bees_def:
                print(f"  [SKIP] 未知角色: {role}")
                continue
            deploy_bee(
                host=host,
                user=user,
                key_file=key_file,
                port=ssh_port,
                role=role,
                bee_def=bees_def[role],
                env_vars=env_vars,
                dry_run=args.dry_run,
            )

    # 3. 记录部署日志
    if not args.dry_run:
        write_deployment_log(Path("logs"), inventory, bees_def)

    print("\n" + "=" * 60)
    print("部署完成！")
    print("=" * 60)
    print("提示：")
    print("  - 检查各节点 ~/.beebox/apps/ 目录确认代码已克隆")
    print("  - 手动在各节点执行 systemd 服务安装以实现后台持久化")
    print("  - 使用 scripts/update.py 进行后续批量更新")


if __name__ == "__main__":
    main()
