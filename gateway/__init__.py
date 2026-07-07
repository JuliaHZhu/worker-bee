"""Worker-Bee Gateway — Hermes-style platform adapter framework.

Provides a pluggable bridge between external messaging platforms and the
internal Agent / NATS layer.

Usage:
    from gateway.run import GatewayRunner
    from gateway.config import GatewayConfig

    cfg = GatewayConfig.load()
    runner = GatewayRunner(cfg)
    runner.start()
"""

# Import adapters so they self-register
from gateway import base, config, platform_registry, run
from gateway.platforms import feishu  # noqa: F401

__all__ = [
    "base",
    "config",
    "platform_registry",
    "run",
]
