# nanobot 核心特色

> 来源: https://github.com/HKUDS/nanobot
> 规模: 6.7万行 Python + React WebUI
> 语言: Python 3.11+, React/TypeScript
> 开源: 开源

## 一句话定位

轻量级开源 AI Agent 框架，内置 React WebUI，支撑 20+ 消息平台。

## 核心架构哲学

### 1. 核心保持小型，边缘扩展
- `agent/loop.py` + `agent/runner.py` 是关键路径，修改要极简
- 新能力 → channel adapter / tool / skill / MCP server，不是 core

### 2. 复制优于过早抽象
- Channel 和 Provider 允许重复逻辑，不为了消灭重复而引入复杂基类
- 每个 channel 文件自包含、可独立阅读

### 3. 明确优于魔法
- 配置在 Pydantic schema 中显式声明，不用隐式环境变量
- 错误处理提明确异常，不是默默修正

## 核心模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 消息总线 | `nanobot/bus/queue.py` | 解耦 channels 与 agent 核心 |
| Agent 循环 | `nanobot/agent/loop.py`, `runner.py` | Session + 工具调度 + LLM 对话 |
| LLM Provider | `nanobot/providers/` | Anthropic/OpenAI/Azure/… 工厂 |
| Channels | `nanobot/channels/` | 20+ 平台 (TG/Discord/Slack/Feishu/…) |
| Tools | `nanobot/agent/tools/` | 文件/壳/shell/web/MCP/cron/… |
| 内存 | `nanobot/agent/memory.py` | 会话历史 + Dream 两阶段压缩 |
| Session | `nanobot/session/` | TTL 自动压缩 + 持续目标 |
| WebUI | `webui/` | Vite React SPA + WebSocket |
| API | `nanobot/api/server.py` | OpenAI-compatible HTTP API |
| Config | `nanobot/config/schema.py` | Pydantic 配置，支持 camelCase alias |

## 可借鉴给 Worker Bee

1. **消息总线抽象** — Worker Bee 的 NATS 是实时的，nanobot 的 MessageBus 更适合异步解耦
2. **Dream 两阶段压缩** — 长会话自动压缩，Worker Bee 现在只有简单截断
3. **Pydantic 配置** — Worker Bee 用原始 dict，nanobot 的 schema 验证更严谨
4. **Channel 自发现** — pkgutil 扫描 + entry-point 插件，Worker Bee 的 tools 也可做
5. **持续目标** — `goal_state.py` 跟踪长期任务，Worker Bee 没有
6. **React WebUI** — 如果 Worker Bee 需要 WebUI，nanobot 是最轻的参照
