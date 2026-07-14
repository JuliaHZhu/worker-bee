"""Gateway configuration loader.

Reads from ~/.worker-bee/config.json under the "gateway" key.
"""
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


def _find_config_yaml() -> Optional[Path]:
    """Look for config.yaml in cwd or ~/.worker-bee/."""
    for p in [Path("config.yaml"), Path.home() / ".worker-bee" / "config.yaml"]:
        if p.exists():
            return p
    return None


@dataclass
class PlatformConfig:
    """Per-platform settings."""

    enabled: bool = True
    port: int = 8080
    host: str = os.getenv("WORKER_BEE_HOST", "127.0.0.1")
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GatewayConfig:
    """Top-level gateway configuration."""

    enabled: bool = False
    platforms: Dict[str, PlatformConfig] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "GatewayConfig":
        if not data:
            return cls(enabled=False)
        platforms = {}
        for name, pcfg in data.get("platforms", {}).items():
            platforms[name] = PlatformConfig(
                enabled=pcfg.get("enabled", True),
                port=pcfg.get("port", 8080),
                host=pcfg.get("host", "0.0.0.0"),
                extra=pcfg.get("extra", {}),
            )
        return cls(
            enabled=data.get("enabled", False),
            platforms=platforms,
        )

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "GatewayConfig":
        """Load gateway config.

        Resolution order:
          1. Explicit ``path`` if given.
          2. ``config.yaml`` (cwd or ~/.worker-bee/) containing a ``gateway`` key.
          3. ``~/.worker-bee/config.json`` legacy fallback.
        """
        if path is not None:
            return cls._load_from_path(path)

        # 1. Try unified config.yaml
        yaml_path = _find_config_yaml()
        if yaml_path is not None:
            try:
                with open(yaml_path) as f:
                    data = yaml.safe_load(f) or {}
                if "gateway" in data:
                    logger.info("Loaded gateway config from %s", yaml_path)
                    return cls.from_dict(data["gateway"])
            except Exception as exc:
                logger.warning("Failed to load gateway config from %s: %s", yaml_path, exc)

        # 2. Legacy fallback: ~/.worker-bee/config.json
        json_path = Path.home() / ".worker-bee" / "config.json"
        if json_path.exists():
            return cls._load_from_path(json_path)

        return cls(enabled=False)

    @classmethod
    def _load_from_path(cls, path: Path) -> "GatewayConfig":
        try:
            with open(path) as f:
                if path.suffix in (".yaml", ".yml"):
                    data = yaml.safe_load(f) or {}
                else:
                    data = json.load(f)
            return cls.from_dict(data.get("gateway"))
        except Exception as exc:
            logger.warning("Failed to load gateway config from %s: %s", path, exc)
            return cls(enabled=False)
