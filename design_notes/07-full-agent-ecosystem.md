# 蜂群职能总结

---

## Bee 全表

| Bee | 设计文档 | 层级 | 一句话 |
|-----|---------|------|--------|
| **Strategic Bee** | `08-strategic-bee.md` | 战略 | 搜索全地形，锁定有意义的目标 |
| **Cardmaster Bee** | `09-cardmaster-bee.md` | 战役 | 总指挥室，回合制选动作 |
| **Commander Bee** | `05-commander-bee.md` | 前线 | 创造性利用菜谱，缺信息回头要 |
| **Chef Bee** | `03-project-manager-bee.md` | 战术 | 主厨，写大阶段+菜谱级 task（原 Commander Bee） |
| **Verification Bee** | `04-verification-bee.md` | 战术 | 真实物理引擎，事实验证+证据链 |
| **Aristotle Bee** | `01-aristotle-bee.md` | 基础设施 | Strategic 辅助——术语定义+归档 |
| **Skeleton Bee** | `02-architecture-bee.md` | 基础设施 | Strategic 辅助——画架构骨架 |
| **Worker Bee** | 核心框架 | 执行 | 唯一 LLM 自由层，取 task 执行 |

---

## 架构总览

```
                  ┌─ Aristotle Bee（术语）
基础设施 ─────────┤
                  └─ Skeleton Bee（骨架）
                        ▲
                        │ Strategic Bee 调用
                        │
战略  Strategic Bee     搜索 + 锁定目标
       │
战役  Cardmaster Bee    总指挥室，回合制选动作
       │
前线  Commander Bee     创造性利用菜谱，缺信息喊 Chef
       │
战术  Chef Bee ──▶ Worker Bees ──▶ Verification Bee
      写菜谱         执行             物理引擎验证
       │                                │
       └────────────────────────────────┘
              验证数据回流 → Strategic 终极报告 → 人
```

**Aristotle Bee + Skeleton Bee = Strategic Bee 的辅助基础设施。**
两者都是长程静默——不在执行管道中。Strategic Bee 在搜索+锁定时调用它们辅助（术语定义、结构骨架），平时不说话。

---

## Strategic Bee — 搜索+锁定

**层级**: 战略。只管两件事：**搜索全地形**和**锁定有意义的目标**。Aristotle 和 Skeleton 是其辅助基础设施。

- **核心矛盾**: 饱和式覆盖 vs 边界精确。先精确划边界（排除法，"不做"比"做"重要），再在边界内穷举
- **上游**: 领域地图 + 信息源清单 + 初始假设 → `strategic-brief.md`
- **下游**: Verification 数据回流 → 起草结论 → **等人审阅确认**
- **8 skill**: boundary-define → domain-map → source-inventory → hypothesis-seed → evidence-synthesize → conclusion-draft → human-review → strategic-report

---

## Cardmaster Bee — 总指挥室

**层级**: 战役。识别战役走势，确认战役目标，卡牌化战术讨论。

- **四象限**: 说服（人→report）、交易（人→demo）、生产（事→pipeline）、研究（事→standard）
- **回合制**: 抽卡 → 标的物规格书 → 调度蜂群 → 结算成功率
- **失败螺旋**: report 不好→补研究。demo 不好→补生产。不倒退，螺旋上升
- **6 skill**: action-select → target-profile → spec-generate → spec-dispatch → quality-evaluate → retro-analyze

---

## Commander Bee — 前线小队长

**层级**: 前线。创造性利用 Chef 的菜谱。缺信息喊，不等完美。

- **缺信息就喊**: gap-assess → 向 Chef 发补充请求。不硬撑，不自编
- **偏差可接受就放行**: 不影响下游就放行，不等完美
- **升级给 Cardmaster**: 重试耗尽 → escalate。不越级找 Strategic
- **7 skill**: plan-ingest → gap-assess → task-batch → task-dispatch → progress-monitor → result-recover → escalate

---

## Chef Bee — 主厨

**层级**: 战术。写大阶段 + 菜谱级 task。先过饱和，再管交付。

- **双重角色**: 行动计划生成器（GOAL→PLAN）+ 交付触发器（边际收益探测）
- **9 字段 task**: Input/Output/时间/资源/人员/前置/阻塞项/容错/完成标准——精确到文件路径、分钟、工具名
- **决策锁**: PLAN.md 写入 LOCKED，解锁需明确触发条件
- **12 skill**: 仅 task-recipe 必需 LLM，其余 11 个纯规则

---

## Verification Bee — 物理引擎

**层级**: 战术。真实物理引擎——事实校验 + 证据链。以后可能接 world model。

- **双重防线**: 免疫过滤（逐 claim 校验→通过/驳回/重试）+ 证据链（交叉验证→三角验证→拼凑）
- **14 步细碎流水线**: 接收→校验→交叉验证→汇总。后期可合并为 6 步
- **回报 Strategic**: 验证数据+证据链+新假设

---

## Aristotle Bee + Skeleton Bee — 基础设施

**层级**: 基础设施。长程静默。Strategic Bee 调用它们辅助工作，平时不说话。

| | Aristotle Bee | Skeleton Bee |
|---|---|---|
| **给 Strategic 提供什么** | 术语的语境化定义、漂移检测 | 架构骨架、规约到不可规约的核心 |
| **何时激活** | 人问术语 / 项目归档 / Strategic 调用 | Strategic 调用来画骨架 |
| **产出** | `dict/<project>.md` | 5 阶段接力文件 |

---

## Worker Bee — 执行蜂

**层级**: 执行。唯一 LLM 自由层。取 task → 读 recipe → 调工具 → 写交付物。三层围栏（Deck/Git/进程隔离）。

---

## 协作闭环

```
人（模糊目标）
  → Strategic（搜索+锁定，调用 Aristotle+Skeleton 辅助）→ strategic-brief.md
    → Cardmaster（选动作）→ 标的物规格书
      → Chef（写菜谱）→ PLAN.md
        → Commander（创造性执行，缺信息喊）→ Job Board
          → Worker（执行）→ 交付物
            → Verification（物理引擎验证）→ 验证数据+证据链
              → Strategic（终极报告）→ 人审阅 ✓
```
