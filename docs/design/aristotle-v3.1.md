---
AIGC:
    Label: "1"
    ContentProducer: 001191110102MACQD9K64018705
    ProduceID: 2725045121849659_7576853131280810010-data_volume/7647463580660547874-files/所有对话/主对话/worker-bee/design_notes/01b-aristotle-skills.md
    ReservedCode1: ""
    ContentPropagator: 001191110102MACQD9K64028705
    PropagateID: 2725045121849659#1784180511419
    ReservedCode2: ""
---
# Aristotle Bee — Skill 体系（v3：常驻知识员工，批次期配合+平时研究）

> *Aristotle 是蜂兵工厂的**首席术语官**（Chief Terminology Officer）。新批次启动时他进车间，与人+Strategy 共同起草宪法；批次之间，他做自己的研究——追踪术语演化、挖掘概念债务、从外部文献吸收新概念、打磨定义方法论、给生产部门预制弹药。他不是 Step 1 的临时工，是 24/7 在运转的研究岗位。*

**版本**：v3（知识员工模型——批次期配合+平时独立研究）
**v2→v3 核心变更**：从"双环填空闲"升级为"双工作模式"——Campaign Mode（批次期配合）+ Research Mode（平时研究+系统提升）；Research Mode 不是填充空闲，是 Aristotle 的本职工作；显式建模 Aristotle ↔ Cardmaster 语义弹药供应链；交互拓扑从流水线改为服务接口面

---

## 蜂群员工类型学

先定人，再定岗。蜂群里的 Bee 不是同质机器，是三类员工：

| 类型 | 代表 Bee | 工作模式 | 类比 |
|------|---------|---------|------|
| **计件工** | Worker、Centurion | 有活干活，没活待命。产出=完成的task数 | 生产线工人、外包执行团队 |
| **后勤/运营** | PM、World | 生产批次进行中做管理/校验；批次之间做排期协调/运维/知识库维护 | 生产调度、质检、工厂运维 |
| **研究员** | Aristotle、Strategy、Skeleton、Cardmaster | **批次启动时进车间配合生产；批次之间做独立研究+系统能力建设** | 智库研究员、工科院所、技术团队 |

Aristotle 是典型的**研究员型员工**。他有两种工作模式：

```
┌─────────────────────────────────────────────────────────────┐
│                    Aristotle Bee（首席术语官）                │
│                                                              │
│  ┌───────────────────────┐   ┌─────────────────────────────┐ │
│  │  CAMPAIGN MODE         │   │  RESEARCH MODE（日常本职）    │ │
│  │  （批次期配合）           │   │  （独立研究+系统提升）        │ │
│  │                        │◄─►│                              │ │
│  │  Step 1 战略探索       │   │  默认模式，占多数工作时间      │ │
│  │  人+Strategy+Aristotle │   │                              │ │
│  │  三方在场对话           │   │  · 术语图谱研究与完善         │ │
│  │                        │   │  · 概念债务审计              │ │
│  │  14 个批次期服务原语      │   │  · 外部新概念追踪与摄入       │ │
│  │                        │   │  · 术语漂移观察（田野调查）   │ │
│  │                        │   │  · 信念墙独立压测            │ │
│  │                        │   │  · 决策后评估（政策复盘）     │ │
│  │                        │   │  · 跨项目/跨领域概念授粉      │ │
│  │                        │   │  · 方法论自我打磨            │ │
│  │                        │   │  · 给Cardmaster预制弹药      │ │
│  └───────────────────────┘   └─────────────────────────────┘ │
│                                                              │
│  共享状态：dict/ + decisions/ + belief-walls/ + ammo-cache/   │
│           + research-notes/ （平时研究笔记，非宪法级产物）     │
└─────────────────────────────────────────────────────────────┘
```

**关键认知**：Research Mode 不是"等批次开产时找点事做"——它是 Aristotle 的**日常工作**。Campaign Mode 是他被拉去"开生产会"配合作业。他的研究产出——更精确的术语、更清晰的信念边界、更完善的定义方法论——直接提升下个生产批次的服务质量。

### 研究工作的原则

1. **研究产出有消费者**：不做无的放矢的"纯思考"。每个平时研究skill都有明确的消费方——Cardmaster要弹药、Strategy要决策回压、Skeleton要结构边界、下个生产批次要更精确的词典。
2. **草稿优先，转正需人确认**：平时研究的结论先入 research-notes/ 或 .draft/，不直接修改 dict/ 和 decisions/（宪法修正案必须走批次期正式流程）。但 ammo-cache/ 里的预制件可以即时消费——弹药不需要等审批。
3. **可中断**：新批次启动随时切 Campaign Mode，研究工作暂停，断点可恢复。
4. **研究有自己的方法论**：不是瞎想——有明确的研究问题、输入源、产出格式、评估标准。下面每个 Research Mode skill 都按"研究问题→输入→方法→产出"格式写。
5. **不越权**：Aristotle 不判断战略方向（那是 Strategy 的研究），不设计结构（那是 Skeleton 的研究），不制定战术（那是 Cardmaster 的研究）。他的研究边界是**术语、定义、概念关系、信念边界、决策语言**。

---

## 交互拓扑（服务接口面）

不是"第X步传给第Y步"，而是**谁向谁请求什么服务、频率如何、什么协议**。

