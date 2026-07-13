#!/usr/bin/env python3
"""
wb — WorkerBee unified CLI.

Direct command-line access to job-probe and todo-ball-machine,
without routing through the agent loop.

Usage:
    wb job create "title" "description" [--cycles N]
    wb job ls
    wb job status JOB-001
    wb job handoff JOB-001
    wb job audit JOB-001
    wb job tick

    wb todo dashboard
    wb todo today
    wb todo draw morning
    wb todo quick
    wb todo complete morning
    wb todo history [N]
    wb todo stats [N]
    wb todo day [YYYY-MM-DD]
    wb todo box
    wb todo cycle
    wb todo new-cycle [name]
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

# Ensure repo root is importable when running in dev mode
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_LARK_CLI = shutil.which("lark-cli") or str(Path.home() / ".local" / "bin" / "lark-cli")


# ---------------------------------------------------------------------------
# Job sub-command
# ---------------------------------------------------------------------------
def _job_create(args):
    from tools.job_probe import probe_create_job
    out = probe_create_job(
        title=args.title,
        description=args.description or "",
        estimated_cycles=args.cycles,
    )
    logger.info(out)


def _job_ls(args):
    from tools.job_probe import probe_status
    out = probe_status()
    logger.info(out)


def _job_status(args):
    from tools.job_probe import probe_status
    out = probe_status(job_id=args.job_id)
    logger.info(out)


def _job_handoff(args):
    from tools.job_probe import probe_handoff
    out = probe_handoff(job_id=args.job_id)
    logger.info(out)


def _job_audit(args):
    from tools.job_probe import probe_status
    out = probe_status(job_id=args.job_id)
    logger.info(out)


def _job_tick(args):
    from tools.job_probe import probe_tick
    out = probe_tick()
    logger.info(out)


def _job_run(args):
    """Execute a job: read meta, infer skill, run tools, write artifacts."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from tools.job_probe import _read_meta, _ensure_job_dir, _append_event, _atomic_write
    from agent.registry import registry

    job_id = args.job_id
    meta, body = _read_meta(job_id)
    if meta is None:
        logger.info(f"Error: {job_id} not found.")
        sys.exit(1)

    title = meta.get("title", "")
    # description may be in meta or in body; fallback to title
    description = meta.get("description", "")
    if not description and body:
        # Extract only the ## Description section, ignore Events / other sections
        import re as _re
        m = _re.search(r"## Description\s*\n+(.*?)(?=\n## |\Z)", body, _re.DOTALL)
        if m:
            description = m.group(1).strip()
        else:
            # No Description section — grab first non-heading paragraph
            lines = [l.strip() for l in body.splitlines() if l.strip() and not l.strip().startswith("#")]
            description = " ".join(lines[:3]) if lines else title

    # Ensure numeric fields are int
    meta["current_cycle"] = int(meta.get("current_cycle", 0))
    meta["estimated_cycles"] = int(meta.get("estimated_cycles", 1))

    # Simple skill inference from title keywords
    title_lower = title.lower()
    if any(k in title_lower for k in ("调研", "研究", "research", "search", "调查", "查找")):
        skill = "research"
    elif any(k in title_lower for k in ("写", "write", "draft", "生成", "create")):
        skill = "write"
    else:
        skill = "general"

    logger.info(f"[{job_id}] Detected skill: {skill}")
    logger.info(f"[{job_id}] Title: {title}")

    # --- Research skill execution ---
    if skill == "research":
        # Build a clean search query:
        # 1. Start from title, strip meta verbs
        # 2. If result is too short, append description nouns
        meta_verbs = ("调研", "研究", "research", "search", "调查", "查找", "了解", "分析")
        clean_title = title
        for verb in meta_verbs:
            clean_title = clean_title.replace(verb, "")
        clean_title = clean_title.strip()

        query = clean_title if clean_title else title
        # NOTE: We intentionally do NOT append description to the search query.
        # Title already contains the core entity; description is human-readable
        # context that may confuse search engines with meta-verbs.
        logger.info(f"[{job_id}] Searching: {query}")

        results = registry.call("net_web_search", {"query": query, "num_results": 5})
        logger.info(f"[{job_id}] Search returned {len(results)} chars")

        # Extract top URLs
        import re
        urls = re.findall(r"https?://[^\s\n]+", results)
        extracts = []
        for url in urls[:3]:
            logger.info(f"[{job_id}] Extracting: {url}")
            text = registry.call("net_web_extract", {"url": url})
            extracts.append(f"## Source: {url}\n\n{text[:1500]}\n")

        # Build report
        report_lines = [
            f"# 调研报告: {title}",
            "",
            f"生成时间: {__import__('datetime').datetime.now().isoformat()}",
            "",
            "## 搜索结果",
            "",
            results,
            "",
            "## 内容摘要",
            "",
            "\n".join(extracts),
            "",
            "## 结论",
            "",
            "（待 AI 总结）",
            "",
        ]
        report = "\n".join(report_lines)

        # Write artifacts with naming: {skill}-{YYYY-MM-DD}-{type}.md
        from datetime import datetime as _dt
        today = _dt.now().strftime("%Y-%m-%d")

        job_dir = _ensure_job_dir(job_id)
        artifacts_dir = job_dir / "artifacts"

        # Save extracts individually
        for idx, extract in enumerate(extracts, 1):
            # Extract domain from "## Source: url" line for filename
            src_line = extract.split("\n")[0]
            domain = f"source-{idx}"
            m = __import__("re").search(r"Source: https?://([^/]+)", src_line)
            if m:
                domain = m.group(1).replace(".", "_")
            extract_path = artifacts_dir / f"{skill}-{today}-extract-{domain}.md"
            _atomic_write(extract_path, extract)
            logger.info(f"[{job_id}] Extract written: {extract_path.name}")

        # Save main report
        report_path = artifacts_dir / f"{skill}-{today}-report.md"
        tmp = report_path.with_suffix(".tmp")
        tmp.write_text(report, encoding="utf-8")
        tmp.replace(report_path)

        _append_event(job_id, f"JOB_RUN skill={skill} query='{query}' artifacts={len(extracts)+1}")
        logger.info(f"[{job_id}] Report written: {report_path.name}")

    else:
        logger.info(f"[{job_id}] Skill '{skill}' execution not yet implemented.")
        sys.exit(1)

    # Update meta
    meta["current_cycle"] = meta.get("current_cycle", 0) + 1
    from tools.job_probe import _write_meta
    _write_meta(job_id, meta, body)
    logger.info(f"[{job_id}] Cycle {meta['current_cycle']}/{meta.get('estimated_cycles', 1)} complete.")


