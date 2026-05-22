"""Tests for SessionDB — session creation, messages, todos, goals."""
import pytest
import tempfile
from pathlib import Path

from memory import SessionDB


@pytest.fixture
def db():
    """In-memory SessionDB for isolated tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    sdb = SessionDB(path)
    yield sdb
    try:
        Path(path).unlink()
    except OSError:
        pass


class TestSessions:
    """Session CRUD."""

    def test_create_session(self, db):
        sid = db.create_session()
        assert len(sid) == 8
        assert isinstance(sid, str)

    def test_create_session_with_title(self, db):
        sid = db.create_session(title="My Test")
        sessions = db.list_sessions()
        titles = {s[2] for s in sessions}
        assert "My Test" in titles

    def test_list_sessions_empty(self, db):
        sessions = db.list_sessions()
        assert sessions == []

    def test_list_sessions_order(self, db):
        db.create_session(title="First")
        db.create_session(title="Second")
        sessions = db.list_sessions()
        # Most recent first
        assert sessions[0][2] == "Second"
        assert sessions[1][2] == "First"


class TestMessages:
    """Message save and retrieval."""

    def test_save_and_get_message(self, db):
        sid = db.create_session()
        db.save_message(sid, "user", "hello")
        db.save_message(sid, "assistant", "hi there")

        msgs = db.get_messages(sid)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "hello"
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["content"] == "hi there"

    def test_message_with_tool_calls(self, db):
        sid = db.create_session()
        tool_calls = [{"id": "tc1", "name": "fs_read_file", "arguments": {"path": "test.txt"}}]
        db.save_message(sid, "assistant", "I'll read that", tool_calls=tool_calls)

        msgs = db.get_messages(sid)
        assert msgs[0]["tool_calls"] == tool_calls

    def test_get_messages_empty_session(self, db):
        sid = db.create_session()
        assert db.get_messages(sid) == []

    def test_messages_isolated_per_session(self, db):
        sid1 = db.create_session()
        sid2 = db.create_session()
        db.save_message(sid1, "user", "a")
        db.save_message(sid2, "user", "b")

        assert len(db.get_messages(sid1)) == 1
        assert len(db.get_messages(sid2)) == 1
        assert db.get_messages(sid1)[0]["content"] == "a"
        assert db.get_messages(sid2)[0]["content"] == "b"


class TestTodos:
    """Todo CRUD."""

    def test_add_and_list_todos(self, db):
        sid = db.create_session()
        tid = db.add_todo(sid, "Write tests")
        assert isinstance(tid, int)
        assert tid > 0

        todos = db.list_todos(sid)
        assert len(todos) == 1
        assert todos[0][1] == "Write tests"
        assert todos[0][2] == "pending"

    def test_update_todo_status(self, db):
        sid = db.create_session()
        tid = db.add_todo(sid, "Do thing")
        db.update_todo_status(tid, "done")

        done = db.list_todos(sid, status="done")
        assert len(done) == 1
        assert done[0][0] == tid

        pending = db.list_todos(sid, status="pending")
        assert len(pending) == 0

    def test_delete_todo(self, db):
        sid = db.create_session()
        tid = db.add_todo(sid, "Delete me")
        db.delete_todo(tid)

        assert db.list_todos(sid) == []

    def test_list_todos_filter_by_status(self, db):
        sid = db.create_session()
        db.add_todo(sid, "Task 1")
        tid2 = db.add_todo(sid, "Task 2")
        db.update_todo_status(tid2, "done")

        assert len(db.list_todos(sid, status="pending")) == 1
        assert len(db.list_todos(sid, status="done")) == 1


class TestGoals:
    """Goal management."""

    def test_set_and_get_goal(self, db):
        sid = db.create_session()
        db.set_goal(sid, "Build a test suite")
        goal = db.get_active_goal(sid)
        assert goal is not None
        assert goal[1] == "Build a test suite"

    def test_set_goal_supersedes_previous(self, db):
        sid = db.create_session()
        db.set_goal(sid, "First goal")
        db.set_goal(sid, "Second goal")

        active = db.get_active_goal(sid)
        assert active[1] == "Second goal"

        all_goals = db.list_goals(sid)
        assert len(all_goals) == 2

    def test_complete_goal(self, db):
        sid = db.create_session()
        db.set_goal(sid, "Complete me")
        db.complete_goal(sid)

        active = db.get_active_goal(sid)
        assert active is None

        goals = db.list_goals(sid)
        assert goals[0][2] == "completed"

    def test_no_active_goal(self, db):
        sid = db.create_session()
        assert db.get_active_goal(sid) is None
