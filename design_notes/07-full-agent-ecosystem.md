# 蜂群职能总结

---

## Bee 全表

| Bee | 设计文档 | 层级 | 一句话 |
|-----|---------|------|--------|
| **Strategic Bee** | `08-strategic-bee.md` | 战略 | 搜索全地形，锁定有意义的目标 |
| **Cardmaster Bee** | `09-cardmaster-bee.md` | 战役 | 总指挥室，回合制选动作 |
| **Commander Bee** | `05-commander-bee.md` | 前线 | 创造性利用菜谱，缺信息回头要 |
| **Chef Bee** | `03-project-manager-bee.md` | 战术 | 主厨，写大阶段+菜谱级 task |
| **Skeleton Bee** | `02-architecture-bee.md` | 战术 | 画骨架，规约到不能规约 |
| **Verification Bee** | `04-verification-bee.md` | 战术 | 真实物理引擎，事实验证+证据链 |
| **Aristotle Bee** | `01-aristotle-bee.md` | 静默 | 术语定义+归档，运行中不说话 |
| **Worker Bee** | 核心框架 | 执行 | 唯一 LLM 自由层，取 task 执行 |

---

## 架构总览

```
战略  Strategic Bee     搜索 + 锁定目标
       │
战役  Cardmaster Bee    总指挥室，回合制选动作
       │
前线  Commander Bee     创造性利用菜谱，缺信息喊 Chef
       │
战术  Chef Bee ──▶ Skeleton Bee ──▶ Worker Bees ──▶ Verification Bee
      写菜谱         画骨架            执行             物理引擎验证
       │                                                   │
       └───────────────────────────────────────────────────┘
                      验证数据回流 → Strategic 终极报告 → 人
Aristotle Bee — 全程静默
```

---

## Strategic Bee — 搜索+锁定

**层级**: 战略。只管两件事：**搜索全地形**和**锁定有意义的目标**。

- **核心矛盾**: 饱和式覆盖 vs 边界精确。先精确划边界（用排除法，"不做"比"做"重要），再在边界内穷举信息源
- **上游**: 领域地图 + 信息源清单 + 初始假设（可验证的命题）→ `strategic-brief.md`
- **下游**: 把 Verification 的验证数据整合进领域框架 → 起草结论 → **等人审阅确认**
- **闭环**: 启动定方向 → 中间收数据 → 收尾出报告
- **8 skill**: boundary-define → domain-map → source-inventory → hypothesis-seed → evidence-synthesize → conclusion-draft → human-review → strategic-report
- **高度人工配合**: 边界定义要人确认，终极结论要人审阅

---

## Cardmaster Bee — 总指挥室

**层级**: 战役。站在战略方向和具体执行之间。**识别战役走势，确认战役目标，卡牌化战术讨论**。

- **四象限**: 说服（人→report）、交易（人→demo）、生产（事→pipeline）、研究（事→standard）
- **回合制**: 抽卡 → 标的物规格书 → 调度蜂群生产 → 结算成功率
- **失败螺旋**: report 不好 → 补研究。demo 不好 → 补生产。不倒退，螺旋上升
- **不执行**: 只写规格书，蜂群是工厂
- **4 种动作就够了**: 不加第五种，复杂度由卡组扩展
- **6 skill**: action-select → target-profile → spec-generate → spec-dispatch → quality-evaluate → retro-analyze

---

## Commander Bee — 前线小队长

**层级**: 前线。拿到 Chef 的菜谱后**创造性地利用它**。关键词：**有效利用**。

- **缺信息就喊**: gap-assess 发现缺口 → 向 Chef 发补充请求。不硬撑，不自己编
- **偏差可接受就放行**: result-recover 判断交付物和验收标准的差距——不影响下游就放行。不等完美
- **派发+回收**: 读 PLAN.md → 分批派发 Job → 回收结果
- **升级给 Cardmaster**: 重试耗尽 → escalate。不越级找 Strategic
- **7 skill**: plan-ingest → gap-assess → task-batch → task-dispatch → progress-monitor → result-recover → escalate

---

## Chef Bee — 主厨

**层级**: 战术。把目标变成**大阶段 + 菜谱级 task**。先过饱和，再管交付。

- **双重角色**: 行动计划生成器（GOAL → PLAN）+ 交付触发器（边际收益探测）
- **9 字段 task**: Input/Output/时间/资源/人员/前置/阻塞项/容错/完成标准——全精确到文件路径、分钟、工具名
- **决策锁**: PLAN.md 写入 LOCKED，执行阶段不讨论。解锁需明确触发条件
- **12 skill**: 只有 task-recipe 必需 LLM，其余 11 个纯规则

---

## Skeleton Bee — 骨架蜂

**层级**: 战术。从混沌意图逼出清晰骨架。**规约到不能规约**。

- **5 阶段**: capture-intent → decompose-goal → reduce-to-core（🔥灵魂，移除测试）→ expose-archetype → evaluate-complexity
- **文件接力**: 每阶段产出独立 md，人可中断/修改/续上
- **适用任何领域**: 软件/电影/书籍/游戏——同一条流水线

---

## Verification Bee — 物理引擎

**层级**: 战术。**真实物理引擎**——事实校验 + 证据链拼凑。以后可能接 world model。安装引擎类 tools。

- **双重防线**: 第一道（免疫过滤）：逐 claim 校验 → 通过/驳回/重试。第二道（证据链）：交叉验证 → 三角验证（3+ 源=high）→ 拼凑证据链
- **14 步细碎流水线**: 接收→校验→交叉验证→汇总。纯规则+LLM 混用
- **后期合并**: 14→6 步，相邻纯规则合并
- **重试闭环**: Worker 出错 → Verification 驳回 → Commander 重试（上限 3 次）
- **回报 Strategic**: 验证数据+证据链+新假设

---

## Aristotle Bee — 术语管家

**层级**: 静默。贯穿全程但**完全不主动说话**。

- **两种激活**: 人主动问术语 / 项目归档
- **词典**: `dict/<project>.md`，纯 markdown，人可改
- **与 Strategic 的区分**: Aristotle 静默归档。Strategic 活跃搜索+报告

---

## Worker Bee — 执行蜂

**层级**: 执行。唯一 LLM 自由层。

- **取 task → 读 recipe → 调工具 → 写交付物 → 报告状态**
- **三层围栏**: Deck / Git / 进程隔离
- **错误成本最低**: 幻觉了不 merge → Verification 驳回 → Commander 重试

---

## 协作闭环

```
人（模糊目标）
  → Strategic（搜索+锁定）→ strategic-brief.md
    → Cardmaster（选动作）→ 标的物规格书
      → Chef（写菜谱）→ PLAN.md
        → Commander（创造性执行，缺信息喊）→ Job Board
          → Skeleton（画骨架，如需）
            → Worker（执行）→ 交付物
              → Verification（物理引擎验证）→ 验证数据+证据链
                → Strategic（终极报告）→ 人审阅 ✓
Aristotle — 全程静默
```
