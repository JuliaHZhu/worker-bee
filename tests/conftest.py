"""Shared test fixtures for worker-bee."""
import os
import tempfile
import pytest
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory, cleaned up after test."""
    with tempfile.TemporaryDirectory(prefix="worker-bee-test-") as d:
        yield Path(d)


@pytest.fixture
def temp_workspace(temp_dir):
    """Temp dir + set WORKER_BEE_WORKSPACE env var."""
    old = os.environ.get("WORKER_BEE_WORKSPACE")
    os.environ["WORKER_BEE_WORKSPACE"] = str(temp_dir)
    yield temp_dir
    if old is None:
        del os.environ["WORKER_BEE_WORKSPACE"]
    else:
        os.environ["WORKER_BEE_WORKSPACE"] = old


@pytest.fixture
def fresh_registry():
    """Return a brand-new ToolRegistry instance."""
    from worker_bee.registry import ToolRegistry
    return ToolRegistry()


@pytest.fixture
def sample_skill_md():
    """Return valid YAML frontmatter content for a skill."""
    return """---
name: test-skill
description: A test skill for unit tests
trigger: test, debugging, verify
tools:
  - fs_read_file
  - sys_terminal
category: testing
composability: atomic
---

# Test Skill

This is a test skill body.
"""


@pytest.fixture
def skills_dir(temp_dir, sample_skill_md):
    """Create a temp skills directory with sample skill files."""
    skills_path = temp_dir / "skills"
    skills_path.mkdir()
    (skills_path / "test-skill.md").write_text(sample_skill_md, encoding="utf-8")

    (skills_path / "web-search.md").write_text("""---
name: web-search
description: Search the web
trigger: search, google, find online, research
tools:
  - net_web_search
  - net_web_extract
category: research
---

# Web Search Skill
Use net_web_search first, then net_web_extract for details.
""", encoding="utf-8")

    return skills_path


@pytest.fixture
def skill_manager(skills_dir):
    """Return a SkillManager pointing at the temp skills dir."""
    from worker_bee.skills import SkillManager
    mgr = SkillManager(str(skills_dir))
    mgr.load_all()
    return mgr


@pytest.fixture
def mock_config():
    """Return a minimal config dict."""
    return {
        "model": "test-model",
        "provider": "anthropic",
        "api_key": "test-key",
        "base_url": "https://api.test.example.com",
        "max_iterations": 5,
        "system_prompt": "You are a test assistant.",
        "tools": ["fs_read_file", "sys_terminal"],
    }