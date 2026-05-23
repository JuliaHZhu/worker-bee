"""Tagged Session — one chef, one counter.

Stack semantics:
  save   → procure a live session from DB, write to markdown note
  tag    → label it
  find   → draw by tag intersection
  archive→ halt (move to archive pool)
  resume → draw back into context
  list   → inspect the active pool

Storage: ~/wiki-hermes-lite/sessions/*.md
Archive: ~/wiki-hermes-lite/sessions/archive/*.md
"""
import json
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from registry import registry


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def _base_dir() -> Path:
    default = Path.home() / "wiki-hermes-lite" / "sessions"
    return Path(os.environ.get("SESSIONS_PATH", str(default)))


def _ensure_dirs():
    _base_dir().mkdir(parents=True, exist_ok=True)
    (_base_dir() / "archive").mkdir(parents=True, exist_ok=True)


def _note_path(session_id: str, archived: bool = False) -> Path:
    base = _base_dir() / "archive" if archived else _base_dir()
    return base / f"{session_id}.md"


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------
def _read_frontmatter(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    meta = {}
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line:
            i += 1
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if v:
            if v.startswith("[") and v.endswith("]"):
                try:
                    v = json.loads(v.replace("'", '"'))
                except (json.JSONDecodeError, ValueError):
                    v = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
            elif v == "true":
                v = True
            elif v == "false":
                v = False
            meta[k] = v
            i += 1
        else:
            # Possible YAML list: read subsequent lines starting with "- "
            i += 1
            items = []
            while i < len(lines):
                next_line = lines[i].rstrip()
                if not next_line:
                    i += 1
                    continue
                if next_line.strip().startswith("-"):
                    items.append(next_line.strip()[1:].strip())
                    i += 1
                else:
                    break
            meta[k] = items if items else ""
    return meta


def _write_frontmatter(path: Path, meta: dict, body: str):
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        elif isinstance(v, bool):
            lines.append(f"{k}: {str(v).lower()}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    body = body.lstrip("\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n\n" + body, encoding="utf-8")


def _build_body(messages: list) -> str:
    lines = []
    for m in messages:
        role = m.get("role", "unknown")
        ts = m.get("created_at", "")
        content = m.get("content", "")
        msg_tags = m.get("tags", [])
        tag_str = f" | tags: {', '.join(msg_tags)}" if msg_tags else ""
        lines.append(f"## {role} | {ts}{tag_str}")
        lines.append(content)
        lines.append("")
    return "\n".join(lines)


def _all_notes(archived: bool = False) -> list:
    base = _base_dir() / "archive" if archived else _base_dir()
    if not base.exists():
        return []
    return sorted(base.glob("*.md"))


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
def _action_save(session_id: str, content: Optional[str]) -> str:
    if not session_id:
        return "❌ 需要 session"

    from memory import SessionDB
    db = SessionDB()
    meta = db.get_session_meta(session_id)
    if not meta:
        return f"❌ Session {session_id} 不存在"

    msgs = db.get_messages(session_id, include_archived=True)
    title = content or meta.get("title") or meta.get("purpose") or f"Session {session_id}"
    purpose = meta.get("purpose") or ""
    created = meta.get("created_at") or ""

    all_tags = set()
    for m in msgs:
        for t in m.get("tags", []):
            all_tags.add(t)

    frontmatter = {
        "session_id": session_id,
        "title": title,
        "purpose": purpose,
        "tags": sorted(all_tags),
        "created": created,
        "archived": False,
        "source": "hermes-lite",
    }
    body = _build_body(msgs)

    _ensure_dirs()
    path = _note_path(session_id)
    _write_frontmatter(path, frontmatter, body)
    return f"✅ 已保存到 {path} (共 {len(msgs)} 条消息)"


def _action_tag(session_id: str, content: Optional[str]) -> str:
    if not session_id:
        return "❌ 需要 session"
    if not content:
        return "❌ 需要 content (格式: +tag1,-tag2 或 #tag1,#tag2)"

    path = _note_path(session_id)
    if not path.exists():
        path = _note_path(session_id, archived=True)
    if not path.exists():
        return f"❌ Session note {session_id} 不存在"

    meta = _read_frontmatter(path)
    tags = set(meta.get("tags", []))

    for part in content.split(","):
        part = part.strip()
        if not part:
            continue
        if part.startswith("+"):
            tags.add(part[1:])
        elif part.startswith("-"):
            tags.discard(part[1:])
        elif part.startswith("#"):
            tags.add(part)
        else:
            tags.add(part)

    meta["tags"] = sorted(tags)
    body_text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n.*?\n---\s*\n", body_text, re.DOTALL)
    body = body_text[m.end():] if m else body_text
    _write_frontmatter(path, meta, body)
    return f"✅ 标签已更新: {', '.join(sorted(tags))}"


def _action_find(content: Optional[str]) -> str:
    if not content:
        return "❌ 需要 content (逗号分隔的标签)"

    query_tags = [t.strip() for t in content.split(",") if t.strip()]
    if not query_tags:
        return "❌ 至少需要一个标签"

    _ensure_dirs()
    results = []
    for path in _all_notes():
        meta = _read_frontmatter(path)
        note_tags = set(meta.get("tags", []))
        if all(t in note_tags for t in query_tags):
            results.append({
                "session_id": meta.get("session_id", path.stem),
                "title": meta.get("title", path.stem),
                "tags": sorted(note_tags),
                "created": meta.get("created", ""),
            })

    if not results:
        return f"📭 没有找到带标签 {query_tags} 的 session"

    lines = [f"═══ 找到 {len(results)} 个 session ═══", ""]
    for r in results:
        lines.append(f"  • {r['session_id']}: {r['title']}")
        lines.append(f"    tags: {', '.join(r['tags'])}  ({r['created'][:10]})")
    return "\n".join(lines)


def _action_archive(session_id: str) -> str:
    if not session_id:
        return "❌ 需要 session"

    src = _note_path(session_id)
    if not src.exists():
        return f"❌ Session note {session_id} 不存在"

    _ensure_dirs()
    dst = _note_path(session_id, archived=True)
    shutil.move(str(src), str(dst))

    meta = _read_frontmatter(dst)
    meta["archived"] = True
    body_text = dst.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n.*?\n---\s*\n", body_text, re.DOTALL)
    body = body_text[m.end():] if m else body_text
    _write_frontmatter(dst, meta, body)

    return f"✅ 已归档 {session_id}"


def _action_resume(session_id: str) -> str:
    if not session_id:
        return "❌ 需要 session"

    path = _note_path(session_id)
    if not path.exists():
        path = _note_path(session_id, archived=True)
    if not path.exists():
        return f"❌ Session note {session_id} 不存在"

    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
    body = text[m.end():] if m else text
    preview = body.strip()[:3000]
    if len(body.strip()) > 3000:
        preview += "\n\n... (已截断)"
    return f"═══ Session {session_id} 内容 ═══\n\n{preview}"


def _action_list() -> str:
    _ensure_dirs()
    notes = _all_notes()
    if not notes:
        return "📭 暂无已保存的 session"

    lines = [f"═══ 已保存的 sessions ({len(notes)}) ═══", ""]
    for path in notes:
        meta = _read_frontmatter(path)
        sid = meta.get("session_id", path.stem)
        title = meta.get("title", "无标题")
        tags = meta.get("tags", [])
        tag_str = f"  [{', '.join(tags)}]" if tags else ""
        created = meta.get("created", "")[:10]
        lines.append(f"  • {sid}: {title}{tag_str}  ({created})")
    return "\n".join(lines)


def _action_help() -> str:
    return (
        "═══ Tagged Session 帮助 ═══\n\n"
        "用法: tagged_session(action='...', [session=..., content=...])\n\n"
        "  save    — 保存当前 session 为 markdown note (session=ID, content=标题)\n"
        "  tag     — 修改标签 (session=ID, content=+tag1,-tag2 或 #tag1,#tag2)\n"
        "  find    — 按标签搜索 (content=逗号分隔的标签)\n"
        "  archive — 归档 note (session=ID)\n"
        "  resume  — 读取 note 内容 (session=ID)\n"
        "  list    — 列出所有活跃 notes\n"
        "  help    — 显示本帮助"
    )


# ---------------------------------------------------------------------------
# Public handler
# ---------------------------------------------------------------------------
def tagged_session(
    action: str,
    session: Optional[str] = None,
    content: Optional[str] = None,
) -> str:
    """Tagged Session — save, tag, find, archive, and resume sessions as markdown notes.

    Args:
        action: 操作类型
        session: Session ID
        content: 标题 / 标签 / 搜索查询
    """
    action = action.lower().strip()
    dispatch = {
        "save": lambda: _action_save(session or "", content),
        "new": lambda: _action_save(session or "", content),
        "tag": lambda: _action_tag(session or "", content),
        "find": lambda: _action_find(content),
        "archive": lambda: _action_archive(session or ""),
        "resume": lambda: _action_resume(session or ""),
        "list": lambda: _action_list(),
        "help": lambda: _action_help(),
    }
    handler = dispatch.get(action)
    if not handler:
        return f"❌ 未知 action: {action}\n可用: {', '.join(dispatch.keys())}"
    try:
        return handler()
    except Exception as e:
        return f"❌ 执行失败: {e}"


registry.register(
    name="tagged_session",
    description=(
        "Tagged Session — 把对话 session 保存为可搜索的 markdown 笔记，支持标签、归档、回溯。\n"
        "Actions: save, tag, find, archive, resume, list, help"
    ),
    parameters={
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["save", "tag", "find", "archive", "resume", "list", "help"]
            },
            "session": {
                "type": "string",
                "description": "Session ID"
            },
            "content": {
                "type": "string",
                "description": "标题 / 标签 / 搜索查询"
            }
        },
        "required": ["action"]
    },
    handler=tagged_session,
    tags=["session", "tag", "archive", "wiki"],
    category="tagged_session"
)
