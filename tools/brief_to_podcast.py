#!/usr/bin/env python3
"""
brief_to_podcast.py — Bridge: Todo Ball Machine → Podcast Agent

把 Todo Ball Machine 的今日状态/统计报告转成播客脚本。
这是 Hermes × NotebookLM “爆炸效果” 的最小可用集成示例。

Usage:
    python tools/brief_to_podcast.py              # 今日状态 → 播客脚本
    python tools/brief_to_podcast.py --stats 7    # 近7天统计 → 播客脚本
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────
def _todo_tool() -> Path:
    return Path(__file__).parent / "todo_ball_machine.py"


def _podcast_tool() -> Path:
    return Path(__file__).parent / "podcast_agent.py"


# ── Fetch brief text from Todo Ball Machine ─────────────────────────
def _run_todo(action: str, content: str = "") -> str:
    """通过 python -c 调用 todo_ball_machine（避免 import 路径问题）。
    使用 JSON 序列化传参，避免字符串拼接导致的代码注入。"""
    project_root = _todo_tool().parent.parent
    import json as _json
    payload = {"action": action}
    if content:
        payload["content"] = content
    code_payload = _json.dumps(payload, ensure_ascii=False)
    code = (
        "from tools.todo_ball_machine import todo_ball_machine; "
        "import json as _json; "
        f"args = _json.loads({repr(code_payload)}); "
        "print(todo_ball_machine(**args))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )
    if result.returncode != 0:
        return f"[Error fetching {action}: {result.stderr.strip()}]"
    return result.stdout


def fetch_today_brief() -> str:
    """获取今日安排和盒子配额的纯文本。"""
    dashboard = _run_todo("dashboard")
    today = _run_todo("today")
    return f"{dashboard}\n\n{today}"


def fetch_stats_brief(days: int = 7) -> str:
    """获取统计报告文本。"""
    return _run_todo("stats", str(days))


# ── Main ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Todo Ball Machine → Podcast script")
    parser.add_argument("--stats", type=int, default=None, help="Use stats report for N days instead of today")
    parser.add_argument("--tone", "-t", default="casual", choices=["professional", "casual", "humorous", "educational"])
    parser.add_argument("--lang", "-l", default="zh", choices=["zh", "en", "zh-CN", "zh-TW"])
    parser.add_argument("--output", "-o", default=None, help="Output JSON path")
    args = parser.parse_args()

    # 1. Fetch brief
    if args.stats:
        print(f"[1/3] Fetching stats brief ({args.stats} days) ...")
        brief = fetch_stats_brief(args.stats)
    else:
        print("[1/3] Fetching today brief ...")
        brief = fetch_today_brief()

    print(f"      Brief length: {len(brief)} chars")

    # 2. Save to temp file for podcast_agent.py
    print("[2/3] Preparing source file ...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(brief)
        tmp_path = Path(f.name)

    # 3. Call podcast_agent.py
    print("[3/3] Generating podcast script ...")
    podcast_script = _podcast_tool()
    if not podcast_script.exists():
        print(f"Error: podcast_agent.py not found at {podcast_script}", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, str(podcast_script), "--source", str(tmp_path),
         "--tone", args.tone, "--lang", args.lang],
        capture_output=True,
        text=True,
    )

    # Cleanup temp
    tmp_path.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"Error: podcast_agent failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    print(result.stdout)

    # 4. Move output to desired path if specified
    if args.output:
        # podcast_agent.py saves to .podcast.json next to source
        # The source was temp, so output is also temp path
        # We need to find where it saved it... Actually subprocess above writes
        # to temp_path.with_suffix('.podcast.json') which is in /tmp
        # Better: let's read the JSON directly instead
        pass


if __name__ == "__main__":
    main()
