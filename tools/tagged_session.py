"""Tagged Session tools — operate on session messages via the SessionDB.

These tools let the agent tag, archive (rewind), list, and close sessions
programmatically. The session_id is passed explicitly so the agent can
operate on any session it knows about.
"""
import json
import os
from pathlib import Path

from registry import registry
from memory import SessionDB


def _get_wiki_path() -> Path:
    default = Path.home() / "wiki-hermes-lite"
    return Path(os.environ.get("WIKI_PATH", str(default)))


def session_tag_message(session_id: str, message_id: int, tag: str) -> str:
    """Tag a single message with a semantic label (e.g. #design, #coding)."""
    db = SessionDB()
    ok = db.tag_message(message_id, tag)
    if not ok:
        return f"Error: message {message_id} not found"
    return f"Tagged message {message_id} with {tag}"


def session_untag_message(session_id: str, message_id: int, tag: str) -> str:
    """Remove a tag from a message."""
    db = SessionDB()
    ok = db.untag_message(message_id, tag)
    if not ok:
        return f"Error: message {message_id} not found"
    return f"Removed {tag} from message {message_id}"


def session_list_messages(session_id: str, include_archived: bool = False) -> str:
    """List messages in a session, with IDs and tags. Use this to show the user a numbered list so they can pick messages to tag."""
    db = SessionDB()
    msgs = db.get_messages(session_id, include_archived=include_archived)
    if not msgs:
        return "No messages in this session."
    lines = []
    for m in msgs:
        mid = m["id"]
        role = m["role"]
        content = m["content"][:60].replace("\n", " ")
        tags = m.get("tags", [])
        tag_str = f"  tags: {', '.join(tags)}" if tags else ""
        archived = "  [ARCHIVED]" if m.get("archived_at") else ""
        lines.append(f"  [{mid}] {role:10} | {content}...{tag_str}{archived}")
    return "\n".join(lines)


def session_archive_after(session_id: str, message_id: int) -> str:
    """Soft-archive all messages AFTER the given message ID (rewind). The message itself stays active."""
    db = SessionDB()
    db.archive_messages_after(session_id, message_id)
    return f"Archived all messages after {message_id}"


def session_archive_from(session_id: str, message_id: int) -> str:
    """Soft-archive the given message and all messages AFTER it."""
    db = SessionDB()
    db.archive_messages_from(session_id, message_id)
    return f"Archived messages from {message_id} onward"


def session_unarchive_all(session_id: str) -> str:
    """Restore all archived messages in the session."""
    db = SessionDB()
    db.unarchive_all(session_id)
    return "Unarchived all messages"


def session_set_purpose(session_id: str, purpose: str) -> str:
    """Set the purpose / intent of the current session."""
    db = SessionDB()
    db.set_session_purpose(session_id, purpose)
    return f"Session purpose set to: {purpose}"


def session_get_meta(session_id: str) -> str:
    """Get session metadata: purpose, closed_at, wiki_path."""
    db = SessionDB()
    meta = db.get_session_meta(session_id)
    if not meta:
        return f"Session {session_id} not found"
    return json.dumps(meta, ensure_ascii=False, indent=2)


def session_close(session_id: str, extract_to_wiki: bool = False) -> str:
    """Close a session. Optionally write the full transcript to wiki/raw/sessions/."""
    db = SessionDB()
    meta = db.get_session_meta(session_id)
    if not meta:
        return f"Session {session_id} not found"

    wiki_path = None
    if extract_to_wiki:
        wiki_root = _get_wiki_path()
        wiki_sessions = wiki_root / "raw" / "sessions"
        wiki_sessions.mkdir(parents=True, exist_ok=True)

        msgs = db.get_messages(session_id, include_archived=True)
        lines = [
            "---",
            f"source_type: hermes-lite-session",
            f"session_id: {session_id}",
            f"purpose: {meta.get('purpose') or ''}",
            f"created: {meta.get('created_at') or ''}",
            f"closed: {meta.get('closed_at') or ''}",
            f"tags: []",
            f"total_messages: {len(msgs)}",
            "---",
            "",
            f"# Session {session_id}",
            "",
        ]
        for m in msgs:
            role = m["role"]
            content = m["content"]
            tags = m.get("tags", [])
            tag_str = f"  tags: {', '.join(tags)}" if tags else ""
            archived = "  [ARCHIVED]" if m.get("archived_at") else ""
            lines.append(f"## [{m['id']}] {role} | {m.get('created_at', '')}{tag_str}{archived}")
            lines.append(content)
            lines.append("")

        out_file = wiki_sessions / f"session-{session_id}.md"
        out_file.write_text("\n".join(lines), encoding="utf-8")
        wiki_path = str(out_file)

    db.close_session(session_id, wiki_path=wiki_path)
    result = f"Session {session_id} closed"
    if wiki_path:
        result += f". Extracted to {wiki_path}"
    return result


