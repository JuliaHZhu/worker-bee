"""Tests for tagged_session tool — markdown I/O, actions, and registry integration."""
import tempfile
from pathlib import Path

import pytest

from memory import SessionDB


@pytest.fixture
def db():
    """SessionDB at default path so tagged_session internal code can find it."""
    path = Path("state.db")
    if path.exists():
        path.unlink()
    sdb = SessionDB(str(path))
    yield sdb
    try:
        path.unlink()
    except OSError:
        pass


@pytest.fixture
def sessions_dir(monkeypatch, temp_dir):
    """Redirect sessions storage to a temp directory."""
    sessions_path = temp_dir / "sessions"
    monkeypatch.setenv("SESSIONS_PATH", str(sessions_path))
    return sessions_path


# ---------------------------------------------------------------------------
# Frontmatter I/O
# ---------------------------------------------------------------------------
def test_frontmatter_roundtrip(sessions_dir):
    """_write_frontmatter and _read_frontmatter are inverses."""
    from tools.tagged_session import _write_frontmatter, _read_frontmatter

    path = sessions_dir / "test.md"
    meta = {
        "session_id": "abc123",
        "title": "Test Session",
        "purpose": "Design review",
        "tags": ["#design", "#review"],
        "created": "2026-05-23T10:00:00",
        "archived": False,
        "source": "hermes-lite",
    }
    body = "## user | 2026-05-23T10:00:00\nHello world\n\n## assistant | 2026-05-23T10:01:00\nHi there\n"
    _write_frontmatter(path, meta, body)

    assert path.exists()
    read_meta = _read_frontmatter(path)
    assert read_meta["session_id"] == "abc123"
    assert read_meta["title"] == "Test Session"
    assert read_meta["archived"] is False
    assert set(read_meta["tags"]) == {"#design", "#review"}


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
def test_save_creates_markdown(db, sessions_dir):
    """save action exports a session from DB to markdown."""
    from tools.tagged_session import tagged_session

    sid = db.create_session(title="Design Discussion")
    db.set_session_purpose(sid, "Review tagged session architecture")
    db.save_message(sid, "user", "How should we structure this?", tags=["#design"])
    db.save_message(sid, "assistant", "Use one chef, one counter.")

    result = tagged_session(action="save", session=sid, content="My Design Session")
    assert "已保存" in result

    note_path = sessions_dir / f"{sid}.md"
    assert note_path.exists()

    text = note_path.read_text(encoding="utf-8")
    assert "session_id:" in text
    assert "My Design Session" in text
    assert "How should we structure this?" in text
    assert "#design" in text


def test_tag_add_and_remove(sessions_dir):
    """tag action modifies frontmatter tags."""
    from tools.tagged_session import _write_frontmatter, _read_frontmatter, tagged_session

    path = sessions_dir / "test123.md"
    meta = {
        "session_id": "test123",
        "title": "Test",
        "tags": ["#design"],
        "created": "2026-05-23T10:00:00",
        "archived": False,
    }
    _write_frontmatter(path, meta, "body")

    # Add
    result = tagged_session(action="tag", session="test123", content="+#coding")
    assert "coding" in result
    meta = _read_frontmatter(path)
    assert "#coding" in meta["tags"]
    assert "#design" in meta["tags"]

    # Remove
    result = tagged_session(action="tag", session="test123", content="-#design")
    meta = _read_frontmatter(path)
    assert "#design" not in meta["tags"]


def test_find_by_tag_intersection(sessions_dir):
    """find action returns notes matching ALL requested tags."""
    from tools.tagged_session import _write_frontmatter, tagged_session

    for sid, tags in [("s1", ["#design", "#coding"]), ("s2", ["#design"]), ("s3", ["#coding"])]:
        path = sessions_dir / f"{sid}.md"
        _write_frontmatter(path, {
            "session_id": sid, "title": sid, "tags": tags,
            "created": "2026-05-23", "archived": False
        }, "body")

    result = tagged_session(action="find", content="#design,#coding")
    assert "s1" in result
    assert "s2" not in result
    assert "s3" not in result


def test_archive_moves_file(sessions_dir):
    """archive action moves note to archive/ and sets archived flag."""
    from tools.tagged_session import _write_frontmatter, tagged_session, _read_frontmatter

    path = sessions_dir / "s1.md"
    _write_frontmatter(path, {
        "session_id": "s1", "title": "S1", "tags": [],
        "created": "2026-05-23", "archived": False
    }, "body")

    result = tagged_session(action="archive", session="s1")
    assert "已归档" in result
    assert not path.exists()

    archived_path = sessions_dir / "archive" / "s1.md"
    assert archived_path.exists()
    meta = _read_frontmatter(archived_path)
    assert meta["archived"] is True


def test_resume_returns_content(sessions_dir):
    """resume action reads note body."""
    from tools.tagged_session import _write_frontmatter, tagged_session

    path = sessions_dir / "s1.md"
    _write_frontmatter(path, {
        "session_id": "s1", "title": "S1", "tags": [],
        "created": "2026-05-23", "archived": False
    }, "## user | 10:00\nHello\n\n## assistant | 10:01\nWorld\n")

    result = tagged_session(action="resume", session="s1")
    assert "Hello" in result
    assert "World" in result


def test_list_active_notes(sessions_dir):
    """list action shows only non-archived notes."""
    from tools.tagged_session import _write_frontmatter, tagged_session

    _write_frontmatter(sessions_dir / "a.md", {
        "session_id": "a", "title": "A", "tags": ["#design"],
        "created": "2026-05-23", "archived": False
    }, "body")
    _write_frontmatter(sessions_dir / "b.md", {
        "session_id": "b", "title": "B", "tags": [],
        "created": "2026-05-23", "archived": False
    }, "body")

    result = tagged_session(action="list")
    assert "A" in result
    assert "B" in result
    assert "#design" in result


def test_list_excludes_archived(sessions_dir):
    """list action does not show archived notes."""
    from tools.tagged_session import _write_frontmatter, tagged_session

    _write_frontmatter(sessions_dir / "active.md", {
        "session_id": "active", "title": "Active", "tags": [],
        "created": "2026-05-23", "archived": False
    }, "body")
    _write_frontmatter(sessions_dir / "archive" / "archived.md", {
        "session_id": "archived", "title": "Archived", "tags": [],
        "created": "2026-05-23", "archived": True
    }, "body")

    result = tagged_session(action="list")
    assert "Active" in result
    assert "Archived" not in result


def test_help_text():
    """help action returns usage instructions."""
    from tools.tagged_session import tagged_session
    result = tagged_session(action="help")
    assert "save" in result
    assert "tag" in result
    assert "find" in result


def test_unknown_action():
    """Unknown action returns an error message."""
    from tools.tagged_session import tagged_session
    result = tagged_session(action="fly")
    assert "未知 action" in result


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------
def test_registry_schema_shape(fresh_registry):
    """tagged_session registers with the expected schema."""
    from tools.tagged_session import tagged_session

    fresh_registry.register(
        name="tagged_session",
        description="test",
        parameters={
            "properties": {
                "action": {"type": "string", "enum": ["save", "tag", "find", "archive", "resume", "list", "help"]},
                "session": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["action"]
        },
        handler=tagged_session,
    )
    schema = fresh_registry.get_schema("tagged_session")
    assert schema is not None
    assert schema["name"] == "tagged_session"
    props = schema["input_schema"]["properties"]
    assert "action" in props
    assert "session" in props
    assert "content" in props
