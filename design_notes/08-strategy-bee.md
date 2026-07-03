# Strategy Bee — 搜索 + 锁定

> *战略的标准是正确。正确 = 饱和式覆盖 + 边界精确。这两个要求相互矛盾，但这就是战略工作的本质。*

---

## 一、Strategy Bee 在蜂群中的位置

```
Strategy Bee（战略：正确）
    │
    │ 战略方向 + 边界定义
    ▼
Commander Bee（前线小队长：创造性执行，信息不足主动向 Chef 要）
    │
    │ 任务流
    ▼
Chef Bee（计划：菜谱级拆解）→ Worker Bees → Verification Bee（验证）
    │                                              │
    │                                              │ 验证数据
    │                                              ▼
    └────────────────────────────── Strategy Bee（终极报告）
```

**Strategy Bee 在两端出现**：上游定方向，下游出报告。这是一个闭环。

---

## 二、战略的核心矛盾

### 饱和式覆盖 vs 边界精确

| 要求 | 含义 | 为什么矛盾 |
|------|------|-----------|
| **饱和式覆盖** | 不遗漏任何相关信息。所有角度、所有数据源、所有可能性 | 覆盖越广，边界越模糊 |
| **边界精确** | 只覆盖相关领域。不浪费资源在无关方向 | 边界越精确，越可能遗漏 |

**战略工作的本质就是管理这个矛盾。** 不是"找到一个完美的平衡点"——是**先精确划定边界，然后在边界内做饱和式覆盖**。关键是边界定义这个动作本身。

### 如何做到

```
步骤 1: 划定边界
  - 这个目标涉及哪些领域？（枚举）
  - 每个领域的边界在哪？（用"不属于此范围"来定义）
  - 相邻领域的接口是什么？

步骤 2: 饱和式覆盖（在边界内）
  - 每个领域内，穷举所有相关信息源
  - 数据源、文献、竞品、法规、案例——不遗漏
  - 这个阶段不求深度，求广度

步骤 3: 收束
  - 从饱和覆盖中提取模式
  - 生成假设（可被 Verification Bee 验证的命题）
  - 明确"已知"和"未知"的边界（新一轮的精确边界）
```

**Strategy Bee 的 decompose-goal 和 Chef Bee 的 task-decompose 是两层**：

| | Strategy Bee | Chef Bee |
|---|---|---|
| 拆什么 | 目标 → 领域（domain） | 任务 → 步骤（step） |
| 精度 | 领域级别 | 文件级别 |
| 追求 | 饱和式覆盖（广度） | 菜谱级精确（深度） |
| 输出 | 领域地图 + 边界定义 | PLAN.md（可执行 task） |
| 何时做 | 启动阶段（一次） | 每个执行周期 |

---

## 三、Strategy Bee 的两个角色

### 角色一：战略规划（上游）

**消费者**: Commander Bee（接受战略方向）  
**产品**: 领域地图 + 边界定义 + 搜索清单

```
输入: 人提出的模糊目标（"我要做 X"）
  │
  ▼
[1] boundary-define   → 划定领域边界（做什么、不做什么）
[2] domain-map        → 枚举所有相关子领域
[3] source-inventory  → 每个子领域的信息源清单（饱和式）
[4] hypothesis-seed   → 生成初始假设（待 Verification Bee 验证）
  │
  ▼
输出: strategic-brief.md → Commander Bee
```

#### [1] boundary-define — 划定边界

| 字段 | 内容 |
|------|------|
| **Input** | 人的原始目标陈述 |
| **Output** | 边界定义文档 |
| **调 LLM** | 是 |

**核心操作**: 用排除法定义边界。说清楚"不做"比说清楚"做"更重要。

```
目标: 研究 AI agent 的商业模式

边界定义:
  IN:
    - AI agent 框架/平台的商业模式
    - 开源 vs 闭源的收入模式
    - 2023 年之后的新模式
  OUT:
    ✗ 传统 SaaS 的商业模式（不是 AI agent 特有的）
    ✗ AI 芯片/硬件的商业模式（不同领域）
    ✗ 纯技术架构比较（除非和商业模式直接相关）
  AMBIGUOUS（需要人确认）:
    - MCP 生态的工具市场抽成模式？← 人在不在？确认一下
```

**边界定义的校验**: "如果有人要我调研一个不在 IN 列表里的东西，我可以有理有据地说'这不在范围内'。"

#### [2] domain-map — 领域地图

| 字段 | 内容 |
|------|------|
| **Input** | boundary-define 的输出 |
| **Output** | 领域地图：子领域 + 交叉关系 |
| **调 LLM** | 是 |

```
AI agent 商业模式 — 领域地图

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  平台/框架    │    │  工具/插件    │    │  服务/咨询    │
│              │    │              │    │              │
│ LangChain    │    │ MCP 市场     │    │ 企业定制     │
│ CrewAI       │    │ GPT Store    │    │ 培训         │
│ AutoGen      │    │ 代码助手     │    │ 咨询         │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                  ┌────────┴────────┐
                  │  开源 vs 闭源    │  ← 横切维度
                  │  个人 vs 企业    │
                  │  国内 vs 海外    │
                  └─────────────────┘
```

