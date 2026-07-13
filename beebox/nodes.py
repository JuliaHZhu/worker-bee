"""Node configuration loader — centralises IP / role mappings.

Resolution order (first wins):
1. Environment variables (BEE_PM_IP, BEE_WORKER_IP, …)
2. ~/.worker-bee/nodes.yaml
3. localhost defaults (safe fallback for dev)
"""
import os
from pathlib import Path

_DEFAULTS = {
    "pm": "127.0.0.1",
    "worker": "127.0.0.1",
    "aristotle": "127.0.0.1",
    "skeleton": "127.0.0.1",
    "world": "127.0.0.1",
    "cardmaster": "127.0.0.1",
    "strategy": "127.0.0.1",
    "centurion": "127.0.0.1",
}

_CONFIG_PATH = Path.home() / ".worker-bee" / "nodes.yaml"


def _load_yaml():
    """Best-effort YAML load; returns {} on any error."""
    if not _CONFIG_PATH.exists():
        return {}
    try:
        import yaml
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def get_node_ip(role: str) -> str:
    """Return IP for *role*, falling back through env → yaml → localhost."""
    env_key = f"BEE_{role.upper().replace('-', '_')}_IP"
    env_val = os.getenv(env_key, "").strip()
    if env_val:
        return env_val
    cfg = _load_yaml()
    if "nodes" in cfg and role in cfg["nodes"]:
        return cfg["nodes"][role]
    return _DEFAULTS.get(role, "127.0.0.1")


def get_pm_ip() -> str:
    """Convenience: IP of the PM (NATS broker) node."""
    return get_node_ip("pm")


def all_nodes():
    """Yield (role, ip) for every known node."""
    cfg = _load_yaml()
    explicit = cfg.get("nodes", {})
    for role in _DEFAULTS:
        ip = explicit.get(role) or os.getenv(f"BEE_{role.upper()}_IP", "").strip() or _DEFAULTS[role]
        yield role, ip


def self_role() -> str:
    """Attempt to detect local role by matching hostname IPs against config."""
    import socket
    try:
        local_ips = set(
            socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        )
        local_ips = {x[4][0] for x in local_ips}
        # Also include all interface addresses
        local_ips.update(
            line.split()[1] for line in os.popen("hostname -I").read().strip().split()
            if "." in line
        )
    except Exception:
        local_ips = set()
    for role, ip in all_nodes():
        if ip in local_ips:
            return role
    return "unknown"
