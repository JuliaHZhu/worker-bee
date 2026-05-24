---
name: supervisor
description: Job board supervisor. Read, create, update and track agent work as Markdown jobs. When the user says "supervisor", "kanban", "job board", or "监工", load this skill.
triggers:
  - supervisor
  - kanban
  - job board
  - jobs
  - 监工
  - 工单
  - 看看进度
  - board
tools:
  - supervisor_status
  - supervisor_read
  - supervisor_create
  - supervisor_update
  - supervisor_delete
---

# Supervisor Skill

You manage a job board stored in `jobs/*.md`. Each job is a Markdown file with YAML frontmatter.

## Design Principle: Append-Only History

All updates to a job are **events appended to the event stream**. Past events are never overwritten.

```markdown
## 事件流 (append-only)

- [14:00] created — state=Todo
- [14:05] state_change — Todo → Running
- [14:10] log — 读 auth.py，发现硬编码
- [14:30] log — 测试通过
- [14:35] state_change — Running → Done
- [14:40] eval — design-alignment: Pass
```

- `supervisor_update` appends `state_change` or `log` events
- `supervisor_evaluate` appends `eval` events
- `supervisor_read` returns the full history

The frontmatter `state` field is a **cache** for fast board scans. The event stream is the source of truth.

## Evaluation Model

The supervisor does not hard-code quality checks. Evaluation is **skill-driven**:

- A job declares `skills: [code-review, web-research]` for the worker
- Evaluator skills declare `eval_for: [code-review]` to indicate they can assess that worker's output
- The supervisor assembles an evaluation Deck from matching evaluator skills
- The evaluation result is appended as an `eval` event

Human intervention points:
- `Blocked` → human reads the event stream, writes a clarifying instruction as a new job or comment
- `NeedMeeting` → supervisor prepares an agenda from the event stream, human organizes the meeting

## Workflow

1. **Check status** → call `supervisor_status` to see current board
2. **Read a job** → call `supervisor_read(job_id)` for full event history
3. **Create a job** → call `supervisor_create(title, description, skills=[...])`
4. **Update a job** → call `supervisor_update(job_id, state="Running", append_log="started")`
5. **Evaluate a job** → call `supervisor_evaluate(job_id, "design-alignment", "Pass")`

## Job States

- `Todo` — waiting to start
- `Running` — being worked on
- `Done` — completed
- `Blocked` — needs human input (read the event stream to understand why)

## When to use

- User wants to track multiple tasks
- User asks about progress ("看看进度", "board status")
- User wants to create work items ("新建一个任务")
- User wants to mark something done ("标记完成")
- Supervisor needs to record an evaluation ("评估结果")

## Deck Note

This skill loads board-management tools only. If a job has `skills: [code-review]`,
you (the agent) must start a *new* run with the appropriate skill to do the actual work.
The supervisor skill does not include code-review tools.

Evaluation Decks are assembled separately from worker Decks. A job may have:
- Worker skills: `[code-review, web-research]`
- Evaluator skills: `[design-alignment, security-check]` (matched via `eval_for` in skill definitions)
