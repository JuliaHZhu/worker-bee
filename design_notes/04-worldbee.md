# WorldBee — 环境引擎

> *蜜蜂在花园里采蜜，但花园有气候、有花期、有土壤数据。WorldBee 就是那个花园。*

## 问题

Bees 干活的时候，它们说的话可能只是"逻辑自洽"，但不一定符合现实：

- Architecture Bee 说"这个算法是 O(n²)，够用了"
  - 但现实中 n 通常 > 10000，O(n²) 会让用户等 30 秒
- PM Bee 说"玩家会喜欢这种战斗节奏"
  - 但 A/B 测试数据显示这种节奏留存率只有 15%
- Aristotle Bee 说"沉浸感 = 心流"
  - 但用户调研里 80% 的人把沉浸感理解为"感官包裹"

**Bees 擅长推理，但不掌握"环境数据"。**

## 第一原理

**推理必须被现实检验。** 再好的逻辑，如果跟数据矛盾，就是错的。

WorldBee 不做具体任务，它只做一件事：**当 bee 的判断跟环境数据矛盾时，提醒它。**

## 行为

1. **被动检查** — 人不主动问，WorldBee 不说话
2. **数据优先** — 用 `worldbee/data/` 里的数据集说话，不用"我觉得"
3. **模型约束** — 用 `worldbee/models/` 里的数学/统计模型验证
4. **规则红线** — 用 `worldbee/rules/` 里的硬约束拦停

### 检查流程

```
Bee 提交一个判断（比如"O(n²) 够用"）
    │
    ▼
WorldBee 查三个东西：
  1. 数据：实际 n 的分布？历史运行记录？
  2. 模型：根据公式，n=10000 时耗时多少？
  3. 规则：有没有硬约束（比如"必须 < 1秒"）？
    │
    ▼
如果矛盾 → 提醒："根据数据集 X，n 中位数 15000，O(n²) 需要 45 秒，超出规则 Y 的 1 秒上限"
如果不矛盾 → 不说话（沉默即同意）
```

## 外源信息素格式

### 1. 数据集

路径：`worldbee/data/<dataset>.md`

```markdown
# Dataset: player_retention

## Source
2024 年 Q1-Q3 所有战斗节奏 A/B 测试数据

## Schema
| Field | Type | Description |
|-------|------|-------------|
| rhythm_type | string | 战斗节奏类型 |
| retention_d7 | float | 7 日留存率 |
| avg_session_sec | int | 平均会话时长（秒） |

## Key Findings
- 快节奏（< 2秒/回合）：留存率 12%
- 中节奏（2-5秒/回合）：留存率 34% ← 最优
- 慢节奏（> 5秒/回合）：留存率 28%

## Raw Data
见 `worldbee/data/player_retention.csv`
```

### 2. 模型

路径：`worldbee/models/<model>.md`

```markdown
# Model: combat_time_complexity

## Formula
T(n, e) = n² × e + n × log(n)

## Parameters
- n = 地图网格边长
- e = 实体数量

## Benchmarks
| n | e | T (ms) | Hardware |
|---|---|--------|----------|
| 50 | 20 | 12 | 2015 笔记本 |
| 100 | 50 | 89 | 2015 笔记本 |
| 200 | 100 | 720 | 2015 笔记本 |

## Rule
T(n, e) < 1000ms（1 秒红线）
```

### 3. 规则

路径：`worldbee/rules/<rule>.md`

```markdown
# Rule: performance_redline

## Constraints
- 任何操作必须 < 1 秒（2015 笔记本）
- 内存占用必须 < 512MB
- 启动时间必须 < 3 秒

## Source
产品需求文档 v2.3 + 硬件兼容性承诺
```

## 提醒格式

```
[WorldBee Check] Architecture Bee 说的"这个算法是 O(n²)，够用了"

检查结果：
- 数据：历史运行中 n 中位数 = 15000
- 模型：O(n²) 在 n=15000 时需要 45 秒
- 规则：性能红线要求 < 1 秒

结论：❌ 矛盾。建议改用 O(n log n) 或增加分页。
```

## Skill 契约

见 `worker_bee/skills/worldbee.md`

## 为什么能用

- WorldBee 不替代 bee 的推理，只**补充现实维度**
- 数据、模型、规则都是**人维护**的，LLM 只负责比对
- 沉默即同意 — 不矛盾时不说话，不干扰
- 所有判断都有**可追溯来源**（哪个数据集、哪个模型、哪条规则）

## 使用场景

- 游戏设计：用真实玩家数据验证"好玩"的假设
- 研究项目：用统计模型验证"显著"的结论
- 工程决策：用性能基准验证"够用"的估计
- 任何"逻辑自洽但可能不符合现实"的场景

## 与 Bees 的关系

| 角色 | 做什么 | 依据 |
|------|--------|------|
| Bee | 推理、设计、计划 | 逻辑、经验、skill 协议 |
| WorldBee | 现实检查 | 数据、模型、规则 |

**Bee 是建筑师，WorldBee 是地质勘探队。** 建筑师可以画任何设计，但地质队会告诉你"这里地基不稳"。
