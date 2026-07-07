"""Tests for gateway module — Hermes-style platform adapter framework."""
import json
import threading
import time
import unittest
from dataclasses import dataclass
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import MagicMock, patch

from gateway.base import BasePlatformAdapter, MessageEvent, SendResult
from gateway.config import GatewayConfig, PlatformConfig
from gateway.platform_registry import PlatformEntry, PlatformRegistry, platform_registry
from gateway.run import GatewayRunner


# ── Fixtures ─────────────────────────────────────────────────────────────────

@dataclass
class MockConfig:
    port: int = 18080
    host: str = "127.0.0.1"
    enabled: bool = True
    extra: dict = None


class MockAdapter(BasePlatformAdapter):
    """In-memory adapter for testing — no network I/O."""

    def __init__(self, config):
        super().__init__(config)
        self.started = False
        self.stopped = False
        self.sent: list = []

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def send(self, event, text):
        self.sent.append((event, text))
        return SendResult(success=True)


# ── Base & Data Structures ───────────────────────────────────────────────────

class TestMessageEvent(unittest.TestCase):
    def test_defaults(self):
        ev = MessageEvent(platform="test", sender_id="u1", text="hello")
        self.assertEqual(ev.platform, "test")
        self.assertEqual(ev.sender_id, "u1")
        self.assertEqual(ev.text, "hello")
        self.assertIsNone(ev.thread_id)
        self.assertIsNone(ev.message_id)
        self.assertEqual(ev.raw, {})


class TestSendResult(unittest.TestCase):
    def test_success(self):
        r = SendResult(success=True, message_id="m123")
        self.assertTrue(r.success)
        self.assertEqual(r.message_id, "m123")

    def test_failure(self):
        r = SendResult(success=False, error="timeout")
        self.assertFalse(r.success)
        self.assertEqual(r.error, "timeout")


# ── PlatformRegistry ─────────────────────────────────────────────────────────

class TestPlatformRegistry(unittest.TestCase):
    def setUp(self):
        self.reg = PlatformRegistry()

    def test_register_and_create(self):
        self.reg.register(
            PlatformEntry(
                name="mock",
                label="Mock Platform",
                adapter_factory=lambda cfg: MockAdapter(cfg),
                check_fn=lambda: True,
            )
        )
        adapter = self.reg.create_adapter("mock", MockConfig())
        self.assertIsInstance(adapter, MockAdapter)

    def test_create_missing(self):
        self.assertIsNone(self.reg.create_adapter("nonexistent", MockConfig()))

    def test_create_check_fails(self):
        self.reg.register(
            PlatformEntry(
                name="broken",
                label="Broken",
                adapter_factory=lambda cfg: MockAdapter(cfg),
                check_fn=lambda: False,
            )
        )
        self.assertIsNone(self.reg.create_adapter("broken", MockConfig()))

    def test_create_validate_fails(self):
        self.reg.register(
            PlatformEntry(
                name="strict",
                label="Strict",
                adapter_factory=lambda cfg: MockAdapter(cfg),
                check_fn=lambda: True,
                validate_config=lambda cfg: False,
            )
        )
        self.assertIsNone(self.reg.create_adapter("strict", MockConfig()))


# ── GatewayConfig ────────────────────────────────────────────────────────────

class TestGatewayConfig(unittest.TestCase):
    def test_empty(self):
        cfg = GatewayConfig.from_dict(None)
        self.assertFalse(cfg.enabled)
        self.assertEqual(cfg.platforms, {})

    def test_from_dict(self):
        cfg = GatewayConfig.from_dict({
            "enabled": True,
            "platforms": {
                "feishu": {"enabled": True, "port": 9090, "host": "0.0.0.0"},
                "slack": {"enabled": False, "port": 9091},
            },
        })
        self.assertTrue(cfg.enabled)
        self.assertIn("feishu", cfg.platforms)
        self.assertEqual(cfg.platforms["feishu"].port, 9090)
        self.assertFalse(cfg.platforms["slack"].enabled)

    def test_load_missing_file(self):
        cfg = GatewayConfig.load(Path("/nonexistent/config.json"))
        self.assertFalse(cfg.enabled)


# ── GatewayRunner ────────────────────────────────────────────────────────────

