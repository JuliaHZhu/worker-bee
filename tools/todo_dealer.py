"""TODO Ball Machine — embedded tool for hermes-lite.

Directly calls the TODO Ball Machine use-case layer (no subprocess).
All state lives under the todo_dealer/ directory.
Set ENTP_BASE_PATH env var to override the data directory.
"""
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from registry import registry

# ---------------------------------------------------------------------------
# Path bootstrap — ensure TODO modules are importable
# ---------------------------------------------------------------------------
_TODO_DIR = Path(__file__).parent.parent / "todo_dealer"
_TODO_BASE = Path(os.environ.get("ENTP_BASE_PATH", _TODO_DIR))
os.environ["ENTP_BASE_PATH"] = str(_TODO_BASE)

_todo_sys = str(_TODO_DIR)
if _todo_sys not in sys.path:
    sys.path.insert(0, _todo_sys)

# Lazy imports (heavy init on first call)
_use_case_factory = None
_block_manager = None


def _factory():
    global _use_case_factory
    if _use_case_factory is None:
        from todo_use_cases import UseCaseFactory
        _use_case_factory = UseCaseFactory()
    return _use_case_factory


def _bm():
    global _block_manager
    if _block_manager is None:
        from todo_managers import BlockManager
        _block_manager = BlockManager(_TODO_BASE)
    return _block_manager


def _today() -> date:
    return date.today()


def _session_enum(s: str):
    from todo_models import Session
    return Session(s.lower())


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Box metadata (中文名称 → 信息)
# ---------------------------------------------------------------------------
_BOX_META = {
    "博士工作": {"emoji": "🎓", "code": "A"},
    "AI创业工作": {"emoji": "🤖", "code": "B"},
    "健康运动": {"emoji": "💪", "code": "C"},
    "治愈休息": {"emoji": "🧘", "code": "D"},
    "空间探索": {"emoji": "🌍", "code": "E"},
    "家务整理": {"emoji": "🏠", "code": "F"},
}

_STATUS_EMOJI = {
    "completed": "✅", "planned": "📋",
    "pending": "⏳", "cancelled": "❌",
}
_SESSION_LABEL = {
    "am": "上午场", "pm": "下午场",
    "evening": "晚间场", "overtime": "加班场",
}


def _fmt_block(block: dict) -> str:
    box = block.get("box", "")
    status = block.get("status", "unknown")
    meta = _BOX_META.get(box, {})
    return (
        f"{_STATUS_EMOJI.get(status, '❓')} "
        f"{meta.get('emoji', '')} "
        f"{block.get('content', '无内容')} "
        f"[{meta.get('code', box)}]"
    )


