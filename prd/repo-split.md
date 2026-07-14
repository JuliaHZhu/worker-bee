# PRD: worker-bee 仓库拆分与角色对齐

> **目标读者**: nanobot（自主修复 Agent）
> **状态**: 待执行
> **创建**: 2026-07-04

---

## 一、问题陈述

### 1.1 worker-bee 当前目录过于臃肿

`worker-bee` 仓库（`JuliaHZhu/worker-bee`）目前包含三类职责，应该拆分成独立仓库：

| 职责 | 当前目录 | 应该去哪 |
|------|---------|---------|
| 单机 Agent 核心 | `agent/`, `tools/`, `skills/`, `cron/`, `todo_ball_machine/` | 留在 `worker-bee` |
| 多机部署工具 | `beebox/`, `beebox-deploy/` | 新建 `beebox` 仓库 |
| 消息总线 | `network/transport/` | 新建 `swarm` 仓库 |
| 设计文档 | `design_notes/` | 留在 `worker-bee` |

### 1.2 beebox 使用的 Bee 角色名已过时

`beebox/config/bees.yaml` 里定义的 Bee 角色是旧版命名，与最新的架构设计（`design_notes/07-full-agent-ecosystem.md` 中的十步流程 + 9 层模型）不一致。

**旧名（beebox 当前）→ 新名 + 对应 GitHub repo：**

| 旧 role | 新 Bee 名 | 新 repo（待创建/已有） | 备注 |
|---------|----------|---------------------|------|
| `commander` | **Centurion Bee** | `centurion-bee`（待创建） | 百夫长，监工不干活，一机盯十个 |
| `world` | **World Bee** | `world-bee`（已存在，需更新） | 真实校验 + 运维知识库 |
| `writer` | **Worker Bee**（写作型） | 合并到 `worker-bee` 作为 skill | 写作 Bee = 加载 writer-skill 的 Worker |
| `worker` | **Worker Bee** | `worker-bee`（基础设施，所有角色 import） | node: worker-bee 不是角色 repo，是核心框架 |
| `hermes` | 废弃 | — | 实验 fork，无需保留 |
| `openclaw` | 废弃 | — | 实验 fork，无需保留 |
| `newspaper` | **Newspaper Swarm** | `newspaper`（已存在，保留） | 模拟报社 demo |
| — | **Strategy Bee** | `strategy-bee`（待创建） | 二级政策层，第 1/2/9 步 |
| — | **PM Bee** | `pm-bee`（待创建） | 项目/战役管理层，第 3/4/6 步 |
| — | **Aristotle Bee** | `aristotle-bee`（待创建） | 术语管家，第 1 步专用 |
| — | **Skeleton Bee** | `skeleton-bee`（待创建） | 骨架蜂，第 2 步专用 |
| — | **Cardmaster Bee** | `cardmaster-bee`（待创建） | 战术本 + 参谋长，第 10 步 |

### 1.3 worker-bee 被错误地当作一个 Bee 角色使用

`beebox/config/bees.yaml` 第 13 行将 `worker` 角色指向 `worker-bee` 仓库。但 worker-bee 是所有 Bee 角色的**共享基础设施**（`agent/`, `tools/`, `skills/`, `cron/`），不是单独一个角色。各角色 Bee 应该在自己的 repo 中 `import worker-bee`，而不是让 worker-bee 充当一个角色。

---

## 二、目标架构

### 2.1 Repo 边界

