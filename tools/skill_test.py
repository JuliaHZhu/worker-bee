"""Skill test — automated validation for skill markdown files.

Validates:
  - Frontmatter format (name, description, trigger, tools, category)
  - Trigger uniqueness (no substring overlap with other skills)
  - Tool existence (each declared tool must be in registry)
  - Body structure (non-empty after frontmatter)
  - Match simulation (sample inputs against triggers)
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from registry import registry


SKILLS_DIR = Path(__file__).parent.parent / "skills"


def _parse_frontmatter(content: str) -> Tuple[Optional[dict], str]:
    """Parse YAML frontmatter. Returns (meta_dict, body_text)."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return None, content

    meta = {}
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line or line.startswith("-"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, rest = line.split(":", 1)
        key = key.strip()
        val = rest.strip()
        if val:
            meta[key] = val
            i += 1
            continue
        # Multi-line list
        j = i + 1
        items = []
        while j < len(lines):
            nl = lines[j].strip()
            if not nl:
                j += 1
                continue
            if nl.startswith("-"):
                items.append(nl[1:].strip())
                j += 1
                continue
            break
        if items:
            meta[key] = items
            i = j
        else:
            meta[key] = ""
            i += 1
    return meta, content[m.end():].strip()


def _get_triggers(meta: dict):
    """Extract triggers from meta, supporting both 'trigger' and 'triggers' keys."""
    triggers = meta.get("trigger", meta.get("triggers", []))
    if isinstance(triggers, str):
        triggers = [t.strip() for t in triggers.split(",") if t.strip()]
    return triggers


def _validate_frontmatter(meta: dict) -> List[str]:
    """Return list of frontmatter validation errors."""
    errors = []
    required = ["name", "description", "trigger", "tools", "category"]
    for key in required:
        if key not in meta:
            errors.append(f"Missing required field: '{key}'")

    name = meta.get("name", "")
    if name:
        if not re.match(r"^[a-z0-9-]+$", name):
            errors.append(f"Invalid name '{name}': must be lowercase letters/numbers/hyphens")
        if len(name) > 64:
            errors.append(f"Name too long: {len(name)} chars (max 64)")

    desc = meta.get("description", "")
    if desc:
        if len(desc) > 1024:
            errors.append(f"Description too long: {len(desc)} chars (max 1024)")
        if not desc.startswith("Use when"):
            errors.append("Description should start with 'Use when...'")

    triggers = _get_triggers(meta)
    if not triggers:
        errors.append("No triggers defined")
    for t in triggers:
        if len(t.split()) < 2 and len(t) < 4:
            errors.append(f"Trigger too short/abstract: '{t}' (use multi-word phrases)")

    tools = meta.get("tools", [])
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",") if t.strip()]
    if len(tools) > 5:
        errors.append(f"Too many tools: {len(tools)} (recommend 2-4)")

    return errors


def _check_trigger_conflicts(all_skills: Dict[str, dict]) -> List[str]:
    """Check for trigger substring overlaps between skills."""
    conflicts = []
    skill_triggers = {}
    for name, meta in all_skills.items():
        triggers = _get_triggers(meta)
        skill_triggers[name] = [t.lower() for t in triggers]

    names = list(skill_triggers.keys())
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for ta in skill_triggers[a]:
                for tb in skill_triggers[b]:
                    if ta in tb or tb in ta:
                        if ta != tb:
                            conflicts.append(
                                f"Trigger overlap: '{a}' ('{ta}') vs '{b}' ('{tb}')"
                            )
    return conflicts


def _check_tool_existence(tools: List[str]) -> List[str]:
    """Check if declared tools exist in registry."""
    missing = []
    for t in tools:
        if not registry.has_tool(t):
            missing.append(f"Tool not found in registry: '{t}'")
    return missing


def _simulate_matches(all_skills: Dict[str, dict], samples: List[str]) -> Dict[str, List[str]]:
    """Simulate trigger matching for sample inputs."""
    results = {}
    for sample in samples:
        matched = []
        sample_lower = sample.lower()
        for name, meta in all_skills.items():
            triggers = _get_triggers(meta)
            for trig in triggers:
                if trig.lower() in sample_lower:
                    matched.append(name)
                    break
        results[sample] = matched
    return results


