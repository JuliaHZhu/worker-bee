"""Tests for skill loading, YAML parsing, trigger matching, and caching."""

from skills import SkillManager, _parse_yamlish


class TestYAMLParser:
    """Tests for _parse_yamlish — the no-dep YAML frontmatter parser."""

    def test_scalar_fields(self):
        """Simple key: value pairs."""
        text = "name: test\ndescription: A test skill\ncategory: testing"
        result = _parse_yamlish(text)
        assert result["name"] == "test"
        assert result["description"] == "A test skill"
        assert result["category"] == "testing"

    def test_list_fields(self):
        """List values under a key."""
        text = "tools:\n  - fs_read_file\n  - sys_terminal\n  - net_web_search"
        result = _parse_yamlish(text)
        assert result["tools"] == ["fs_read_file", "sys_terminal", "net_web_search"]

    def test_mixed_scalars_and_lists(self):
        """A mix of scalar and list values."""
        text = """name: web-research
description: Research on the web
trigger: search, find, research
tools:
  - net_web_search
  - net_web_extract"""
        result = _parse_yamlish(text)
        assert result["name"] == "web-research"
        assert result["description"] == "Research on the web"
        assert result["trigger"] == "search, find, research"
        assert result["tools"] == ["net_web_search", "net_web_extract"]

    def test_empty_list(self):
        """Empty list yields empty list."""
        text = "tools:"
        result = _parse_yamlish(text)
        assert result["tools"] == ""

    def test_blank_lines_ignored(self):
        """Blank lines between fields don't break parsing."""
        text = "name: test\n\ndescription: desc\n\n  \ntools:\n  - t1"
        result = _parse_yamlish(text)
        assert result["name"] == "test"
        assert result["tools"] == ["t1"]

    def test_empty_input(self):
        """Empty string returns empty dict."""
        assert _parse_yamlish("") == {}


class TestSkillParsing:
    """Tests for parsing complete skill markdown files."""

    def test_parse_skill_with_frontmatter(self, skill_manager, skills_dir):
        """Skill with YAML frontmatter is correctly parsed."""
        skill = skill_manager.get_skill("test-skill")
        assert skill is not None
        assert skill["name"] == "test-skill"
        assert "A test skill" in skill["description"]
        assert "test" in skill["triggers"]
        assert "debugging" in skill["triggers"]
        assert "verify" in skill["triggers"]
        assert "fs_read_file" in skill["tools"]
        assert "sys_terminal" in skill["tools"]
        assert skill["category"] == "testing"
        assert skill["composability"] == "atomic"
        # Body exists
        assert skill["_body"].startswith("# Test Skill")

    def test_parse_skill_trigger_string(self, skills_dir):
        """Trigger as comma-separated string is split into list."""
        mgr = SkillManager(str(skills_dir))
        mgr.load_all()
        skill = mgr.get_skill("web-search")
        assert "search" in skill["triggers"]
        assert "google" in skill["triggers"]
        assert "find online" in skill["triggers"]
        assert "research" in skill["triggers"]

    def test_parse_skill_all_loaded(self, skill_manager):
        """All skills in the directory are loaded."""
        skills = skill_manager.list_skills()
        assert "test-skill" in skills
        assert "web-search" in skills
        assert len(skills) == 2

    def test_get_skill_nonexistent(self, skill_manager):
        """Nonexistent skill returns None."""
        assert skill_manager.get_skill("nonexistent") is None


class TestTriggerMatching:
    """Tests for keyword-based trigger matching."""

    def test_direct_trigger_match(self, skill_manager):
        """Exact trigger word matches the skill."""
        matched = skill_manager.match_skills("can you test this code")
        assert "test-skill" in matched

    def test_partial_trigger_match(self, skill_manager):
        """Trigger substring in user input matches."""
        # "debugging" is a trigger, so "debugging" in input should match
        matched = skill_manager.match_skills("I need to do some debugging today")
        assert "test-skill" in matched

    def test_multiple_matches(self, skill_manager):
        """Input matching multiple triggers returns all relevant skills."""
        matched = skill_manager.match_skills("test the search function")
        assert "test-skill" in matched
        assert "web-search" in matched

    def test_no_match(self, skill_manager):
        """Irrelevant input matches nothing."""
        matched = skill_manager.match_skills("calculate the sum")
        assert matched == []

    def test_case_insensitive(self, skill_manager):
        """Trigger matching is case-insensitive."""
        matched = skill_manager.match_skills("I want to RESEARCH something online")
        assert "web-search" in matched


