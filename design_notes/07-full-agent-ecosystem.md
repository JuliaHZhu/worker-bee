# 蜂群全貌 — 设计文档索引

> 每个 Bee 一份设计文档。不搞抽象理论层。设计文档自带文件格式。

---

## Bee 清单

| # | Bee | 设计文档 | 状态 | 核心 |
|---|-----|---------|------|------|
| 1 | **Aristotle Bee** | `01-aristotle-bee.md` | 稳定 | 术语语境化管理，漂移检测 |
| 2 | **Architecture Bee** | `02-architecture-bee.md` | 稳定 | 5 阶段流水线：意图→骨架→复杂度 |
| 3 | **PM Bee** | `03-project-manager-bee.md` | v3.0 | 12 skill：行动计划生成 + 交付触发 |
| 4 | **World Bee** | `04-worldbee.md` | v2.0 | 14 步免疫过滤 + 证据链引擎 |
| 5 | **Cardmaster Bee** | `09-cardmaster-bee.md` | v2.0 | 4 象限回合制动作引擎 |
| — | **Worker Bee** | (核心框架，非设计文档) | 运行中 | LLM 自由执行层 |

---

## 蜂群协作

```
Cardmaster Bee（选动作：说服/交易/生产/研究）
    │
    │ 标的物规格书
    ▼
PM Bee（拆成菜谱级 task → PLAN.md）
    │
    │ PLAN.md
    ▼
Architecture Bee（如需设计流水线/标准结构）
    │
    │ 结构原型
    ▼
Worker Bees（执行 task → 产出交付物）
    │
    │ 交付物
    ▼
World Bee（事实校验 → 交叉验证 → 证据链）
    │
    │ 验证报告 + 新假设
    ▼
Strategic Bee / Cardmaster Bee（下一回合决策）

Aristotle Bee（贯穿全程：术语定义 + 漂移检测）
```

---

## 设计原则

1. **文件接力** — Bee 之间不传内存对象，只传文件。每个中间产物人可读、人可改。
2. **消费者驱动** — 每个 skill 先定义"谁用这个产出"，再定义怎么产。
3. **纯规则优先** — 能用规则就不用 LLM。LLM 只用于需要判断/创意的地方。
4. **过饱和展开** — 计划阶段宁可信息冗余，执行阶段不回头补信息。
5. **回滚成本最小化** — 流程切细碎，每步错只回滚那一步。

---

## 已删除的设计文档

以下文件已被后续版本取代，不再维护：

- `05-commander-worker-io.md` → Commander 概念整合进 PM Bee v3.0
- `06-worldbee-pheromone.md` → 信息素隐喻被 World Bee v2.0 显式文件格式取代
- `08-strategic-bee.md` → 太薄，重写时再建
- `beebox.md` → 认知轨迹笔记，非设计文档
- `exogenous-pheromone-formats.md` → 抽象理论层，每个 Bee 已自带文件格式
