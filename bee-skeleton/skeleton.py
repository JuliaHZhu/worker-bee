#!/usr/bin/env python3
"""
Skeleton Bee — 总工程师/首席架构师（CAO）
版本: MVP v3.1（红队修订版）
日期: 2026-07-16

唯一职责：给每个生产批次画对蓝图。
"""

from __future__ import annotations

import os
import sys
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# ─── 常量 ───
BASE_DIR = Path(__file__).parent.resolve()
ARCH_DIR = BASE_DIR / "arch"
DRAFTS_DIR = BASE_DIR / "drafts"
PATTERNS_FILE = BASE_DIR / "patterns.md"
ANTIPATTERNS_FILE = BASE_DIR / "anti-patterns.md"

CONSTITUTION_PATHS = {"arch/"}


# ─── 核心约束: safe_write ───
def safe_write(path: str | Path, content: str, approved_by: str = "") -> None:
    """
    写 arch/ 必须带 approved_by（厂长在回路时的批准标记）。
    Research Mode 不提供 approved_by，写 arch/ 直接报错。
    所有写操作必须在 BASE_DIR 内。
    """
    path = Path(path)

    # ● 沙箱：任何写操作必须在 BASE_DIR 内
    try:
        path.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        raise PermissionError(
            f"[Skeleton] 越权写操作：{path} 不在 BASE_DIR {BASE_DIR} 内"
        )

    # ● 宪法路径：用 Path.parts 精确匹配，不是 substring
    path_parts = path.resolve().parts
    in_constitution = any(
        part == "arch" for part in path_parts
    )
    if in_constitution:
        if not approved_by:
            raise PermissionError(
                f"[Skeleton] 写 arch/ 必须提供 approved_by：{path}"
            )
        # 在内容头部嵌入批准元数据
        header = f"<!-- Approved by: {approved_by} | {datetime.now().strftime('%Y-%m-%d')} -->\n"
        content = header + content

    path.write_text(content, encoding="utf-8")
    print(f"[Skeleton] 写入: {path}")


def safe_read(path: str | Path) -> str:
    """读取文件，不存在时返回空字符串。"""
    path = Path(path)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def ensure_dirs(project: str) -> Path:
    """确保 arch/<project>/ 目录存在，返回路径。"""
    proj_dir = ARCH_DIR / project
    proj_dir.mkdir(parents=True, exist_ok=True)
    return proj_dir


# ─── Campaign Mode: 5步原语 + closure 收尾 ───

def capture_intent(project: str, raw_need: str, approved_by: str) -> Path:
    """步骤1: 把原始冲动锚定成文字，划清"做/不做"。"""
    proj_dir = ensure_dirs(project)
    content = f"""# Intent: {project}

**原始需求**：{raw_need}

**真正想要什么**：（在对话中精炼后填充）

**不做什么**：（明确排除的范围）
"""
    out = proj_dir / "intent.md"
    safe_write(out, content, approved_by)
    return out


def decompose_goal(project: str, approved_by: str) -> Path:
    """步骤2: 目标层级展开，写清反目标。"""
    proj_dir = ARCH_DIR / project
    content = f"""# Goals: {project}

## 目标层级
1. 顶层目标：...
2. 子目标：...

## 反目标（不达成什么）
- 不做...
- 不触及...
"""
    out = proj_dir / "goals.md"
    safe_write(out, content, approved_by)
    return out


def reduce_to_core(project: str, approved_by: str) -> Path:
    """步骤3: 层层删，规约到不能再删的一句话核心 + 正交基底。"""
    proj_dir = ARCH_DIR / project
    content = f"""# Core: {project}

**规约到不能规约的核心**：（一句话，删无可删）

**为什么是这个而不是别的**：
- 保留了：...
- 砍掉了：...（为什么）

**正交基底**：（核心由哪几个独立维度构成）
- 基底1：...
- 基底2：...
"""
    out = proj_dir / "core.md"
    safe_write(out, content, approved_by)
    return out


def expose_archetype(project: str, approved_by: str) -> Path:
    """步骤4: 暴露产出形态和结构模板。"""
    proj_dir = ARCH_DIR / project
    content = f"""# Archetype: {project}

**产出形态**：report / demo / pipeline / standard / deck ...

**结构模板**：（产出由哪些部分组成，顺序是什么）

**参考模式**：（是否复用 patterns.md 中的已有模式）
"""
    out = proj_dir / "archetype.md"
    safe_write(out, content, approved_by)
    return out


