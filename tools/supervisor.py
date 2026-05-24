"""supervisor — Job board management for agent work tracking.

Jobs are Markdown files with YAML frontmatter. The board is a text
information field: humans read it, LLMs read it, git tracks it.
"""
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Config ──────────────────────────────────────────────────────────
JOBS_DIR = Path(__file__).parent.parent / "jobs"
INDEX_FILE = JOBS_DIR / "_index.json"


def _ensure_dir() -> None:
    JOBS_DIR.mkdir(exist_ok=True)


def _parse_frontmatter(content: str) -> Tuple[Optional[dict], str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return None, content
    # Re-use the lightweight yamlish parser from skills.py
    try:
        from skills import _parse_yamlish
        meta = _parse_yamlish(m.group(1))
    except Exception:
        # Fallback: empty meta so the file is still readable
        meta = {}
    return meta, content[m.end():].strip()


def _render_frontmatter(meta: dict) -> str:
    """Render minimal YAML frontmatter (enough for our schema)."""
    lines = ["---"]
    for k, v in sorted(meta.items()) if False else meta.items():
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

    # Group by state
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
    body = f"## 任务描述\n{description}\n\n## 执行记录\n\n## 阻塞记录\n"
    content = _render_frontmatter(meta) + body
    path = JOBS_DIR / f"{job_id}.md"
    path.write_text(content)
    _update_index_entry(job_id, meta)
    return f"Created {job_id}: {title}"


def supervisor_update(job_id: str, state: Optional[str] = None,
                      append_log: Optional[str] = None) -> str:
    """Update job state and/or append a log line."""
    _ensure_dir()
    path = JOBS_DIR / f"{job_id}.md"
    if not path.exists():
        return f"Error: {job_id} not found."

    content = path.read_text()
    meta, body = _parse_frontmatter(content)
    if meta is None:
        meta = {}

    changed = False
    if state and state in ("Todo", "Running", "Done", "Blocked"):
        meta["state"] = state
        changed = True

    if append_log:
        ts = time.strftime("%H:%M", time.gmtime())
        log_line = f"- [{ts}] {append_log}\n"
        if "## 执行记录" in body:
            body = body.replace("## 执行记录\n", "## 执行记录\n" + log_line)
        else:
            body += f"\n## 执行记录\n{log_line}"
        changed = True

    if changed:
        meta["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        new_content = _render_frontmatter(meta) + body
        path.write_text(new_content)
        _update_index_entry(job_id, meta)

    return f"Updated {job_id}"


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
        parameters={
            "type": "object",
            "properties": {},
        },
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
        description="Update a job's state (Todo/Running/Done/Blocked) and/or append a log line.",
        parameters={
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "state": {"type": "string", "enum": ["Todo", "Running", "Done", "Blocked"]},
                "append_log": {"type": "string"},
            },
            "required": ["job_id"],
        },
        handler=supervisor_update,
    )
    registry.register(
        name="supervisor_delete",
        description="Delete a job from the board.",
        parameters={
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
            },
            "required": ["job_id"],
        },
        handler=supervisor_delete,
    )
except ImportError:
    pass  # standalone import guard
