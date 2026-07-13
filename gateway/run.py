"""Gateway runner — orchestrates platform adapters and routes messages.

This is the central hub: it starts all configured adapters, receives
incoming MessageEvents from them, dispatches to the Agent/NATS layer,
and routes replies back to the originating platform.
"""
import asyncio
import json
import logging
import os
import threading
from typing import Any, Dict, Optional

from gateway.base import BasePlatformAdapter, MessageEvent, SendResult
from gateway.config import GatewayConfig
from gateway.platform_registry import platform_registry

logger = logging.getLogger("gateway")

# NATS dispatch defaults — overridden by SWARM_NATS_URL env var
DEFAULT_SWARM_NATS_URL = os.getenv("SWARM_NATS_URL", "nats://localhost:4222")
SWARM_INCOMING_SUBJECT = "swarm.incoming.gateway"


def _nats_auth_from_config() -> tuple[Optional[str], Optional[str]]:
    """Read NATS credentials from config.yaml (nats_auth section)."""
    from pathlib import Path
    try:
        import yaml
    except ModuleNotFoundError:
        return None, None
    for p in [Path("config.yaml"), Path.home() / ".worker-bee" / "config.yaml"]:
        if not p.exists():
            continue
        try:
            with open(p) as f:
                cfg = yaml.safe_load(f) or {}
            auth = cfg.get("nats_auth", {})
            user = auth.get("user", "")
            password = auth.get("password", "")
            if user:
                return user, password
        except Exception:
            pass
    return None, None


class GatewayRunner:
    """Manages the lifecycle of all platform adapters and routes messages."""

    def __init__(self, config: GatewayConfig) -> None:
        self.config = config
        self.adapters: Dict[str, BasePlatformAdapter] = {}
        self._running = False
        self._lock = threading.Lock()
        self._agent = None
        # Load agent config from the same source as the rest of worker-bee
        self._agent_config = self._load_agent_config()

    def _load_agent_config(self) -> dict:
        import json
        from pathlib import Path
        cfg_path = Path.home() / ".worker-bee" / "config.json"
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

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

    async def _dispatch_via_nats(self, event: MessageEvent) -> str:
        """Forward the incoming event to the swarm via NATS request/reply."""
        try:
            import nats
        except ModuleNotFoundError:
            raise RuntimeError("nats-py not installed")

        nats_url = os.getenv("SWARM_NATS_URL", DEFAULT_SWARM_NATS_URL)
        connect_kwargs: Dict[str, Any] = {"connect_timeout": 10}
        nats_user = os.getenv("NATS_USER")
        nats_password = os.getenv("NATS_PASSWORD", "")
        if not nats_user:
            nats_user, nats_password = _nats_auth_from_config()
        if nats_user:
            connect_kwargs["user"] = nats_user
            connect_kwargs["password"] = nats_password or ""
        nc = await nats.connect(nats_url, **connect_kwargs)
        try:
            payload = json.dumps(
                {
                    "source": event.platform,
                    "sender": event.sender_id,
                    "text": event.text,
                    "chat_id": event.raw.get("chat_id", "") if hasattr(event, "raw") else "",
                    "message_id": event.message_id,
                    "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else str(event.timestamp),
                },
                ensure_ascii=False,
            ).encode("utf-8")

            response = await nc.request(
                SWARM_INCOMING_SUBJECT,
                payload,
                timeout=30,
            )
            return response.data.decode("utf-8")
        finally:
            await nc.close()

    def process_with_agent(self, event: MessageEvent) -> str:
        """Dispatch event to the Agent / NATS layer.

        First attempts NATS request/reply to the swarm; falls back to a
        local agent if NATS is unavailable or nats-py is not installed.
        """
        try:
            return asyncio.run(self._dispatch_via_nats(event))
        except Exception as exc:
            logger.warning("NATS dispatch failed (%s), falling back to local agent", exc)
            return self._run_local_agent(event)

    def _run_local_agent(self, event: MessageEvent) -> str:
        """Run local AIAgent and return reply text."""
        try:
            if self._agent is None:
                from agent.agent import AIAgent
                self._agent = AIAgent(self._agent_config)
            reply = self._agent.run([{"role": "user", "content": event.text}])
            logger.info("Local agent reply: %.200s", reply)
            return reply
        except Exception as exc:
            logger.error("Local agent failed: %s", exc, exc_info=True)
            return f"[agent error] {exc}"

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
