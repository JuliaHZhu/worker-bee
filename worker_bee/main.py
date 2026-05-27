#!/usr/bin/env python3
"""Worker Bee — CLI entry point.

Usage:
    worker-bee              Start interactive session
    worker-bee setup        Configure API key and model
    worker-bee -m "hello"   Quick model ping test
    worker-bee -c "hello"   Quick channel ping test (Feishu/Discord)
    worker-bee --version    Show version
"""
import argparse
import json
import os
import sys
import threading

from worker_bee.agent import AIAgent
from worker_bee.memory import SessionDB
from worker_bee.skills import SkillManager
from worker_bee.registry import registry
from worker_bee.infra_toolsets import InfraToolSet
from worker_bee.deck import build_deck, Deck

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


import os
import json
from pathlib import Path


def _config_dir() -> Path:
    """Return the user config directory (~/.worker-bee)."""
    return Path.home() / ".worker-bee"


def get_config_path():
    _config_dir().mkdir(parents=True, exist_ok=True)
    return str(_config_dir() / "config.json")


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
    print("  Worker Bee — Setup")
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
        print("❌ No config. Run: worker-bee setup")
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
        print("Run: worker-bee setup")
        sys.exit(1)

    agent = AIAgent(config)
    db = SessionDB()
    skill_mgr = SkillManager()
    infra = InfraToolSet()

    base_system_prompt = agent.system_prompt

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

    # Session-aware system prompt so the agent knows its session ID for tagged-session tools
    agent.system_prompt = f"{base_system_prompt}\n\nCurrent session ID: {session_id}"

    print(f"\n✨ Worker Bee — Session: {session_id}")
    print("Commands: /exit, /history, /tools, /clear, /todo, /skills, /cats, /infra")
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
                tags = m.get("tags", [])
                tag_str = f"  tags:{','.join(tags)}" if tags else ""
                print(f"  [{role:10}] {content}...{tag_str}")
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
        if user_input.lower().startswith("/task"):
            print("⚠️  /task is deprecated. Use natural language with the tagged-session skill instead.")
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
        deck = build_deck(skill_tools, registry, redundancy=3)

        # 4. Merge platform base tools from config
        base_tools = set(config.get("tools", []))
        merged_tools = set(deck.tools) | base_tools
        final_tools = infra.filter_tools(list(merged_tools))
        deck = Deck(final_tools, registry)

        print(f"  [Deck ready: {deck.size()} tools]")

        # --- Dynamic context injection for skill-authoring skills ---
        skill_context = skill_mgr.build_context_for_skills(matched_skills)
        if skill_context:
            # Check if any matched skill is an authoring skill
            has_authoring = any(
                (skill_mgr.get_skill(sn) or {}).get("category") == "skill-authoring"
                for sn in matched_skills
            )
            if has_authoring:
                # Inject project metadata: existing skills and tools
                lines = ["\n## Active Project Context (auto-injected)"]
                lines.append("### Existing Skills")
                for name, meta in skill_mgr.list_skills().items():
                    triggers = meta.get("triggers", [])
                    trig_str = f"  [{', '.join(triggers)}]" if triggers else ""
                    lines.append(f"- {name}{trig_str}")
                lines.append("\n### Existing Tools")
                for name in sorted(registry.list_tools()):
                    info = registry.get_tool_info(name)
                    desc = info.get("description", "")[:50] if info else ""
                    lines.append(f"- {name}: {desc}")
                skill_context += "\n".join(lines)
            # Temporarily augment system prompt with skill context
            agent.system_prompt = f"{agent.system_prompt}\n\n{skill_context}"

        # --- Tag extraction: leading #tags are stripped and stored separately ---
        tags, clean_input = _extract_tags(user_input)

        messages.append({"role": "user", "content": clean_input, "tags": tags})
        db.save_message(session_id, "user", clean_input, tags=tags)

        print("\nAgent: ", end="", flush=True)
        try:
            response = agent.run(messages, deck=deck)
        except Exception as e:
            response = f"Error: {e}"
        finally:
            # Restore original system prompt (keeping session ID suffix)
            if skill_context:
                agent.system_prompt = f"{base_system_prompt}\n\nCurrent session ID: {session_id}"

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


def _extract_tags(text: str):
    """Extract leading #tags from user input.

    Example:
        "#design #question how does this work?" -> (["#design", "#question"], "how does this work?")
        "no tags here" -> ([], "no tags here")
    """
    words = text.split()
    tags = []
    idx = 0
    for i, w in enumerate(words):
        if w.startswith("#") and len(w) > 1:
            tags.append(w)
            idx = i + 1
        else:
            break
    clean = " ".join(words[idx:]) if idx > 0 else text
    return tags, clean


def main():
    parser = argparse.ArgumentParser(
        prog="worker-bee",
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
        print(f"worker-bee {VERSION}")
        return

    if args.help:
        print("""Worker Bee — Lightweight AI Agent

Usage:
  worker-bee              Start interactive session
  worker-bee setup        Configure API key and model
  worker-bee -m "hello"   Quick model connectivity test
  worker-bee -c "hello"   Quick channel connectivity test
  worker-bee -v           Show version

Onboarding:
  1. worker-bee setup     → Enter API key
  2. worker-bee -m "hi"   → Verify model responds
  3. export FEISHU_WEBHOOK_URL=...  → Optional: configure channel
  4. worker-bee -c "hi"   → Verify channel works
  5. worker-bee           → Start using
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
