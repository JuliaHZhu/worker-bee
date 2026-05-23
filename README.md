# Hermes Lite

> 借鉴理念，改造形态。取 Hermes Agent 的 skill 概念，加一层 Deck。

---

## 我们与 Hermes Agent 的关系

Hermes Agent 是完整的 AI 工程框架，功能全面。我们在其设计理念上做了精简改造：

| | Hermes Agent | Hermes Lite |
|---|---|---|
| Skill 定义 | 目录树 + `SKILL.md` | 单文件 + YAML frontmatter |
| 激活方式 | 子 agent 索引匹配 | 声明式 `trigger` |
| 工具边界 | 全部可见 | **Deck 裁剪**（仅加载相关工具） |
| 架构目标 | 功能完整 | **精准调用** |

核心区别：**我们抽了一层 Deck 出来。**

---

## Deck：运行时工具边界

### 为什么要 Deck？

Registry 里注册了所有工具，如果全部丢给 LLM，它会混乱——用 `fs_write_file` 改 todo、用 `sys_terminal` 查天气。我们需要一种机制：**每次任务只暴露相关的工具。**

Deck 就是这个机制。

### 概念

- **Registry** = 工具仓库（全部工具常驻内存，数量随注册动态变化）
- **Skill** = 契约：声明 trigger（何时激活）+ tools（需要什么工具）
- **Deck** = 运行时堆栈：装填 → 抽取 → halt

### 工作流程

```
用户输入
    │
    ▼
Skill Manager 匹配 triggers
    │
    ▼
收集匹配 skills 声明的 tools
    │
    ▼
Deck 装填：skill tools + 冗余卡槽（+3）
    │
    ▼
LLM 只能从 Deck 里抽工具 → 不会越界
```

### 堆栈思维

Deck 就是一个**工具栈**：

- **装填**：匹配到的 skill 工具 → 入栈
- **冗余**：自动填 +3 个基础工具卡槽（如 `fs_read_file`、`sys_terminal`等）
- **抽取**：LLM 只能在栈里选
- **Halt**：栈空了就停

```python
# 采购
Deck = skill_tools + redundancy_slots(+3)

# 执行（约束）
LLM.draw(tool) ∈ Deck  # 不能越界
```

### 动态大小

Deck 的大小是**动态**的：

| 组成 | 来源 | 可变？ |
|------|------|------|
| Skill tools | 匹配到的 skills 声明 | ✅ 随用户输入变化 |
| 冗余卡槽 | 固定 +3 ，从基础池填 | ❌ 恒定上限 |

举例：匹配到 1 个 skill 声明 1 个工具 → Deck 大小 = 1 + 3 = **4**。匹配到 2 个 skills 共 5 个工具 → Deck 大小 = 5 + 3 = **8**。

基础池只是一个安全网，确保 LLM 在需要查配置/看日志/执行命令时不会 halt。

### 代码

```python
class Deck:
    """不可变工具栈。"""
    def __init__(self, tools, registry):
        self.tools = dedup(tools)  # 有序列表

    def has(self, name): 
        return name in self.tools

    def schemas(self): 
        return [registry.get_schema(t) for t in self.tools]

def build_deck(skill_tools, registry, redundancy=3):
    """采购：skill_tools + 基础工具填充到 +3 卡槽。"""
    tools = list(skill_tools)
    added = 0
    for t in BASELINE_POOL:  # 按优先级填充
        if t not in tools and registry.has_tool(t):
            tools.append(t)
            added += 1
            if added >= redundancy:
                break
    return Deck(tools, registry)
```

整个 Deck 模块不到 100 行。

---

## Todo Ball Machine

人生任务管理系统——基于"抽彩球"的日程安排。

### 核心概念

装填 → 抽取 → 完成

- **装填（Fill）**：彩球 shuffle 后入栈，单文件 `state.json` 持久化
- **抽取（Draw）**：random.choice + pop，一场一球
- **重抽（Redraw）**：旧球 push 回栈顶，再抽
- **完成（Done）**：status 标记，完成率可统计

### 默认盒子（可自定义）

| 盒子 | emoji | 配额 |
|------|-------|------|
| 学习 | 📚 | 21 |
| 工作 | 💼 | 21 |
| 运动 | 🏃 | 15 |
| 治愈 | 🧘 | 14 |
| 社交 | 🎉 | 7 |
| 家务 | 🧹 | 6 |

改分类、改配额、改球内容 → 编辑 `balls.json` + `config.json`，**零代码改架构**。

### 接入 Deck

Todo Ball Machine 是 Deck 体系中的**一个 skill**，必须写清楚 tools：

```yaml
---
name: todo-ball-machine
description: 人生任务管理系统，基于抽球机制的日常场次管理
triggers:
  - todo_ball_machine
  - Todo Ball Machine
  - todo ball
  - 抽球
  - 场次
  - 今日安排
  - 盒子配额
  - 早报
tools:
  - todo_ball_machine
---
```

当用户说"帮我抽今天的 todo"，trigger 匹配 → `todo_ball_machine` 工具进入 Deck → LLM 只能在 Deck 里调用这个工具操作。

### Tool API

