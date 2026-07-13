"""Minimal AI Agent — thin shell delegating to protocols + loop.

Backward-compatible: ``from agent.agent import AIAgent`` still works.
Internal methods (_build_tools, _to_api_messages) are preserved as forwarders
so existing tests don't break.

Architecture:
    agent/agent.py      ← this file — AIAgent class, config, tool schema caching
    agent/protocols.py  ← AnthropicProtocol / OpenAIProtocol — all format details
    agent/loop.py       ← run_conversation() — protocol-agnostic agent loop
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

from agent.loop import run_conversation as _run_conversation
from agent.protocols import AnthropicProtocol, OpenAIProtocol, Protocol, normalize_schema
from agent.registry import registry

DEFAULT_SYSTEM_PROMPT = (
    "You are a terminal-based AI agent. You have tools to interact with the system:\n"
    "- sys_terminal: run shell commands\n"
    "- fs_read_file / fs_write_file / fs_search_files: file operations\n"
    "- net_web_search / net_web_extract: web access\n"
    "- agent_delegate_task: delegate a single subtask to a child agent\n"
    "- agent_delegate_parallel: delegate multiple subtasks in parallel\n"
    "- agent_cross_validate: run the same task through multiple models for comparison\n"
    "\n"
    "## CRITICAL: Always use tools, never output code blocks\n"
    "- To run a command, ALWAYS call the sys_terminal tool. NEVER wrap commands in ```bash blocks.\n"
    "- To read a file, call fs_read_file. NEVER show 'cat' or 'ls' as markdown.\n"
    "- The user sees tool output directly. You do not need to repeat it unless summarizing.\n"
    "- Be concise. One action per response when possible.\n"
    "\n"
    "## Safety\n"
    "- require_confirmation=false is OK for: find, ls, cat, grep, git status, pip list, python --version\n"
    "- NEVER set require_confirmation=false for: rm -rf, sudo, mkfs, dd, curl | sh, or any disk/format operation."
)


def _load_prompt_files() -> str:
    """Load ~/.worker-bee/{agent.md,soul.md} and return as injection text."""
    parts = []
    base = Path.home() / ".worker-bee"
    for filename in ("agent.md", "soul.md"):
        path = base / filename
        if path.exists():
            parts.append(f"\n\n--- {filename.upper()} ---\n\n{path.read_text(encoding='utf-8')}")
    return "".join(parts)


class AIAgent:
    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "kimi-k2.6")
        self.max_iterations = config.get("max_iterations", 60)
        self.max_context_messages = config.get("max_context_messages", 90)
        self.temperature = config.get("temperature", 0.0)
        base_prompt = config.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
        injection = _load_prompt_files()
        self.system_prompt = f"{base_prompt}{injection}" if injection else base_prompt
        self.enabled_tools = config.get("tools", [])
        self._tool_schema_cache: dict = {}

        provider = config.get("provider", "anthropic")
        self._protocol_name = (
            "openai" if provider.lower() in Protocol._OPENAI_COMPAT else "anthropic"
        )
        # Backward-compat: expose ``_protocol`` as string for existing tests
        self._protocol = self._protocol_name

        self._init_client()

    # ── internal: kept as forwarders for backward compat ────────────────

    def _init_client(self):
        """Create the protocol+client. Exposed for test mocking."""
        self.protocol = Protocol.create(self.config)

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
            result = [normalize_schema(c) for c in converted]
        else:
            result = [normalize_schema(s) for s in schemas]

        self._tool_schema_cache[cache_key] = result
        return result

    # ── message conversion (test backward compat) ───────────────────────

    def _to_api_messages(self, messages: List[Dict]) -> List[Dict]:
        return self.protocol.build_messages(messages)

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
