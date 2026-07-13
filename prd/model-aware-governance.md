# PRD: Model-Aware Message Governance

> **版本**: v1.0  
> **状态**: 待评审  
> **目标**: 将 Loop 的消息截断从"按消息数硬截"升级为"按模型感知的 4 阶段治理"  
> **读者**: nanobot（自主修复 Agent）

---

## 目录

1. [问题陈述](#一问题陈述)
2. [目标架构](#二目标架构)
3. [详细设计](#三详细设计)
4. [与 Loop 集成](#四与-loop-集成)
5. [实现任务列表](#五实现任务列表)
6. [验收标准](#六验收标准)
7. [风险与缓解](#七风险与缓解)

---

## 一、问题陈述

### 1.1 当前问题

`agent/loop.py` 目前只有一个 `_trim_messages()`：

```python
def _trim_messages(messages, max_count=30):
    return messages[-max_count:]
```

**这带来三个问题：**

1. **无视模型差异** — GPT-3.5（16k）和 GPT-4o（128k）用同一个 `max_count=30`，大模型浪费上下文，小模型可能溢出。
2. **按消息数而非 token 数截断** — 30 条短消息和 30 条长消息占用的 token 天差地别，无法精准控制预算。
3. **不处理消息健康** — 中断后残留的 orphan tool_result、缺失的 tool_call 结果、膨胀的旧 read_file 输出，都直接塞进 LLM，污染上下文。

### 1.2 为什么必须改

- worker-bee 的 8 台机器可能跑不同模型（kimi-k2.6 256k vs gpt-3.5-turbo 16k），统一截断不可行。
- 长会话（>20 轮）后，历史消息中的 tool 结果膨胀严重，必须按模型窗口精准裁剪。
- 治理是 Loop 的基础设施，不是 Skill 的业务逻辑（见 ADR-0001）。

---

## 二、目标架构

### 2.1 治理流水线

```
消息历史 (messages)
    │
    ▼
┌─────────────────┐
│ 1. Drop orphans │  ← 删除无 matching tool_call 的 tool_result
└────────┬────────┘
         ▼
┌────────────────────┐
│ 2. Backfill missing│  ← 为缺失结果的 tool_call 注入占位错误
└────────┬───────────┘
         ▼
┌────────────────────┐
│ 3. Microcompact    │  ← 旧 read_file/exec 结果压缩为一行摘要
└────────┬───────────┘
         ▼
┌────────────────────┐
│ 4. Hard trim       │  ← 按模型 token 预算丢弃最旧消息
└────────┬───────────┘
         ▼
干净的 messages → protocol.build_call()
```

### 2.2 模型感知

治理参数不硬编码，从 `ModelProfile` 读取：

| 参数 | 作用 | GPT-3.5 默认值 | Claude 默认值 |
|---|---|---|---|
| `context_window` | 模型总上下文长度 | 16 384 | 200 000 |
| `reserved_output_tokens` | 为模型回复预留的 token | 4 096 | 8 192 |
| `microcompact_age_turns` | 多少轮前的 tool 结果开始压缩 | 10 | 10 |
| `compact_threshold_ratio` | 达到多少比例时启动微压缩 | 0.75 | 0.80 |
| `hard_trim_ratio` | 达到多少比例时强制截断 | 0.90 | 0.92 |

### 2.3 关键原则

| 原则 | 说明 |
|---|---|
| **Loop  owns governance** | 消息健康是 Loop 的基础设施责任，Skill 不介入 |
| **模型差异化** | 不同模型的 context window、tokenizer、阈值都不同 |
| **不破坏 tool 对** | hard-trim 时若丢弃 assistant tool_call，一并丢弃其所有 tool_result |
| **保留 system 消息** | 无论怎么截断，system 消息始终保留在头部 |
| **中断即丢弃** | 不支持 mid-turn injection（grill-me Q3 确认） |

---

## 三、详细设计

### 3.1 ModelProfile 数据结构

```python
@dataclass(frozen=True)
class ModelProfile:
    name: str                          # "gpt-4o", "claude-sonnet-4-20250514"
    context_window: int                # 总上下文长度（tokens）
    encoding_name: str = "auto"        # tiktoken 编码名 或 "hf:<repo_id>"
    reserved_output_tokens: int = 4096 # 为回复预留
    governance: dict[str, int | float] # 阈值配置（可覆盖）
```

内置 6 个常用模型的 profile（gpt-4o / gpt-4o-mini / gpt-4-turbo / gpt-3.5-turbo / claude-sonnet-4-20250514 / kimi-k2.6）。

### 3.2 Token 计数

| 优先级 | 方案 | 覆盖模型 |
|---|---|---|
| 1 | tiktoken | OpenAI 系列（GPT-4/3.5） |
| 2 | transformers AutoTokenizer | 非 OpenAI 模型（Claude、Kimi 等近似） |
| 3 | 字符估算（~4 chars/token） | 无 tokenizer 时的保底 |

```python
def build_counter(encoding_name: str) -> Callable[[str], int]:
    if encoding_name == "auto":
        return tiktoken_counter("cl100k_base")  # 或 o200k_base
    if encoding_name.startswith("tiktoken:"):
        return tiktoken_counter(...)
    if encoding_name.startswith("hf:"):
        return hf_counter(...)
    return char_estimate  # fallback
```

### 3.3 4 阶段治理详解

#### Stage 1: Drop orphans

遍历所有 `role == "tool"` 的消息，检查其 `tool_call_id` 是否存在于任何 assistant message 的 `tool_calls` 中。不存在则删除。

**目的**：清理中断残留的无效 tool_result。

#### Stage 2: Backfill missing

遍历所有 assistant message 的 `tool_calls`，若某个 `tool_call_id` 没有对应的 `role == "tool"` 结果，注入一个错误占位：

```python
{
    "role": "tool",
    "tool_call_id": tc["id"],
    "content": "[error: tool result missing — possibly interrupted]",
    "name": tc.get("name", "unknown"),
}
```

**目的**：防止 LLM 等待永远到不了的结果。

#### Stage 3: Microcompact

对 `age > microcompact_age_turns` 的 tool_result，如果其 tool 属于 `{fs_read_file, fs_list_dir, sys_terminal, web_fetch}`，将内容替换为一行摘要：

```
[fs_read_file result: 18432 chars — truncated by microcompact]
```

**目的**：减少旧 tool 结果对上下文的膨胀，同时保留"有过这个操作"的信息。

#### Stage 4: Hard trim

计算当前消息总 token 数。若超过 `usable_context = context_window - reserved_output_tokens`，从 oldest 开始丢弃，直到符合预算。

**规则**：
- 始终保留 system 消息（index 0）
- 丢弃 assistant tool_call 时，一并丢弃其所有 matching tool_result
- 不单独丢弃 tool_result 而不丢弃其 tool_call（防止 LLM 看到无意义的结果）

---

## 四、与 Loop 集成

治理函数在每次 LLM 调用前执行，对 Loop 的侵入极小：

```python
# agent/loop.py (修改后)
from agent.governance import govern_messages
from agent.models import ModelRegistry

registry = ModelRegistry()
profile = registry.get(config["model"])

# ... inside the while loop, before build_call ...
messages = govern_messages(messages, profile)
response = generate_response(protocol.build_call(messages, tools))
```

**Loop 核心行数变化**：治理逻辑全部外移到 `agent/governance.py`，Loop 本身只增加 ~3 行调用代码，保持精简。

---

## 五、实现任务列表

### Phase 1: 基础设施（P0）

| # | 任务 | 文件 | 说明 |
|---|---|---|---|
| 1.1 | 新增 `agent/models.py` | `agent/models.py` | ModelProfile + TokenCounter + ModelRegistry |
| 1.2 | 新增 `agent/governance.py` | `agent/governance.py` | 4 阶段治理流水线 |
| 1.3 | 修改 `requirements.txt` | `requirements.txt` | 添加 `tiktoken>=0.8.0` |
| 1.4 | 修改 `agent/loop.py` | `agent/loop.py` | 在 `build_call` 前调用 `govern_messages()` |
| 1.5 | 删除旧 `_trim_messages` | `agent/loop.py` | 移除按消息数硬截断的旧逻辑 |

### Phase 2: 测试（P0）

| # | 任务 | 文件 | 说明 |
|---|---|---|---|
| 2.1 | 新增 `tests/test_governance.py` | `tests/test_governance.py` | ParagraphEditor fixture（分段写作） |
| 2.2 | 补充 EcoGameEngine fixture | `tests/test_governance.py` | 物理循环引擎（刮风→下雨→长草→树→雷→火→烧） |
| 2.3 | 单元测试：orphan drop | `tests/test_governance.py` | 验证无 matching tool_call 的 result 被删除 |
| 2.4 | 单元测试：backfill | `tests/test_governance.py` | 验证缺失结果自动注入占位 |
| 2.5 | 单元测试：hard-trim | `tests/test_governance.py` | 验证 2k token 小窗口下消息正确截断 |
| 2.6 | 单元测试：pair integrity | `tests/test_governance.py` | 验证 assistant/tool 对不被拆散 |
| 2.7 | 对比基准 | `tests/test_governance.py` | 同一长会话，对比改前后的 token 浪费率 |

### Phase 3: 文档（P1）

| # | 任务 | 文件 | 说明 |
|---|---|---|---|
| 3.1 | 更新 ADR-0001 状态 | `docs/adr/0001-loop-governance-by-model.md` | Proposed → Accepted |
| 3.2 | 新增 ADR-0002 | `docs/adr/0002-governance-implementation.md` | 实现细节、第三方依赖、设计决策 |
| 3.3 | 更新 CONTEXT.md | `CONTEXT.md` | 补充 ModelProfile、Governance 术语 |

---

## 六、验收标准

- [ ] `agent/models.py` 存在，内置 6 个模型 profile，支持 runtime override
- [ ] `agent/governance.py` 存在，4 阶段流水线（drop → backfill → microcompact → hard-trim）
- [ ] `agent/loop.py` 在每次 LLM 调用前调用 `govern_messages()`，旧 `_trim_messages` 已删除
- [ ] `tests/test_governance.py` 全部通过（6+ 个测试用例）
- [ ] ParagraphEditor fixture：8 段落写作 + 合成，截断后无 orphan tool_call
- [ ] EcoGameEngine fixture：3–4 轮物理循环，最新状态保留，状态链合法
- [ ] 对比基准：长会话（>50 轮）下，改后 token 浪费率 < 改前 50%
- [ ] 无 tiktoken 时 graceful fallback 到字符估算，不报错
- [ ] 新增模型只需在 `ModelRegistry` 注册 profile，不修改 governance 逻辑

---

## 七、风险与缓解

| 风险 | 缓解 |
|---|---|
| **Model Profile 漂移**（首要风险） | ① `get()` 回退到保守通用 profile；② `register()` 支持 runtime 覆盖；③ 各机器 `config.yaml` 可 pin profile；④ token 计数是 hint 非 correctness gate，偏差 10% 仍可运行 |
| **Token 计数不准**（非 OpenAI 模型） | transformers 作为可选 fallback；计数误差只影响截断时机，不影响正确性 |
| **Hard trim 误删关键消息** | 始终保留 system 消息；tool 对原子性丢弃；microcompact 先于 hard-trim 减少误删概率 |
| **Governance bug 导致 Loop 崩溃** | 纯本地数据处理，无网络调用；异常时回退到原消息（passthrough） |
| **Loop 行数膨胀** | 治理逻辑全部外移，Loop 只增 3 行调用，保持 ~250 行内 |
