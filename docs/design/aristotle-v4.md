---
AIGC:
    Label: "1"
    ContentProducer: 001191110102MACQD9K64018705
    ProduceID: 2725045121849659_7576853131280810010-data_volume/7647463580660547874-files/所有对话/主对话/worker-bee/design_notes/01b-aristotle-skills.md
    ReservedCode1: ""
    ContentPropagator: 001191110102MACQD9K64028705
    PropagateID: 2725045121849659#1784184901958
    ReservedCode2: ""
---
# Aristotle Bee — 首席术语官（CTO）

> 版本：MVP v4（极简核心版）
> 日期：2026-07-16
> 前身：v1 字典编辑 → v2 制宪者 → v3.1 常驻知识员工（过度设计，已归档至 `archive/01b-aristotle-skills-v3.1.md`）

---

## 为什么存在

多 Agent 说同一个词时意思不一样，沟通就坍塌了。
Aristotle 唯一的职责：**让大家说的是同一个东西。**

---

## 核心约束（一条铁律）

```python
CONSTITUTION_PATHS = {"dict.md", "decisions/"}

def safe_write(path: str, content: str):
    if any(p in path for p in CONSTITUTION_PATHS):
        raise PermissionError(f"AI 不能写宪法文件，只能写 drafts/：{path}")
    # 正常写入
```

- **人**维护 `dict.md` 和 `decisions/`（宪法）
- **AI（Aristotle）**所有产出写 `drafts/`（草稿）
- 宪法更新 = 人把草稿 merge 进宪法，不是 AI 直接改

没有双模式权限状态机，没有"Retro 字段可追加但 Definition 字段不可"的精细规则，没有文件系统只读挂载。一条路径检查就够了。

---

## 目录结构

```
bee-knowledge/
├── dict.md              # 术语词典（人维护）
├── decisions/           # 决策日志 NNNN-slug.md（人维护）
└── drafts/              # AI 草稿区（Aristotle 唯一可写目录）
```

### dict.md 格式

每个术语三个字段，够用就行：

```markdown
## swarm
- **Definition**: 多Agent协作系统，由有限规则组合产生无限行为，强调自组织
- **Status**: stable
- **Notes**: 区别于 multi-agent system——swarm 强调涌现和自组织
```

Status 只有三值：`stable`（已确认）/ `draft`（待讨论）/ `suspended`（暂不定义）。

### decisions/ 格式

`NNNN-slug.md`，四字段：

```markdown
# 0001: swarm 定义边界

**Context**: 多Agent系统和蜂群系统的边界在讨论中反复混淆
**Decision**: swarm = 有限规则×无限生成的多Agent系统，强调自组织涌现
**Date**: 2026-07-16
**Notes**: （可选）
```

### drafts/ 内容

Aristotle 的所有产出落在这里，文件名带类型前缀，人定期清理和 merge：

| 文件名模式 | 对应活动 | 处理方式 |
|-----------|---------|---------|
| `define-*.md` | 新术语提案 | merge 进 dict.md |
| `fork-*.md` | 术语分叉（一个词两个意思） | 讨论后 resolve |
| `resolve-*.md` | 分叉解决方案 | merge 进 dict.md |
| `align-*.md` | 用法纠偏（不是改定义，是纠正误用） | 通知相关方，不一定进 dict.md |
| `grill-*.md` | 对某定义的追问/挑战/反例 | 讨论材料，不直接 merge |
| `drift-YYYY-MM-DD.md` | 漂移观察（扫描日志发现的术语误用） | 批次期人审阅 |
| `ammo-*.md` | 给 Cardmaster/其他 Bee 的术语预制件，标 `[DRAFT]` | 消费方自行判断是否使用 |
| `audit-YYYY-MM-DD.md` | 批次清算：哪些术语 status 应从 stable 变 draft | 人确认后更新 dict.md |
| `decisions/NNNN-*.md` | 决策提案 | merge 进 decisions/ |

---

## 工作模式

### 双模式不是权限，是行为

| 模式 | 何时 | 做什么 |
|------|------|--------|
| **Campaign Mode**（批次期） | 人喊"Aristotle 回来"、新项目启动、新批次开始 | 跟人对话定义/分叉/裁决术语，当场写 draft、当场 merge |
| **Research Mode**（执行期） | 其他时间，按需手动触发 | 写 drift 报告、ammo 预制件、audit 报告，全部落 drafts/ 等人处理 |

Campaign 不是"AI 获得了写宪法的权限"，而是"人在旁边，讨论完毕当场 merge"。

### 7 个核心原语（草稿类型，不是独立工具）

| 原语 | 干什么 | 触发时机 |
|------|--------|---------|
| **define** | 提出新术语定义 | 讨论中出现反复使用但没有定义的概念 |
| **fork** | 标记术语分叉（同一词被用作两个意思） | 发现歧义 |
| **resolve** | 提出分叉解决方案（选哪个、怎么改名） | 有 fork 待解决 |
| **align** | 标记术语误用，提出纠偏 | 发现某 Bee 用错词 |
| **decide** | 提出决策记录 | 术语争议有人拍板后 |
| **grill** | 对已有定义提出追问/反例/边界测试 | 定义看起来不稳 |
| **relate** | 标记术语间依赖关系 | define 时附在 Notes 里（See also: xxx） |

这些不是 7 个独立函数，是 Aristotle 产出的 7 种 draft 类型。grep `drafts/define-*` 就能找到所有待定义的术语。

