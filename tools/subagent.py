"""Subagent tool — delegate tasks to a child agent instance."""
import os
from registry import registry


def agent_delegate_task(
    goal: str,
    context: str = "",
    tools: list = None,
    model: str = None,
    max_iterations: int = 10
) -> str:
    """Spawn a child agent to work on an independent subtask.

    The child agent gets a fresh context (no access to parent conversation).
    It can use a subset of tools and returns a final summary.
    """
    from agent import AIAgent

    config = {
        "model": model or os.environ.get("LITE_MODEL", "kimi-k2.6"),
        "provider": os.environ.get("LITE_PROVIDER", "anthropic"),
        "api_key": os.environ.get("ARKCODE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", ""),
        "base_url": os.environ.get("ARKCODE_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding"),
        "max_iterations": max_iterations,
        "system_prompt": (
            "You are a focused sub-agent working on a specific subtask. "
            "Work independently and return a concise final answer."
        ),
        "tools": tools or []
    }

    agent = AIAgent(config)
    messages = []
    if context:
        messages.append({"role": "user", "content": f"Context: {context}\n\nTask: {goal}"})
    else:
        messages.append({"role": "user", "content": goal})

    return agent.run(messages)


registry.register(
    name="agent_delegate_task",
    description=(
        "Delegate an independent subtask to a child agent. "
        "Use for parallelizable work or when the main task can be broken into smaller pieces. "
        "The sub-agent has a fresh context and does not see the parent conversation."
    ),
    parameters={
        "properties": {
            "goal": {"type": "string", "description": "Clear description of what the sub-agent should accomplish"},
            "context": {"type": "string", "description": "Additional context the sub-agent needs", "default": ""},
            "tools": {"type": "array", "items": {"type": "string"}, "description": "List of tool names the sub-agent may use", "default": []},
            "model": {"type": "string", "description": "Override model for this sub-agent", "default": ""},
            "max_iterations": {"type": "integer", "description": "Max tool-use iterations", "default": 10}
        },
        "required": ["goal"]
    },
    handler=agent_delegate_task,
    tags=["agent", "delegate", "subtask"],
    category="agent"
)
