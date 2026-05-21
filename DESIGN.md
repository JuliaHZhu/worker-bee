# Hermes Lite — Design Evolution

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

So we designed hermes-lite's skill as a single file with YAML frontmatter:

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

## Phase 3: The Deck

> *"活用字典，粗筛粗，细筛细，先组卡组，再抽卡。"*

The Deck architecture separates **procurement** from **execution**:

### Procurement (Compile Time)

1. LLM reads all skill summaries (name, description, triggers, tools)
2. LLM selects relevant skills **semantically**
3. Collect all tools declared by selected skills → form a **Deck**
4. Verify each tool exists in the Registry

### Execution (Runtime)

5. Agent draws **only** from the Deck — no other tools are visible
6. If the task cannot be completed with the Deck → **halt**
7. Human rephrases or new skills are added

**Why halt?** Because the first procurement was already as broad as possible. If the LLM could not solve the task with the chosen tools, retrying with the same deck is unlikely to succeed. The approach itself may be wrong.

### The Math (可约分)

```
Let S  = set of skills selected by LLM
Let T(s) = tools declared by skill s

Deck = ⋃_{s ∈ S} T(s)   (union, deduplicated)
```

Even if skill A routes to skill B at runtime, B.tools is already in the Deck if B was in S. **The tool space of nested skills collapses to a flat, immutable set before execution.** This is "约分" — skill-to-skill nesting does not expand the runtime tool boundary.

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
┌─────────────────────┐
│  Skill Library      │
│  (flat files with   │
│   YAML frontmatter) │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  DeckBuilder        │  LLM semantic selection
│  - Enumerate skills │
│  - LLM picks S      │
│  - Deck = ⋃ T(s)    │
└─────────┬───────────┘
          │ immutable
          ▼
┌─────────────────────┐
│  Deck               │
│  (verified tool set)│
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Agent.run(deck=deck)│  LLM draws ONLY from Deck
│  - tool_use loop    │
│  - max_iter guard   │
└─────────┬───────────┘
          │
    ├─────┴─────┐
    │           │
 success     max_iter?
    │           │
    ▼           ▼
 return     Halt — ask human
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

## Files

| File | Role |
|------|------|
| `skills.py` | Skill loader, trigger matcher, context builder |
| `registry.py` | Tool registry with rich metadata (description, tags, category) |
| `deck.py` | Deck (immutable tool set) + DeckBuilder (LLM-driven procurement) |
| `agent.py` | Protocol adapter (Anthropic/OpenAI) with `run(deck=...)` |
| `main.py` | CLI entry point — orchestrates DeckBuilder, displays deck, handles halt |

---

## From Here

- Add a `decks/` directory for pre-curated tool sets (e.g., `math-deck`, `web-research-deck`)
- Add skill-level priority scoring for conflict resolution
- Add a `skill validate` command to check trigger coverage and tool existence
