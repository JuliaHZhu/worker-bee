# Hermes Lite

受 [Hermes Agent](https://github.com/nousresearch/hermes-agent) 启发的轻量级 AI Agent 框架。为那些想要核心 agent 架构、但不想承受生产级复杂度的开发者而设计。

---

## 一、我们在做什么

我们在造一个**先采购工具、再动手做事**的 Agent。

大部分 Agent 的做法是：把一长串工具清单扔给 LLM，指望它自己挑对的。这很不稳定——LLM 会困惑、选错、纠正、再试一次。我们用 **Deck 架构** 替换了这套做法：

1. **选** — LLM 从技能库中挑选相关的 skill
2. **购** — 把这些 skill 声明的所有工具收拢成一个 Deck
3. **做** — Agent 只从 Deck 里抽工具。Deck 之外，什么都没有。

如果 Deck 里的工具做不完这件事 → **停下来**。因为第一次采购已经是尽可能宽的范围了，用同样的工具再试一次也不太可能成功。这说明方法本身可能错了——该人类上场了。

**约分：**
```
设 S  = LLM 选出的 skill 集合
设 T(s) = skill s 声明的工具集合

Deck = ⋃_{s ∈ S} T(s)   （取并集，去重）
```

即使运行时 skill A 又调用了 skill B，只要 B 一开始就在 S 里，B 的工具就已经在 Deck 中了。嵌套 skill 的工具空间会在执行前坍缩成一个扁平的、不可变集合。

---

## 二、这个问题从哪来

### 起因

我们从好奇 [Hermes Agent](https://github.com/nousresearch/hermes-agent) 开始——一个功能完备的 agent，有 skill、子代理、多平台分发。我们想搞清楚：**它的工具是怎么组织的？**

Hermes 用目录树管理 skill，但**没有 trigger 字段**。skill 是靠索引或子代理来匹配的，没有声明式合约。这就引出了问题：**如果 skill 的名字有歧义，系统怎么知道该加载哪个？**

### 领悟

**Skill 不是工具集。Skill 是一份合约**——它声明了：
- **什么时候**用它（`trigger`）
- **用什么**工具（`tools`）
- **怎么用**（body / 指令）

但即使 skill 本身很精确，LLM 执行时仍然能看到太多工具。我们需要一个**边界**。

### 比喻

> *"活用字典，粗筛粗，细筛细，先组卡组，再抽卡。"*
>
> 就像做饭前先备齐食材。做到一半发现缺料， shouldn't 再跑一趟超市。如果买的料不够用，那可能是菜谱本身有问题。

---

## 三、接下来要搭什么："设计之眼"

Hermes Lite 现在有了一双精确的手。接下来我们要造的是**设计之眼**——把模糊意图变成可执行方案的能力。

### Pipeline

这就是人类发现知识、发明东西的方式。我们要把它变成可执行的流程：

```
模糊想法
    │
    ▼
┌─────────────────┐
│  /clarify       │  "我们到底在解决什么？"
│  意图澄清        │  输出：约束清单 + 成功标准
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  /explore       │  "有哪些可行的路径？"
│  方案探索        │  输出：2-3 个候选方案 + 权衡分析
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  /decide        │  "选哪条路？为什么？"
│  决策锚定        │  输出：决策记录 + 风险评估
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  /validate      │  "做出来对不对？"
│  实现验证        │  输出：验证报告 + 偏差分析
└────────┬────────┘
         │
         ▼
    回到 /clarify（循环）
```

### 为什么是研究拆解实验的方法论？

牛顿、法拉第、图灵——他们都是这么干的。观察现象，提出模糊问题，澄清为可验证的假设，设计实验，执行，验证，迭代。**我们在自动化科学方法。**

Agent 不是在"写游戏功能"。它在**把抽象问题拆解成实验**，执行它们，然后根据证据调整方向。

### 多机体并行

如果一个 agent 搞不定，就多复制几个。不同 LLM 有不同的偏见和盲区。让多个独立 agent 走同一条路，然后交叉比对：

```
同一个问题
    │
    ├── Agent A (Claude) → 路径 1 → 结果 α
    ├── Agent B (GPT-4)  → 路径 2 → 结果 β
    ├── Agent C (Kimi)   → 路径 3 → 结果 γ
    │
    ▼
交叉比对
    α = β = γ  → 高置信度，可能正确
    α = β ≠ γ  → 检查 C 的偏见
    α ≠ β ≠ γ  → 问题本身没被澄清透，回到 /clarify
```

这就是科学共同体所说的**同行评审**。

### 即将推出的 Skills

| Skill | 用途 |
|-------|------|
| `design-clarify` | 把模糊意图转译为可量化的约束条件 |
| `hypothesis-generator` | 从观察中生成可验证的假设 |
| `experiment-designer` | 设计最小实验来验证假设 |
| `multi-agent-executor` | 并行起多个 agent，比对结果，消解冲突 |

---

## 与 Hermes 的关键差异

| 维度 | Hermes | Hermes Lite |
|------|--------|-------------|
| 代码量 | ~35,900 行 | **~1,700 行** |
| 平台 | 15+ | Linux CLI（可选 Feishu/Discord webhook） |
| 注册表 | 以 toolset 为中心，静态配置 | **标签/分类 + 动态加载** |
| Skill 匹配 | 被动列举（LLM 自己挑） | **主动匹配（系统推送）** |
| 工具边界 | 宏 toolset（4–40 个工具） | **不可变 Deck（1–5 个工具）** |
| 消息格式 | 内部统一为 OpenAI | 双协议（Anthropic + OpenAI） |
| 设计阶段 | 无 | **/clarify → /explore → /decide → /validate** |

---

## 注册表：清晰本身就是边界

每个注册函数都遵循严格的命名规范：

```python
registry.register(
    name="fs_read_file",
    description="读取文本文件并支持分页。用于检查源码、配置或日志。",
    parameters={...},
    handler=fs_read_file,
    tags=["filesystem", "read"],
    category="filesystem"
)
```

**命名规范：** `{domain}_{action}_{object}`
- `fs_read_file`, `fs_write_file`, `fs_search_files`
- `net_web_search`, `net_web_extract`
- `sys_terminal`, `agent_delegate_task`

模糊的命名是 LLM 困惑的根源。`name + description + parameters` 三者构成完整的接口合约。

### Skill + 注册表 + Deck = 确定性导航

```
用户："帮我 review 代码"
    ↓
系统匹配到 Skill "code-review"
    ↓
Skill 声明 tooldeck：[fs_read_file, fs_search_files]
    ↓
组建 Deck —— 本次任务只有这 2 个工具
    ↓
注册表确认 fs_read_file = "读取本地文本文件并支持分页"
    ↓
LLM 在 2 个工具内操作 —— 零歧义
```

**传统做法（不稳定）：** LLM 看到 40 个工具 → 猜 → 可能猜错 → 纠正 → 不稳定。  
**Hermes Lite（稳定）：** Skill 导航到精确子集 → Deck 强制执行边界 → 确定性行为。

---

## 快速开始

Hermes Lite 是**项目本地**的——所有东西都在一个目录里。

```bash
# 1. 任意位置克隆
git clone https://github.com/JuliaHZhu/hermes-lite.git
cd hermes-lite

# 2. 安装（可编辑模式，项目本地）
pip install -e .

# 3. 配置（生成 ./config.json —— 已被 gitignore）
hermes-lite setup

# 4. 验证模型连通性
hermes-lite -m "hello"

# 5. 开始使用
hermes-lite
```

---

## 架构

```
hermes-lite/
├── main.py              # CLI 入口 + 命令路由
├── agent.py             # AI Agent 主循环（双协议）
├── deck.py              # Deck 采购 + 不可变工具边界
├── registry.py          # 带丰富元数据的工具注册表
├── skills.py            # Skill 加载器 + trigger 匹配
├── memory.py            # SQLite 持久化
├── infra_toolsets.py    # 平台检测 + 工具门控
├── DESIGN.md            # 完整的设计演化文档
└── tools/
    ├── terminal.py      # sys_terminal
    ├── file.py          # fs_read_file, fs_write_file, fs_search_files
    ├── web.py           # net_web_search, net_web_extract
    ├── subagent.py      # agent_delegate_task
    └── send_message.py  # Feishu/Discord webhook
```

---

## 协议

MIT License —— 详见 [LICENSE](./LICENSE)。

## 致谢

Hermes Lite 的设计思想和架构源自 [Hermes Agent](https://github.com/nousresearch/hermes-agent)（Nous Research）。本项目与 Nous Research 无关联，也未获其背书。
