"""Message governance — keeps conversation history healthy and within budget.

Used by the Loop *before* every LLM call.  Responsibilities:
  1. Drop orphan tool_results (no matching assistant tool_call).
  2. Backfill missing tool_results (assistant issued tool_call but no result yet).
  3. Compact old messages (microcompact) when history grows long.
  4. Hard-truncate when approaching the model's context-window limit.
  5. Enforce role alternation (merge consecutive same-role, fix trailing assistant).

All strategies are model-aware via ModelProfile.

---
What we bring in (3rd-party):
  None directly — tiktoken / transformers are consumed via agent.models.

What we write ourselves:
  _drop_orphans()              — remove dangling tool results.
  _backfill_missing()          — inject placeholders for incomplete calls.
  _microcompact()              — collapse old read_file / exec results to summaries.
  _hard_trim()                 — discard oldest messages to fit token budget.
  _enforce_role_alternation()  — merge consecutive same-role, fix trailing assistant.
  govern_messages()            — public entrypoint used by the Loop.
"""
from __future__ import annotations

import copy
import logging
from typing import Any, Dict

from agent.models import ModelProfile, TokenCounter, build_counter, estimate_tokens

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

Message = Dict[str, Any]


def _estimate_message_tokens(m: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls if present."""
    text = str(m.get("content", ""))
    tokens = estimate_tokens(text, counter)
    tool_calls = m.get("tool_calls")
    if tool_calls:
        # tool_calls JSON also consumes tokens; approximate by serialising.
        tokens += estimate_tokens(json.dumps(tool_calls, separators=(",", ":")), counter)
    return tokens


# ---------------------------------------------------------------------------
# Token estimation helper (includes tool_calls)
# ---------------------------------------------------------------------------

def _message_token_estimate(m: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls if present."""
    content = str(m.get("content", ""))
    tokens = estimate_tokens(content, counter)
    tool_calls = m.get("tool_calls")
    if tool_calls:
        # Rough estimate: JSON-serialised tool_calls also consume context tokens
        tokens += estimate_tokens(json.dumps(tool_calls), counter)
    return tokens


# ---------------------------------------------------------------------------
# Token estimation helpers
# ---------------------------------------------------------------------------

def _estimate_message_tokens(message: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls if present."""
    content = message.get("content", "")
    tokens = estimate_tokens(str(content) if content is not None else "", counter)
    # tool_calls also consume tokens (function name + JSON arguments)
    for tc in message.get("tool_calls", []):
        fn = tc.get("function", {})
        tokens += estimate_tokens(fn.get("name", ""), counter)
        tokens += estimate_tokens(str(fn.get("arguments", "")), counter)
    return tokens
# ---------------------------------------------------------------------------

def _message_tokens(message: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls payload."""
    tokens = estimate_tokens(str(message.get("content", "")), counter)
    for tc in message.get("tool_calls", []):
        # function name + arguments JSON are both sent to the model
        func = tc.get("function", tc)
        tokens += estimate_tokens(func.get("name", ""), counter)
        tokens += estimate_tokens(str(func.get("arguments", "")), counter)
    return tokens


# ---------------------------------------------------------------------------
# Token estimation helpers
# ---------------------------------------------------------------------------

def _message_tokens(m: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls."""
    tokens = estimate_tokens(str(m.get("content", "")), counter)
    # tool_calls also consume tokens (function name + arguments JSON)
    for tc in m.get("tool_calls", []):
        name = tc.get("function", {}).get("name", "") if "function" in tc else tc.get("name", "")
        args = tc.get("function", {}).get("arguments", "") if "function" in tc else tc.get("arguments", "")
        tokens += estimate_tokens(name, counter)
        tokens += estimate_tokens(str(args), counter)
    return tokens


# ---------------------------------------------------------------------------
# Token estimation helpers
# ---------------------------------------------------------------------------

def _message_tokens(m: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls."""
    text = str(m.get("content", ""))
    tokens = estimate_tokens(text, counter)
    # tool_calls also consume tokens (id, name, arguments JSON)
    if m.get("role") == "assistant" and "tool_calls" in m:
        for tc in m["tool_calls"]:
            tokens += estimate_tokens(tc.get("id", ""), counter)
            tokens += estimate_tokens(tc.get("type", ""), counter)
            fn = tc.get("function", {})
            tokens += estimate_tokens(fn.get("name", ""), counter)
            tokens += estimate_tokens(str(fn.get("arguments", "")), counter)
    return tokens
# ---------------------------------------------------------------------------

def _drop_orphans(messages: list[Message]) -> list[Message]:
    """Remove tool_results whose tool_call_id has no matching assistant tool_call."""
    valid_ids = {
        tc["id"]
        for m in messages
        if m.get("role") == "assistant" and "tool_calls" in m
        for tc in m["tool_calls"]
    }
    cleaned: list[Message] = []
    dropped = 0
    for m in messages:
        if m.get("role") == "tool" and m.get("tool_call_id") not in valid_ids:
            dropped += 1
            continue
        cleaned.append(m)
    if dropped:
        logger.debug("Dropped %d orphan tool_result(s)", dropped)
    return cleaned


# ---------------------------------------------------------------------------
# 2. Backfill missing results
# ---------------------------------------------------------------------------

def _backfill_missing(messages: list[Message]) -> list[Message]:
    """For every assistant tool_call without a matching tool_result, inject an
    error placeholder so the LLM isn't left waiting."""
    result_ids = {
        m.get("tool_call_id")
        for m in messages
        if m.get("role") == "tool"
    }
    out = copy.deepcopy(messages)
    for m in out:
        if m.get("role") != "assistant" or "tool_calls" not in m:
            continue
        for tc in m["tool_calls"]:
            if tc["id"] not in result_ids:
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": "[error: tool result missing — possibly interrupted]",
                        "name": tc.get("name", "unknown"),
                    }
                )
                logger.warning("Backfilled missing result for tool_call %s", tc["id"])
    return out


# ---------------------------------------------------------------------------
# 3. Microcompact — summarise old tool results
# ---------------------------------------------------------------------------

_MICROCOMPACTABLE = {"fs_read_file", "fs_list_dir", "sys_terminal", "web_fetch"}


def _microcompact(
    messages: list[Message],
    age_turns: int,
) -> list[Message]:
    """Replace tool results older than *age_turns* with one-line summaries.

    Only affects tools in _MICROCOMPACTABLE.
    """
    if not messages:
        return messages

    out: list[Message] = []
    # Map tool_call_id → assistant message index (for age calculation)
    call_indices: dict[str, int] = {}
    for idx, m in enumerate(messages):
        if m.get("role") == "assistant" and "tool_calls" in m:
            for tc in m["tool_calls"]:
                call_indices[tc["id"]] = idx

    for m in messages:
        if m.get("role") != "tool":
            out.append(m)
            continue

        tc_id = m.get("tool_call_id")
        if tc_id not in call_indices:
            out.append(m)
            continue

        age = len(messages) - call_indices[tc_id]
        if age <= age_turns:
            out.append(m)
            continue

        tool_name = m.get("name", "unknown")
        if tool_name not in _MICROCOMPACTABLE:
            out.append(m)
            continue

        content = str(m.get("content", ""))
        summary = f"[{tool_name} result: {len(content)} chars — truncated by microcompact]"
        out.append({**m, "content": summary})
        logger.debug("Microcompact tool_result %s (age=%d)", tc_id, age)

    return out


def _message_tokens(m: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls content."""
def _estimate_message_tokens(m: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls content."""
    total = estimate_tokens(str(m.get("content", "")), counter)
    for tc in m.get("tool_calls", []):
        fn = tc.get("function", {})
        total += estimate_tokens(str(fn.get("name", "")), counter)
        total += estimate_tokens(str(fn.get("arguments", "")), counter)
    return total
    for tc in m.get("tool_calls", []):
        func = tc.get("function", tc)
        total += estimate_tokens(func.get("name", ""), counter)
        total += estimate_tokens(str(func.get("arguments", "")), counter)
    return total


# ---------------------------------------------------------------------------
# Token estimation helpers (include tool_calls in the count)
# ---------------------------------------------------------------------------

def _message_tokens(m: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls if present."""
    text = str(m.get("content", ""))
    tool_calls = m.get("tool_calls")
    if tool_calls:
        for tc in tool_calls:
            text += tc.get("function", {}).get("name", "")
            text += tc.get("function", {}).get("arguments", "")
    return estimate_tokens(text, counter)


# ---------------------------------------------------------------------------
# Token estimation helpers
# ---------------------------------------------------------------------------

def _estimate_message_tokens(message: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls."""
    total = estimate_tokens(str(message.get("content", "")), counter)
    for tc in message.get("tool_calls", []):
        # tool_call tokens: name + arguments JSON
        func = tc.get("function", tc)
        total += estimate_tokens(func.get("name", ""), counter)
        total += estimate_tokens(json.dumps(func.get("arguments", "")), counter)
    return total

def _estimate_message_tokens(m: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls if present."""
    text = str(m.get("content", ""))
    tool_calls = m.get("tool_calls")
    if tool_calls:
        # ---------------------------------------------------------------------------
        # 4. Hard trim — discard oldest messages to fit budget
        # ---------------------------------------------------------------------------

        def _message_tokens(m: Message, counter: TokenCounter) -> int:
            """Estimate tokens for a single message, including tool_calls."""
            total = estimate_tokens(str(m.get("content", "")), counter)
            for tc in m.get("tool_calls", []):
                total += estimate_tokens(tc.get("name", ""), counter)
                total += estimate_tokens(str(tc.get("arguments", "")), counter)
            return total


        def _message_tokens(m: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls."""
    content = str(m.get("content", ""))
    total = estimate_tokens(content, counter)
    # ---------------------------------------------------------------------------
    # 4. Hard trim — discard oldest messages to fit budget
    # ---------------------------------------------------------------------------

    def _message_tokens(m: Message, counter: TokenCounter) -> int:
        """Estimate tokens for a single message, including tool_calls if present."""
        content = str(m.get("content", ""))
        total = estimate_tokens(content, counter)
        tool_calls = m.get("tool_calls")
        if tool_calls:
            # Approximate: JSON-serialised tool_calls also consume context tokens.
            total += estimate_tokens(json.dumps(tool_calls, ensure_ascii=False), counter)
        return total


    def _message_tokens(m: Message, counter: TokenCounter) -> int:
    """Estimate tokens for a single message, including tool_calls."""
    tokens = estimate_tokens(str(m.get("content", "")), counter)
    tcs = m.get("tool_calls")
    if tcs:
        tokens += estimate_tokens(json.dumps(tcs), counter)
    return tokens
        messages: list[Message],
        profile: ModelProfile,
        counter: TokenCounter | None = None,
    ) -> list[Message]:
        """Remove oldest messages until total token count <= usable_context.

        Preserves the system message (role="system") if present.
        Never breaks an assistant/tool pair: if an assistant message with
        tool_calls is kept, all matching tool_results are kept too.
        """
        if counter is None:
            counter = build_counter(profile.encoding_name)

        def _msg_tokens(m: Message) -> int:
            """Estimate tokens for a single message, including tool_calls."""
            total = estimate_tokens(str(m.get("content", "")), counter)
            # tool_calls carry tokens too (OpenAI charges for function name + arguments)
            for tc in m.get("tool_calls", []):
                total += estimate_tokens(tc.get("function", {}).get("name", ""), counter)
                total += estimate_tokens(str(tc.get("function", {}).get("arguments", "")), counter)
            return total

        usable = profile.usable_context

        def _msg_tokens(m: Message) -> int:
            """Estimate tokens for a message, including tool_calls if present."""
            tokens = estimate_tokens(str(m.get("content", "")), counter)
            # Tool calls consume tokens too (function name + arguments JSON).
            # We serialise the whole tool_calls list for a rough estimate.
            if m.get("role") == "assistant" and "tool_calls" in m:
                try:
                    tool_json = json.dumps(m["tool_calls"], ensure_ascii=False)
                    tokens += estimate_tokens(tool_json, counter)
                except (TypeError, ValueError):
                    pass
            return tokens
        usable = profile.usable_context
        total = sum(
            _estimate_message_tokens(m, counter) for m in messages
        )

        if total <= usable:
            return messages

        out = copy.deepcopy(messages)
        system_msg: Message | None = None
        if out and out[0].get("role") == "system":
            system_msg = out.pop(0)

        while out:
            # Estimate current total
            current = sum(
                _estimate_message_tokens(m, counter) for m in out
            )
            if system_msg:
                current += _estimate_message_tokens(system_msg, counter)
            if current <= usable:
                break
                drop_ids = {tc["id"] for tc in oldest["tool_calls"]}
                out = [m for m in out if not (m.get("role") == "tool" and m.get("tool_call_id") in drop_ids)]
            elif oldest.get("role") == "tool":
                # If we drop a tool_result, mark its call as unprotected
                pass  # the assistant message will still exist; LLM may retry

        if system_msg:
            out.insert(0, system_msg)

        logger.info(
            "Hard-trimmed messages: %d → %d (token budget %d)",
            len(messages),
            len(out),
            usable,
        )
        return out


# ---------------------------------------------------------------------------
# 5. Role alternation enforcement
# ---------------------------------------------------------------------------

_SYNTHETIC_USER_CONTENT = "[system] Continuing conversation..."


def _enforce_role_alternation(messages: list[Message]) -> list[Message]:
    """Merge consecutive same-role messages and fix trailing assistant messages.

    Some providers (OpenAI-compat, vLLM, Ollama, etc.) reject requests where:
      - two consecutive non-system messages share the same role, or
      - the last message is a bare assistant (no tool_calls).

    This function sanitises the message list to keep API calls safe.
    """
    if not messages:
        return messages

    merged: list[Message] = []
    for msg in messages:
        role = msg.get("role")
        if (
            merged
            and role != "system"
            and role not in ("tool",)
            and merged[-1].get("role") == role
            and role in ("user", "assistant")
        ):
            prev = merged[-1]
            if role == "assistant":
                prev_has_tools = bool(prev.get("tool_calls"))
                curr_has_tools = bool(msg.get("tool_calls"))
                if curr_has_tools:
                    # Current message has tool_calls — it takes precedence
                    merged[-1] = dict(msg)
                    continue
                if prev_has_tools:
                    # Previous message has tool_calls — keep it, skip current
                    continue
            # Merge content strings
            prev_content = prev.get("content") or ""
            curr_content = msg.get("content") or ""
            if isinstance(prev_content, str) and isinstance(curr_content, str):
                prev["content"] = (prev_content + "\n\n" + curr_content).strip()
            else:
                merged[-1] = dict(msg)
        else:
            merged.append(dict(msg))

    # Drop trailing assistant messages that have no tool_calls
    last_popped: Message | None = None
    while merged and merged[-1].get("role") == "assistant":
        last_popped = merged.pop()

    # If removing trailing assistants left only system messages, recover
    # the last popped assistant as a user message so the request stays valid.
    if (
        merged
        and last_popped is not None
        and not any(m.get("role") in ("user", "tool") for m in merged)
    ):
        recovered = dict(last_popped)
        recovered["role"] = "user"
        merged.append(recovered)

    # Safety net: first non-system message must not be a bare assistant
    for i, msg in enumerate(merged):
        if msg.get("role") != "system":
            if msg.get("role") == "assistant" and not msg.get("tool_calls"):
                merged.insert(i, {"role": "user", "content": _SYNTHETIC_USER_CONTENT})
            break

    return merged


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def govern_messages(
    messages: list[Message],
    profile: ModelProfile,
    counter: TokenCounter | None = None,
) -> list[Message]:
    """Apply full governance pipeline to *messages*.

    Order matters:
      1. Drop orphans (clean up invalid state)
      2. Backfill missing (complete partial state)
      3. Microcompact old results (reduce bloat)
      4. Hard trim to token budget (fit context window)
      5. Drop orphans again (hard_trim may have broken pairs)
      6. Backfill missing again
      7. Enforce role alternation (final safety net)
    """
    out = _drop_orphans(messages)
    out = _backfill_missing(out)

    age = int(profile.governance.get("microcompact_age_turns", 10))
    out = _microcompact(out, age)

    out = _hard_trim(out, profile, counter)

    # Hard trim may have dropped assistant/tool pairs; re-normalise.
    out = _drop_orphans(out)
    out = _backfill_missing(out)

    out = _enforce_role_alternation(out)
    return out
