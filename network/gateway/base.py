"""Gateway base abstractions — Hermes-style platform adapter framework.

Provides the contract layer between external messaging platforms (Feishu,
WhatsApp, etc.) and the internal Agent/NATS routing layer.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MessageEvent:
    """Normalized message event — platform-agnostic."""

    platform: str          # Source platform name, e.g. "feishu"
    sender_id: str         # User identifier on that platform
    text: str              # Normalized text content
    thread_id: Optional[str] = None   # Chat / group / thread ID
    message_id: Optional[str] = None  # Original message ID (for reply)
    raw: Dict[str, Any] = field(default_factory=dict)  # Platform-specific raw payload


@dataclass
class SendResult:
    """Result of sending a message to a platform."""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class BasePlatformAdapter(ABC):
    """Abstract base for every messaging platform adapter.

    Lifecycle:
        1. __init__(config) — construction
        2. gateway_runner = runner — injected by GatewayRunner
        3. start() — begin receiving messages (HTTP server / WS / polling)
        4. handle_incoming(event) — callback when message arrives
        5. stop() — graceful shutdown
    """

    def __init__(self, config: Any) -> None:
        self.config = config
        self.gateway_runner: Optional["GatewayRunner"] = None  # injected at start

    @abstractmethod
    def start(self) -> None:
        """Start the platform connection (blocking or non-blocking)."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Gracefully stop the platform connection."""
        ...

    @abstractmethod
    def send(self, event: MessageEvent, text: str) -> SendResult:
        """Send *text* back to the user/channel described by *event*."""
        ...

    def handle_incoming(self, event: MessageEvent) -> None:
        """Entry point called by the adapter when a message arrives.

        Hands off to GatewayRunner for routing / Agent processing.
        """
        if self.gateway_runner is not None:
            self.gateway_runner.route_incoming(event)
