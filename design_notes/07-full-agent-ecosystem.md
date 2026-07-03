# 蜂群全貌 — 设计文档索引

> 每个 Bee 一份设计文档。不搞抽象理论层。设计文档自带文件格式。

---

## Bee 清单

| # | Bee | 设计文档 | 状态 | 核心 |
|---|-----|---------|------|------|
| 1 | **Aristotle Bee** | `01-aristotle-bee.md` | 稳定 | 术语定义+归档。项目运行中完全静默 |
| 2 | **Architecture Bee** | `02-architecture-bee.md` | 稳定 | 5 阶段流水线：意图→骨架→复杂度 |
| 3 | **PM Bee** | `03-project-manager-bee.md` | v3.0 | 12 skill：行动计划生成 + 交付触发 |
| 4 | **World Bee** | `04-worldbee.md` | v2.0 | 14 步免疫过滤 + 证据链引擎 |
| 5 | **Strategic Bee** | `08-strategic-bee.md` | v1.0 | 战略统合：边界定义+饱和覆盖+终极报告 |
| 6 | **Cardmaster Bee** | `09-cardmaster-bee.md` | v2.0 | 4 象限回合制动作引擎 |
| — | **Commander Bee** | (整合在 PM/Strategic 中) | 设计中 | 战役小队长：派发+协调 |
| — | **Worker Bee** | (核心框架) | 运行中 | LLM 自由执行层 |

---

## 蜂群协作

```
Strategic Bee（战略：边界 + 方向）
    │
    │ strategic-brief.md
    ▼
Commander Bee（战役：小队长，派发任务）
    │
    │ Job Board
    ▼
Cardmaster Bee → PM Bee → Architecture Bee
（选动作）     （拆菜谱）  （画骨架）
    │              │           │
    └──────────────┼───────────┘
                   │
                   ▼
            Worker Bees（执行）
                   │
                   ▼
            World Bee（验证）
                   │
                   ▼
            Strategic Bee（终极报告）
                   │
                   ▼
                  人（审阅确认）
```

**Aristotle Bee** 贯穿全程但完全静默——只在人主动问"这个术语什么意思"或项目归档时激活。

---

## 战略/战役/战术 三层

| 层级 | Bee | 管什么 | 标准 |
|------|-----|--------|------|
| **战略** | Strategic Bee | 方向对不对 | 正确（饱和覆盖+边界精确） |
| **战役** | Commander Bee | 执行到不到位 | 到位（任务派发+回收） |
| **战术** | PM + Cardmaster + Arch | 怎么做最有效 | 高效（菜谱级精确） |

---

## 设计原则

1. **文件接力** — Bee 之间不传内存对象，只传文件
2. **消费者驱动** — 先定义"谁用这个产出"，再定义怎么产
3. **纯规则优先** — 能用规则就不用 LLM
4. **过饱和展开** — 计划阶段宁可冗余，执行阶段不回头补
5. **回滚成本最小化** — 流程切细碎，错只回滚一步
