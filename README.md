# Worker Bee

> One Agent. One Board. That's enough.

---

## One Sentence

**Worker Bee = Hermes Lite kernel + swarm extensions.**

It keeps the same minimal architecture — registry, Deck, protocol abstraction, protocol-agnostic loop — and adds the things a real agent needs: sessions, cron, tags, platform awareness, NATS swarm communication, and a skill ecosystem.

No daemon. No orchestrator. One CLI entry point.

---

## Why One Agent Is Enough

Multi-agent frameworks assume tasks are so complex they need division of labor, orchestrators, worker pools, and inter-agent protocols.

Worker Bee assumes differently:

> **The agent itself is the dispatcher.** The Deck architecture already solves tool distribution — each task only exposes relevant tools. The agent does not need to be "scheduled"; it only needs to be "activated".

```
User says "check my todo list"
    |
    v
Trigger matches todo-ball-machine skill
    |
    v
Deck loads ball-drawing tools
    |
    v
Agent draws -> reports -> halts
```

The agent does one thing at a time, but **one thing can be very complex** — reading multiple jobs, evaluating quality, generating reports. Complexity does not imply multiple agents.

---

## Architecture: A Five-Story Factory

Think of Worker Bee as a factory with five floors. Each floor has one job, and materials (data) flow upward. The agent lives on the top floor; it never worries about what happens in the basement.

```
+------------------------------------------+
|  5F: Swarm Extensions                    |
|  - NATS pub/sub (cross-machine talk)     |
|  - Cron scheduler (background probes)    |
|  - Job Probe (watchdog for jobs/)        |
|  - SessionDB (SQLite, persistent)        |
+------------------------------------------+
|  4F: Agent Shell                         |
|  - Config loader (~/.worker-bee/)        |
|  - Schema cache + agent.md/soul.md       |
+------------------------------------------+
|  3F: Protocol Kernel (Hermes Lite)       |
|  - protocols.py (Anthropic / OpenAI)     |
|  - loop.py (protocol-agnostic loop)      |
+------------------------------------------+
|  2F: Tool Boundary (Deck + Registry)     |
|  - registry.py (thread-safe tool store)  |
|  - deck.py (runtime tool boundary)       |
|  - skills.py (Markdown skill matcher)    |
+------------------------------------------+
|  1F: Tool Implementations                |
|  - lark.py, file.py, terminal.py, ...    |
|  - Auto-register on import. Zero config. |
+------------------------------------------+
```

**What this means in practice**: if Hermes Lite fixes a protocol bug or adds a new provider, Worker Bee gets it for free by copying `protocols.py` and `loop.py`. No merge conflicts. No drift.

---

## How a Request Flows

Here is what happens when you type: *"Send Bob the deployment report"*

```
User input: "Send Bob the deployment report"
    |
    v
┌─────────────────┐
│ skills.py       │  Trigger match: "send" hits lark-messaging skill
│ (Matcher)       │  "Bob" may also hit lark-contact
└────────┬────────┘
         |
         v
┌─────────────────┐
│ deck.py         │  Procure: load tools declared by the skill
│ (Deck Builder)  │  lark-messaging declares: [feishu_lark]
│                 │  + 3 baseline tools (read, search, terminal)
└────────┬────────┘
         |
         v
┌─────────────────┐
│ loop.py         │  Conversation loop begins. LLM only sees Deck tools.
│ (Conversation)  │  Cannot see cronjob, cannot see swarm_publish.
│                 │  Only sees feishu_lark + file ops.
└────────┬────────┘
         |
         v
┌─────────────────┐
│ registry.py     │  LLM calls feishu_lark with:
│ (Dispatcher)    │  {"command": "contact +search-user --query Bob"}
└────────┬────────┘
         |
         v
┌─────────────────┐
│ tools/lark.py   │  Thin execution: subprocess.run(["lark-cli", ...])
│ (Executor)      │  Safety gate: lark_allow_write? Read passes.
│                 │  Write blocked unless config allows.
└────────┬────────┘
         |
         v
    Result -> back to loop -> next turn or done
```

