#!/usr/bin/env python3
"""
Feishu Gateway — 飞书 ↔ NATS 双向桥接
=====================================
职责：
  1. HTTP webhook 接收飞书消息推送
  2. 解析后 publish 到 NATS (swarm.incoming.feishu)
  3. 订阅 NATS (swarm.outgoing.feishu) 把回复发回飞书

依赖：nats-py（已在 worker-bee 依赖中）
配置：~/.worker-bee/gateway.json 或环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET

运行：
    python gateway/feishu_gateway.py

飞书事件订阅地址：
    http://<PM_IP>:8080/webhook/feishu
"""
import asyncio
import http.server
import json
import os
import socketserver
import threading
import time
import urllib.request
from pathlib import Path

try:
    import nats
except ModuleNotFoundError as exc:
    raise SystemExit("nats-py not installed. Run: pip install nats-py") from exc

# ── 配置 ──────────────────────────────────────────
CONFIG_PATH = Path.home() / ".worker-bee" / "gateway.json"
NATS_URL = os.environ.get("SWARM_NATS_URL", "nats://localhost:4222")
WEBHOOK_PORT = int(os.environ.get("GATEWAY_PORT", "8080"))


def _load_cfg():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}


cfg = _load_cfg()
APP_ID = os.environ.get("FEISHU_APP_ID") or cfg.get("app_id")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET") or cfg.get("app_secret")

# ── 异步事件循环（独立线程）────────────────────────
_loop = asyncio.new_event_loop()


def _run_loop():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


threading.Thread(target=_run_loop, daemon=True).start()

# ── NATS 连接 ─────────────────────────────────────
_nc = None


async def _connect_nats():
    global _nc
    if _nc is None:
        _nc = await nats.connect(NATS_URL)
        print(f"[GW] NATS connected: {NATS_URL}")


async def _publish(subject: str, payload: dict):
    await _connect_nats()
    await _nc.publish(subject, json.dumps(payload, ensure_ascii=False).encode())


def publish_sync(subject: str, payload: dict):
    asyncio.run_coroutine_threadsafe(_publish(subject, payload), _loop).result(timeout=5)


# ── 飞书 Token 管理 ───────────────────────────────
_token = None
_token_exp = 0


def _feishu_token():
    global _token, _token_exp
    if _token and time.time() < _token_exp - 60:
        return _token
    if not APP_ID or not APP_SECRET:
        return None
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    _token = resp.get("tenant_access_token")
    _token_exp = time.time() + resp.get("expire", 7200)
    return _token


def feishu_send(chat_id: str, text: str):
    tok = _feishu_token()
    if not tok:
        print("[GW] No token — reply skipped")
        return
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        data=json.dumps({
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }).encode(),
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print(f"[GW] Reply sent to chat {chat_id}")
    except Exception as e:
        print(f"[GW] Reply failed: {e}")


# ── 监听 NATS 回复通道 ────────────────────────────
async def _reply_loop():
    await _connect_nats()
    sub = await _nc.subscribe("swarm.outgoing.feishu")
    print("[GW] Subscribed: swarm.outgoing.feishu")
    async for msg in sub.messages:
        try:
            data = json.loads(msg.data.decode())
            feishu_send(data.get("chat_id"), data.get("content", ""))
        except Exception as e:
            print(f"[GW] Reply handler error: {e}")


asyncio.run_coroutine_threadsafe(_reply_loop(), _loop)

# ── HTTP Webhook Handler ──────────────────────────
class FeishuHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))

            # 1. 飞书 URL 验证
            if body.get("type") == "url_verification":
                self._respond(200, {"challenge": body.get("challenge")})
                return

            # 2. 解析消息
            event = body.get("event", {})
            message = event.get("message", {})
            sender = event.get("sender", {}).get("sender_id", {}).get("open_id", "unknown")
            chat_id = message.get("chat_id")
            msg_type = message.get("message_type", "text")
            content = json.loads(message.get("content", "{}"))
            text = content.get("text", "") if msg_type == "text" else str(content)

            print(f"[GW] From {sender}: {text[:80]}")

            # 3. 转发到 NATS
            publish_sync("swarm.incoming.feishu", {
                "source": "feishu",
                "sender": sender,
                "chat_id": chat_id,
                "text": text,
                "timestamp": time.time(),
            })

            self._respond(200, {"code": 0, "msg": "ok"})

        except Exception as e:
            print(f"[GW] HTTP error: {e}")
            self._respond(500, {"code": -1, "msg": str(e)})

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, *args):
        pass


# ── 启动 ──────────────────────────────────────────
if __name__ == "__main__":
    print(f"[GW] HTTP server on http://0.0.0.0:{WEBHOOK_PORT}/webhook/feishu")
    if not APP_ID:
        print("[GW] WARNING: No FEISHU_APP_ID configured — replies disabled")
        print("[GW] Create ~/.worker-bee/gateway.json: {'app_id': 'cli_xxx', 'app_secret': 'xxx'}")

    with socketserver.TCPServer(("0.0.0.0", WEBHOOK_PORT), FeishuHandler) as httpd:
        httpd.serve_forever()
