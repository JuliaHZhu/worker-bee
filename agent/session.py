"""Session state helpers for run_session."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from agent.deck import DeckManager
from agent.infra_toolsets import InfraToolSet
from agent.memory import SessionDB
from agent.registry import registry
from agent.skills import SkillManager
from agent.main import _cron_tick_loop, _tick_stop, _tick_thread, load_bee_config, load_config, AIAgent


@dataclass
class _SessionState:
    """Encapsulates all mutable state for a single interactive session."""

    config: dict[str, Any]
    agent: AIAgent
    db: SessionDB
    skill_mgr: SkillManager
    infra: InfraToolSet
    deck_mgr: DeckManager
    session_id: str
    messages: list[dict] = field(default_factory=list)
    base_system_prompt: str = ""
    bee_role: str = "seed"
    bee_evolution: dict = field(default_factory=dict)


def _init_session(temperature_override: float | None = None) -> _SessionState:
    """Initialise config, agent, DB, skills, deck, and cron scheduler."""
    config = load_config()
    if not config:
        print("❌ No config found.")
        print("Run: worker-bee setup")
        raise SystemExit(1)

    if temperature_override is not None:
        config["temperature"] = temperature_override

    if config.get("auto_confirm"):
        import os as _os
        _os.environ["WORKER_BEE_AUTO_CONFIRM"] = "true"
    else:
        import os as _os
        _os.environ.pop("WORKER_BEE_AUTO_CONFIRM", None)

    agent = AIAgent(config)
    db = SessionDB()
    skill_mgr = SkillManager()
    infra = InfraToolSet()
    deck_mgr = DeckManager(config.get("tools", []), registry)

    base_system_prompt = agent.system_prompt

    loaded_skills = skill_mgr.load_all()
    if loaded_skills:
        print(f"Loaded {len(loaded_skills)} skill(s): {', '.join(loaded_skills)}")

    # Bee role detection
    bee_cfg = load_bee_config()
    bee_role = bee_cfg.get("role", "seed")
    bee_evolution = bee_cfg.get("evolution", {})
    print(f"Bee role: {bee_role}")
    if bee_role == "seed":
        stage = bee_evolution.get("stage", "seed")
        tasks = bee_evolution.get("tasks_completed", 0)
        print(f"  Evolution stage: {stage} | tasks completed: {tasks}")
        task_types = bee_evolution.get("task_types", {})
        if task_types:
            print(f"  Task types: {task_types}")
    elif bee_role != "seed":
        evolved_at = bee_evolution.get("evolved_at", "unknown")
        print(f"  Evolved at: {evolved_at}")

    plat = infra.platform
    print(f"Platform: {plat}")
    if plat != "linux":
        available = infra.get_available_tools()
        print(f"Infra tools: {', '.join(available) if available else 'none'}")
    print()
    print(f"Deck mode: {deck_mgr.mode}  (use /deck to manage)")
    print()

    # Start cron scheduler in background
    global _tick_thread
    if _tick_thread is not None and _tick_thread.is_alive():
        _tick_stop.set()
        _tick_thread.join(timeout=2)
    _tick_stop.clear()
    _tick_thread = threading.Thread(
        target=_cron_tick_loop,
        args=(config, skill_mgr),
        daemon=True,
        name="cron-tick",
    )
    _tick_thread.start()
    print("[Cron scheduler] started — tick every 60s")
    print()

    # Session selection / creation
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

    # Auto handoff injection
    handoff = db.get_handoff()
    if handoff:
        messages.insert(0, {"role": "user", "content": f"[Handoff] {handoff}"})
        print(f"[Handoff loaded] {handoff[:80]}...")

    # Session-aware system prompt
    agent.system_prompt = f"{base_system_prompt}\n\nCurrent session ID: {session_id}"

    return _SessionState(
        config=config,
        agent=agent,
        db=db,
        skill_mgr=skill_mgr,
        infra=infra,
        deck_mgr=deck_mgr,
        session_id=session_id,
        messages=messages,
        base_system_prompt=base_system_prompt,
        bee_role=bee_role,
        bee_evolution=bee_evolution,
    )


def _shutdown_session(state: _SessionState) -> None:
    """Stop cron scheduler, export handoff, and print farewell."""
    _tick_stop.set()
    if _tick_thread:
        _tick_thread.join(timeout=5)
        from cron import scheduler
        scheduler.shutdown()
        print("[Cron scheduler] stopped")

    try:
        handoff_path = state.db.export_handoff(state.session_id)
        print(f"[Handoff] exported to {handoff_path}")
    except Exception as e:
        print(f"[Handoff] export failed: {e}")

    try:
        from agent.main import _make_handoff
        h = _make_handoff(state.messages)
        if h:
            state.db.save_handoff(state.session_id, h)
            print("[Handoff] saved for next session")
    except Exception as e:
        import sys
        print(f"[Handoff] save failed: {e}", file=sys.stderr)

    print(f"\nSession {state.session_id} saved.")
