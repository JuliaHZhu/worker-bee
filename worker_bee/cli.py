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
import sys
from pathlib import Path

# Ensure repo root is importable when running in dev mode
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


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
    print(out)


def _job_ls(args):
    from tools.job_probe import probe_status
    out = probe_status()
    print(out)


def _job_status(args):
    from tools.job_probe import probe_status
    out = probe_status(job_id=args.job_id)
    print(out)


def _job_handoff(args):
    from tools.job_probe import probe_handoff
    out = probe_handoff(job_id=args.job_id)
    print(out)


def _job_audit(args):
    from tools.job_probe import probe_status
    out = probe_status(job_id=args.job_id)
    print(out)


def _job_tick(args):
    from tools.job_probe import probe_tick
    out = probe_tick()
    print(out)


def _job_run(args):
    """Execute a job: read meta, infer skill, run tools, write artifacts."""
    import os
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from tools.job_probe import _read_meta, _ensure_job_dir, _append_event, _atomic_write
    from worker_bee.registry import registry

    job_id = args.job_id
    meta, body = _read_meta(job_id)
    if meta is None:
        print(f"Error: {job_id} not found.")
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

    print(f"[{job_id}] Detected skill: {skill}")
    print(f"[{job_id}] Title: {title}")

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
        print(f"[{job_id}] Searching: {query}")

        results = registry.call("net_web_search", {"query": query, "num_results": 5})
        print(f"[{job_id}] Search returned {len(results)} chars")

        # Extract top URLs
        import re
        urls = re.findall(r"https?://[^\s\n]+", results)
        extracts = []
        for url in urls[:3]:
            print(f"[{job_id}] Extracting: {url}")
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
            print(f"[{job_id}] Extract written: {extract_path.name}")

        # Save main report
        report_path = artifacts_dir / f"{skill}-{today}-report.md"
        tmp = report_path.with_suffix(".tmp")
        tmp.write_text(report, encoding="utf-8")
        tmp.replace(report_path)

        _append_event(job_id, f"JOB_RUN skill={skill} query='{query}' artifacts={len(extracts)+1}")
        print(f"[{job_id}] Report written: {report_path.name}")

    else:
        print(f"[{job_id}] Skill '{skill}' execution not yet implemented.")
        sys.exit(1)

    # Update meta
    meta["current_cycle"] = meta.get("current_cycle", 0) + 1
    from tools.job_probe import _write_meta
    _write_meta(job_id, meta, body)
    print(f"[{job_id}] Cycle {meta['current_cycle']}/{meta.get('estimated_cycles', 1)} complete.")


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
    print(todo_ball_machine(action="dashboard"))


def _todo_today(args):
    from tools.todo_ball_machine import todo_ball_machine
    print(todo_ball_machine(action="today"))


def _todo_draw(args):
    from tools.todo_ball_machine import todo_ball_machine
    print(todo_ball_machine(action="draw", session=args.session))


def _todo_quick(args):
    from tools.todo_ball_machine import todo_ball_machine
    print(todo_ball_machine(action="quick_draw"))


def _todo_complete(args):
    from tools.todo_ball_machine import todo_ball_machine
    print(todo_ball_machine(action="complete", session=args.session))


def _todo_history(args):
    from tools.todo_ball_machine import todo_ball_machine
    n = str(args.days) if args.days else None
    print(todo_ball_machine(action="history", content=n))


def _todo_stats(args):
    from tools.todo_ball_machine import todo_ball_machine
    n = str(args.days) if args.days else None
    print(todo_ball_machine(action="stats", content=n))


def _todo_day(args):
    from tools.todo_ball_machine import todo_ball_machine
    d = args.date or None
    print(todo_ball_machine(action="day", content=d))


def _todo_box(args):
    from tools.todo_ball_machine import todo_ball_machine
    print(todo_ball_machine(action="box_list"))


def _todo_cycle(args):
    from tools.todo_ball_machine import todo_ball_machine
    print(todo_ball_machine(action="cycle_status"))


def _todo_new_cycle(args):
    from tools.todo_ball_machine import todo_ball_machine
    print(todo_ball_machine(action="new_cycle", content=args.name))


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
def _swarm_listen(args):
    """Start the NATS swarm listener (background process)."""
    import subprocess
    import os
    from pathlib import Path

    listener_path = Path(__file__).parent.parent / "swarm" / "listener.py"
    if not listener_path.exists():
        print(f"Error: listener not found at {listener_path}")
        sys.exit(1)

    nats_url = args.url or os.environ.get("SWARM_NATS_URL", "nats://localhost:4222")
    print(f"[wb swarm listen] Starting listener → {nats_url}")
    print(f"[wb swarm listen] Writing messages to ~/.worker-bee/mailbox/inbox/")
    print(f"[wb swarm listen] Press Ctrl+C to stop")
    sys.stdout.flush()

    try:
        subprocess.run(
            [sys.executable, str(listener_path), nats_url],
            check=True,
        )
    except KeyboardInterrupt:
        print("\n[wb swarm listen] Stopped.")


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
        print(f"✅ NATS: connected to {connected}")
    except Exception as e:
        print(f"❌ NATS: {e}")

    # Check mailbox
    inbox = Path.home() / ".worker-bee" / "mailbox" / "inbox"
    read = Path.home() / ".worker-bee" / "mailbox" / "read"
    if inbox.exists():
        unread = len(list(inbox.glob("*.json")))
        print(f"📬 Mailbox: {unread} unread, inbox={inbox}")
    else:
        print(f"📭 Mailbox: not initialized (no messages yet)")

    # Check if listener process is running
    import subprocess
    result = subprocess.run(
        ["pgrep", "-f", "swarm/listener.py"],
        capture_output=True, text=True,
    )
    if result.stdout.strip():
        print(f"🟢 Listener: running (PID {result.stdout.strip().split()[0]})")
    else:
        print(f"🔴 Listener: not running (start with: wb swarm listen)")


def _add_swarm_parser(sub):
    swarm = sub.add_parser("swarm", help="NATS swarm communication")
    swarm_sub = swarm.add_subparsers(dest="swarm_cmd", required=True)

    p = swarm_sub.add_parser("listen", help="Start NATS listener (writes messages to mailbox)")
    p.add_argument("url", nargs="?", default=None, help="NATS URL (default: nats://localhost:4222)")
    p.set_defaults(func=_swarm_listen)

    p = swarm_sub.add_parser("status", help="Check NATS connection and listener health")
    p.set_defaults(func=_swarm_status)


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
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_job_parser(sub)
    _add_todo_parser(sub)
    _add_swarm_parser(sub)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
