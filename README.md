# Hermes Lite

A lightweight, minimal AI agent framework inspired by [Hermes Agent](https://github.com/nousresearch/hermes-agent). Built for developers who want the core agentic architecture without the production-grade complexity.

## 1. What We Are Doing

We are building an agent that **procures its tools before it acts**.

Most agents hand a massive tool list to the LLM and hope it picks the right ones. That is unstable — the LLM gets confused, picks wrong, corrects, tries again. We replaced this with the **Deck** architecture:

1. **Select** — LLM picks relevant skills from the library
2. **Procure** — Collect all tools declared by those skills into a Deck
3. **Execute** — The agent draws **only** from the Deck. Nothing else exists.

If the task cannot be completed with the Deck → **halt**. The first procurement was already as broad as possible. A second try with the same tools is unlikely to succeed. The approach itself may be wrong — time for a human.

**Math (可约分):**
```
Let S  = set of skills selected by LLM
Let T(s) = tools declared by skill s

Deck = ⋃_{s ∈ S} T(s)   (union, deduplicated)
```

Even if skill A routes to skill B at runtime, B.tools is already in the Deck if B was in S. The tool space of nested skills collapses to a flat, immutable set before execution.

---

## 2. Where This Problem Came From

### The Spark

We started by looking at Hermes Agent — a full-featured agent with skills, subagents, and multi-platform delivery. We were curious: **how does it organize tools?**

Hermes uses a directory tree of skills, but there is **no trigger field**. Skills are matched by an index or subagent, not by a declarative contract. This raised the question: **if skill names are ambiguous, how does the system know which skill to load?**

### The Realization

A **skill is not a tool set**. A skill is a **contract** — it declares:
- **When** to use it (`trigger`)
- **What** tools it needs (`tools`)
- **How** to use them (the body / instructions)

But even with precise skills, the LLM still sees too many tools during execution. We needed a **boundary**.

### The Analogy

> *"活用字典，粗筛粗，细筛细，先组卡组，再抽卡。"*
>
> Like gathering tools before making something. You do not go back to the store mid-cooking. If the ingredients you bought are insufficient, the recipe itself may be wrong.

---

## 3. What Comes Next: The "Design Eye"

Hermes Lite now has a precise hand. Next, we are building a **design eye** — the ability to turn vague intent into concrete, executable plans.

### The Pipeline

```
模糊想法
    │
    ▼
┌─────────────────┐
│  /clarify       │  "我们到底在解决什么？"
│  意图澄清        │  输出: 约束清单 + 成功标准
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  /explore       │  "有哪些可行的路径？"
│  方案探索        │  输出: 2-3 个候选方案 + 权衡分析
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  /decide        │  "选哪条路？为什么？"
│  决策锚定        │  输出: 决策记录 + 风险评估
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  /validate      │  "做出来对不对？"
│  实现验证        │  输出: 验证报告 + 偏差分析
└────────┬────────┘
         │
         ▼
    回到 /clarify（循环）
```

### Why Game Design?

As agents become mainstream, people will immediately face the same problem game studios face: **the communication gap between designer and implementer**.

| Designer says | Implementer hears | The real problem |
|---------------|-------------------|------------------|
| "This skill should feel good" | ??? | "Good" was never translated to measurable specs |
| "Enemies should feel oppressive" | Tune AI behavior tree | "Oppressive" was never mapped to pacing, sound, or scale |
| "The gameplay needs depth" | Add more systems | "Depth" was never defined as cognitive load vs. strategy space |
| "There's a bug here" | Fix it | The fix breaks the intended feel because the design intent was invisible |

We will build skills that **translate subjective intent into objective constraints**, so the agent (and the human) can verify whether the implementation matches the vision.

### Upcoming Skills

| Skill | Purpose |
|-------|---------|
| `game-feel-clarifier` | Turn "爽 / 压迫感 / 节奏感" into engineering metrics |
| `implementation-impact-check` | Analyze side effects before fixing a bug |
| `design-clarify` | General-purpose intent clarification for any domain |

---

## Key Differences from Hermes

| Dimension | Hermes | Hermes Lite |
|-----------|--------|-------------|
| Lines of code | ~35,900 | **~1,700** |
| Platforms | 15+ | Linux CLI (Feishu/Discord webhook opt-in) |
| Registry | Toolset-centric, static config | **Tag/category + dynamic loading** |
| Skill trigger | Passive listing (LLM pulls) | **Active matching (system pushes)** |
| Tool boundary | Macro toolsets (4–40 tools) | **Immutable Deck per task (1–5 tools)** |
| Message format | Unified OpenAI internally | Dual protocol (Anthropic + OpenAI) |
| Design phase | N/A | **/clarify → /explore → /decide → /validate** |

---

## Registry Redesign: Clarity is the Boundary

Every registered function follows strict naming conventions:

```python
registry.register(
    name="fs_read_file",           # domain_action_object — no ambiguity
    description="Read a text file with pagination. Use when inspecting source code, configs, or logs.",
    parameters={...},
    handler=fs_read_file,
    tags=["filesystem", "read"],
    category="filesystem"
)
```

**Naming convention:** `{domain}_{action}_{object}`
- `fs_read_file`, `fs_write_file`, `fs_search_files`
- `net_web_search`, `net_web_extract`
- `sys_terminal`, `agent_delegate_task`

This eliminates LLM confusion caused by vague names. The function signature — `name + description + parameters` — is the complete interface contract.

### Skill + Registry + Deck = Deterministic Navigation

```
User: "review my code"
    ↓
System matches Skill "code-review"
    ↓
Skill declares tooldeck: [fs_read_file, fs_search_files]
    ↓
Deck is built — only these 2 tools exist for this task
    ↓
Registry confirms fs_read_file = "Read local text file with pagination"
    ↓
LLM operates within 2 tools — zero ambiguity
```

**Traditional (unstable):** LLM sees 40 tools → guesses → may be wrong → corrects → unstable.  
**Hermes Lite (stable):** Skill navigates to a precise subset → Deck enforces the boundary → deterministic behavior.

---

## InfraToolSet (Platform Gating)

Skill decides "what the LLM sees." InfraToolSet decides "what is physically available."

```
┌────────────────────────────────────────────┐
│  Skill layer (AI reasoning)                │
│  code-review → [fs_read_file, fs_search]   │
├────────────────────────────────────────────┤
│  InfraToolSet layer (env gating)           │
│  linux → all tools pass                    │
│  feishu → only send_message passes         │
├────────────────────────────────────────────┤
│  Registry layer (atomic tools)             │
│  fs_read_file, send_message, ...           │
└────────────────────────────────────────────┘
```

---

## Quick Start

Hermes Lite is **project-local** — everything lives in one directory.

```bash
# 1. Clone anywhere
git clone https://github.com/JuliaHZhu/hermes-lite.git
cd hermes-lite

# 2. Install (editable, project-local)
pip install -e .

# 3. Configure (creates ./config.json — gitignored)
hermes-lite setup

# 4. Verify model
hermes-lite -m "hello"

# 5. (Optional) Verify channel
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
hermes-lite -c "hello"

# 6. Start using
hermes-lite
```

---

## Architecture

```
hermes-lite/
├── main.py              # CLI entry + command routing
├── agent.py             # AI agent loop (dual protocol)
├── deck.py              # Deck procurement + immutable tool boundary
├── registry.py          # Tool registry with rich metadata
├── skills.py            # Skill loader with trigger matching
├── memory.py            # SQLite persistence
├── infra_toolsets.py    # Platform detection and tool gating
├── DESIGN.md            # Full design evolution document
└── tools/
    ├── terminal.py      # sys_terminal
    ├── file.py          # fs_read_file, fs_write_file, fs_search_files
    ├── web.py           # net_web_search, net_web_extract
    ├── subagent.py      # agent_delegate_task
    └── send_message.py  # Feishu/Discord webhook
```

---

## License

MIT License — see [LICENSE](./LICENSE).

## Acknowledgment

Hermes Lite is derived from the architecture and design philosophy of [Hermes Agent](https://github.com/nousresearch/hermes-agent) by Nous Research. It is not affiliated with or endorsed by Nous Research.
