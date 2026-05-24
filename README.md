# Hermes Lite

> 一个 Agent，一块板。够了。

---

## 一句话

**Hermes Lite = 一台 Agent + 一块 Job Board。**

不需要 Symphony，不需要多 Agent 编排，不需要 daemon。Agent 自己读板、自己派活、自己留下信息素。人随时打开文件就能看到全貌。

---

## 为什么一个 Agent 就够了

多 Agent 框架的默认假设：任务复杂到需要分工，所以要有 orchestrator、worker pool、agent 间通信协议。

Hermes Lite 的假设不同：

> **Agent 自己就是 dispatcher。** Deck 架构已经解决了工具分发——每次任务只暴露相关工具。Agent 不需要"被调度"，它只需要"被激活"。

```
用户说"监工，看看进度"
    │
    ▼
trigger 匹配 job-supervisor skill
    │
    ▼
Deck 装填 board 管理 tools（8 个）
    │
    ▼
Agent 读 board → 汇报 → halt
```

Agent 一次只做一件事，但**一件事可以很复杂**——读多个 job、评估质量、生成报告。复杂不等于需要多个 agent。

---

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/JuliaHZhu/hermes-lite.git
cd hermes-lite

# 2. 装依赖
pip install -e .

# 3. 配置 API key
cp config.example.json config.json
# 编辑 config.json 填入你的 API key

# 4. 测试
python -m pytest tests/ -q
# 299 passed

# 5. 跑起来
python main.py
# 测试连通: python main.py -m ping
```

没有 daemon，没有配置文件目录，没有 orchestrator。`main.py` 就是入口。

---

## Text as Model

Job 的真实状态不在内存里，不在数据库里，在 `jobs/JOB-XXX.md` 的 frontmatter 里。

**人 `cat` 一下就能看懂，LLM 读一遍就能操作，git diff 能追踪变更。**

一个完整的 Job 文件：

```markdown
---
id: JOB-001
title: 重构 auth 模块
owner: agent-001
reviewer: human
skills: [code-review, refactor]
deliverables:
  - auth/sso.py
  - tests/test_sso.py
  - migration_guide.md
acceptance:
  - 向后兼容
  - 测试覆盖率>80%
  - 不改 public API
state: Done
phase: done
created: 2026-05-24T14:00:00Z
updated: 2026-05-24T14:55:00Z
---

## 任务描述
将 SSO 逻辑拆分成独立模块，保持向后兼容。

## 交付物
- [x] auth/sso.py
- [x] tests/test_sso.py
- [x] migration_guide.md

## 验收标准
- [x] 向后兼容
- [x] 测试覆盖率>80%
- [x] 不改 public API

## 事件流 (append-only)

- [14:00] created — state=Todo
- [14:05] checkpoint — phase=confirmed, who=agent-001, note=理解了任务和交付标准
- [14:10] checkpoint — phase=planned, who=agent-001, note=方案：先迁移函数，再补测试
- [14:15] checkpoint — phase=planned, who=human, note=方案通过，执行
- [14:20] state_change — Todo → Running
- [14:30] log — 创建 auth/sso.py
- [14:35] log — 测试通过，覆盖率 85%
- [14:40] self_check — deliverables 3/3, acceptance 3/3
- [14:45] eval — design-alignment: Pass
- [14:50] checkpoint — phase=reviewed, who=human, note=验收通过
- [14:55] checkpoint — phase=done, who=system
- [14:55] state_change — Running → Done
```

**这就是全部。** 没有隐藏状态，没有数据库，没有 ORM。一个 Markdown 文件 = 一个完整的工作记录。

---

## 交付质量四要素

每个 job 天然包含：

| 要素 | 字段 | 含义 |
|---------|-------|---------|
| **What** | `title` + `description` + `skills` | 任务内容和所需能力 |
| **Who** | `owner` + `reviewer` | 责任链：谁执行，谁确认 |
| **Deliverables** | `deliverables` checklist | 交付什么产出物 |
| **Acceptance** | `acceptance` checklist | 质量门槛是什么 |

---

## 七阶段生命周期

```
created → confirmed → planned → executing → self_checked → reviewed → done
```

| Phase | 意思 | 谁确认 | 产出 |
|-------|------|---------|------|
| `created` | 刚创建 | 系统 | job 文件 |
| `confirmed` | 责任人确认理解 | owner | 理解摘要 |
| `planned` | 方案提交并通过 | reviewer | 方案批准 |
| `executing` | 执行中 | owner | 代码/文档 |
| `self_checked` | 责任人自检 | owner | checklist 结果 |
| `reviewed` | 评估人复核 | reviewer | 评估结论 |
| `done` | 归档 | 系统 | 完整历史 |

每个关卡迁移都是 **checkpoint** 事件，记录：谁、什么关卡、什么结论、时间。

---

## 与 Symphony 的区别

| | **Symphony** | **Hermes Lite** |
|---|---|---|
| **核心假设** | 任务需要多个 worker 分工 | 一个 agent 可以序列处理多个任务 |
| **调度** | 硬代码 orchestrator（`while/for/sleep`） | agent 自己读板、自己决策 |
| **并发** | 内部管理多个 agent 实例 | 顺序执行，简单可预测 |
| **状态存哪** | 内存 / 数据库 / JSON | **Markdown 文件**（人可读） |
| **人怎么干预** | 改配置重启 | **直接改 job 文件** |
| **形态** | 工厂流水线（自动化） | 工单板（可管理） |

> **Symphony 是"机器自己跟着流水线跑"。Hermes Lite 是"机器跟着人的板子走"。**

---

## 还有别的吗？

有。这些是现有的 skill，都走同一套 Deck 架构：

| Skill | 做什么 | Trigger |
|-------|---------|---------|
| **job-supervisor** | Job board 管理 | 监工、工单、board |
| **todo-ball-machine** | 人生任务抽球系统 | 抽球、场次 |
| **podcast-agent** | 文档转播客 | 播客、podcast |
| **code-review** | 代码审查 | code review、审代码 |

添加新 skill 只需要：写一个 `skills/xxx.md` 契约 + 一个 `tools/xxx.py` handler。零核心侵入。

---

## 设计原则

| 原则 | 含义 |
|------|------|
| **一个 Agent 就够了** | 不要多 agent，不要 orchestrator，不要 daemon |
| **Text as Model** | 所有状态在 Markdown 里，人随时可读可改 |
| **Append-Only** | 事件流不可覆盖，历史不丢 |
| **Deck 裁剪** | 每次任务只暴露相关工具，不越界 |
| **关卡驱动** | 任务不是"Todo→Done"，是 7 个确认节点 |

---

> 你有一个 Agent。
> 
> 你有一块板。
> 
> 这两个东西一直在对话。
> 
> 你随时可以拍拍它的肩膀问："这个怎么样了？"
> 
> 它会指给你看板上的记录。
> 
> 够了。