```
┌──────────────────────────────────────────────────┐
│ worker-bee  ← 单机 Agent 核心框架                 │
│   agent/      agent loop, Deck, 工具注册          │
│   tools/      所有工具实现                        │
│   skills/     skill 加载与匹配                    │
│   cron/       定时任务                            │
│   todo_ball_machine/  任务追踪                    │
│   design_notes/  架构设计文档                     │
│                                                  │
│   ⚠️ 不包含: beebox/, beebox-deploy/, network/transport/     │
│   ⚠️ 不被 beebox 作为"角色"部署                  │
└──────────────────────────────────────────────────┘
            ↑ import by all bee repos

┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│ strategy-bee    │  │ pm-bee           │  │ centurion-bee   │
│ import wb       │  │ import wb        │  │ import wb       │
│ + strategy-skill│  │ + pm-skill       │  │ + centurion-skl │
└─────────────────┘  └──────────────────┘  └─────────────────┘

┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│ world-bee       │  │ aristotle-bee    │  │ skeleton-bee    │
│ import wb       │  │ import wb        │  │ import wb       │
│ + world-skill   │  │ + aristotle-skil │  │ + skeleton-skil │
└─────────────────┘  └──────────────────┘  └─────────────────┘

┌─────────────────┐  ┌──────────────────┐
│ cardmaster-bee  │  │ newspaper        │  ← 已存在，保留
│ import wb       │  │ (独立 demo)      │
│ + cardmaster-skl│  └──────────────────┘
└─────────────────┘

┌──────────────────────────────────────────────────┐
│ beebox  ← 多机部署工具（新 repo）                   │
│   依赖: worker-bee (import wb + install as dep)  │
│   config/bees.yaml   角色→repo 映射               │
│   inventory.yaml     服务器清单                   │
│   deploy.py          批量 SSH 部署                 │
│   update.py          批量 git pull                │
│   logs.py            日志收集                     │
│   skills.py          skill 分发                   │
│   CLI: wb beebox deploy/update/logs/sync-skills  │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ swarm  ← NATS 消息总线（新 repo）                   │
│   listener.py       NATS→mailbox 订阅进程          │
│   file_server.py    文件服务（如有）               │
│   独立于 beebox，可单独使用                        │
└──────────────────────────────────────────────────┘
```

### 2.2 依赖关系

```
beebox ──depends on──→ worker-bee (作为 Python 包)
beebox ──uses────────→ swarm (作为通信层)
各 Bee repo ──depends on──→ worker-bee (作为 Python 包)
各 Bee repo ──uses────────→ swarm (发/收消息)
```

---

## 三、具体执行任务

### Task 1: 拆分 worker-bee → 三个 repo

#### 1a. 保留在 `worker-bee`

- `agent/`
- `tools/`
- `skills/`（保留 worker-bee 内置 skill，通用 skill 在 `JuliaHZhu/skills` 独立仓库）
- `cron/`
- `todo_ball_machine/`
- `design_notes/`
- `tests/`
- `pyproject.toml`（只保留 worker-bee 核心依赖）
- `requirements.txt`
- `README.md`

#### 1b. 迁移到新 `beebox` 仓库

- `beebox/` → 保持目录结构
- `beebox-deploy/` → 删除（已被 `beebox/` 的 CLI 取代）
- 创建 `beebox/pyproject.toml`，依赖 `worker-bee`
- CLI: `wb beebox` 子命令（通过 `import worker_bee` 注册）

#### 1c. 迁移到新 `swarm` 仓库

- `network/transport/listener.py` → `network/transport/listener.py`
- `network/transport/file_server.py` → `network/transport/file_server.py`（如有）
- 创建 `network/transport/pyproject.toml`
- 独立可运行，不依赖 worker-bee 的 agent 部分

### Task 2: 更新 `beebox/config/bees.yaml`

用新 Bee 名称替换旧的：

```yaml
bees:
  - role: strategy
    repo: "https://github.com/JuliaHZhu/strategy-bee.git"
    branch: main
    description: "二级战略层（政策层）— 搜索方向 + 战役报告 + 扬弃"

  - role: pm
    repo: "https://github.com/JuliaHZhu/pm-bee.git"
    branch: main
    description: "项目/战役管理层 — 排期/拆分/监听汇总结案 + 容灾"

  - role: centurion
    repo: "https://github.com/JuliaHZhu/centurion-bee.git"
    branch: main
    description: "百夫长 — 监工不干活，一机盯十个 Worker"

  - role: world
    repo: "https://github.com/JuliaHZhu/world-bee.git"
    branch: main
    description: "真实校验 + 运维知识库"

  - role: aristotle
    repo: "https://github.com/JuliaHZhu/aristotle-bee.git"
    branch: main
    description: "术语管家 — 三层解析器（本体/修辞阐释/信念承重墙）"

  - role: skeleton
    repo: "https://github.com/JuliaHZhu/skeleton-bee.git"
    branch: main
    description: "骨架蜂 — 规约到不能规约，选牌型 + 定结构"

  - role: cardmaster
    repo: "https://github.com/JuliaHZhu/cardmaster-bee.git"
    branch: main
    description: "战术本 + 参谋长 — 回合制选动作 + 博弈复盘"

  - role: newspaper
    repo: "https://github.com/JuliaHZhu/newspaper.git"
    branch: main
    description: "模拟报社工作室 swarm demo"

# 不再包含: commander, writer, hermes, openclaw (已废弃)
# worker-bee 不再作为角色出现，而是所有 Bee 的基础依赖

skills_repo:
  url: "https://github.com/JuliaHZhu/skills.git"
  branch: main
  local_path: "skills"
```

