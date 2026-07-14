"""
swarm listener — NATS 订阅进程，将蜂群消息写入 mailbox。

职责单一：sub → 写文件。不做业务逻辑，不做路由决策。

启动方式：
    python network/transport/listener.py [nats_url]
    # 默认 nats://localhost:4222

进程模型：
    - 独立 asyncio 进程，不在 Agent 循环内
    - 崩了不影响 Agent（只是收不到消息）
    - 配合 systemd 或 wb swarm listen 管理
"""
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import nats
    import nats.js.api as js_api
    from nats.errors import ConnectionClosedError, NoServersError, TimeoutError as NatsTimeoutError
except ModuleNotFoundError:  # pragma: no cover
    nats = None  # type: ignore
    js_api = None  # type: ignore
    ConnectionClosedError = Exception  # type: ignore
    NoServersError = Exception  # type: ignore
    NatsTimeoutError = asyncio.TimeoutError  # type: ignore


# ── 配置 ──────────────────────────────────────────────
DEFAULT_NATS_URL = os.environ.get("SWARM_NATS_URL", "nats://localhost:4222")
MAILBOX_INBOX = Path.home() / ".worker-bee" / "mailbox" / "inbox"
MAILBOX_SENT  = Path.home() / ".worker-bee" / "mailbox" / "sent"
NATS_TIMEOUT = float(os.environ.get("SWARM_NATS_TIMEOUT", "5"))
HEARTBEAT_INTERVAL = 30  # seconds
PID_FILE = Path.home() / ".worker-bee" / "listener.pid"


def _write_pid() -> None:
    """将当前进程 PID 写入文件，用于 CLI 单例检查。"""
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def _remove_pid() -> None:
    """清理 PID 文件。"""
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Failed to remove PID file: %s", exc, exc_info=True)


def read_listener_pid() -> int | None:
    """读取已记录的 listener PID（供 CLI 使用）。"""
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception as exc:
        logger.debug("Failed to read listener PID: %s", exc)
        return None

# ── bee_id 读取 ──────────────────────────────────────────────

def _get_bee_id() -> str:
    try:
        cfg = json.loads((Path.home() / ".worker-bee" / "config.json").read_text(encoding="utf-8"))
        return cfg.get("bee_id", "unknown-bee")
    except Exception as exc:
        logger.warning("Failed to read bee_id from config: %s", exc)
        return "unknown-bee"


def _load_nats_auth_from_config() -> tuple[str | None, str | None]:
    """Read nats_auth from config.yaml if present."""
    for p in [Path("config.yaml"), Path.home() / ".worker-bee" / "config.yaml"]:
        if not p.exists():
            continue
        try:
            import yaml
            with open(p) as f:
                cfg = yaml.safe_load(f) or {}
            auth = cfg.get("nats_auth", {})
            user = auth.get("user", "")
            password = auth.get("password", "")
            if user:
                return user, password
        except Exception as exc:
            logger.debug("Failed to load NATS auth from config: %s", exc)
            return None, None

# ── 心跳 ────────────────────────────────────────────────────────────────────

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
        except Exception as exc:
            logger.warning("Heartbeat failed: %s", exc, exc_info=True)
            await asyncio.sleep(5)  # back off before next attempt

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


def _handle_feishu_notify(data: bytes):
    """Handle swarm.notify.feishu message — send via lark-cli if available.

    Only nodes with lark-cli configured (typically PM) will actually send.
    Others silently skip.
    """
    import shutil
    import subprocess

    lark_cli = shutil.which("lark-cli")
    if not lark_cli:
        return  # No lark-cli on this node, silently skip

    try:
        payload = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("[swarm-listener] ⚠️ Invalid feishu notify payload")
        return

    target_type = payload.get("target_type", "user")
    target_id = payload.get("target_id", "")
    text = payload.get("text", "")
    sender = payload.get("sender", "unknown")

    if not target_id or not text:
        logger.warning("[swarm-listener] ⚠️ Feishu notify missing target_id or text")
        return

    if target_type == "group":
        cmd = [lark_cli, "im", "+messages-send", "--chat-id", target_id, "--text", text]
    else:
        cmd = [lark_cli, "im", "+messages-send", "--user-id", target_id, "--text", text]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    try:
        data = json.loads(result.stdout)
        if data.get("ok") or data.get("code") == 0:
            logger.info("[swarm-listener] 📨 Feishu notify sent → %s (from %s)", target_id, sender)
        else:
            err = data.get("msg", data.get("error", {}).get("message", result.stdout[:200]))
            logger.warning("[swarm-listener] ❌ Feishu notify failed: %s", err)
    except json.JSONDecodeError:
        logger.warning("[swarm-listener] ❌ lark-cli output unreadable: %s", result.stdout[:200])


# ── 主循环 ────────────────────────────────────────────

def _setup_signal_handlers(loop):
    """注册信号处理器，保证收到 SIGTERM/SIGINT 时清理 PID 文件。"""
    for sig in ("SIGTERM", "SIGINT"):
        try:
            loop.add_signal_handler(
                getattr(__import__("signal"), sig),
                lambda: asyncio.create_task(_graceful_shutdown()),
            )
        except Exception as exc:
            logger.debug("Failed to set up signal handler: %s", exc)
            pass


