#!/usr/bin/env python3
"""Batch learn-from-doing: analyze sessions and write to wiki.

Usage:
    python batch_learn.py [--wiki PATH] [--limit N] [--session SID]

Environment:
    WIKI_PATH    Override wiki directory
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ── Config ──
HERMES_LITE_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = HERMES_LITE_DIR / "config.json"
DEFAULT_DB = HERMES_LITE_DIR / "state.db"


def load_llm_config():
    """Read hermes-lite config.json for API settings."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    # Fallback: env vars
    key = os.environ.get("ARKCODE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return {
            "provider": "anthropic",
            "model": os.environ.get("MODEL", "kimi-k2.6"),
            "api_key": key,
            "base_url": os.environ.get("BASE_URL", "https://ark.cn-beijing.volces.com/api/coding"),
        }
    return None


def get_wiki_path():
    return Path(os.environ.get("WIKI_PATH", Path.home() / "wiki-hermes-lite"))


def get_client(config):
    """Return an API client based on provider."""
    provider = config.get("provider", "anthropic")
    if provider == "openai":
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package not installed: pip install openai")
        return OpenAI(api_key=config["api_key"], base_url=config.get("base_url"))
    else:
        try:
            from anthropic import Anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed: pip install anthropic")
        return Anthropic(api_key=config["api_key"], base_url=config.get("base_url"))


def llm_call(client, config, prompt, max_tokens=2048):
    """Simple LLM call without tools."""
    provider = config.get("provider", "anthropic")
    model = config.get("model", "claude-sonnet-4")
    if provider == "openai":
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""
    else:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        texts = []
        for block in resp.content:
            if hasattr(block, "text"):
                texts.append(block.text)
        return "\n".join(texts)


def get_sessions(db_path, limit=10, exclude_ids=None):
    """List sessions from state.db, optionally excluding already-analyzed ones."""
    if not Path(db_path).exists():
        return []
    conn = sqlite3.connect(db_path)
    sql = "SELECT id, created_at, title FROM sessions ORDER BY created_at DESC LIMIT ?"
    rows = conn.execute(sql, (limit,)).fetchall()
    conn.close()
    if exclude_ids:
        rows = [r for r in rows if r[0] not in exclude_ids]
    return rows


def get_session_messages(db_path, session_id):
    """Fetch full message history for a session."""
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT role, content, tool_calls, created_at FROM messages WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    conn.close()
    return rows


def already_analyzed(wiki_path, session_id):
    """Check if objective record already exists for this session."""
    obj_dir = wiki_path / "learn-from-doing" / "objective"
    if not obj_dir.exists():
        return False
    pattern = f"*session-{session_id}.md"
    return any(obj_dir.glob(pattern))


def build_objective_prompt(session_id, created_at, title, goal, messages):
    """Build prompt for objective-layer analysis."""
    msg_lines = []
    for role, content, tool_calls, ts in messages:
        tc = json.loads(tool_calls) if tool_calls else None
        tc_str = f" [tools: {tc}]" if tc else ""
        msg_lines.append(f"[{role}]{tc_str}\n{content[:500]}{'...' if len(content) > 500 else ''}")

    msg_text = "\n\n---\n\n".join(msg_lines)

    prompt = f"""You are a session archivist. Produce an OBJECTIVE record — facts only, no speculation.

Session: {session_id}
Created: {created_at}
Title: {title or "(none)"}
Active Goal: {goal or "(none)"}

MESSAGES:
{msg_text}

Write the objective record in this exact format:

```markdown
---
title: "Session {session_id} — <one-line summary>"
date: {datetime.now().strftime('%Y-%m-%d')}
session_id: {session_id}
type: objective-record
tags: [<2-4 tags from: skill-test, deck, registry, halt, user-feedback, tool-use>]
sources: [raw/sessions/{session_id}.md]
confidence: high
---

## 原始目的
<quote the user's first message>

## LLM 理解
<how the agent interpreted the request>

## 执行内容
- <timeline of key tool calls / decisions>
- Final state: success / halt / error

## 用户评价
<explicit and implicit feedback from user during session>

## 关联 Skill
<which skills were involved and how they performed>

## 数据质量备注
<any missing info or external failures>
```

Rules:
- Only facts from the transcript. No mind-reading.
- If user intent is unclear, state "用户意图未明确表达".
- Use Chinese for the body, as the user communicates in Chinese.
"""
    return prompt


