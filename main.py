#!/usr/bin/env python3
"""Minimal Hermes — CLI entry point."""
import json
import os
import sys

# Import tools to trigger registration
import tools.terminal
import tools.file
import tools.web
import tools.subagent

from agent import AIAgent
from memory import SessionDB
from skills import SkillManager
from registry import registry
from infra_toolsets import InfraToolSet


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    # Auto-config from environment
    key = os.environ.get("ARKCODE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    base = os.environ.get("ARKCODE_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding")
    if key:
        return {
            "model": "kimi-k2.6",
            "provider": "anthropic",
            "api_key": key,
            "base_url": base,
            "max_iterations": 20,
            "system_prompt": (
                "You are a helpful coding assistant. You have access to tools:\n"
                "- sys_terminal: run shell commands\n"
                "- fs_read_file / fs_write_file / fs_search_files: file operations\n"
                "- net_web_search / net_web_extract: web access\n"
                "- agent_delegate_task: delegate subtasks to child agents\n"
                "Think step by step. Prefer reading files before editing."
            ),
            "tools": [
                "sys_terminal",
                "fs_read_file", "fs_write_file", "fs_search_files",
                "net_web_search", "net_web_extract",
                "agent_delegate_task"
            ]
        }
    print("❌ No API key found. Set ARKCODE_API_KEY or create config.json")
    sys.exit(1)


def main():
    config = load_config()
    agent = AIAgent(config)
    db = SessionDB()
    skill_mgr = SkillManager()
    infra = InfraToolSet()

    # Load skills
    loaded_skills = skill_mgr.load_all()
    if loaded_skills:
        print(f"Loaded {len(loaded_skills)} skill(s): {', '.join(loaded_skills)}")

    # Detect platform and print infra status
    plat = infra.platform
    print(f"Platform: {plat}")
    if plat != "linux":
        available = infra.get_available_tools()
        print(f"Infra tools: {', '.join(available) if available else 'none'}")
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
    print("Commands: /exit, /history, /tools, /clear, /todo, /goal, /skills, /cats")
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
            handle_todo(user_input, db, session_id)
            continue
        if user_input.lower().startswith("/goal"):
            handle_goal(user_input, db, session_id)
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

        # ── Skill matching + dynamic tool loading ──
        matched_skills = skill_mgr.match_skills(user_input)
        active_tools = list(config.get("tools", []))  # base tools
        skill_ctx = ""

        if matched_skills:
            print(f"  [Skills triggered: {', '.join(matched_skills)}]")
            skill_tools = skill_mgr.get_tools_for_skills(matched_skills)
            # Merge: base tools + skill-specific tools
            for t in skill_tools:
                if t not in active_tools:
                    active_tools.append(t)
            skill_ctx = skill_mgr.build_context_for_skills(matched_skills)

        # ── InfraToolSet filter: env-level gating ──
        active_tools = infra.filter_tools(active_tools)
        infra_tools = [t for t in active_tools if t not in config.get("tools", [])]
        if infra_tools:
            print(f"  [Infra gated: {', '.join(infra_tools)} available on {infra.platform}]")

        # Inject active goal into system context
        goal = db.get_active_goal(session_id)
        if goal:
            user_input = f"[Active Goal: {goal[1]}]\n{user_input}"

        # Inject skill context
        if skill_ctx:
            user_input = f"{skill_ctx}\n\n{user_input}"

        messages.append({"role": "user", "content": user_input})
        db.save_message(session_id, "user", user_input)

        print("\nAgent: ", end="", flush=True)
        try:
            response = agent.run(messages, tools=active_tools)
        except Exception as e:
            response = f"Error: {e}"
        print(response)

        messages.append({"role": "assistant", "content": response})
        db.save_message(session_id, "assistant", response)

    print(f"\nSession {session_id} saved.")


def handle_todo(cmd: str, db: SessionDB, session_id: str):
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


def handle_goal(cmd: str, db: SessionDB, session_id: str):
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


if __name__ == "__main__":
    main()