### Task 3: 更新 `beebox/inventory.yaml`

用新角色名替换旧的：

```yaml
servers:
  - host: "10.0.1.10"
    name: "beebox-strategy"
    roles:
      - strategy
    nats_server: true

  - host: "10.0.1.11"
    name: "beebox-pm"
    roles:
      - pm
    nats_server: false

  - host: "10.0.1.12"
    name: "beebox-centurion-1"
    roles:
      - centurion
    nats_server: true

  - host: "10.0.1.13"
    name: "beebox-centurion-2"
    roles:
      - centurion
      - world
    nats_server: false

  - host: "10.0.1.14"
    name: "beebox-creative"
    roles:
      - aristotle
      - skeleton
      - cardmaster
    nats_server: false

  - host: "10.0.1.15"
    name: "beebox-newspaper"
    roles:
      - newspaper
    nats_server: false
```

### Task 4: 创建各 Bee 角色的独立 repo 骨架

每个新 Bee repo 最小结构：

```
strategy-bee/          # 以 strategy-bee 为例
├── pyproject.toml     # depends: worker-bee
├── requirements.txt
├── bee.py             # 主入口: from worker_bee.agent import AIAgent
├── skills/            # 该角色专属 skill（如 strategy-bee 的 skill）
│   └── strategy.md
├── config.yaml        # 角色配置
└── README.md
```

所有 Bee repo 共享模式：`import worker_bee` + 自己的 skill + 自己的 config。

### Task 5: 废弃旧 repo

以下 repo 标记为 archived/deprecated：

| repo | 原因 |
|------|------|
| `commander-bee` | 已重命名为 Centurion Bee |
| `writer-bee` | 已合并为 Worker Bee 的写作 skill |
| `hermes-lite` | 实验 fork，不再使用 |
| `openclaw-lite` | 实验 fork，不再使用 |

---

## 四、不变项

以下**不需要改**：

- `worker-bee/agent/` — 核心 agent loop 不变
- `worker-bee/tools/` — 工具实现不变
- `worker-bee/skills/` — 内置 skill 不变
- `worker-bee/cron/` — 定时任务不变
- `worker-bee/design_notes/` — 设计文档不变
- `JuliaHZhu/skills` — 独立 skill 仓库不变
- `JuliaHZhu/newspaper` — demo 项目不变
- `beebox/` 的四个命令（deploy/update/logs/sync-skills）逻辑不变，只更新角色名

---

## 五、验收标准

- [ ] `worker-bee` repo 不再包含 `beebox/`、`beebox-deploy/`、`network/transport/` 目录
- [ ] 新 `beebox` repo 包含完整的 deploy/update/logs/sync-skills 功能
- [ ] 新 `swarm` repo 包含 listener + file_server
- [ ] `beebox/config/bees.yaml` 使用新 Bee 名称
- [ ] `beebox/inventory.yaml` 使用新 Bee 名称
- [ ] `beebox` CLI (`wb beebox deploy`) 在新 repo 中可用
- [ ] 每个新 Bee repo 能独立 `pip install` + 启动
- [ ] 旧 repo（commander-bee, writer-bee, hermes-lite, openclaw-lite）标记为 archived
- [ ] worker-bee 的所有测试仍通过（不因目录移动而破坏 import）
