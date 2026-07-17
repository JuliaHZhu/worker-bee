"""Configuration helpers — zero external dependencies beyond stdlib.

Extracted from agent.main to break the main ↔ session circular dependency.
"""
import json
import logging
import os
import socket
from pathlib import Path

logger = logging.getLogger(__name__)


def _config_dir() -> Path:
    """Return the user config directory (~/.worker-bee)."""
    return Path.home() / ".worker-bee"


def load_bee_config() -> dict:
    """Load bee role config from config.yaml (seed/role/evolution).

    Looks for config.yaml in:
      1. Current working directory (project root)
      2. Fallback: ~/.worker-bee/config.yaml

    Returns dict with defaults if not found.
    """
    import yaml
    paths = [
        Path("config.yaml"),
        _config_dir() / "config.yaml",
    ]
    for p in paths:
        if p.exists():
            try:
                with open(p) as f:
                    cfg = yaml.safe_load(f) or {}
                cfg.setdefault("role", "seed")
                cfg.setdefault("evolution", {})
                return cfg
            except Exception as e:
                logger.warning("Failed to load bee config from %s: %s", p, e)
                pass
    return {"role": "seed", "evolution": {}}


def get_config_path():
    _config_dir().mkdir(parents=True, exist_ok=True)
    return str(_config_dir() / "config.json")


def load_config():
    """Load config from file or env. Returns dict or None."""
    path = get_config_path()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    key = os.environ.get("MOONSHOT_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base = os.environ.get("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
    if key:
        return _make_config("openai", "kimi-k2.6", key, base)
    return None


def _make_config(provider, model, api_key, base_url, max_iter=60, temperature=0.0):
    default_bee_id = socket.gethostname().lower().replace(".", "-")
    # Import here to avoid circular dependency at module load time
    from agent.agent import DEFAULT_SYSTEM_PROMPT
    return {
        "model": model,
        "provider": provider,
        "api_key": api_key,
        "base_url": base_url,
        "max_iterations": max_iter,
        "temperature": temperature,
        "auto_confirm": False,
        "bee_id": default_bee_id,
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "tools": [
            "sys_terminal",
            "fs_read_file", "fs_write_file", "fs_search_files",
            "net_web_search", "net_web_extract",
            "agent_delegate_task", "agent_delegate_parallel", "agent_cross_validate"
        ]
    }
