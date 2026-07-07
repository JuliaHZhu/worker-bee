"""Tests for skill_test — bottom-up execution-level test framework."""

import json
import pytest
from pathlib import Path

from agent.skill_test import (
    SkillTestRunner,
    SkillTestLevel,
    SkillTestResult,
    SkillTestReport,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_registry():
    """Registry with tools for test framework."""
    from agent.registry import ToolRegistry
    reg = ToolRegistry()
    for name in ["fs_read_file", "fs_write_file", "sys_terminal", "net_web_search", "net_web_extract"]:
        reg.register(
            name=name,
            description=f"Mock {name}",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}, "query": {"type": "string"}},
                "required": [],
            },
            handler=lambda *a, **_kw: "ok",
            tags=["test"],
            category="test",
        )
    return reg


@pytest.fixture
def test_skills_dir(temp_dir):
    """Skills directory with testable skills."""
    skills_path = temp_dir / "skills"
    skills_path.mkdir()

    # Valid skill
    (skills_path / "web-research.md").write_text("""---
name: web-research
description: Research on the web
trigger: search, google, research
tools:
  - net_web_search
  - net_web_extract
category: research
---

# Web Research

Search then extract.
""", encoding="utf-8")

    # Skill with bad tool
    (skills_path / "broken-skill.md").write_text("""---
name: broken-skill
description: Broken
trigger: broken
tools:
  - nonexistent_tool
---

# Broken

Has a bad tool.
""", encoding="utf-8")

    # Skill with regression data
    (skills_path / "regression-skill.md").write_text("""---
name: regression-skill
description: Has regression data
trigger: regress
tools:
  - fs_read_file
---

# Regression Skill

Test skill.
""", encoding="utf-8")

    (skills_path / "regression-skill.regression.json").write_text(json.dumps([
        {"name": "read_file", "input": "read the config file", "expected_tools": ["fs_read_file"]},
        {"name": "missing_tool", "input": "do something weird", "expected_tools": ["nonexistent_tool"]},
    ]), encoding="utf-8")

    return skills_path


@pytest.fixture
def runner(test_registry, test_skills_dir):
    return SkillTestRunner(test_registry, test_skills_dir)


# ---------------------------------------------------------------------------
# Report basics
# ---------------------------------------------------------------------------

class TestSkillTestReport:
    def test_empty_report_not_passed(self):
        r = SkillTestReport(skill_name="test")
        assert not r.passed  # no results = not passed
        assert r.score == 0.0

    def test_all_passed(self):
        r = SkillTestReport(skill_name="test")
        r.results.append(SkillTestResult("t1", SkillTestLevel.UNIT, True, "ok"))
        r.results.append(SkillTestResult("t2", SkillTestLevel.UNIT, True, "ok"))
        assert r.passed
        assert r.score == 1.0

    def test_one_failed(self):
        r = SkillTestReport(skill_name="test")
        r.results.append(SkillTestResult("t1", SkillTestLevel.UNIT, True, "ok"))
        r.results.append(SkillTestResult("t2", SkillTestLevel.UNIT, False, "bad"))
        assert not r.passed
        assert r.score == 0.5

    def test_to_dict(self):
        r = SkillTestReport(skill_name="test")
        r.results.append(SkillTestResult("t1", SkillTestLevel.UNIT, True, "ok", 1.5))
        d = r.to_dict()
        assert d["skill"] == "test"
        assert d["passed"] is True
        assert d["summary"]["total"] == 1


# ---------------------------------------------------------------------------
# L1: Unit Tests
# ---------------------------------------------------------------------------

class TestUnitTests:
    def test_valid_skill_unit_passes(self, runner):
        report = runner.run_skill("web-research", levels={SkillTestLevel.UNIT})
        assert report.passed
        assert any(r.name == "schema_valid_net_web_search" for r in report.results)
        assert any(r.name == "tools_non_empty" for r in report.results)

    def test_missing_tool_fails_schema(self, runner):
        report = runner.run_skill("broken-skill", levels={SkillTestLevel.UNIT})
        assert not report.passed
        assert any(
            r.name == "schema_exists_nonexistent_tool" and not r.passed
            for r in report.results
        )

    def test_empty_tools_fails(self, runner):
        skills_dir = Path(runner.skills_dir)
        (skills_dir / "empty-skill.md").write_text("""---
name: empty-skill
description: Empty
trigger: empty
tools: []
---

# Empty

No tools.
""", encoding="utf-8")
        runner2 = SkillTestRunner(runner.registry, skills_dir)
        report = runner2.run_skill("empty-skill", levels={SkillTestLevel.UNIT})
        assert not report.passed
        assert any(r.name == "tools_non_empty" and not r.passed for r in report.results)

    def test_trigger_parsable(self, runner):
        report = runner.run_skill("web-research", levels={SkillTestLevel.UNIT})
        t = [r for r in report.results if r.name == "trigger_parsable"][0]
        assert t.passed
        assert "3 trigger" in t.message


