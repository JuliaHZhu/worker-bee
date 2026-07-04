# Worker Bee — Design Evolution

> How a curiosity about Hermes Agent turned into a new architecture for stable skill invocation.

---

## Table of Contents

1. [Phase 0: The Spark](#phase-0-the-spark)
2. [Phase 1: What Is a Skill?](#phase-1-what-is-a-skill)
3. [Phase 2: The Registry](#phase-2-the-registry)
4. [Phase 3: The Deck](#phase-3-the-deck)
5. [Phase 4: Orthogonal Routing](#phase-4-orthogonal-routing)
6. [Current Architecture](#current-architecture)
7. [Design Principles](#design-principles)
8. [Phase 5: Batch Handoff](#phase-5-batch-handoff)
9. [Phase 6: Forks](#phase-6-forks)
10. [Phase 7: Multi-Node Communication](#phase-7-multi-node-communication)

---

## Phase 0: The Spark

We started by looking at [Hermes Agent](https://github.com/nousresearch/hermes-agent) — a full-featured AI agent with skills, subagents, and multi-platform delivery. We were curious: **how does it organize tools?**

Hermes uses a directory tree:

```
skills/
├── research/
│   └── DESCRIPTION.md
├── software-development/
│   ├── plan/SKILL.md
│   └── github-code-review/SKILL.md
└── media/
    └── youtube-content/SKILL.md
```

Each domain is a folder, each skill is a subfolder with a `SKILL.md`. But there is **no trigger field**. Skills are matched by an index or subagent, not by a declarative frontmatter.

This raised the first question: **if skill names are ambiguous, how does the system know which skill to load?**

---

## Phase 1: What Is a Skill?

We realized that a **skill is not a tool set**. A skill is a **playbook** — a declaration of:

- **When** to use it (`trigger`)
- **What** tools it needs (`tools`)
- **How** to use them (the body / instructions)

Hermes treats skills as **packages**. We wanted them to be **contracts** — precise, self-describing, and machine-readable.

So we designed worker-bee's skill as a single file with YAML frontmatter:

```yaml
---
name: web-research
description: Research topics on the web and summarize findings
trigger: search, look up, research, find online
tools:
  - net_web_search
  - net_web_extract
---
```

This solved the first layer of precision: **a skill declares its own activation conditions.**

But a new problem emerged: **if the skill name is poorly chosen, or the trigger is too broad, the wrong skill gets matched.** And even if the right skill is chosen, the LLM still has to pick the right tools from a large pool.

---

## Phase 2: The Registry

The original tool registry was just a name → handler map. We upgraded it to a **rich metadata registry**:

```python
registry.register(
    name="fs_read_file",
    description="Read a text file with pagination. Use when inspecting source code...",
    parameters={...},
    handler=read_file,
    tags=["filesystem", "read"],
    category="filesystem"
)
```

**Key insight:** The `description` is not for humans. It is a **tool instruction manual for the LLM**. When the LLM chooses between 5 tools, it reads only `name + description + parameters`. Every word in the description influences the decision.

This solved the **second layer of precision**: tool selection within a skill.

But a deeper problem remained: **the entire tool pool is visible to the LLM during execution.** If 20 tools are loaded, the LLM can make cross-domain mistakes — e.g., using `fs_write_file` when the user only asked a question.

We needed a **boundary**.

---

## Phase 3: The Deck — Formula, Engine, Gameplay

> *"公式组装成引擎，引擎包装成玩法，这就是工程。"*

### The Dwarf Fortress Analogy

[Dwarf Fortress](https://www.bay12games.com/dwarves/) has three layers:

| Layer | What It Is | Example |
|-------|-----------|---------|
| **Formula** | Discovered rules from exploration | Fluid dynamics, temperature transfer, social relationship decay |
| **Engine** | Formulas assembled into a runnable system | The simulation loop that updates temperature, fluid pressure, dwarf moods every tick |
| **Gameplay** | Engine packaged into player-facing interaction | You tell dwarves to dig, build, trade. You don't touch the fluid equations directly. |

**The formulas came from discovery.** The creator didn't invent gravity — he observed it, abstracted it, encoded it. Then **engineering** wrapped those formulas into a game.

### Our Three Layers

| Layer | In Our System | Phase |
|-------|--------------|-------|
| **Formula** | Verified constraints, validated assumptions, known-good tool combinations | `/explore` → `/validate` |
| **Engine** | The **Deck** — an immutable, pre-procured tool set assembled from selected skills | Procurement |
| **Gameplay** | Agent execution — drawing only from the Deck to solve the user's task | Execution |

### Procurement (Build the Engine)

1. Load all skills from `skills/` (YAML frontmatter with triggers and tools)
2. Match triggers against user input via **substring search** (`trigger.lower() in ui_lower`)
3. Collect all tools declared by matched skills → form a **Deck**
4. Verify each tool exists in the Registry

> **Implementation note:** The current trigger matcher is a substring search, not LLM semantic selection. At ~15 skills, this is precise enough and avoids an extra LLM call during procurement. Semantic selection can be introduced when the skill library grows significantly.

The Deck is the **engine**: a flat, immutable, verified set of capabilities. No more, no less.

### Execution (Play the Game)

5. Agent draws **only** from the Deck — no other tools are visible
6. The LLM orchestrates tool calls like a player orchestrates dwarves: using the engine, not rewriting it
7. If the task cannot be completed with the Deck → **halt**

**Why halt?** Because the engine was already built from the broadest possible procurement. If the LLM cannot solve the task with this engine, the **formulas are insufficient** — not the execution. The user needs to `/explore` more, discover new constraints, or design new skills. Restarting with the same Deck is like replaying a broken save: the engine hasn't changed.

### The Math (约分)

```
Let S  = set of skills selected by LLM
Let T(s) = tools declared by skill s

Deck = ⋃_{s ∈ S} T(s)   (union, deduplicated)
```

Even if skill A routes to skill B at runtime, B.tools is already in the Deck if B was in S. **The tool space of nested skills collapses to a flat, immutable set before execution.** This is 约分 — skill-to-skill nesting does not expand the runtime tool boundary. The engine doesn't grow mid-flight.

---

## Phase 4: Orthogonal Routing

Skill-to-skill routing (composable skills) is **separate** from the Deck boundary:

- **Atomic skills** = single operations (like a remote button)
- **Procedural skills** = macros that orchestrate other skills
- **Routing** = LLM semantic analysis deciding which sub-skill to invoke

This routing happens **inside execution**, but still **within the Deck boundary**. The procedural skill does not bring new tools into the Deck — it merely decides how to use the tools that were already procured.

**Analogy:** You buy all your ingredients before cooking. The recipe (procedural skill) tells you which ingredient to use next, but you cannot go back to the store mid-cooking.

---

## Current Architecture

```
User Input
    │
    ▼
██████████████████████████████████████████████████
│  Skill Library      │
│  (flat files with   │
│   YAML frontmatter) │
│                     │
███████████████████████
          │
          ▼
██████████████████████████████████████████████████
│  DeckBuilder        │  trigger substring match
│  - Enumerate skills │
│  - Match triggers   │
│  - Deck = ⋃ T(s)   │
███████████████████████
          │
          ▼ immutable
██████████████████████████████████████████████████
│  Deck               │
│  (verified tool set)│
███████████████████████
          │
          ▼
██████████████████████████████████████████████████
│  Agent.run(deck=deck)│  LLM draws ONLY from Deck
│  - tool_use loop     │
│  - max_iter guard    │
███████████████████████
          │
    ┌─────┴─────┐
    ▼           ▼
success     max_iter?
    │           │
    ▼           ▼
 return      Halt — ask human
```

---

## Design Principles

| Principle | Rationale |
|-----------|-----------|
| **Skill as Contract** | A skill must declare `trigger` + `tools` + `description`. Ambiguity is a bug. |
| **Description as Manual** | Registry descriptions are LLM-facing instructions, not human documentation. |
| **Procure Before Execute** | The Deck is built once, before the first LLM turn. No mid-flight tool shopping. |
| **Immutable Boundary** | The Deck does not grow during execution. What you procured is what you get. |
| **Halt on Exhaustion** | If `max_iterations` is reached, the deck was insufficient. Stop, do not recurse. |
| **约分 (Reduction)** | Nested skill tool spaces collapse to a flat union at procurement time. |
| **Orthogonal Routing** | Skill-to-skill routing is a semantic decision inside execution, not a procurement expansion. |

---

## Phase 5: Batch Handoff (Session Continuation)

> *Worker Bee sessions are batch pipelines, not endless chats. When a session grows long, don't compress history — snapshot the work-state and start a fresh session.*

### 5.1 Design Principle

Hermes Agent uses **context compaction** (summarize middle history, keep head+tail). That works for open-ended conversations where most turns are disposable.

Worker Bee is different: every message advances a business task. The whole chain matters. Compressing it loses critical constraints.

**Solution:** Export a **handoff document** — a work-state snapshot, not a chat summary.

### 5.2 Handoff Format

```markdown
# Handoff

**Session:** `a1b2c3d4`
**Exported:** 2026-05-29T18:30:00

## Purpose
Generate a Python onboarding course for backend engineers

## Completed
- Chapter 01 outline approved
- `chapter_01.md` generated with project-driven structure

## Todos
- [ ] Generate exercise solutions
- [ ] Review chapter 02 outline

## Context
- Target audience is backend engineers with 1-2 years experience
- Course should be project-driven, not syntax-reference style

## Next Step
Generate exercise solutions for chapter 01
```

### 5.3 Usage

```bash
# During session
> /export
Handoff exported to: ~/.worker-bee/handoffs/a1b2c3d4.md

# Exit also auto-exports
> /exit
[Handoff] exported to ~/.worker-bee/handoffs/a1b2c3d4.md

# Start fresh session with handoff
$ worker-bee --continue ~/.worker-bee/handoffs/a1b2c3d4.md
```

### 5.4 Implementation

- `memory.py`: `export_handoff()` — builds the Markdown from session meta + recent messages + todos
- `main.py`: `/export` command + auto-export on exit
- Future: `--continue <path>` CLI arg to load handoff into a new session's system prompt

### 5.5 Why This Fits Worker Bee

| Hermes Compaction | Worker Bee Handoff |
|---|---|
| For open-ended, multi-topic chats | For focused, single-task pipelines |
| LLM summarizes history (lossy) | Raw state preserved (lossless) |
| Automatic, user-unaware | User-controlled (`/export` or exit) |
| 64K–750K token threshold | Human decides when a "batch" ends |

**Each session = one batch. Handoff = the batch output. Next session = next batch, reading previous output as input.**

---

## Phase 6: Forks — Specialized Bees

> *Worker Bee is a shell. The skills determine what kind of thinker you are talking to.*

The core (deck, registry, agent loop) stays the same. But by swapping skills and exogenous-pheromone formats, we fork Worker Bee into **domain-specific cognitive tools**.

Each fork follows the same first-principles:
- **Human is the cognitive center** — the B executes, does not decide
- **All state is Markdown** — human-readable, human-editable
- **LLM is a glove** — it wears the skill, follows the protocol, does not improvise

---

### 6.1 Aristotle Bee — Definition Master

**Problem:** The same word means different things in different sessions. "Immersion" today is flow, tomorrow it is sensory. The LLM does not notice the drift.

**Behavior:**
1. When the user mentions a term, check `~/.worker-bee/dict/<project>.md`
2. If the term exists — quote its definition, flag drift if context differs
3. If the term does not exist — ask: "What do you mean by X?"
4. If the user coins a new term — record it with `[New term]` label

**Exogenous Pheromone:** `~/.worker-bee/dict/<project>.md`

```markdown
## Immersion
- **Definition**: Player forgets reality, fully absorbed
- **Variants**: flow | sensory | narrative
- **Context**: Session e5f6g7h8 — meant narrative
- **Drift warning**: Session a1b2c3d4 used for sensory
```

**Skill:** `skills/aristotle.md`

**Why it works:** The dictionary is a **shared mental model** between human and LLM. Both species read the same Markdown. The LLM does not "understand" the term — it looks it up and injects the definition into context. Precision without comprehension.

---

### 6.2 Architecture Prototype B — Structure Reducer

**Problem:** You have a vague idea ("I want a roguelike"). You need to reduce it to irreducible constraints before writing code.

**Behavior:**
1. **Interrogate** — ask what, not how ("What is the goal?" not "What framework?")
2. **Reduce** — ask "why" until you hit physical or user constraints that cannot split further
3. **Estimate** — sketch Big O for each module (time vs space tradeoffs)
4. **Output** — module decomposition as orthogonal basis (high cohesion, low coupling)

**Exogenous Pheromone:** `~/.worker-bee/arch/<project>.md`

```markdown
# Architecture: Simple Roguelike

## Goal
Combat depth from positional tactics, not stat grinding.

## Core Constraints
- Must run at 60fps on 2015 laptop
- Combat completable without leveling
- Map generation produces solvable dungeons

## Modules

### Map Generator
- **Responsibility**: Procedural layout + enemy placement
- **Interface**: Input(seed, difficulty) → Output(tilemap, entities)
- **Algorithm**: Cellular automata + A* solvability check
- **Complexity**: O(n²) for n×n grid, n≤50
```

**Skill:** `skills/architect.md`

**Why it works:** Architecture is **reduction**, not construction. The B forces the human to strip away ambiguity until only constraints remain. Code comes after structure is agreed upon. The LLM does not design — it interrogates and records.

---

### 6.3 Project Manager Bee — Orchestration Optimizer

**Problem:** You have real-world materials (regulations, contacts, deadlines) and limited resources. You need to sequence tasks, not just list them.

**Behavior:**
1. **Decompose** — what actually needs to happen (regulations, contacts, documents)
2. **Template-first** — lay out the final artifact format immediately (thesis, proposal, design doc)
3. **Focus on presentation** — "What will the final artifact look like? How many sections?"
4. **Leave blanks** — mark uncertain parts `[TBD]`, do not polish
5. **Optimize orchestration** — given limited time/energy, what order minimizes risk? Blockers first.

**Exogenous Pheromone:** `~/.worker-bee/pm/<project>.md`

```markdown
# Project: Master's Thesis

## Final Artifact
15,000-word thesis on procedural content generation.

## Template
- Abstract — 300 words — [TBD]
- Chapter 1: Introduction — 3 pages — [TBD]
- Chapter 2: Literature Review — 8 pages — [TBD]
...

## Tasks
- [ ] Submit proposal — me — Week 1 — [blocker: none]
- [ ] Get IRB approval — me — Week 2-3 — [blocker: proposal]
- [ ] Recruit participants — me+lab — Week 4-6 — [blocker: IRB]

## Contacts
- [Prof. Smith]: advisor — contact 1st — [status: meeting scheduled]

## Risks
- [Recruitment slow]: mitigate by online forums
```

**Skill:** `skills/project-manager.md`

**Why it works:** PM Bee treats every project as a **pipeline with a known output format**. The conversation is not "what should I do?" but "what goes in each slot of the template?" Done is better than perfect. The scaffold makes iteration cheap.

---

### 6.4 How Forks Work

All three Bs share the same Worker Bee core. The only difference is:

| Fork | Skill Loaded | Exogenous Pheromone | Conversation Style |
|------|-------------|---------------------|-------------------|
| Aristotle Bee | `aristotle.md` | `dict/*.md` | Abstract, definitional — "What do you mean by X?" |
| Architecture Bee | `architect.md` | `arch/*.md` | Structural — "Why? Can it split further?" |
| Project Manager Bee | `project-manager.md` | `pm/*.md` | Concrete — "What is the deliverable? What goes in slot 3?" |

**No code changes to core.** Just skills + Markdown files. The human decides which B to invoke by which skill they place in `~/.worker-bee/skills/` or which directory they maintain.

---

## Summary: The First Principles

| Fact | Design Decision |
|------|-----------------|
| LLM is a next-token predictor | It executes, does not decide. Human is the cognitive center. |
| LLM context window is finite | State must be externalized as Markdown (exogenous pheromone). |
| Text is the only shared language | All persistent state is human-readable Markdown. |
| Complexity grows exponentially with abstraction layers | Skill is minimal: trigger + tools + behavior. No eval frameworks. |
| User needs a mental model | Predictable, fixed behavior > smart but unpredictable. |

**Worker Bee = shell. Skills = gloves. Human = hand.**

---

## Phase 7: Multi-Node Communication

> *Worker Bee can run as a swarm: multiple machines, each hosting one Bee role, communicating via NATS and Git.*

### 7.1 Communication Layer Separation

| Type | Channel | Why |
|------|---------|-----|
| **Scheduling notifications** | NATS | Lightweight, real-time, fire-and-forget |
| **Task files** | Git | Versioned, auditable, durable |
| **Heartbeats / events** | NATS | Broadcast, no storage needed |
| **Skill iteration** | Git | PR workflow, human review |

**NATS says "what happened". Git says "what is the content".**

### 7.2 NATS: Notifications Only

```
Centurion (Node 5)
  │
  ├── NATS: "swarm.task.new: task-001"
  │
Worker (Node 6)
  │
  ├── Receives NATS notification
  ├── git pull tasks/queue/ → fetches task-001
  ├── Executes...
  ├── git push tasks/done/ → commits result-001
  ├── NATS: "swarm.task.done: task-001"
  │
Centurion
  ├── Receives NATS notification
  ├── git pull tasks/done/ → fetches result-001
```

NATS is **notification-only**: it tells a node "something happened", not "here is the data". Nodes use NATS to know *when* to pull, and Git to know *what* they pulled.

**Benefits:**
- NATS does not carry large payloads → low latency, low memory
- If NATS is down, nodes can still poll Git and make progress
- Task history is permanent in Git, not ephemeral in a message queue

### 7.3 Git: File-Layer Truth

```
# Per-node repo layout
tasks/
  queue/       ← Centurion writes, Workers read
  active/      ← Worker moves task here while running
  done/        ← Worker writes results, Centurion reads
  archive/     ← Centurion moves completed tasks after review

skills/
  *.md         ← Skill definitions (YAML frontmatter)
  pheromone/   ← Skill iteration history

ops/
  known-gaps.md      ← World Bee: recurring warnings
  deck-recipes/      ← Pre-curated tool sets
```

- Each node has its own repo or branch
- Changes flow through normal Git operations: `commit → push → PR → merge`
- No custom sync protocol needed

### 7.4 Why This Fits Worker Bee

| Traditional Message Queue | Worker Bee NATS+Git |
|---|---|
| Messages are ephemeral | Task files are permanent |
| Central broker is a bottleneck | Git is distributed |
| Skill updates need custom deployment | Skill updates are `git pull` |
| Debugging requires log spelunking | Debugging is `git log` |

**NATS is the nervous system. Git is the skeleton. Both are off-the-shelf.**

### 7.5 8-Node Role Mapping

| Node | Bee Role | Layer | Key Responsibility |
|------|---------|-------|-------------------|
| 1 | Aristotle Bee | Strategic auxiliary | Terminology, definitions |
| 2 | Skeleton Bee | Strategic auxiliary | Card-type selection, structure |
| 3 | Strategy Bee | Secondary strategy | Direction, dialectics, negation |
| 4 | PM Bee | Campaign management | Scheduling, splitting, monitoring |
| 5 | Centurion Bee | Execution squad | Dispatch, monitor Workers |
| 6 | Worker Bee | Execution squad | Tool execution |
| 7 | World Bee | Fault tolerance | Real-time validation, archival |
| 8 | Cardmaster Bee | Tactical advisor | Playbook, debrief, adversarial review |

Each node runs the same Worker Bee core. The difference is only: **which skills are loaded**, and **which exogenous pheromone directory they maintain**.

---

## Files

| File | Role |
|------|------|
| `skills.py` | Skill loader, trigger matcher, context builder |
| `registry.py` | Tool registry with rich metadata (description, tags, category) |
| `deck.py` | Deck (immutable tool set) + DeckBuilder (LLM-driven procurement) |
| `agent.py` | Protocol adapter (Anthropic/OpenAI) with `run(deck=...)` |
| `main.py` | CLI entry point — orchestrates DeckBuilder, displays deck, handles halt |
| `swarm/listener.py` | NATS event listener, heartbeat, mailbox writer |
| `swarm/server.conf` | NATS server configuration (cluster mode) |
| `skills/swarm-awareness.md` | Skill for inter-agent communication and request handling |

---

## From Here

- Add a `decks/` directory for pre-curated tool sets (e.g., `math-deck`, `web-research-deck`)
- Add skill-level priority scoring for conflict resolution
- Add a `skill validate` command to check trigger coverage and tool existence
