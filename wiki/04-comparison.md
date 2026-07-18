# 三项目横向对比

> 日期: 2026-07-18

## 基本信息

| 项目 | hermes-agent | nanobot | grok-build |
|------|-------------|---------|-----------|
| 组织 | Nous Research | HKUDS | xAI (SpaceXAI) |
| 规模 | 50万+ 行 | 6.7万行 | ~10万+行 |
| 语言 | Python/Rust/TS | Python + React | Rust |
| 开源 | MIT | 开源 | Apache 2.0 (不接 PR) |
| 定位 | 通用个人 Agent | 轻量级框架 | 终端 TUI Agent |

## 架构哲学对比

| 维度 | hermes-agent | nanobot | grok-build |
|------|-------------|---------|-----------|
| 核心原则 | 窄腰扩展 | 小核心边缘扩展 | Workspace 为中心 |
| 拓展方式 | Plugin/Skill/MCP | Channel/Tool/Skill/MCP | Tool/MCP/Plugin |
| 复用态度 | 允许重复，拒绝过早抽象 | 复制优于抽象 | 严格模块化 |
| 配置风格 | config.yaml | Pydantic schema | Rust config |

## 功能对比

| 功能 | hermes-agent | nanobot | grok-build |
|------|-------------|---------|-----------|
| CLI | ✅ | ✅ | ✅ |
| TUI | ✅ (全屏) | ✅ | ✅ (全屏 ratatui) |
| WebUI | ✅ (Electron) | ✅ (React) | ❌ |
| 消息平台 | 20+ | 20+ | ❌ |
| 技能系统 | ✅ | ✅ | ✅ |
| MCP | ✅ | ✅ | ✅ |
| 子 Agent | ✅ | ✅ | ❌ |
| Cron | ✅ | ✅ | ❌ |
| 内存压缩 | ✅ | ✅ (Dream) | ✅ |
| 检查点 | ❌ | ❌ | ✅ |
| ACP 协议 | ❌ | ❌ | ✅ |

## 安全设计对比

| 维度 | hermes-agent | nanobot | Worker Bee |
|------|-------------|---------|-----------|
| 写保护 | file safety | sandbox | write denylist |
| shell 执行 | shell hooks | sandbox backends | hardline cmd |
| 秘密管理 | secret scope | credential pool | 环境变量 |
| 审计日志 | audit log | ❌ | audit.py |
| 自我修改 | self-modify lock | ❌ | self-modify lock |

## 可借鉴给 Worker Bee 的优先级

| 优先级 | 来源 | 具体点 |
|--------|------|---------|
| **P0** | nanobot | MessageBus 消息总线抽象 — 解耦 channels 与 agent |
| **P0** | hermes-agent | 会话缓存保护 — 不破坏 mid-conversation context |
| **P1** | nanobot | Dream 两阶段压缩 — 长会话自动压缩而非截断 |
| **P1** | hermes-agent | FTS5 会话搜索 — 跨会话回忆 |
| **P1** | nanobot | Pydantic 配置验证 — 代替原始 dict |
| **P2** | grok-build | MCP 协议支持 — 行业标准接口 |
| **P2** | grok-build | 检查点系统 — 自动状态快照 |
| **P2** | nanobot | 持续目标跟踪 — 长期任务管理 |
