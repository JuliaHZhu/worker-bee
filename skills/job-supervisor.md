---
name: job-supervisor
description: Job board supervisor with delivery-quality tracking. Manage jobs, record checkpoints, and track deliverables/acceptance.
triggers:
  - job-supervisor
  - job supervisor
  - kanban
  - job board
  - jobs
  - 监工
  - 工单
  - 看看进度
  - board
tools:
  - job_supervisor_status
  - job_supervisor_read
  - job_supervisor_create
  - job_supervisor_update
  - job_supervisor_checkpoint
  - job_supervisor_self_check
  - job_supervisor_evaluate
  - job_supervisor_delete
---

# Job Supervisor Skill

You manage a job board stored in `jobs/*.md`. Each job is a Markdown file tracking delivery quality.

## Delivery Quality: Four Elements

Every job declares:

| Element | Field | Meaning |
|---------|-------|---------|
| **What** | `title` + `description` + `skills` | Task content and required capabilities |
| **Who** | `owner` (responsible) + `reviewer` (validator) | Accountability chain |
| **Deliverables** | `deliverables` checklist | Artifacts to produce |
| **Acceptance** | `acceptance` checklist | Quality gates to pass |

## Phase Lifecycle (Checkpoints)

```
created → confirmed → planned → executing → self_checked → reviewed → done
```

- `created` — job file created
- `confirmed` — owner confirms understanding of task and standards
- `planned` — owner submits approach, reviewer approves
- `executing` — work in progress
- `self_checked` — owner verifies deliverables and acceptance criteria
- `reviewed` — reviewer validates quality
- `done` — archived

Each phase transition is a **checkpoint** recorded in the event stream.

## Workflow

1. **Create** → `job_supervisor_create(title, description, owner=?, reviewer=?, deliverables=[...], acceptance=[...])`
2. **Confirm** → `job_supervisor_checkpoint(job_id, "confirmed", who="agent-001", note="understood")`
3. **Plan** → `job_supervisor_checkpoint(job_id, "planned", who="agent-001", note="approach: ...")`
4. **Execute** → `job_supervisor_update(job_id, state="Running", append_log="...")`
5. **Self-check** → `job_supervisor_self_check(job_id, deliverables_done=[...], acceptance_passed=[...])`
6. **Review** → `job_supervisor_checkpoint(job_id, "reviewed", who="human", note="pass")`
7. **Evaluate** → `job_supervisor_evaluate(job_id, "design-alignment", "Pass")`
8. **Done** → `job_supervisor_update(job_id, state="Done")`

## Append-Only History

All updates append events. Past events are never overwritten.

```markdown
## 事件流 (append-only)

- [14:00] created — state=Todo
- [14:05] checkpoint — phase=confirmed, who=agent-001
- [14:10] checkpoint — phase=planned, who=human, note=approved
- [14:20] state_change — Todo → Running
- [14:40] self_check — deliverables 3/3, acceptance 3/3
- [14:50] checkpoint — phase=reviewed, who=human, note=pass
- [14:55] state_change — Running → Done
```

Frontmatter `state` and `phase` are caches for fast board scans. The event stream is the source of truth.

## When to use

- User wants to create tracked work items
- User asks about progress ("看看进度", "board status")
- Recording phase confirmations ("确认了", "方案通过")
- Self-check after completing work
- Evaluation by external skill

## Deck Note

This skill loads board-management tools only. Worker skills (code-review, web-research) are loaded separately when executing a job.
