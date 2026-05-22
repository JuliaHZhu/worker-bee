#!/usr/bin/env python3
"""Hermes Lite — CLI entry point.

Usage:
    hermes-lite              Start interactive session
    hermes-lite setup        Configure API key and model
    hermes-lite -m "hello"   Quick model ping test
    hermes-lite -c "hello"   Quick channel ping test (Feishu/Discord)
    hermes-lite --version    Show version
"""
import argparse
import json
import os
import sys
import threading

# Import tools to trigger registration

from agent import AIAgent
from memory import SessionDB
from skills import SkillManager
from registry import registry
from infra_toolsets import InfraToolSet
from deck import build_deck, Deck

VERSION = "0.1.0"

_tick_stop = threading.Event()
_tick_thread = None


def _cron_tick_loop(config: dict, skill_mgr):
    """Background thread: tick every 60 seconds."""
    from cron import scheduler
    while not _tick_stop.is_set():
        try:
            scheduler.tick(config, skill_mgr)
        except Exception as e:
            print(f"  [Cron tick error: {e}]")
        _tick_stop.wait(60)


def get_config_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    """Load config from file or env. Returns dict or None."""
    path = get_config_path()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    key = os.environ.get("ARKCODE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    base = os.environ.get("ARKCODE_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding")
    if key:
        return _make_config("anthropic", "kimi-k2.6", key, base)
    return None


def _make_config(provider, model, api_key, base_url, max_iter=20):
    return {
        "model": model,
        "provider": provider,
        "api_key": api_key,
        "base_url": base_url,
        "max_iterations": max_iter,
        "system_prompt": (
            "You are a helpful coding assistant. You have access to tools:\n"
            "- sys_terminal: run shell commands\n"
            "- fs_read_file / fs_write_file / fs_search_files: file operations\n"
            "- net_web_search / net_web_extract: web access\n"
            "- agent_delegate_task: delegate a single subtask to a child agent\n"
            "- agent_delegate_parallel: delegate multiple subtasks in parallel\n"
            "- agent_cross_validate: run the same task through multiple models for comparison\n"
            "Think step by step. Prefer reading files before editing."
        ),
        "tools": [
            "sys_terminal",
            "fs_read_file", "fs_write_file", "fs_search_files",
            "net_web_search", "net_web_extract",
            "agent_delegate_task", "agent_delegate_parallel", "agent_cross_validate"
        ]
    }


def setup():
    """Interactive onboarding — just provider + api_key."""
    print("=" * 45)
    print("  Hermes Lite — Setup")
    print("=" * 45)
    print()

    # Provider
    print("Provider:")
    print("  [1] Anthropic / Volcano (Anthropic protocol)")
    print("  [2] OpenAI-compatible (OpenAI protocol)")
    p = input("> ").strip()
    if p == "2":
        provider = "openai"
        default_model = "gpt-4o"
        default_base = "https://api.openai.com/v1"
    else:
        provider = "anthropic"
        default_model = "kimi-k2.6"
        default_base = "https://ark.cn-beijing.volces.com/api/coding"

    # API Key
    print()
    key = input("API Key: ").strip()
    if not key:
        print("❌ API key required.")
        sys.exit(1)

    # Optional overrides
    print()
    model = input(f"Model [{default_model}]: ").strip() or default_model
    base = input(f"Base URL [{default_base}]: ").strip() or default_base

    config = _make_config(provider, model, key, base)
    path = get_config_path()
    with open(path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    import stat
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    print()
    print(f"✅ Saved to {path}")
    print(f"   Provider: {provider} | Model: {model}")


def ping_model(message: str):
    """Quick model connectivity test."""
    config = load_config()
    if not config:
        print("❌ No config. Run: hermes-lite setup")
        sys.exit(1)
    print(f"→ Pinging {config['model']} ({config['provider']})...")
    try:
        agent = AIAgent(config)
        msgs = [{"role": "user", "content": message}]
        resp = agent.run(msgs)
        print("← Response:")
        print(resp)
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)


def ping_channel(message: str):
    """Quick channel connectivity test (Feishu/Discord)."""
    from tools.send_message import send_message
    infra = InfraToolSet()
    plat = infra.platform
    if plat == "linux":
        print("❌ No channel configured. Set FEISHU_WEBHOOK_URL or DISCORD_WEBHOOK_URL.")
        sys.exit(1)
    print(f"→ Sending to {plat}...")
    result = send_message(message)
    print("← Result:", result)


def run_session():
    """Main interactive session."""
    config = load_config()
    if not config:
        print("❌ No config found.")
        print("Run: hermes-lite setup")
        sys.exit(1)

    agent = AIAgent(config)
    db = SessionDB()
    skill_mgr = SkillManager()
    infra = InfraToolSet()

    loaded_skills = skill_mgr.load_all()
    if loaded_skills:
        print(f"Loaded {len(loaded_skills)} skill(s): {', '.join(loaded_skills)}")

    plat = infra.platform
    print(f"Platform: {plat}")
    if plat != "linux":
        available = infra.get_available_tools()
        print(f"Infra tools: {', '.join(available) if available else 'none'}")
    print()

    # Start cron scheduler in background
    global _tick_thread
    _tick_stop.clear()
    _tick_thread = threading.Thread(
        target=_cron_tick_loop,
        args=(config, skill_mgr),
        daemon=True,
        name="cron-tick"
    )
    _tick_thread.start()
    print("[Cron scheduler] started — tick every 60s")
    print()

    sessions = db.list_sessions()
    if sessions:
        print(f"Found {len(sessions)} session(s). Type 'new' for new session, or number to resume.")
        for i, (sid, created, title) in enumerate(sessions[:5]):
            print(f"  {i}: [{sid}] {title or '(no title)'} — {created[:19]}")
        choice = input("> ").strip()
        if choice.lower() == "new":
            session_id = db.create_session()
            messages = []
        else:
            try:
                session_id = sessions[int(choice)][0]
                messages = db.get_messages(session_id)
            except (ValueError, IndexError):
                session_id = db.create_session()
                messages = []
    else:
        session_id = db.create_session()
        messages = []

    print(f"\n✨ Hermes Lite — Session: {session_id}")
    print("Commands: /exit, /history, /tools, /clear, /todo, /goal, /skills, /cats, /infra")
    print("-" * 50)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("/exit", "exit", "quit"):
            break
        if user_input.lower() == "/history":
            for m in messages[-10:]:
                role = m["role"]
                content = m.get("content", "")[:80].replace("\n", " ")
                print(f"  [{role:10}] {content}...")
            continue
        if user_input.lower() == "/tools":
            cats = registry.list_by_category()
            for cat, names in sorted(cats.items()):
                print(f"  [{cat}] {', '.join(names)}")
            continue
        if user_input.lower() == "/cats":
            for cat, names in sorted(registry.list_by_category().items()):
                print(f"  {cat}: {len(names)} tool(s)")
            continue
        if user_input.lower() == "/infra":
            print(infra.describe())
            continue
        if user_input.lower() == "/clear":
            messages = []
            print("Context cleared.")
            continue
        if user_input.lower().startswith("/todo"):
            _handle_todo(user_input, db, session_id)
            continue
        if user_input.lower().startswith("/goal"):
            _handle_goal(user_input, db, session_id)
            continue
        if user_input.lower() == "/skills":
            skills = skill_mgr.list_skills()
            if skills:
                for name, meta in skills.items():
                    triggers = meta.get("triggers", [])
                    tools = meta.get("tools", [])
                    trig_str = f"  triggers: {', '.join(triggers)}" if triggers else ""
                    tool_str = f"  tools: {', '.join(tools)}" if tools else ""
                    print(f"  • {name}: {meta.get('description', 'No description')}{trig_str}{tool_str}")
            else:
                print("No skills loaded.")
            continue

        # --- Deck procurement: gather tools BEFORE execution ---
        print("  [Procuring deck...]", flush=True)

        # 1. Match skills by triggers
        matched_skills = skill_mgr.match_skills(user_input)
        if not matched_skills:
            # Fallback: let LLM semantically select (or use all if no skills)
            matched_skills = list(skill_mgr.list_skills().keys())

        # 2. Collect tools from matched skills
        skill_tools = skill_mgr.get_tools_for_skills(matched_skills)

        # 3. Build deck with redundancy slots (+3 baseline)
        from deck import build_deck
        deck = build_deck(skill_tools, registry, redundancy=3)

        # 4. Merge platform base tools from config
        base_tools = set(config.get("tools", []))
        merged_tools = set(deck.tools) | base_tools
        final_tools = infra.filter_tools(list(merged_tools))
        from deck import Deck
        deck = Deck(final_tools, registry)

        print(f"  [Deck ready: {deck.size()} tools]")

        # Inject goal
        goal = db.get_active_goal(session_id)
        if goal:
            user_input = f"[Active Goal: {goal[1]}]\n{user_input}"

        messages.append({"role": "user", "content": user_input})
        db.save_message(session_id, "user", user_input)

        print("\nAgent: ", end="", flush=True)
        try:
            response = agent.run(messages, deck=deck)
        except Exception as e:
            response = f"Error: {e}"

        # Halt if the agent hit the iteration limit — the deck was insufficient
        if response == "(reached max iterations)":
            print(response)
            print("\n⚠️  The task could not be completed with the current tool deck.")
            print("   This usually means the approach needs to change, or a tool is missing.")
            print("   Please rephrase your request or check /tools and /skills.")
            messages.append({"role": "assistant", "content": response})
            db.save_message(session_id, "assistant", response)
            continue

        print(response)

        messages.append({"role": "assistant", "content": response})
        db.save_message(session_id, "assistant", response)

    # Stop cron scheduler
    _tick_stop.set()
    if _tick_thread:
        _tick_thread.join(timeout=5)
        from cron import scheduler
        scheduler.shutdown()
        print("[Cron scheduler] stopped")

    print(f"\nSession {session_id} saved.")


def _handle_todo(cmd: str, db: SessionDB, session_id: str):
    parts = cmd.split(None, 2)
    if len(parts) == 1:
        todos = db.list_todos(session_id)
        if not todos:
            print("No todos.")
            return
        for tid, content, status, created in todos:
            mark = "✓" if status == "done" else "○"
            print(f"  {mark} [{tid}] {content}")
    elif parts[1] == "add" and len(parts) == 3:
        tid = db.add_todo(session_id, parts[2])
        print(f"Added todo [{tid}].")
    elif parts[1] == "done" and len(parts) == 3:
        try:
            db.update_todo_status(int(parts[2]), "done")
            print(f"Marked todo {parts[2]} as done.")
        except ValueError:
            print("Usage: /todo done <id>")
    elif parts[1] == "pending" and len(parts) == 3:
        try:
            db.update_todo_status(int(parts[2]), "pending")
            print(f"Marked todo {parts[2]} as pending.")
        except ValueError:
            print("Usage: /todo pending <id>")
    elif parts[1] == "delete" and len(parts) == 3:
        try:
            db.delete_todo(int(parts[2]))
            print(f"Deleted todo {parts[2]}.")
        except ValueError:
            print("Usage: /todo delete <id>")
    else:
        print("Usage: /todo, /todo add <text>, /todo done <id>, /todo pending <id>, /todo delete <id>")


def _handle_goal(cmd: str, db: SessionDB, session_id: str):
    parts = cmd.split(None, 1)
    if len(parts) == 1:
        goal = db.get_active_goal(session_id)
        if goal:
            print(f"Active goal: {goal[1]}")
        else:
            print("No active goal.")
    elif parts[1] == "clear":
        db.complete_goal(session_id)
        print("Goal cleared.")
    elif parts[1] == "list":
        goals = db.list_goals(session_id)
        for gid, content, status, created, completed in goals:
            print(f"  [{status:12}] {content}")
    else:
        db.set_goal(session_id, parts[1])
        print(f"Goal set: {parts[1]}")


def main():
    parser = argparse.ArgumentParser(
        prog="hermes-lite",
        description="Lightweight AI agent with tool access.",
        add_help=False,
    )
    parser.add_argument("setup", nargs="?", help="Run setup wizard")
    parser.add_argument("-m", "--model-ping", metavar="MSG", help="Quick model ping test")
    parser.add_argument("-c", "--channel-ping", metavar="MSG", help="Quick channel ping test (Feishu/Discord)")
    parser.add_argument("-v", "--version", action="store_true", help="Show version")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")
    args = parser.parse_args()

    if args.version:
        print(f"hermes-lite {VERSION}")
        return

    if args.help:
        print("""Hermes Lite — Lightweight AI Agent

Usage:
  hermes-lite              Start interactive session
  hermes-lite setup        Configure API key and model
  hermes-lite -m "hello"   Quick model connectivity test
  hermes-lite -c "hello"   Quick channel connectivity test
  hermes-lite -v           Show version

Onboarding:
  1. hermes-lite setup     → Enter API key
  2. hermes-lite -m "hi"   → Verify model responds
  3. export FEISHU_WEBHOOK_URL=...  → Optional: configure channel
  4. hermes-lite -c "hi"   → Verify channel works
  5. hermes-lite           → Start using
""")
        return

    if args.model_ping:
        ping_model(args.model_ping)
        return

    if args.channel_ping:
        ping_channel(args.channel_ping)
        return

    if args.setup == "setup":
        setup()
        return

    # Default: run interactive session
    run_session()


if __name__ == "__main__":
    main()