def _add_job_parser(sub):
    job = sub.add_parser("job", help="Job probe commands")
    job_sub = job.add_subparsers(dest="job_cmd", required=True)

    p = job_sub.add_parser("create", help="Create a new job")
    p.add_argument("title")
    p.add_argument("description", nargs="?", default="")
    p.add_argument("--cycles", type=int, default=1, help="Estimated cycles (default 1)")
    p.set_defaults(func=_job_create)

    p = job_sub.add_parser("ls", help="List all jobs")
    p.set_defaults(func=_job_ls)

    p = job_sub.add_parser("status", help="Show job details")
    p.add_argument("job_id")
    p.set_defaults(func=_job_status)

    p = job_sub.add_parser("handoff", help="Generate handoff package for a job")
    p.add_argument("job_id")
    p.set_defaults(func=_job_handoff)

    p = job_sub.add_parser("audit", help="Audit / review a job")
    p.add_argument("job_id")
    p.set_defaults(func=_job_audit)

    p = job_sub.add_parser("tick", help="Manually trigger probe tick")
    p.set_defaults(func=_job_tick)

    p = job_sub.add_parser("run", help="Execute a job (auto-detect skill and run)")
    p.add_argument("job_id")
    p.set_defaults(func=_job_run)


# ---------------------------------------------------------------------------
# Todo sub-command
# ---------------------------------------------------------------------------
def _todo_dashboard(args):
    from tools.todo_ball_machine import todo_ball_machine
    logger.info(todo_ball_machine(action="dashboard"))


def _todo_today(args):
    from tools.todo_ball_machine import todo_ball_machine
    logger.info(todo_ball_machine(action="today"))


def _todo_draw(args):
    from tools.todo_ball_machine import todo_ball_machine
    logger.info(todo_ball_machine(action="draw", session=args.session))


def _todo_quick(args):
    from tools.todo_ball_machine import todo_ball_machine
    logger.info(todo_ball_machine(action="quick_draw"))


def _todo_complete(args):
    from tools.todo_ball_machine import todo_ball_machine
    logger.info(todo_ball_machine(action="complete", session=args.session))


def _todo_history(args):
    from tools.todo_ball_machine import todo_ball_machine
    n = str(args.days) if args.days else None
    logger.info(todo_ball_machine(action="history", content=n))


def _todo_stats(args):
    from tools.todo_ball_machine import todo_ball_machine
    n = str(args.days) if args.days else None
    logger.info(todo_ball_machine(action="stats", content=n))


def _todo_day(args):
    from tools.todo_ball_machine import todo_ball_machine
    d = args.date or None
    logger.info(todo_ball_machine(action="day", content=d))


def _todo_box(args):
    from tools.todo_ball_machine import todo_ball_machine
    logger.info(todo_ball_machine(action="box_list"))


def _todo_cycle(args):
    from tools.todo_ball_machine import todo_ball_machine
    logger.info(todo_ball_machine(action="cycle_status"))


def _todo_new_cycle(args):
    from tools.todo_ball_machine import todo_ball_machine
    logger.info(todo_ball_machine(action="new_cycle", content=args.name))


def _add_todo_parser(sub):
    todo = sub.add_parser("todo", help="Todo Ball Machine commands")
    todo_sub = todo.add_subparsers(dest="todo_cmd", required=True)

    p = todo_sub.add_parser("dashboard", aliases=["d"], help="System dashboard")
    p.set_defaults(func=_todo_dashboard)

    p = todo_sub.add_parser("today", aliases=["t"], help="Today's sessions")
    p.set_defaults(func=_todo_today)

    p = todo_sub.add_parser("draw", help="Draw a session (morning/afternoon/evening/overtime)")
    p.add_argument("session")
    p.set_defaults(func=_todo_draw)

    p = todo_sub.add_parser("quick", aliases=["q"], help="Quick draw three sessions")
    p.set_defaults(func=_todo_quick)

    p = todo_sub.add_parser("complete", aliases=["done"], help="Mark session complete")
    p.add_argument("session")
    p.set_defaults(func=_todo_complete)

    p = todo_sub.add_parser("history", aliases=["h"], help="History (default 7 days)")
    p.add_argument("days", nargs="?", type=int, default=7)
    p.set_defaults(func=_todo_history)

    p = todo_sub.add_parser("stats", aliases=["s"], help="Stats report (default 7 days)")
    p.add_argument("days", nargs="?", type=int, default=7)
    p.set_defaults(func=_todo_stats)

    p = todo_sub.add_parser("day", help="Detail for a specific date (YYYY-MM-DD)")
    p.add_argument("date", nargs="?", default=None)
    p.set_defaults(func=_todo_day)

    p = todo_sub.add_parser("box", aliases=["b"], help="Box quota list")
    p.set_defaults(func=_todo_box)

    p = todo_sub.add_parser("cycle", aliases=["c"], help="Cycle status")
    p.set_defaults(func=_todo_cycle)

    p = todo_sub.add_parser("new-cycle", help="Start a new cycle")
    p.add_argument("name", nargs="?", default=None)
    p.set_defaults(func=_todo_new_cycle)


