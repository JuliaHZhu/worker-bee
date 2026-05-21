import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path


class SessionDB:
    def __init__(self, db_path="state.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT,
                title TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                session_id TEXT,
                role TEXT,
                content TEXT,
                tool_calls TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY,
                session_id TEXT,
                content TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY,
                session_id TEXT,
                content TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                completed_at TEXT
            );
        """)
        self.conn.commit()

    def create_session(self, title="") -> str:
        sid = str(uuid.uuid4())[:8]
        self.conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?)",
            (sid, datetime.now().isoformat(), title)
        )
        self.conn.commit()
        return sid

    def save_message(self, session_id: str, role: str, content: str, tool_calls=None):
        self.conn.execute(
            "INSERT INTO messages (session_id, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, json.dumps(tool_calls) if tool_calls else None, datetime.now().isoformat())
        )
        self.conn.commit()

    def get_messages(self, session_id: str):
        rows = self.conn.execute(
            "SELECT role, content, tool_calls FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,)
        ).fetchall()
        messages = []
        for role, content, tool_calls in rows:
            msg = {"role": role, "content": content}
            if tool_calls:
                msg["tool_calls"] = json.loads(tool_calls)
            messages.append(msg)
        return messages

    def list_sessions(self):
        return self.conn.execute(
            "SELECT id, created_at, title FROM sessions ORDER BY created_at DESC"
        ).fetchall()

    # ── Todos ──
    def add_todo(self, session_id: str, content: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO todos (session_id, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, content, datetime.now().isoformat(), datetime.now().isoformat())
        )
        self.conn.commit()
        return cur.lastrowid

    def list_todos(self, session_id: str, status: str = None):
        sql = "SELECT id, content, status, created_at FROM todos WHERE session_id = ?"
        params = [session_id]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY created_at"
        return self.conn.execute(sql, params).fetchall()

    def update_todo_status(self, todo_id: int, status: str):
        self.conn.execute(
            "UPDATE todos SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), todo_id)
        )
        self.conn.commit()

    def delete_todo(self, todo_id: int):
        self.conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        self.conn.commit()

    # ── Goals ──
    def set_goal(self, session_id: str, content: str) -> int:
        # Mark previous goals as superseded
        self.conn.execute(
            "UPDATE goals SET status = 'superseded' WHERE session_id = ? AND status = 'active'",
            (session_id,)
        )
        cur = self.conn.execute(
            "INSERT INTO goals (session_id, content, created_at) VALUES (?, ?, ?)",
            (session_id, content, datetime.now().isoformat())
        )
        self.conn.commit()
        return cur.lastrowid

    def get_active_goal(self, session_id: str):
        row = self.conn.execute(
            "SELECT id, content, created_at FROM goals WHERE session_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
            (session_id,)
        ).fetchone()
        return row

    def complete_goal(self, session_id: str):
        self.conn.execute(
            "UPDATE goals SET status = 'completed', completed_at = ? WHERE session_id = ? AND status = 'active'",
            (datetime.now().isoformat(), session_id)
        )
        self.conn.commit()

    def list_goals(self, session_id: str):
        return self.conn.execute(
            "SELECT id, content, status, created_at, completed_at FROM goals WHERE session_id = ? ORDER BY id DESC",
            (session_id,)
        ).fetchall()
