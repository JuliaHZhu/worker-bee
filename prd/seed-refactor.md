# PRD: worker-bee 种子化改造

> **版本**: v1.0  
> **状态**: 待评审  
> **目标**: 将 worker-bee 从"带角色预设的 agent 框架"重构为"不预设角色的全能种子"  
> **读者**: nanobot（自主修复 Agent）

---

## 目录

1. [问题陈述](#一问题陈述)
2. [目标架构](#二目标架构)
3. [种子设计](#三种子设计)
4. [自我改装机制](#四自我改装机制)
5. [种子 skill 详细设计](#五种子-skill-详细设计)
6. [evolve 工具详细设计](#六evolve-工具详细设计)
7. [beebox 重构](#七beebox-重构)
8. [仓库拆分计划](#八仓库拆分计划)
9. [实现任务列表](#九实现任务列表)
10. [验收标准](#十验收标准)
11. [风险与缓解](#十一风险与缓解)

---

## 一、问题陈述

### 1.1 当前问题

worker-bee 目前是一个"预设角色"的仓库：

- `beebox/config/bees.yaml` 预先定义了 8 个角色，每个角色指向一个独立 repo
- `beebox/inventory.yaml` 预先分配了每台服务器的角色
- 部署时，beebox 根据预设角色克隆对应的 repo 到对应服务器

**这不符合实际演化路径。** 实际路径应该是：

1. 8 台裸机全部装同一个 worker-bee（种子）
2. 各自 `gh repo create` 分叉，从此刻起独立演化
3. 在十步流程中，每台机根据自己实际参与的工作，逐渐改装成特定角色
4. 改装完成后，角色才真正成立

### 1.2 为什么预设角色是错的

- 角色是在实践中"长出来"的，不是预先分配的
- 一台机可能在流程初期做 strategy 的工作，后期做 centurion 的工作
- 改装是渐进过程——不是"装好就是 Centurion"，而是"做了足够多次派发监工后才成为 Centurion"
- 预设角色限制了灵活性和自组织能力

---

## 二、目标架构

### 2.1 种子 → 角色演化流程

```
                     ┌─────────────────┐
第 1 步: 装机         │  worker-bee     │  ← 同一个 repo
                     │  (种子)          │     git clone 到 8 台机
                     │  role: seed      │
                     └─────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
第 2 步: 分叉  bee-01       bee-02       bee-03  ... bee-08
              gh repo      gh repo      gh repo
              create       create       create
              各自独立 repo，各自独立演化
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
第 3 步: 跑流程  参与第1步    参与第5步    参与第5步
              战略探索      自动执行      自动执行
              (聊天)       (被派发task)  (被要求校验)
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
第 4 步: 发现角色  连续做战略   连续做执行   连续做校验
              讨论         被监工        出报告
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
第 5 步: 改装    evolve(     evolve(      evolve(
              "strategy")  "centurion")  "world")
              写skill      写skill      写skill
              改config     改config     改config
              git push     git push     git push
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
第 6 步: 持续演化  strategy-bee centurion-bee world-bee
              (独立repo)   (独立repo)   (独立repo)
              持续改skill  持续改skill  持续改skill
```

### 2.2 仓库关系

```
worker-bee (种子)         ← 所有 Bee 的起点
    │
    ├── bee-01 分叉 → strategy-bee (独立 repo, 改装后)
    ├── bee-02 分叉 → pm-bee        (独立 repo, 改装后)
    ├── bee-03 分叉 → centurion-bee (独立 repo, 改装后)
    ├── bee-04 分叉 → centurion-bee (独立 repo, 改装后)
    ├── bee-05 分叉 → world-bee     (独立 repo, 改装后)
    ├── bee-06 分叉 → aristotle-bee (独立 repo, 改装后)
    ├── bee-07 分叉 → skeleton-bee  (独立 repo, 改装后)
    └── bee-08 分叉 → cardmaster-bee(独立 repo, 改装后)

beebox (运维工具)         ← 独立 repo，只管部署/更新/日志
JuliaHZhu/skills (技能库) ← 独立 repo，各 Bee 拉取 skill
```

### 2.3 关键原则

| 原则 | 说明 |
|------|------|
| **种子不预设角色** | worker-bee 的默认 `role: seed`，不指定这台机是什么 Bee |
| **角色是跑出来的** | 只有当一台机持续做某类工作后，才调用 evolve 改装 |
| **改装不可逆** | 一旦 evolve 完成，机器就有了明确的角色，不再回到 seed |
| **各 Bee 独立 repo** | 分叉后各自独立：自己的 skill、自己的 tool、自己的 git history |
| **beebox 不管角色** | beebox 只负责部署种子、更新代码、收集日志，不预设也不读取角色信息 |

---

## 三、种子设计

### 3.1 种子包含什么

种子 = 任何 Bee 角色都需要的**最小通用能力集合**。

| 模块 | 路径 | 作用 | 每个角色都需要？ |
|------|------|------|:---:|
| Agent 核心 | `agent/` | loop, Deck, 工具注册, skill 加载, 协议适配 | ✅ |
| 全工具集 | `tools/` | file, terminal, web, subagent, cron, swarm, deck_manage, job_probe, skill_audition, todo_ball_machine, send_message, lark | ✅ |
| Skill 框架 | `skills/` | 加载、trigger 匹配、context 注入 | ✅ |
| 种子 skill | `skills/seed.md` | **新增**：帮 Bee 发现自己该演化成什么角色 | ✅ |
| 改装工具 | `tools/evolve.py` | **新增**：写 skill、改 config、git push | ✅ |
| 定时调度 | `cron/` | 定时任务 | ✅ |
| 消息通信 | `network/transport/` | NATS listener, mailbox 收发 | ✅ |
| 任务追踪 | `todo_ball_machine/` | job 管理 | ✅ |
| 测试 | `tests/` | 单元测试 | ✅ |

### 3.2 种子不包含什么

| 移出 | 原因 | 去向 |
|------|------|------|
| `beebox/` | 部署运维工具，不是 agent 核心 | 独立 `beebox` repo |
| `beebox-deploy/` | 已被 `beebox/` 取代 | 删除 |
| `design_notes/` | 架构文档，不是运行时代码 | wiki 或独立 docs repo |
| `prd/` | 项目管理文档 | wiki |
| `DESIGN.md` | 设计演进记录 | 合并到 design_notes/ |
| `DEVLOG.md` | 开发日志 | wiki |
| `templates/` | 模板文件 | wiki |
| `state.db` | 运行时 SQLite 文件 | `.gitignore`，不提交 |

### 3.3 种子 config.yaml

```yaml
# worker-bee 种子配置
# 每台机 clone 后自行修改

role: seed           # 当前角色：seed | strategy | pm | centurion | world | aristotle | skeleton | cardmaster
bee_id: auto         # 自动生成 UUID，或手动指定（如 "centurion-east-1"）
nats_url: "nats://localhost:4222"

# 改装状态
evolution:
  stage: seed              # seed | observing | evolving | evolved
  tasks_completed: 0       # 完成的任务计数（用于自动发现角色）
  task_types: {}           # 任务类型统计（如 {"dispatch": 12, "verify": 3}）
  evolve_threshold: 10     # 连续做同一类任务超过此次数 → 建议演化
  evolved_at: null         # 改装完成时间
  evolved_to: null         # 改装成的角色

# skill 仓库
skills_repo: "https://github.com/JuliaHZhu/skills.git"
skills_branch: main
```

### 3.4 种子目录结构

```
worker-bee/
├── agent/              # Agent 核心
│   ├── agent.py
│   ├── cli.py
│   ├── deck.py
│   ├── loop.py
│   ├── memory.py
│   ├── protocols.py
│   ├── registry.py
│   ├── safety.py
│   ├── skills.py
│   └── workspace.py
├── tools/              # 全工具集
│   ├── __init__.py
│   ├── cronjob.py
│   ├── deck_manage.py
│   ├── evolve.py       # ★ 新增：自我改装工具
│   ├── file.py
│   ├── job_probe.py
│   ├── lark.py
│   ├── send_message.py
│   ├── skill_audition.py
│   ├── subagent.py
│   ├── swarm.py
│   ├── terminal.py
│   ├── todo_ball_machine.py
│   └── web.py
├── skills/             # Skill 文件
│   └── seed.md         # ★ 新增：种子 skill
├── network/transport/              # NATS 通信
│   ├── listener.py
│   └── file_server.py
├── cron/               # 定时调度
│   ├── __init__.py
│   ├── jobs.py
│   └── scheduler.py
├── todo_ball_machine/  # 任务追踪
│   ├── engine.py
│   └── morning_brief.py
├── tests/
├── config.yaml         # ★ 修改：加 role + evolution 字段
├── pyproject.toml
├── requirements.txt
├── .gitignore          # ★ 修改：加 state.db, config.local.yaml
└── README.md
```

---

## 四、自我改装机制

### 4.1 改装触发条件（两种方式）

**方式一：人工指定（显式改装）**

```
人 → NATS 消息: {"type": "evolve", "target": "bee-03", "role": "centurion"}
或
人直接对话: "你现在是 Centurion Bee"
```

**方式二：自动发现（隐式改装）**

种子 skill 持续追踪自己执行的任务类型。当同一类任务超过 `evolve_threshold`（默认 10 次），自动触发建议：

```
[seed skill] 检测到:
  - dispatch 类任务: 12 次
  - verify 类任务: 2 次
  - research 类任务: 1 次

→ 建议演化: centurion (你 80% 的工作是派发和监工)
→ 询问人是否确认
→ 人确认 → evolve("centurion")
```

### 4.2 任务类型自动分类

种子 skill 通过分析自己接收到的 NATS 消息类型 + 被调用的工具组合，自动分类：

| 任务模式 | 匹配规则 | 建议角色 |
|---------|---------|---------|
| 收到大量战略讨论 | 对话中包含"方向""目标""要不要做" + 调用 aristotle dict | Strategy Bee |
| 收到排期/拆分指令 | 调用 plan-decompose, schedule-optimize | PM Bee |
| 收到 task-dispatch 指令 | 调用 task-dispatch, worker-monitor, timeout-handler | Centurion Bee |
| 被派发执行任务 | 接收 NATS `task.new` 消息，调用 file/terminal/web | Worker Bee |
| 收到校验请求 | 调用 fact-check, evidence-chain | World Bee |
| 对话中频繁做术语定义 | 调用 dict-query, term-drift-detection | Aristotle Bee |
| 被要求做结构设计 | 调用 structure-reduce, card-type-select | Skeleton Bee |
| 被要求做博弈复盘 | 调用 tactical-playbook, adversarial-review | Cardmaster Bee |

### 4.3 改装过程

```
evolve("centurion") 执行流程:

1. 预检查
   - 确认 config.yaml 中 role == "seed"（只有种子能改装）
   - 确认目标角色 skill 文件存在于 skills 仓库

2. 拉取角色 skill
   - git clone JuliaHZhu/skills（如尚未 clone）
   - cp skills/centurion.md → ~/.worker-bee/skills/centurion.md

3. 更新配置
   - config.yaml: role: "centurion"
   - config.yaml: evolution.stage: "evolved"
   - config.yaml: evolution.evolved_at: <timestamp>
   - config.yaml: evolution.evolved_to: "centurion"

4. 更新身份
   - ~/.worker-bee/soul.md: 写入 Centurion 角色人格
   - ~/.worker-bee/agent.md: 更新角色描述

5. 提交改装
   - git add -A
   - git commit -m "evolve: seed → centurion"
   - git push origin main

6. 重启生效
   - 下次启动时，agent 读取 config.yaml → role: centurion
   - 加载 skills/centurion.md 作为主 skill
```

### 4.4 改装后行为

改装完成后，Bee 不再加载 seed.md，改为加载角色 skill。但保留种子时期的全部工具能力——角色 skill 通过 Deck 机制限制工具范围，而非删除工具。

```
seed 时期:        Deck = seed.md 声明的工具（全工具集的子集）
centurion 时期:   Deck = centurion.md 声明的工具（更窄的子集）
                  + 手动添加的 task-dispatch/worker-monitor 等
```

---

## 五、种子 skill 详细设计

### 5.1 skills/seed.md

```markdown
---
name: seed
description: >
  种子 skill — worker-bee 的默认形态。帮助 Bee 发现自己该演化成什么角色。
  追踪任务类型，累积到阈值后建议改装。听到明确的角色指派后立即改装。
trigger: >
  启动时自动加载。当 role=seed 时激活。
  不匹配用户输入——这是系统级 skill，由 agent 在 role=seed 时强制加载。
tools:
  - fs_read_file
  - fs_write_file
  - fs_search_files
  - sys_terminal
  - send_message
  - evolve
---

# 种子 skill

你是 worker-bee 的种子形态。你还不知道自己会成为什么角色。

## 核心行为

### 1. 每次任务后记录

每完成一个任务（无论是人直接给的还是 NATS 收到的），在 `config.yaml` 的 `evolution.task_types` 中 +1：

```yaml
evolution:
  task_types:
    dispatch: 5
    verify: 2
    research: 1
    strategy_discuss: 3
```

任务类型分类规则：
- 你被要求派发任务给其他 Bee → `dispatch`
- 你被要求校验数据/产出 → `verify`
- 你被要求搜索/调研 → `research`
- 你被要求讨论方向/目标 → `strategy_discuss`
- 你被要求拆任务/排期 → `schedule`
- 你被要求定义术语 → `define_term`
- 你被要求设计结构/骨架 → `structure`
- 你被要求做博弈复盘 → `debrief`

### 2. 阈值触发

当某个类型的计数超过 `evolve_threshold`（默认 10 次），自动发出建议：

> "我已经执行了 {count} 次 {task_type} 类型的任务。建议演化为 {suggested_role}。是否确认？"

对应的角色映射（见第五节任务类型分类表）。

### 3. 显式改装

当人通过 NATS 或直接对话说："你是 Centurion Bee" / "你现在是 Strategy Bee" / 等，**立即调用 `evolve(role)` 工具**，不等阈值。人对角色的判断优先于自动发现。

### 4. 不确定时继续观察

如果 task_types 分布均匀（没有任何类型超过阈值的 50%），不触发建议。继续观察。

### 5. 改写 config.yaml 的方法

使用 `sys_terminal` 工具调用 Python 修改 YAML：

```bash
python3 -c "
import yaml
with open('config.yaml') as f:
    cfg = yaml.safe_load(f)
cfg['evolution']['task_types']['dispatch'] = cfg['evolution']['task_types'].get('dispatch', 0) + 1
with open('config.yaml', 'w') as f:
    yaml.dump(cfg, f)
"
```
```

---

## 六、evolve 工具详细设计

### 6.1 tools/evolve.py

```python
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
CONFIG_PATH = WB_DIR / "config.yaml"
SKILLS_DIR = WB_DIR / "skills"
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
        return f"错误: 当前角色是 '{config['role']}'，不是 seed。已经改装过的 Bee 不能再次改装。"

    # 2. 拉取角色 skill
    skill_file = ROLE_SKILL_MAP[role]
    os.makedirs(SKILLS_DIR, exist_ok=True)

    if not (SKILLS_LOCAL / ".git").exists():
        _clone_skills_repo()

    # git pull 最新
    subprocess.run(
        ["git", "-C", str(SKILLS_LOCAL), "pull", "origin", "main"],
        capture_output=True
    )

    src = SKILLS_LOCAL / skill_file
    if not src.exists():
        return f"错误: skill 文件 '{skill_file}' 在 skills 仓库中不存在"

    dst = SKILLS_DIR / skill_file
    shutil.copy2(src, dst)

    # 3. 更新 config.yaml
    config["role"] = role
    config["evolution"]["stage"] = "evolved"
    config["evolution"]["evolved_at"] = datetime.now(timezone.utc).isoformat()
    config["evolution"]["evolved_to"] = role
    _save_config(config)

    # 4. 生成/更新 soul.md（角色人格）
    _write_soul(role)

    # 5. 提交改装
    _git_commit_and_push(role)

    return f"改装完成: seed → {role}\nskill: {skill_file}\nconfig: role={role}\n"

def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {"role": "seed", "evolution": {}}

def _save_config(config: dict):
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

def _clone_skills_repo():
    subprocess.run(
        ["git", "clone", "--depth", "1", SKILLS_REPO_URL, str(SKILLS_LOCAL)],
        check=True
    )

def _write_soul(role: str):
    soul = {
        "strategy": """你是 Strategy Bee。二级战略层（政策层）。
你的工作是搜索全地形、锁定有意义的目标、选牌型、出战役报告、讨论战略扬弃。
你不执行，不排期，不监工。""",
        "pm": """你是 PM Bee。项目/战役管理层。
你的工作是排期协调、拆分配兵、后台监听汇总结案。
你只记录不行动，100% 时通知人，不催促。""",
        "centurion": """你是 Centurion Bee。百夫长。
你的工作是监工——派发任务、监控进度、回收结果、处理补丁。一机盯十个 Worker。
你不写菜谱（那是 PM 的事），不执行任务（那是 Worker 的事），不校验质量（那是 World 的事）。""",
        "world": """你是 World Bee。生产一线容错 + 数据自动化价值复用。
你的工作是事实校验、拼凑证据链、复盘归档、skill 运维提醒。
你不做战略决策，只提供验证过的数据。""",
        "aristotle": """你是 Aristotle Bee。术语管家。
你的工作是质疑每个名词——查词典、检测漂移、追问未定义词、接纳新造词。
你只在战略探索阶段（第 1 步）出场。""",
        "skeleton": """你是 Skeleton Bee。骨架蜂。
你的工作是规约到不能规约——把模糊目标拆成可执行的结构骨架。
你只在选牌型阶段（第 2 步）出场。""",
        "cardmaster": """你是 Cardmaster Bee。战术本 + 参谋长。
你的工作是翻战术本选动作、写标的物规格书、博弈复盘。
你不决策，只做参谋。""",
    }

    soul_path = WB_DIR / "soul.md"
    content = soul.get(role, f"# {role} Bee\n\n改装自 worker-bee 种子。")
    soul_path.write_text(content, encoding="utf-8")

def _git_commit_and_push(role: str):
    """将改装变更提交到 git 并推送。"""
    import subprocess
    workspace = Path.cwd()
    if not (workspace / ".git").exists():
        return  # 没有 git repo，跳过

    subprocess.run(["git", "add", "-A"], cwd=workspace)
    subprocess.run(
        ["git", "commit", "-m", f"evolve: seed → {role}"],
        cwd=workspace
    )
    subprocess.run(["git", "push", "origin", "main"], cwd=workspace)
```

### 6.2 工具注册（在 tools/__init__.py 或 registry 中）

```python
from tools.evolve import evolve

registry.register(
    name="evolve",
    description="将当前 Bee 从种子形态改装为指定角色。只能调用一次。",
    parameters={
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "enum": ["strategy", "pm", "centurion", "world", "aristotle", "skeleton", "cardmaster"],
                "description": "目标角色名"
            }
        },
        "required": ["role"]
    },
    handler=evolve,
)
```

---

## 七、beebox 重构

### 7.1 新 beebox 仓库结构

```
beebox/                     ← 独立 repo（从 worker-bee 移出）
├── deploy.py               ← 批量 SSH 克隆 worker-bee 种子到各节点
├── update.py               ← 批量 git pull + 依赖重装
├── logs.py                 ← 日志收集（git log + pipeline log + NATS log）
├── skills.py               ← 从 JuliaHZhu/skills 同步到各节点
├── config/
│   └── inventory.yaml      ← 服务器清单（不预设角色）
├── pyproject.toml          ← 依赖 worker-bee
└── README.md
```

### 7.2 新的 inventory.yaml

```yaml
# beebox 服务器清单
# 种子模式：不预设角色。每台机的角色由自己演化决定。

ssh:
  user: "ubuntu"
  key_file: "~/.ssh/id_rsa"
  port: 22

# 8 台机——只记录 IP 和名字，不管角色
servers:
  - host: "10.0.1.10"
    name: "bee-01"
  - host: "10.0.1.11"
    name: "bee-02"
  - host: "10.0.1.12"
    name: "bee-03"
  - host: "10.0.1.13"
    name: "bee-04"
  - host: "10.0.1.14"
    name: "bee-05"
  - host: "10.0.1.15"
    name: "bee-06"
  - host: "10.0.1.16"
    name: "bee-07"
  - host: "10.0.1.17"
    name: "bee-08"

# NATS 集群节点
nats_nodes:
  - host: "10.0.1.10"
    name: "nats-1"
  - host: "10.0.1.11"
    name: "nats-2"
  - host: "10.0.1.12"
    name: "nats-3"

# 种子仓库——所有机器装同一个
seed_repo: "https://github.com/JuliaHZhu/worker-bee.git"
seed_branch: main

skills_repo:
  url: "https://github.com/JuliaHZhu/skills.git"
  branch: main
```

### 7.3 deploy.py 改动

原来：根据 `bees.yaml` 的角色 → repo 映射，每台机部署不同 repo。

改为：所有机器统一部署 `seed_repo`。

```python
def deploy_all(inventory, seed_repo, seed_branch):
    for server in inventory["servers"]:
        host = server["host"]
        name = server["name"]
        # 所有机器克隆同一个种子 repo
        cmd = f"git clone --branch {seed_branch} {seed_repo} ~/worker-bee"
        ssh_cmd(host, user, key_file, port, cmd)
        print(f"  [DEPLOY] {name} ({host}): worker-bee seed")
```

### 7.4 删除 bees.yaml

不再需要 `beebox/config/bees.yaml`。角色映射由每台机自己的 `config.yaml` 维护。

---

## 八、仓库拆分计划

### 8.1 worker-bee 清理

```
保留:
  agent/  tools/  skills/  network/transport/  cron/  todo_ball_machine/  tests/
  config.yaml  pyproject.toml  requirements.txt  README.md  .gitignore

移出 → 新建 beebox repo:
  beebox/  beebox-deploy/

移出 → wiki 或 docs repo:
  design_notes/  prd/  DESIGN.md  DEVLOG.md  templates/

.gitignore 新增:
  state.db
  config.local.yaml
```

### 8.2 各 Bee 独立 repo（种子分叉后自然产生）

不在本次改造范围内。由种子被克隆到 8 台机后，每台机自行 `gh repo create` 产生。

---

## 九、实现任务列表

### Phase 1: 种子核心（P0）

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 1.1 | 修改 config.yaml | `config.yaml` | 加 `role: seed` + `evolution` 字段 |
| 1.2 | 新增 seed.md | `skills/seed.md` | 种子 skill：任务类型追踪 + 阈值触发 + 显式改装 |
| 1.3 | 新增 evolve.py | `tools/evolve.py` | 自我改装工具：拉 skill、改 config、git commit push |
| 1.4 | 注册 evolve 工具 | `tools/__init__.py` 或 `agent/registry.py` | 让 agent 可以调用 evolve |
| 1.5 | agent 启动时读取 role | `agent/main.py` 或 `agent/agent.py` | role=seed 时强制加载 seed.md；role=其他时加载对应角色 skill |

### Phase 2: 仓库清理（P0）

| # | 任务 | 说明 |
|---|------|------|
| 2.1 | 移出 beebox/ | 创建独立 `JuliaHZhu/beebox` repo，复制 beebox/ 目录 |
| 2.2 | 删除 beebox-deploy/ | 已被 beebox/ 取代 |
| 2.3 | 移出 design_notes/ | 移到 wiki 或独立 docs repo |
| 2.4 | 移出 prd/ | 移到 wiki |
| 2.5 | 移出 DESIGN.md, DEVLOG.md, templates/ | 移到 wiki |
| 2.6 | .gitignore 加 state.db, config.local.yaml | 防止运行时文件进 repo |

### Phase 3: beebox 重构（P1）

| # | 任务 | 说明 |
|---|------|------|
| 3.1 | 简化 inventory.yaml | 去掉角色预设，只记录 IP |
| 3.2 | 删除 bees.yaml | 不再需要角色 → repo 映射 |
| 3.3 | 修改 deploy.py | 统一部署 seed_repo |
| 3.4 | 修改 update.py/logs.py/skills.py | 不依赖 bees.yaml 的角色列表 |

---

## 十、验收标准

- [ ] worker-bee 默认 `role: seed`，启动后加载 seed.md
- [ ] seed.md 能追踪任务类型并在 config.yaml 中累加计数
- [ ] 当某类型超过阈值，seed.md 发出演化建议
- [ ] 人说"你是 Centurion Bee"时，agent 立即调用 `evolve("centurion")`
- [ ] `evolve("centurion")` 完成后：skill 已复制、config 已更新、soul.md 已写入、git 已 push
- [ ] 重启后 agent 读取 `role: centurion`，不再加载 seed.md
- [ ] worker-bee repo 不再包含 `beebox/`, `beebox-deploy/`, `design_notes/`, `prd/`
- [ ] `JuliaHZhu/beebox` repo 存在且可用，inventory.yaml 不预设角色
- [ ] 种子可以 `pip install` 后直接 `worker-bee` 启动
- [ ] 现有测试全部通过（不因目录移动而破坏 import）

---

## 十一、风险与缓解

| 风险 | 缓解 |
|------|------|
| evolve 工具被意外调用（改装不可逆） | evolve 工具只在 role=seed 时可调用，改装后失效 |
| 自动发现错误角色（统计偏差） | 阈值默认 10 次可配置；必须人确认后才执行 evolve |
| beebox 移出后 import 路径断裂 | beebox 独立 repo 通过 `pip install worker-bee` 依赖核心，不 import 内部模块 |
| 种子 skill 本身不能出错（否则无法启动） | seed.md 是纯文本 skill，不依赖任何自定义 tool，最大程度减少故障面 |
| 多台机同时 evolve 到同一角色 | 预期行为——多台 Centurion 是正常的（一个 PM 管多个 Centurion） |