**Key insight**: the Deck is a runtime boundary. The LLM cannot hallucinate tools that are not in the Deck. If a skill does not declare `swarm_publish`, the agent literally cannot invoke it — not because of a permission error, but because the tool does not exist in the current context.

---

## Skill / Tool / CLI: Three Layers, Zero Overlap

Worker Bee enforces a strict separation of concerns. A recent example is the Lark (Feishu) integration:

| Layer | File | Responsibility | Example |
|-------|------|----------------|---------|
| **Skill** | `skills/lark-*.md` | **WHEN / HOW / WHAT-TO-AVOID** — teaches the agent decision flows, boundaries, and anti-patterns | "Before sending, confirm the target. For names, search first; never guess IDs." |
| **Tool** | `tools/lark.py` | **Thin execution** — safely shells out to `lark-cli`. One boolean gate (`lark_allow_write`) | `subprocess.run(["lark-cli", "im", "+messages-send", ...])` |
| **CLI** | `cli.py` | **Human shortcut** — bypass the agent loop for frequent ops | `wb lark send "Bob" "project is live"` |

**The Skill never teaches command syntax** (that lives in the Tool schema). **The Tool never teaches decision logic** (that lives in the Skill). **The CLI is for humans, not the agent**.

This is the core axiom: **Skill = reasoning manual. Tool = execution engine. No duplication.**

---

## Quick Start

```bash
# 1. Create a virtual environment (Ubuntu/Debian requires this)
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

# 2. Install
pip install git+https://github.com/JuliaHZhu/worker-bee.git

# 3. Onboard — configure API key
worker-bee setup
# Or edit ~/.worker-bee/config.json directly

# 4. Test model connection
worker-bee -m "hello"

# 5. Test channel (optional)
export FEISHU_WEBHOOK_URL=...
worker-bee -c "hello"

# 6. Run interactive session
worker-bee
```

### Optional Dependencies

| Package | When You Need It |
|---------|-----------------|
| `transformers` | Non-OpenAI models (Claude, Kimi, etc.) for accurate token counting. Without it, falls back to character estimate (~4 chars/token), which is conservative but less precise. |

```bash
# For Claude / Kimi / local models
pip install transformers
```

No daemon. No orchestrator. One CLI entry point.

**Or use `wb` for direct commands:**

```bash
# Job management
wb job create "Refactor auth module" "Split SSO logic into independent service"
wb job ls
wb job status JOB-001
wb job run JOB-001          # Auto-detect skill, search/extract, write artifacts
wb job tick                 # Manually trigger background probe

# Todo ball machine
wb todo dashboard
wb todo draw morning
wb todo complete morning

# Swarm
wb swarm status
wb swarm listen

# Lark / Feishu
wb lark who Bob             # Search user by name -> open_id
wb lark chats               # List recent chats
wb lark send --to Bob hello # Send DM by name
wb lark inbox --from Bob    # Pull recent messages
```

---

## Project Structure

