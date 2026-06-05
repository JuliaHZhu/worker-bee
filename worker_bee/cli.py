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

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
