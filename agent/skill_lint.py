"""Top-down lint for skills — validate against Deck system constraints.

Design-level checks (top-down):
  L1 Structure      — file layout, frontmatter completeness
  L2 Deck Compat    — tools exist in registry, focus-mode coverage
  L3 Safety         — dangerous tools, confirmation policy, param patterns
  L4 Contract       — input/output description, error handling, density

Usage:
    from agent.skill_lint import SkillLint, LintLevel
    linter = SkillLint(registry, skills_dir)
    report = linter.lint_skill("web-research")
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Iterable

from agent.deck import BASELINE_POOL, build_deck


class LintLevel(Enum):
    """Lint severity levels."""

    ERROR = auto()      # Violates system constraint — will break at runtime
    WARN = auto()       # Risky or inconsistent — may cause unexpected behavior
    INFO = auto()       # Suggestion for improvement


@dataclass
class LintFinding:
    """A single lint finding."""

    level: LintLevel
    category: str       # structure | deck_compat | safety | contract
    code: str           # e.g. S001, D002
    message: str
    line: int | None = None


@dataclass
class LintReport:
    """Complete lint report for a skill."""

    skill_name: str
    findings: list[LintFinding] = field(default_factory=list)

    @property
    def errors(self) -> list[LintFinding]:
        return [f for f in self.findings if f.level == LintLevel.ERROR]

    @property
    def warnings(self) -> list[LintFinding]:
        return [f for f in self.findings if f.level == LintLevel.WARN]

    @property
    def infos(self) -> list[LintFinding]:
        return [f for f in self.findings if f.level == LintLevel.INFO]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    @property
    def score(self) -> float:
        """Simple score: 1.0 = no findings, 0.0 = any error."""
        if self.errors:
            return 0.0
        penalty = len(self.warnings) * 0.05 + len(self.infos) * 0.01
        return max(0.0, 1.0 - penalty)

    def to_dict(self) -> dict:
        return {
            "skill": self.skill_name,
            "ok": self.ok,
            "score": round(self.score, 2),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "infos": len(self.infos),
            "findings": [
                {
                    "level": f.level.name,
                    "category": f.category,
                    "code": f.code,
                    "message": f.message,
                    "line": f.line,
                }
                for f in self.findings
            ],
        }


class SkillLint:
    """Lint checker for skills against Deck system constraints."""

    # Safety-sensitive tools that need extra scrutiny
    DANGEROUS_TOOLS: set[str] = {
        "sys_terminal",
        "fs_write_file",
        "fs_delete_file",
        "fs_move_file",
        "deck_manage",
    }

    # Dangerous shell patterns (regex)
    DANGEROUS_PATTERNS: list[tuple[re.Pattern, str]] = [
        (re.compile(r"rm\s+-rf?\s+(/|~)"), "rm on root/home directory"),
        (re.compile(r">\s*/dev/null\s*&&\s*rm"), "redirect + rm pattern"),
        (re.compile(r"curl\s+.*\s*\|\s*sh"), "curl pipe to shell"),
        (re.compile(r"wget\s+.*\s*\|\s*sh"), "wget pipe to shell"),
        (re.compile(r"sudo\s+rm\s+-rf"), "sudo rm -rf"),
        (re.compile(r"mkfs\.|dd\s+if=.*of=/dev/"), "disk destroyer"),
    ]

    # Required frontmatter fields (matching parsed skill dict keys)
    REQUIRED_FIELDS: set[str] = {"name", "description", "triggers", "tools"}
    # Recommended frontmatter fields
    RECOMMENDED_FIELDS: set[str] = {"category", "version", "composability"}

    def __init__(self, registry, skills_dir: str | Path):
        self.registry = registry
        self.skills_dir = Path(skills_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lint_skill(self, skill_name: str) -> LintReport:
        """Lint a single skill by name."""
        report = LintReport(skill_name=skill_name)
        skill_path = self._find_skill_file(skill_name)

        if skill_path is None:
            report.findings.append(
                LintFinding(
                    LintLevel.ERROR, "structure", "S001",
                    f"SKILL.md not found for skill '{skill_name}'",
                )
            )
            return report

        raw = skill_path.read_text(encoding="utf-8")
        from agent.skills import SkillManager
        mgr = SkillManager(str(self.skills_dir))
        skill = mgr._load_skill_file(skill_path)

        if skill is None:
            report.findings.append(
                LintFinding(
                    LintLevel.ERROR, "structure", "S002",
                    f"Failed to parse skill file: {skill_path.name}",
                )
            )
            return report

        self._check_structure(report, skill, skill_path, raw)
        self._check_deck_compat(report, skill)
        self._check_safety(report, skill, raw)
        self._check_contract(report, skill, raw)

        return report

    def lint_all(self) -> list[LintReport]:
        """Lint all skills in the directory."""
        reports: list[LintReport] = []
        if not self.skills_dir.exists():
            return reports

        for path in sorted(self.skills_dir.glob("*.md")):
            # Skip cache and local overrides
            if path.name.startswith(".") or path.suffixes == [".md", ".local"]:
                continue
            skill = self._quick_parse(path)
            if skill and "name" in skill:
                reports.append(self.lint_skill(skill["name"]))

        return reports

    # ------------------------------------------------------------------
    # L1: Structure
    # ------------------------------------------------------------------

    def _check_structure(
        self, report: LintReport, skill: dict, path: Path, raw: str
    ) -> None:
        """Check file structure and frontmatter completeness."""
        # S003: required fields present and non-empty
        missing_fields: list[str] = []
        for field in self.REQUIRED_FIELDS:
            val = skill.get(field)
            if val is None or val == "" or val == []:
                missing_fields.append(field)
        if missing_fields:
            report.findings.append(
                LintFinding(
                    LintLevel.ERROR, "structure", "S003",
                    f"Missing or empty required fields: {sorted(missing_fields)}",
                )
            )

        # S004: recommended fields
        missing_rec = self.RECOMMENDED_FIELDS - set(skill.keys())
        if missing_rec:
            report.findings.append(
                LintFinding(
                    LintLevel.INFO, "structure", "S004",
                    f"Missing recommended fields: {sorted(missing_rec)}",
                )
            )

        # S005: frontmatter name matches filename stem
        frontmatter_name = self._extract_frontmatter_name(raw)
        if frontmatter_name and frontmatter_name != path.stem:
            report.findings.append(
                LintFinding(
                    LintLevel.WARN, "structure", "S005",
                    f"Filename stem '{path.stem}' does not match frontmatter name '{frontmatter_name}'",
                )
            )

        # S006: tools list non-empty
        tools = skill.get("tools", [])
        if not tools:
            report.findings.append(
                LintFinding(
                    LintLevel.ERROR, "structure", "S006",
                    "Skill declares no tools — cannot build Deck",
                )
            )

        # S007: body exists (after frontmatter)
        body = skill.get("_body", "")
        if len(body.strip()) < 50:
            report.findings.append(
                LintFinding(
                    LintLevel.WARN, "structure", "S007",
                    f"Skill body is very short ({len(body.strip())} chars) — may lack context",
                )
            )

    # ------------------------------------------------------------------
    # L2: Deck Compatibility
    # ------------------------------------------------------------------

    def _check_deck_compat(self, report: LintReport, skill: dict) -> None:
        """Check skill compatibility with Deck system."""
        tools: list[str] = skill.get("tools", [])
        if not tools:
            return

        # D001: all declared tools exist in registry
        missing_tools = [t for t in tools if not self.registry.has_tool(t)]
        if missing_tools:
            report.findings.append(
                LintFinding(
                    LintLevel.ERROR, "deck_compat", "D001",
                    f"Tools not in registry: {missing_tools}",
                )
            )

        # D002: tool naming convention (snake_case)
        bad_names = [t for t in tools if not re.match(r"^[a-z][a-z0-9_]*$", t)]
        if bad_names:
            report.findings.append(
                LintFinding(
                    LintLevel.WARN, "deck_compat", "D002",
                    f"Tool names not snake_case: {bad_names}",
                )
            )

        # D003: focus-mode coverage — can we build a valid Deck?
        try:
            deck = build_deck(tools, self.registry, redundancy=3)
            if deck.size() == 0:
                report.findings.append(
                    LintFinding(
                        LintLevel.ERROR, "deck_compat", "D003",
                        "focus mode Deck built with 0 tools — skill is uncallable",
                    )
                )
        except Exception as exc:
            report.findings.append(
                LintFinding(
                    LintLevel.ERROR, "deck_compat", "D003",
                    f"Deck build failed: {exc}",
                )
            )

        # D004: tools declared but not in BASELINE_POOL redundancy path
        # This is INFO-level: the skill works, but won't get extra tools in focus mode
        declared = set(tools)
        available_in_focus = declared | set(BASELINE_POOL)
        # Already covered by build_deck, so just a sanity check
        if not declared:
            report.findings.append(
                LintFinding(
                    LintLevel.ERROR, "deck_compat", "D004",
                    "No tools declared — Deck cannot be built",
                )
            )

    # ------------------------------------------------------------------
    # L3: Safety
    # ------------------------------------------------------------------

    def _check_safety(
        self, report: LintReport, skill: dict, raw: str
    ) -> None:
        """Check safety constraints."""
        tools: list[str] = skill.get("tools", [])
        body = skill.get("_body", "")

        # F001: dangerous tools declared
        dangerous = set(tools) & self.DANGEROUS_TOOLS
        if dangerous:
            report.findings.append(
                LintFinding(
                    LintLevel.WARN, "safety", "F001",
                    f"Dangerous tools declared: {sorted(dangerous)} — verify confirmation policy",
                )
            )

        # F002: dangerous patterns in body
        for pattern, desc in self.DANGEROUS_PATTERNS:
            for match in pattern.finditer(body):
                line = raw[: match.start()].count("\n") + 1
                report.findings.append(
                    LintFinding(
                        LintLevel.ERROR, "safety", "F002",
                        f"Dangerous pattern detected: {desc}",
                        line=line,
                    )
                )

        # F003: fs_write_file without mention of confirmation
        if "fs_write_file" in tools:
            if "confirm" not in body.lower() and "确认" not in body:
                report.findings.append(
                    LintFinding(
                        LintLevel.WARN, "safety", "F003",
                        "fs_write_file in tools but body lacks confirmation guidance",
                    )
                )

        # F004: sys_terminal with broad commands
        if "sys_terminal" in tools:
            # Check if examples include sanitized patterns
            has_safe_examples = any(
                safe in body
                for safe in ("ALLOWLIST", "whitelist", "允许列表", "只读")
            )
            if not has_safe_examples:
                report.findings.append(
                    LintFinding(
                        LintLevel.INFO, "safety", "F004",
                        "sys_terminal declared — consider documenting safe command patterns",
                    )
                )

    # ------------------------------------------------------------------
    # L4: Contract
    # ------------------------------------------------------------------

    def _check_contract(
        self, report: LintReport, skill: dict, raw: str
    ) -> None:
        """Check information contract completeness."""
        body = skill.get("_body", "")

        # C001: input/output description
        has_io = any(
            kw in body.lower()
            for kw in ("输入", "输出", "input", "output", "参数", "parameter", "返回", "return")
        )
        if not has_io:
            report.findings.append(
                LintFinding(
                    LintLevel.INFO, "contract", "C001",
                    "No explicit input/output description found",
                )
            )

        # C002: error handling description
        has_error = any(
            kw in body.lower()
            for kw in ("错误", "异常", "失败", "error", "exception", "fail", "做不到")
        )
        if not has_error:
            report.findings.append(
                LintFinding(
                    LintLevel.INFO, "contract", "C002",
                    "No error handling guidance found",
                )
            )

        # C003: information density — body should have actionable detail
        words = len(body.split())
        if words < 30:
            report.findings.append(
                LintFinding(
                    LintLevel.WARN, "contract", "C003",
                    f"Body is sparse ({words} words) — may lack actionable detail",
                )
            )

        # C004: examples present
        has_examples = "```" in body or "example" in body.lower() or "示例" in body
        if not has_examples:
            report.findings.append(
                LintFinding(
                    LintLevel.INFO, "contract", "C004",
                    "No code examples or usage samples found",
                )
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_skill_file(self, skill_name: str) -> Path | None:
        """Find skill file by name (matches path.stem or frontmatter name)."""
        if not self.skills_dir.exists():
            return None
        for path in self.skills_dir.glob("*.md"):
            if path.name.startswith("."):
                continue
            # Fast path: match filename stem
            if path.stem == skill_name:
                return path
            # Slow path: parse frontmatter name
            raw = path.read_text(encoding="utf-8")
            fm_name = self._extract_frontmatter_name(raw)
            if fm_name == skill_name:
                return path
        return None

    def _quick_parse(self, path: Path) -> dict | None:
        """Quick-parse a skill file without loading all."""
        from agent.skills import SkillManager
        mgr = SkillManager(str(self.skills_dir))
        return mgr._load_skill_file(path)

    def _extract_frontmatter_name(self, raw: str) -> str | None:
        """Extract the 'name' field from raw frontmatter text."""
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
        if m:
            from agent.skills import _parse_yamlish
            meta = _parse_yamlish(m.group(1))
            return meta.get("name")
        return None
