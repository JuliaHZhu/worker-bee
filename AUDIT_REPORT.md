# Worker-Bee 核心模块审计报告

**审计日期**: 2026-06-14
**审计范围**: `worker_bee/` 目录下 10 个核心文件
**审计方法**: 逐文件静态分析 + 交叉引用验证

---

## 一、架构骨架总览

```
main.py          ← CLI入口、会话管理、Deck采购、Skill触发
  ├─ agent.py    ← AIAgent 薄壳：配置、工具schema缓存、向后兼容转发
  ├─ loop.py     ← 协议无关的对话循环 (run_conversation)
  ├─ protocols.py ← AnthropicProtocol / OpenAIProtocol (格式转换 + API调用)
  ├─ registry.py  ← ToolRegistry：注册、缓存、调用（模块级单例）
  ├─ deck.py      ← Deck：不可变运行时工具边界 + 冗余填充
  ├─ skills.py    ← SkillManager：markdown加载、触发器匹配、双层缓存
  ├─ memory.py    ← SessionDB：SQLite会话/消息/todo持久化
  ├─ workspace.py ← 工作区路径解析（单一真相源）
  └─ infra_toolsets.py ← 平台基础设施工具集（当前仅linux桩）
```

**分层关系**:
- **入口层**: `main.py` — 用户交互、会话流程编排
- **循环层**: `loop.py` — 协议无关的 tool-use 循环
- **协议层**: `protocols.py` — Anthropic/OpenAI 格式差异隔离
- **执行层**: `registry.py` + `deck.py` — 工具注册、边界控制、调度
- **知识层**: `skills.py` — 技能匹配与上下文注入
- **持久层**: `memory.py` — SQLite 会话与消息存储
- **环境层**: `workspace.py` + `infra_toolsets.py` — 路径解析与平台感知

---

## 二、逐文件审计

---

### 2.1 agent.py（131行）

**架构角色**: AIAgent 薄壳 — 聚合配置、创建 Protocol、提供向后兼容方法。

| 发现 | 严重度 | 描述 |
|------|--------|------|
| `_tool_schema_cache` 键包含 `registry.generation` | 🟢 正面 | 利用 registry 的 generation 计数器自动感知注册表变更，设计精良 |
| `_init_client` 每次重建 protocol | 🟡 注意 | `__init__` 调用 `_init_client()`，但 protocol 通过 property 暴露 setter——外部可直接替换 client 绕过 config |
| `_load_prompt_files` 硬编码 `~/.worker-bee/` | 🟢 无风险 | 路径固定，不可被用户输入控制 |
| `run()` 仅一行转发 | 🟢 设计 | 保持 agent.py 薄壳定位，核心逻辑在 loop.py |

**未使用代码**: 无

---

### 2.2 deck.py（106行）

**架构角色**: 不可变运行时工具边界 — "装填(Procure) → 抽取(Draw) → 约束(Halt)"。

| 发现 | 严重度 | 描述 |
|------|--------|------|
| Deck 不可变设计 | 🟢 正面 | 构造后 `self.tools` 不再改变，线程安全 |
| `build_deck()` 冗余策略合理 | 🟢 正面 | 从 BASELINE_POOL 按优先级填充，填满即停 |
| `get_schemas_for_protocol()` OpenAI转换与 `agent._build_tools()` 重复逻辑 | 🟡 技术债 | 两处都有 "openai" 分支的 function-calling 格式转换，应统一到一处 |
| `Deck.__init__` 依赖外部 `registry` | 🟢 设计 | 传入而非硬编码，可测试性好 |
| `schemas()` 方法对不存在工具静默跳过 | 🟡 注意 | 如果 skill 声明的工具未注册，LLM 拿不到 schema 但不知原因 |

**关键问题 — Deck 合并破坏顺序** (见 main.py 审计)

**未使用代码**: 无

---

### 2.3 registry.py（190行）

**架构角色**: 工具注册与调度中心，支持标签分类、LRU缓存、线程安全。