def build_inference_prompt(session_id, objective_text, user_profile_text):
    """Build prompt for inference-layer analysis."""
    prompt = f"""You are an interaction analyst. Given the OBJECTIVE record below, produce an INFERENCE record.

The inference record is EXPLICITLY SPECULATIVE. It attempts to reconstruct the user's mental model.

OBJECTIVE RECORD:
{objective_text}

USER PROFILE:
{user_profile_text or "(no user profile yet)"}

Write the inference record in this exact format:

```markdown
---
title: "Inference for Session {session_id}"
date: {datetime.now().strftime('%Y-%m-%d')}
session_id: {session_id}
type: inference
tags: [user-expectation, mental-model, skill-evolution]
confidence: medium
anchors: [<list concrete cultural references>]
---

## 用户预期分析

### 显式预期
...

### 隐式预期（假设）
- "..." ^[medium]

## 落差诊断
- 意图层 / 能力层 / 品味层 / 边界层

## 脑内画面推测

### 画面描述
2-3 sentences describing the user's imagined workflow.

### 具体文化锚点
- **电影/动画**: 《xxx》(年份) 中的 xxx 场景
- **游戏**: xxx 中的 xxx 机制
- **软件/工具**: xxx 的 xxx 功能
- **建筑/空间**: xxx 的 xxx 设计
- **历史/现实**: xxx 的 xxx 流程
(At least 2 anchors. Must be publicly searchable online.)

## User-Profile 关联
- 支持的假设：...
- 挑战的假设：...
- 需要补充的用户画像维度：...

## 修正建议
1. ...
2. ...
3. ...
```

Rules:
- EVERY hypothesis about user mental state must be tagged with confidence.
- EVERY "脑内画面" must anchor to a concrete, searchable cultural reference (film, game, software, architecture, historical process).
- Use Chinese for the body.
- Be bold in speculation, but label it as such.
"""
    return prompt


def sanitize_filename(s):
    """Make a string safe for use in a filename."""
    return re.sub(r'[^\w\-_.]', '_', s)[:50]


def update_index(wiki_path, obj_file, inf_file, session_id, date_str):
    """Add new learn-from-doing entries to index.md."""
    index_path = wiki_path / "index.md"
    if not index_path.exists():
        return
    content = index_path.read_text(encoding="utf-8")

    obj_entry = f"- [[{obj_file.stem}]] | Objective record for session {session_id}"
    inf_entry = f"- [[{inf_file.stem}]] | Inference analysis for session {session_id}"

    # Inject under ## Learn-From-Doing if exists
    if "## Learn-From-Doing" in content:
        lines = content.splitlines()
        new_lines = []
        inserted_obj = False
        inserted_inf = False
        for line in lines:
            new_lines.append(line)
            if line.strip() == "## Learn-From-Doing":
                new_lines.append("")
                new_lines.append("### Objective Records")
                new_lines.append(obj_entry)
                new_lines.append("")
                new_lines.append("### Inference Records")
                new_lines.append(inf_entry)
                inserted_obj = True
                inserted_inf = True  # noqa: F841
        if inserted_obj:
            content = "\n".join(new_lines)
    else:
        content += f"\n## Learn-From-Doing\n\n### Objective Records\n{obj_entry}\n\n### Inference Records\n{inf_entry}\n"

    # Update date and count
    content = re.sub(r"Last updated: \d{4}-\d{2}-\d{2}", f"Last updated: {date_str}", content)
    # Bump count roughly
    count_match = re.search(r"Total pages: (\d+)", content)
    if count_match:
        new_count = int(count_match.group(1)) + 2
        content = re.sub(r"Total pages: \d+", f"Total pages: {new_count}", content)

    index_path.write_text(content, encoding="utf-8")


def append_log(wiki_path, date_str, session_id):
    log_path = wiki_path / "log.md"
    if log_path.exists():
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n## [{date_str}] learn-from-doing | Session {session_id}\n")
            f.write("- Generated objective and inference records\n")


