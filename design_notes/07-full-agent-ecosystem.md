# 蜂群全貌 — 设计文档索引

> 战略 → 战役 → 战术。三层分明。

---

## Bee 清单

| # | Bee | 设计文档 | 状态 | 核心 |
|---|-----|---------|------|------|
| 1 | **Aristotle Bee** | `01-aristotle-bee.md` | 稳定 | 术语定义+归档。项目运行中完全静默 |
| 2 | **Architecture Bee** | `02-architecture-bee.md` | 稳定 | 5 阶段流水线：意图→骨架→复杂度 |
| 3 | **PM Bee** | `03-project-manager-bee.md` | v3.0 | 12 skill：行动计划生成 + 交付触发 |
| 4 | **World Bee** | `04-worldbee.md` | v2.0 | 14 步免疫过滤 + 证据链引擎 |
| 5 | **Strategic Bee** | `08-strategic-bee.md` | v1.0 | 战略统合：边界定义+饱和覆盖+终极报告 |
| 6 | **Cardmaster Bee** | `09-cardmaster-bee.md` | v2.0 | 战役总指挥室：4 象限回合制动作引擎 |
| — | **Commander Bee** | (整合在 PM/Cardmaster 中) | 设计中 | 前线小队长：派发任务+回收结果 |
| — | **Worker Bee** | (核心框架) | 运行中 | LLM 自由执行层 |

---

## 四层架构

```
战略层 — 管方向对不对
  Strategic Bee（边界定义 + 领域地图 + 终极报告）
    │ strategic-brief.md
    ▼
战役层 — 管这仗怎么打
  Cardmaster Bee（总指挥室：选动作、定回合、写标的物规格书）
    │ 标的物规格书
    ▼
战术层 — 管怎么执行
  Commander Bee（前线小队长：拆任务、派发 Job、回收结果）
    │ Job Board
    ▼
  PM Bee ──▶ Architecture Bee ──▶ Worker Bees ──▶ World Bee
  （拆菜谱）   （画骨架）          （执行）         （验证）
    │                                                   │
    │                                         验证数据+证据链
    │                                                   │
    └───────────────────────────────────────────────────┘
                                                        │
                                                        ▼
                                               Strategic Bee（终极报告）
                                                        │
                                                        ▼
                                                       人
```

**Aristotle Bee** — 贯穿全程，完全静默。只在人主动问术语或归档时激活。

---

## 四层职责

| 层级 | Bee | 管什么 | 标准 |
|------|-----|--------|------|
| **战略** | Strategic Bee | 方向对不对 | 正确（饱和覆盖+边界精确） |
| **战役** | Cardmaster Bee | 这仗怎么打 | 标的物质量（report/demo/pipeline/standard） |
| **前线** | Commander Bee | 任务到不到位 | 派发+回收闭环 |
| **战术** | PM + Arch + Worker + World | 怎么做最有效 | 菜谱级精确+验证闭环 |

---

## 协作流程

1. Strategic 定方向（领域地图 + 假设）→ `strategic-brief.md`
2. Cardmaster 选动作（说服/交易/生产/研究）→ 标的物规格书
3. Commander 拆任务 → 派发到 Job Board
4. PM 拆菜谱 → PLAN.md → Worker 执行 → World 验证
5. World 验证数据回流 → Strategic 出终极报告 → 人审阅

---

## 设计原则

1. **文件接力** — Bee 之间不传内存对象，只传文件
2. **消费者驱动** — 先定义"谁用这个产出"，再定义怎么产
3. **纯规则优先** — 能用规则就不用 LLM
4. **过饱和展开** — 计划阶段宁可冗余，执行阶段不回头补
5. **回滚成本最小化** — 流程切细碎，错只回滚一步
