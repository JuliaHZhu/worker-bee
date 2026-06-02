---
name: learn-from-doing
description: Extract structured learning from session history. Dual-layer analysis — objective facts in objective/, inferential analysis in inference/. Write to wiki learn-from-doing/ space.
trigger: learn, 总结, analyze session, 回顾, session analysis, learn from doing, 学习记录, 执行分析, 复盘
tools:
  - fs_read_file
  - fs_write_file
  - fs_search_files
  - sys_terminal
---

# Learn-From-Doing

> "从执行中学习，但不让学习漂移。"

Extract, structure, and persist learning from worker-bee sessions into the wiki.
This skill produces **dual-layer records**: objective facts are immutable; inferential
analysis is explicitly speculative and tied to user-profile context.

## When This Skill Activates

- User asks to summarize, review, or analyze a session
- User asks to "learn from doing"
- User says something didn't meet expectations and wants to record why
- Automated cron job triggers periodic session analysis
- User asks to update the user profile based on interaction patterns

## Wiki Location

```bash
WIKI="${WIKI_PATH:-$HOME/wiki-worker-bee}"
OBJECTIVE_DIR="$WIKI/learn-from-doing/objective"
INFERENCE_DIR="$WIKI/learn-from-doing/inference"
USER_PROFILE="$WIKI/entities/user-profile.md"
```

## Dual-Layer Architecture (CRITICAL — never mix layers)

```
session data
    │
    ├──► Objective Layer (objective/)
    │     • Immutable factual record
    │     • What happened, not why
    │     • Timestamped, traceable
    │
    └──► Inference Layer (inference/)
          • Hypothesis about user expectation
          • Mental-model reconstruction
          • Explicitly speculative — tagged with confidence
          • References concrete cultural anchors (films, games, searchable examples)
```

### Rule: Objective never drifts

Once an objective record is written, it is append-only. Corrections go in a new
objective file that references the old one. The objective layer is the ground truth.

### Rule: Inference is versioned

Inference files may be updated when new user-profile information emerges. Old
versions are moved to `_archive/` within `learn-from-doing/inference/`.

## How to Extract Session Data

Sessions live in `state.db` (SQLite, co-located with worker-bee).

Read recent sessions:
```bash
cd /path/to/worker-bee
sqlite3 state.db "SELECT id, created_at, title FROM sessions ORDER BY created_at DESC LIMIT 10;"
```

Read messages for a session:
```bash
sqlite3 state.db "SELECT role, content, tool_calls, created_at FROM messages WHERE session_id = '<SID>' ORDER BY id;"
```

Read active goal for a session:
```bash
sqlite3 state.db "SELECT content FROM goals WHERE session_id = '<SID>' AND status = 'active' ORDER BY id DESC LIMIT 1;"
```

## Analysis Procedure

### Step 1: Orient

Before analyzing ANY session:
1. Read `$WIKI/SCHEMA.md`
2. Read `$WIKI/index.md`
3. Read `$WIKI/entities/user-profile.md` (if exists)
4. Read last 20 lines of `$WIKI/log.md`

### Step 2: Read Session

Use `sys_terminal` with `sqlite3` to extract the full message history of the target
session(s). Default target: the most recently completed session. User may specify a
session ID.

### Step 3: Write Objective Record

Create `$OBJECTIVE_DIR/YYYY-MM-DD-session-{id}.md`

**Required frontmatter:**
```yaml
---
title: "Session {id} — {one-line summary}"
date: YYYY-MM-DD
session_id: {id}
type: objective-record
tags: [from SCHEMA taxonomy, e.g., skill-test, deck, halt]
sources: [raw/sessions/{id}.md]
confidence: high
---
```

**Required sections (write in this order):**

```markdown
## 原始目的
用户发起这个 session 时想要达成什么。引用用户的第一条消息原文。

## LLM 理解
Agent 是如何理解这个请求的。引用 system prompt 注入后的实际输入（如果有 goal injection，注明）。

## 执行内容
按时间线列出 tool calls 和关键决策点：
- [timestamp] tool_call / user_feedback / agent_response
- 最终状态：success / halt / error

## 用户评价
用户在 session 中给出的显式反馈（如果有）。包括：
- 直接评价（"很好"、"不对"、"漂移了"）
- 隐式评价（重新表述需求、追加约束、改变话题）
- 最终是否达成目标

## 关联 Skill
这次执行涉及了哪些 skills，每个 skill 的表现如何（工具调用次数、是否触发、是否足够）。

## 数据质量备注
- 是否有信息缺失（如用户未完整表达意图）
- 是否有外部依赖失败（网络、API）
```