| action | session | content | 说明 |
|--------|---------|---------|-----|
| `dashboard` | — | — | 仪表盘：今日安排 + 盒子剩余 + 周期进度 |
| `today` | — | — | 今日 4 场详情 |
| `draw` | morning/afternoon/evening/overtime | — | 抽取指定场次 |
| `quick_draw` | — | — | 快速抽取三场 |
| `complete` | morning/... | — | 标记完成 |
| `redraw` | morning/... | — | 重抽：旧球回栈 → 新抽 |
| `edit` | morning/... | 新内容 | 修改场次内容 |
| `history` | — | N天（默认7） | 历史记录 |
| `day` | — | 日期（默认今天） | 指定日期详情 |
| `stats` | — | N天（默认7） | 统计报告 |
| `new_cycle` | — | 周期名 | 开启新周期 |

### 自动化

Cron 每日 8:00 自动推送早报到飞书：今日安排 + 盒子剩余 + 昨日回顾 + 连续完成天数 🔥

---

## Podcast Agent 🎙️

文档 → 播客脚本。受 Google NotebookLM Audio Overview 启发的内容重构工具。

### 能做什么

把任何文档（PDF、Markdown、TXT）转换成**自然双人对话式播客脚本**。不是 TTS，而是 LLM 理解、提炼、重新组织成对话。

### 使用

```bash
# CLI 单机
python tools/podcast_agent.py --source ~/paper.pdf --tone casual --lang zh

# Hermes Tool 调用
podcast_agent(source="~/notes.md", tone="educational", lang="zh")
```

**输出**：`paper.pdf.podcast.json` — title + summary + dialogue array

### 工作流程

```
文档 → 解析(pymupdf) → 分块(超长文档自动压缩) → LLM生成对话脚本 → JSON输出
```

### Prompt 约束

来源于开源实现 gabrielchua/open-notebooklm：
- 每行 ≤100 字符（约 5-8 秒说话时长）
- 严格 JSON 输出
- 自然口语，不朗读原文
- 三维可配：tone / lang / length

### 配置

`~/.hermes/podcast_agent_config.json` — 自动创建，自动检测 `OPENAI_API_KEY` / `MOONSHOT_API_KEY`

### 组合工流：Todo → Podcast

```bash
python tools/brief_to_podcast.py
```

自动拉取 Todo Ball Machine 今日状态 → 生成播客脚本。这是 Hermes × NotebookLM "爆炸效果"的最小可用示例。

### 接入 Deck

```yaml
---
name: podcast-agent
description: 文档转播客脚本
triggers:
  - podcast
  - 播客
  - 生成播客
tools:
  - podcast_agent
---
```

---

## Skill 的生命周期

**一个 session 内，skill 匹配一次、Deck 构建一次。**

- 用户说"帮我看看今天的 todo" → trigger 匹配 `todo-ball-machine` → Deck 包含 `todo_ball_machine` 工具 → LLM 开始调用
- 用户聊别的 → **session 切换，skill 结束，Deck 释放**
- 用户再提 todo → 重新匹配，重新构建 Deck

**没有常驻 skill，没有状态漂移。** 每次都是从 trigger → skill → Deck → 执行，干净闭环。

---

## 文件结构

```
┌─────────────────────────────────────────────────────────────┐
│  核心框架                                               │
├─────────────────────────────────────────────────────────────┤
│  deck.py                    # Deck（不可变工具栈）+ build_deck     │
│  skills.py                  # Skill 加载、trigger 匹配、缓存        │
│  registry.py                # 工具注册中心（schema + handler）    │
│  main.py                    # CLI 入口：skill 匹配 → Deck 装填 → 执行 │
├─────────────────────────────────────────────────────────────┤
│  工具                                                      │
├─────────────────────────────────────────────────────────────┤
│  tools/                                                     │
│  ├── todo_ball_machine.py      # Todo Ball Machine 工具入口              │
│  ├── podcast_agent.py          # 文档→播客脚本（NotebookLM-style）   │
│  └── brief_to_podcast.py       # 组合工流：Todo → Brief → Podcast    │
├─────────────────────────────────────────────────────────────┤
│  Skill 定义                                                  │
├─────────────────────────────────────────────────────────────┤
│  skills/                                                     │
│  ├── todo-ball-machine.md      # Todo Ball Machine 契约               │
│  └── podcast-agent.md          # Podcast Agent 契约                   │
├─────────────────────────────────────────────────────────────┤
│  数据                                                       │
├─────────────────────────────────────────────────────────────┤
│  todo_ball_machine/                                           │
│  ├── engine.py                # 极简引擎（抽/完成/重抽/统计）    │
│  ├── state.json               # 单文件运行时状态                   │
│  ├── balls.json               # 彩球定义（分类驱动）               │
│  ├── config.json              # 周期配置                         │
│  └── morning_brief.py         # 每日早报脚本（cron 调用）        │
└─────────────────────────────────────────────────────────────┘
```

---

## 设计原则

| 原则 | 含义 |
|------|------|
| Skill as Contract | trigger + tools + description，模糊即 bug |
| Procure Before Execute | Deck 构建一次，运行时不可变 |
| Immutable Boundary | 执行中不加载新工具， Deck 不膨胀 |
| Halt on Exhaustion | 工具不够就停，不回退重试 |
| 约分 | 嵌套 skill 的工具空间在采购阶段扁平化 |

---

> **从 Hermes 取了 skill 的概念，加了 Deck 的边界。**
> 
> **Todo Ball Machine 是这套边界里的第一个应用。**
> **Podcast Agent 是第二个——它证明了 Deck 的 skill 不仅可以是工具，还可以是内容引擎。**