### Research Mode 只做 3 件事

| Skill | 做什么 | 触发 |
|-------|--------|------|
| **drift-watch** | 扫日志/对话记录，发现术语漂移和误用，写 drift 报告 | 手动触发："Aristotle 看看最近有没有用错词" |
| **ammo-prep** | 其他 Bee 问"X 是什么意思"时，从 dict.md+notes 组装一份预制件（标 [DRAFT]）写 drafts/ammo-x.md，返回给请求方 | 按需 pull |
| **audit-debt** | 批次结束时扫描 drafts/ 堆积，列出哪些术语需要重审、哪些 draft 可以 merge、哪些废弃 | 批次收尾时手动触发 |

没有定时调度、没有主动推送、没有事件驱动、没有跨 Bee 消息协议。等出现真实需求再升级。

---

## 其他 Bee 怎么用

| Bee | 读什么 | 怎么写回来 |
|-----|--------|-----------|
| **所有 Bee** | 直接读 `dict.md`（就是读一个文件，grep 即可） | 发现术语问题时，给 Aristotle 提需求（通过 PM 或人） |
| **Cardmaster** | 读 dict.md；需要预制件时 pull ammo-prep | 不直接写 |
| **World** | 读 dict.md（执行基线） | 漂移信号 → 通知人或 PM，不强制 World 改 telemetry 格式 |
| **Strategy** | 读 dict.md + decisions/ | 不直接写 |
| **PM** | 读全部；协调 Campaign Mode | 人通过 PM 调度 Aristotle |

没有结构化 diff 协议，没有 type:terminology 事件标记，没有主动推送机制。"校准"就是人说一声"Aristotle 看看 World 那边 X 用得不对"，Aristotle 写一个 align draft。

---

## 升级路线图（按需触发，不预设时间表）

v3.1 文档（`archive/01b-aristotle-skills-v3.1.md`）是完整设计储备，遇到真实问题时从中取对应设计：

| 信号 | 升级动作 | 参考 v3.1 设计 |
|------|---------|---------------|
| drafts/ 堆积 >10 个找不到东西 | drafts/ 分子目录（notes/cache） | 五层信息素的 notes/cache 分离 |
| AI 乱改 drafts/ 外的文件（安全约束不够） | 加强权限检查 | Research Mode 只读挂载 |
| dict.md 超过 50 个术语/跨项目冲突 | dict.md 拆为 dict/ 目录+项目隔离 | _global.md 项目隔离 |
| Cardmaster 拿到 [DRAFT] 弹药但无法判断可靠性 | 引入绿卡/黄卡分级 | 弹药三级制 |
| 术语间依赖关系复杂到手动理不清 | 引入 Presupposes 依赖图字段 | relate 图谱 |
| 定义质量差/反复返工 | 引入 belief-stress 压测流程 | 五轴压测 |
| 跨项目术语重复/冲突 | 引入 cross-pollinate | 跨项目授粉 |
| 草稿质量稳定、手动 merge 成为瓶颈 | 上 Campaign 自动 merge 流程 | decide/handoff 原语 |
| drift-watch 需要每 6 小时自动跑 | 上 cron 调度 | 事件驱动调度 |

**核心原则：先跑起来，再筑墙。** 没遇到问题就不提前设计。

---

## 不做的事（和 v3.1 的区别）

| v3.1 设计 | MVP 不做 | 为什么 |
|-----------|---------|--------|
| 14 个 Campaign 原语 | 砍到 7 个（且是类型标签不是工具） | 语法式非枚举，7 个覆盖所有合法操作 |
| 10 个 Research skill | 砍到 3 个 | 3-5 个熟手工具原则 |
| 5 层信息素目录（dict/decisions/belief-walls/ammo-cache/research-notes） | 3 个（dict.md/decisions/drafts） | YAGNI，50 术语以内单文件够用 |
| 信念墙五轴压测（∞/0/反/时/值） | 不做 | 这是人的思维活动，不是代码的事 |
| concept-debt 三指标+利息公式 | 不做 | 没数据、系数无依据，优先级判断是人的事 |
| 绿卡🟢/黄卡🟡/红卡🔴三级弹药 | 不做，只标 [DRAFT] | 风险判断是消费方的事 |
| World→Aristotle 结构化校准 diff | 不做 | 人喊一声就够了 |
| decision-retro 主动推送 | 不做 | 等消息基础设施存在 |
| 跨 Bee type:terminology 事件协议 | 不做 | 不强制 World 改格式 |
| 事件驱动自动调度（6h/2d cron） | 不做 | 手动触发，等真有需要 |
| 4-phase 落地路线图 | 不做，没有分 phase | MVP 就是完整第一版，不是"残缺的 v3.1" |

---

## 设计哲学

- **术语是元认知基础设施，但管理员不是研究院**——Aristotle 是字典编辑+裁判，不是知识管理中心
- **AI 只写草稿，人永远有最终 merge 权**——防止 AI 自我膨胀偷偷改定义
- **文件即数据，路径即 API**——纯 Markdown，零依赖，Git 友好，grep 即查询
- **有消费者才生产**——不写没人读的东西
- **草稿优先**——先写 draft 讨论，再 merge 进宪法
- **语法式非枚举**——7 个原语是合法操作的种类，不是功能列表
- **小而精**——一个 Bee 干好一件事（管术语），不膨胀成部门

---

> 本内容由 Coze AI 生成，请遵循相关法律法规及《人工智能生成合成内容标识办法》使用与传播。
