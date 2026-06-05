"""Minimal AI Agent — thin shell delegating to protocols + loop.

Backward-compatible: ``from worker_bee.agent import AIAgent`` still works.
All internal methods (_build_tools, _to_api_messages, _extract_text, etc.)
are preserved as forwarders so existing tests don't break.

Architecture:
    worker_bee/agent.py      ← this file — AIAgent class, config, tool schema caching
    worker_bee/protocols.py  ← AnthropicProtocol / OpenAIProtocol — all format details
    worker_bee/loop.py       ← run_conversation() — protocol-agnostic agent loop
"""
import json
from typing import Dict, List, Optional

from worker_bee.loop import run_conversation as _run_conversation
from worker_bee.protocols import AnthropicProtocol, OpenAIProtocol, Protocol
from worker_bee.registry import registry


class AIAgent:
    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "kimi-k2.6")
        self.max_iterations = config.get("max_iterations", 30)
        self.max_context_messages = config.get("max_context_messages", 60)
        self.temperature = config.get("temperature", 0.0)
        self.system_prompt = config.get(
            "system_prompt", "You are a helpful assistant with tool access."
        )
        self.enabled_tools = config.get("tools", [])
        self._tool_schema_cache: dict = {}

        provider = config.get("provider", "anthropic")
        self._protocol_name = "openai" if provider == "openai" else "anthropic"
        # Backward-compat: expose ``_protocol`` as string for existing tests
        self._protocol = self._protocol_name

        self._init_client()

    # ── internal: kept as forwarders for backward compat ────────────────

    def _init_client(self):
        """Create the protocol+client. Exposed for test mocking."""
        if self._protocol_name == "openai":
            self.protocol = OpenAIProtocol(self.config)
        else:
            self.protocol = AnthropicProtocol(self.config)

    @property
    def protocol(self) -> Protocol:
        return self._protocol_obj

    @protocol.setter
    def protocol(self, value: Protocol):
        self._protocol_obj = value

    @property
    def client(self):
        """Backward-compat: tests mock ``agent.client`` directly."""
        return self.protocol.client

    @client.setter
    def client(self, value):
        self.protocol.client = value

    def _build_tools(self, tool_names=None):
        """Forwarder — cached tool schema builder. Kept for test compat."""
        names = tool_names if tool_names is not None else self.enabled_tools
        if not names:
            return None

        cache_key = (frozenset(names), self._protocol_name, registry.generation)
        if cache_key in self._tool_schema_cache:
            return self._tool_schema_cache[cache_key]

        schemas = registry.get_schemas(enabled=names)

        if self._protocol_name == "openai":
            converted = []
            for s in schemas:
                openai_schema = {
                    "name": s["name"],
                    "description": s["description"],
                    "parameters": s.get("input_schema", {"type": "object"}),
                }
                converted.append({"type": "function", "function": openai_schema})
            result = converted
        else:
            result = schemas

        self._tool_schema_cache[cache_key] = result
        return result

    # ── message conversion (test backward compat) ───────────────────────

    def _to_api_messages(self, messages: List[Dict]) -> List[Dict]:
        return self.protocol.build_messages(messages)

    def _extract_text(self, msg) -> str:
        """Test-compat: extracts text from raw API response object."""
        if self._protocol_name == "anthropic":
            texts = []
            for block in msg.content:
                if hasattr(block, "text"):
                    texts.append(block.text)
            return "\n".join(texts)
        return msg.content or ""

    def _extract_reasoning(self, msg) -> Optional[str]:
        """Test-compat: extracts reasoning from raw API response object."""
        if self._protocol_name == "anthropic":
            parts = []
            for block in msg.content:
                if getattr(block, "type", None) == "thinking" and hasattr(block, "thinking"):
                    parts.append(block.thinking)
            return "\n".join(parts) if parts else None
        rc = getattr(msg, "reasoning_content", None)
        if rc:
            return rc
        if hasattr(msg, "model_extra") and msg.model_extra:
            return msg.model_extra.get("reasoning_content")
        return None

    def _extract_tool_calls(self, msg) -> List[Dict]:
        """Test-compat: extracts tool_calls from raw API response object."""
        calls = []
        if self._protocol_name == "anthropic":
            for block in msg.content:
                if getattr(block, "type", None) == "tool_use":
                    args = block.input
                    if hasattr(args, "model_dump"):
                        args = args.model_dump()
                    calls.append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": args,
                    })
        else:
            for tc in (msg.tool_calls or []):
                calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })
        return calls

    # ── public API ─────────────────────────────────────────────────────

    def run(
        self,
        messages: List[Dict],
        tools: Optional[List[str]] = None,
        deck=None,
    ) -> str:
        """Run one turn of conversation with automatic tool-use loop.

        Args:
            messages: Conversation history in internal format.
            tools: Optional tool name list (default: self.enabled_tools).
            deck: Optional Deck — if provided, tools drawn ONLY from Deck.

        Returns:
            Final assistant text, or "(reached max iterations)".
        """
        return _run_conversation(self, messages, tools=tools, deck=deck)
