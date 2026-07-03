# 蜂群职能总结

---

## 架构总览

```
战略层  Strategic Bee  搜索 + 锁定目标
         │
战役层  Cardmaster Bee  总指挥室，选动作
         │
前线层  Commander Bee  创造性执行，缺信息主动要
         │
战术层  Chef Bee ──▶ Skeleton Bee ──▶ Worker Bees ──▶ Verification Bee
        写菜谱         画骨架            执行             物理引擎验证
         │                                                   │
         └───────────────────────────────────────────────────┘
                        验证数据回流 → Strategic Bee 终极报告 → 人
Aristotle Bee — 全程静默
```

---

## Strategic Bee — 搜索+锁定

**职能范围**: 战略层。只管两件事——**搜索全地形**和**锁定有意义的目标**。不参与执行。

**设计核心**:
- **核心矛盾**: 饱和式覆盖 vs 边界精确。先精确划定边界，再在边界内穷举所有信息源。用排除法定义边界——说清楚"不做"比"做"重要
- **上游产出**: 领域地图 + 信息源清单（饱和式）+ 初始假设（可验证的命题）
- **下游产出**: 终极报告——把 Verification Bee 的验证数据整合进领域框架，起草结论，**等人审阅确认**
- **上下游闭环**: 启动时定方向 → 收尾时出报告。中间定期接收 Verification 数据
- **8 个 skill**: boundary-define → domain-map → source-inventory → hypothesis-seed（上游）→ evidence-synthesize → conclusion-draft → human-review → strategic-report（下游）
- **高度人工配合**: 边界定义要人确认（ambiguous 项），终极结论要人审阅

---

## Cardmaster Bee — 战役总指挥室

**职能范围**: 战役层。站在 Strategic（战略方向）和 Chef/Commander（具体执行）之间。**识别战役走势，确认战役目标，用卡牌方式游戏化战术讨论**。

**设计核心**:
- **四象限动作矩阵**: 说服（人→标的物 report）、交易（人→标的物 demo）、生产（事→产品 pipeline）、研究（事→产品 standard）
- **回合制**: 每回合抽一张动作卡 → 生成标的物规格书 → 调度蜂群生产 → 结算成功率
- **失败螺旋上升**: report 不好 → 研究标准有问题。demo 不好 → 生产流水线有问题。不是倒退，是螺旋补课
- **不执行**: 只写规格书。蜂群是工厂，Cardmaster 是总指挥室
- **4 种动作就够了**: 不加第五种。复杂度由卡组扩展承载
- **6 个 skill**: action-select → target-profile → spec-generate → spec-dispatch → quality-evaluate → retro-analyze

---

## Commander Bee — 前线小队长

**职能范围**: 前线层。拿到 Chef Bee 的项目计划书后，**创造性地利用它**。不是被动执行——信息不足会主动向 Chef 要。关键词是**"有效利用"**。

**设计核心**:
- **创造性执行者**: 菜谱是死的，执行是活的。Commander 理解菜谱的意图，根据现场情况灵活调整
- **主动要信息**: 执行中缺什么，回头向 Chef Bee 要补充说明或更细的 task，不硬撑
- **派发+回收闭环**: 唯一能开 Issue 的角色。把计划书拆成 Job → 派发到 Job Board → 回收结果
- **不是规则引擎**: 不幻觉，但有判断力。判断"这个 task 现在能不能做"、"缺什么信息"
- **与 Chef Bee 的分工**: Chef 写菜谱（大阶段+精确 task），Commander 用菜谱（派发+协调+要补充）

---

## Chef Bee — 主厨

**职能范围**: 战术层。把目标变成**大阶段 + 菜谱级 task**。先过饱和展开，再管交付节奏。

**设计核心**:
- **双重角色**: 行动计划生成器（GOAL.md → PLAN.md）+ 交付触发器（边际收益探测，强制交付）
- **9 字段 task**: Input（精确到文件路径）、Output（精确到格式和存放位置）、时间（精确到分钟）、资源（具体工具名）、人员、前置（T-xxx 编号）、阻塞项（是/否+原因）、容错（至少一个可操作 fallback）、完成标准（可验证条件）
- **不可约分环节优先**: 先列"不做就完蛋"的最小步骤
- **过饱和展开**: 计划阶段不删信息，全部保留在 `_internal/`，审计可回溯
- **决策锁**: PLAN.md 写入后 LOCKED。执行阶段只执行不讨论。解锁需明确触发条件
- **12 个 skill**: 只有 task-recipe 必需 LLM，其余 11 个全是规则引擎
- **与 Commander 的关系**: Chef 产出 PLAN.md → Commander 拿来用 → 信息不足时 Commander 回头要