def evaluate_complexity(project: str, approved_by: str) -> Path:
    """步骤5: 多维度量纲评估（预估值，实际值留空）。"""
    proj_dir = ARCH_DIR / project
    content = f"""# Complexity: {project}

| 维度 | 预估值 | 实际值（closure填写） | 偏差 |
|------|--------|---------------------|------|
| 时间 | O(?) | | |
| 认知负荷 | O(?) | | |
| 概念密度 | O(?) | | |
| Worker 需求 | ? 个 | | |
| 补丁轮次 | ? 轮 | | |
"""
    out = proj_dir / "complexity.md"
    safe_write(out, content, approved_by)
    return out


def write_closure(project: str, approved_by: str,
                  actual_time: str = "",
                  actual_patches: str = "",
                  pitfalls: list[str] | None = None,
                  pattern_proposals: list[str] | None = None,
                  antipattern_proposals: list[str] | None = None) -> tuple[Path, list[Path]]:
    """
    收尾: 必须产出 closure.md。同时写好对应 drafts。
    返回 (closure_path, list_of_draft_paths)
    """
    proj_dir = ARCH_DIR / project
    pitfalls = pitfalls or []
    pattern_proposals = pattern_proposals or []
    antipattern_proposals = antipattern_proposals or []
    drafts_written: list[Path] = []

    # 1. 填充 closure
    content = f"""# Closure: {project}

## 复杂度偏差（回填 complexity.md）
| 维度 | 预估 | 实际 | 偏差原因 |
|------|------|------|---------|
| 时间 | O(?) | {actual_time or "O(?)"} | ... |
| 补丁轮次 | ?轮 | {actual_patches or "?轮"} | ... |

## 本次踩的坑（一句话一条）
"""
    for i, p in enumerate(pitfalls, 1):
        content += f"{i}. {p}\n"
    if not pitfalls:
        content += "1. 未记录明显坑点\n"

    content += "\n## 可提炼的模式（MERGE-PROPOSAL）\n"
    if pattern_proposals:
        for pp in pattern_proposals:
            content += f"- [ ] `pattern-{pp}.md`:（一句话描述，draft已写好）\n"
    else:
        content += "- [ ] 无新模式可提炼\n"

    content += "\n## 应记录的反模式（MERGE-PROPOSAL）\n"
    if antipattern_proposals:
        for ap in antipattern_proposals:
            content += f"- [ ] `anti-pattern-{ap}.md`:（一句话描述踩的坑，draft已写好）\n"
    else:
        content += "- [ ] 无新反模式\n"

    content += "\n## 废弃的模式/反模式\n- （如果本次实战证明某个已有模式/反模式不对，在这里标注）\n"

    closure_path = proj_dir / "closure.md"
    safe_write(closure_path, content, approved_by)

    # 2. 同时写好 pattern drafts
    for pp in pattern_proposals:
        draft = DRAFTS_DIR / f"pattern-{pp}.md"
        dcontent = f"""# Pattern Proposal: {pp}
- 来自项目: {project}
- closure中的MERGE-PROPOSAL已标记
- 适用：...
- 结构：...
- 正交性验证：...
"""
        draft.write_text(dcontent, encoding="utf-8")
        drafts_written.append(draft)

    # 3. 同时写好 anti-pattern drafts
    for ap in antipattern_proposals:
        draft = DRAFTS_DIR / f"anti-pattern-{ap}.md"
        dcontent = f"""# Anti-Pattern Proposal: {ap}
- 来自项目: {project}
- 症状：...
- 根因：...
- 怎么避：...
"""
        draft.write_text(dcontent, encoding="utf-8")
        drafts_written.append(draft)

    return closure_path, drafts_written


# ─── Research Mode: 3+1 skill ───

def pattern_mining(project: str, pattern_name: str) -> Path:
    """触发：closure 自动触发。
    产出：drafts/pattern-*.md
    """
    draft = DRAFTS_DIR / f"pattern-{pattern_name}.md"
    content = f"""# Pattern Proposal: {pattern_name}
- 来自项目: {project}
- 适用：...
- 结构：...
- 正交性验证：...
"""
    draft.write_text(content, encoding="utf-8")
    print(f"[Skeleton] Pattern draft: {draft}")
    return draft


def anti_pattern_log(project: str, antipattern_name: str,
                     symptom: str = "", cause: str = "", avoid: str = "") -> Path:
    """触发：closure 自动触发 或 World 报告架构违规时。
    产出：drafts/anti-pattern-*.md
    """
    draft = DRAFTS_DIR / f"anti-pattern-{antipattern_name}.md"
    content = f"""# Anti-Pattern: {antipattern_name}
- 来自项目: {project}
- 症状: {symptom or "..."}
- 根因: {cause or "..."}
- 怎么避: {avoid or "..."}
"""
    draft.write_text(content, encoding="utf-8")
    print(f"[Skeleton] Anti-pattern draft: {draft}")
    return draft


