"""Session state helpers for run_session."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from agent.deck import DeckManager
from agent.infra_toolsets import InfraToolSet
from agent.memory import SessionDB
from agent.registry import registry
from agent.skills import SkillManager
from agent.main import _cron_tick_loop, _tick_stop, _tick_thread, load_bee_config, load_config, AIAgent

logger = logging.getLogger(__name__)


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
        logger.error("❌ No config found.")
        logger.info("Run: worker-bee setup")
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
        logger.info("Loaded %d skill(s): %s", len(loaded_skills), ", ".join(loaded_skills))

    # Bee role detection
    bee_cfg = load_bee_config()
    bee_role = bee_cfg.get("role", "seed")
    bee_evolution = bee_cfg.get("evolution", {})
    logger.info("Bee role: %s", bee_role)
    if bee_role == "seed":
        stage = bee_evolution.get("stage", "seed")
        tasks = bee_evolution.get("tasks_completed", 0)
        logger.info("  Evolution stage: %s | tasks completed: %s", stage, tasks)
        task_types = bee_evolution.get("task_types", {})
        if task_types:
            logger.info("  Task types: %s", task_types)
    elif bee_role != "seed":
        evolved_at = bee_evolution.get("evolved_at", "unknown")
        logger.info("  Evolved at: %s", evolved_at)

    plat = infra.platform
    logger.info("Platform: %s", plat)
    if plat != "linux":
        available = infra.get_available_tools()
        logger.info("Infra tools: %s", ", ".join(available) if available else "none")
    logger.info("")
    logger.info("Deck mode: %s  (use /deck to manage)", deck_mgr.mode)
    logger.info("")

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
    logger.info("[Cron scheduler] started — tick every 60s")
    logger.info("")

    # Session selection / creation
    sessions = db.list_sessions()
    if sessions:
        logger.info("Found %d session(s). Type 'new' for new session, or number to resume.", len(sessions))
        for i, (sid, created, title) in enumerate(sessions[:5]):
            logger.info("  %d: [%s] %s — %s", i, sid, title or "(no title)", created[:19])
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
        logger.info("[Handoff loaded] %s...", handoff[:80])

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
        logger.info("[Cron scheduler] stopped")

    try:
        handoff_path = state.db.export_handoff(state.session_id)
        logger.info("[Handoff] exported to %s", handoff_path)
    except Exception as e:
        logger.error("[Handoff] export failed: %s", e)

    try:
        from agent.main import _make_handoff
        h = _make_handoff(state.messages)
        if h:
            state.db.save_handoff(state.session_id, h)
            logger.info("[Handoff] saved for next session")
    except Exception as e:
        logger.error("[Handoff] save failed: %s", e)

    logger.info("\nSession %s saved.", state.session_id)
