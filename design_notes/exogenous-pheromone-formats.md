# Exogenous Pheromone Formats

> *All state must be human-readable Markdown. Both species read the same file.*

## What Is an Exogenous Pheromone?

In Worker Bee, **exogenous pheromone** = external state files that human and LLM both read/write.

- **Exogenous** (外源的): outside the LLM's context window, outside the program's memory
- **Pheromone** (信息素): a shared chemical signal that both parties can sense and respond to

The metaphor: ants leave pheromone trails for other ants to follow. Worker Bee leaves Markdown trails for the next session (or the human) to pick up.

## Design Rules

1. **Markdown only** — no JSON, no binary, no database schemas
2. **Both species read it** — format must be parseable by LLM (`read_file`) and readable by human (any text editor)
3. **Append-friendly** — new entries go at the end or as new sections, no renumbering
4. **Human is the source of truth** — if LLM and human disagree, human wins

---

## Format 1: Terminology Dictionary

Path: `~/.worker-bee/dict/<project>.md`

Used by: **Aristotle B**

```markdown
# 术语词典：<Project>

## <Term>
- **Definition**: <exact definition>
- **Variants**: <variant 1> | <variant 2>
- **Context**: Session <id> — meant <which variant>
- **Drift warning**: Session <id> used it for <different meaning>

## <Another Term>
...
```

### Rules
- Each term = one H2 (`##`)
- Fields = bullet list with `**bold key**`
- `Drift warning` is optional but encouraged
- No strict ordering — append new terms at bottom

---

## Format 2: Architecture Document

Path: `~/.worker-bee/arch/<project>.md`

Used by: **Architecture Prototype B**

```markdown
# Architecture: <Project>

## Goal
<One sentence, irreducible>

## Core Constraints
- [Constraint 1]: <cannot be split further>
- [Constraint 2]: <physical or user boundary>

## Modules

### <Module A>
- **Responsibility**: <single sentence>
- **Interface**: <input → output contract>
- **Algorithm**: <name or sketch>
- **Complexity**: <Big O>
- **Dependencies**: <other modules>

### <Module B>
...

## Tradeoffs
- Chose X over Y because <reason>
```

### Rules
- Goal must be one sentence. If you need two, it is not reduced enough.
- Constraints must be "irreducible" — if you can ask "why?" and get a meaningful answer, keep going.
- Each module is an H3 under `## Modules`.
- Tradeoffs are decisions that could be reversed. Record them so future you knows why.

---

## Format 3: Project Plan

Path: `~/.worker-bee/pm/<project>.md`

Used by: **Project Manager B**

```markdown
# Project: <Project>

## Final Artifact
<What is being delivered?>

## Template
- <Section 1>: <title> — <size> — [TBD/Draft/Done]
- <Section 2>: <title> — <size> — [status]

## Tasks
- [ ] <Task> — <owner> — <due> — [blocker: <what>]

## Contacts
- [<Name>]: <role> — <contact order> — [status]

## Risks
- [<Risk>]: <mitigation>
```

### Rules
- `Final Artifact` is the north star. Everything else serves it.
- `Template` is the scaffold. It should look like the final doc, just with blanks.
- `Tasks` use `[blocker: X]` to show dependencies. No blockers = can start now.
- `Contacts` include contact order (who to reach first, second...).
- `Risks` are not fears — they are specific events with mitigations.

---

## Format 4: Handoff Document

Path: `~/.worker-bee/handoffs/<session_id>.md`

Used by: **All Bs** (batch continuation)

```markdown
# Handoff

**Session:** `<session_id>`
**Exported:** <ISO timestamp>

## Purpose
<What was this session trying to achieve?>

## Completed
- <What got done>

## Todos
- [ ] <Remaining work>

## Context
- <Key facts the next session needs>

## Next Step
<What should the next session do first?>
```

### Rules
- Not a chat summary. A **work-state snapshot**.
- `Completed` = factual, not interpretive.
- `Context` = anything the next session would otherwise have to rediscover.
- `Next Step` = one clear action, not a list of options.

---

## Comparison

| Format | Path | Used By | Content |
|--------|------|---------|---------|
| Dictionary | `dict/*.md` | Aristotle B | Term definitions + drift tracking |
| Architecture | `arch/*.md` | Architecture B | Modules + constraints + tradeoffs |
| Project Plan | `pm/*.md` | PM B | Template + tasks + contacts + risks |
| Handoff | `handoffs/*.md` | All Bs | Work-state snapshot for continuation |