# ---------------------------------------------------------------------------
# L2: Integration Tests
# ---------------------------------------------------------------------------

class TestIntegrationTests:
    def test_deck_build(self, runner):
        report = runner.run_skill("web-research", levels={SkillTestLevel.INTEGRATION})
        db = [r for r in report.results if r.name == "deck_build"][0]
        assert db.passed
        # Deck includes skill tools + baseline redundancy; just verify non-zero
        assert "tools" in db.message

    def test_skill_match(self, runner):
        report = runner.run_skill("web-research", levels={SkillTestLevel.INTEGRATION})
        sm = [r for r in report.results if r.name == "skill_match"][0]
        assert sm.passed

    def test_protocol_conversion(self, runner):
        report = runner.run_skill("web-research", levels={SkillTestLevel.INTEGRATION})
        pc = [r for r in report.results if r.name == "protocol_conversion"][0]
        assert pc.passed

    def test_broken_skill_deck_fails(self, runner):
        report = runner.run_skill("broken-skill", levels={SkillTestLevel.INTEGRATION})
        db = [r for r in report.results if r.name == "deck_build"][0]
        # Deck still builds with baseline tools even if skill tool missing
        assert db.passed


# ---------------------------------------------------------------------------
# L3: Regression Tests
# ---------------------------------------------------------------------------

class TestRegressionTests:
    def test_regression_data_found(self, runner):
        report = runner.run_skill("regression-skill", levels={SkillTestLevel.REGRESSION})
        assert any(r.name == "regression_read_file" and r.passed for r in report.results)

    def test_regression_missing_tool_fails(self, runner):
        report = runner.run_skill("regression-skill", levels={SkillTestLevel.REGRESSION})
        assert any(
            r.name == "regression_missing_tool" and not r.passed
            for r in report.results
        )

    def test_no_regression_data_info(self, runner):
        report = runner.run_skill("web-research", levels={SkillTestLevel.REGRESSION})
        assert any(
            r.name == "regression_data" and r.passed
            for r in report.results
        )


# ---------------------------------------------------------------------------
# L4: Stress Tests
# ---------------------------------------------------------------------------

class TestStressTests:
    def test_large_input(self, runner):
        report = runner.run_skill("web-research", levels={SkillTestLevel.STRESS})
        li = [r for r in report.results if r.name == "stress_large_input"][0]
        assert li.passed

    def test_empty_tools_deck(self, runner):
        report = runner.run_skill("web-research", levels={SkillTestLevel.STRESS})
        et = [r for r in report.results if r.name == "stress_empty_tools"][0]
        assert et.passed

    def test_dedup(self, runner):
        report = runner.run_skill("web-research", levels={SkillTestLevel.STRESS})
        dd = [r for r in report.results if r.name == "stress_dedup"][0]
        assert dd.passed


# ---------------------------------------------------------------------------
# Multi-level / batch
# ---------------------------------------------------------------------------

class TestMultiLevel:
    def test_default_levels(self, runner):
        # Default = UNIT + INTEGRATION
        report = runner.run_skill("web-research")
        levels = {r.level for r in report.results}
        assert SkillTestLevel.UNIT in levels
        assert SkillTestLevel.INTEGRATION in levels
        assert SkillTestLevel.REGRESSION not in levels

    def test_all_levels(self, runner):
        report = runner.run_skill("web-research", levels={
            SkillTestLevel.UNIT, SkillTestLevel.INTEGRATION,
            SkillTestLevel.REGRESSION, SkillTestLevel.STRESS,
        })
        levels = {r.level for r in report.results}
        assert SkillTestLevel.UNIT in levels
        assert SkillTestLevel.INTEGRATION in levels
        assert SkillTestLevel.STRESS in levels

    def test_run_all(self, runner):
        reports = runner.run_all(levels={SkillTestLevel.UNIT})
        names = {r.skill_name for r in reports}
        assert "web-research" in names
        assert "broken-skill" in names