def complexity_recal(project: str, actuals: dict[str, str]) -> Path:
    """
    触发：closure 自动触发。
    产出：drafts/audit-*.md 记录校准。
    """
    stamp = datetime.now().strftime("%Y%m%d")
    draft = DRAFTS_DIR / f"audit-{project}-{stamp}.md"
    lines = [f"# Complexity Recalibration: {project}\n"]
    for dim, val in actuals.items():
        lines.append(f"- {dim}: 预估 vs 实际 = {val}\n")
    draft.write_text("".join(lines), encoding="utf-8")
    print(f"[Skeleton] Complexity audit: {draft}")
    return draft


def triple_scan() -> Path | None:
    """
    触发：每完成3个项目自动运行。
    产出：drafts/audit-scan-N.md
    
    返回 None 如果不满足3个项目。
    """
    projects = [d.name for d in ARCH_DIR.iterdir() if d.is_dir()]
    n = len(projects)
    if n == 0 or n % 3 != 0:
        print(f"[Skeleton] triple_scan skipped: {n} projects (need multiple of 3)")
        return None

    scan_id = n // 3
    draft = DRAFTS_DIR / f"audit-scan-{scan_id}.md"

    # 汇总 complexity 偏差
    lines = [f"# Triple-Scan #{scan_id} ({n} projects)\n\n"]
    lines.append("## Complexity 偏差汇总\n\n")
    for proj in projects:
        cfile = ARCH_DIR / proj / "complexity.md"
        if cfile.exists():
            txt = cfile.read_text(encoding="utf-8")
            lines.append(f"### {proj}\n{txt[:500]}...\n\n")

    # patterns.md 使用率（简单计数）
    lines.append("## Patterns usage\n\n")
    if PATTERNS_FILE.exists():
        ptxt = PATTERNS_FILE.read_text(encoding="utf-8")
        matches = re.findall(r"##\s+(.+)", ptxt)
        lines.append(f"Total patterns: {len(matches)}\n")
        for m in matches:
            lines.append(f"- {m.strip()}\n")
    else:
        lines.append("(no patterns.md yet)\n")

    draft.write_text("".join(lines), encoding="utf-8")
    print(f"[Skeleton] Triple-scan: {draft}")
    return draft


# ─── CLI ───

def run_campaign(project: str, raw_need: str, approved_by: str) -> None:
    """运行完整 Campaign 5步。"""
    print(f"\n[Skeleton] Campaign start: {project}\n")
    capture_intent(project, raw_need, approved_by)
    decompose_goal(project, approved_by)
    reduce_to_core(project, approved_by)
    expose_archetype(project, approved_by)
    evaluate_complexity(project, approved_by)
    print(f"[Skeleton] Campaign 5步完成: {ARCH_DIR / project}")


def run_closure(project: str, approved_by: str,
                **kwargs) -> None:
    """运行收尾，产出 closure.md + drafts。"""
    print(f"\n[Skeleton] Closure start: {project}\n")
    closure_path, drafts = write_closure(project, approved_by, **kwargs)
    # 自动试触发 triple-scan
    triple_scan()
    print(f"[Skeleton] Closure 完成: {closure_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Skeleton Bee — 总工程师/CAO")
    sub = parser.add_subparsers(dest="cmd")

    # campaign
    p_camp = sub.add_parser("campaign", help="运行 5步 Campaign")
    p_camp.add_argument("project", help="项目名")
    p_camp.add_argument("--need", required=True, help="原始需求")
    p_camp.add_argument("--by", dest="approved_by", required=True, help="批准人")

    # closure
    p_close = sub.add_parser("closure", help="运行收尾")
    p_close.add_argument("project", help="项目名")
    p_close.add_argument("--by", dest="approved_by", required=True, help="批准人")
    p_close.add_argument("--time", default="", help="实际时间")
    p_close.add_argument("--patches", default="", help="实际补丁轮次")
    p_close.add_argument("--pitfalls", nargs="*", default=[], help="踩的坑")
    p_close.add_argument("--patterns", nargs="*", default=[], help="模式提案")
    p_close.add_argument("--antipatterns", nargs="*", default=[], help="反模式提案")

    # triple-scan
    sub.add_parser("triple-scan", help="运行三倍扫描")

    args = parser.parse_args()

    if args.cmd == "campaign":
        run_campaign(args.project, args.need, args.approved_by)
    elif args.cmd == "closure":
        run_closure(
            args.project, args.approved_by,
            actual_time=args.time,
            actual_patches=args.patches,
            pitfalls=args.pitfalls,
            pattern_proposals=args.patterns,
            antipattern_proposals=args.antipatterns
        )
    elif args.cmd == "triple-scan":
        triple_scan()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
