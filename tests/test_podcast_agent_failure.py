"""#1 — podcast_agent CLI handles API failures gracefully (non-zero exit + readable msg)."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import tools.podcast_agent as pa


class TestPodcastAgentMainFailure:
    def test_main_exits_on_api_failure(self, capsys):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "source.md"
            src.write_text("# Hello\n\nWorld", encoding="utf-8")
            # Minimal config so ensure_config doesn't fail on key
            with patch.object(pa, "ensure_config", return_value={
                "provider": "openai",
                "openai_api_key": "fake",
                "model": "gpt-4o",
            }):
                with patch.object(pa, "generate_script", side_effect=RuntimeError("Rate limit")):
                    with patch.object(sys, "argv", ["podcast_agent.py", "--source", str(src)]):
                        with pytest.raises(SystemExit) as exc:
                            pa.main()
                        assert exc.value.code != 0

    def test_tool_returns_error_string_on_api_failure(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "source.md"
            src.write_text("# Hello", encoding="utf-8")
            with patch.object(pa, "ensure_config", return_value={
                "provider": "openai",
                "openai_api_key": "fake",
                "model": "gpt-4o",
            }):
                with patch.object(pa, "generate_script", side_effect=RuntimeError("Rate limit")):
                    result = pa.podcast_agent(str(src))
                    assert "Error:" in result
                    assert "Rate limit" in result
