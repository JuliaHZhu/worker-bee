"""Feishu/Lark platform adapter — webhook receiver + API sender.

Uses stdlib http.server (zero new dependencies) and self-implements
token / reply logic so it has no dependency on agent.lark_cli internals.
"""
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional

from gateway.base import BasePlatformAdapter, MessageEvent, SendResult
from gateway.platform_registry import PlatformEntry, platform_registry

logger = logging.getLogger("gateway.feishu")

# ── Self-contained Feishu API helpers ────────────────────────────────────────

_feishu_token: Optional[str] = None
_feishu_token_expires: float = 0
_token_lock = threading.Lock()


def _get_feishu_token(app_id: str, app_secret: str, base_url: str = "https://open.feishu.cn") -> Optional[str]:
    global _feishu_token, _feishu_token_expires
    now = time.time()
    with _token_lock:
        if _feishu_token and now < _feishu_token_expires - 60:
            return _feishu_token
    if not app_id or not app_secret:
        return None
    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(
        f"{base_url}/open-apis/auth/v3/tenant_access_token/internal",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("code") == 0:
            with _token_lock:
                _feishu_token = data["tenant_access_token"]
                _feishu_token_expires = now + data.get("expire", 7200)
            return _feishu_token
    except Exception:
        pass
    return None


def _send_reply(
    receive_id: str,
    receive_id_type: str,
    content: str,
    token: str,
    msg_type: str = "text",
    base_url: str = "https://open.feishu.cn",
) -> dict:
    api_content = json.dumps({"text": content}, ensure_ascii=False) if msg_type == "text" else content
    body = json.dumps(
        {"receive_id": receive_id, "msg_type": msg_type, "content": api_content},
        ensure_ascii=False,
    ).encode()

    req = urllib.request.Request(
        f"{base_url}/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": resp.status, "data": json.loads(resp.read().decode())}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()}", "code": e.code}
    except Exception as e:
        return {"error": str(e)}


class _FeishuWebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler that parses Feishu events and forwards to adapter.

    ``adapter`` and ``verification_token`` are injected per-instance
    via a dynamically-created subclass (see ``FeishuAdapter.start()``).
    """

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
        else:
            logger.info("Ignoring unsupported Feishu event type: %s", event_type)

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
        extra = getattr(config, "extra", {}) or {}
        self._verification_token = extra.get("verification_token", os.environ.get("FEISHU_VERIFICATION_TOKEN", ""))
        self._app_id = extra.get("app_id", os.environ.get("FEISHU_APP_ID", ""))
        self._app_secret = extra.get("app_secret", os.environ.get("FEISHU_APP_SECRET", ""))
        self._base_url = extra.get("base_url", os.environ.get("FEISHU_BASE_URL", "https://open.feishu.cn"))

    def start(self) -> None:
        # Create a per-instance handler subclass so multiple adapters
        # can coexist without stomping on class-level state.
        handler_cls = type(
            "_BoundFeishuHandler",
            (_FeishuWebhookHandler,),
            {"adapter": self, "verification_token": self._verification_token},
        )
        self._server = HTTPServer((self._host, self._port), handler_cls)
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
            logger.warning("Feishu send failed: missing recipient ID (chat_type=%s chat_id=%s sender_open_id=%s)", chat_type, chat_id, sender_open_id)
            return SendResult(success=False, error="Missing recipient ID")

        if not self._app_id or not self._app_secret:
            logger.warning("Feishu send failed: app_id or app_secret not configured")
            return SendResult(success=False, error="Missing app_id or app_secret")

        token = _get_feishu_token(self._app_id, self._app_secret, self._base_url)
        if not token:
            return SendResult(success=False, error="Unable to obtain tenant_access_token")

        result = _send_reply(rid, rid_type, text, token, base_url=self._base_url)
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