# ── Register with registry ──────────────────────────────────────────

registry.register(
    name="session_tag_message",
    description="Tag a single message with a semantic label like #design or #coding. Use after listing messages so the user can pick by ID.",
    parameters={
        "properties": {
            "session_id": {"type": "string", "description": "Session ID"},
            "message_id": {"type": "integer", "description": "Message database ID"},
            "tag": {"type": "string", "description": "Tag to add, e.g. #design"}
        },
        "required": ["session_id", "message_id", "tag"]
    },
    handler=session_tag_message,
    tags=["session", "tag"],
    category="tagged_session"
)

registry.register(
    name="session_untag_message",
    description="Remove a tag from a message.",
    parameters={
        "properties": {
            "session_id": {"type": "string", "description": "Session ID"},
            "message_id": {"type": "integer", "description": "Message database ID"},
            "tag": {"type": "string", "description": "Tag to remove"}
        },
        "required": ["session_id", "message_id", "tag"]
    },
    handler=session_untag_message,
    tags=["session", "tag"],
    category="tagged_session"
)

registry.register(
    name="session_list_messages",
    description="List messages in a session with their IDs and tags. Use this FIRST when the user wants to tag or review past messages.",
    parameters={
        "properties": {
            "session_id": {"type": "string", "description": "Session ID"},
            "include_archived": {"type": "boolean", "description": "Whether to include archived (rewound) messages", "default": False}
        },
        "required": ["session_id"]
    },
    handler=session_list_messages,
    tags=["session", "list"],
    category="tagged_session"
)

registry.register(
    name="session_archive_after",
    description="Soft-archive all messages AFTER the given message ID. The message itself stays active. Equivalent to 'rewind to here'.",
    parameters={
        "properties": {
            "session_id": {"type": "string", "description": "Session ID"},
            "message_id": {"type": "integer", "description": "Message ID to rewind after"}
        },
        "required": ["session_id", "message_id"]
    },
    handler=session_archive_after,
    tags=["session", "archive", "rewind"],
    category="tagged_session"
)

registry.register(
    name="session_archive_from",
    description="Soft-archive the given message and all messages after it.",
    parameters={
        "properties": {
            "session_id": {"type": "string", "description": "Session ID"},
            "message_id": {"type": "integer", "description": "Message ID to start archiving from"}
        },
        "required": ["session_id", "message_id"]
    },
    handler=session_archive_from,
    tags=["session", "archive", "rewind"],
    category="tagged_session"
)

registry.register(
    name="session_unarchive_all",
    description="Restore all archived messages in the session.",
    parameters={
        "properties": {
            "session_id": {"type": "string", "description": "Session ID"}
        },
        "required": ["session_id"]
    },
    handler=session_unarchive_all,
    tags=["session", "archive", "rewind"],
    category="tagged_session"
)

registry.register(
    name="session_set_purpose",
    description="Set the purpose / intent of a session. This replaces the old /task add concept.",
    parameters={
        "properties": {
            "session_id": {"type": "string", "description": "Session ID"},
            "purpose": {"type": "string", "description": "Short description of what this session is for"}
        },
        "required": ["session_id", "purpose"]
    },
    handler=session_set_purpose,
    tags=["session", "meta"],
    category="tagged_session"
)

registry.register(
    name="session_get_meta",
    description="Get session metadata (purpose, closed_at, wiki_path).",
    parameters={
        "properties": {
            "session_id": {"type": "string", "description": "Session ID"}
        },
        "required": ["session_id"]
    },
    handler=session_get_meta,
    tags=["session", "meta"],
    category="tagged_session"
)

registry.register(
    name="session_close",
    description="Close a session. Optionally extract the full transcript to the wiki raw/sessions/ folder.",
    parameters={
        "properties": {
            "session_id": {"type": "string", "description": "Session ID"},
            "extract_to_wiki": {"type": "boolean", "description": "Whether to write transcript to wiki/raw/sessions/", "default": False}
        },
        "required": ["session_id"]
    },
    handler=session_close,
    tags=["session", "close", "wiki"],
    category="tagged_session"
)