```
                            ┌──────────┐
                            │   人     │
                            │ (全局)   │
                            └────┬─────┘
                高频 ↓            │            ↓ 高频
            ┌────────────────────┼────────────────────┐
            │                    │                     │
            ▼                    │                     ▼
     ┌──────────────┐    ┌──────┴──────┐      ┌──────────────┐
     │  Cardmaster  │◄───┤  Strategy   │      │  PM Bee      │
     │  (调度长)     │───►│  (情报调研)  │      │  (车间主任)  │
     └──┬────┬────┬─┘    └──────┬──────┘      └──────────────┘
        │    │    │              │
   语义弹药│    │规格书    战略断言│         ← 三者都是研究员型员工，
   (预制/即取)│    │              │           平时各做各的研究
        │    │    │     ┌────────┴────────┐
        │    │    └────►│  Aristotle Bee   │◄─── 漂移汇报 ── World Bee
        │    │          │  (首席术语官)     │──── 校准请求 ──► World Bee
        │    │          └────────┬────────┘
        │    │                   │
        │    │              handoff包
        │    │                   │
        │    │                   ▼
        │    │           ┌──────────────┐
        │    └──────────►│  Skeleton    │
        │   蓝图规格调度  │  (总工程师)   │
        │               └──────────────┘
        │
        │  ┌─────────────────────────────────────────┐
        │  │  执行层（PM→Centurion→Worker→World）     │
        │  │  生产批次期间：                           │
        └──┤  · Aristotle 在 Research Mode 独立研究    │
           │  · World 汇报质检日志→Aristotle 观察术语  │
           │  · Cardmaster 随时 pull 弹药              │
           └─────────────────────────────────────────┘
```

### 接口契约详表

| 客户 | 服务类型 | 模式 | 协议 |
|------|---------|------|------|
| **人 → Aristotle** | 概念追问/校准/研究方向指令 | Campaign + Research（人可随时喊他） | 自然语言 |
| **Strategy ↔ Aristotle** | 断言地基审查 + 假设显化 + 决策回压推送 | Campaign（Step 1高频）+ Research（决策回压推送给Strategy Step 9用） | 批次期：grilling/absurdum实时响应；平时：decision-retro完成后**主动推送**（消息/邮件）给Strategy，不等Strategy自己pull——避免"写了没人读" |
| **Aristotle → Skeleton** | Step 1→2 交接包 | Campaign（handoff） | handoff包（dict/快照+decisions索引+open-questions+belief-walls/） |
| **World → Aristotle** | 执行期术语使用反馈（仅术语异常） | Research（持续田野观察） | drift-watch**只监听术语相关log**（术语使用/新词涌现/定义偏差），过滤执行噪音；🔴漂移拉回Campaign校准。过滤规则：只汇报"术语使用异常"，不汇报执行细节 |
| **Aristotle → World** | 校准指令（可执行diff） | Campaign（被拉回时） | 校准指令必须包含**可执行的diff**（"把X改成Y"的具体操作），不只是引用dict/抽象定义——确保World无需理解dict/语义就能更新执行基线 |
| **Cardmaster → Aristotle** | 语义弹药请求 | Research（主要）+ Campaign（research牌） | ammo-prep push/pull双模式；grilling可远程调用（低保真异步） |
| **Aristotle → Cardmaster** | 预制语义弹药包 | Research（持续） | ammo-cache/ 中预置好的术语包+标准骨架+信念边界 |
| **PM/Centurion/Worker** | 读dict/（不直接对话） | 全程 | 术语基线是task/recipe/log的通用语言 |
| **跨项目 → Aristotle** | 术语复用参考 | Research | cross-pollinate发现→新项目开局推荐 |

**三个最高频交互**：
1. **Strategy ↔ Aristotle**（批次期实时对话，Step 1）
2. **Aristotle → Cardmaster 弹药供应**（平时持续预制+批次期即取）
3. **World → Aristotle 术语田野反馈**（平时持续观察，按需触发批次期校准）

---

## Skill 全景

```
┌──────────────────────────────────────────────────────────────┐
│  CAMPAIGN MODE — 批次期配合（Step 1 战略探索，人在回路）        │
├──────────────────────────────────────────────────────────────┤
│  字典写入层   define · fork · resolve · align                │
│  决策沉淀层   decide · handoff                               │
│  解析攻击层   unpack → grilling → absurdum                  │
│  图谱结构层   relate                                         │
│  守门层       gap_scan · hold · coin                         │
│  大雾探索层   explore                                        │
│ （共 14 个批次期服务原语）                                      │
├──────────────────────────────────────────────────────────────┤
│  RESEARCH MODE — 平时研究+系统提升（默认工作模式）            │
├──────────────────────────────────────────────────────────────┤
│  术语图谱研究   enrich                                       │
│  质量审计       proofread                                    │
│  概念债务审计   concept-debt                                 │
│  外部概念追踪   concept-mining                               │
│  术语田野观察   drift-watch                                  │
│  信念墙独立压测 belief-stress                                │
│  决策后评估     decision-retro                               │
│  跨领域授粉     cross-pollinate                              │
│  弹药预制       ammo-prep（服务Cardmaster）                  │
│  方法论打磨     method-sharpen                               │
│ （共 10 个平时研究skill）                                     │
└──────────────────────────────────────────────────────────────┘
```

---

## CAMPAIGN MODE：批次期配合原语（14 个）