| 发现 | 严重度 | 描述 |
|------|--------|------|
| RLock + 独立 cache_lock 双锁设计 | 🟢 正面 | 读写分离，减少锁竞争 |
| generation 计数器用于缓存失效 | 🟢 正面 | 外部缓存无需持有锁即可检测数据变更 |
| `register()` 中 `parameters` 直接合并到 `input_schema` | 🟡 注意 | `**parameters` 解包 — 如果 parameters 中包含 `"type"` 会覆盖外层的 `{"type": "object"}` |
| `call()` 对 handler 返回值 `str(result)[:8000]` | 🟡 注意 | 8000 字符硬截断可能丢失关键信息，且对大返回值无流式处理 |
| `call()` 错误处理笼统 | 🟡 注意 | `except Exception as e: return f"Error: {e}"` — 错误信息暴露给 LLM，但 handler 内部的具体异常类型信息丢失 |
| `list_by_category()` 使用 `setdefault` | 🟢 正确 | 标准 Python dict 方法 |
| LRU实现为手动 OrderedDict 弹窗 | 🟢 正确 | 但 `self._schemas_cache.pop(next(iter(...)))` 对于 OrderedDict 弹出最旧项是正确的 |

**未使用代码**:
- `snapshot()` (L176-186) — 全项目无调用点。仅在 `tests/test_registry.py` 中有测试覆盖。

---

### 2.4 memory.py（434行）

**架构角色**: SQLite 会话/消息/todo 持久化，支持标签、归档、handoff。

| 发现 | 严重度 | 描述 |
|------|--------|------|
| tag 过滤使用 LIKE 拼接 | 🟡 安全 | L159-161: `f'%"{t}"%'` — 如果 tag 包含 `"`、`%` 或 `_`，可能导致 SQL LIKE 注入或意外匹配。虽然当前 tag 来自 `#word` 解析（不含这些字符），但防御性不足 |
| `save_message` 无条件 json.dumps | 🟢 正确 | tool_calls 和 tags 都经过 JSON 序列化 |
| `get_messages` 中 `json.loads` 反序列化 | 🟢 正确 | 对称操作 |
| 损坏数据库自动重命名 | 🟢 正面 | L17-26: 捕获 DatabaseError/OSError 后自动归档损坏文件并重建 |
| 线程本地连接 (`threading.local`) | 🟢 正面 | 每个线程持有独立连接，`check_same_thread=False` 放宽限制 |
| Schema 迁移机制 | 🟢 正面 | `_migrate_schema()` 用 PRAGMA table_info 检查列存在性再 ALTER TABLE |
| `export_handoff()` 路径安全 | 🟢 正面 | 输出路径限定在 `~/.worker-bee/handoffs/`，无路径穿越风险 |
| `create_session` 使用 `str(uuid.uuid4())[:8]` | 🟡 注意 | 8字符截断导致碰撞概率不可忽略（约 2^32 空间），生产环境建议完整UUID |
| `get_messages` 中 tags 参数可能导致慢查询 | 🟡 性能 | 多个 tag 过滤产生多个 LIKE 条件，且无索引。大量消息时性能堪忧 |
| `archive_messages_after/from` 使用 `>` / `>=` | 🟢 正确 | 语义清晰 |

**未使用代码**（全项目搜索确认）:
- `archive_messages_after()` (L200) — 无外部调用点
- `archive_messages_from()` (L210) — 无外部调用点
- `unarchive_all()` (L220) — 无外部调用点

> 注：这些方法可能在工具 handler 中通过 registry 注册使用，但在当前代码库中未找到引用。若确实如此，属设计预留。

---

### 2.5 skills.py（263行）

**架构角色**: Markdown 技能文件加载、触发器匹配、上下文注入。

| 发现 | 严重度 | 描述 |
|------|--------|------|
| 双层缓存设计 | 🟢 正面 | 内存LRU(`_parse_cache`) + 磁盘快照(`.skills_cache.json`)，基于 mtime+size 做变更检测 |
| `_build_manifest()` 使用相对路径 | 🟢 正面 | 避免绝对路径污染快照文件 |
| 磁盘快照 manifest 校验 | 🟢 正面 | `_load_disk_snapshot` 中 `snapshot.get("manifest") != current_manifest` 精确检测文件变更 |
| `_parse_yamlish` 仅支持标量和列表 | 🟡 限制 | 不支持嵌套结构，注释行若无 `:` 会被跳过（L30-32: `if ":" not in stripped: continue`） |
| `match_skills` 大小写不敏感匹配 | 🟢 正面 | 但若 trigger 为空字符串，`"" in ui_lower` 始终为 True，会误匹配（当前 trigger 列表过滤了空串） |
| `_parse_skill` 中 `triggers` 字段兼容 `trigger`/`triggers` 两种写法 | 🟢 正面 | 向后兼容性好 |
| `_parse_skill` 重复调用 `Path(path).stat()` | 🟡 性能 | L168-169: 在已有 stat 的情况下（来自 `_load_skill_file`），又调用一次 stat |
| `_parse_cache` 的 key 不包含文件路径规范化 | 🟡 注意 | 同一文件通过不同路径（如 `./skills/foo.md` vs 绝对路径）会产生两个缓存条目 |
| `_parse_skill` 重复调用 `Path(path).stat()` | 🟡 性能 | L168-169: `_mtime`/`_size` 使用了额外的 stat 调用，而 `_load_skill_file` 已做过 stat |