def analyze_session(session_id, db_path, wiki_path, client, config):
    """Run dual-layer analysis for one session and write to wiki."""
    messages = get_session_messages(db_path, session_id)
    if not messages:
        print(f"  ⚠️ No messages for session {session_id}")
        return False

    # Fetch metadata
    conn = sqlite3.connect(db_path)
    meta = conn.execute(
        "SELECT created_at, title FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    conn.close()
    created_at, title = meta if meta else ("", "")
    goal = None  # goal system removed; tasks replace it

    print(f"  → Analyzing session {session_id} ({len(messages)} messages)...")

    # Objective layer
    obj_prompt = build_objective_prompt(session_id, created_at, title, goal, messages)
    obj_text = llm_call(client, config, obj_prompt, max_tokens=2048)

    # Extract markdown from response
    obj_match = re.search(r"```markdown\n(.*?)\n```", obj_text, re.DOTALL)
    if obj_match:
        obj_text = obj_match.group(1)

    date_str = datetime.now().strftime("%Y-%m-%d")
    obj_dir = wiki_path / "learn-from-doing" / "objective"
    obj_dir.mkdir(parents=True, exist_ok=True)
    obj_file = obj_dir / f"{date_str}-session-{session_id}.md"
    obj_file.write_text(obj_text, encoding="utf-8")
    print(f"    ✅ Objective: {obj_file.name}")

    # Inference layer
    user_profile_path = wiki_path / "entities" / "user-profile.md"
    user_profile_text = user_profile_path.read_text(encoding="utf-8") if user_profile_path.exists() else ""
    inf_prompt = build_inference_prompt(session_id, obj_text, user_profile_text)
    inf_text = llm_call(client, config, inf_prompt, max_tokens=2048)

    inf_match = re.search(r"```markdown\n(.*?)\n```", inf_text, re.DOTALL)
    if inf_match:
        inf_text = inf_match.group(1)

    inf_dir = wiki_path / "learn-from-doing" / "inference"
    inf_dir.mkdir(parents=True, exist_ok=True)
    inf_file = inf_dir / f"{date_str}-session-{session_id}-inference.md"
    inf_file.write_text(inf_text, encoding="utf-8")
    print(f"    ✅ Inference: {inf_file.name}")

    # Update navigation
    update_index(wiki_path, obj_file, inf_file, session_id, date_str)
    append_log(wiki_path, date_str, session_id)

    return True


def main():
    parser = argparse.ArgumentParser(description="Batch learn-from-doing analysis")
    parser.add_argument("--wiki", help="Wiki directory path")
    parser.add_argument("--db", help="State DB path", default=str(DEFAULT_DB))
    parser.add_argument("--limit", type=int, default=5, help="Max sessions to analyze")
    parser.add_argument("--session", help="Analyze specific session ID only")
    args = parser.parse_args()

    wiki_path = Path(args.wiki) if args.wiki else get_wiki_path()
    db_path = args.db

    if not Path(db_path).exists():
        print(f"❌ State DB not found: {db_path}")
        print("   Hermes-lite must be run at least once to create state.db.")
        sys.exit(1)

    config = load_llm_config()
    if not config:
        print("❌ No LLM config found. Run hermes-lite setup first.")
        sys.exit(1)

    client = get_client(config)

    # Determine which sessions to analyze
    if args.session:
        sessions = [(args.session, "", "")]
    else:
        # Find already-analyzed sessions
        obj_dir = wiki_path / "learn-from-doing" / "objective"
        analyzed = set()
        if obj_dir.exists():
            for f in obj_dir.glob("*.md"):
                m = re.search(r"session-([a-zA-Z0-9_-]+)", f.name)
                if m:
                    analyzed.add(m.group(1))
        sessions = get_sessions(db_path, limit=args.limit * 3, exclude_ids=analyzed)
        sessions = sessions[:args.limit]

    if not sessions:
        print("📭 No new sessions to analyze.")
        return

    print(f"🔍 Found {len(sessions)} session(s) to analyze")
    analyzed_count = 0
    for sid, created_at, title in sessions:
        try:
            if analyze_session(sid, db_path, wiki_path, client, config):
                analyzed_count += 1
        except Exception as e:
            print(f"  ❌ Error analyzing {sid}: {e}")

    print(f"\n✅ Done. Analyzed {analyzed_count} session(s).")
    print(f"   Wiki: {wiki_path}")


if __name__ == "__main__":
    main()
