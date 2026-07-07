"""Feishu/Lark platform adapter — webhook receiver + API sender.

Uses stdlib http.server (zero new dependencies) and reuses token / reply
logic from agent.lark_cli.
"""
import json
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional

from gateway.base import BasePlatformAdapter, MessageEvent, SendResult
from gateway.platform_registry import PlatformEntry, platform_registry

logger = logging.getLogger("gateway.feishu")

# Reuse lark_cli utilities (token cache, reply helper)
from agent.lark_cli import _get_feishu_token, _send_reply


class _FeishuWebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler that parses Feishu events and forwards to adapter."""

    # Class-level reference to the parent adapter (injected by FeishuAdapter)
    adapter: Optional["FeishuAdapter"] = None
    verification_token: str = ""

    def log_message(self, fmt: str, *args: Any) -> None:
        pass  # Suppress noisy default HTTP logs

    def _respond_json(self, data: Dict[str, Any], code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self) -> None:
        if self.path != "/webhook":
            self._respond_json({"error": "not found"}, 404)
            return

        clen = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(clen).decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._respond_json({"error": "bad json"}, 400)
            return

        # 1. Challenge handshake
        if payload.get("type") == "url_verification":
            self._respond_json({"challenge": payload.get("challenge", "")})
            logger.info("Challenge handshake OK")
            return

        # 2. Token verification
        header_token = payload.get("header", {}).get("token", "")
        if self.verification_token and header_token != self.verification_token:
            self._respond_json({"error": "forbidden"}, 403)
            return

        # 3. Route message events
        event_type = payload.get("header", {}).get("event_type", "")
        if event_type == "im.message.receive_v1":
            threading.Thread(target=self._handle_message, args=(payload,), daemon=True).start()

        self._respond_json({"code": 0, "msg": "ok"})

    def _handle_message(self, payload: Dict[str, Any]) -> None:
        event = payload.get("event", {})
        message = event.get("message", {})
        sender = event.get("sender", {})

        if message.get("message_type") != "text":
            return

        try:
            content = json.loads(message.get("content", "{}"))
        except json.JSONDecodeError:
            return
        text = content.get("text", "").strip()

        chat_id = message.get("chat_id", "")
        chat_type = message.get("chat_type", "")  # p2p or group
        sender_open_id = sender.get("sender_id", {}).get("open_id", "")
        message_id = message.get("message_id", "")

        # Strip @bot mentions in group chats
        mentions = message.get("mentions", [])
        for m in mentions:
            key = m.get("key", "")
            if key:
                text = text.replace(f"@{key}", "").strip()

        # Build normalized MessageEvent
        msg_event = MessageEvent(
            platform="feishu",
            sender_id=sender_open_id,
            text=text,
            thread_id=chat_id if chat_type == "group" else None,
            message_id=message_id,
            raw={
                "chat_id": chat_id,
                "chat_type": chat_type,
                "sender_open_id": sender_open_id,
                "message_id": message_id,
            },
        )

        if self.adapter is not None:
            self.adapter.handle_incoming(msg_event)


class FeishuAdapter(BasePlatformAdapter):
    """Feishu platform adapter.

    Config attributes (from PlatformConfig.extra):
        verification_token — Feishu event subscription verification token
        app_id, app_secret  — Optional overrides (falls back to env vars)
    """

    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._port = getattr(config, "port", 8080)
        self._host = getattr(config, "host", "0.0.0.0")
        self._verification_token = os.environ.get("FEISHU_VERIFICATION_TOKEN", "")
        extra = getattr(config, "extra", {}) or {}
        if "verification_token" in extra:
            self._verification_token = extra["verification_token"]

    def start(self) -> None:
        _FeishuWebhookHandler.adapter = self
        _FeishuWebhookHandler.verification_token = self._verification_token
        self._server = HTTPServer((self._host, self._port), _FeishuWebhookHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Feishu webhook server listening on %s:%d", self._host, self._port)

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        _FeishuWebhookHandler.adapter = None
        logger.info("Feishu webhook server stopped")

    def send(self, event: MessageEvent, text: str) -> SendResult:
        """Send reply back to Feishu via App Bot API."""
        raw = event.raw or {}
        chat_type = raw.get("chat_type", "p2p")
        chat_id = raw.get("chat_id", "")
        sender_open_id = raw.get("sender_open_id", "")

        rid_type = "open_id" if chat_type == "p2p" else "chat_id"
        rid = sender_open_id if chat_type == "p2p" else chat_id

        if not rid:
            return SendResult(success=False, error="Missing recipient ID")

        result = _send_reply(rid, rid_type, text)
        if "error" in result:
            return SendResult(success=False, error=result["error"])
        return SendResult(success=True, message_id=result.get("data", {}).get("message_id"))


# ── Self-registration ────────────────────────────────────────────────────────

def _check_dependencies() -> bool:
    return True  # Pure stdlib


def _validate_config(config: Any) -> bool:
    return True


platform_registry.register(
    PlatformEntry(
        name="feishu",
        label="Feishu / Lark",
        adapter_factory=lambda cfg: FeishuAdapter(cfg),
        check_fn=_check_dependencies,
        validate_config=_validate_config,
    )
)
