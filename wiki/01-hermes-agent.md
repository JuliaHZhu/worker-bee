# hermes-agent 核心特色

> 来源: https://github.com/nousresearch/hermes-agent
> 规模: 50万+ 行 (Python/Rust/TS 混合)
> 语言: Python 3.11+, 部分 Rust, TUI 用 TS
> 开源: MIT

## 一句话定位

通用个人 AI Agent，支撑 CLI + TUI + 消息网关(Telegram/Discord/Slack/…) + Electron 桌面端。

## 核心架构哲学

### 1. Prompt 缓存是神圣的
- 长会话每轮重用缓存前缀
- **不能** mid-conversation 更新 system prompt 或切换 toolset
- 唯一例外: context compression

### 2. 核心是窄腰，能力在边缘
- 每新增一个 core tool，每次 API 调用都得带上
- 扩展优先级: 现有代码 → CLI+skill → service-gated tool → plugin → MCP server → core tool (最后手段)
- 叫 "The Footprint Ladder"

### 3. Plugin 孤立居住
- Plugin 只能在自己目录里运作，通过 ABC/hook 与核心交互
- 如果 plugin 需要改核心文件，不行—先扩宽通用 plugin 表面

## 核心模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 会话生命周期 | `gateway/session.py`, `gateway/run.py` | SessionStore + GatewayRunner |
| Agent 循环 | `agent/conversation_loop.py` (~323K) | 多轮对话、工具调度 |
| 提示构建 | `agent/prompt_builder.py` (~98K) | 系统提示编排 |
| 工具执行 | `agent/tool_executor.py` (~86K) | 工具执行、guardrails |
| 内存管理 | `agent/memory_manager.py` (~49K) | 会话历史持久化 |
| 技能系统 | `agent/skill_commands.py`, `skill_utils.py` | 热加载技能 + LRU |
| 消息网关 | `gateway/run.py` (~16K) | 平台适配器 + 消息路由 |
| TUI | `cli.py` (~761K) | 全屏终端界面 |
| 插件系统 | `plugins/` (20+ 插件) | 平台/模型/工具插件 |

## 可借鉴给 Worker Bee

1. **会话缓存保护** — Worker Bee 每次切换 Deck 都可能破坏缓存，可学 hermes 的 "cache-safe" 原则
2. **Plugin 层级** — hermes 的 plugin 独立目录模式比 Worker Bee 的 skills 更规范
3. **多平台网关** — 消息网关抽象层，不是硬编到 agent 里
4. **FTS5 会话搜索** — 跨会话回忆检索，Worker Bee 现在只有单会话搜索
5. **当面不变性** — AGENTS.md 里写清楚 "What we want / What we don't"
