"""Minimal AI Agent — dual-protocol (Anthropic/OpenAI) with Deck-bound tool execution.

When run with a Deck, the agent can only use tools in the Deck.
Without a Deck, falls back to config-level tool list.
"""
import json
from typing import List, Dict, Optional

from worker_bee.registry import registry


class AIAgent:
    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "kimi-k2.6")
        self.max_iterations = config.get("max_iterations", 30)
        self.system_prompt = config.get("system_prompt", "You are a helpful assistant with tool access.")
        self.enabled_tools = config.get("tools", [])
        self._tool_schema_cache: dict = {}
        self._init_client()

    def _init_client(self):
        provider = self.config.get("provider", "anthropic")
        if provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.config["api_key"],
                base_url=self.config.get("base_url")
            )
            self._protocol = "openai"
        else:
            from anthropic import Anthropic
            self.client = Anthropic(
                api_key=self.config["api_key"],
                base_url=self.config.get("base_url")
            )
            self._protocol = "anthropic"

    def _build_tools(self, tool_names=None):
        names = tool_names if tool_names is not None else self.enabled_tools
        if not names:
            return None

        # Cache key: (frozenset(names), protocol, registry_generation)
        cache_key = (frozenset(names), self._protocol, registry.generation)
        if cache_key in self._tool_schema_cache:
            return self._tool_schema_cache[cache_key]

        schemas = registry.get_schemas(enabled=names)
        if self._protocol == "openai":
            converted = []
            for s in schemas:
                openai_schema = {
                    "name": s["name"],
                    "description": s["description"],
                    "parameters": s.get("input_schema", {"type": "object"})
                }
                converted.append({"type": "function", "function": openai_schema})
            result = converted
        else:
            result = schemas

        self._tool_schema_cache[cache_key] = result
        return result

    def _to_api_messages(self, messages: List[Dict]) -> List[Dict]:
        """Normalize internal messages to Anthropic/OpenAI format."""
        api_msgs = []
        for m in messages:
            role = m["role"]
            content = m.get("content", "")
            tool_calls = m.get("tool_calls")
            reasoning = m.get("reasoning")
            if role == "tool":
                if self._protocol == "anthropic":
                    api_msgs.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": m.get("tool_call_id", ""),
                            "content": content
                        }]
                    })
                else:
                    api_msgs.append({"role": "tool", "tool_call_id": m.get("tool_call_id", ""), "content": content})
            elif role == "assistant" and tool_calls:
                if self._protocol == "anthropic":
                    blocks = []
                    if reasoning:
                        blocks.append({"type": "text", "text": reasoning})
                    elif content:
                        blocks.append({"type": "text", "text": content})
                    for tc in tool_calls:
                        blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id", tc.get("tool_use_id", "")),
                            "name": tc.get("name", tc.get("function", {}).get("name", "")),
                            "input": tc.get("input") or tc.get("function", {}).get("arguments", {}) or tc.get("arguments", {})
                        })
                    api_msgs.append({"role": "assistant", "content": blocks})
                else:
                    # OpenAI protocol: preserve reasoning_content if present
                    assistant_payload = {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": [{"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])}} for tc in tool_calls]
                    }
                    if reasoning:
                        assistant_payload["reasoning_content"] = reasoning
                    api_msgs.append(assistant_payload)
            else:
                api_msgs.append({"role": role, "content": content})
        return api_msgs

    def _extract_text(self, msg) -> str:
        """Extract text from API response content."""
        if self._protocol == "anthropic":
            texts = []
            for block in msg.content:
                if hasattr(block, "text"):
                    texts.append(block.text)
            return "\n".join(texts)
        return msg.content or ""

    def _extract_reasoning(self, msg) -> Optional[str]:
        """Extract reasoning / thinking content from API response."""
        if self._protocol == "anthropic":
            parts = []
            for block in msg.content:
                if getattr(block, "type", None) == "thinking" and hasattr(block, "thinking"):
                    parts.append(block.thinking)
            return "\n".join(parts) if parts else None
        else:
            # OpenAI protocol: some providers (Moonshot/Kimi) include reasoning_content
            rc = getattr(msg, "reasoning_content", None)
            if rc:
                return rc
            # Some providers embed reasoning in the message object as an attribute
            if hasattr(msg, "model_extra") and msg.model_extra:
                return msg.model_extra.get("reasoning_content")
            return None

    def _extract_tool_calls(self, msg) -> List[Dict]:
        """Extract tool calls from API response."""
        calls = []
        if self._protocol == "anthropic":
            for block in msg.content:
                if getattr(block, "type", None) == "tool_use":
                    args = block.input
                    if hasattr(args, "model_dump"):
                        args = args.model_dump()
                    calls.append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": args
                    })
        else:
            for tc in (msg.tool_calls or []):
                calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments)
                })
        return calls

    def run(self, messages: List[Dict], tools: Optional[List[str]] = None, deck=None) -> str:
        """Run one turn of conversation with tool use loop.

        Args:
            messages: Conversation history.
            tools: Optional list of tool names to enable for this run.
                   If None, uses self.enabled_tools from config.
            deck: Optional Deck instance. If provided, tools are drawn ONLY
                  from the Deck. Overrides the `tools` argument.
        """
        if deck is not None:
            active_tools = deck.get_schemas_for_protocol(self._protocol)
            if not active_tools:
                active_tools = None
        else:
            active_tools = self._build_tools(tools)
        api_messages = self._to_api_messages(messages)

        for i in range(self.max_iterations):
            if self._protocol == "anthropic":
                kwargs = {
                    "model": self.model,
                    "max_tokens": 4096,
                    "messages": api_messages,
                    "system": self.system_prompt,
                }
                if active_tools:
                    kwargs["tools"] = active_tools
                response = self.client.messages.create(**kwargs)
                msg = response
            else:
                kwargs = {
                    "model": self.model,
                    "messages": [{"role": "system", "content": self.system_prompt}] + api_messages,
                }
                if active_tools:
                    kwargs["tools"] = active_tools
                    kwargs["tool_choice"] = "auto"
                response = self.client.chat.completions.create(**kwargs)
                msg = response.choices[0].message

            text = self._extract_text(msg)
            reasoning = self._extract_reasoning(msg)
            tool_calls = self._extract_tool_calls(msg)

            if not tool_calls:
                return text

            # Record assistant message with tool calls and reasoning
            assistant_msg = {"role": "assistant", "content": text, "tool_calls": tool_calls}
            if reasoning:
                assistant_msg["reasoning"] = reasoning
            messages.append(assistant_msg)

            if self._protocol == "anthropic":
                api_msgs = []
                if reasoning:
                    api_msgs.append({"type": "thinking", "thinking": reasoning})
                elif text:
                    api_msgs.append({"type": "text", "text": text})
                for tc in tool_calls:
                    api_msgs.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["arguments"]
                    })
                api_messages.append({"role": "assistant", "content": api_msgs})
            else:
                assistant_payload = {
                    "role": "assistant",
                    "content": text,
                    "tool_calls": [{"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])}} for tc in tool_calls]
                }
                if reasoning:
                    assistant_payload["reasoning_content"] = reasoning
                api_messages.append(assistant_payload)

            # Execute tools
            for tc in tool_calls:
                result = registry.call(tc["name"], tc["arguments"])
                tool_msg = {"role": "tool", "tool_call_id": tc["id"], "content": result}
                messages.append(tool_msg)

                if self._protocol == "anthropic":
                    api_messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tc["id"],
                            "content": result
                        }]
                    })
                else:
                    api_messages.append(tool_msg)

        return "(reached max iterations)"
