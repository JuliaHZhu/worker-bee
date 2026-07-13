"""BeeBox deploy — bulk clone seed, install, NATS setup (seed mode)."""
"""BeeBox deploy — bulk clone seed, install, NATS setup (seed mode)."""
"""BeeBox deploy — bulk clone seed, install, NATS setup (seed mode)."""
from __future__ import annotations

import os
import shlex
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
    nats_user: str = "",
    nats_password: str = "",
) -> None:
    """Deploy NATS server on a remote host."""
    print(f"  [NATS] deploying to {host} ...")
    routes = "\n    ".join(f'nats://{n["host"]}:6222' for n in nats_nodes)
    auth_block = ""
    if nats_user and nats_password:
        auth_block = textwrap.dedent(f"""\
            authorization {{
              user: {nats_user}
              password: {nats_password}
              timeout: 2
            }}
        """)
    conf = textwrap.dedent(f"""\
        server_name: "{node_name}"
        port: 4222
        http_port: 8222
        max_payload: 8MB
        max_pending: 32MB
        {auth_block}
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


def deploy_seed(
    host: str,
    user: str,
    key_file: str,
    port: int,
    seed_repo: str,
    seed_branch: str,
    server_name: str,
    env_vars: dict,
    dry_run: bool,
) -> None:
    """Deploy worker-bee seed to a remote host. All servers get the same repo."""
    app_dir = "~/.beebox/worker-bee"
    venv_dir = "~/.beebox/venv"
    print(f"  [SEED] deploying to {host} ({server_name}) ...")

    env_exports = " ".join(f'export {k}={shlex.quote(str(v))}; ' for k, v in env_vars.items() if v)
    cmd = textwrap.dedent(f"""\
        set -e
        {env_exports}
        mkdir -p ~/.beebox/{{venv,logs,shared,skills}}
        if [ -d {app_dir}/.git ]; then
            cd {app_dir} && git fetch origin && git checkout {seed_branch} && git pull origin {seed_branch}
        else
            git clone --branch {seed_branch} --depth 1 {seed_repo} {app_dir}
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
        echo "[DONE] worker-bee seed deployed at {host} ({server_name})"
    """)

    if dry_run:
        print(f"  [DRY-RUN] would run:\n{textwrap.indent(cmd, '    ')}")
        return

    rc, out, err = ssh_cmd(host, user, key_file, port, cmd)
    print(textwrap.indent(out, "    "))
    if rc != 0:
        raise RuntimeError(f"seed@{host} deploy failed: {err}")


def write_log(log_dir: Path, inventory: dict) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    from .core import yaml

    log_file = log_dir / f"deploy-{timestamp}.yaml"
    log_data = {
        "timestamp": timestamp,
        "seed_repo": inventory.get("seed_repo", ""),
        "servers": [
            {"host": s["host"], "name": s["name"]}
            for s in inventory.get("servers", [])
        ],
    }
    with open(log_file, "w", encoding="utf-8") as f:
        yaml.dump(log_data, f, allow_unicode=True, sort_keys=False)
    print(f"[LOG] deploy record saved: {log_file}")
