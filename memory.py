import sqlite3
import json
import uuid
import threading
from datetime import datetime


class SessionDB:
    def __init__(self, db_path="state.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_schema()

    def _get_conn(self):
        """Return a connection bound to the current thread."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._local.conn

    def _init_schema(self):
        conn = self._get_conn()
        conn.executescript("""
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
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                session_id TEXT,
                content TEXT,
                status TEXT DEFAULT 'todo',
                assigned_to TEXT,
                priority INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                done_at TEXT
            );
        """)
        conn.commit()

    def create_session(self, title="") -> str:
        sid = str(uuid.uuid4())[:8]
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?)",
            (sid, datetime.now().isoformat(), title)
        )
        conn.commit()
        return sid

    def save_message(self, session_id: str, role: str, content: str, tool_calls=None):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO messages (session_id, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, json.dumps(tool_calls) if tool_calls else None, datetime.now().isoformat())
        )
        conn.commit()

    def get_messages(self, session_id: str):
        conn = self._get_conn()
        rows = conn.execute(
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
        conn = self._get_conn()
        return conn.execute(
            "SELECT id, created_at, title FROM sessions ORDER BY created_at DESC"
        ).fetchall()

    # ── Todos ──
    def add_todo(self, session_id: str, content: str) -> int:
        conn = self._get_conn()
        cur = conn.execute(
            "INSERT INTO todos (session_id, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, content, datetime.now().isoformat(), datetime.now().isoformat())
        )
        conn.commit()
        return cur.lastrowid

    def list_todos(self, session_id: str, status: str = None):
        conn = self._get_conn()
        sql = "SELECT id, content, status, created_at FROM todos WHERE session_id = ?"
        params = [session_id]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY created_at"
        return conn.execute(sql, params).fetchall()

    def update_todo_status(self, todo_id: int, status: str):
        conn = self._get_conn()
        conn.execute(
            "UPDATE todos SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), todo_id)
        )
        conn.commit()

    def delete_todo(self, todo_id: int):
        conn = self._get_conn()
        conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        conn.commit()

    # ── Tasks ──
    def add_task(self, session_id: str, content: str, assigned_to: str = None, priority: int = 0) -> int:
        conn = self._get_conn()
        now = datetime.now().isoformat()
        cur = conn.execute(
            "INSERT INTO tasks (session_id, content, assigned_to, priority, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, content, assigned_to, priority, now, now)
        )
        conn.commit()
        return cur.lastrowid

    def list_tasks(self, session_id: str = None, status: str = None, assigned_to: str = None):
        conn = self._get_conn()
        sql = "SELECT id, session_id, content, status, assigned_to, priority, created_at FROM tasks WHERE 1=1"
        params = []
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if assigned_to:
            sql += " AND assigned_to = ?"
            params.append(assigned_to)
        sql += " ORDER BY priority DESC, created_at ASC"
        return conn.execute(sql, params).fetchall()

    def update_task_status(self, task_id: int, status: str):
        conn = self._get_conn()
        now = datetime.now().isoformat()
        if status == "done":
            conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ?, done_at = ? WHERE id = ?",
                (status, now, now, task_id)
            )
        else:
            conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, task_id)
            )
        conn.commit()

    def assign_task(self, task_id: int, assigned_to: str):
        conn = self._get_conn()
        conn.execute(
            "UPDATE tasks SET assigned_to = ?, updated_at = ? WHERE id = ?",
            (assigned_to, datetime.now().isoformat(), task_id)
        )
        conn.commit()

    def get_pending_tasks_for_job(self, assigned_to: str):
        conn = self._get_conn()
        return conn.execute(
            "SELECT id, content, priority FROM tasks WHERE assigned_to = ? AND status IN ('todo', 'in_progress') ORDER BY priority DESC, created_at ASC",
            (assigned_to,)
        ).fetchall()
