"""Send message — Feishu and Discord webhook only.

No other platforms. No gateway. Just simple HTTP POST.
"""
import json
import os
import urllib.request
from registry import registry


def _send_feishu(content: str) -> str:
    """Send text message via Feishu bot webhook."""
    url = os.environ.get("FEISHU_WEBHOOK_URL", "")
    if not url:
        return json.dumps({"error": "FEISHU_WEBHOOK_URL not set"}, ensure_ascii=False)
    payload = {
        "msg_type": "text",
        "content": {"text": content}
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return json.dumps({"status": resp.status, "body": body}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _send_discord(content: str) -> str:
    """Send text message via Discord webhook."""
    url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url:
        return json.dumps({"error": "DISCORD_WEBHOOK_URL not set"}, ensure_ascii=False)
    payload = {"content": content}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8") or "(empty)"
            return json.dumps({"status": resp.status, "body": body}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def send_message(content: str, platform: str = None) -> str:
    """Send a message to the configured platform (feishu or discord).

    The platform is auto-detected from env vars:
      - FEISHU_WEBHOOK_URL → sends to Feishu
      - DISCORD_WEBHOOK_URL → sends to Discord

    Args:
        content: The message text to send.
        platform: Optional override ("feishu" or "discord").
                  If None, auto-detect from env.
    """
    if platform is None:
        if os.environ.get("FEISHU_WEBHOOK_URL"):
            platform = "feishu"
        elif os.environ.get("DISCORD_WEBHOOK_URL"):
            platform = "discord"
        else:
            return json.dumps(
                {"error": "No webhook configured. Set FEISHU_WEBHOOK_URL or DISCORD_WEBHOOK_URL."},
                ensure_ascii=False
            )

    if platform == "feishu":
        return _send_feishu(content)
    elif platform == "discord":
        return _send_discord(content)
    else:
        return json.dumps({"error": f"Unsupported platform: {platform}"}, ensure_ascii=False)


registry.register(
    name="send_message",
    description=(
        "Send a text message to the configured messaging platform. "
        "Supports Feishu (Lark) and Discord via webhook. "
        "The platform is auto-detected from environment variables. "
        "When FEISHU_WEBHOOK_URL is set, messages go to Feishu. "
        "When DISCORD_WEBHOOK_URL is set, messages go to Discord."
    ),
    parameters={
        "properties": {
            "content": {
                "type": "string",
                "description": "The message text to send. Keep it concise."
            },
            "platform": {
                "type": "string",
                "description": "Optional override: 'feishu' or 'discord'. If omitted, auto-detect from env.",
                "enum": ["feishu", "discord"]
            }
        },
        "required": ["content"]
    },
    handler=send_message,
    tags=["messaging", "infra"],
    category="infra"
)
