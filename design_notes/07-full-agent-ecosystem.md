# 蜂群全貌 — 设计文档索引

> 战略 → 战役 → 战术。四层分明。

---

## Bee 清单

| # | Bee | 设计文档 | 状态 | 核心 |
|---|-----|---------|------|------|
| 1 | **Scout Bee** | `08-scout-bee.md` | v1.0 | 搜索 + 锁定有意义的目标。饱和覆盖 + 边界精确 |
| 2 | **Cardmaster Bee** | `09-cardmaster-bee.md` | v2.0 | 战役总指挥室。识别战役走势，确认战役目标，卡牌化战术讨论 |
| 3 | **Commander Bee** | (待独立设计) | 设计中 | 前线小队长。拿到 Chef 的菜谱后创造性执行，信息不足主动要 |
| 4 | **Chef Bee** | `03-project-manager-bee.md` | v3.0 | 主厨。大阶段 + 菜谱级 task，过饱和展开 |
| 5 | **Skeleton Bee** | `02-architecture-bee.md` | 稳定 | 骨架蜂。5 阶段流水线：意图→骨架→复杂度 |
| 6 | **Verification Bee** | `04-worldbee.md` | v2.0 | 真实物理引擎。事实校验 + 证据链。安装引擎类 tools |
| 7 | **Aristotle Bee** | `01-aristotle-bee.md` | 稳定 | 术语定义+归档。项目运行中完全静默 |
| — | **Worker Bee** | (核心框架) | 运行中 | LLM 自由执行层 |

---

## 四层架构

```
战略层 — 搜索 + 锁定目标
  Scout Bee（搜索全地形 → 锁定有意义的目标 → 终极报告）
    │ strategic-brief.md
    ▼
战役层 — 识别走势 + 确认目标
  Cardmaster Bee（战役总指挥室：选动作、定回合、卡牌化讨论）
    │ 标的物规格书
    ▼
前线层 — 创造性执行
  Commander Bee（拿到菜谱 → 创造性利用 → 信息不足主动向 Chef 要）
    │ Job Board
    ▼
战术层 — 生产 + 验证
  Chef Bee ──▶ Skeleton Bee ──▶ Worker Bees ──▶ Verification Bee
  （写菜谱）    （画骨架）        （执行）          （物理引擎验证）
    │                                                   │
    │                                         验证数据+证据链
    │                                                   │
    └───────────────────────────────────────────────────┘
                                                        │
                                                        ▼
                                                  Scout Bee（终极报告）
                                                        │
                                                        ▼
                                                       人
```

**Aristotle Bee** — 贯穿全程，完全静默。只在人主动问术语或归档时激活。

---

## 四层职责

| 层级 | Bee | 管什么 | 核心能力 |
|------|-----|--------|---------|
| **战略** | Scout Bee | 搜索全地形，锁定有意义的目标 | 饱和覆盖 + 边界精确 |
| **战役** | Cardmaster Bee | 识别战役走势，确认具体目标，卡牌化讨论 | 4 象限动作引擎 |
| **前线** | Commander Bee | 拿到菜谱创造性执行，信息不足主动要 | 有效利用 + 主动应变 |
| **战术** | Chef + Skeleton + Worker + Verification | 生产菜谱、画骨架、执行、物理验证 | 菜谱级精确 + 真实物理引擎 |

---

## 协作流程

1. Scout 搜索 + 锁定目标 → `strategic-brief.md`
2. Cardmaster 识别走势 + 选动作 → 标的物规格书
3. Commander 拿 Chef 的菜谱创造性执行 → 派发 Job → 信息不足回头要
4. Chef 拆菜谱（大阶段 + 精确 task）→ Skeleton 画骨架 → Worker 执行 → Verification 验证
5. Verification 验证数据回流 → Scout 出终极报告 → 人审阅

---

## 命名对照

| 旧名 | 新名 | 改名理由 |
|------|------|---------|
| Strategic Bee | **Scout Bee** | 核心是"搜索"+"锁定目标"，不是泛泛的"战略" |
| PM Bee | **Chef Bee** | 写菜谱的，具体好玩 |
| Architecture Bee | **Skeleton Bee** | 画骨架的，具体好玩 |
| World Bee | **Verification Bee** | 真实物理引擎，不是"环境"是"验证" |