14 个原语（define / fork / resolve / align / decide / handoff / unpack / grilling / absurdum / relate / gap_scan / hold / coin / explore）规格保持 v2 设计，此处仅列 v3 增量调整：

### 增量 1：grilling 可被 Cardmaster 远程调用

Cardmaster 出 research 牌（build standard）发现术语弹药不足时，可远程请求 grilling——Aristotle 基于已有 dict/、decisions/、literature 执行低保真 grilling，需要人判断的问题生成 question-ticket 等人下次上线时答，不卡住出牌。

### 增量 2：handoff 包新增 belief-walls/ 完整快照

不只 summary，是每个被 absurdum 压测过的信念墙的完整极限推记录，供 Skeleton 规约设计时精确掌握边界。

### 增量 3：人可随时拉回 Campaign Mode

平时研究期间人随时喊"Aristotle 回来说一下"——立即暂停 Research Mode，进入 Campaign Mode 响应，处理完继续 Research。

---

## RESEARCH MODE：平时研究+系统提升（10 个）

Research Mode 是 Aristotle 的**默认工作模式**——不在生产批次进行中时他就在做这些。每个 skill 按"研究问题→输入→方法→产出→消费方→频率"格式说明。

---

### R1. `enrich`（术语图谱完善）

**研究问题**：生产批次赶时间，relate 只连了当时用得到的边。全图里有没有"应该连但没连"的关系？有没有孤立节点？有没有循环定义？

**输入**：dict/ 全部 active 术语 + 现有 relate 边 + decisions/ 中引用术语的方式

**方法**：
1. 扫描全图，补 is-a / part-of / contrasts-with / presupposes 候选边
2. 识别孤立节点（定义了但没连任何边）→ 补边或标记 orphan
3. 检测循环定义（A presupposes B → B presupposes C → C presupposes A）→ 标记给下次批次期 grilling
4. 检查 Forbidden aliases 是否在正式文件里被误用

**产出**：`research-notes/enrich/<date>.md`——候选边列表+孤立节点报告+循环检测结果，人下次上线可批量 yes/no 审批

**消费方**：下次批次期（更完整的图谱）+ ammo-prep（更准确的关系推荐）

**频率**：生产批次进入执行期后每 3 天一次；新项目首次全量

**类比**：词典编纂者在没有截稿压力时，回头把所有词条之间的交叉引用补齐——写作时只引了最直接的，闲了把整个语义网编织完整

---

### R2. `proofread`（术语表质量审计）

**研究问题**：批次期赶节奏，define 可能写得不够精确。哪些定义模糊、Genus 弱、和其他词撞车？

**输入**：dict/ 全部 active 术语

**方法**：
1. Definition 长度检查（≤2句）+ 模糊词检测（"可能""大概""相关"等）
2. Genus+Differentia 区分度检测：同类术语的 Differentia 是否真正区分了它们
3. Forbidden aliases 和其他术语 Definition 撞车检测
4. deprecated 术语残留引用检测

**产出**：`research-notes/proofread/<date>.md`——问题清单（🔴定义模糊/🟡Genus弱/🟢清理提示）

**消费方**：下次批次期（人可快速修正）+ concept-debt（高严重度问题进入债务清单）

**频率**：每次 enrich 之后自动跑

**类比**：学术期刊的文字编辑在排版前做的术语一致性校对——作者赶 deadline 时写得快，编辑闲了逐个检查定义是否严谨

---

### R3. `concept-debt`（概念债务审计）

**研究问题**：生产批次高压下有些术语是"先这么用着吧"的应急定义——这些概念债务在积累。哪些定义因为仓促而埋下了后续沟通成本的隐患？债务的利息是多少？

**输入**：proofread 结果 + drift-watch 历史报告 + Worker/World 执行日志中的术语误用记录 + 历次生产批次进行中"因为术语不清导致返工"的记录

**债务利息量化指标**（先有指标再排序，不做空话）：
- `misuse_count`: drift-watch 报告的该术语漂移/误用次数
- `align_count`: 该术语在批次期被 align/resolve 的次数（从 decisions/ 历史统计）
- `session_rework`: 因该术语不清导致的 session 重开/返工次数（从 session 历史统计）
- 利息分 = misuse_count × 3 + align_count × 2 + session_rework × 5（返工权重最高）

**方法**：
1. 识别**仓促定义特征**：Definition 含模糊词、没有 Forbidden aliases、没有 presupposes 边、首次定义后10轮内被 align 过 ≥2 次
2. 计算**债务利息**：按上述三个指标统计每个术语的利息分，按分排序
3. 识别**债务关联**：一个模糊定义导致了哪些下游术语也模糊了？（依赖链传播）——模糊术语的 presupposes 下游术语自动获得关联利息分
4. 按利息分排序，出债务清单

**产出**：`research-notes/concept-debt/<date>.md`——债务清单（术语+仓促证据+利息证据+建议处理方式：redefine/fork/retire标注）

**消费方**：人（下次批次期优先处理高息债务）+ ammo-prep（高息债务的术语不在预制件中推荐使用）

**频率**：每次生产批次结束后做一次债务清算；平时每 2 周扫描一次

**类比**：做研究的人都知道有些概念是"写论文时先这么用着"的working definition，投完稿回头一看——因为这个偷懒的定义，后面三个章节的论证都站不稳。这就是概念债务，利息是审稿人的质疑。

