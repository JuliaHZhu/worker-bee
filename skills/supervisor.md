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

## Workflow

1. **Check status** → call `supervisor_status` to see current board
2. **Read a job** → call `supervisor_read(job_id)` for details
3. **Create a job** → call `supervisor_create(title, description, skills=[...])`
4. **Update a job** → call `supervisor_update(job_id, state="Done", append_log="completed")

## Job States

- `Todo` — waiting to start
- `Running` — being worked on
- `Done` — completed
- `Blocked` — needs human input

## When to use

- User wants to track multiple tasks
- User asks about progress ("看看进度", "board status")
- User wants to create work items ("新建一个任务")
- User wants to mark something done ("标记完成")

## Deck Note

This skill loads board-management tools only. If a job has `skills: [code-review]`,
you (the agent) must start a *new* run with the appropriate skill to do the actual work.
The supervisor skill does not include code-review tools.
