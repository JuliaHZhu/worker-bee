# Worker Bee

> One Agent. One Board. That's enough.

---

## One Sentence

**Worker Bee = Hermes Lite kernel + swarm extensions.**

It keeps the same minimal architecture — registry, Deck, protocol abstraction, protocol-agnostic loop — and adds the things a real agent needs: sessions, cron, tags, platform awareness, and skill ecosystems.

---

## Why One Agent Is Enough

Multi-agent frameworks assume tasks are so complex they need division of labor, orchestrators, worker pools, and inter-agent protocols.

Worker Bee assumes differently:

> **The agent itself is the dispatcher.** The Deck architecture already solves tool distribution — each task only exposes relevant tools. The agent does not need to be "scheduled"; it only needs to be "activated".

```
User says "supervisor, check progress"
    |
    v
Trigger matches job-supervisor skill
    |
    v
Deck loads board management tools (8)
    |
    v
Agent reads board -> reports -> halts
```

The agent does one thing at a time, but **one thing can be very complex** — reading multiple jobs, evaluating quality, generating reports. Complexity does not imply multiple agents.

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

# 6. Run
worker-bee
```

No daemon. No orchestrator. One CLI entry point.

---

## Architecture

Worker Bee reuses the Hermes Lite kernel verbatim and adds its own layers on top.

```
+------------------------------------------+
|  Worker Bee extensions (swarm layer)     |
|  - SessionDB (SQLite, persistent)        |
|  - Cron scheduler (background thread)    |
|  - Tag extraction (#design #question)    |
|  - InfraToolSet (platform detection)     |
|  - SkillManager (Markdown contracts)     |
|  - Handoff export / resume               |
+------------------------------------------+
|  Agent shell (worker_bee/agent.py)       |
|  - Config, schema cache, thin wrapper    |
+------------------------------------------+
|  Hermes Lite kernel (reused as-is)       |
|  - protocols.py  (Anthropic / OpenAI)    |
|  - loop.py       (protocol-agnostic)     |
+------------------------------------------+
|  Shared infrastructure                   |
|  - registry.py   (tool registry)         |
|  - deck.py       (tool boundary)         |
|  - skills.py     (skill matching)        |
|  - tools/        (file, terminal, web)   |
+------------------------------------------+
```

**What this means in practice**: if Hermes Lite fixes a protocol bug or adds a new provider, Worker Bee gets it for free by copying `protocols.py` and `loop.py`. No merge conflicts. No drift.

---

## Text as Model

The job's true state is not in memory, not in a database — it is in the `jobs/JOB-XXX.md` frontmatter.

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
| **job-supervisor** | Job board management | supervisor, job board |
| **todo-ball-machine** | Life task ball-drawing system | draw, session |
| **podcast-agent** | Document to podcast script | podcast |
| **code-review** | Code review | code review |

Adding a new skill only requires: write a `skills/xxx.md` contract + a `tools/xxx.py` handler. Zero core intrusion.

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

## Specialized Forks

Swap skills and exogenous-pheromone formats to turn Worker Bee into domain-specific tools:

| Fork | Skill | Pheromone | What It Does |
|------|-------|-----------|-------------|
| **Aristotle Bee** | aristotle | `dict/*.md` | Terminology guardian — dictionary lookup + drift detection |
| **Architecture Bee** | architect | `arch/*.md` | Structure reducer — reduce vague goals to irreducible constraints |
| **Project Manager Bee** | project-manager | `pm/*.md` | Orchestration optimizer — template-first delivery with `[TBD]` blanks |

All forks share the same core. Only the skill and data format change.

See `design_notes/` for full design docs.

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
