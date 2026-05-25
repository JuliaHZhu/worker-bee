"""job_supervisor — Job board management with delivery-quality tracking.

Jobs are Markdown files with YAML frontmatter. Each job tracks:
- What: title + description + skills
- Who: owner (responsible) + reviewer (validator)
- Deliverables: checklist of artifacts to produce
- Acceptance: checklist of quality gates

Phase checkpoints (append-only):
    created → confirmed → planned → executing → self_checked → reviewed → done

Design: text-as-model. All history is append-only. Frontmatter state is a cache.
"""
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Config ──────────────────────────────────────────────────────────
JOBS_DIR = Path(__file__).parent.parent / "jobs"
INDEX_FILE = JOBS_DIR / "_index.json"

_VALID_STATES = ("Todo", "Running", "Done", "Blocked")
_VALID_PHASES = (
    "created", "confirmed", "planned", "executing",
    "self_checked", "reviewed", "done",
)


def _ensure_dir() -> None:
    JOBS_DIR.mkdir(exist_ok=True)


_LIST_FIELDS = {"skills", "deliverables", "acceptance"}


def _parse_frontmatter(content: str) -> Tuple[Optional[dict], str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return None, content
    try:
        from worker_bee.skills import _parse_yamlish
        meta = _parse_yamlish(m.group(1))
    except Exception:
        meta = {}
    # Type correction: known list fields should be lists
    for k in _LIST_FIELDS:
        if k in meta and not isinstance(meta[k], list):
            if meta[k] in ("", None):
                meta[k] = []
            else:
                meta[k] = [meta[k]]
    return meta, content[m.end():].strip()


def _render_frontmatter(meta: dict) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---\n")
    return "\n".join(lines)


def _atomic_write(path: Path, content: str) -> None:
    """Atomic file write via temp file + rename."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _read_index() -> dict:
    _ensure_dir()
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text())
        except Exception:
            pass
    return {"schema_version": 1, "last_id": 0, "jobs": {}}


def _write_index(index: dict) -> None:
    _atomic_write(INDEX_FILE, json.dumps(index, indent=2, ensure_ascii=False) + "\n")


def _next_job_id() -> str:
    index = _read_index()
    idx = index["last_id"]
    if idx == 0:
        # Index may be empty/corrupted — scan disk for existing IDs
        existing = sorted(JOBS_DIR.glob("JOB-*.md"))
        if existing:
            max_id = 0
            for p in existing:
                m = re.match(r"JOB-(\d+)", p.stem)
                if m:
                    max_id = max(max_id, int(m.group(1)))
            idx = max_id
    idx += 1
    index["last_id"] = idx
    _write_index(index)
    return f"JOB-{idx:03d}"


def _update_index_entry(job_id: str, meta: dict) -> None:
    index = _read_index()
    index["jobs"][job_id] = {
        "state": meta.get("state", "Todo"),
        "phase": meta.get("phase", "created"),
        "title": meta.get("title", ""),
        "updated": meta.get("updated", ""),
    }
    _write_index(index)


def _parse_job(path: Path) -> Tuple[dict, str]:
    content = path.read_text()
    meta, body = _parse_frontmatter(content)
    return meta or {}, body


def _append_event(body: str, event: str) -> str:
    """Append an event line to the ## 事件流 section."""
    ts = time.strftime("%H:%M", time.gmtime())
    line = f"- [{ts}] {event}\n"
    marker = "## 事件流"
    if marker in body:
        parts = body.split(marker, 1)
        before = parts[0]
        after = parts[1]
        # Find end of event-stream section (next ## or EOF)
        next_section = after.find("\n## ", 1)
        if next_section == -1:
            section = after
            rest = ""
        else:
            section = after[:next_section]
            rest = after[next_section:]
        section = section.rstrip("\n") + "\n" + line
        return before + marker + section + rest
    return body + f"\n{marker} (append-only)\n\n{line}"


# ── Public tools ────────────────────────────────────────────────────

def job_supervisor_status() -> str:
    """Return a human-readable Kanban board summary."""
    _ensure_dir()
    jobs = []
    for p in sorted(JOBS_DIR.glob("JOB-*.md")):
        meta, _ = _parse_job(p)
        jobs.append({
            "id": meta.get("id", p.stem),
            "title": meta.get("title", "(untitled)"),
            "state": meta.get("state", "Todo"),
            "phase": meta.get("phase", "created"),
            "owner": meta.get("owner", ""),
            "skills": ", ".join(meta.get("skills", [])),
        })

    if not jobs:
        return "Board is empty. No jobs yet."

    states = {"Todo": [], "Running": [], "Done": [], "Blocked": []}
    for j in jobs:
        states.setdefault(j["state"], []).append(j)

    lines = ["# Job Board", ""]
    for st in ["Todo", "Running", "Blocked", "Done"]:
        entries = states.get(st, [])
        if entries:
            lines.append(f"## {st} ({len(entries)})")
            for j in entries:
                phase_hint = f" ({j['phase']})" if j["phase"] != "created" else ""
                owner_hint = f" @{j['owner']}" if j["owner"] else ""
                skill_hint = f" [{j['skills']}]" if j["skills"] else ""
                lines.append(f"- {j['id']}: {j['title']}{phase_hint}{owner_hint}{skill_hint}")
            lines.append("")

    return "\n".join(lines)


def job_supervisor_read(job_id: str) -> str:
    """Read the full Markdown of a job."""
    _ensure_dir()
    path = JOBS_DIR / f"{job_id}.md"
    if not path.exists():
        return f"Error: {job_id} not found."
    return path.read_text()


def job_supervisor_create(
    title: str,
    description: str,
    skills: Optional[List[str]] = None,
    owner: str = "",
    reviewer: str = "",
    deliverables: Optional[List[str]] = None,
    acceptance: Optional[List[str]] = None,
) -> str:
    """Create a new job file and return its ID.

    Four elements of delivery quality:
      - owner: who is responsible
      - reviewer: who validates
      - deliverables: what artifacts to produce
      - acceptance: quality gates to pass
    """
    _ensure_dir()
    job_id = _next_job_id()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta = {
        "id": job_id,
        "title": title,
        "owner": owner,
        "reviewer": reviewer,
        "skills": skills or [],
        "deliverables": deliverables or [],
        "acceptance": acceptance or [],
        "state": "Todo",
        "phase": "created",
        "priority": 2,
        "created": now,
        "updated": now,
    }
    body = f"## 任务描述\n{description}\n\n"
    body += "## 交付物\n"
    for d in (deliverables or []):
        body += f"- [ ] {d}\n"
    body += "\n## 验收标准\n"
    for a in (acceptance or []):
        body += f"- [ ] {a}\n"
    body += "\n## 事件流 (append-only)\n\n"
    body += f"- [{time.strftime('%H:%M', time.gmtime())}] created — state=Todo\n"
    content = _render_frontmatter(meta) + body
    path = JOBS_DIR / f"{job_id}.md"
    _atomic_write(path, content)
    _update_index_entry(job_id, meta)
    return f"Created {job_id}: {title}"


def job_supervisor_update(
    job_id: str,
    state: Optional[str] = None,
    append_log: Optional[str] = None,
) -> str:
    """Update job state and/or append a log/event line. All history is append-only."""
    _ensure_dir()
    path = JOBS_DIR / f"{job_id}.md"
    if not path.exists():
        return f"Error: {job_id} not found."

    content = path.read_text()
    meta, body = _parse_frontmatter(content)
    if meta is None:
        meta = {}

    changed = False
    old_state = meta.get("state", "Todo")

    if state and state in _VALID_STATES and state != old_state:
        meta["state"] = state
        body = _append_event(body, f"state_change — {old_state} → {state}")
        changed = True

    if append_log:
        body = _append_event(body, f"log — {append_log}")
        changed = True

    if changed:
        meta["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        new_content = _render_frontmatter(meta) + body
        _atomic_write(path, new_content)
        _update_index_entry(job_id, meta)

    return f"Updated {job_id}"


def job_supervisor_checkpoint(
    job_id: str,
    phase: str,
    who: str,
    note: str = "",
) -> str:
    """Record a phase checkpoint. Phase must be one of the valid lifecycle phases.

    Phases: created → confirmed → planned → executing → self_checked → reviewed → done
    """
    if phase not in _VALID_PHASES:
        return f"Error: phase '{phase}' invalid. Valid: {', '.join(_VALID_PHASES)}"

    _ensure_dir()
    path = JOBS_DIR / f"{job_id}.md"
    if not path.exists():
        return f"Error: {job_id} not found."

    content = path.read_text()
    meta, body = _parse_frontmatter(content)
    if meta is None:
        meta = {}

    meta["phase"] = phase
    event = f"checkpoint — phase={phase}, who={who}"
    if note:
        event += f", note={note}"
    body = _append_event(body, event)

    meta["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    new_content = _render_frontmatter(meta) + body
    _atomic_write(path, new_content)
    _update_index_entry(job_id, meta)

    return f"Checkpoint {job_id}: {phase} by {who}"


def job_supervisor_self_check(
    job_id: str,
    deliverables_done: Optional[List[str]] = None,
    acceptance_passed: Optional[List[str]] = None,
) -> str:
    """Owner self-check: verify deliverables and acceptance criteria.
    Automatically appends a checkpoint event."""
    _ensure_dir()
    path = JOBS_DIR / f"{job_id}.md"
    if not path.exists():
        return f"Error: {job_id} not found."

    content = path.read_text()
    meta, body = _parse_frontmatter(content)
    if meta is None:
        meta = {}

    # Read expected deliverables / acceptance from meta
    expected_del = meta.get("deliverables", []) or []
    expected_acc = meta.get("acceptance", []) or []
    done_del = [d for d in (deliverables_done or []) if d in expected_del]
    passed_acc = [a for a in (acceptance_passed or []) if a in expected_acc]

    del_status = f"{len(done_del)}/{len(expected_del)}"
    acc_status = f"{len(passed_acc)}/{len(expected_acc)}"

    body = _append_event(
        body,
        f"self_check — deliverables {del_status}, acceptance {acc_status}"
    )

    # Also update the checklist in body if we can match items
    for d in done_del:
        body = body.replace(f"- [ ] {d}\n", f"- [x] {d}\n")
    for a in passed_acc:
        body = body.replace(f"- [ ] {a}\n", f"- [x] {a}\n")

    meta["phase"] = "self_checked"
    meta["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    new_content = _render_frontmatter(meta) + body
    _atomic_write(path, new_content)
    _update_index_entry(job_id, meta)

    return f"Self-check {job_id}: deliverables {del_status}, acceptance {acc_status}"


def job_supervisor_evaluate(
    job_id: str,
    eval_skill: str,
    eval_result: str,
) -> str:
    """Append an evaluation result to a job's event stream."""
    _ensure_dir()
    path = JOBS_DIR / f"{job_id}.md"
    if not path.exists():
        return f"Error: {job_id} not found."

    content = path.read_text()
    meta, body = _parse_frontmatter(content)
    if meta is None:
        meta = {}

    body = _append_event(body, f"eval — {eval_skill}: {eval_result}")
    meta["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    new_content = _render_frontmatter(meta) + body
    _atomic_write(path, new_content)
    _update_index_entry(job_id, meta)
    return f"Evaluated {job_id} with {eval_skill}: {eval_result}"


def job_supervisor_delete(job_id: str) -> str:
    """Delete a job file and its index entry."""
    _ensure_dir()
    path = JOBS_DIR / f"{job_id}.md"
    if not path.exists():
        return f"Error: {job_id} not found."
    path.unlink()
    index = _read_index()
    index["jobs"].pop(job_id, None)
    _write_index(index)
    return f"Deleted {job_id}"


# ── Registry registration ───────────────────────────────────────────
try:
    from worker_bee.registry import registry

    registry.register(
        name="job_supervisor_status",
        description="Read the job board and return a Kanban summary (Todo/Running/Blocked/Done).",
        parameters={"type": "object", "properties": {}},
        handler=job_supervisor_status,
    )
    registry.register(
        name="job_supervisor_read",
        description="Read the full Markdown content of a specific job by ID.",
        parameters={
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job ID, e.g. JOB-001"},
            },
            "required": ["job_id"],
        },
        handler=job_supervisor_read,
    )
    registry.register(
        name="job_supervisor_create",
        description="Create a new job with title, description, and optional skills, owner, reviewer, deliverables, acceptance. Returns job ID.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "skills": {"type": "array", "items": {"type": "string"}, "description": "Skill names for Deck assembly"},
                "owner": {"type": "string", "description": "Responsible agent/human"},
                "reviewer": {"type": "string", "description": "Validator agent/human"},
                "deliverables": {"type": "array", "items": {"type": "string"}, "description": "Artifacts to produce"},
                "acceptance": {"type": "array", "items": {"type": "string"}, "description": "Quality gates"},
            },
            "required": ["title", "description"],
        },
        handler=job_supervisor_create,
    )
    registry.register(
        name="job_supervisor_update",
        description="Update a job's state and/or append a log line. All history is append-only.",
        parameters={
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "state": {"type": "string", "enum": list(_VALID_STATES)},
                "append_log": {"type": "string"},
            },
            "required": ["job_id"],
        },
        handler=job_supervisor_update,
    )
    registry.register(
        name="job_supervisor_checkpoint",
        description="Record a phase checkpoint. Phases: created, confirmed, planned, executing, self_checked, reviewed, done.",
        parameters={
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "phase": {"type": "string", "enum": list(_VALID_PHASES)},
                "who": {"type": "string", "description": "Agent or human confirming this phase"},
                "note": {"type": "string"},
            },
            "required": ["job_id", "phase", "who"],
        },
        handler=job_supervisor_checkpoint,
    )
    registry.register(
        name="job_supervisor_self_check",
        description="Owner self-check: verify deliverables and acceptance criteria. Automatically appends a checkpoint.",
        parameters={
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "deliverables_done": {"type": "array", "items": {"type": "string"}},
                "acceptance_passed": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["job_id"],
        },
        handler=job_supervisor_self_check,
    )
    registry.register(
        name="job_supervisor_evaluate",
        description="Append an evaluation result. eval_skill is the skill name that performed evaluation; eval_result is Pass/NeedClarify/NeedMeeting.",
        parameters={
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "eval_skill": {"type": "string"},
                "eval_result": {"type": "string"},
            },
            "required": ["job_id", "eval_skill", "eval_result"],
        },
        handler=job_supervisor_evaluate,
    )
    registry.register(
        name="job_supervisor_delete",
        description="Delete a job from the board.",
        parameters={
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
        },
        handler=job_supervisor_delete,
    )
except ImportError:
    pass
