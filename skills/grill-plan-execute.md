---
name: grill-plan-execute
description: 3-phase workflow — Grill interview for requirements, Plan as structured task tree with acceptance criteria, Execute with context guardrails. Reduces planning fatigue by making AI interview you instead of you reviewing AI drafts.
triggers:
  - grill-plan
  - task-orchestrator
  - 需求确认
  - 结构化执行
  - 任务拆解
  - 三步走
tools:
  - fs_read_file
  - fs_write_file
  - deck_manage
category: workflow
version: "1.0.0"
composability: composable
---

# Grill-Plan-Execute Skill

This skill implements a **3-phase workflow** inspired by the "Grill-me + Trellis" pattern:
1. **Grill** — AI interviews you with focused questions to surface hidden constraints
2. **Plan** — Consensus is converted into a structured task tree with explicit acceptance criteria
3. **Execute** — Tasks are executed one by one, with context guardrails preventing drift

**Why this works**: Traditional "AI writes → you review" is cognitively expensive (like grading essays). This flips it to "AI asks → you choose" (like multiple-choice), reducing planning overhead by ~70%.

## When to use

- Starting a complex feature or refactor where requirements feel fuzzy
- You have a vague idea but don't want to write a full spec
- Long-running tasks that tend to drift off-track after 10+ rounds
- Any task where "I'll know it when I see it" — the AI's job is to make you articulate it

## Workflow

### Phase 1: GRILL (Requirements Interview)

**Goal**: Surface all implicit assumptions before a single line of code is written.

**Rules**:
- AI asks **one question at a time**, never a questionnaire dump
- Each question is **binary or multiple-choice** where possible ("SQLite or PostgreSQL?" not "What database?")
- User answers in **5-10 seconds** per question
- After 5-8 questions, AI summarizes consensus and asks: "Did I miss anything critical?"

**Stop condition**: Both AI and user agree the constraint surface is fully explored.

**Example question sequence**:
```
Q1: Is this a new feature or modifying existing code?
Q2: Should it persist state to disk or be in-memory only?
Q3: Priority: correctness first or speed first?
Q4: Error handling: fail fast or graceful degradation?
Q5: Who calls this — human, another agent, or both?
```

### Phase 2: PLAN (Task Tree)

**Goal**: Convert consensus into an executable, non-ambiguous plan.

**Output format**: A markdown task tree written to `tasks/<job-id>.md`:
```markdown
# Task Tree: [Job Name]

## Consensus Summary
[2-3 sentences from Phase 1]

## Tasks

### T1: [Task name]
- **Acceptance**: [Specific, verifiable condition]
- **Files to touch**: [list]
- **Estimated complexity**: Low / Medium / High
- **Blockers**: [None | depends on T?]

### T2: ...
```

**Rules**:
- Every task must have a **verifiable acceptance criterion** (not "make it better")
- Tasks are ordered by dependency, not by preference
- Total task count should be ≤ 15; if more, suggest splitting into sub-jobs

### Phase 3: EXECUTE (Guarded Execution)

**Goal**: Execute the task tree without context drift.

**Rules**:
- Execute **one task at a time**, confirm completion before next
- After each task, re-read the task tree to re-anchor context
- If a task reveals new constraints that violate Phase 1 consensus:
  - **Pause execution**
  - Report the conflict
  - User decides: update consensus and replan, or override and continue
- Tool outputs clamped to 10,000 chars before entering conversation history (per framework default)
- If > 50% of tasks are done, offer a mid-point review

## Error Handling

| Scenario | Response |
|----------|----------|
| User answers "I don't know" to a grill question | AI proposes 2-3 sensible defaults, user picks one |
| Phase 2 reveals contradictory Phase 1 answers | Flag conflict, re-grill the specific decision point only |
| Task execution fails acceptance | Stop, diagnose root cause, do NOT skip to next task |
| Long pause (> 5 min) between tasks | AI re-reads task tree and summarizes "Where we are" |
| User wants to change scope mid-execution | Treat as new job: save current state, run Phase 1+2 on delta |

## Safety

- `fs_write_file` only writes to `tasks/` directory for task trees — safe
- `fs_read_file` is read-only — safe
- `deck_manage` may switch to focus mode for deep execution — user is informed
- No destructive tools used in planning phase

## Examples

### Example 1: Normal case — new API endpoint

```
User: "I need a new endpoint to export job history"
→ AI (Grill):
  Q1: REST or gRPC?
  Q2: JSON or CSV output?
  Q3: Filterable by date range?
  Q4: Paginated or full dump?
  Q5: Auth required?
→ User answers: REST, JSON, yes, paginated, yes
→ AI (Plan): writes tasks/export-job-history.md with 4 tasks
→ AI (Execute): implements T1-T4 sequentially, verifying each
→ Result: endpoint shipped, no back-and-forth on "oh I also need..."
```

### Example 2: Edge case — conflicting requirements discovered

```
User: "Make the report generator handle both real-time and batch"
→ AI (Grill): user says "same code path for both"
→ AI (Plan): writes task tree
→ AI (Execute T2): discovers real-time requires streaming, batch requires buffering — same path is architectural conflict
→ AI: STOPS. Reports conflict. Asks user: "Split into two modules, or pick one mode?"
→ User: "Split. Batch first."
→ AI: Updates task tree, replans T2-T5, resumes execution
```

## Integration with worker-bee roles

This skill can be invoked by:
- **Strategy Bee** — when receiving a vague strategic objective
- **PM Bee** — when a task description is underspecified
- **Centurion Bee** — before dispatching to Worker Bees, to ensure task clarity
- **Aristotle Bee** — when a philosophical design decision needs human input

## Related skills

- `grill-me` (nanobot) — the original relentless interview skill; this skill extends it with Plan+Execute
- `job-handoff` — if execution spans sessions, handoff after any completed task
- `deck-control` — may switch deck modes between Plan (full) and Execute (focus)

## Notes

- The "10-minute interview" vs "40-minute review" tradeoff: this skill optimizes for **human cognitive load**, not wall-clock time
- If user says "just do it" and refuses Phase 1, skip to Phase 2 with explicit risk flag: "Proceeding with implicit assumptions — backtracking likely"
- Task tree format is intentionally simple markdown so it survives across any tool or platform