---

### R4. `concept-mining`（外部新概念追踪）

**研究问题**：外面在变，外部世界在产生新概念、新术语、新框架。蜂群的 dict/ 是不是滞后了？哪些外部概念值得提前摄入？

**输入**：外部信息流——arXiv 新论文（和蜂群研究方向相关的）、行业动态、开源项目文档、学术会议、用户最近关注的话题

**方法**：
1. 定期扫描预设信息源（可配置：arXiv关键词、特定GitHub repos、行业博客等）
2. 提取高频新术语（出现≥3次且不在 dict/ 和 _global.md 中）
3. 对每个候选术语做初步 Genus+Differentia 草稿
4. 评估摄入优先级：
   - 🔴 生产批次相关：下个生产批次（根据Strategy方向判断）可能直接用到的
   - 🟡 领域前沿：代表方向演化但不一定马上用
   - 🟢 背景噪音：可能是buzzword，观察
5. 高优先级术语出摄入建议

**产出**：`research-notes/concept-mining/<date>.md`——新术语候选清单（词+初步定义草稿+来源+优先级+建议：define入典/observe/ignore）

**消费方**：人（审批哪些入_global/dict）+ ammo-prep（高优先级术语预制进弹药包）+ Strategy（前沿概念可能影响战略判断）

**频率**：每周一次全量扫描

**重要约束**：Aristotle 不自己决定把外部概念写入 dict/——他只做采矿和初步打磨，入典必须走批次期 define 流程（人确认）。这和学术研究一样：你读了100篇论文看到一个新概念，不能直接当自己的框架用，要经过自己的审视和界定。

**类比**：大学图书馆的文献采访馆员——持续追踪新出版的书和论文，评估哪些值得馆藏，给教授们列采购建议，但不替教授决定读什么。

---

### R5. `drift-watch`（术语田野观察）

**研究问题**：术语在执行一线是怎么被实际使用的？和 dict/ 里的定义一致吗？执行层有没有"长出来"的新词？

**输入**：World Bee 校验日志 + Centurion task 派发记录 + Worker 执行 log + PM 漏洞清单

**log过滤规则**（不读全量噪音log，只监听术语相关事件）：
- ✅ 监听：术语使用/引用事件、新词出现事件、术语定义偏差报告、World QA标记的"理解歧义"缺陷
- ❌ 过滤：纯执行细节（API调用/文件IO/进度百分比）、资源消耗日志、Worker心跳
- World在telemetry上报时必须标记`type: terminology`的事件，drift-watch只消费这类事件

**方法**：
1. 读取术语相关log事件（按过滤规则），提取术语使用实例
2. 和 dict/ 定义做 diff，分三类：
   - **良性语境扩展**：Worker 用了术语的特定技术实例，不改变核心 Definition → 记录，不报警（这是正常的语言使用）
   - **概念偷换**：用 dict/ 术语指代了不一致的东西 → 🟡 漂移
   - **执行层涌现术语**：Worker 反复使用 dict/ 里没有但工作正常的词 → 这些是"田野里长出来的词"，可能值得正式 define
3. 严重度分档：🟢记录 / 🟡写入观察报告 / 🔴发校准请求拉回批次期
4. **特别关注**：涌现术语——它们反映了执行层的真实需求，可能是 dict/ 的盲区

**产出**：
- `research-notes/drift-watch/<date>.md`——观察报告
- 🔴漂移 → 触发校准请求 → 拉回 Campaign Mode

**消费方**：Aristotle自己（校准判断依据）+ World（校准后更新基线）+ concept-debt（反复漂移的术语=高息债务）

**频率**：每 6 小时扫一次 log，有🔴立即上报

**不做的事**：不自己改 dict/，不打断执行层——只观察和报告，修正走批次期流程

**类比**：语言学家做田野调查——去一线观察语言是怎么被实际使用的，记录新词新用法，回来写论文提议词典更新，但不替语言社区决定怎么说话

---

### R6. `belief-stress`（信念墙独立压测）

**研究问题**：批次期 absurdum 受对话时间限制只推了最明显的几个极限轴。所有信念墙都五轴推完了吗？有没有隐藏的崩塌点？外部文献有没有反例？

**输入**：belief-walls/ 中所有信念墙 + 已压测记录 + 外部文献（concept-mining 摄入的相关论文/资料）

**方法**：
1. 对标记 `[Partially tested]` 的信念墙跑完整版五轴极限推（∞/0/反/时/值）
2. 对已 `[Validated]` 的信念墙，用 concept-mining 新摄入的外部资料重新检验——有没有新的反例？
3. 跨信念墙检测：两个已压测信念推到极限时会不会互相矛盾？（信念冲突检测）
4. 更新压测记录，标注"有支撑/无支撑/有反例/与其他信念冲突"

**产出**：更新 `belief-walls/<project>/<belief>.md`——完整版极限推报告+反例文献+冲突检测；发现崩塌的标记 `[Precarious: re-examine in wartime]`

**消费方**：批次期 absurdem（不用从零推）+ Strategy Step 9（扬弃时看哪些信念被证伪）+ ammo-prep（给 Cardmaster research 牌预制经过压测的信念边界）

**频率**：每周全量压测一次；新信念墙产生后立即推完；concept-mining 摄入高相关资料后重新检验相关信念墙