def skill_test(target: str = "all", verbose: bool = False) -> str:
    """Validate skill markdown files.

    Args:
        target: "all" to validate all skills, or a specific skill filename (without .md)
        verbose: include full match simulation and details
    """
    if not SKILLS_DIR.exists():
        return "Error: skills/ directory not found"

    # Load all skill files
    skill_files = {}
    for path in sorted(SKILLS_DIR.glob("*.md")):
        if path.name.startswith("."):
            continue
        content = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(content)
        skill_files[path.stem] = {
            "path": str(path),
            "meta": meta or {},
            "body": body,
            "has_frontmatter": meta is not None,
        }

    if target != "all" and target not in skill_files:
        return f"Error: skill '{target}' not found in {SKILLS_DIR}"

    targets = [target] if target != "all" else list(skill_files.keys())

    # Build all_skills dict for conflict checking
    all_skills = {name: data["meta"] for name, data in skill_files.items()}

    reports = []
    total_issues = 0

    for name in targets:
        data = skill_files[name]
        issues = []

        # Frontmatter presence
        if not data["has_frontmatter"]:
            issues.append("No YAML frontmatter found")
            reports.append((name, issues))
            total_issues += len(issues)
            continue

        meta = data["meta"]

        # Frontmatter validation
        issues.extend(_validate_frontmatter(meta))

        # Body non-empty
        if not data["body"]:
            issues.append("Body is empty after frontmatter")

        # Tool existence
        tools = meta.get("tools", [])
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(",") if t.strip()]
        issues.extend(_check_tool_existence(tools))

        reports.append((name, issues))
        total_issues += len(issues)

    # Global checks
    global_issues = _check_trigger_conflicts(all_skills)
    total_issues += len(global_issues)

    # Build output
    lines = ["# Skill Test Report", ""]

    # Score calculation: for single-target, exclude global conflicts
    score_issues = total_issues
    if target != "all":
        score_issues = sum(len(issues) for _, issues in reports)
    score = max(0, 10 - score_issues)
    lines.append(f"Score: {score}/10")
    lines.append(f"Skills checked: {len(targets)}")
    lines.append(f"Total issues: {total_issues}")
    if target == "all" and global_issues:
        lines.append(f"Global conflicts: {len(global_issues)}")
    lines.append("")

    # Per-skill report
    for name, issues in reports:
        status = "✅ PASS" if not issues else "❌ FAIL"
        lines.append(f"## {name} {status}")
        if issues:
            for issue in issues:
                lines.append(f"  - {issue}")
        else:
            lines.append("  No issues found.")
        lines.append("")

    # Global conflicts
    if global_issues:
        lines.append("## Global Trigger Conflicts")
        for issue in global_issues:
            lines.append(f"  - {issue}")
        lines.append("")

    # Match simulation (verbose only)
    if verbose:
        samples = [
            "create mechanism skill",
            "create task skill",
            "audit skill",
            "search something online",
            "review my code",
        ]
        sim = _simulate_matches(all_skills, samples)
        lines.append("## Match Simulation")
        for sample, matched in sim.items():
            match_str = ", ".join(matched) if matched else "(none)"
            lines.append(f"  '{sample}' → {match_str}")
        lines.append("")

    lines.append("---")
    if total_issues == 0:
        lines.append("All checks passed. Skill is ready to deploy.")
    else:
        lines.append(f"Fix {total_issues} issue(s) before deploying.")

    return "\n".join(lines)


# Register tool
registry.register(
    name="skill_test",
    description=(
        "Validate skill markdown files for frontmatter correctness, "
        "trigger uniqueness, tool existence, and body structure. "
        "Use after writing or editing a skill."
    ),
    parameters={
        "properties": {
            "target": {
                "type": "string",
                "description": 'Skill name to validate (without .md), or "all" for all skills',
                "default": "all",
            },
            "verbose": {
                "type": "boolean",
                "description": "Include match simulation details",
                "default": False,
            },
        },
        "required": [],
    },
    handler=skill_test,
    tags=["skill", "testing", "validation"],
    category="skill-authoring",
)
