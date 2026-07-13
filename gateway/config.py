"""Gateway configuration loader.

Reads from ~/.worker-bee/config.json under the "gateway" key.
"""
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class PlatformConfig:
    """Per-platform settings."""

    enabled: bool = True
    port: int = 8080
    host: str = "0.0.0.0"
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
        """Load from ~/.worker-bee/config.json or the given path."""
        if path is None:
            path = Path.home() / ".worker-bee" / "config.json"
        if not path.exists():
            return cls(enabled=False)
        try:
            with open(path) as f:
                data = json.load(f)
            return cls.from_dict(data.get("gateway"))
        except Exception as exc:
            logger.warning("Failed to load gateway config from %s: %s", path, exc)
            return cls(enabled=False)
