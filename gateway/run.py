"""Gateway runner — orchestrates platform adapters and routes messages.

This is the central hub: it starts all configured adapters, receives
incoming MessageEvents from them, dispatches to the Agent/NATS layer,
and routes replies back to the originating platform.
"""
import asyncio
import logging
import threading
from typing import Any, Dict, Optional

from gateway.base import BasePlatformAdapter, MessageEvent, SendResult
from gateway.config import GatewayConfig
from gateway.platform_registry import platform_registry

logger = logging.getLogger("gateway")


class GatewayRunner:
    """Manages the lifecycle of all platform adapters and routes messages."""

    def __init__(self, config: GatewayConfig) -> None:
        self.config = config
        self.adapters: Dict[str, BasePlatformAdapter] = {}
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start all enabled adapters.

        Synchronous entry point — each adapter decides internally whether
        it runs in a background thread or within the current event loop.
        """
        # Lazy-load built-in adapters so import-time stays lightweight.
        try:
            from gateway import _ensure_adapters_loaded
            _ensure_adapters_loaded()
        except Exception:  # pragma: no cover
            pass

        with self._lock:
            if self._running:
                return
            self._running = True

            for name, pcfg in self.config.platforms.items():
                if not pcfg.enabled:
                    logger.info("Platform %s disabled, skipping", name)
                    continue

                adapter = platform_registry.create_adapter(name, pcfg)
                if adapter is None:
                    logger.warning("Platform %s not available (check dependencies)", name)
                    continue

                adapter.gateway_runner = self
                self.adapters[name] = adapter
                try:
                    adapter.start()
                    logger.info("Platform adapter started: %s", name)
                except Exception as exc:
                    logger.exception("Failed to start adapter %s: %s", name, exc)

    def stop(self) -> None:
        """Gracefully stop all adapters."""
        with self._lock:
            if not self._running:
                return
            self._running = False
            adapters_snapshot = list(self.adapters.items())
            self.adapters.clear()

        for name, adapter in adapters_snapshot:
            try:
                adapter.stop()
                logger.info("Platform adapter stopped: %s", name)
            except Exception as exc:
                logger.exception("Error stopping adapter %s: %s", name, exc)

    def route_incoming(self, event: MessageEvent) -> None:
        """Called by an adapter when a new message arrives.

        Flow:
            1. Process with Agent (or NATS)
            2. Send reply back via the originating adapter
        """
        logger.info("Incoming [%s] from %s: %.80s...", event.platform, event.sender_id, event.text)
        try:
            response = self.process_with_agent(event)
        except Exception as exc:
            logger.exception("Agent processing failed: %s", exc)
            response = "⚠️ 处理失败，请稍后重试。"

        with self._lock:
            source = self.adapters.get(event.platform)
        if source is None:
            logger.error("No adapter for platform %s to send reply", event.platform)
            return

        try:
            result = source.send(event, response)
            if not result.success:
                logger.error("Send failed on %s: %s", event.platform, result.error)
        except Exception as exc:
            logger.exception("Send error on %s: %s", event.platform, exc)

    def process_with_agent(self, event: MessageEvent) -> str:
        """Dispatch event to the Agent / NATS layer.

        Override or monkey-patch this method to wire into worker-bee's
        actual agent loop. Default implementation is an echo for testing.
        """
        # TODO: wire into worker-bee Agent or NATS dispatcher
        return f"Echo: {event.text}"

    def send_to_platform(self, platform: str, event: MessageEvent, text: str) -> SendResult:
        """Cross-platform send — route a message to a specific platform adapter."""
        with self._lock:
            adapter = self.adapters.get(platform)
        if adapter is None:
            return SendResult(success=False, error=f"Platform {platform} not loaded")
        return adapter.send(event, text)


# ── Async convenience wrappers ───────────────────────────────────────────────

async def start_gateway(config: Optional[GatewayConfig] = None) -> GatewayRunner:
    """Async entry point — start the gateway and return the runner."""
    if config is None:
        config = GatewayConfig.load()
    runner = GatewayRunner(config)
    # Run start() in a thread so blocking adapters don't stall the event loop
    await asyncio.to_thread(runner.start)
    return runner


async def stop_gateway(runner: GatewayRunner) -> None:
    """Async entry point — stop the gateway."""
    await asyncio.to_thread(runner.stop)