```
worker-bee/
├─── agent/           # Core agent + CLI
│   ├─── main.py           # CLI entry point (setup / ping / session / lark)
│   ├─── cli.py            # wb command-line interface (job + todo + swarm + lark)
│   ├─── agent.py          # Agent shell (config, schema cache, agent.md/soul.md injection)
│   ├─── loop.py           # Protocol-agnostic run loop (Hermes kernel)
│   ├─── protocols.py      # Anthropic / OpenAI protocol adapters (Hermes kernel)
│   ├─── registry.py       # Tool registry (thread-safe, LRU cache, generation counter)
│   ├─── deck.py           # Tool boundary (Deck procurement)
│   ├─── skills.py         # Skill matching engine (Markdown contracts, trigger matching)
│   ├─── memory.py         # Session DB (SQLite, persistent)
│   ├─── infra_toolsets.py # Platform detection (Linux / Feishu / Discord)
│   ├─── lark_cli.py       # Standalone Feishu Lark bot (HTTP webhook)
│   └─── skills/           # Markdown skill contracts
│       ├─── lark-contact.md
│       ├─── lark-messaging.md
│       ├─── lark-drive.md
│       ├─── code-review.md
│       ├─── todo-ball-machine.md
│       ├─── swarm-send.md
│       ├─── swarm-receive.md
│       └─── ...
├─── tools/                # Tool implementations (auto-registered)
│   ├─── lark.py           # Feishu Lark CLI wrapper (feishu_lark tool)
│   ├─── send_message.py   # Feishu App Bot API / Webhook / Discord
│   ├─── terminal.py       # Shell execution
│   ├─── file.py           # Read / write / search files
│   ├─── web.py            # Web search / extract
│   ├─── subagent.py       # Delegate to child agents
│   ├─── cronjob.py        # Cron job management
│   ├─── job_probe.py      # Background job monitoring + probe tick
│   ├─── swarm.py          # NATS publish + request
│   └─── ...
├─── swarm/                # NATS swarm communication
│   ├─── server.conf       # NATS server config (single-node, cluster-ready)
│   └─── listener.py       # Background listener: NATS -> mailbox/inbox/
├─── cron/                 # Background scheduler
│   ├─── scheduler.py      # Tick loop (integrated with job probe)
│   └─── jobs.py           # Job definitions
├─── jobs/                 # Job storage (Markdown + YAML frontmatter)
│   └─── JOB-XXX/
│       ├─── meta.md
│       ├─── sessions/
│       └─── artifacts/
├─── tests/                # pytest suite (326 tests)
├─── design_notes/         # Architecture docs
├─── todo_ball_machine/    # Life task ball-drawing system
└─── templates/            # Skill authoring templates + agent.md/soul.md examples
```

---

## Text as Model

The job's true state is not in memory, not in a database — it is in the `jobs/JOB-XXX/` directory frontmatter.

**Humans `cat` and understand. LLMs read and operate. Git diff tracks changes.**

A complete job file:

```markdown
---
id: JOB-001
title: Refactor auth module
owner: agent-001
reviewer: human
skills: [code-review, refactor]
deliverables:
  - auth/sso.py
  - tests/test_sso.py
  - migration_guide.md
acceptance:
  - backward compatible
  - test coverage >80%
  - no public API changes
state: Done
phase: done
created: 2026-05-24T14:00:00Z
updated: 2026-05-24T14:55:00Z
---

## Task Description
Split SSO logic into independent module, keep backward compatible.

## Deliverables
- [x] auth/sso.py
- [x] tests/test_sso.py
- [x] migration_guide.md

## Acceptance Criteria
- [x] backward compatible
- [x] test coverage >80%
- [x] no public API changes

## Event Stream (append-only)

- [14:00] created — state=Todo
- [14:05] checkpoint — phase=confirmed, who=agent-001, note=understood task
- [14:10] checkpoint — phase=planned, who=agent-001, note=approach agreed
- [14:20] state_change — Todo -> Running
- [14:30] log — created auth/sso.py
- [14:35] log — tests passed, coverage 85%
- [14:40] self_check — deliverables 3/3, acceptance 3/3
- [14:50] checkpoint — phase=reviewed, who=human, note=pass
- [14:55] state_change — Running -> Done
```

**That is it.** No hidden state. No ORM. One Markdown file = one complete work record.

---

## Four Elements of Delivery Quality

Every job natively contains:

| Element | Field | Meaning |
|---------|-------|---------|
| **What** | `title` + `description` + `skills` | Task content and required capabilities |
| **Who** | `owner` + `reviewer` | Accountability chain: who executes, who validates |
| **Deliverables** | `deliverables` checklist | What artifacts to produce |
| **Acceptance** | `acceptance` checklist | Quality gates to pass |

---

## Seven-Phase Lifecycle

```
created -> confirmed -> planned -> executing -> self_checked -> reviewed -> done
```

| Phase | Meaning | Who Confirms | Output |
|-------|---------|------------|--------|
| `created` | Just created | System | Job file |
| `confirmed` | Owner confirms understanding | Owner | Understanding summary |
| `planned` | Approach submitted and approved | Reviewer | Approved plan |
| `executing` | Work in progress | Owner | Code / docs |
| `self_checked` | Owner self-verification | Owner | Checklist results |
| `reviewed` | Evaluator validates quality | Reviewer | Evaluation conclusion |
| `done` | Archived | System | Complete history |