#### [3] source-inventory — 信息源清单

| 字段 | 内容 |
|------|------|
| **Input** | domain-map |
| **Output** | 每个子领域的信息源清单（饱和式） |
| **调 LLM** | 是 |

**这是"饱和式覆盖"的核心环节。** 对每个子领域，列出所有能找到的信息源。

```markdown
# 信息源清单: AI agent 商业模式

## 平台/框架
- [ ] LangChain 官方博客 + 定价页
- [ ] CrewAI 官方文档 + 融资新闻
- [ ] AutoGen (Microsoft) 官方公告
- [ ] Dify 国内版 vs 海外版定价对比
- [ ] Coze (字节) 商业化进展
- [ ] 各大框架的 GitHub Star 趋势（代理指标）

## 工具/插件
- [ ] OpenAI GPT Store 分成政策
- [ ] Anthropic MCP 生态的经济模型
- [ ] GitHub Copilot 收入数据
- [ ] Cursor / Windsurf 定价

## 开源 vs 闭源
- [ ] Red Hat 开源商业模式案例
- [ ] MongoDB SSPL 许可证争议
- [ ] GitLab 开源+付费的平衡
- [ ] 中国开源项目商业化案例（TiDB, OceanBase）

## 横切数据
- [ ] CB Insights AI agent 市场报告
- [ ] a16z / Sequoia 相关投资分析
- [ ] 中国信通院 AI agent 白皮书
```

每个条目标注状态：`[ ]` 待搜索 / `[x]` 已搜索 / `[!]` 找不到（标记缺口）。

#### [4] hypothesis-seed — 初始假设

| 字段 | 内容 |
|------|------|
| **Input** | domain-map + source-inventory |
| **Output** | 待验证的初始假设列表 |
| **调 LLM** | 是 |

**假设 = 可以用数据验证的命题。** 初始假设不保证对——它们是"值得验证的方向"。

```markdown
# 初始假设: AI agent 商业模式

201|## H1: 开源框架的商业模式正在收敛到 2 种
- 命题: 开源 AI agent 框架要么走"托管云服务"（像 MongoDB Atlas），要么走"企业支持"（像 Red Hat）
- 可验证: 收集 ≥10 个开源框架的定价页面 → 分类统计
- 如果为真: 新进入者的选择空间很小，必须在 2 者中选
- 优先级: high

## H2: 中国市场的 agent 商业化路径和海外不同
- 命题: 国内 agent 产品更依赖大厂生态（字节/阿里/腾讯），独立产品的空间比海外小
- 可验证: 对比国内 top 5 vs 海外 top 5 agent 产品的用户来源
- 优先级: high

## H3: 工具/插件市场的抽成模型不可持续
- 命题: 30% 抽成（类似 App Store）在 agent 工具市场上会被开源替代方案侵蚀
- 可验证: 追踪 GPT Store 的开发者留存率 + 开源替代的数量增长
- 优先级: medium
```

这些假设交给 Commander → PM → Worker → World 执行验证。Verification Bee 验证后，数据回流到 Strategy Bee 做终极报告。

---

### 角色二：终极报告（下游）

**消费者**: 人（最终的决策者）  
**产品**: 战略报告（高度人工配合）  
**输入**: Verification Bee 的验证数据 + 证据链报告

```
Verification Bee 验证数据
    │
    ▼
[5] evidence-synthesize → 将验证数据整合进领域框架
[6] conclusion-draft    → 起草结论（标注置信度）
[7] human-review        → 人审阅、修改、确认
[8] strategic-report    → 最终报告
```

**这是高度人工配合的过程。** Strategy Bee 不做最终判断——它把验证过的数据按领域框架组织好，起草结论，然后**等人来确认或推翻**。

#### [5] evidence-synthesize — 整合验证数据

| 字段 | 内容 |
|------|------|
| **Input** | Verification Bee 的 evidence-chain.md + verified/ 数据 + domain-map |
| **Output** | 按领域框架组织的数据汇编 |
| **调 LLM** | 是 |

```markdown
# 数据汇编: AI agent 商业模式

## 领域: 平台/框架
- [triangulated] LangChain: 月活开发者 2M+，付费转化 ~3%，ARR ~$15M
- [verified] CrewAI: 2024 融资 $18M，开源 Star 20K+，无公开收入
- [single] AutoGen: 微软内部使用为主，外部采用有限
- [gap] Coze 商业化数据缺失

## 领域: 工具/插件
- [triangulated] GPT Store: 开发者留存率 < 20%，争议大
- [verified] GitHub Copilot: ARR $400M+，企业版增长最快
- [contradiction] Cursor 定价数据：source-A 说 $20/月，source-B 说 $40/月 → 标记需重新验证

## 假设验证结果
- H1: ✅ 开源框架确实收敛到 2 种模式（托管云 + 企业支持）— 10/12 个案例支持
- H2: ✅ 中国市场差异显著 — 国内 top 5 中 4 个依托大厂生态
- H3: ⚠️ 部分支持 — GPT Store 留存率低，但 Copilot 的模式（工具内集成）抽成可持续
```

