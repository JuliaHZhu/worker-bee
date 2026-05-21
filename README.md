# Hermes Lite

A lightweight, minimal AI agent framework inspired by [Hermes Agent](https://github.com/nousresearch/hermes-agent). Built for developers who want the core agentic architecture without the production-grade complexity.

## Philosophy

Hermes is a powerful, full-featured agent framework serving 15+ platforms with 35k+ lines of code. Hermes Lite extracts the **essential skeleton** — Registry → Tool → Skill → Agent → CLI — into ~1,700 lines of readable Python, then sharpens it with a few opinionated improvements.

## Key Differences from Hermes

| Dimension | Hermes | Hermes Lite |
|-----------|--------|-------------|
| Lines of code | ~35,900 | **~1,700** |
| Platforms | 15+ | Linux CLI (Feishu/Discord webhook opt-in) |
| Registry | Toolset-centric, static config | **Tag/category + dynamic loading** |
| Skill trigger | Passive listing (LLM pulls) | **Active matching (system pushes)** |
| Tool grouping | Macro toolsets (4–40 tools) | **Precise tooldeck per skill (1–5 tools)** |
| Message format | Unified OpenAI internally | Dual protocol (Anthropic + OpenAI) |

## Registry Redesign: Clarity is the Boundary

The registry in Hermes Lite is rebuilt around a simple conviction:

> **"Saying it clearly is itself a good boundary."**
>
> — If a name is ambiguous, the LLM will be confused. If a name is precise, the LLM needs no example.

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

This eliminates LLM confusion caused by vague names like `create_object` or `set_position`. The function signature — `name + description + parameters` — is the complete interface contract. No video demos, no sample projects needed.

### Skill + Registry = Deterministic Navigation

When Skill and Registry are both precise, the system stops "guessing" and starts "navigating":

```
User: "review my code"
    ↓
System matches Skill "code-review"
    ↓
Skill declares tooldeck: [fs_read_file, fs_search_files]
    ↓
Registry confirms fs_read_file = "Read local text file with pagination"
    ↓
LLM operates within 2 tools — zero ambiguity
```

**Traditional (unstable):** LLM sees 40 tools → guesses → may be wrong → corrects → unstable.
**Hermes Lite (stable):** Skill navigates to a precise tool subset → Registry confirms exact semantics → deterministic behavior.

> **"Saying it clearly is itself a good boundary."** — This applies to Registry names, Skill tooldecks, and trigger matching. Clarity at every layer compounds into runtime stability.

### Thread Safety & Caching

- `RLock` + monotonic generation counter for concurrent access
- LRU in-memory cache (30 s TTL) for schema lookups
- Agent-level schema cache keyed on `(tool_names, protocol, registry_generation)`

## Skill Format (Recommended)

A skill in Hermes Lite is **not** a macro toolset. It is a **curated workflow** triggered by user intent and exposing a precise tooldeck:

```markdown
---
name: code-review
description: Review code for quality, bugs, and style issues
trigger: review, code review, check code, review this, look at this code
tools:
  - fs_read_file
  - fs_search_files
  - fs_write_file
---

When reviewing code:

1. `fs_read_file` — read the target files
2. `fs_search_files` — find related definitions and usages
3. `fs_write_file` — record review comments if asked

Focus on: correctness, edge cases, naming clarity, and unnecessary complexity.
```

**Principles:**
1. **One skill = one feature**, not one domain. Prefer many small skills over few large ones.
2. **Tooldeck is explicit.** List exactly the functions the skill needs. No more, no less.
3. **Trigger is the only gate.** The system matches triggers → loads the tooldeck → injects context. LLM never selects from 100 tools.
4. **Function names are the demo.** A precise `name + description + parameters` is sufficient; no video or sample project needed.

## InfraToolSet (Platform Gating)

Hermes Lite introduces `InfraToolSet` as a separate layer from Skill:

- **Skill** decides "what should the LLM see for this conversation"
- **InfraToolSet** decides "what is physically available on this platform"

```
┌────────────────────────────────────────────┐
│  Skill layer (AI reasoning)                │
│  code-review → [fs_read_file, fs_search]   │
├────────────────────────────────────────────┤
│  InfraToolSet layer (env gating)           │
│  linux → all tools pass                    │
│  feishu → only send_message passes         │
│  discord → only send_message passes        │
├────────────────────────────────────────────┤
│  Registry layer (atomic tools)             │
│  fs_read_file, send_message, ...           │
└────────────────────────────────────────────┘
```

Platforms: `linux` (default), `feishu`, `discord`.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/JuliaHZhu/hermes-lite.git
cd hermes-lite

# 2. Install
pip install -e .

# 3. Configure
hermes-lite setup
# → Select provider → Paste API key → Done

# 4. Verify model
hermes-lite -m "hello"

# 5. (Optional) Verify channel
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
hermes-lite -c "hello"

# 6. Start using
hermes-lite
```

## CLI

```
hermes-lite              Start interactive session
hermes-lite setup        Configure API key and model
hermes-lite -m "msg"     Quick model connectivity test
hermes-lite -c "msg"     Quick channel ping (Feishu/Discord)
hermes-lite -v           Show version
hermes-lite -h           Show help
```

## Architecture

```
hermes-lite/
├── main.py              # CLI entry + command routing
├── agent.py             # AI agent loop (Anthropic/OpenAI dual protocol)
├── registry.py          # Tool registry with tags, categories, caching
├── skills.py            # Skill loader with disk snapshot cache
├── memory.py            # SQLite persistence (sessions, messages, todos, goals)
├── infra_toolsets.py    # Platform detection and tool gating
├── pyproject.toml       # pip install config
├── config.json          # User config (gitignored)
└── tools/
    ├── terminal.py      # sys_terminal
    ├── file.py          # fs_read_file, fs_write_file, fs_search_files
    ├── web.py           # net_web_search, net_web_extract
    ├── subagent.py      # agent_delegate_task
    └── send_message.py  # Feishu/Discord webhook (infra)
```

## Features

- **Dual protocol:** Anthropic Messages API + OpenAI Chat Completions API
- **Dynamic tool loading:** Skill trigger → load exact tooldeck per conversation
- **SQLite persistence:** Sessions, messages, todos, goals survive restarts
- **Subagent delegation:** Spawn child agents for isolated subtasks
- **Skill system:** Markdown + YAML frontmatter, trigger matching, context injection
- **InfraToolSet:** Platform-aware tool gating (linux/feishu/discord)

## License

MIT License — see [LICENSE](./LICENSE).

## Acknowledgment

Hermes Lite is derived from the architecture and design philosophy of [Hermes Agent](https://github.com/nousresearch/hermes-agent) by Nous Research. It is not affiliated with or endorsed by Nous Research. The goal is to provide a minimal, hackable reference implementation for developers building their own agent systems.