Every phase transition is a **checkpoint** event recording: who, what phase, what conclusion, when.

---

## vs Symphony

| | **Symphony** | **Worker Bee** |
|---|---|---|
| **Core Assumption** | Tasks need multiple workers | One agent can sequence multiple tasks |
| **Scheduling** | Hard-coded orchestrator (`while/for/sleep`) | Agent reads board, decides itself |
| **Concurrency** | Manages multiple agent instances internally | Sequential execution, simple and predictable |
| **State Storage** | Memory / database / JSON | **Markdown files** (human-readable) |
| **Human Intervention** | Restart with config changes | **Edit job file directly** |
| **Metaphor** | Factory assembly line (automation) | Kanban board (manageable) |

> **Symphony is "machines running the assembly line themselves". Worker Bee is "machines following the human's board".**

---

## What Else?

Existing skills, all using the same Deck architecture:

| Skill | What It Does | Trigger |
|-------|-------------|---------|
| **todo-ball-machine** | Life task ball-drawing system | draw, session |
| **lark-contact** | Resolve names to IDs | find contact, search user, search group |
| **lark-messaging** | Send/receive messages | send, notify, inbox, chat history |
| **lark-drive** | Upload/download/share files | upload, download, file, attachment |
| **code-review** | Code review | code review |
| **job-status** | Job board monitoring | job, status |
| **job-handoff** | Export job state for continuity | handoff |
| **job-audit** | Review deliverables against acceptance | audit |
| **web-research** | Web search and extract | search, research, look up |
| **swarm-send** | Publish/request to swarm via NATS | notify, broadcast, dispatch |
| **swarm-receive** | Read swarm messages from mailbox | check inbox, new messages |
| **wiki** | Local knowledge base operations | wiki, note |
| **pm-bee** | Project management helper | plan, schedule, milestone |
| **skill-creator-is-you** | Skill authoring coach | write skill, create skill |
| **code-decision-guidelines** | Coding decision assistant | tech decision, stack choice |

Adding a new skill only requires: write a `skills/xxx.md` contract + a `tools/xxx.py` handler. Zero core intrusion.

---

## `wb` CLI

`wb` is the direct command-line interface — no agent loop, no context window, just do:

```bash
# Job probe commands
wb job create "Title" "Description" --cycles 2
wb job ls
wb job status JOB-001
wb job handoff JOB-001
wb job audit JOB-001
wb job run JOB-001          # Auto-detect skill from title, search/extract, write artifacts
wb job tick                 # Manually trigger background probe

# Todo ball machine commands
wb todo dashboard
wb todo today
wb todo draw morning
wb todo quick
wb todo complete morning
wb todo history [N]
wb todo stats [N]
wb todo day [YYYY-MM-DD]
wb todo box
wb todo cycle
wb todo new-cycle [name]

# Swarm commands
wb swarm status
wb swarm listen

# Lark commands
wb lark who Bob
wb lark chats
wb lark send --to Bob hello
wb lark inbox --from Bob --limit 10
```

`wb` shares the same `jobs/` directory and `state.db` as the interactive `worker-bee` session. Use `wb` for automation; use `worker-bee` for open-ended conversation.

---

## Job Probe System

The background monitor watches all jobs in `jobs/` and surfaces status without human polling:

```
Every 60s (cron tick):
  |-- Scan jobs/ for active jobs
  |-- Check cycle deadlines
  |-- Surface overdue / blocked jobs
  |-- Trigger handoff if context threshold reached
```

Probe thresholds are configurable (default: 80 rounds warn, 85 rounds handoff).

Skills react to probe state:
- `job-status` -> reads probe output, reports concise dashboard
- `job-handoff` -> exports job state + artifact tree for continuity
- `job-audit` -> reviews deliverables against acceptance criteria

---

## Swarm Communication (NATS)

Worker Bees on different machines talk through NATS — a lightweight pub/sub message bus. Each bee connects to a local NATS server; servers cluster to route messages across the swarm.