def _load_draws(target_date: date = None):
    """Load daily_draws JSON if exists."""
    target_date = target_date or _today()
    date_str = target_date.strftime("%Y%m%d")
    draw_file = _TODO_BASE / "daily_draws" / f"{date_str}_draw.json"
    if draw_file.exists():
        with open(draw_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
def _action_dashboard() -> str:
    result = _factory().status.execute()
    lines = ["═══ TODO Ball Machine 仪表盘 ═══", ""]
    lines.append(f"📅 今日: {_today()}")
    today_blocks = result.get('today', [])
    remaining = 4 - len(today_blocks)  # am+pm+evening+overtime
    lines.append(f"⏳ 剩余场次: {max(0, remaining)}")
    lines.append(f"📊 周期进度: {result.get('cycle_progress', 0)}%")
    lines.append("")
    lines.append("━ 今日安排 ━")
    if today_blocks:
        for b in today_blocks:
            sess = b.get('session', '')
            lines.append(f"  • {_SESSION_LABEL.get(sess, sess)}: {_fmt_block(b)}")
    else:
        lines.append("  （暂无安排）")
    lines.append("")
    lines.append("━ 盒子配额 ━")
    for key, info in sorted(result.get('boxes', {}).items()):
        meta = _BOX_META.get(key, {})
        lines.append(
            f"  {meta.get('emoji', '')} {meta.get('code', key)}({key}): "
            f"{info.get('used',0)}/{info.get('total',0)} 已用, 剩{info.get('remaining',0)}"
        )
    return "\n".join(lines)


def _action_today() -> str:
    today = _today()
    blocks = _bm().load_blocks(today)
    draws_data = _load_draws(today)

    # Build lookup
    block_by_session = {}
    for b in blocks:
        if b.session:
            block_by_session[b.session.value] = b.to_dict()

    draw_by_session = {}
    if draws_data and "draws" in draws_data:
        draw_by_session = draws_data["draws"]

    lines = [f"═══ 今日场次 ({today}) ═══", ""]
    for key in ("am", "pm", "evening", "overtime"):
        label = _SESSION_LABEL.get(key, key)
        if key in block_by_session:
            lines.append(f"  {label}: {_fmt_block(block_by_session[key])}")
        elif key in draw_by_session:
            d = draw_by_session[key]
            box = d.get("box", "")
            meta = _BOX_META.get(box, {})
            lines.append(
                f"  {label}: 📋 {meta.get('emoji', '')} "
                f"{d.get('content','无内容')} [{meta.get('code', box)}]"
            )
        else:
            extra = "（可选）" if key == "overtime" else ""
            lines.append(f"  {label}: 待抽取{extra}")
    return "\n".join(lines)


def _action_draw(session: str) -> str:
    if not session:
        return "❌ 请提供 session"
    result = _factory().draw_session.execute(session)
    if not result.get("success"):
        return f"❌ {result.get('message', '抽取失败')}"
    block = result.get("block", {})
    return (
        f"✅ {result['message']}\n"
        f"  {_fmt_block(block)}\n"
        f"  时长: {block.get('duration', '?')}h"
    )


def _action_quick_draw() -> str:
    result = _factory().quick_draw.execute()
    if not result.get("success"):
        return f"❌ {result.get('message', '快速抽取失败')}"
    lines = [f"✅ {result['message']}", ""]
    for b in result.get("blocks", []):
        lines.append(f"  • {_SESSION_LABEL.get(b.get('session',''), b.get('session',''))}: {_fmt_block(b)}")
    return "\n".join(lines)


def _action_box_list() -> str:
    result = _factory().status.execute()
    lines = ["═══ 盒子配额 ═══", ""]
    for key, info in sorted(result.get('boxes', {}).items()):
        meta = _BOX_META.get(key, {})
        lines.append(
            f"  {meta.get('emoji', '')} {meta.get('code', key)} ({key}): "
            f"{info.get('total',0)}总 | {info.get('used',0)}用 | {info.get('remaining',0)}剩"
        )
    return "\n".join(lines)


def _action_cycle_status() -> str:
    result = _factory().status.execute()
    boxes = result.get('boxes', {})
    total_used = sum(v.get("used", 0) for v in boxes.values())
    total_quota = sum(v.get("total", 0) for v in boxes.values())
    rate = int(total_used / total_quota * 100) if total_quota > 0 else 0
    info = result.get('cycle_info', {})
    start = info.get('start_date', '')
    end = info.get('end_date', '')
    return (
        "═══ 周期状态 ═══\n\n"
        f"  周期: {info.get('name', '未知')}\n"
        f"  起止: {start} → {end}\n"
        f"  完成度: {rate}% ({total_used}/{total_quota})\n"
        f"  周期进度: {result.get('cycle_progress', 0)}%"
    )


def _action_complete(block_id: str) -> str:
    if not block_id:
        return "❌ 请提供 block_id"
    today = _today()
    blocks = _bm().load_blocks(today)
    block = _bm().find_block_by_id(blocks, block_id)
    if not block:
        # search across all cycle blocks
        from todo_infrastructure import config_manager
        cfg = config_manager.load_config()
        cycle_start = datetime.strptime(cfg.get("start_date", "2026-04-01"), "%Y-%m-%d").date()
        all_blocks = _bm().load_all_blocks(cycle_start)
        block = _bm().find_block_by_id(all_blocks, block_id)
        if block:
            blocks = all_blocks
    if not block:
        return f"❌ 找不到 block: {block_id}"
    from todo_models import BlockStatus
    _bm().update_block(blocks, block_id, status=BlockStatus.COMPLETED)
    _bm().save_blocks(blocks, block.date)
    return f"✅ Block {block_id} 已标记为完成"


def _action_redraw(session: str) -> str:
    try:
        sess = _session_enum(session)
    except Exception as e:
        return f"❌ 场次错误: {e}"
    today = _today()
    blocks = _bm().load_blocks(today)
    existing = _bm().find_block_by_session(blocks, sess)
    if existing:
        # Return ball to pool
        uf = _factory()
        if existing.ball_id:
            uf._ball_pool_manager.return_ball(existing.box, existing.ball_id)
        blocks = [b for b in blocks if b.id != existing.id]
        _bm().save_blocks(blocks, today)
    # Draw new
    result = _factory().draw_session.execute(sess)
    if not result.get("success"):
        return f"❌ {result.get('message', '重抽失败')}"
    block = result.get("block", {})
    return (
        f"🔄 重抽完成\n"
        f"  {_fmt_block(block)}\n"
        f"  时长: {block.get('duration', '?')}h"
    )


def _action_edit(session: str, content: str) -> str:
    try:
        sess = _session_enum(session)
    except Exception as e:
        return f"❌ 场次错误: {e}"
    if not content:
        return "❌ 请提供 content"
    today = _today()
    blocks = _bm().load_blocks(today)
    block = _bm().find_block_by_session(blocks, sess)
    if not block:
        return f"❌ {session} 场暂无 block，请先抽取"
    _bm().update_block(blocks, block.id, content=content)
    _bm().save_blocks(blocks, today)
    return f"✅ {session} 场内容已更新: {content}"


def _action_help() -> str:
    return (
        "═══ TODO Ball Machine 帮助 ═══\n\n"
        "用法: todo_dealer(action='...', [session=..., content=..., block_id=...])\n\n"
        "  dashboard    — 系统仪表盘\n"
        "  today        — 今日场次状态\n"
        "  draw         — 抽取指定场次 (session=am/pm/evening/overtime)\n"
        "  quick_draw   — 快速抽取三场\n"
        "  redraw       — 重抽指定场次\n"
        "  edit         — 编辑场次内容 (session + content)\n"
        "  complete     — 完成 block (block_id)\n"
        "  box_list     — 盒子配额列表\n"
        "  cycle_status — 周期状态\n"
        "  help         — 显示本帮助"
    )


# ---------------------------------------------------------------------------
# Public handler
# ---------------------------------------------------------------------------
def todo_dealer(
    action: str,
    session: Optional[str] = None,
    content: Optional[str] = None,
    block_id: Optional[str] = None,
) -> str:
    """TODO Ball Machine tool.

    Args:
        action: 操作类型
        session: 场次名 (am/pm/evening/overtime)
        content: 编辑内容
        block_id: block ID
    """
    action = action.lower().strip()
    dispatch = {
        "dashboard": lambda: _action_dashboard(),
        "today": lambda: _action_today(),
        "draw": lambda: _action_draw(session or ""),
        "quick_draw": lambda: _action_quick_draw(),
        "quick": lambda: _action_quick_draw(),
        "redraw": lambda: _action_redraw(session or ""),
        "edit": lambda: _action_edit(session or "", content or ""),
        "complete": lambda: _action_complete(block_id or ""),
        "box_list": lambda: _action_box_list(),
        "box": lambda: _action_box_list(),
        "cycle_status": lambda: _action_cycle_status(),
        "cycle": lambda: _action_cycle_status(),
        "help": lambda: _action_help(),
    }
    handler = dispatch.get(action)
    if not handler:
        return f"❌ 未知 action: {action}\n可用: {', '.join(dispatch.keys())}"
    try:
        return handler()
    except Exception as e:
        return f"❌ 执行失败: {e}"


registry.register(
    name="todo_dealer",
    description=(
        "TODO Ball Machine — 人生任务管理系统。\n"
        "支持抽球机制、场次管理、配额追踪。\n"
        "Actions: dashboard, today, draw, quick_draw, redraw, edit, complete, box_list, cycle_status, help"
    ),
    parameters={
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": [
                    "dashboard", "today", "draw", "quick_draw", "redraw",
                    "edit", "complete", "box_list", "cycle_status", "help"
                ]
            },
            "session": {
                "type": "string",
                "description": "场次名: am, pm, evening, overtime",
                "enum": ["am", "pm", "evening", "overtime"]
            },
            "content": {
                "type": "string",
                "description": "编辑内容（edit 时使用）"
            },
            "block_id": {
                "type": "string",
                "description": "Block ID（complete 时使用）"
            }
        },
        "required": ["action"]
    },
    handler=todo_dealer,
    tags=["todo", "productivity", "life-system"],
    category="productivity"
)
