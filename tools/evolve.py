"""
evolve — worker-bee 自我改装工具

从种子形态改装为特定角色 Bee。
调用时机：种子 skill 建议改装 + 人确认后；或人直接发 NATS evolve 指令。

工具注册名: evolve
"""

import os
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

WB_DIR = Path.home() / ".worker-bee"
CONFIG_PATH = Path("config.yaml")  # 相对于工作目录
SKILLS_DIR = Path("skills")
SKILLS_REPO_URL = "https://github.com/JuliaHZhu/skills.git"
SKILLS_LOCAL = WB_DIR / "skills-repo"

VALID_ROLES = [
    "strategy", "pm", "centurion", "world",
    "aristotle", "skeleton", "cardmaster"
]

ROLE_SKILL_MAP = {
    "strategy":   "strategy-bee.md",
    "pm":         "pm-bee.md",
    "centurion":  "centurion-bee.md",
    "world":      "world-bee.md",
    "aristotle":  "aristotle-bee.md",
    "skeleton":   "skeleton-bee.md",
    "cardmaster": "cardmaster-bee.md",
}

ROLE_SOUL = {
    "strategy": """你是 Strategy Bee。二级战略层（政策层）。
你的工作是搜索全地形、锁定有意义的目标、选牌型、出战役报告、讨论战略扬弃。
你不执行，不排期，不监工。你只在项目入口（第 1-2 步）和出口（第 9 步）出现。""",

    "pm": """你是 PM Bee。项目/战役管理层。
你的工作是排期协调（第 3 步）、拆分配兵（第 4 步）、后台监听汇总结案（第 6 步）。
你只记录不行动，100% 时通知人，不催促。交接即退场。""",

    "centurion": """你是 Centurion Bee。百夫长。
你的工作是监工——派发任务、监控进度、回收结果、处理补丁（第 5/7 步）。
一机盯十个 Worker。你不写菜谱（PM 的事），不执行任务（Worker 的事），不校验质量（World 的事）。""",

    "world": """你是 World Bee。生产一线容错 + 数据自动化价值复用。
你的工作是事实校验、拼凑证据链（第 5/7 步）、复盘归档 + skill 运维提醒（第 8 步）。
你不做战略决策，只提供验证过的数据。""",

    "aristotle": """你是 Aristotle Bee。术语管家。
你的工作是质疑每个名词——查词典、检测漂移、追问未定义词、接纳新造词。
你只在战略探索阶段（第 1 步）出场，由人 + Strategy Bee 召唤。""",

    "skeleton": """你是 Skeleton Bee。骨架蜂。
你的工作是规约到不能规约——把模糊目标拆成可执行的结构骨架。
你只在选牌型阶段（第 2 步）出场，由人 + Strategy Bee 召唤。""",

    "cardmaster": """你是 Cardmaster Bee。战术本 + 参谋长。
你的工作是翻战术本选动作、写标的物规格书、博弈复盘（第 10 步）。
你不决策，只做参谋——分析对面什么意思、建议怎么打更好。""",
}


def evolve(role: str) -> str:
    """
    将当前 Bee 从种子改装为指定角色。

    Args:
        role: 目标角色名。可选: strategy, pm, centurion, world,
              aristotle, skeleton, cardmaster

    Returns:
        改装结果描述
    """
    role = role.lower().strip()

    # 1. 校验
    if role not in VALID_ROLES:
        return f"错误: 未知角色 '{role}'。可选: {', '.join(VALID_ROLES)}"

    config = _load_config()
    if config.get("role", "seed") != "seed":
        return (
            f"错误: 当前角色是 '{config['role']}'，不是 seed。"
            f"已经改装过的 Bee 不能再次 evolve。"
        )

    # 2. 拉取角色 skill
    skill_file = ROLE_SKILL_MAP[role]
    os.makedirs(SKILLS_DIR, exist_ok=True)

    if not (SKILLS_LOCAL / ".git").exists():
        _clone_skills_repo()
    else:
        subprocess.run(
            ["git", "-C", str(SKILLS_LOCAL), "pull", "origin", "main"],
            capture_output=True,
        )

    src = SKILLS_LOCAL / skill_file
    if not src.exists():
        return (
            f"错误: skill 文件 '{skill_file}' 在 skills 仓库中不存在。"
            f"请确认 JuliaHZhu/skills 中包含此文件。"
        )

    dst = SKILLS_DIR / skill_file
    shutil.copy2(src, dst)

    # 3. 更新 config.yaml
    config["role"] = role
    if "evolution" not in config:
        config["evolution"] = {}
    config["evolution"]["stage"] = "evolved"
    config["evolution"]["evolved_at"] = datetime.now(timezone.utc).isoformat()
    config["evolution"]["evolved_to"] = role
    _save_config(config)

    # 4. 写入 soul.md（角色人格）
    _write_soul(role)

    # 5. Git commit + push
    git_result = _git_commit_and_push(role)

    return (
        f"改装完成: seed → {role}\n"
        f"skill 文件: skills/{skill_file}\n"
        f"config: role={role}, stage=evolved\n"
        f"soul.md: 已写入 {role} Bee 人格\n"
        f"git: {git_result}"
    )


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {"role": "seed", "evolution": {}}


def _save_config(config: dict):
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def _clone_skills_repo():
    subprocess.run(
        ["git", "clone", "--depth", "1", SKILLS_REPO_URL, str(SKILLS_LOCAL)],
        check=True,
    )


def _write_soul(role: str):
    soul_path = WB_DIR / "soul.md"
    content = ROLE_SOUL.get(role, f"# {role} Bee\n\n改装自 worker-bee 种子。")
    soul_path.write_text(content, encoding="utf-8")


def _git_commit_and_push(role: str) -> str:
    """将改装变更提交到 git 并推送。返回结果描述。"""
    workspace = Path.cwd()
    if not (workspace / ".git").exists():
        return "跳过（无 git repo）"

    results = []
    r = subprocess.run(["git", "add", "-A"], cwd=workspace, capture_output=True, text=True)
    if r.returncode != 0:
        return f"git add 失败: {r.stderr.strip()}"

    r = subprocess.run(
        ["git", "commit", "-m", f"evolve: seed -> {role}"],
        cwd=workspace, capture_output=True, text=True,
    )
    if r.returncode == 0:
        results.append("committed")
    else:
        results.append(f"commit: {r.stderr.strip()[:60]}")

    r = subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=workspace, capture_output=True, text=True,
    )
    if r.returncode == 0:
        results.append("pushed")
    else:
        results.append(f"push: {r.stderr.strip()[:60]}")

    return ", ".join(results)


# ── Registry ────────────────────────────────────────────────────────
try:
    from agent.registry import registry

    registry.register(
        name="evolve",
        description="将当前 Bee 从种子形态改装为指定角色。可选: strategy, pm, centurion, world, aristotle, skeleton, cardmaster。只能调用一次（role=seed 时）。",
        parameters={
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "目标角色名",
                    "enum": ["strategy", "pm", "centurion", "world", "aristotle", "skeleton", "cardmaster"],
                }
            },
            "required": ["role"],
        },
        handler=evolve,
        tags=["evolve", "bee"],
        category="bee",
    )
except Exception:
    pass
