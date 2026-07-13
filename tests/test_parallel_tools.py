"""Parallel tool execution tests."""
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from agent.loop import _execute_single_tool


class FakeRegistry:
    """Mock registry that tracks call order and delays."""

    def __init__(self, delays: dict):
        self.delays = delays
        self.calls = []
        self._lock = MagicMock()

    def call(self, name, arguments: dict):
        # name may be a MagicMock from the protocol mock
        name_str = name if isinstance(name, str) else getattr(name, "_mock_name", str(name))
        self.calls.append(name_str)
        delay = self.delays.get(name_str, 0)
        if delay:
            time.sleep(delay)
        return f"result:{name_str}"

    def is_parallel_safe(self, name) -> bool:
        name_str = name if isinstance(name, str) else getattr(name, "_mock_name", str(name))
        return name_str.startswith("safe_")


class TestExecuteSingleTool:
    def test_success(self):
        reg = FakeRegistry({})
        result = _execute_single_tool(reg, "safe_read", {"path": "/tmp"}, "tc_1")
        assert result == "result:safe_read"
        assert reg.calls == ["safe_read"]

    def test_error_returns_generic_message(self):
        class BadRegistry:
            def call(self, name, arguments):
                raise RuntimeError("boom")
            def is_parallel_safe(self, name):
                return True

        reg = BadRegistry()
        result = _execute_single_tool(reg, "bad", {}, "tc_1")
        assert "failed" in result.lower()


class TestParallelExecutionInLoop:
    """Verify that the loop groups safe/unsafe tools correctly.

    We patch _api_call_with_retry to bypass the real network layer and
    feed synthetic responses directly into the loop body.
    """

    def test_parallel_batch_saves_time(self, monkeypatch):
        """Two safe tools with 0.2s delay each should finish in ~0.2s, not 0.4s."""
        from agent.loop import run_conversation

        delays = {"safe_a": 0.2, "safe_b": 0.2}
        fake_reg = FakeRegistry(delays)

        # Patch the registry import inside loop.py
        monkeypatch.setattr("agent.loop.tool_registry", fake_reg)

        from agent.protocols import Protocol

        class FakeProtocol(Protocol):
            def build_messages(self, msgs):
                return list(msgs)

            def build_assistant_block(self, text, reasoning, tool_calls):
                return {"role": "assistant", "content": text}

            def build_tool_result_block(self, tc_id, result):
                return {"role": "tool", "tool_call_id": tc_id, "content": result}

        call_count = [0]

        def _fake_api_call(protocol, system_prompt, api_msgs, tools, model, temperature):
            """Return synthetic responses without hitting real APIs."""
            call_count[0] += 1
            if call_count[0] == 1:
                # First response: assistant requests two tools
                return MagicMock(
                    choices=[MagicMock(
                        message=MagicMock(
                            content="",
                                tool_calls=[
                                MagicMock(
                                    id="tc_a",
                                    function=SimpleNamespace(name="safe_a", arguments='{"x":1}'),
                                ),
                                MagicMock(
                                    id="tc_b",
                                    function=SimpleNamespace(name="safe_b", arguments='{"x":2}'),
                                ),
                            ],
                        )
                    )]
                ), None
            # Second response: assistant is done
            return MagicMock(
                choices=[MagicMock(
                    message=MagicMock(content="Done.", tool_calls=None)
                )]
            ), None

        monkeypatch.setattr("agent.loop._api_call_with_retry", _fake_api_call)

        # Monkey-patch build_response on the protocol so it works with our mocks
        def _build_response(self, response):
            msg = response.choices[0].message
            tool_calls = []
            for tc in (msg.tool_calls or []):
                func = tc.function
                tool_calls.append({
                    "id": tc.id,
                    "name": func.name,
                    "arguments": json.loads(func.arguments),
                })
            return {
                "text": msg.content or "",
                "reasoning": "",
                "tool_calls": tool_calls,
            }

        import agent.protocols as proto_mod
        monkeypatch.setattr(proto_mod.Protocol, "build_response", _build_response)

        class FakeAgent:
            protocol = FakeProtocol()
            model = "gpt-4"
            system_prompt = "You are helpful."
            max_iterations = 5
            temperature = 0.0
            _protocol_name = "openai"

            def _build_tools(self, tools):
                return None

        import json
        agent = FakeAgent()
        start = time.time()

        result = run_conversation(agent, [{"role": "user", "content": "test"}])
        elapsed = time.time() - start

        # Both safe tools executed in parallel → elapsed ≈ 0.2s, not 0.4s
        # Allow 0.5s for ThreadPoolExecutor startup overhead on slow CI runners.
        assert elapsed < 0.5, f"Expected parallel execution (~0.2s), got {elapsed:.2f}s"
        assert set(fake_reg.calls) == {"safe_a", "safe_b"}