```
Agent says "notify swarm deck done"
    |
    v
swarm-send skill matched -> Deck loads swarm_publish
    |
    v
Agent calls swarm_publish("swarm.event.deck-done", payload)
    |
    v
NATS routes -> swarm_listener (background process) writes to mailbox/inbox/
    |
    v
Agent says "check inbox" -> swarm-receive skill -> reads mailbox -> processes
```

- **Send**: `swarm_publish` (broadcast) or `swarm_request` (query with reply)
- **Receive**: Background `swarm/listener.py` subscribes NATS -> writes `~/.worker-bee/mailbox/inbox/`
- **CLI**: `wb swarm status`, `wb swarm listen`

Agents never subscribe directly. They read the mailbox — same philosophy as the Job Board: all state in files.

---

## Session Handoff

When a session grows long, do not compress history. Export a handoff and start fresh:

```bash
# During session
> /export
Handoff exported to: ~/.worker-bee/handoffs/a1b2c3d4.md

# Exit also auto-exports
> /exit
[Handoff] exported to ~/.worker-bee/handoffs/a1b2c3d4.md
```

Load it in a new session:
```bash
worker-bee --continue ~/.worker-bee/handoffs/a1b2c3d4.md
```

A handoff is a work-state snapshot (Purpose, Completed, Todos, Context, Next Step) — not a chat summary.

---

## Design Notes

Historical fork concepts (Aristotle Bee, Skeleton Bee, Project Manager Bee, WorldBee) and the full agent ecosystem design are archived in `design_notes/`. They illustrate how the same kernel can wear different skill skins.

Operational specs (pheromone formats, mechanism vs task skill distinctions) live in `design_notes/exogenous-pheromone-formats.md`.

Recent architecture studies:
- **BeeBox** (`design_notes/beebox.md`) — three tightening constraints for agentic hardware
- **AEvo** (`design_notes/architecture-study/aevo-harnessing-agentic-evolution.md`) — harnessing agentic evolution
- **Autogenesis** (`design_notes/architecture-study/autogenesis-self-evolving-agent-protocol.md`) — self-evolving agent protocol

---

## Design Principles

| Principle | Meaning |
|-----------|---------|
| **Reuse the Kernel** | `protocols.py` + `loop.py` are copied verbatim from Hermes Lite. No divergence. |
| **One Agent Is Enough** | No multi-agent, no orchestrator, no daemon |
| **Text as Model** | All state in Markdown, human-readable and editable anytime |
| **Append-Only** | Event stream never overwritten, history never lost |
| **Deck Pruning** | Each task only exposes relevant tools, no boundary crossing |
| **Checkpoint-Driven** | Tasks are not "Todo->Done"; they are 7 confirmation nodes |
| **Skill != Tool** | Skill = reasoning manual (WHEN/HOW/WHAT to avoid). Tool = thin execution engine. Zero duplication. |

---

## Customizing the Agent (agent.md + soul.md)

Want to change how the agent behaves? Write two Markdown files — no code changes needed.

```
~/.worker-bee/
├── agent.md    # Agent behavior: rules, preferences, tool usage patterns
└── soul.md     # Agent personality: tone, style, identity
```

On startup, Worker Bee reads both files and appends them to the system prompt. Each file is wrapped with its own header:

```
--- AGENT.MD ---
[contents of agent.md]

--- SOUL.MD ---
[contents of soul.md]
```

**How it works** (from `agent/agent.py`):

```python
def _load_prompt_files() -> str:
    base = Path.home() / ".worker-bee"
    for filename in ("agent.md", "soul.md"):
        path = base / filename
        if path.exists():
            parts.append(f"\n\n--- {filename.upper()} ---\n\n{path.read_text()}")
    return "".join(parts)

# In AIAgent.__init__:
self.system_prompt = f"{base_prompt}{injection}"
```

**Bottom line**: edit the files -> agent behavior changes. No restart, no config, no code.

---

> You have an Agent.
>
> You have a Board.
>
> These two things are always talking.
>
> You can pat its shoulder anytime and ask: "How is this one going?"
>
> It will point you to the records on the board.
>
> That is enough.