**铁律**：**不在 Research Mode 改 dict/ 和 decisions/**——压测发现只是报告，修订宪法必须回批次期走正式 grilling→absurdum→decide。研究员私下发现法律有漏洞，不能自己改法条——要走修宪程序。

**技术约束（enforcement，不能只靠文档铁律）**：
- Research Mode 运行环境对 `dict/` 和 `decisions/` 目录**只读挂载**（文件系统级约束），写入操作直接被OS拒绝
- 所有 Research Mode skill 代码显式检查目标路径：若命中 `dict/`、`decisions/`，直接 raise PermissionError
- Research Mode 唯一可写的目录：`research-notes/`、`ammo-cache/`、`belief-walls/<project>/*.md` 的压测记录字段（不修改belief本身）
- Campaign Mode 启动时切换为读写权限

**类比**：哲学家在书房里对某个论点做 thought experiment——不受会议时间限制，可以把所有极限情况想透，但想完了写论文，要改变共识还得经过同行评议（批次期对话）

---

### R7. `decision-retro`（决策后评估）

**研究问题**：过去的决策在执行中表现如何？哪些被证实、哪些被证伪、哪些没被检验？给 Strategy Step 9 的扬弃准备事实依据。

**输入**：World Bee 验证数据 + PM 漏洞清单 + 执行 log + 补丁记录 + 历次 belief-stress 结果

**方法**：
1. 对每个 NNNN 决策做回压评估：
   - 🟢 Held up：执行结果和决策预期一致
   - 🟡 Partially held：边界比预想的窄/宽
   - 🔴 Broken：决策前提不成立
   - ⚪ Unchallenged：执行没触及这个决策的边界
2. 特别关注 absurdum 推过边界的决策：执行是否撞了边界？怎么处理的？
3. 关联决策链：一个🟡/🔴决策的上下游（通过 relate 的 presupposes 和 decided-by 边）是否受影响？
4. Step 9 前生成完整回压报告

**产出**：
- 持续更新：`research-notes/decision-retro/<NNNN>.md`——每个决策的回压状态+证据链
- Step 9 前：`decisions/<project>/retro-report.md`——全决策回压汇总（这是正式产物，Strategy 直接消费）

**消费方**：Strategy（Step 9 扬弃的核心输入）+ Cardmaster（Step 10 判断"决策错了还是执行偏差"）+ concept-debt（🟡/🔴决策相关的术语可能有债务）

**频率**：每周评估一次；Step 9 前出完整报告

**不做的事**：不做扬弃判断（那是 Strategy+人的事），只做"事实对决策的回压记录"——政策评估员不替总统做决策，只提供评估报告

---

### R8. `cross-pollinate`（跨领域概念授粉）

**研究问题**：蜂群服务多个项目（多个生产批次、多个研究方向）。不同项目之间有没有可以复用的术语？有没有反复出现的决策模式？跨领域的概念类比能不能带来新洞见？

**输入**：所有项目的 dict/ + decisions/ + belief-walls/ + _global.md

**方法**：
1. **同义词检测**：跨项目找 Definition 高度相似但命名不同的术语→推荐统一或标注跨项目别名
2. **决策模式抽象**：识别跨项目反复出现的决策（如"每次做研究类项目都要决定数据是否公开"）→抽象成决策模板，包含常见选项+rationale+边界条件
3. **信念墙迁移检测**：一个项目压测过的信念对其他项目是否适用？
4. **全局术语维护**：更新 _global.md——跨项目通用的蜂群架构核心概念（Agent/Tool/Skill/信息素等）
5. **跨领域类比发现**：不同领域的概念结构如果同构（比如"信息素通信"和"stigma"和"黑板模式"都是"通过环境耦合通信"），记录这类类比——它们可能启发新术语或新决策

**产出**：
- `research-notes/cross-pollinate/synonyms/<date>.md`——跨项目同义词候选
- `research-notes/cross-pollinate/templates/<topic>.md`——可复用决策模板
- `dict/_global.md`——全局基础术语表（新项目开局自动加载）
- `research-notes/cross-pollinate/analogies/<date>.md`——跨领域类比发现

**消费方**：新项目开局（自动查询cross-pollination给开局建议）+ enrich（跨项目边推荐）+ Strategy（跨领域类比可能启发战略方向）

**频率**：每月全量扫描；新项目创建时自动查询推荐

**不做的事**：不强制跨项目统一——只推荐，人决定是否采纳。不同项目可以有不同定义，这是正常的（学术里不同学派用同一个词指不同东西是常见的，但需要标注）

**类比**：跨学科研究——把一个领域发展成熟的概念移植到另一个领域（比如把进化论的"选择压力"用到组织理论里），有时候会产生最有价值的洞见

---

### R9. `ammo-prep`（Cardmaster 语义弹药预制）

**研究问题**：Cardmaster 是最高频人机交互面。它出四种牌，每种都需要语义输入。怎么在出牌前就把弹药准备好，不让人等？

**输入**：Cardmaster deck.json + 回合日志 + Strategy 方向 + dict/ + belief-walls/ + concept-mining 新摄入术语

**方法**：
1. 读取 Cardmaster 当前状态，预判最可能出的下几张牌
2. 针对预判的牌型预制弹药：

| 牌型 | 预制内容 | 优先级 |
|------|---------|--------|
| **research (standard)** | 标准维度候选词+draft定义+维度间关系+相关信念边界 | 🔴最高（最依赖术语精度） |
| **persuade (report)** | 按目标画像预制领域术语包（投资人→金融术语/学术→研究术语/客户→商业术语） | 🟡高 |
| **produce (pipeline)** | 各阶段候选名+边界描述草稿 | 🟡高 |
| **trade (demo)** | 技术术语初始定义包 | 🟢中 |

3. **research 牌特化服务**：对可预见的 standard 主题，提前跑候选维度词的 define 草稿+relate 边+简版 belief-stress
4. **弹药质量分级**（绿卡/黄卡制）：

| 等级 | 条件 | Cardmaster使用规则 |
|------|------|-------------------|
| 🟢 **绿卡（Green）** | 经过 belief-stress + proofread，draft定义完整、信念边界压测通过 | 可直接使用，出牌时直接引用 |
| 🟡 **黄卡（Yellow）** | draft状态，未经过完整belief-stress，或基于concept-mining新概念尚未正式define | 使用时**必须标注"未经压测"**；Cardmaster可自行决定先用黄卡（接受风险）还是等绿卡（延迟响应） |
| 🔴 **红卡（Red）** | 高concept-debt术语，drift-watch反复标记误用 | **禁止预制**，必须走批次期正式define后才能使用 |

5. 接收 Cardmaster 的 pull 请求（出牌时弹药不足）→ 紧急响应

**产出**：`ammo-cache/<project>/<card-type>/<topic>.md`——弹药预制件，文件名首字符标注等级（`🟢_topic.md` / `🟡_topic.md`），Cardmaster spec-generate 可直接引用

**调用协议**：
- **Push**：平时预判预制 → 写入 ammo-cache/ → 出牌时先查缓存，有则直接用
- **Pull**：出牌时弹药不足 → 紧急请求 → 立即响应（优先于其他研究工作）

**消费方**：Cardmaster（唯一直接消费方）

**频率**：每 2 天全量预判一次；Cardmaster pull 请求时立即响应（中断其他研究工作，优先出弹）

**类比**：兵工厂的弹药预置——不生产的时候，炼词车间根据情报预判下一批次可能需要什么概念弹药，提前炼好送到弹药架；车间开产时直接领，不用临时炼词

---

### R10. `method-sharpen`（方法论自我打磨）

**研究问题**：Aristotle 自己的工具和方法好不好用？grilling 的5条硬约束够不够？dict/的glossary格式有没有缺陷？relate的5种边类型够不够？每次生产批次的经验能不能反哺方法论本身？

**输入**：历次生产批次进行中 grilling/absurdum/define/relate 的执行记录 + 人的反馈（"你上次追问得太多/太少"）+ drift-watch/concept-debt 揭示的系统性问题

**方法**：
1. 回顾历次批次期对话记录，识别方法论痛点：
   - grilling 哪些问题追问效率低？是不是硬约束需要调整？
   - dict/ 格式哪些字段实际使用中不好用？
   - relate 边类型是不是不够？（比如发现需要"causes""enables""replaces"等新边？）
   - absurdum 五轴推是不是有些轴对某些信念类型不适用？
   - gap_scan 巡逻频率是否合适？hold 阈值太高还是太低？
2. 对每个痛点提出方法论调整提案（小调整自己试，大调整要等批次期人确认）
3. 积累足够案例后，提炼成方法论改进建议

**产出**：`research-notes/method-sharpen/<date>.md`——方法论自省报告，包含：
- 观察到的方法论痛点+证据
- 小调整的trial结果（自己在Research Mode或下次批次期试的）
- 需要人决策的大调整提案
- 成功的改进→更新Aristotle自己的SKILL.md/操作手册

**消费方**：Aristotle自己（持续自我改进）+ 人（审批大的方法论调整）+ 跨项目（方法论改进进入_global，所有项目受益）

**频率**：每次生产批次结束后做一次retro；平时每2周一次自省

**铁律**：小调整（比如grilling推荐答案的措辞优化）可以自己试；大调整（比如新增relate边类型、修改glossary格式、改变grilling硬约束）必须等批次期人确认——研究员可以优化自己的笔记方法，但不能未经审批改变宪法的格式要求

**类比**：工匠在不打铁的时候打磨自己的工具——锤子用久了手柄松了紧紧、凿子钝了磨磨、发现新的夹具好用自己打一个。但要改变整个工坊的工艺流程，得和工头商量

---

## Research Mode 调度

不是10个skill同时跑——有优先级和调度：

```
生产批次结束/执行期启动 → Aristotle 进入 Research Mode（默认模式）
  │
  ├─ 持续运行（事件驱动）：
  │   · drift-watch（订阅执行log，每6h扫+🔴立即响应）
  │   · ammo-prep（接收Cardmaster pull请求时立即响应，最高优先级中断）
  │
  ├─ 生产批次刚结束时：
  │   1. concept-debt（清算本次生产批次的概念债务）
  │   2. method-sharpen（本次生产批次方法论自省）
  │   3. decision-retro（启动持续回压评估）
  │
  ├─ 日常周期：
  │   · 每2天：ammo-prep 全量预判
  │   · 每3天：enrich → proofread
  │   · 每周：belief-stress + decision-retro评估
  │   · 每2周：concept-debt扫描 + method-sharpen自省
  │   · 每月：cross-pollinate + concept-mining（和concept-mining周扫描错开）
  │
  ├─ 每周：
  │   · concept-mining（外部新概念扫描）
  │
  ├─ 中断处理（优先级从高到低）：
  │   1. 人喊"Aristotle回来" → 立即切Campaign Mode
  │   2. Cardmaster pull弹药 → ammo-prep紧急响应（不切Campaign，快速返回预制件）
  │      · 如果绿卡可用 → 立即返回绿卡
  │      · 如果只有黄卡 → 返回黄卡 + 标注"未经压测"，由Cardmaster决定是否接受
  │      · 如果无预制件 → 低保真grilling生成黄卡，标记question-ticket等人审批
  │   3. World 🔴漂移 → 拉回Campaign Mode做align/resolve
  │   4. 新生产批次启动（Step 1开始）→ 切Campaign Mode
  │
  └─ Step 9前：
      · decision-retro出正式retro-report.md → Strategy扬弃用
```

---

## 双层外源信息素格式（v3 更新）

### dict/\<project\>.md（严格 glossary）

```markdown
# 术语词典：<project>

## <term>
- **Definition**: 一句话精确界定，不超过 2 句
- **Genus（属）**: 它是什么大类
- **Differentia（种差）**: 和同类其他东西的核心区别
- **Forbidden aliases**: 禁止使用的别名/近义词
- **First defined**: Session <id>
- **Status**: active / deprecated / forked-into-X / draft
- **Presupposes**: [term-A, term-B]
- **Source**: wartime-campaign / concept-mining (pending review) / cross-pollinate
- **Debt level**: none / low / medium / high（concept-debt评估）
- **Retro notes**:（Research Mode 注解，如执行中发现的边界；正式修订走批次期流程）
```

### decisions/\<project\>/NNNN-slug.md（决策日志 ADR）

```markdown
# NNNN: <decision-slug>

## Context
...

## Decision
...

## Rationale
...

## Boundary
...

## Date / Session
...

---
## Research Retro（平时评估，Research Mode维护，不修改原文）
- **Status**: 🟢 Held up / 🟡 Partially held / 🔴 Broken / ⚪ Unchallenged
- **Evidence**:（执行日志/World验证/补丁记录中的具体证据）
- **Related beliefs**:（关联的belief-walls，压测状态）
- **Last evaluated**: <date>
```

### research-notes/（平时研究笔记，非正式宪法）

```
research-notes/
├── enrich/               ← 图谱补全候选
├── proofread/            ← 质量审计报告
├── concept-debt/         ← 概念债务清单
├── concept-mining/       ← 外部新术语候选
├── drift-watch/          ← 术语田野观察报告
├── belief-stress/        ← 信念墙压测（更新belief-walls/正式文件但标注precarious）
├── decision-retro/       ← 决策回压草稿（正式retro-report.md入decisions/）
├── cross-pollinate/      ← 跨领域授粉发现
│   ├── synonyms/
│   ├── templates/
│   └── analogies/
└── method-sharpen/       ← 方法论自省
```

research-notes/ 是 Aristotle 的**研究工作区**——类似研究员的笔记本，里面是草稿、候选、观察、提案。它们不是宪法，不约束执行层，但为下次批次期和其他Bee提供养料。人可以随时翻看研究笔记，挑出值得转正的内容。

---

## 典型调用流

### 批次期：Step 1 战略探索

清晰起点：gap_scan → unpack → grilling（含保真度分流）→ decide → absurdum → relate → handoff
大雾起点：explore → 每session一张ticket → 雾散 → handoff

### 平时：Research Mode 独立研究

```
生产批次结束
  │
  ├─ concept-debt 清算 → method-sharpen 自省 → decision-retro 启动
  │
  ├─ [每6h] drift-watch 田野观察
  │   ├─ 🟢 → 记录
  │   ├─ 🟡 → 研究笔记
  │   └─ 🔴 → 拉回批次期校准
  │
  ├─ [每2天] ammo-prep 预判预制 → Cardmaster出牌即取
  │   └─ Cardmaster pull → 立即响应（中断其他研究）
  │
  ├─ [每3天] enrich → proofread → 候选边/问题入笔记
  │
  ├─ [每周] belief-stress + decision-retro评估 + concept-mining
  │
  ├─ [每2周] concept-debt扫描 + method-sharpen自省
  │
  ├─ [每月] cross-pollinate
  │
  └─ [人喊回/新生产批次/🔴漂移] → 切Campaign Mode
```

### 校准触发（执行期发现漂移）

```
drift-watch/World发现🔴漂移
  │
  ├─ 暂停Research Mode → Campaign Mode
  ├─ align对比 → resolve锁定/define新词/fork裂变
  ├─ 更新dict/ → 发校准指令给World
  └─ 回Research Mode继续
```

---

## Aristotle 对 Cardmaster 的弹药供应（详例）

**没有平时预制（v2世界）：** Cardmaster出牌时Aristotle现场从0开始定义术语→打断出牌节奏，人被拉去回答定义问题。

**有平时预制（v3世界）：**
1. ammo-prep 预判：Strategy方向"需要融资"→ 大概率persuade投资人 → 需要金融术语+report质量维度
2. 平时提前在ammo-cache/persuade/investor-terms.md预制：TAM/SAM/SOM、ARR、moat等术语draft定义；在ammo-cache/research/report-quality.md预制：data_accuracy等5维度draft定义+关系+信念边界
3. Cardmaster出牌时spec-generate直接引用draft，人只需refine不用从零想
4. 人refine完→转正入dict/（生产批次中正式define，或人在平时审批research-notes时转正）

---

## 对其他研究员型Bee的启示

Aristotle的"批次期配合+平时研究"模型同样适用于其他三个研究员：

| Bee | 批次期配合 | 平时研究方向（举例，待展开） |
|-----|---------|---------------------------|
| **Strategy** | Step1/2/9方向+扬弃 | 外部环境扫描（竞品/政策/技术趋势）、战略期权开发、兵棋推演（war-gaming）、战略框架打磨、历史生产批次模式分析 |
| **Skeleton** | Step2结构设计 | 架构模式库建设（从已完成项目抽象可复用结构）、反模式目录、结构质量度量、新结构原型实验 |
| **Cardmaster** | 出牌调度+Step10复盘 | 牌效分析（哪些牌成功率高/为什么）、对手建模（目标客体类型画像库）、playbook建设、新卡原型设计、meta-game分析 |
| **(Aristotle)** | Step1术语 | 即本文档 |

这些平时研究不是"空闲期填充"——是各自的**本职研究议程**。计件工（Worker/Centurion）的产出是task，研究员的产出是**知识和能力**——更准的术语、更清晰的框架、更有效的战术、更敏锐的战略判断。

---

## 外部依赖与借鉴

| 来源 | 借鉴 |
|------|------|
| [mattpocock/skills](https://github.com/mattpocock/skills) | grilling/wayfinder/domain-modeling原语+v3远程grilling |
| nanobot Dream机制 | 空闲期自我完善——但Aristotle的"梦"不是基于git diff，而是基于术语图谱+执行日志+外部文献 |
| DDD Bounded Context | cross-pollinate的跨上下文术语映射 |
| 学术同行评议 | belief-stress的"冷静期再检验" |
| 军事后勤学 | ammo-prep的"批次需求预判+弹药架预制+开产即领" |
| 词典编纂学 | enrich/proofread的词条维护和交叉引用 |
| 语言人类学田野调查 | drift-watch的"观察语言实际使用而非规定" |
| 技术债务概念（Ward Cunningham） | concept-debt的"仓促定义的复利成本" |
| 图书馆文献采访 | concept-mining的"追踪+评估+推荐但不替读者决定" |
| 政策评估 | decision-retro的"事实回压但不替决策者判断" |
| 跨学科研究方法 | cross-pollinate的"概念迁移与类比发现" |
| 工匠传统 | method-sharpen的"持续打磨自己的工具" |

## 版本演进

- **v1**：10个skill，以字典编辑为核心，有seal/retire
- **v2**：14个skill，升级为"制宪者"，引入grilling原语+ADR决策日志+handoff+explore，砍seal/retire/question_belief
- **v3**：常驻知识员工模型，Campaign Mode（14个批次期原语）+ Research Mode（10个平时研究skill）；新增concept-debt/concept-mining/method-sharpen；交互拓扑改为服务接口面；显式建模Cardmaster弹药供应链
- **v3.1**（评审后修订）：接口面4项修复（decision-retro主动推送Strategy、World→Aristotle log过滤规则、Aristotle→World校准指令可执行diff、drift-watch术语事件过滤）；concept-debt债务利息量化（misuse_count/align_count/session_rework三指标）；belief-stress技术enforcement（Research Mode只读挂载+代码路径检查）；ammo-prep绿卡/黄卡/红卡三级弹药分级；新增v3落地路线图（4-phase YAGNI分批）


## v3 落地路线图（评审反馈补充）

v3 设计完整，但实现成本不均。按 YAGNI 阶梯分批落地，避免基础设施超配：

### Phase 1：Campaign Mode 14原语代码化（批次期刚需）
- 14个原语先实现为可调用skill（define/fork/resolve/align/decide/handoff/unpack/grilling/absurdum/relate/gap_scan/hold/coin/explore）
- dict/ 和 decisions/ 格式落地（glossary + ADR）
- handoff包格式定义
- **技术约束**：Campaign Mode 对 dict/decisions 读写；Research Mode 只读（文件系统级+代码级双保险）

### Phase 2：Research Mode 三个最高频skill（MVP）
- **drift-watch**：执行期术语观察（只消费World上报的`type: terminology`事件，不读全量log）
- **ammo-prep**：服务Cardmaster弹药预制（绿卡/黄卡分级；pull紧急响应）
- **concept-debt**：批次结束后债务清算（按`misuse_count/align_count/session_rework`三指标量化）
- 其余7个Research skill标记为"待实现"，等数据管道成熟后启用

### Phase 3：按需扩展
- Research Mode 其余skill（enrich/proofread/concept-mining/belief-stress/decision-retro/cross-pollinate/method-sharpen）
- decision-retro → Strategy主动推送机制
- 自动调度系统（Phase 1-2全部手动触发：人喊"跑drift-watch"或"出弹"，不搞全自动周期调度）

### Phase 4：基础设施成熟后
- 事件驱动调度（消息队列、状态机）
- 全自动周期调度（每6h/每2天/每周的定时任务）
- 跨Bee自动推送（decision-retro主动推送Strategy等）

---

> 本内容由 Coze AI 生成，请遵循相关法律法规及《人工智能生成合成内容标识办法》使用与传播。
