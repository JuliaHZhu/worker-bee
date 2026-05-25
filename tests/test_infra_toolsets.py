"""Tests for InfraToolSet — platform detection and tool filtering."""
import os
import pytest

from worker_bee.infra_toolsets import InfraToolSet


@pytest.fixture
def clean_infra():
    """A fresh InfraToolSet with cleared env."""
    # Save and clear env vars
    saved_feishu = os.environ.pop("FEISHU_WEBHOOK_URL", None)
    saved_discord = os.environ.pop("DISCORD_WEBHOOK_URL", None)

    infra = InfraToolSet()
    yield infra

    # Restore env
    if saved_feishu:
        os.environ["FEISHU_WEBHOOK_URL"] = saved_feishu
    if saved_discord:
        os.environ["DISCORD_WEBHOOK_URL"] = saved_discord


class TestPlatformDetection:
    """Platform auto-detection from environment variables."""

    def test_defaults_to_linux(self, clean_infra):
        """No webhook env vars → linux platform."""
        assert clean_infra.detect_platform() == "linux"

    def test_detects_feishu(self, clean_infra):
        """FEISHU_WEBHOOK_URL → feishu platform."""
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hook.example.com/feishu"
        clean_infra.invalidate()
        assert clean_infra.detect_platform() == "feishu"

    def test_detects_discord(self, clean_infra):
        """DISCORD_WEBHOOK_URL → discord platform."""
        os.environ["DISCORD_WEBHOOK_URL"] = "https://hook.example.com/discord"
        clean_infra.invalidate()
        assert clean_infra.detect_platform() == "discord"

    def test_feishu_priority_over_discord(self, clean_infra):
        """If both set, feishu wins."""
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hook.example.com/feishu"
        os.environ["DISCORD_WEBHOOK_URL"] = "https://hook.example.com/discord"
        clean_infra.invalidate()
        assert clean_infra.detect_platform() == "feishu"

    def test_platform_property(self, clean_infra):
        """platform property returns the detected platform."""
        assert clean_infra.platform == "linux"


class TestToolAvailability:
    """Tool availability per platform."""

    def test_linux_all_available(self, clean_infra):
        """Linux returns empty list (meaning no filter)."""
        assert clean_infra.get_available_tools() == []

    def test_feishu_send_message_available(self, clean_infra):
        """Feishu platform only has send_message."""
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hook.example.com"
        clean_infra.invalidate()
        available = clean_infra.get_available_tools()
        assert "send_message" in available

    def test_discord_send_message_available(self, clean_infra):
        """Discord platform only has send_message."""
        os.environ["DISCORD_WEBHOOK_URL"] = "https://hook.example.com"
        clean_infra.invalidate()
        available = clean_infra.get_available_tools()
        assert "send_message" in available

    def test_is_tool_available(self, clean_infra):
        """is_tool_available checks platform-specific availability."""
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hook.example.com"
        clean_infra.invalidate()
        assert clean_infra.is_tool_available("send_message")
        assert not clean_infra.is_tool_available("fs_read_file")


class TestToolFiltering:
    """filter_tools behavior."""

    def test_linux_no_filter(self, clean_infra):
        """Linux platform passes through all tools unchanged."""
        tools = ["fs_read_file", "sys_terminal", "net_web_search", "send_message"]
        filtered = clean_infra.filter_tools(tools)
        assert filtered == tools

    def test_feishu_filters_to_send_message(self, clean_infra):
        """Feishu only keeps send_message."""
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hook.example.com"
        clean_infra.invalidate()
        tools = ["fs_read_file", "sys_terminal", "send_message", "net_web_search"]
        filtered = clean_infra.filter_tools(tools)
        assert filtered == ["send_message"]

    def test_filter_empty_list(self, clean_infra):
        """Empty tool list stays empty."""
        assert clean_infra.filter_tools([]) == []


class TestCaching:
    """Cache invalidation behavior."""

    def test_platform_cached(self, clean_infra):
        """Platform detection is cached after first call."""
        first = clean_infra.detect_platform()
        # Change env but don't invalidate
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hook.example.com"
        second = clean_infra.detect_platform()
        assert second == first  # Still cached as linux

    def test_invalidate_clears_cache(self, clean_infra):
        """invalidate clears the cached platform."""
        first = clean_infra.detect_platform()
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hook.example.com"
        clean_infra.invalidate()
        second = clean_infra.detect_platform()
        assert second != first
        assert second == "feishu"

    def test_available_tools_cached(self, clean_infra):
        """Available tools are cached."""
        clean_infra.get_available_tools()
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hook.example.com"
        # Without invalidate, still cached
        assert clean_infra.get_available_tools() == []
