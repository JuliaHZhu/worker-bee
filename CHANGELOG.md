# Changelog

Hermes Lite 开发历史。从最初 300 行的 nanobot 到现在的 ~2,700 行 agent 框架。

---

## 2026-05-22

### 🔄 /goal → /task 系统 (`26efd3e`)

**删除** `/goal`（被动上下文注入，不驱动任何循环）。

**新增** `/task` 机制 — 可分配、可追踪的工作单元：

```
/task add 把 auth 迁移到 Fastify
/task add #morning-brief 检查日志
/task list [status|#job]
/task start 3 | done 3 | cancel 3
/task assign 3 #evening-brief
```

数据模型：

| 字段 | 说明 |
|------|------|
| `status` | todo → in_progress → done \| cancelled |
| `assigned_to` | cron job ID，空 = 未分配 |
| `priority` | 数字，越大越优先 |

Cron 集成：job 执行前自动注入分配给自己、状态为 `todo/in_progress` 的 tasks。

修改文件：`memory.py`, `main.py`, `batch_learn.py`, `cron/scheduler.py`, `tests/test_memory.py`

### ✨ Skill Creator 动态上下文注入 (`85e5f32`)

当匹配到 `skill-authoring` 类 skill 时，自动注入现有 skills 列表和已注册 tools 列表到 system prompt。创建新 skill 时 LLM 能看到完整项目上下文。

### 🧪 Skill Creator 测试验证 (`85e5f32`)

新增 `_validate_skill()` 函数 — 创建 skill 后自动验证 trigger、tools、frontmatter 格式。

### 🔧 Skill Creator Trigger 审计 (`a6a2589`)

去掉过于宽泛的 trigger keyword（如 `skill with state`、`底层skill`、`information skill`），改为具体动作型 trigger。给每个 creator 加了 phase label。

### 🏗️ Skill Authoring 双轨流水线 (`58bef1f`)

- **creator-is-you** — 和 LLM 协作设计 skill（触发 → kernel → 工作流 → 边界）
- **creating-trainer** — skill 创建完成后审查质量（trigger 检查、工具验证、反模式扫描）

---

## 2026-05-21

### 📝 Skill Creator 指南 (`b148643`)

新增两个 skill creator：
- **create-mechanism-skill** — 需要 Python 后端 + 状态持久化的 skill
- **create-task-skill** — 纯编排的轻量 skill（无自定义代码）

每个包含五元组检查清单、固定步骤、最小完整模板、6 个常见陷阱。

### 🐛 Deck 修复 (`299cf46`)

`build_deck(redundancy=0)` 时判断 `filled >= redundancy` 在 append **之后**，导致漏一个工具。修复：检查移到循环开头。

### 🔧 Deck 协议修复 (`a3ee473`)

Deck v2 重写删除了 `get_schemas_for_protocol()`，导致 `agent.py` 调用失败。加回，支持 Anthropic/OpenAI 双协议转换。

### 📦 Todo Ball Machine v2 + Deck Stack (`2c53846`)

Deck 从线性工具集重写为堆栈模型，Todo Ball Machine 重构为 v2。

---

## 早期（2026-05-20 之前）

### 🧪 测试套件 (`2f85508`)

212 个 pytest 测试，覆盖 registry、skills、memory、infra、cron、file、terminal、web、subagent。

### 🔒 安全修复 (`ddce7d0`, `0adfc0b`, `0f6a31b`)

- SQLi 修复（参数化查询）
- allowlist + confirm 安全模型
- 移除硬编码文件扩展名
- workspace guard（cron 脚本必须在允许目录内）

### 🚀 gstack 集成 (`670a54d`)

集成 gstack（Bun/TS browser 守护进程），适配 5 个 skill：review、cso、investigate、ship、browse。

### 🤖 并行子代理 (`6ecf3fe`)

`agent_delegate_parallel` + `agent_cross_validate` — 多子代理并行执行 + 多模型交叉验证。

### 📋 TODO Ball Machine 集成 (`2bbc4a0`)

从 ex-ENTP 项目移植，支持 todo 抽球、cron 调度、subagent 委派、OpenAI 协议。

### 🃏 Deck 架构 (`7c7b0ea`)

核心创新：Registry（工具注册）→ Skills（声明需求）→ Deck（运行时边界）→ Agent（受约束执行）。冗余 +3 基础工具槽。

### 🏁 初始提交 (`414ce5a`)

~300 行 nanobot — 最小可运行 agent，Anthropic 协议，CLI 交互。
