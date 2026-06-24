"""
swarm listener — NATS 订阅进程，将蜂群消息写入 mailbox。

职责单一：sub → 写文件。不做业务逻辑，不做路由决策。

启动方式：
    python swarm/listener.py [nats_url]
    # 默认 nats://localhost:4222

进程模型：
    - 独立 asyncio 进程，不在 Agent 循环内
    - 崩了不影响 Agent（只是收不到消息）
    - 配合 systemd 或 wb swarm listen 管理
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import nats


# ── 配置 ──────────────────────────────────────────────
DEFAULT_NATS_URL = os.environ.get("SWARM_NATS_URL", "nats://localhost:4222")
MAILBOX_INBOX = Path.home() / ".worker-bee" / "mailbox" / "inbox"
MAILBOX_SENT  = Path.home() / ".worker-bee" / "mailbox" / "sent"
NATS_TIMEOUT = float(os.environ.get("SWARM_NATS_TIMEOUT", "5"))
HEARTBEAT_INTERVAL = 30  # seconds

# ── bee_id 读取 ──────────────────────────────────────────────

def _get_bee_id() -> str:
    try:
        cfg = json.loads((Path.home() / ".worker-bee" / "config.json").read_text(encoding="utf-8"))
        return cfg.get("bee_id", "unknown-bee")
    except Exception:
        return "unknown-bee"

# ── 心跳 ────────────────────────────────────────────────────

async def _heartbeat_loop(nc, bee_id: str):
    """每 30 秒发送一次心跳，包含当前能力清单。"""
    while True:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            heartbeat = {
                "message_id": str(uuid.uuid4()),
                "subject": f"swarm.heartbeat.{bee_id}",
                "data": {"status": "alive", "capabilities": []},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sender": bee_id,
                "sequence": _next_seq(),
            }
            await nc.publish(f"swarm.heartbeat.{bee_id}", json.dumps(heartbeat).encode())
        except asyncio.CancelledError:
            break
        except Exception:
            pass  # 心跳失败不影响主循环

# ── 消息写入 ────────────────────────────────────────────────────

_sender_sequence = 0

def _next_seq() -> int:
    global _sender_sequence
    _sender_sequence += 1
    return _sender_sequence


def _write_envelope(subject: str, reply_to: str, data: bytes):
    """将一条 NATS 消息写成 mailbox JSON 文件。"""
    MAILBOX_INBOX.mkdir(parents=True, exist_ok=True)

    try:
        payload = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {"raw": data.decode("utf-8", errors="replace")}

    # 如果消息本身已经包含 message_id（发送方已包裵），则直接使用
    if isinstance(payload, dict) and "message_id" in payload:
        envelope = dict(payload)
        envelope.setdefault("reply_to", reply_to or "")
    else:
        envelope = {
            "message_id": str(uuid.uuid4()),
            "subject": subject,
            "reply_to": reply_to or "",
            "data": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sender": "unknown",
            "sequence": _next_seq(),
        }

    filename = f"{envelope['message_id']}.json"
    filepath = MAILBOX_INBOX / filename
    filepath.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 主循环 ────────────────────────────────────────────

async def listen(nats_url: str = DEFAULT_NATS_URL, subject: str = "swarm.>"):
    """连接 NATS，订阅 subject，写入 mailbox。永不退出。"""
    bee_id = _get_bee_id()
    print(f"[swarm-listener] 连接 {nats_url} ... (身份: {bee_id})")
    nc = await nats.connect(nats_url, connect_timeout=NATS_TIMEOUT)

    # ── bee_id 冲突检测 ──
    conflict_subject = f"swarm.heartbeat.{bee_id}"
    conflict_detected = False

    async def _conflict_check(msg):
        nonlocal conflict_detected
        try:
            data = json.loads(msg.data.decode("utf-8"))
            if data.get("action") == "check_conflict":
                # 回复冲突检查——有人在问是不是重复了
                reply_data = json.dumps({"conflict": True, "responder": bee_id})
                await nc.publish(msg.reply, reply_data.encode())
        except Exception:
            pass

    await nc.subscribe(conflict_subject, cb=_conflict_check)

    # 发送冲突检查请求，等 2 秒
    check_msg = json.dumps({"action": "check_conflict"})
    try:
        resp = await nc.request(conflict_subject, check_msg.encode(), timeout=2)
        resp_data = json.loads(resp.data.decode("utf-8"))
        if resp_data.get("conflict"):
            print(f"\n[swarm-listener] ❌ bee_id 冲突: {bee_id} 已被其他节点使用")
            print("[swarm-listener] 请修改 config.json 中的 bee_id 后重启。")
            await nc.drain()
            sys.exit(1)
    except asyncio.TimeoutError:
        pass  # 没有冲突，继续
    except Exception:
        pass

    # 正式订阅
    async def handler(msg):
        _write_envelope(msg.subject, msg.reply or "", msg.data)

    await nc.subscribe(subject, cb=handler)
    print(f"[swarm-listener] 就绪 — 监听 {subject} → {MAILBOX_INBOX}")

    # 启动心跳
    heartbeat_task = asyncio.create_task(_heartbeat_loop(nc, bee_id))

    # 一直跑，直到被信号中断
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n[swarm-listener] 收到中断信号，正在 drain ...")
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        await nc.drain()
        print("[swarm-listener] 已断开")


# ── 入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_NATS_URL
    asyncio.run(listen(nats_url=url))
