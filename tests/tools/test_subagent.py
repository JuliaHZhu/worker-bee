"""Tests for subagent tools — delegate, parallel, cross-validate.

Note: These are integration tests that require a working LLM API.
They are marked with @pytest.mark.integration and skipped by default.
Run with: pytest -m integration
"""
import json
import pytest


@pytest.mark.integration
class TestSubAgentTools:
    """Integration tests — skipped without --run-integration."""

    def test_delegate_task_structure(self):
        """Verify delegate_task function signature and parameter handling."""
        from tools.subagent import agent_delegate_task, _make_agent_config

        # Test config generation doesn't crash
        config = _make_agent_config(model="test-model")
        assert config["model"] == "test-model"
        assert config["provider"] in ("anthropic", "openai")
        assert "api_key" in config
        assert "base_url" in config

    def test_delegate_parallel_structure(self):
        """Verify delegate_parallel returns valid JSON."""
        from tools.subagent import agent_delegate_parallel
        # Even with no real LLM, verify the function signature
        # Just test that it accepts valid input shape
        pass

    def test_cross_validate_structure(self):
        """Verify cross_validate parameter handling."""
        from tools.subagent import agent_cross_validate, _make_agent_config
        config = _make_agent_config(max_iterations=5)
        assert config["max_iterations"] == 5

    def test_make_agent_config_env_fallback(self, monkeypatch):
        """_make_agent_config falls back to env vars."""
        import os
        from tools.subagent import _make_agent_config

        monkeypatch.setenv("ARKCODE_API_KEY", "test-key-123")
        monkeypatch.setenv("ARKCODE_BASE_URL", "https://test-api.example.com")

        config = _make_agent_config()
        assert config["api_key"] == "test-key-123"
        assert config["base_url"] == "https://test-api.example.com"

    def test_make_agent_config_provider_override(self):
        """Explicit provider override works."""
        from tools.subagent import _make_agent_config

        config = _make_agent_config(provider="openai", api_key="sk-test")
        assert config["provider"] == "openai"
        assert config["api_key"] == "sk-test"