**未使用代码**: 无

---

### 2.6 loop.py（99行）

**架构角色**: 协议无关的核心对话循环 — tool-use loop。

| 发现 | 严重度 | 描述 |
|------|--------|------|
| 协议无关设计 | 🟢 正面 | 不分支 provider，所有格式差异由 `protocol` 对象处理 |
| `_trim_messages` 原地修改调用方列表 | 🟡 设计 | L23: `del messages[i:j]` — 直接修改传入的列表引用，调用方的 messages 被静默截断。虽然当前用法正确（main.py 中 messages 就是待修改的会话历史），但缺乏文档说明且容易引发调用方 bug |
| `_trim_messages` 截断逻辑 | 🟡 设计 | 使用 `max_len=60` 硬编码默认值，但调用方传 `max_ctx`（来自 `agent.max_context_messages=90`）——值合理但默认值不一致 |
| Tool 调用无错误恢复 | 🟡 健壮性 | L83: `tool_result = registry.call(...)` — 即使返回 `"Error: ..."` 字符串，也继续传给 LLM。无重试/降级/指数退避 |
| 同时维护 `messages` 和 `api_msgs` 两套列表 | 🟡 复杂度 | `messages`（内部格式）和 `api_msgs`（API格式）需手动同步，容易不一致。截断时调 `_trim_messages(messages)` 后重建 `api_msgs`，说明存在耦合 |
| `for _ in range(max_iters)` | 🟢 正确 | 有明确的迭代上限 |
| max_iterations 耗尽处理 | 🟢 正确 | 返回 `"(reached max iterations)"` 信号字符串 |

**未使用代码**: 无

---

### 2.7 main.py（770行）

**架构角色**: CLI 入口、交互式会话、Deck 采购编排。

| 发现 | 严重度 | 描述 |
|------|--------|------|
| **Deck 合并破坏工具顺序** | 🟡 设计 | L519-522: `merged_tools = set(deck.tools) \| base_tools` → Python `set` 无序，再构造 `Deck(list(merged_tools), registry)` 丢失了 `build_deck()` 精心维护的工具优先级顺序 |
| `open(path)` 未指定 encoding | 🟡 正确性 | L68: `open(path)` 依赖系统 locale；L152: `open(path, "w")` 同样。应在所有文件I/O处显式指定 `encoding="utf-8"` |
| 模块级全局变量控制 cron 线程 | 🟡 线程安全 | L39-40: `_tick_stop`, `_tick_thread` — 全局状态意味着同一进程不能运行多个会话，也使得测试困难 |
| `from cron import scheduler` 依赖包安装 | 🟡 可移植性 | cron 是独立 top-level 包（非 worker_bee 子包），需通过 pyproject.toml 的 packages 列表安装后才能导入。`cli.py` 有 `sys.path.insert` 修补但 `main.py` 没有 |
| `/tasks` 命令标记废弃但未移除 | 🟢 兼容 | L483-485: 打印警告引导用户使用 `/todo` |
| Skill authoring 上下文注入后未恢复 | 🟢 正确 | L563-565: finally 块中恢复 system_prompt |
| `_make_handoff` 字符串截断粗糙 | 🟡 数据质量 | L672-674: 硬截断 200 字符，可能在多字节字符（中文）边界截断 |
| config 中 `tools` 列表与 Deck 冗余 | 🟡 设计 | config.tools 定义了基础工具列表，Deck 也有 BASELINE_POOL，两者在 L519 合并——职责重叠 |
| `run_session` 函数过长 | 🟡 可维护性 | ~170行单一函数，建议拆分为 `_init_session()`, `_interactive_loop()`, `_teardown_session()` |