**Constraint:** The objective record contains ONLY facts observable from the session
transcript. No speculation. No mind-reading. If a user's intent is unclear, state
"用户意图未明确表达" rather than guessing.

### Step 4: Write Inference Record

Create `$INFERENCE_DIR/YYYY-MM-DD-session-{id}-inference.md`

**Required frontmatter:**
```yaml
---
title: "Inference for Session {id}"
date: YYYY-MM-DD
session_id: {id}
type: inference
tags: [user-expectation, mental-model, skill-evolution]
confidence: high | medium | low
anchors: [list of concrete cultural references used]
---
```

**Required sections (write in this order):**

```markdown
## 用户预期分析

### 显式预期
用户明确说出的成功标准。

### 隐式预期（假设）
用户没有明说但被暗示的期望。每个假设必须标注置信度：
- "用户可能期望..." ^[medium]

## 落差诊断

如果执行不符合预期，分析落差发生在哪一层：
- **意图层**：用户表达了 A，LLM 理解为 B
- **能力层**：LLM 理解正确，但 deck/tools  insufficient
- **品味层**：输出功能正确，但风格/粒度/形式不符合用户偏好
- **边界层**：用户期望的 scope 与 LLM 实际处理的 scope 不一致

## 脑内画面推测

结合 `[[entities/user-profile]]`，推测用户脑中可能存在的参照画面。

### 画面描述
用 2-3 句话描述用户可能想象的工作流/交互/结果。

### 具体文化锚点
必须给出 **人类和 AI 都能方便在网上公开搜到** 的具体例子：
- **电影/动画**: 《xxx》(年份) 中的 xxx 场景
- **游戏**: xxx 中的 xxx 机制/界面
- **软件/工具**: xxx 的 xxx 功能
- **建筑/空间**: xxx 的 xxx 设计
- **历史/现实**: xxx 的 xxx 流程

至少提供 2 个锚点。锚点的作用是让抽象的"用户预期"变成可讨论、可验证的具体参照物。

## User-Profile 关联

这次交互对 user profile 的哪些假设提供了支持或挑战：
- 支持的假设：...
- 挑战的假设：...
- 需要补充的用户画像维度：...

## 修正建议

下次遇到同类请求时，agent 应该：
1. ...
2. ...
3. ...

如果建议涉及 skill 修改，注明应更新哪个 skill 文件。
```

### Step 5: Update Navigation

1. Add objective record to `index.md` under a new section `## Learn-From-Doing`
2. Add inference record to `index.md`
3. Append to `log.md`: `## [YYYY-MM-DD] learn-from-doing | Session {id}`
4. If user-profile insights emerged, update `entities/user-profile.md`

### Step 6: Report

Summarize to user:
- Objective record path
- Inference record path
- Key insight (1-2 sentences)
- Any skill or deck changes suggested

## User Profile Template

When `entities/user-profile.md` does not exist, create it with this structure:

```markdown
---
title: User Profile
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity
tags: [user, profile]
---

# User Profile

## Identity
- Name / handle:
- Role / background:
- Communication style:

## Core Beliefs (stable)
- 关于 skill 设计的信念：...
- 关于工程组织的信念：...

## Preferences (evolving)
- 输出格式偏好：...
- 交互深度偏好：...
- 边界偏好（何时希望agent自主，何时希望确认）：...

## Mental-Model Anchors（文化参照物）
- 电影/游戏/作品：...
- 这些锚点暗示的工作流偏好：...

## Interaction Patterns（从 learn-from-doing 归纳）
- 高频请求类型：...
- 常见落差模式：...
- 有效触发词：...

## Open Questions（待验证的假设）
- ...
```

## Batch / Automated Mode

When triggered by cron or user requests analysis of multiple sessions:

1. List all sessions from `state.db` not yet represented in `learn-from-doing/objective/`
2. For each: run Steps 3-5 above
3. After batch: synthesize a `concepts/session-patterns.md` page if patterns emerge
4. Update `log.md` with batch summary

## Pitfalls

- **NEVER mix objective and inference in the same file.** This is the primary anti-pattern.
- **NEVER update an objective record after creation.** New facts → new objective file.
- **Inference without anchors is weak.** Every mental-model hypothesis needs a concrete, searchable cultural reference.
- **Don't over-anchor.** 2-3 strong anchors beat 10 vague ones.
- **User profile is hypothesis, not fact.** Tag everything in it as confidence-mediated.
- **If user explicitly says "我只是试试" or "不用记录",** skip the analysis. Respect the signal.