# ---------------------------------------------------------------------------
# Swarm sub-command
# ---------------------------------------------------------------------------
def _listener_pid_file() -> Path:
    from pathlib import Path
    return Path.home() / ".worker-bee" / "listener.pid"


def _listener_is_running() -> tuple[bool, int | None]:
    """检查 listener 是否已在运行。返回 (running, pid_or_none)。"""
    import os
    pid_file = _listener_pid_file()
    if not pid_file.exists():
        return False, None
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        return True, pid
    except (ValueError, OSError, ProcessLookupError):
        # PID 文件残留但进程已死 → 清理
        try:
            pid_file.unlink(missing_ok=True)
        except Exception:
            pass
        return False, None


def _swarm_listen(args):
    """Start the NATS swarm listener (foreground process)."""
    import subprocess
    import os
    from pathlib import Path

    running, pid = _listener_is_running()
    if running:
        logger.info(f"⚠️  Listener already running (PID {pid}). Stop it first: wb swarm menu → 3")
        sys.exit(1)

    listener_path = Path(__file__).parent.parent / "swarm" / "listener.py"
    if not listener_path.exists():
        logger.info(f"Error: listener not found at {listener_path}")
        sys.exit(1)

    nats_url = args.url or os.environ.get("SWARM_NATS_URL", "nats://localhost:4222")
    logger.info(f"[wb swarm listen] Starting listener → {nats_url}")
    logger.info("[wb swarm listen] Writing messages to ~/.worker-bee/mailbox/inbox/")
    logger.info("[wb swarm listen] Press Ctrl+C to stop")
    sys.stdout.flush()

    try:
        subprocess.run(
            [sys.executable, str(listener_path), nats_url],
            check=True,
        )
    except KeyboardInterrupt:
        logger.info("\n[wb swarm listen] Stopped.")


def _swarm_status(args):
    """Check NATS connection and listener health."""
    import asyncio
    import os
    import nats
    from pathlib import Path

    nats_url = os.environ.get("SWARM_NATS_URL", "nats://localhost:4222")

    # Check NATS connection
    try:
        async def _check():
            nc = await nats.connect(nats_url, connect_timeout=3)
            url = nc.connected_url.netloc
            await nc.drain()
            return url
        connected = asyncio.run(_check())
        logger.info(f"✅ NATS: connected to {connected}")
    except Exception as e:
        logger.info(f"❌ NATS: {e}")

    # Check mailbox
    inbox = Path.home() / ".worker-bee" / "mailbox" / "inbox"
    if inbox.exists():
        unread = len(list(inbox.glob("*.json")))
        logger.info(f"📬 Mailbox: {unread} unread, inbox={inbox}")
    else:
        logger.info("📭 Mailbox: not initialized (no messages yet)")

    # Check if listener process is running
    running, pid = _listener_is_running()
    if running:
        logger.info(f"🟢 Listener: running (PID {pid})")
    else:
        logger.info("🔴 Listener: not running (start with: wb swarm listen)")


def _add_swarm_parser(sub):
    swarm = sub.add_parser("swarm", help="NATS swarm communication")
    swarm_sub = swarm.add_subparsers(dest="swarm_cmd", required=True)

    p = swarm_sub.add_parser("listen", help="Start NATS listener (writes messages to mailbox)")
    p.add_argument("url", nargs="?", default=None, help="NATS URL (default: nats://localhost:4222)")
    p.set_defaults(func=_swarm_listen)

    p = swarm_sub.add_parser("status", help="Check NATS connection and listener health")
    p.set_defaults(func=_swarm_status)

    p = swarm_sub.add_parser("menu", help="Interactive swarm control menu (TUI)")
    p.set_defaults(func=_swarm_menu)


