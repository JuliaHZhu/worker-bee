"""Worker-Bee Gateway — Hermes-style platform adapter framework.

Provides a pluggable bridge between external messaging platforms and the
internal Agent / NATS layer.

Usage:
    from network.gateway.run import GatewayRunner
    from network.gateway.config import GatewayConfig

    cfg = GatewayConfig.load()
    runner = GatewayRunner(cfg)
    runner.start()
"""

from network.gateway import base, config, platform_registry, run

__all__ = [
    "base",
    "config",
    "platform_registry",
    "run",
]


def _ensure_adapters_loaded() -> None:
    """Lazy-load built-in adapters so ``import gateway`` does not pull
    heavy dependency chains (e.g. agent, LLM SDKs) at import time."""
    from network.gateway.platforms import feishu  # noqa: F401