class TestGatewayRunner(unittest.TestCase):
    def setUp(self):
        self.mock_reg = PlatformRegistry()
        self.mock_reg.register(
            PlatformEntry(
                name="mock",
                label="Mock",
                adapter_factory=lambda cfg: MockAdapter(cfg),
                check_fn=lambda: True,
            )
        )

    @patch("gateway.run.platform_registry", new_callable=lambda: PlatformRegistry())
    def test_start_stop(self, mock_global_reg):
        # Register locally on the patched global registry
        mock_global_reg.register(
            PlatformEntry(
                name="mock",
                label="Mock",
                adapter_factory=lambda cfg: MockAdapter(cfg),
                check_fn=lambda: True,
            )
        )
        cfg = GatewayConfig(
            enabled=True,
            platforms={"mock": PlatformConfig(enabled=True)},
        )
        runner = GatewayRunner(cfg)
        runner.start()
        self.assertTrue(runner._running)
        self.assertIn("mock", runner.adapters)
        self.assertTrue(runner.adapters["mock"].started)

        adapter = runner.adapters["mock"]
        runner.stop()
        self.assertFalse(runner._running)
        self.assertTrue(adapter.stopped)

    @patch("gateway.run.platform_registry", new_callable=lambda: PlatformRegistry())
    def test_disabled_platform_skipped(self, mock_global_reg):
        mock_global_reg.register(
            PlatformEntry(
                name="mock",
                label="Mock",
                adapter_factory=lambda cfg: MockAdapter(cfg),
                check_fn=lambda: True,
            )
        )
        cfg = GatewayConfig(
            enabled=True,
            platforms={"mock": PlatformConfig(enabled=False)},
        )
        runner = GatewayRunner(cfg)
        runner.start()
        self.assertNotIn("mock", runner.adapters)
        runner.stop()

    @patch("gateway.run.platform_registry", new_callable=lambda: PlatformRegistry())
    def test_route_incoming(self, mock_global_reg):
        mock_global_reg.register(
            PlatformEntry(
                name="mock",
                label="Mock",
                adapter_factory=lambda cfg: MockAdapter(cfg),
                check_fn=lambda: True,
            )
        )
        cfg = GatewayConfig(
            enabled=True,
            platforms={"mock": PlatformConfig(enabled=True)},
        )
        runner = GatewayRunner(cfg)
        runner.start()

        event = MessageEvent(platform="mock", sender_id="u1", text="hello")
        runner.route_incoming(event)

        adapter = runner.adapters["mock"]
        self.assertEqual(len(adapter.sent), 1)
        self.assertEqual(adapter.sent[0][1], "Echo: hello")

        runner.stop()

    @patch("gateway.run.platform_registry", new_callable=lambda: PlatformRegistry())
    def test_process_with_agent_override(self, mock_global_reg):
        mock_global_reg.register(
            PlatformEntry(
                name="mock",
                label="Mock",
                adapter_factory=lambda cfg: MockAdapter(cfg),
                check_fn=lambda: True,
            )
        )
        cfg = GatewayConfig(
            enabled=True,
            platforms={"mock": PlatformConfig(enabled=True)},
        )
        runner = GatewayRunner(cfg)
        runner.process_with_agent = lambda ev: f"Custom: {ev.text}"
        runner.start()

        event = MessageEvent(platform="mock", sender_id="u1", text="ping")
        runner.route_incoming(event)

        adapter = runner.adapters["mock"]
        self.assertEqual(adapter.sent[0][1], "Custom: ping")
        runner.stop()


# ── FeishuAdapter (integration smoke) ────────────────────────────────────────

class TestFeishuAdapter(unittest.TestCase):
    """Lightweight smoke tests for FeishuAdapter webhook server."""

    @patch("gateway.platforms.feishu._get_feishu_token", return_value="fake_token")
    @patch("gateway.platforms.feishu._send_reply", return_value={"data": {"message_id": "m1"}})
    def test_webhook_challenge(self, mock_send, mock_token):
        from gateway.platforms.feishu import FeishuAdapter

        cfg = MockConfig(port=18081, host="127.0.0.1")
        adapter = FeishuAdapter(cfg)
        adapter.start()
        try:
            time.sleep(0.3)  # Let server bind
            conn = HTTPConnection("127.0.0.1", 18081)
            payload = json.dumps({"type": "url_verification", "challenge": "abc123"})
            conn.request("POST", "/webhook", body=payload, headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            body = json.loads(resp.read().decode())
            self.assertEqual(body["challenge"], "abc123")
            conn.close()
        finally:
            adapter.stop()

    @patch("gateway.platforms.feishu._get_feishu_token", return_value="fake_token")
    @patch("gateway.platforms.feishu._send_reply", return_value={"data": {"message_id": "m1"}})
    def test_webhook_message_event(self, mock_send, mock_token):
        from gateway.platforms.feishu import FeishuAdapter

        cfg = MockConfig(port=18082, host="127.0.0.1")
        adapter = FeishuAdapter(cfg)
        # Capture incoming events
        received_events = []
        original_handle = adapter.handle_incoming

        def capture(event):
            received_events.append(event)
            # Don't call original to avoid full route cycle in unit test

        adapter.handle_incoming = capture
        adapter.start()
        try:
            time.sleep(0.3)
            conn = HTTPConnection("127.0.0.1", 18082)
            payload = json.dumps({
                "header": {"event_type": "im.message.receive_v1", "token": ""},
                "event": {
                    "message": {
                        "message_type": "text",
                        "content": json.dumps({"text": "hello feishu"}),
                        "chat_id": "chat_1",
                        "chat_type": "p2p",
                        "message_id": "msg_1",
                    },
                    "sender": {"sender_id": {"open_id": "user_1"}},
                },
            })
            conn.request("POST", "/webhook", body=payload, headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            conn.close()
            time.sleep(0.5)  # Wait for daemon thread
            self.assertEqual(len(received_events), 1)
            ev = received_events[0]
            self.assertEqual(ev.platform, "feishu")
            self.assertEqual(ev.sender_id, "user_1")
            self.assertEqual(ev.text, "hello feishu")
            self.assertEqual(ev.message_id, "msg_1")
        finally:
            adapter.stop()

    @patch("gateway.platforms.feishu._get_feishu_token", return_value="fake_token")
    @patch("gateway.platforms.feishu._send_reply", return_value={"data": {"message_id": "m99"}})
    def test_send_p2p(self, mock_send, mock_token):
        from gateway.platforms.feishu import FeishuAdapter

        cfg = MockConfig()
        adapter = FeishuAdapter(cfg)
        event = MessageEvent(
            platform="feishu",
            sender_id="user_1",
            text="hi",
            raw={"chat_type": "p2p", "chat_id": "", "sender_open_id": "user_1"},
        )
        result = adapter.send(event, "reply")
        self.assertTrue(result.success)
        self.assertEqual(result.message_id, "m99")
        mock_send.assert_called_once()
        # First arg should be open_id for p2p
        self.assertEqual(mock_send.call_args[0][0], "user_1")
        self.assertEqual(mock_send.call_args[0][1], "open_id")


if __name__ == "__main__":
    unittest.main()
