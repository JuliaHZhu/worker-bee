# Hermes Lite

> 🤖 **本仓库由 AI Agent 自动托管维护。**  
> 提交记录、文档和代码变更均通过人机协作完成。

受 [Hermes Agent](https://github.com/nousresearch/hermes-agent) 启发的最小化、独立 AI Agent 框架。它在单仓库、零额外依赖的包中，保留了核心架构——skill 合约、trigger 匹配、不可变工具边界。

**如果你想要一个最小化的 Hermes 来学习、fork 或嵌入，用这个。**  
完整的设计演化见 [DESIGN.md](./DESIGN.md)。

---

## 与 Hermes 的核心差异

| | Hermes | Hermes Lite |
|---|---|---|
| **代码量** | ~35,900 行 | **~1,700 行** |
| **平台** | 15+（Discord、Telegram、Feishu 等） | **Linux CLI**（可选 webhook） |
| **Skill 匹配** | 被动列举——LLM 从扁平索引中自己挑 | **主动匹配**——系统通过 `trigger` 字段推送 |
| **工具边界** | 宏 toolset（每次调用 4–40 个工具） | **不可变 Deck**（每个任务 1–5 个工具） |
| **注册表** | 以 toolset 为中心，静态 YAML 配置 | **动态加载**——`fs_*`、`net_*`、`sys_*`、`agent_*` 命名空间 |
| **消息格式** | 内部统一为 OpenAI | **双协议**——Anthropic + OpenAI |
| **定位** | 全功能生产系统 | **便于学习的最小核心** |

---

## 快速开始

```bash
git clone https://github.com/JuliaHZhu/hermes-lite.git
cd hermes-lite
pip install -e .
hermes-lite setup          # 生成 ./config.json（已被 gitignore）
hermes-lite -m "hello"     # 验证模型连通性
hermes-lite                # 启动交互会话
```

---

## 架构

```
hermes-lite/
├── main.py              # CLI 入口
├── agent.py             # Agent 循环（双协议）
├── deck.py              # 不可变工具边界
├── registry.py          # 带元数据的工具注册表
├── skills.py            # Skill 加载器 + trigger 匹配
├── memory.py            # SQLite 持久化
├── DESIGN.md            # 完整设计演化文档
└── tools/               # fs_*、net_*、sys_*、agent_*
```

---

## 协议

MIT —— 详见 [LICENSE](./LICENSE)。

Hermes Lite 的设计思想和架构源自 [Hermes Agent](https://github.com/nousresearch/hermes-agent)（Nous Research）。本项目与 Nous Research 无关联，也未获其背书。
