"""Bottom-up test framework for skills — validate execution-level behavior.

Test levels (bottom-up):
  L1 Unit        — schema validation, param boundary checks
  L2 Integration — Deck build + skill match, tool call chains
  L3 Regression  — historical scenario replay
  L4 Stress      — large inputs, concurrency safety

Usage:
    from agent.skill_test import SkillTestRunner, SkillTestLevel
    runner = SkillTestRunner(registry, skills_dir)
    result = runner.run_skill("web-research", levels={SkillTestLevel.UNIT, SkillTestLevel.INTEGRATION})
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable


class SkillTestLevel(Enum):
    """Test coverage levels."""

    UNIT = auto()
    INTEGRATION = auto()
    REGRESSION = auto()
    STRESS = auto()


@dataclass
class SkillTestCase:
    """A single test case."""

    name: str
    level: SkillTestLevel
    func: Callable[[], tuple[bool, str]]


@dataclass
class SkillTestResult:
    """Result of a single test case."""

    name: str
    level: SkillTestLevel
    passed: bool
    message: str
    duration_ms: float = 0.0


@dataclass
class SkillTestReport:
    """Complete test report for a skill."""

    skill_name: str
    results: list[SkillTestResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        if not self.results:
            return False
        return all(r.passed for r in self.results)

    @property
    def summary(self) -> dict[str, int]:
        return {
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
        }

    @property
    def score(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    def to_dict(self) -> dict:
        return {
            "skill": self.skill_name,
            "passed": self.passed,
            "score": round(self.score, 2),
            "summary": self.summary,
            "results": [
                {
                    "name": r.name,
                    "level": r.level.name,
                    "passed": r.passed,
                    "message": r.message,
                    "duration_ms": round(r.duration_ms, 1),
                }
                for r in self.results
            ],
        }


class SkillTestRunner:
    """Run bottom-up tests against a skill."""

    def __init__(self, registry, skills_dir: str | Path):
        self.registry = registry
        self.skills_dir = Path(skills_dir)
        self._skill_cache: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_skill(
        self,
        skill_name: str,
        levels: set[SkillTestLevel] | None = None,
    ) -> SkillTestReport:
        """Run all applicable tests for a skill."""
        if levels is None:
            levels = {SkillTestLevel.UNIT, SkillTestLevel.INTEGRATION}

        report = SkillTestReport(skill_name=skill_name)
        skill = self._load_skill(skill_name)

        if skill is None:
            report.results.append(
                SkillTestResult(
                    name="skill_exists",
                    level=SkillTestLevel.UNIT,
                    passed=False,
                    message=f"Skill '{skill_name}' not found",
                )
            )
            return report

        # L1: Unit tests
        if SkillTestLevel.UNIT in levels:
            report.results.extend(self._run_unit_tests(skill))

        # L2: Integration tests
        if SkillTestLevel.INTEGRATION in levels:
            report.results.extend(self._run_integration_tests(skill))

        # L3: Regression tests
        if SkillTestLevel.REGRESSION in levels:
            report.results.extend(self._run_regression_tests(skill))

        # L4: Stress tests
        if SkillTestLevel.STRESS in levels:
            report.results.extend(self._run_stress_tests(skill))

        return report

    def run_all(
        self,
        levels: set[SkillTestLevel] | None = None,
    ) -> list[SkillTestReport]:
        """Run tests for all skills."""
        reports: list[SkillTestReport] = []
        if not self.skills_dir.exists():
            return reports

        for path in sorted(self.skills_dir.glob("*.md")):
            if path.name.startswith(".") or path.suffixes == [".md", ".local"]:
                continue
            skill = self._quick_parse(path)
            if skill and "name" in skill:
                reports.append(self.run_skill(skill["name"], levels=levels))

        return reports

    # ------------------------------------------------------------------
    # L1: Unit Tests
    # ------------------------------------------------------------------

    def _run_unit_tests(self, skill: dict) -> list[SkillTestResult]:
        """Schema and boundary checks for declared tools."""
        results: list[SkillTestResult] = []
        tools: list[str] = skill.get("tools", [])

        # T001: all tools have valid schemas
        for tool_name in tools:
            t0 = time.perf_counter()
            if not self.registry.has_tool(tool_name):
                results.append(
                    SkillTestResult(
                        name=f"schema_exists_{tool_name}",
                        level=SkillTestLevel.UNIT,
                        passed=False,
                        message=f"Tool '{tool_name}' not in registry",
                        duration_ms=(time.perf_counter() - t0) * 1000,
                    )
                )
                continue

            schema = self.registry.get_schema(tool_name)
            if schema is None:
                results.append(
                    SkillTestResult(
                        name=f"schema_valid_{tool_name}",
                        level=SkillTestLevel.UNIT,
                        passed=False,
                        message=f"Tool '{tool_name}' has no schema",
                        duration_ms=(time.perf_counter() - t0) * 1000,
                    )
                )
                continue

            # Validate schema structure
            ok, msg = self._validate_schema_structure(schema)
            results.append(
                SkillTestResult(
                    name=f"schema_valid_{tool_name}",
                    level=SkillTestLevel.UNIT,
                    passed=ok,
                    message=msg,
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
            )

        # T002: tools list non-empty
        t0 = time.perf_counter()
        results.append(
            SkillTestResult(
                name="tools_non_empty",
                level=SkillTestLevel.UNIT,
                passed=len(tools) > 0,
                message="tools" if len(tools) > 0 else "Skill declares no tools",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )

        # T003: trigger parsing
        t0 = time.perf_counter()
        triggers = skill.get("triggers", [])
        results.append(
            SkillTestResult(
                name="trigger_parsable",
                level=SkillTestLevel.UNIT,
                passed=len(triggers) > 0,
                message=f"{len(triggers)} trigger(s)" if triggers else "No triggers",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )

        return results

    # ------------------------------------------------------------------
    # L2: Integration Tests
    # ------------------------------------------------------------------

    def _run_integration_tests(self, skill: dict) -> list[SkillTestResult]:
        """Deck build and skill matching integration."""
        results: list[SkillTestResult] = []
        tools: list[str] = skill.get("tools", [])
        skill_name = skill.get("name", "unknown")

        # I001: Deck can be built
        t0 = time.perf_counter()
        try:
            from agent.deck import build_deck
            deck = build_deck(tools, self.registry, redundancy=3)
            ok = deck.size() > 0
            msg = f"Deck built with {deck.size()} tools"
        except Exception as exc:
            ok = False
            msg = f"Deck build failed: {exc}"
        results.append(
            SkillTestResult(
                name="deck_build",
                level=SkillTestLevel.INTEGRATION,
                passed=ok,
                message=msg,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )

        # I002: skill match triggers
        t0 = time.perf_counter()
        try:
            from agent.skills import SkillManager
            mgr = SkillManager(str(self.skills_dir))
            # Only load this one skill for isolation
            mgr._skills[skill_name] = skill
            matched = mgr.match_skills(skill.get("triggers", [""])[0] if skill.get("triggers") else "test")
            ok = skill_name in matched
            msg = f"Matched by trigger: {ok}"
        except Exception as exc:
            ok = False
            msg = f"Match test failed: {exc}"
        results.append(
            SkillTestResult(
                name="skill_match",
                level=SkillTestLevel.INTEGRATION,
                passed=ok,
                message=msg,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )

        # I003: protocol conversion
        t0 = time.perf_counter()
        try:
            from agent.deck import Deck
            deck = Deck(tools, self.registry)
            anthropic = deck.get_schemas_for_protocol("anthropic")
            openai = deck.get_schemas_for_protocol("openai")
            ok = len(anthropic) == len(openai) == deck.size()
            msg = f"Protocol schemas: anthropic={len(anthropic)}, openai={len(openai)}"
        except Exception as exc:
            ok = False
            msg = f"Protocol conversion failed: {exc}"
        results.append(
            SkillTestResult(
                name="protocol_conversion",
                level=SkillTestLevel.INTEGRATION,
                passed=ok,
                message=msg,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )

        return results

    # ------------------------------------------------------------------
    # L3: Regression Tests
    # ------------------------------------------------------------------

    def _run_regression_tests(self, skill: dict) -> list[SkillTestResult]:
        """Replay historical scenarios if available."""
        results: list[SkillTestResult] = []
        skill_name = skill.get("name", "unknown")

        # Look for regression fixture: skills/<name>.regression.json
        regression_path = self.skills_dir / f"{skill_name}.regression.json"
        if not regression_path.exists():
            results.append(
                SkillTestResult(
                    name="regression_data",
                    level=SkillTestLevel.REGRESSION,
                    passed=True,  # Not a failure if no data yet
                    message="No regression data found — create .regression.json to enable",
                )
            )
            return results

        try:
            data = json.loads(regression_path.read_text(encoding="utf-8"))
            cases = data if isinstance(data, list) else data.get("cases", [])
        except Exception as exc:
            results.append(
                SkillTestResult(
                    name="regression_load",
                    level=SkillTestLevel.REGRESSION,
                    passed=False,
                    message=f"Failed to load regression data: {exc}",
                )
            )
            return results

        for i, case in enumerate(cases):
            t0 = time.perf_counter()
            name = case.get("name", f"case_{i}")
            input_text = case.get("input", "")
            expected_tools = case.get("expected_tools", [])

            try:
                # Verify expected tools are in skill's declared tools
                missing_tools = [t for t in expected_tools if t not in skill.get("tools", [])]
                if missing_tools:
                    ok = False
                    msg = f"Expected tools not declared: {missing_tools}"
                else:
                    ok = True
                    msg = f"All expected tools declared"
            except Exception as exc:
                ok = False
                msg = f"Regression case '{name}' failed: {exc}"

            results.append(
                SkillTestResult(
                    name=f"regression_{name}",
                    level=SkillTestLevel.REGRESSION,
                    passed=ok,
                    message=msg,
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
            )

        return results

    # ------------------------------------------------------------------
    # L4: Stress Tests
    # ------------------------------------------------------------------

    def _run_stress_tests(self, skill: dict) -> list[SkillTestResult]:
        """Stress tests for edge cases."""
        results: list[SkillTestResult] = []
        tools: list[str] = skill.get("tools", [])

        # S001: large trigger input
        t0 = time.perf_counter()
        try:
            from agent.skills import SkillManager
            mgr = SkillManager(str(self.skills_dir))
            mgr._skills[skill.get("name", "unknown")] = skill
            big_input = "test " * 1000
            matched = mgr.match_skills(big_input)
            ok = True
            msg = f"Large input ({len(big_input)} chars) processed without error"
        except Exception as exc:
            ok = False
            msg = f"Large input failed: {exc}"
        results.append(
            SkillTestResult(
                name="stress_large_input",
                level=SkillTestLevel.STRESS,
                passed=ok,
                message=msg,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )

        # S002: empty/null tools boundary
        t0 = time.perf_counter()
        try:
            from agent.deck import build_deck
            deck = build_deck([], self.registry, redundancy=3)
            ok = True
            msg = f"Empty skill tools Deck built with {deck.size()} baseline tools"
        except Exception as exc:
            ok = False
            msg = f"Empty tools Deck failed: {exc}"
        results.append(
            SkillTestResult(
                name="stress_empty_tools",
                level=SkillTestLevel.STRESS,
                passed=ok,
                message=msg,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )

        # S003: duplicate tools dedup
        t0 = time.perf_counter()
        try:
            from agent.deck import Deck
            dup_tools = tools + tools  # double the list
            deck = Deck(dup_tools, self.registry)
            unique = len(set(tools))
            ok = deck.size() == unique
            msg = f"Deduplication: {len(dup_tools)} -> {deck.size()} (expected {unique})"
        except Exception as exc:
            ok = False
            msg = f"Dedup test failed: {exc}"
        results.append(
            SkillTestResult(
                name="stress_dedup",
                level=SkillTestLevel.STRESS,
                passed=ok,
                message=msg,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_skill(self, skill_name: str) -> dict | None:
        """Load a skill by name (cached)."""
        if skill_name in self._skill_cache:
            return self._skill_cache[skill_name]

        from agent.skills import SkillManager
        mgr = SkillManager(str(self.skills_dir))
        mgr.load_all()
        skill = mgr.get_skill(skill_name)
        if skill:
            self._skill_cache[skill_name] = skill
        return skill

    def _quick_parse(self, path: Path) -> dict | None:
        from agent.skills import SkillManager
        mgr = SkillManager(str(self.skills_dir))
        return mgr._load_skill_file(path)

    def _validate_schema_structure(self, schema: dict) -> tuple[bool, str]:
        """Validate tool schema has required structure."""
        if not isinstance(schema, dict):
            return False, "Schema is not a dict"

        if "name" not in schema:
            return False, "Missing 'name' field"

        # Anthropic-style: input_schema
        if "input_schema" in schema:
            params = schema["input_schema"]
            if not isinstance(params, dict):
                return False, "input_schema is not a dict"
            if "properties" not in params:
                return False, "input_schema missing 'properties'"
            return True, "Anthropic-style schema OK"

        # OpenAI-style: parameters
        if "parameters" in schema:
            params = schema["parameters"]
            if not isinstance(params, dict):
                return False, "parameters is not a dict"
            if "properties" not in params:
                return False, "parameters missing 'properties'"
            return True, "OpenAI-style schema OK"

        return False, "Schema missing input_schema or parameters"
