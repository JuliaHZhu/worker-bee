# grok-build 核心特色

> 来源: https://github.com/xai-org/grok-build
> 规模: ~10万+行 Rust
> 语言: Rust (pinned toolchain)
> 开源: Apache 2.0 (不接受外部 PR)

## 一句话定位

SpaceXAI 内部终端 TUI 编码 Agent，运行在全屏终端界面中，支持交互式/无头/编辑器嵌入三种模式。

## 核心架构哲学

### 1. Workspace 为中心
- 代码库本身就是"workspace"
- 文件系统、VCS、执行环境、检查点都在 workspace crate 里
- Agent 不是逃离工程师的工具箱，就是工程师的终端

### 2. 多模式运行
- **交互式**: 全屏 TUI (基于 `ratatui`)
- **无头**: 脚本/CI 模式，从标准输入读取任务
- **编辑器嵌入**: 通过 Agent Client Protocol (ACP) 接入 VS Code 等编辑器

### 3. Rust 的安全保证
- 记忆管理、并发、错误处理都在编译时解决
- 没有 Python 的 runtime NameError/ImportError 问题
- 但构建时间长，开发速度慢于 Python

## 核心模块

| 模块 | 路径 | 职责 |
|------|--------|------|
| TUI | `crates/codegen/xai-grok-pager` | 全屏终端界面，scrollback + 提示符 + modal |
| Agent Shell | `crates/codegen/xai-grok-shell` | 运行时 + leader/stdio/无头入口 |
| Tools | `crates/codegen/xai-grok-tools` | 终端、文件编辑、搜索、MCP 服务器 |
| Workspace | `crates/codegen/xai-grok-workspace` | 文件系统、VCS、执行、检查点 |
| 配置 | `crates/codegen/xai-grok-config` | 配置系统 |
| MCP | `crates/codegen/xai-grok-mcp` | Model Context Protocol 支持 |
| 内存 | `crates/codegen/xai-grok-memory` | 会话内存 |
| 插件市场 | `crates/codegen/xai-grok-plugin-marketplace` | 插件管理 |

## 可借鉴给 Worker Bee

1. **Workspace 为中心** — Worker Bee 的 workspace 保护是后续加的，grok 一开始就是 workspace-native
2. **检查点系统** — 自动保存状态快照，Worker Bee 有 snapshot 但缺 checkpoint
3. **MCP 支持** — Model Context Protocol 是行业标准，Worker Bee 还没有
4. **ACP 协议** — Agent Client Protocol 让编码 Agent 可以嵌入任意编辑器
5. **终端渲染** — TUI 不是打印文字，而是真正的终端界面（ratatui 库）
