"""BeeBox deploy — bulk clone, install, NATS setup."""
from __future__ import annotations

import os
import textwrap
import time
from pathlib import Path

from .core import load_yaml, ssh_cmd


def deploy_nats(
    host: str,
    user: str,
    key_file: str,
    port: int,
    nats_nodes: list[dict],
    node_name: str,
) -> None:
    """Deploy NATS server on a remote host."""
    print(f"  [NATS] deploying to {host} ...")
    routes = "\n    ".join(f'nats://{n["host"]}:6222' for n in nats_nodes)
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
    cmd = (
        "mkdir -p ~/.beebox/nats-jetstream && "
        f"cat > ~/.beebox/nats-server.conf << 'EOF'\n{conf}\nEOF && "
        "which nats-server || (curl -sfL https://get-nats.io | sh && sudo mv nats-server /usr/local/bin/) && "
        "nohup nats-server -c ~/.beebox/nats-server.conf > ~/.beebox/nats.log 2>&1 &"
    )
    rc, _, err = ssh_cmd(host, user, key_file, port, cmd)
    if rc != 0:
        print(f"  [NATS] warning: {host} may have failed: {err}")
    else:
        print(f"  [NATS] {host} started")


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
    """Deploy a single bee role to a remote host."""
    repo_url = bee_def["repo"]
    branch = bee_def["branch"]
    app_dir = f"~/.beebox/apps/{role}"
    venv_dir = f"~/.beebox/venvs/{role}"
    print(f"  [BEE:{role}] deploying to {host} ...")

    env_exports = " ".join(f'export {k}="{v}"; ' for k, v in env_vars.items() if v)
    cmd = textwrap.dedent(f"""\
        set -e
        {env_exports}
        mkdir -p ~/.beebox/{{apps,venvs,logs,shared,skills}}
        if [ -d {app_dir}/.git ]; then
            cd {app_dir} && git fetch origin && git checkout {branch} && git pull origin {branch}
        else
            git clone --branch {branch} --depth 1 {repo_url} {app_dir}
        fi
        python3 -m venv {venv_dir}
        source {venv_dir}/bin/activate
        pip install --upgrade pip -q
        if [ -f {app_dir}/requirements.txt ]; then
            pip install -r {app_dir}/requirements.txt -q
        fi
        if [ -f {app_dir}/pyproject.toml ]; then
            pip install -e {app_dir} -q
        fi
        echo "[DONE] {role} deployed at {host}"
    """)

    if dry_run:
        print(f"  [DRY-RUN] would run:\n{textwrap.indent(cmd, '    ')}")
        return

    rc, out, err = ssh_cmd(host, user, key_file, port, cmd)
    print(textwrap.indent(out, "    "))
    if rc != 0:
        raise RuntimeError(f"{role}@{host} deploy failed: {err}")


def write_log(log_dir: Path, inventory: dict, bees_def: dict) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    from .core import yaml
    log_file = log_dir / f"deploy-{timestamp}.yaml"
    log_data = {
        "timestamp": timestamp,
        "servers": [
            {"host": s["host"], "name": s["name"], "roles": s["roles"]}
            for s in inventory.get("servers", [])
        ],
        "bees": bees_def,
    }
    with open(log_file, "w", encoding="utf-8") as f:
        yaml.dump(log_data, f, allow_unicode=True, sort_keys=False)
    print(f"[LOG] deploy record saved: {log_file}")