def _swarm_menu(args):
    """Interactive menu for swarm operations."""
    import json
    import subprocess
    import os
    from pathlib import Path
    from tools.swarm import swarm_publish

    nats_url = os.environ.get("SWARM_NATS_URL", "nats://localhost:4222")
    bee_id = "unknown"
    role = "seed"
    try:
        cfg = json.loads((Path.home() / ".worker-bee" / "config.json").read_text())
        bee_id = cfg.get("bee_id", "unknown")
        role = cfg.get("role", "seed")
    except Exception:
        pass

    def _print_header():
        logger.info("\n" + "=" * 50)
        logger.info(f"  🐝 Swarm Control Menu  |  {bee_id} ({role})")
        logger.info(f"  NATS: {nats_url}")
        logger.info("=" * 50)

    def _menu_items():
        # Listener status
        pg = subprocess.run(["pgrep", "-f", "swarm/listener.py"], capture_output=True, text=True)
        listener_pid = pg.stdout.strip().split()[0] if pg.stdout.strip() else None
        listener_status = f"🟢 PID {listener_pid}" if listener_pid else "🔴 stopped"

        # Mailbox count
        inbox = Path.home() / ".worker-bee" / "mailbox" / "inbox"
        unread = len(list(inbox.glob("*.json"))) if inbox.exists() else 0

        return [
            ("1", f"Status overview       ({listener_status}, 📬 {unread} unread)"),
            ("2", "Start listener        (spawn background NATS subscriber)"),
            ("3", "Stop listener         (kill swarm/listener.py process)"),
            ("4", "Send test message     (fire-and-forget to swarm.test.hello)"),
            ("5", "Read mailbox          (show latest inbox messages)"),
            ("6", "Set role              (write role to config.json)"),
            ("0", "Exit"),
        ]

    def _start_listener():
        running, pid = _listener_is_running()
        if running:
            logger.info(f"⚠️  Listener already running (PID {pid}). Stop it first (menu option 3).")
            return
        listener_path = Path(__file__).parent.parent / "swarm" / "listener.py"
        if not listener_path.exists():
            logger.info("❌ listener.py not found")
            return
        subprocess.Popen(
            [sys.executable, str(listener_path), nats_url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info("🟢 Listener spawned (background). Check status in a few seconds.")

    def _stop_listener():
        running, pid = _listener_is_running()
        if running and pid is not None:
            subprocess.run(["kill", str(pid)])
            logger.info(f"🔴 Listener stopped (PID {pid})")
            return
        # Fallback: 模糊匹配（兼容旧进程没有 PID 文件的情况）
        pg = subprocess.run(["pgrep", "-f", "swarm/listener.py"], capture_output=True, text=True)
        if not pg.stdout.strip():
            logger.info("🔴 Listener not running")
            return
        for p in pg.stdout.strip().split():
            subprocess.run(["kill", p])
        logger.info("🔴 Listener stopped")

    def _send_test():
        try:
            result = swarm_publish("swarm.test.hello", {"from": bee_id, "msg": "ping"})
            data = json.loads(result)
            logger.info("✅" if data.get("ok") else "❌", result)
        except Exception as e:
            logger.info(f"❌ {e}")

    def _read_mailbox():
        inbox = Path.home() / ".worker-bee" / "mailbox" / "inbox"
        if not inbox.exists():
            logger.info("📭 Mailbox empty")
            return
        files = sorted(inbox.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
        logger.info(f"\n📬 Latest {len(files)} messages:")
        for f in files:
            try:
                msg = json.loads(f.read_text())
                ts = msg.get("timestamp", "?")[:19]
                subj = msg.get("subject", "?")
                sender = msg.get("sender", "?")
                logger.info(f"  [{ts}] {subj:30s} from {sender}")
            except Exception:
                logger.info(f"  (unreadable) {f.name}")

    def _set_role():
        logger.info("\nRoles: strategy | pm | centurion | worker | world | aristotle | skeleton | cardmaster | seed")
        new_role = input("Enter role: ").strip().lower()
        if not new_role:
            return
        cfg_path = Path.home() / ".worker-bee" / "config.json"
        try:
            cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        except Exception:
            cfg = {}
        cfg["role"] = new_role
        # Atomic write to avoid corruption if process crashes mid-write
        tmp_path = cfg_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(cfg_path)
        nonlocal role
        role = new_role
        logger.info(f"✅ Role set to '{new_role}' in {cfg_path}")

    while True:
        _print_header()
        for key, desc in _menu_items():
            logger.info(f"  [{key}] {desc}")
        choice = input("\nSelect: ").strip()

        if choice == "0":
            logger.info("Bye.")
            break
        elif choice == "1":
            _swarm_status(args)
        elif choice == "2":
            _start_listener()
        elif choice == "3":
            _stop_listener()
        elif choice == "4":
            _send_test()
        elif choice == "5":
            _read_mailbox()
        elif choice == "6":
            _set_role()
        else:
            logger.info("Invalid choice")
        input("\nPress Enter to continue...")


# ---------------------------------------------------------------------------
# Workspace sub-command
# ---------------------------------------------------------------------------
def _workspace_show(args):
    from agent.workspace import get_workspace
    logger.info(get_workspace())


def _add_workspace_parser(sub):
    ws = sub.add_parser("workspace", help="Show the current workspace path")
    ws.set_defaults(func=_workspace_show)


# ---------------------------------------------------------------------------
# Lark / Feishu sub-command
# ---------------------------------------------------------------------------
def _lark_who(args):
    """Resolve a contact name to open_id."""
    import subprocess, json
    result = subprocess.run(
        [_LARK_CLI, "contact", "+search-user", "--query", args.name],
        capture_output=True, text=True, timeout=10,
    )
    try:
        data = json.loads(result.stdout)
        users = data.get("items", data.get("data", {}).get("items", []))
    except json.JSONDecodeError:
        logger.info(result.stdout[:500])
        return
    if not users:
        logger.info(f"No results for '{args.name}'")
        return
    for u in users[:5]:
        name = u.get("name", "?")
        uid = u.get("open_id", u.get("user_id", "?"))
        email = u.get("email", "")
        dept = ", ".join(u.get("department_names", []))
        logger.info(f"{name:20s}  {uid}  {email}  {dept}")


def _lark_chats(args):
    """List or search group chats."""
    import subprocess, json
    cmd = [_LARK_CLI, "im", "+chat-list"]
    if args.query:
        cmd = [_LARK_CLI, "im", "+chat-search", "--query", args.query]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    try:
        data = json.loads(result.stdout)
        chats = data.get("items", data.get("data", {}).get("items", []))
    except json.JSONDecodeError:
        logger.info(result.stdout[:500])
        return
    if not chats:
        logger.info(f"No chats found" + (f" for '{args.query}'" if args.query else ""))
        return
    for c in chats[:20]:
        name = c.get("name", "?")
        cid = c.get("chat_id", "?")
        members = c.get("member_count", "?")
        logger.info(f"{name:30s}  {cid}  ({members} members)")


def _lark_send(args):
    """Send a message — resolves name to ID automatically."""
    import json, subprocess

    # Check write permission (same gate as tools/lark.py)
    config_path = Path.home() / ".worker-bee" / "config.json"
    try:
        cfg = json.loads(config_path.read_text())
        if not cfg.get("lark_allow_write", False):
            logger.info("Write operations are disabled. Enable with: wb setup → lark_allow_write: true")
            return
    except (FileNotFoundError, json.JSONDecodeError):
        logger.info("Write operations are disabled (no config or invalid). Run: wb setup")
        return

    if args.group:
        # Resolve group name
        r = subprocess.run(
            [_LARK_CLI, "im", "+chat-search", "--query", args.group],
            capture_output=True, text=True, timeout=10,
        )
        try:
            data = json.loads(r.stdout)
            chats = data.get("items", data.get("data", {}).get("items", []))
        except json.JSONDecodeError:
            logger.info(f"Error searching groups: {r.stdout[:200]}")
            return
        exact = [c for c in chats if c.get("name", "").lower() == args.group.lower()]
        if exact:
            chat = exact[0]
        elif chats:
            logger.info(f"Group '{args.group}' not found exactly. Did you mean:")
            for c in chats[:5]:
                logger.info(f"  - {c.get('name', '?')}")
            return
        else:
            logger.info(f"Group not found: {args.group}")
            return
        cid = chat["chat_id"]
        name = chat.get("name", args.group)
        text = " ".join(args.msg) if isinstance(args.msg, list) else (args.msg or "")
        if not text.strip():
            logger.info("Message is empty. Usage: wb lark send --group <name> <message text>")
            return
        cmd = [_LARK_CLI, "im", "+messages-send", "--chat-id", cid, "--text", text]
    elif args.to:
        # Resolve user name
        r = subprocess.run(
            [_LARK_CLI, "contact", "+search-user", "--query", args.to],
            capture_output=True, text=True, timeout=10,
        )
        try:
            data = json.loads(r.stdout)
            users = data.get("items", data.get("data", {}).get("items", []))
        except json.JSONDecodeError:
            logger.info(f"Error searching users: {r.stdout[:200]}")
            return
        exact = [u for u in users if u.get("name", "").lower() == args.to.lower()]
        if exact:
            user = exact[0]
        elif users:
            logger.info(f"User '{args.to}' not found exactly. Did you mean:")
            for u in users[:5]:
                logger.info(f"  - {u.get('name', '?')}")
            return
        else:
            logger.info(f"User not found: {args.to}")
            return
        uid = user.get("open_id", user.get("user_id"))
        uname = user.get("name", args.to)
        text = " ".join(args.msg) if isinstance(args.msg, list) else (args.msg or "")
        if not text.strip():
            logger.info("Message is empty. Usage: wb lark send --to <name> <message text>")
            return
        cmd = [_LARK_CLI, "im", "+messages-send", "--user-id", uid, "--text", text]
        name = uname
    else:
        logger.info("Specify --to <name> or --group <name>")
        return

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    try:
        data = json.loads(result.stdout)
        if data.get("ok"):
            msg_id = data.get("data", {}).get("message_id", "?")
            logger.info(f"✅ Sent to {name} (msg_id: {msg_id})")
        else:
            err = data.get("error", {}).get("message", result.stdout[:200])
            logger.info(f"❌ {err}")
    except json.JSONDecodeError:
        logger.info(result.stdout[:500])


def _lark_inbox(args):
    """Pull recent messages from a user or group — resolves name to ID."""
    import subprocess, json

    if args.group:
        r = subprocess.run(
            [_LARK_CLI, "im", "+chat-search", "--query", args.group],
            capture_output=True, text=True, timeout=10,
        )
        try:
            data = json.loads(r.stdout)
            chats = data.get("items", data.get("data", {}).get("items", []))
        except json.JSONDecodeError:
            logger.info(f"Error: {r.stdout[:200]}")
            return
        exact = [c for c in chats if c.get("name", "").lower() == args.group.lower()]
        if exact:
            chat = exact[0]
        elif chats:
            logger.info(f"Group '{args.group}' not found exactly. Did you mean:")
            for c in chats[:5]:
                logger.info(f"  - {c.get('name', '?')}")
            return
        else:
            logger.info(f"Group not found: {args.group}")
            return
        cid = chat["chat_id"]
        label = chat.get("name", args.group)
        cmd = [_LARK_CLI, "im", "+chat-messages-list", "--chat-id", cid, "--limit", str(args.limit)]
    elif args.from_user:
        r = subprocess.run(
            [_LARK_CLI, "contact", "+search-user", "--query", args.from_user],
            capture_output=True, text=True, timeout=10,
        )
        try:
            data = json.loads(r.stdout)
            users = data.get("items", data.get("data", {}).get("items", []))
        except json.JSONDecodeError:
            logger.info(f"Error: {r.stdout[:200]}")
            return
        exact = [u for u in users if u.get("name", "").lower() == args.from_user.lower()]
        if exact:
            user = exact[0]
        elif users:
            logger.info(f"User '{args.from_user}' not found exactly. Did you mean:")
            for u in users[:5]:
                logger.info(f"  - {u.get('name', '?')}")
            return
        else:
            logger.info(f"User not found: {args.from_user}")
            return
        uid = user.get("open_id", user.get("user_id"))
        label = user.get("name", args.from_user)
        cmd = [_LARK_CLI, "im", "+chat-messages-list", "--user-id", uid, "--limit", str(args.limit)]
    else:
        logger.info("Specify --from <name> or --group <name>")
        return

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    try:
        data = json.loads(result.stdout)
        msgs = data.get("items", data.get("data", {}).get("items", []))
    except json.JSONDecodeError:
        logger.info(result.stdout[:500])
        return

    logger.info(f"📬 {label} — last {len(msgs)} messages:\n")
    for m in reversed(msgs):
        sender = m.get("sender", {}).get("name", m.get("sender_name", "?"))
        body = m.get("body", {}).get("content", "")
        # Try to get plain text from various message formats
        if not body:
            body = m.get("content", "")
        # Truncate long messages
        if len(body) > 200:
            body = body[:200] + "…"
        ts = m.get("create_time", "")
        logger.info(f"[{ts}] {sender}: {body}")


def _lark_notify(args):
    """Send a Feishu notification — direct via lark-cli, or delegate via NATS to PM."""
    import json
    import subprocess
    import asyncio
    from datetime import datetime, timezone

    text = " ".join(args.text) if isinstance(args.text, list) else (args.text or "")
    if not text.strip():
        logger.info("Message is empty. Usage: wb lark notify --to <open_id> --text <message>")
        return

    # Try local lark-cli first
    lark_cli = shutil.which("lark-cli")
    if lark_cli:
        if args.to:
            cmd = [lark_cli, "im", "+messages-send", "--user-id", args.to, "--text", text]
        elif args.group:
            cmd = [lark_cli, "im", "+messages-send", "--chat-id", args.group, "--text", text]
        else:
            logger.info("Specify --to <open_id> or --group <chat_id>")
            return

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        try:
            data = json.loads(result.stdout)
            if data.get("ok") or data.get("code") == 0:
                logger.info("✅ Sent via lark-cli")
                return
            else:
                err = data.get("msg", data.get("error", {}).get("message", result.stdout[:200]))
                logger.info(f"❌ lark-cli failed: {err}")
                if args.no_fallback:
                    return
        except json.JSONDecodeError:
            logger.info(f"❌ lark-cli output: {result.stdout[:200]}")
            if args.no_fallback:
                return
        logger.info("Falling back to NATS delegation...")
    else:
        if args.no_fallback:
            logger.info("lark-cli not found and fallback disabled.")
            return
        logger.info("lark-cli not found, delegating via NATS...")

    # NATS delegation
    try:
        import nats
    except ModuleNotFoundError:
        logger.info("nats-py not installed. Cannot delegate via NATS.")
        return

    nats_url = os.environ.get("SWARM_NATS_URL", "nats://localhost:4222")
    bee_id = "unknown-bee"
    try:
        cfg = json.loads((Path.home() / ".worker-bee" / "config.json").read_text())
        bee_id = cfg.get("bee_id", "unknown-bee")
    except Exception:
        pass

    payload = {
        "target_type": "user" if args.to else ("group" if args.group else "user"),
        "target_id": args.to or args.group or "",
        "text": text,
        "sender": bee_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    async def _publish():
        nc = await nats.connect(nats_url, connect_timeout=5)
        await nc.publish("swarm.notify.feishu", json.dumps(payload).encode())
        await nc.drain()
        logger.info("📨 Delegated to PM via NATS (swarm.notify.feishu)")

    asyncio.run(_publish())


def _add_lark_parser(sub):
    lark = sub.add_parser("lark", help="Feishu/Lark operations — resolve names to IDs")
    lark_sub = lark.add_subparsers(dest="lark_cmd", required=True)

    p = lark_sub.add_parser("who", help="Find a user by name → open_id")
    p.add_argument("name", help="Name or partial name")
    p.set_defaults(func=_lark_who)

    p = lark_sub.add_parser("chats", help="List/search group chats")
    p.add_argument("query", nargs="?", default="", help="Optional search keyword")
    p.set_defaults(func=_lark_chats)

    p = lark_sub.add_parser("send", help="Send a message (resolves name → ID)")
    p.add_argument("--to", default="", help="User name to DM")
    p.add_argument("--group", default="", help="Group name")
    p.add_argument("msg", nargs="*", default=[], help="Message text")
    p.set_defaults(func=_lark_send)

    p = lark_sub.add_parser("inbox", help="Pull recent messages from a user or group")
    p.add_argument("--from", dest="from_user", default="", help="User name")
    p.add_argument("--group", default="", help="Group name")
    p.add_argument("--limit", type=int, default=20, help="Max messages (default: 20)")
    p.set_defaults(func=_lark_inbox)

    p = lark_sub.add_parser("notify", help="Send notification — local lark-cli or NATS delegate to PM")
    p.add_argument("--to", default="", help="Target user open_id")
    p.add_argument("--group", default="", help="Target group chat_id")
    p.add_argument("--text", nargs="+", required=True, help="Message text")
    p.add_argument("--no-fallback", action="store_true", help="Disable NATS delegation when local lark-cli fails")
    p.set_defaults(func=_lark_notify)

    p = lark_sub.add_parser("serve", help="Start Feishu Lark webhook bot server")
    p.add_argument("--port", type=int, default=8080, help="Webhook server port (default: 8080)")
    p.set_defaults(func=_lark_serve)


def _lark_serve(args):
    """Start the Feishu Lark webhook server."""
    from agent.lark_cli import run_server
    run_server(port=args.port)


# ---------------------------------------------------------------------------
# Deck sub-command
# ---------------------------------------------------------------------------
def _deck_mode(args):
    from agent.main import load_config
    from agent.deck import DeckManager
    from agent.registry import registry
    cfg = load_config() or {}
    dm = DeckManager(cfg.get("tools", []), registry)
    logger.info(f"Mode: {dm.mode}")
    tools = dm.list_tools()
    logger.info(f"Tools ({len(tools)}): {', '.join(tools) if tools else '(none)'}")


def _deck_full(args):
    from agent.main import load_config
    from agent.deck import DeckManager
    from agent.registry import registry
    cfg = load_config() or {}
    dm = DeckManager(cfg.get("tools", []), registry)
    logger.info(dm.set_mode("full"))


def _deck_focus(args):
    from agent.main import load_config
    from agent.deck import DeckManager
    from agent.registry import registry
    cfg = load_config() or {}
    dm = DeckManager(cfg.get("tools", []), registry)
    logger.info(dm.set_mode("focus"))


def _deck_add(args):
    from agent.main import load_config
    from agent.deck import DeckManager
    from agent.registry import registry
    cfg = load_config() or {}
    dm = DeckManager(cfg.get("tools", []), registry)
    logger.info(dm.add_tool(args.tool))


def _deck_drop(args):
    from agent.main import load_config
    from agent.deck import DeckManager
    from agent.registry import registry
    cfg = load_config() or {}
    dm = DeckManager(cfg.get("tools", []), registry)
    logger.info(dm.drop_tool(args.tool))


def _deck_reset(args):
    from agent.main import load_config
    from agent.deck import DeckManager
    from agent.registry import registry
    cfg = load_config() or {}
    dm = DeckManager(cfg.get("tools", []), registry)
    logger.info(dm.reset())


def _deck_list(args):
    from agent.main import load_config
    from agent.deck import DeckManager
    from agent.registry import registry
    cfg = load_config() or {}
    dm = DeckManager(cfg.get("tools", []), registry)
    tools = dm.list_tools()
    logger.info(f"Tools ({len(tools)}): {', '.join(tools) if tools else '(none)'}")


def _deck_log(args):
    import json
    from agent.main import load_config
    from agent.deck import DeckManager
    from agent.registry import registry
    cfg = load_config() or {}
    dm = DeckManager(cfg.get("tools", []), registry)
    logger.info(json.dumps(dm.get_log(), ensure_ascii=False, indent=2))


def _gateway_start(args):
    import logging
    import signal
    import sys
    import time
    from gateway.config import GatewayConfig
    from gateway.run import GatewayRunner
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = GatewayConfig.load()
    if not cfg.enabled:
        logger.info("Gateway is disabled. Add 'gateway.enabled: true' to config.yaml (or ~/.worker-bee/config.json)")
        return
    runner = GatewayRunner(cfg)
    _shutdown_requested = False

    def _on_signal(signum, frame):
        nonlocal _shutdown_requested
        _shutdown_requested = True
        logger.info(f"\nReceived signal {signum}, shutting down...")

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    try:
        runner.start()
        logger.info(f"Gateway started with platforms: {list(runner.adapters.keys())}")
        logger.info("Press Ctrl+C or send SIGTERM to stop")
        while not _shutdown_requested:
            time.sleep(0.5)
    except Exception as exc:
        logger.info(f"Gateway error: {exc}")
    finally:
        runner.stop()
        logger.info("Gateway stopped.")


def _add_gateway_parser(sub):
    gw = sub.add_parser("gateway", help="Gateway — external messaging platform bridge")
    gw_sub = gw.add_subparsers(dest="gateway_cmd", required=True)
    p = gw_sub.add_parser("start", help="Start the gateway server")
    p.set_defaults(func=_gateway_start)


def _add_deck_parser(sub):
    deck = sub.add_parser("deck", help="Deck management — tool boundary control")
    deck_sub = deck.add_subparsers(dest="deck_cmd", required=True)

    p = deck_sub.add_parser("mode", help="Show current deck mode and tools")
    p.set_defaults(func=_deck_mode)

    p = deck_sub.add_parser("full", help="Switch to full-tool mode")
    p.set_defaults(func=_deck_full)

    p = deck_sub.add_parser("focus", help="Switch to focus mode")
    p.set_defaults(func=_deck_focus)

    p = deck_sub.add_parser("add", help="Add a tool to current deck")
    p.add_argument("tool")
    p.set_defaults(func=_deck_add)

    p = deck_sub.add_parser("drop", help="Remove a tool from current deck")
    p.add_argument("tool")
    p.set_defaults(func=_deck_drop)

    p = deck_sub.add_parser("reset", help="Reset deck and re-match skills")
    p.set_defaults(func=_deck_reset)

    p = deck_sub.add_parser("list", help="List tools in current deck")
    p.set_defaults(func=_deck_list)

    p = deck_sub.add_parser("log", help="Show deck usage statistics")
    p.set_defaults(func=_deck_log)


# ---------------------------------------------------------------------------
# Cron sub-command — daily auto-update
# ---------------------------------------------------------------------------

_CRON_MARKER = "# worker-bee-auto-update"
_CRON_ENTRY = (
    "0 3 * * * "
    "{python} -m pip install --upgrade --quiet "
    "git+https://github.com/JuliaHZhu/worker-bee.git "
    "2>&1 | logger -t worker-bee-update"
)


def _cron_install(args):
    """Add a daily auto-update cron job for worker-bee."""
    import subprocess, sys

    # Check if already installed
    result = subprocess.run(
        ["crontab", "-l"], capture_output=True, text=True,
    )
    if result.returncode != 0:
        existing = ""
    else:
        existing = result.stdout.rstrip("\n")
    if _CRON_MARKER in existing:
        logger.info("✅ Cron job already installed.")
        return

    # Build the entry
    python = sys.executable
    entry = _CRON_ENTRY.format(python=python)

    # Append
    new_crontab = (existing + "\n" if existing else "") + _CRON_MARKER + "\n" + entry + "\n"
    subprocess.run(
        ["crontab", "-"],
        input=new_crontab, text=True, check=True,
    )
    logger.info("✅ Installed daily auto-update (runs at 03:00 UTC daily).")
    logger.info(f"   Command: pip install --upgrade worker-bee")


def _cron_uninstall(args):
    """Remove the worker-bee auto-update cron job."""
    import subprocess

    result = subprocess.run(
        ["crontab", "-l"], capture_output=True, text=True,
    )
    if result.returncode != 0 or _CRON_MARKER not in result.stdout:
        logger.info("ℹ️  No worker-bee cron job found.")
        return

    lines = result.stdout.split("\n")
    new_lines = []
    skip_next = False
    for line in lines:
        if _CRON_MARKER in line:
            skip_next = True
            continue
        if skip_next:
            skip_next = False
            continue
        new_lines.append(line)

    new_crontab = "\n".join(new_lines).strip() + "\n"
    if new_crontab.strip():
        subprocess.run(
            ["crontab", "-"],
            input=new_crontab, text=True, check=True,
        )
    else:
        subprocess.run(["crontab", "-r"], check=True)
    logger.info("🗑️  Removed worker-bee auto-update cron job.")


def _cron_status(args):
    """Check whether the auto-update cron job is installed."""
    import subprocess

    result = subprocess.run(
        ["crontab", "-l"], capture_output=True, text=True,
    )
    if result.returncode != 0:
        logger.info("🔴 No crontab configured.")
    elif _CRON_MARKER in result.stdout:
        logger.info("🟢 Auto-update cron job is installed (daily at 03:00 UTC).")
    else:
        logger.info("🔴 Worker-bee auto-update cron job is NOT installed.")


def _add_cron_parser(sub):
    cron = sub.add_parser("cron", help="Manage daily auto-update cron job")
    cron_sub = cron.add_subparsers(dest="cron_cmd", required=True)

    p = cron_sub.add_parser("install", help="Install daily auto-update cron job")
    p.set_defaults(func=_cron_install)

    p = cron_sub.add_parser("uninstall", help="Remove the auto-update cron job")
    p.set_defaults(func=_cron_uninstall)

    p = cron_sub.add_parser("status", help="Check if auto-update is installed")
    p.set_defaults(func=_cron_status)


# ---------------------------------------------------------------------------
# Skill sub-command (lint + test)
# ---------------------------------------------------------------------------

def _skill_lint(args):
    import json
    from agent.main import load_config
    from agent.registry import registry
    from agent.skill_lint import SkillLint
    cfg = load_config() or {}
    skills_dir = cfg.get("skills_dir", os.path.join(os.path.dirname(__file__), "..", "skills"))
    linter = SkillLint(registry, skills_dir)

    if args.skill:
        report = linter.lint_skill(args.skill)
        reports = [report]
    else:
        reports = linter.lint_all()

    if args.json:
        logger.info(json.dumps([r.to_dict() for r in reports], ensure_ascii=False, indent=2))
        return

    for report in reports:
        status = "✅" if report.ok else "❌"
        logger.info(f"\n{status} {report.skill_name}  score={report.score:.2f}")
        for f in report.findings:
            icon = {"ERROR": "🔴", "WARN": "🟡", "INFO": "🔵"}[f.level.name]
            line_info = f":{f.line}" if f.line else ""
            logger.info(f"   {icon} [{f.code}] {f.message}{line_info}")


def _skill_test(args):
    import json
    from agent.main import load_config
    from agent.registry import registry
    from agent.skill_test import SkillTestRunner, SkillTestLevel
    cfg = load_config() or {}
    skills_dir = cfg.get("skills_dir", os.path.join(os.path.dirname(__file__), "..", "skills"))
    runner = SkillTestRunner(registry, skills_dir)

    level_map = {
        "unit": SkillTestLevel.UNIT,
        "integration": SkillTestLevel.INTEGRATION,
        "regression": SkillTestLevel.REGRESSION,
        "stress": SkillTestLevel.STRESS,
    }
    levels = {level_map[l] for l in args.levels.split(",") if l in level_map}
    if not levels:
        levels = {SkillTestLevel.UNIT, SkillTestLevel.INTEGRATION}

    if args.skill:
        report = runner.run_skill(args.skill, levels=levels)
        reports = [report]
    else:
        reports = runner.run_all(levels=levels)

    if args.json:
        logger.info(json.dumps([r.to_dict() for r in reports], ensure_ascii=False, indent=2))
        return

    total_passed = 0
    total_failed = 0
    for report in reports:
        status = "✅" if report.passed else "❌"
        s = report.summary
        total_passed += s["passed"]
        total_failed += s["failed"]
        logger.info(f"\n{status} {report.skill_name}  score={report.score:.2f}  ({s['passed']}/{s['total']})")
        for r in report.results:
            if not r.passed:
                logger.info(f"   🔴 [{r.level.name}] {r.name}: {r.message}")

    logger.info(f"\n{'=' * 40}")
    logger.info(f"Total: {total_passed} passed, {total_failed} failed")


def _add_skill_parser(sub):
    skill = sub.add_parser("skill", help="Skill QA — lint (design) and test (execution)")
    skill_sub = skill.add_subparsers(dest="skill_cmd", required=True)

    p = skill_sub.add_parser("lint", help="Top-down lint: structure, deck compat, safety, contract")
    p.add_argument("skill", nargs="?", default="", help="Skill name (omit to lint all)")
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.set_defaults(func=_skill_lint)

    p = skill_sub.add_parser("test", help="Bottom-up test: unit, integration, regression, stress")
    p.add_argument("skill", nargs="?", default="", help="Skill name (omit to test all)")
    p.add_argument("--levels", default="unit,integration",
                   help="Comma-separated levels: unit,integration,regression,stress")
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.set_defaults(func=_skill_test)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="wb",
        description="WorkerBee CLI — direct access to job and todo systems.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  wb job create 'Refactor auth' 'Split JWT logic into service' --cycles 2\n"
            "  wb job ls\n"
            "  wb job status JOB-001\n"
            "  wb job tick\n"
            "  wb todo dashboard\n"
            "  wb todo draw morning\n"
            "  wb todo quick\n"
            "  wb todo stats 14\n"
            "  wb workspace\n"
            "  wb swarm listen\n"
            "  wb swarm menu\n"
            "  wb lark serve --port 8080\n"
            "  wb lark who 张三\n"
            "  wb lark chats\n"
            "  wb lark send --to 张三 hello\n"
            "  wb lark notify --to ou_xxx --text \"蜂群上线\"\n"
            "  wb deck mode\n"
            "  wb deck focus\n"
            "  wb deck add fs_write_file\n"
            "  wb skill lint web-research\n"
            "  wb skill test web-research --levels unit,integration\n"
            "  wb cron install\n"
            "  wb cron status\n"
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_job_parser(sub)
    _add_todo_parser(sub)
    _add_swarm_parser(sub)
    _add_workspace_parser(sub)
    _add_lark_parser(sub)
    _add_gateway_parser(sub)
    _add_deck_parser(sub)
    _add_skill_parser(sub)
    _add_cron_parser(sub)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()