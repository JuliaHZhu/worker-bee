"""supervisor — Job board management for agent work tracking.

Jobs are Markdown files with YAML frontmatter. The board is a text
information field: humans read it, LLMs read it, git tracks it.

Design constraint: HISTORY IS APPEND-ONLY. Never overwrite past events.
State changes are recorded as events in the body; frontmatter state is
a derived cache for fast board scans.
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


def _ensure_dir() -> None:
    JOBS_DIR.mkdir(exist_ok=True)


def _parse_frontmatter(content: str) -> Tuple[Optional[dict], str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return None, content
    try:
        from skills import _parse_yamlish
        meta = _parse_yamlish(m.group(1))
    except Exception:
        meta = {}
    return meta, content[m.end():].strip()


def _render_frontmatter(meta: dict) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---\n")
    return "\n".join(lines)


def _read_index() -> dict:
    _ensure_dir()
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text())
        except Exception:
            pass
    return {"schema_version": 1, "last_id": 0, "jobs": {}}


def _write_index(index: dict) -> None:
    INDEX_FILE.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")


def _next_job_id() -> str:
    index = _read_index()
    idx = index["last_id"] + 1
    index["last_id"] = idx
    _write_index(index)
    return f"JOB-{idx:03d}"


def _update_index_entry(job_id: str, meta: dict) -> None:
    index = _read_index()
    index["jobs"][job_id] = {
        "state": meta.get("state", "Todo"),
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
        # Find end of event-stream section (next ## or EOF) and insert there
        parts = body.split(marker, 1)
        before = parts[0]
        after = parts[1]
        # after starts with " (append-only)\n\n..." or "\n\n..."
        # Find next section header (## ) or end of string
        next_section = after.find("\n## ", 1)
        if next_section == -1:
            section = after
            rest = ""
        else:
            section = after[:next_section]
            rest = after[next_section:]
        # Append line to section
        section = section.rstrip("\n") + "\n" + line
        return before + marker + section + rest
    return body + f"\n{marker} (append-only)\n\n{line}"


# ── Public tools ────────────────────────────────────────────────────

def supervisor_status() -> str:
    """Return a human-readable Kanban board summary."""
    _ensure_dir()
    jobs = []
    for p in sorted(JOBS_DIR.glob("JOB-*.md")):
        meta, _ = _parse_job(p)
        jobs.append({
            "id": meta.get("id", p.stem),
            "title": meta.get("title", "(untitled)"),
            "state": meta.get("state", "Todo"),
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
                skill_hint = f"  [{j['skills']}]" if j["skills"] else ""
                lines.append(f"- {j['id']}: {j['title']}{skill_hint}")
            lines.append("")

    return "\n".join(lines)


def supervisor_read(job_id: str) -> str:
    """Read the full Markdown of a job."""
    _ensure_dir()
    path = JOBS_DIR / f"{job_id}.md"
    if not path.exists():
        return f"Error: {job_id} not found."
    return path.read_text()


def supervisor_create(title: str, description: str,
                      skills: Optional[List[str]] = None) -> str:
    """Create a new job file and return its ID."""
    _ensure_dir()
    job_id = _next_job_id()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta = {
        "id": job_id,
        "title": title,
        "skills": skills or [],
        "state": "Todo",
        "priority": 2,
        "created": now,
        "updated": now,
    }
    body = f"## 任务描述\n{description}\n\n## 事件流 (append-only)\n\n"
    body += f"- [{time.strftime('%H:%M', time.gmtime())}] created — state=Todo\n"
    content = _render_frontmatter(meta) + body
    path = JOBS_DIR / f"{job_id}.md"
    path.write_text(content)
    _update_index_entry(job_id, meta)
    return f"Created {job_id}: {title}"


def supervisor_update(job_id: str, state: Optional[str] = None,
                      append_log: Optional[str] = None) -> str:
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
        path.write_text(new_content)
        _update_index_entry(job_id, meta)

    return f"Updated {job_id}"


def supervisor_evaluate(job_id: str, eval_skill: str,
                        eval_result: str) -> str:
    """Append an evaluation result to a job's event stream.

    eval_skill: name of the skill that performed evaluation (e.g. design-alignment)
    eval_result: short conclusion (Pass / NeedClarify / NeedMeeting / ...)
    """
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
    path.write_text(new_content)
    _update_index_entry(job_id, meta)
    return f"Evaluated {job_id} with {eval_skill}: {eval_result}"


def supervisor_delete(job_id: str) -> str:
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
    from registry import registry

    registry.register(
        name="supervisor_status",
        description="Read the job board and return a Kanban summary (Todo/Running/Blocked/Done).",
        parameters={"type": "object", "properties": {}},
        handler=supervisor_status,
    )
    registry.register(
        name="supervisor_read",
        description="Read the full Markdown content of a specific job by ID.",
        parameters={
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job ID, e.g. JOB-001"},
            },
            "required": ["job_id"],
        },
        handler=supervisor_read,
    )
    registry.register(
        name="supervisor_create",
        description="Create a new job with title, description, and optional skills. Returns job ID.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "skills": {"type": "array", "items": {"type": "string"},
                           "description": "Skill names for Deck assembly"},
            },
            "required": ["title", "description"],
        },
        handler=supervisor_create,
    )
    registry.register(
        name="supervisor_update",
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
        handler=supervisor_update,
    )
    registry.register(
        name="supervisor_evaluate",
        description="Append an evaluation result to a job's event stream. eval_skill is the skill name that performed the evaluation; eval_result is the conclusion (Pass/NeedClarify/NeedMeeting).",
        parameters={
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "eval_skill": {"type": "string", "description": "Skill that performed evaluation, e.g. design-alignment"},
                "eval_result": {"type": "string", "description": "Conclusion: Pass, NeedClarify, NeedMeeting, etc."},
            },
            "required": ["job_id", "eval_skill", "eval_result"],
        },
        handler=supervisor_evaluate,
    )
    registry.register(
        name="supervisor_delete",
        description="Delete a job from the board.",
        parameters={
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
        },
        handler=supervisor_delete,
    )
except ImportError:
    pass