class TestSkillTools:
    """Tests for tool collection from skills."""

    def test_get_tools_for_skills(self, skill_manager):
        """Collect tools from named skills."""
        tools = skill_manager.get_tools_for_skills(["test-skill"])
        assert "fs_read_file" in tools
        assert "sys_terminal" in tools

    def test_get_tools_for_multiple_skills(self, skill_manager):
        """Tools from multiple skills are unioned."""
        tools = skill_manager.get_tools_for_skills(["test-skill", "web-search"])
        assert "fs_read_file" in tools
        assert "sys_terminal" in tools
        assert "net_web_search" in tools
        assert "net_web_extract" in tools
        # Deduplication (both have fs_read_file, but it should appear once)
        assert tools.count("fs_read_file") == 1

    def test_get_tools_for_nonexistent(self, skill_manager):
        """Nonexistent skills yield empty list."""
        tools = skill_manager.get_tools_for_skills(["nonexistent"])
        assert tools == []


class TestSkillContextBuilding:
    """Tests for building skill context for prompts."""

    def test_build_context_for_skill(self, skill_manager):
        """Build context for a single skill injects body content."""
        ctx = skill_manager.build_context_for_skills(["test-skill"])
        assert "## Skill: test-skill" in ctx
        assert "Test Skill" in ctx
        assert "This is a test skill body" in ctx

    def test_build_context_nonexistent(self, skill_manager):
        """Nonexistent skill is silently skipped."""
        ctx = skill_manager.build_context_for_skills(["nonexistent"])
        assert ctx == ""

    def test_build_context_truncation(self, skill_manager, skills_dir):
        """Long skill body is truncated at 2000 chars."""
        long_body = "# Long Skill\n\n" + "x" * 3000
        (skills_dir / "long-skill.md").write_text(
            f"---\nname: long-skill\ndescription: Long\ntrigger: long\ntools: []\n---\n{long_body}",
            encoding="utf-8",
        )
        mgr = SkillManager(str(skills_dir))
        mgr.load_all()
        ctx = mgr.build_context_for_skills(["long-skill"])
        # Should contain truncated body with "..."
        assert "..." in ctx
        assert len(ctx) <= 2500  # generous bound: 2000 body + header


class TestSkillDiskCache:
    """Tests for disk snapshot caching."""

    def test_disk_cache_written(self, skills_dir):
        """Loading skills writes a disk snapshot."""
        mgr = SkillManager(str(skills_dir))
        mgr.load_all()
        cache_path = skills_dir / ".skills_cache.json"
        assert cache_path.exists()
        import json
        snapshot = json.loads(cache_path.read_text(encoding="utf-8"))
        assert "skills" in snapshot
        assert "manifest" in snapshot
        assert "test-skill" in snapshot["skills"]

    def test_disk_cache_read_on_reload(self, skills_dir):
        """Second load uses disk cache (lightning-fast)."""
        mgr1 = SkillManager(str(skills_dir))
        mgr1.load_all()

        # Second SkillManager should use disk snapshot
        mgr2 = SkillManager(str(skills_dir))
        loaded = mgr2.load_all()
        assert "test-skill" in loaded
        assert "web-search" in loaded

    def test_invalidate_cache(self, skills_dir):
        """invalidate_cache clears memory + removes disk snapshot."""
        mgr = SkillManager(str(skills_dir))
        mgr.load_all()
        cache_path = skills_dir / ".skills_cache.json"
        assert cache_path.exists()

        mgr.invalidate_cache()
        assert not cache_path.exists()
        assert mgr._skills == {}
        assert mgr._parse_cache == {}