---

## Skeleton Bee — 骨架蜂

**职能范围**: 战术层。从混沌意图逼出清晰骨架。**规约到不能规约**。

**设计核心**:
- **5 阶段流水线**: capture-intent（冲动锚定）→ decompose-goal（目标展开+反目标）→ reduce-to-core（规约灵魂，移除测试）→ expose-archetype（原型暴露，正交基底检验）→ evaluate-complexity（Big O 资源量纲）
- **适用任何领域**: 软件/电影/书籍/游戏——任何需要骨架的东西
- **文件接力**: 每个阶段产出一个独立 markdown，人可在任意阶段中断、修改、再续上
- **Stage 3 是灵魂**: reduce-to-core——对每个子目标不断问"为什么"，直到答案变成"因为去掉它整个东西就不存在了"
- **不预设领域**: 同样的流水线，做软件架构和做电影叙事结构用的是同一套方法论

---

## Verification Bee — 物理引擎

**职能范围**: 战术层。**真实物理引擎**——事实校验 + 证据链拼凑。以后可能接 world model。安装引擎类 tools。

**设计核心**:
- **双重防线**: 第一道（免疫过滤）：逐个 claim 校验事实 → 通过/驳回/重试。第二道（证据链）：交叉验证 → 三角验证（3+ 源 = high 置信度）→ 拼凑证据链
- **14 步细碎流水线**: 阶段 0（接收标准化）→ 阶段 1（事实校验 4 步）→ 阶段 2（交叉验证 4 步）→ 阶段 3（汇总假设 4 步）。纯规则 + LLM 混用
- **后期合并路径**: 14 步 → 6 步（相邻纯规则合并），跑通后提升流畅度
- **重试闭环**: Worker 出错 → Verification 驳回 → Commander 重试（上限 3 次）
- **回报 Strategic Bee**: 验证数据 + 证据链 + 新假设 → Strategic 做终极报告
- **引擎类 tools**: 不是"查数据库"——是跑模型、跑模拟、跑基准测试。类似物理引擎：输入数据 → 模拟运行 → 输出是否符合物理规律

---

## Aristotle Bee — 术语管家

**职能范围**: 静默层。贯穿全程但**完全不主动说话**。管术语定义和归档。

**设计核心**:
- **只在两种情况下激活**: 人主动问"这个术语什么意思"，或项目归档
- **核心行为**: 读到术语 → 查词典 → 有则注入语境 → 没有则问"具体指什么" → 有但语境不同则标注漂移
- **词典是外源信息素**: `~/.worker-bee/dict/<project>.md`，纯 markdown，人随时可改
- **不做百科全书**: 只记对话中实际出现的术语。不替用户发明定义。语境优先于字典定义
- **与 Strategic Bee 的区分**: Aristotle 是静默的档案管理员。Strategic 是活跃的搜索者+报告者

---

## Worker Bee — 执行蜂

**职能范围**: 战术层底层。唯一的 LLM 自由执行层。

**设计核心**:
- **取 task → 读 recipe → 调工具 → 写交付物 → 报告状态**
- **三层围栏**: Deck（可用工具列表）、Git（版本控制）、进程隔离
- **错误成本最低**: 幻觉了 → PR 不 merge → Verification 驳回 → Commander 重试
- **不主动通信**: 只接收 Commander（Job Board）和 Chef（PLAN.md），不主动和任何 Bee 对话

---

## 协作闭环

```
人（模糊目标）
  → Strategic（搜索+锁定）→ strategic-brief.md
    → Cardmaster（选动作）→ 标的物规格书
      → Chef（写菜谱）→ PLAN.md
        → Commander（创造性执行，缺信息回头要）→ Job Board
          → Skeleton（画骨架，如需）
            → Worker（执行）→ 交付物
              → Verification（物理引擎验证）→ 验证数据+证据链
                → Strategic（终极报告）→ 人审阅 ✓

Aristotle — 全程静默
```

**关键接口**:
- Strategic ↔ Cardmaster: strategic-brief.md（方向和边界）
- Cardmaster ↔ Chef: 标的物规格书（做什么）
- Chef ↔ Commander: PLAN.md（怎么一步步做）
- Commander ↔ Worker: Job Board（派发+回收）
- Worker ↔ Verification: 交付物（执行结果）
- Verification ↔ Strategic: 验证数据+证据链（真实物理引擎的输出）