**未使用代码**: 无

---

### 2.8 protocols.py（253行）

**架构角色**: Anthropic/OpenAI 协议差异隔离。

| 发现 | 严重度 | 描述 |
|------|--------|------|
| Protocol 基类 `api_call` 签名无 `temperature` | 🟡 接口 | 基类 L51-53: `api_call(self, system_prompt, api_msgs, tools, model)` 无 temperature 参数；子类 L146/242 有 `temperature: float = 0.0`。loop.py L58-61 调用时传了 temperature，靠鸭子类型工作 |
| OpenAI `build_response` 中 `json.loads` 可能抛异常 | 🟡 健壮性 | L215: `json.loads(tc.function.arguments)` — 如果模型返回非标准 JSON 会崩溃。Anthropic 侧用 `_normalize_args` 则不会 |
| `_normalize_args` 只处理 dict 和 pydantic | 🟡 局限 | 对于 list/str 等类型的 input 会返回 `{}`，可能丢失数据 |
| Anthropic `max_tokens` 硬编码 4096 | 🟡 限制 | L150: 大输出场景可能不够，应可配置 |
| `Protocol.create` 静态工厂方法 | 🟢 正面 | 但代码中 `agent.py` 用 if/else 判断而非此工厂 |
| 两套协议实现完整且对称 | 🟢 正面 | Anthropic 用 content blocks，OpenAI 用 tool_calls 格式，转换逻辑清晰 |
| OpenAI `reasoning_content` 有回退读取 | 🟢 正面 | L219-220: `model_extra.get("reasoning_content")` 兼容多种 SDK 版本 |

**未使用代码**: `Protocol.create()` (L26-31) — 工厂方法定义了但 agent.py 未使用（改用 if/else 判断）

---

### 2.9 workspace.py（24行）

**架构角色**: 工作区路径单一真相源。

| 发现 | 严重度 | 描述 |
|------|--------|------|
| 简洁明确 | 🟢 正面 | 24行完成单一职责 |
| 环境变量解析 + expanduser + resolve | 🟢 正确 | 阻止 `~` 注入和符号链接绕过 |
| 默认路径自动创建 | 🟢 正面 | `default.mkdir(parents=True, exist_ok=True)` |
| 无路径穿越风险 | 🟢 安全 | `resolve()` 消除 `..` 组件 |

**未使用代码**: 无

---

### 2.10 infra_toolsets.py（52行）

**架构角色**: 平台基础设施工具集 — 当前仅 linux 桩。

| 发现 | 严重度 | 描述 |
|------|--------|------|
| 当前实现为纯桩 | 🟡 设计 | `detect_platform()` 和 `platform` property 永远返回 `"linux"`，`get_available_tools()` 返回 `[]`，`is_tool_available()` 永远返回 `True`。这是设计占位，等待多平台支持 |
| `__init__` 空实现 | 🟡 冗余 | L16-17: `def __init__(self): pass` — 可省略 |
| `invalidate()` 空实现 | 🟡 冗余 | L46-48: 方法声明 cache invalidation 但无 cache |

**未使用代码**:
- 模块级单例 `infra` (L52) — 全项目无导入引用。main.py 自己创建 `InfraToolSet()` 实例。

---

## 三、跨文件问题汇总

### 🔴 严重 (Critical)
*（无发现 — 所有已识别问题均有缓解因素或非必然触发）*

### 🟡 高优先级 (High)

| # | 问题 | 涉及文件 | 影响 |
|---|------|----------|------|
| 1 | **Deck 合并破坏工具顺序** | main.py:519-522, deck.py | set 去重导致工具列表无序，Deck 精心维护的优先级丢失 |
| 2 | **memory.py tag LIKE 注入面** | memory.py:159-161 | 虽当前 tag 来源受限（`#word` 解析），但防御深度不足 |
| 3 | **Protocol.api_call 签名不一致** | protocols.py:51-53 vs 146/242 | 基类缺少 temperature 参数，依赖鸭子类型 |
| 4 | **未使用代码积累** | registry.py, infra_toolsets.py, memory.py, protocols.py | `snapshot()`, `infra` 单例, `archive_*`, `Protocol.create` |

### 🟡 中优先级 (Medium)