#### [6] conclusion-draft — 起草结论

| 字段 | 内容 |
|------|------|
| **Input** | evidence-synthesize 的输出 |
| **Output** | 结论草案（标注置信度 + 证据充分度） |
| **调 LLM** | 是 |

每条结论附带：
- **置信度**: high（多源三角验证）/ medium（2源吻合）/ low（单源或矛盾）
- **证据充分度**: 充分 / 不足（标注缺失数据）
- **可行动建议**: 基于这条结论，应该做什么

```markdown
# 结论草案 — AI agent 商业模式

## 高置信度结论（可以直接用）

1. 开源 agent 框架的主流商业模式是"托管云服务"和"企业支持"双轨制
   证据: 10/12 案例支持，多源三角验证
   行动: 如果要做开源框架，从第一天就设计好云服务架构

2. Copilot 模式（工具内集成）是目前唯一验证成功的 agent 付费模式
   证据: GitHub Copilot ARR $400M+，Cursor 快速增长
   行动: 优先考虑"嵌入已有工作流"的模式，而非独立产品

## 中置信度结论（可以用，但需要持续关注）

3. GPT Store 的分成模式在 agent 工具市场上可持续性存疑
   证据: 留存率低但需要更长时间的数据（当前只有 6 个月）
   行动: 如果做 agent 工具，优先考虑 Copilot 式的工具内集成

## 信息缺口（影响结论质量）
- 中国 agent 产品的付费数据严重缺乏 → 建议启动专门的国内调研
- Coze/Dify 的商业化数据不可得 → 标记为"竞争对手黑箱"
```

#### [7] human-review — 人审阅

| 字段 | 内容 |
|------|------|
| **Input** | conclusion-draft |
| **Output** | 经过人确认/修改/推翻的结论 |
| **调 LLM** | 否 |

**这是 Strategy Bee 停下来等人的环节。** 目标让人确认三件事：
1. 边界定义对不对？（有没有该做但没做的领域？）
2. 结论对不对？（有没有数据不支持但直觉告诉你是对的？）
3. 信息缺口要不要填？（有些缺口如果填的成本太高可以不填）

#### [8] strategic-report — 最终报告

| 字段 | 内容 |
|------|------|
| **Input** | human-review 后的结论 + evidence-synthesize 的数据 |
| **Output** | 最终战略报告 |
| **调 LLM** | 是（组装） |

---

## 四、Strategy Bee 与 Aristotle Bee 的分工

| | Strategy Bee | Aristotle Bee |
|---|---|---|
| **活跃时机** | 启动 + 收尾（两端），运行中定期 | 子项目运行中**完全静默** |
| **管什么** | 战略方向、领域边界、终极报告 | 术语定义、词典归档 |
| **数据来源** | Verification Bee 的验证数据 + 人的输入 | 项目中自然出现的术语 |
| **产出** | strategic-brief.md, 战略报告 | dict/<project>.md |
| **和人的关系** | 高度配合（人确认边界、人审阅结论） | 被动服务（人有新术语才用） |

**Aristotle Bee 在项目运行中不说话。** Worker Bee 写东西时如果遇到未定义术语，自己查词典——不叫 Aristotle Bee。只有人主动说"定义一下 X"或项目归档时才激活。

---

## 五、与 Commander Bee 的分工

| | Strategy Bee | Commander Bee |
|---|---|---|
| **层级** | 战略 | 战役 |
| **管什么** | 方向对不对 | 执行到不到位 |
| **输入** | 人的目标 + World 数据 | Strategy Bee 的战略简报 |
| **输出** | 领域地图 + 假设 + 最终报告 | 任务流（Job Board） |
| **决策方式** | LLM + 人确认 | 规则引擎 |
| **何时用 LLM** | boundary-define, domain-map, conclusion-draft | 不用 LLM 做决策 |

**Commander Bee = 小队长。** 战略定了"要调研 AI agent 商业模式"，Commander 负责把这件事变成具体的任务派发出去。它不管方向对不对——那是 Strategic 的活。它只保证"派出去的任务能收回来"。

---

## 六、Skill 清单

| # | Skill | 角色 | 调 LLM |
|---|-------|------|--------|
| 1 | boundary-define | 战略规划 | 是 |
| 2 | domain-map | 战略规划 | 是 |
| 3 | source-inventory | 战略规划 | 是 |
| 4 | hypothesis-seed | 战略规划 | 是 |
| 5 | evidence-synthesize | 终极报告 | 是 |
| 6 | conclusion-draft | 终极报告 | 是 |
| 7 | human-review | 终极报告 | 否（等人） |
| 8 | strategic-report | 终极报告 | 是 |

---

## 七、信息素文件

```
~/.worker-bee/strategic/<project>/
├── strategic-brief.md       ← 角色一产出（给 Commander）
├── domain-map.md
├── source-inventory.md
├── hypotheses.md
├── evidence-assembly.md     ← 角色二产出
├── conclusion-draft.md
├── conclusion-final.md      ← 人审阅后
└── strategic-report.md      ← 最终报告
```