async def _graceful_shutdown():
    """信号触发时取消主任务，使 finally 块执行。"""
    for task in asyncio.all_tasks():
        if task is not asyncio.current_task():
            task.cancel()


async def _ensure_pull_subscription(js, subject: str, stream_name: str, consumer_name: str):
    """创建或重新创建 durable pull subscription。

    在 NATS 断线重连后调用，恢复消息消费。
    """
    config = js_api.ConsumerConfig(
        durable_name=consumer_name,
        ack_policy=js_api.AckPolicy.EXPLICIT,
        ack_wait=30,
        max_deliver=3,
        deliver_policy=js_api.DeliverPolicy.ALL,
    )
    sub = await js.pull_subscribe(
        subject,
        durable=consumer_name,
        stream=stream_name,
        config=config,
    )
    return sub


async def listen(nats_url: str = DEFAULT_NATS_URL, subject: str = "swarm.>"):
    """连接 NATS + JetStream，用 durable pull consumer 拉取消息写入 mailbox。

    使用 JetStream 保证 listener 重启后不丢消息。
    断线重连后自动恢复 subscription，避免静默失效。
    启动前写入 PID 文件，退出时清理，防止重复启动。
    """
    if nats is None:
        raise RuntimeError(
            "nats-py is required for swarm listener. "
            "Install it with: pip install 'worker-bee[swarm]'"
        )
    _write_pid()
    loop = asyncio.get_running_loop()
    _setup_signal_handlers(loop)
    bee_id = _get_bee_id()
    logger.info("[swarm-listener] 连接 %s ... (身份: %s)", nats_url, bee_id)
    connect_kwargs = {
        "connect_timeout": NATS_TIMEOUT,
        "max_reconnect_attempts": -1,  # 无限重连
    }
    nats_user = os.environ.get("NATS_USER")
    nats_password = os.environ.get("NATS_PASSWORD", "")
    if not nats_user:
        cfg_user, cfg_pass = _load_nats_auth_from_config()
        if cfg_user:
            nats_user = cfg_user
            nats_password = cfg_pass
    if nats_user:
        connect_kwargs["user"] = nats_user
        connect_kwargs["password"] = nats_password
    nc = await nats.connect(nats_url, **connect_kwargs)

    # ── JetStream 初始化 ──
    js = nc.jetstream()

    stream_name = "swarm-messages"
    try:
        await js.add_stream(
            name=stream_name,
            subjects=["swarm.>"],
            max_age=3600 * 24 * 90,  # 90天 ≈ 3个月
            storage=js_api.StorageType.FILE,
            retention=js_api.RetentionPolicy.LIMITS,
        )
        logger.info("[swarm-listener] 创建 JetStream Stream: %s", stream_name)
    except Exception as exc:
        if "already exists" in str(exc).lower():
            pass
        else:
            logger.warning("[swarm-listener] JetStream stream creation failed: %s", exc)
            raise

    # Durable Pull Consumer：重启后从上次消费位置继续
    consumer_name = f"swarm-listener-{bee_id}".replace(".", "-")
    sub = await _ensure_pull_subscription(js, subject, stream_name, consumer_name)
    logger.info("[swarm-listener] 就绪 — 监听 %s → %s (JetStream durable)", subject, MAILBOX_INBOX)

    # 启动心跳
    heartbeat_task = asyncio.create_task(_heartbeat_loop(nc, bee_id))

    # 主循环：pull + 写文件 + ack
    # 断线后自动重新创建 subscription
    try:
        while True:
            try:
                msgs = await sub.fetch(batch=10, timeout=5)
            except NatsTimeoutError:
                continue  # 空轮询，继续下一轮
            except (ConnectionClosedError, NoServersError) as e:
                logger.warning("[swarm-listener] ⚠️ NATS 连接中断 (%s)，等待重连...", type(e).__name__)
                # 等待连接恢复
                while nc.is_closed or not nc.is_connected:
                    await asyncio.sleep(1)
                logger.info("[swarm-listener] 🔄 NATS 已重连，重新订阅...")
                sub = await _ensure_pull_subscription(js, subject, stream_name, consumer_name)
                logger.info("[swarm-listener] ✅ 重新订阅完成")
                continue
            for msg in msgs:
                _write_envelope(msg.subject, msg.reply or "", msg.data)
                if msg.subject == "swarm.notify.feishu":
                    _handle_feishu_notify(msg.data)
                await msg.ack()
    except KeyboardInterrupt:
        logger.info("\n[swarm-listener] 收到中断信号，正在 drain ...")
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        try:
            await nc.drain()
        except Exception as exc:
            logger.debug("NATS drain failed: %s", exc)
            pass
        _remove_pid()
        logger.info("[swarm-listener] 已断开")


# ── 入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_NATS_URL
    try:
        asyncio.run(listen(nats_url=url))
    finally:
        _remove_pid()