| # | 问题 | 涉及文件 | 影响 |
|---|------|----------|------|
| 5 | **_trim_messages 修改调用方列表** | loop.py:23 | 副作用可能引发难以调试的 bug |
| 6 | **open() 未指定编码** | main.py:68 | 非 UTF-8 系统上行为不确定 |
| 7 | **Tool 调用无错误恢复机制** | loop.py:83 | 工具失败直接传给 LLM，无重试/降级 |
| 8 | **模块级全局 cron 状态** | main.py:39-40 | 不可测试、不可并发、不可多会话 |
| 9 | **`create_session` UUID 8字符截断** | memory.py:97 | 碰撞概率不可忽略 |

### 🟢 低优先级 / 备注 (Low/Info)

| # | 问题 | 涉及文件 |
|---|------|----------|
| 10 | InfraToolSet 为纯桩实现 | infra_toolsets.py |
| 11 | skills._parse_skill 重复 stat 调用 | skills.py:168-169 |
| 12 | loop.py 同时维护两套消息列表增加维护成本 | loop.py |
| 13 | `_make_handoff` 多字节字符边界截断 | main.py:672-674 |
| 14 | `run_session` 函数过长 (>170行) | main.py |
| 15 | Deck 与 agent._build_tools 的 OpenAI 转换逻辑重复 | deck.py:59-70 vs agent.py:92-101 |

---

## 四、安全评估

### 4.1 路径穿越
- `workspace.py`: `Path(env).expanduser().resolve()` ✅ 防护充分
- `memory.py export_handoff()`: 限定在 `~/.worker-bee/handoffs/` ✅ 安全
- `agent._load_prompt_files()`: 硬编码路径 ✅ 不可利用
- **结论**: 路径穿越风险低

### 4.2 命令注入
- `registry.call()` dispatch 到 handler 时传递 LLM 返回的参数 — 风险在 handler 层而非 registry
- 主循环中无直接 shell 拼接
- **结论**: registry 层无命令注入，handler 层需独立审计

### 4.3 SQL 注入
- `memory.py` tag LIKE 查询: 参数化查询 + 手动 LIKE 拼接 (L159-161) — 🟡 低风险但防御不足
- 其他查询均使用 `?` 占位符 ✅
- **结论**: 主流程安全，tag 过滤边界有微弱注入面

### 4.4 信息泄露
- `registry.call()` 错误信息包含异常详情 ✅ 设计意图（帮助 LLM 调试）
- config 中 `api_key` 在 `/config show` 时部分掩码 ✅
- **结论**: 风险可控

---

## 五、架构评价

### 优点
1. **分层清晰**: agent(薄壳) → loop(循环) → protocol(格式) → registry(执行)，每层职责单一
2. **Protocol 抽象干净**: 真正的提供者无关循环，添加新协议只需实现 Protocol 子类
3. **Deck 概念优秀**: 不可变工具边界，Skill → Deck 的采购模型直观
4. **缓存策略成熟**: registry 用 generation 计数器、skills 用 mtime+size 清单
5. **向后兼容考虑周全**: agent.py 保留了大量转发方法供测试使用

### 改进方向
1. **Deck 合并逻辑**: 保持顺序的去重而非 set 打散
2. **错误恢复**: loop 中增加工具调用重试/降级机制
3. **配置收敛**: config.tools 与 BASELINE_POOL 的职责重叠
4. **测试性**: 全局 cron 状态应改为实例或上下文管理
5. **代码清理**: 移除确认无用的 `snapshot()`, `infra` 单例, `archive_*` 方法
6. **Protocol 签名统一**: 基类 api_call 应与子类签名一致

---

## 六、测试覆盖情况（参考）

| 模块 | 测试文件 | 备注 |
|------|----------|------|
| registry | tests/test_registry.py | `list_by_category`, `get_tool_info` 等有覆盖 |
| memory | tests/test_memory.py | `list_open_sessions` 等有覆盖 |
| agent | tests/test_agent.py | 通过 conftest 集成测试 |
| deck | 未找到专属测试 | — |
| skills | 未找到专属测试 | — |
| loop | 未找到专属测试 | — |
| protocols | 未找到专属测试 | — |

> `snapshot()` 仅在 test_registry.py 中有测试覆盖，生产代码无调用点。

---

*报告结束*
