"""Protocol-agnostic agent conversation loop.

This module runs the core agent loop — it never branches on provider.
All protocol details (message format, API call shape, response extraction)
are handled by the Protocol object passed in.
"""
from typing import Dict, List, Optional, Tuple, Any
import time
import logging

from agent.registry import registry
from agent.audit import log_tool_call
from agent.governance import govern_messages
from agent.models import ModelRegistry

logger = logging.getLogger(__name__)


# ── API resilience: retry with exponential backoff ──────────────────────

def _api_call_with_retry(
    protocol,
    system_prompt: str,
    api_msgs: List[Dict],
    active_tools,
    model: str,
    temperature: float,
    max_retries: int = 3,
) -> Tuple[Any, Optional[str]]:
    """Call protocol.api_call with automatic retry and backoff.

    Returns (response, error_category) where error_category is one of:
    'rate_limited', 'timeout', 'server_error', 'connection', None.
    """
    import traceback

    last_error_category = None
    for attempt in range(max_retries):
        try:
            response = protocol.api_call(
                system_prompt, api_msgs, active_tools, model, temperature,
            )
            return response, None
        except Exception as exc:
            exc_str = str(exc).lower()
            exc_type = type(exc).__name__

            # Classify error
            if "429" in exc_str or "rate_limit" in exc_str or "too many requests" in exc_str:
                last_error_category = "rate_limited"
                wait = 60  # Default for rate limit; no header access at this layer
            elif "timeout" in exc_str or "timed out" in exc_str:
                last_error_category = "timeout"
                wait = 2 ** attempt
            elif "connection" in exc_str or "connect" in exc_str or "broken pipe" in exc_str or "reset" in exc_str:
                last_error_category = "connection"
                wait = 2 ** attempt
            elif "502" in exc_str or "503" in exc_str or "504" in exc_str or "service unavailable" in exc_str:
                last_error_category = "server_error"
                wait = 2 ** attempt
            else:
                # Unknown error: retry once quickly then give up
                last_error_category = "unknown"
                wait = 1 if attempt < max_retries - 1 else 0

            if attempt < max_retries - 1:
                logger.warning(
                    "API call failed (%s, attempt %d/%d): %s — retrying in %ds",
                    last_error_category, attempt + 1, max_retries, exc_type, wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "API call failed after %d attempts (%s): %s",
                    max_retries, last_error_category, traceback.format_exc(),
                )

    return None, last_error_category


def run_conversation(
    agent,          # AIAgent instance (for config, protocol, max_iterations access)
    messages: List[Dict],
    tools: Optional[List[str]] = None,
    deck=None,
) -> str:
    """Run one turn of conversation with automatic tool-use loop.

    Args:
        agent: AIAgent instance — supplies protocol, model, system_prompt, max_iterations.
        messages: Conversation history in internal format.
        tools: Optional list of enabled tool names.
        deck: Optional Deck; if provided, tools drawn ONLY from the Deck.

    Returns:
        Final assistant text response, or "(reached max iterations)".
    """
    protocol = agent.protocol
    max_iters = agent.max_iterations

    # ── model-aware governance setup ───────────────────────────────────
    registry = ModelRegistry()
    profile = registry.get(agent.model)

    # ── resolve tools ──────────────────────────────────────────────────
    if deck is not None:
        active_tools = deck.get_schemas_for_protocol(agent._protocol_name)
        if not active_tools:
            active_tools = None
    else:
        active_tools = agent._build_tools(tools)

    # DEBUG: log tool count being sent to API
    import logging
    _log = logging.getLogger(__name__)
    _tool_names = [t.get("function", t).get("name", "?") for t in (active_tools or [])]
    _log.warning("DEBUG tool_call: sending %d tools to API: %s", len(_tool_names), _tool_names)

    # ── governance before first LLM call ───────────────────────────────
    messages = govern_messages(messages, profile)
    api_msgs = protocol.build_messages(messages)

    temperature = getattr(agent, "temperature", 0.0)
    for _ in range(max_iters):
        response, err_cat = _api_call_with_retry(
            protocol, agent.system_prompt, api_msgs, active_tools,
            agent.model, temperature,
        )
        if response is None:
            # All retries exhausted — return a meaningful error to the user
            _error_msgs = {
                "rate_limited": "API 限流了（429），已重试 3 次仍被节流。请稍等几分钟后重试。",
                "timeout": "API 连接超时，网络波动或服务端响应慢。已重试 3 次未恢复。",
                "server_error": "模型服务暂时不可用（502/503），已重试 3 次。请稍后再试。",
                "connection": "API 连接断开，网络不稳定。已重试 3 次未恢复。",
            }
            return _error_msgs.get(err_cat or "unknown", f"API 调用失败：{err_cat or 'unknown error'}，已重试 3 次未恢复。")

        result = protocol.build_response(response)

        if not result["tool_calls"]:
            return result["text"]

        # ── record assistant turn ───────────────────────────────────
        assistant_msg: dict = {
            "role": "assistant",
            "content": result["text"],
            "tool_calls": result["tool_calls"],
        }
        if result["reasoning"]:
            assistant_msg["reasoning"] = result["reasoning"]
        messages.append(assistant_msg)

        api_msgs.append(protocol.build_assistant_block(
            result["text"], result["reasoning"], result["tool_calls"],
        ))

        # ── execute tools ───────────────────────────────────────────
        for tc in result["tool_calls"]:
            t0 = time.time()
            try:
                tool_result = registry.call(tc["name"], tc["arguments"])
                dt = (time.time() - t0) * 1000
                log_tool_call(tc["name"], tc["arguments"], tool_result, dt, error=False)
            except Exception as e:
                # Log detailed error internally; return generic message to LLM
                # to prevent information leakage via exception strings.
                _err_detail = f"Tool error: {e}"
                dt = (time.time() - t0) * 1000
                log_tool_call(tc["name"], tc["arguments"], _err_detail, dt, error=True)
                tool_result = "Tool execution failed. Please check your request and try again."
            tool_msg = {
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result,
            }
            messages.append(tool_msg)
            api_msgs.append(protocol.build_tool_result_block(
                tc["id"], tool_result,
            ))

        # ── governance before next LLM call ─────────────────────────
        messages = govern_messages(messages, profile)
        api_msgs = protocol.build_messages(messages)

    return "(reached max iterations)"
