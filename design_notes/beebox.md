# BeeBox 架构笔记

> 蜂群系统的设计思考——随分析积累，每次有新认知就追记。
> 不是设计文档，是认知轨迹。读的顺序不重要，每一段自包含。

---

## 2026-06-05: AGP 版本化 → Deck Snapshot 版本化

**触发**: 读 Autogenesis (AGP) 论文，喜欢其 RSPL 资源版本化 + rollback 的设计，但审视 worker-bee 现状后认为不该走中心化注册表路线。

**三个输入的合成**:

| 输入 | 内容 |
|------|------|
| AGP 的 RSPL | 五类资源（Prompt/Agent/Tool/Env/Mem）注册表 + version lineage + rollback |
| Worker-Bee 现状 | 专机专能 + 多机集群 + Deck 机制 |
| 黄超的判断 | agent 就是个 tool-calling loop |

**合成结论**: 版本化不需要 RSPL 那样的中心化注册表。Deck 本身就是一种轻量版本化机制——每个 atom 有来源、有标签、有归属轮次，一次 Deck snapshot 就是"那一时刻的知识版本"。专机专能的 agent 无状态，只管跑 tool-calling loop，状态在 Deck 和 NATS 消息里。

**版本化路径**: 不是加 RSPL，而是让 Deck 的 snapshot 机制更显式——
- 每次进化后自动记一个 Deck version
- 回滚 = 切 Deck snapshot
- agent 永远无状态，只读当前 Deck + 收 NATS 消息

---

## 2026-06-05: AEvo → WorldBee + Strategic Bee 双体联合

**触发**: 读 AEvo 论文，其核心是 meta-agent 编辑进化机制 Π，而非直接产生候选。

**映射**:
- **WorldBee** = AEvo 的 Harness 角色（状态观测 + 环境边界）
- **Strategic Bee** = AEvo 的 Meta-Agent 角色（机制编辑决策）

**与 AEvo 的关键差异**: AEvo 的 meta-agent 是单体的，Worker-Bee 是双体联合——观测和决策分开，各自独立演化和替换。更符合蜂群去中心化原则。

---

## 2026-06-05: 三篇论文的定位关系

| 维度 | AEvo | AGP | Worker-Bee |
|------|------|-----|------------|
| 性质 | 进化框架 | 协议规范 | 蜂群系统 |
| 资源模型 | 无统一抽象 | 五类资源 + 被动约束 | Skill/Tool/Agent 三类 |
| 版本控制 | Harness 内 candidate history | RSPL 原生 version lineage | Deck snapshot（无原生版本控制） |
| 进化机制 | Meta-agent 编辑 Π | SEPL 算子代数 | WorldBee + Strategic Bee 联合 |
| 安全模型 | Evaluator 隔离 | 每次变更版本化+可回滚 | safety.py + audit log |
| 通信模型 | 单机 harness | Bus 模型（AGS） | NATS + mailbox |

**Worker-Bee 的差异化**: 惯例驱动（非协议驱动），agent 极简（非胖 agent），一切皆 skill（非五类抽象），skill 接 tool 接死（非动态改写）。

---

## 2026-06-05: worker-bee 的"写死"是选择，不是缺失

AGP 和 AEvo 都假定"越可进化越好"。Worker-Bee 刻意在多个层级写死：

| 层级 | 写死的 | 可进化的 | 理由 |
|------|--------|---------|------|
| Tool | ✅ 写死 | — | 工具是基础设施，稳定 > 灵活 |
| Skill | — | ✅ Darwin Skill | 进化发生在技能层 |
| Agent | ✅ 写死（极简 loop） | — | 专机专能，换机不换 agent 逻辑 |
| 通信 | ✅ 写死（NATS） | — | 协议层稳定，内容层灵活 |
| 知识 | — | ✅ Deck atom + tag | 知识是唯一该持续进化的层 |

这和 AGP 的"所有五类资源都该可版本化"是对立的设计哲学。不是谁对谁错——是两条路。
