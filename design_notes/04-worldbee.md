# World Bee — 免疫过滤 + 证据链引擎

> *第一道防线：过滤事实错误。第二道防线：拼凑环环相扣的证据链。*
> *流程切得细碎——降低返工。后期再合并——提升流畅。*

---

## 一、World Bee 的双重防线

| 防线 | 角色 | 触发 | 消费者 |
|------|------|------|--------|
| **免疫过滤**（第一道） | 事实校验 → 过滤错误 → 重试指令 | 每个 Worker 提交产出 | Commander（重试指令） |
| **证据链引擎**（第二道） | 交叉验证 → 拼凑证据 → 阶段性结论 + 新假设 | 多个 Worker 产出汇集 | Strategic Bee（报告） |

**两道的区别**：第一道是"这个数据对不对"，第二道是"这些数据放一起说明什么"。

---

## 二、核心假设

1. **Worker Bee 没有 subagent 机制** — 它不会自己查自己。出错就交给 World Bee 检测 → Commander 重试。
2. **流程切细碎** — 每个 skill 做一件事，错了只回滚那一步，不用整个阶段重做。
3. **后期合并** — 细碎 skill 跑通后，相邻的纯规则 skill 可以合并为一个，减少文件跳转。
4. **证据链必须是闭环的** — 不能只靠一个 Worker 的数据下结论。至少 2 个方向的数据相互印证。
5. **回报 Strategic Bee** — World Bee 不做战略决策，只把"验证过的数据 + 发现的新问题"打包给 Strategic Bee。

---

## 三、信息素文件体系

```
~/.worker-bee/world/<project>/
├── ledger.json                  ← 所有 Worker 产出的注册表
├── verified/                    ← 通过验证的干净数据
│   ├── T-001_news_verified.md
│   ├── T-002_tech_verified.md
│   └── ...
├── suspect/                     ← 可疑但未驳回的
├── rejected/                    ← 驳回的数据 + 原因
├── _internal/
│   ├── 01-ingested.json         ← 原始数据注册
│   ├── 02-normalized.json       ← 标准化后的 claims
│   ├── 03-fact-checked.json     ← 事实校验结果
│   ├── 04-verdicts.json         ← 通过/可疑/驳回判定
│   ├── 05-pairwise.json         ← 两两对比结果
│   ├── 06-triangulated.json     ← 三角验证结果
│   ├── 07-contradictions.json   ← 矛盾记录
│   ├── 08-evidence-chain.md     ← 证据链
│   ├── 09-summary.md            ← 阶段性结论
│   ├── 10-hypotheses.md         ← 新假设
│   └── 11-gaps.md               ← 信息缺口
└── reports/
    └── strategic-<date>.md      ← 给 Strategic Bee 的定期报告
```

---

## 四、14 步细碎流水线

```
Worker 产出
    │
    ▼
── 阶段 0：接收与标准化 ──
[1] data-ingest       → ledger.json            登记入库
[2] data-normalize    → 02-normalized.json     提取可验证 claims
    │
    ▼
── 阶段 1：事实校验（第一道防线）──
[3] fact-check-basic   → 03-fact-checked.json  格式/完整性/明显错误
[4] fact-check-source  → 03-fact-checked.json  来源可信度评分
[5] fact-check-internal → 03-fact-checked.json  内部一致性
[6] fact-verdict       → 04-verdicts.json      通过/可疑/驳回
    │
    ├─ 驳回 → Commander（重试指令）
    ├─ 可疑 → suspect/（继续但不作为证据链主力）
    └─ 通过 → verified/
    │
    ▼
── 阶段 2：交叉验证（第二道防线）──
[7] cross-pairwise      → 05-pairwise.json     两两对比
[8] cross-triangulate   → 06-triangulated.json 3+ 源一致确认
[9] cross-contradiction → 07-contradictions.json 矛盾检测
[10] evidence-chain     → 08-evidence-chain.md  拼凑证据链
    │
    ▼
── 阶段 3：汇总与假设 ──
[11] summary-synthesize → 09-summary.md         阶段性结论
[12] hypothesis-generate → 10-hypotheses.md     新假设
[13] gap-detect         → 11-gaps.md            信息缺口
[14] report-strategic   → reports/strategic-*.md 回报 Strategic Bee
```

---

## 五、阶段 0：接收与标准化

### [1] data-ingest — 登记入库

| 字段 | 内容 |
|------|------|
| **Input** | Worker 提交的文件路径 + 元数据（来源 Worker、task ID、提交时间） |
| **Output** | `ledger.json` 追加一条记录 |
| **工具** | `fs_read_file` |
| **调 LLM** | 否 |
| **回滚成本** | 几乎为零（只写一条 JSON） |

**ledger.json 格式**:
```json
{
  "entries": [
    {
      "id": "entry-001",
      "task_id": "JOB-001",
      "worker": "worker-news",
      "role": "news",
      "artifact_path": "data/jobs/JOB-001/article-news.md",
      "submitted_at": "2026-07-01T10:30:00Z",
      "status": "ingested",
      "content_hash": "sha256:abc123..."
    }
  ]
}
```

### [2] data-normalize — 提取可验证 claims

| 字段 | 内容 |
|------|------|
| **Input** | `ledger.json` 中 status=ingested 的条目 |
| **Output** | `02-normalized.json` — 每条数据拆成一组原子 claim |
| **工具** | `fs_read_file`（读 artifact），LLM 辅助提取 claims |
| **调 LLM** | 是 |
| **回滚成本** | 低（只影响一个 entry 的标准化，不需要重读其他） |

**核心操作**: 把 Worker 的整篇文章拆成可独立验证的原子事实声明（claim）。

```
文章 → claims:
  claim-001: "央行降准0.5个百分点"
  claim-002: "释放长期资金约1万亿元"
  claim-003: "上证指数收报3250点（+0.8%）"
  claim-004: "某公司Q2营收580亿元（+12%）"
```

**02-normalized.json 格式**:
```json
{
  "entry-001": {
    "task_id": "JOB-001",
    "worker": "worker-news",
    "claims": [
      {
        "id": "claim-001",
        "text": "央行降准0.5个百分点",
        "type": "numeric_fact",
        "verifiable_by": "public_data",
        "entities": ["央行", "降准"],
        "values": {"percentage": 0.5}
      },
      {
        "id": "claim-002",
        "text": "释放长期资金约1万亿元",
        "type": "numeric_fact",
        "verifiable_by": "public_data",
        "entities": ["长期资金"],
        "values": {"amount_trillion": 1.0}
      }
    ]
  }
}
```

**claim 类型分类**:
| 类型 | 示例 | 验证方式 |
|------|------|---------|
| `numeric_fact` | 降准 0.5% | 查公开数据 |
| `event_fact` | 联合国气候峰会达成协议 | 查新闻 |
| `entity_fact` | IBM 发布 Condor II 芯片 | 查官方公告 |
| `interpretation` | "这是历史性突破" | 主观判断，不验证 |
| `citation` | "分析人士指出..." | 查引用来源 |
| `synthetic` | 多个事实的组合陈述 | 拆成子 claim 分别验证 |

---

## 六、阶段 1：事实校验（第一道防线）

### [3] fact-check-basic — 基础校验

| 字段 | 内容 |
|------|------|
| **Input** | `02-normalized.json` |
| **Output** | `03-fact-checked.json` — 每个 claim 的格式/完整性评分 |
| **工具** | 纯规则 |
| **调 LLM** | 否 |
| **回滚成本** | 很低（规则引擎，重新跑即可） |

**检查规则**（不查真实性，只查"像不像真数据"）:
1. **格式完型**: numeric_fact 必须有数字，event_fact 必须有时间/地点/主体
2. **数值合理**: 降准 500%（不可能）、营收 -100 亿（可能但可疑）
3. **日期合理**: 未来的日期、过去 100 年的"最新"
4. **引用完整**: citation 类型是否有来源指向

**03-fact-checked.json 格式**:
```json
{
  "claim-001": {
    "basic_check": "pass",
    "issues": []
  },
  "claim-XXX": {
    "basic_check": "fail",
    "issues": ["数值异常: 降准幅度 500% 超出正常范围(0-5%)"]
  }
}
```

### [4] fact-check-source — 来源可信度

| 字段 | 内容 |
|------|------|
| **Input** | `03-fact-checked.json`（basic_check=pass 的 claims）+ `02-normalized.json` |
| **Output** | `03-fact-checked.json` 补充 source_credibility 字段 |
| **工具** | LLM（评估 worker 角色 vs claim 类型是否匹配） |
| **调 LLM** | 是 |
| **回滚成本** | 中（LLM 调用，但每个 claim 独立） |

**可信度评分**:
```
worker-news 声称"央行降准0.5%" → 可信度: high（新闻编辑应该报道宏观经济）
worker-culture 声称"央行降准0.5%" → 可信度: medium（文化版不该有原始财经数据）
worker-tech 声称"故宫大展开幕" → 可信度: low（非其专业领域）
```

**评分规则**:
| 条件 | 可信度 |
|------|--------|
| claim 类型匹配 worker 角色 | high |
| claim 类型部分匹配或中性 | medium |
| claim 类型不匹配 worker 角色 | low |
| 同一 claim 被 ≥2 个不同方向的 worker 提到 | +1 级 |

### [5] fact-check-internal — 内部一致性

| 字段 | 内容 |
|------|------|
| **Input** | `03-fact-checked.json`（同一 worker 的所有 claims） |
| **Output** | `03-fact-checked.json` 补充 internal_consistency 字段 |
| **工具** | LLM |
| **调 LLM** | 是 |
| **回滚成本** | 中 |

**检查逻辑**: 同一个 Worker 的文章里，前后说的数字/事实不能矛盾。

```
例: JOB-003 finance worker 的文章里
  claim-A: "营收 580 亿元（+12%）"
  claim-B: "营收增长 15%"  ← 和 A 矛盾！12% ≠ 15%
  → internal_consistency: fail
```

### [6] fact-verdict — 综合判定

| 字段 | 内容 |
|------|------|
| **Input** | `03-fact-checked.json`（含 basic_check + source_credibility + internal_consistency） |
| **Output** | `04-verdicts.json` + 文件分发 |
| **工具** | 纯规则（阈值判定） |
| **调 LLM** | 否 |
| **回滚成本** | 几乎为零 |

**判定矩阵**:
```
pass = basic_check==pass AND source_credibility>=medium AND internal_consistency==pass
suspect = basic_check==pass AND (source_credibility==low OR internal_consistency==fail)
reject = basic_check==fail

pass → verified/<task>_<worker>_verified.md
suspect → suspect/<task>_<worker>_suspect.md
reject → rejected/<task>_<worker>_rejected.md（附原因）→ 触发 Commander 重试
```

**重试指令格式**（发给 Commander）:
```json
{
  "type": "retry",
  "task_id": "JOB-002",
  "worker": "worker-tech",
  "reason": "rejected: 3 claims failed basic_check",
  "failed_claims": ["claim-005: 数值异常", "claim-007: 日期不合理"],
  "suggested_fix": "检查素材数据准确性，重新生成科技版文章"
}
```

---

## 七、阶段 2：交叉验证（第二道防线）

**前置条件**: 至少 2 个不同 Worker 的产出通过阶段 1（status=pass）。

### [7] cross-pairwise — 两两对比

| 字段 | 内容 |
|------|------|
| **Input** | `verified/` 下 ≥2 个文件 |
| **Output** | `05-pairwise.json` — 每对 worker 的重叠 claim 对比 |
| **工具** | LLM |
| **调 LLM** | 是 |
| **回滚成本** | 中 |

**对比内容**:
```
worker-news vs worker-finance:
  重叠 claim:
    "央行降准0.5%" — news: ✓  finance: ✓  → agree
    "释放资金约1万亿" — news: ✓  finance: ✗ (未提到) → news-only
    "上证3250点" — news: ✓  finance: ✓  → agree
    "某公司Q2营收580亿" — news: ✗  finance: ✓  → finance-only
```

**05-pairwise.json 格式**:
```json
{
  "pairs": [
    {
      "pair": ["worker-news", "worker-finance"],
      "overlap_count": 3,
      "agreed": 2,
      "disagreed": 0,
      "news_only": 1,
      "finance_only": 1,
      "agreement_rate": 1.0
    }
  ]
}
```

### [8] cross-triangulate — 三角验证

| 字段 | 内容 |
|------|------|
| **Input** | `05-pairwise.json` |
| **Output** | `06-triangulated.json` — 3+ 源一致确认的 claims |
| **工具** | 纯规则 |
| **调 LLM** | 否 |
| **回滚成本** | 几乎为零 |

**三角验证规则**: 同一个 claim 被 ≥3 个不同方向的 Worker 独立确认 → 升级为 "triangulated"（高置信度）。

```
"央行降准0.5%":
  worker-news ✓
  worker-finance ✓
  → 只有 2 个源，不满足 3 源要求 → 置信度: medium

如果 worker-culture 也提到了（虽然它不是财经 worker）→ 3 源 → high
```

**置信度分级**:
| 源数量 | 置信度 |
|--------|--------|
| 1 | low — 孤证 |
| 2 | medium — 需要更多验证 |
| ≥3 | high — 可信 |

### [9] cross-contradiction — 矛盾检测

| 字段 | 内容 |
|------|------|
| **Input** | `05-pairwise.json`（disagreed 项）+ `verified/` 原文 |
| **Output** | `07-contradictions.json` |
| **工具** | LLM |
| **调 LLM** | 是 |
| **回滚成本** | 中 |

**矛盾类型**:
| 类型 | 示例 | 处理 |
|------|------|------|
| **数值冲突** | worker-A 说"营收 580 亿"，worker-B 说"营收 620 亿" | 两个都标记 suspect，发重试 |
| **事实冲突** | worker-A 说"气候协议通过"，worker-B 说"气候协议否决" | 两个都驳回 |
| **时间冲突** | worker-A 说"6月发布"，worker-B 说"7月发布" | 查最新来源 |

### [10] evidence-chain — 拼凑证据链

| 字段 | 内容 |
|------|------|
| **Input** | `06-triangulated.json` + `05-pairwise.json` + `verified/` |
| **Output** | `08-evidence-chain.md` — 环环相扣的证据链 |
| **工具** | LLM |
| **调 LLM** | 是 |
| **回滚成本** | 中 |

**核心逻辑**: 不是简单汇总。是找出 claims 之间的**因果/时序/逻辑关系**，拼成一条链。

```
孤立的 claims:
  claim-001: 央行降准 0.5%
  claim-002: 上证收报 3250（+0.8%）
  claim-003: 某公司 Q2 营收 580 亿（+12%）
  claim-004: 某公司海外收入占比 34%

拼成证据链:
  央行降准 0.5%（政策宽松）
    → 上证涨 0.8%（市场正面反应）
      → 某公司 Q2 营收 +12%（受益于政策环境？需验证：海外占比 34% 说明增长不完全靠国内政策）
```

**08-evidence-chain.md 格式**:
```markdown
# 证据链: 2026年7月1日

## 链 1: 货币政策 → 市场反应
**置信度: high** (3源三角验证)
1. [triangulated] 央行降准0.5% — 来源: news✓ finance✓ culture✓
2. [agreed] 上证+0.8% — 来源: news✓ finance✓
3. [inferred] 降准是市场上涨的核心催化剂 — 逻辑链完整

## 链 2: 企业财报
**置信度: medium** (2源)
1. [agreed] 某公司Q2营收580亿(+12%) — 来源: finance✓ tech✓
2. [single] 研发投入89亿(15.3%) — 来源: finance only → ⚠️ 孤证
3. [single] 海外收入占比34% — 来源: finance only → ⚠️ 孤证

## 断裂点（需要补证）
- 证据链 2 的 claim 2-3 只有 1 个源 → 需要第二个 Worker 验证
- 链 1 和链 2 之间的因果关系未验证 → 需要 World 自己的数据支撑
```

---

## 八、阶段 3：汇总与假设

### [11] summary-synthesize — 阶段性结论

| 字段 | 内容 |
|------|------|
| **Input** | `08-evidence-chain.md` + `verified/` |
| **Output** | `09-summary.md` |
| **工具** | LLM |
| **调 LLM** | 是 |

从证据链中提炼**当前可以确信的结论**。区分"已知"和"推测"。

```markdown
# 阶段性结论 — 2026-07-01

## 可以确信的（多源验证通过）
- 央行于7月1日降准0.5%，释放约1万亿长期资金
- 上证当日收涨0.8%，深证+1.2%
- 某公司Q2营收580亿(+12%)，净利142亿(+18%)

## 部分可信的（需要更多验证）
- 某公司研发投入占比15.3%（仅1源）→ 需要第二个Worker确认
- 某公司海外收入占比34%（仅1源）→ 需要第二个Worker确认

## 尚未验证的
- 降准与公司业绩之间的因果关系
- 海外增长是否与国内政策无关
```

### [12] hypothesis-generate — 新假设

| 字段 | 内容 |
|------|------|
| **Input** | `11-gaps.md`（信息缺口）+ `09-summary.md` |
| **Output** | `10-hypotheses.md` — 值得验证的新假设 |
| **工具** | LLM |
| **调 LLM** | 是 |

**假设生成规则**: 从已验证的数据和已发现的缺口，倒推出"如果 X 是真的，那 Y 应该也能观察到"。

```markdown
# 新假设 — 2026-07-01

## H1: 海外增长独立于国内政策
- 触发: 海外收入占比34%（但仅1源）
- 可验证: 找该公司的海外市场分区域数据 → 发 research task
- 如果为真: 公司增长不依赖国内货币政策，抗风险能力强
- 优先级: high

## H2: 研发投入与毛利率正相关
- 触发: 研发占比15.3%（仅1源），净利增长18%>营收增长12%
- 可验证: 查过去8个季度的研发占比 vs 毛利率走势 → 发 research task
- 如果为真: 研发是利润增长的核心驱动，而非成本负担
- 优先级: medium
```

### [13] gap-detect — 信息缺口

| 字段 | 内容 |
|------|------|
| **Input** | `08-evidence-chain.md` + `06-triangulated.json` |
| **Output** | `11-gaps.md` |
| **工具** | 纯规则 |
| **调 LLM** | 否 |

**缺口检测规则**:
```
1. 孤证缺口: triangulated_count < 2 的 claim → 需要补证
2. 断裂缺口: 证据链中两个环节之间的因果关系未被数据覆盖
3. 盲区缺口: 根据 GOAL.md 的目标范围，某些领域完全没有数据
4. 时效缺口: 数据时间戳过期（如"最新财报"但已过了一个季度）
```

### [14] report-strategic — 回报 Strategic Bee

| 字段 | 内容 |
|------|------|
| **Input** | `09-summary.md` + `10-hypotheses.md` + `11-gaps.md` |
| **Output** | `reports/strategic-<date>.md` |
| **工具** | LLM（组装） |
| **调 LLM** | 是 |
| **消费者** | **Strategic Bee** ← 这是最终交付对象 |

```markdown
# World Bee 报告 — 2026-07-01

## 数据概况
- 4 个 Worker 提交产出
- 通过验证: 12 claims
- 驳回: 3 claims（已触发重试）
- 证据链: 2 条（1 条 high 置信度，1 条 medium）

## 阶段性结论
<09-summary.md 的精简版>

## 值得验证的新假设（按优先级）
1. [high] H1: 海外增长独立于国内政策 — 可验证，影响大
2. [medium] H2: 研发投入与毛利率正相关 — 需要历史数据

## 当前信息缺口（需要 Strategic Bee 判断方向）
- Q: 海外的34%是来自哪些市场？需要启动针对性调研吗？
- Q: 某公司的同行对比数据缺失，需要做竞品分析吗？

## 下一次报告
预计 2026-07-08（或当 verified/ 新增 ≥5 条时触发）
```

---

## 九、重试闭环

Worker 出错 → World 检测 → Commander 重试：

```
Worker (JOB-002) 提交产出
    │
    ▼
World: [3] fact-check-basic → 3 claims failed
World: [6] fact-verdict → reject
    │
    ▼
Commander: 收到 retry 指令 {"task_id": "JOB-002", "reason": "...", "suggested_fix": "..."}
Commander: 重新派发 JOB-002（携带修复建议）
    │
    ▼
Worker: 重新生成（这次参考了建议）
    │
    ▼
World: 再次进入 [1] data-ingest → ... → 通过 or 再驳回
```

重试上限：同一 task 最多重试 3 次。3 次后 → 标记为 "failed_permanent"，上报 Strategic Bee。

---

## 十、后期合并路径

细碎 skill 跑通后，相邻的纯规则 skill 可以合并：

| 当前（14 步） | 合并后 |
|-------------|--------|
| [1] data-ingest + [2] data-normalize | → `ingest-and-normalize`（1 读 + 1 LLM → 1 步）|
| [3] basic-check + [4] source-check + [5] internal-check + [6] verdict | → `fact-check-pipeline`（4 步 → 1 步，LLM 一次调用覆盖四个维度）|
| [7] pairwise + [8] triangulate + [9] contradiction | → `cross-validate`（3 步 → 1 步）|
| [11] summary + [12] hypotheses + [13] gaps | → `synthesize`（3 步 → 1 步）|

合并后从 14 步 → 6 步：
```
ingest-and-normalize → fact-check-pipeline → evidence-chain → cross-validate → synthesize → report-strategic
```

---

## 十一、Skill 清单汇总

| # | Skill | 阶段 | 调 LLM | 回滚成本 | 后期合并 |
|---|-------|------|--------|---------|---------|
| 1 | data-ingest | 0 | 否 | 极低 | → ingest-and-normalize |
| 2 | data-normalize | 0 | 是 | 低 | → ingest-and-normalize |
| 3 | fact-check-basic | 1 | 否 | 很低 | → fact-check-pipeline |
| 4 | fact-check-source | 1 | 是 | 中 | → fact-check-pipeline |
| 5 | fact-check-internal | 1 | 是 | 中 | → fact-check-pipeline |
| 6 | fact-verdict | 1 | 否 | 极低 | → fact-check-pipeline |
| 7 | cross-pairwise | 2 | 是 | 中 | → cross-validate |
| 8 | cross-triangulate | 2 | 否 | 极低 | → cross-validate |
| 9 | cross-contradiction | 2 | 是 | 中 | → cross-validate |
| 10 | evidence-chain | 2 | 是 | 中 | 保留独立 |
| 11 | summary-synthesize | 3 | 是 | 中 | → synthesize |
| 12 | hypothesis-generate | 3 | 是 | 中 | → synthesize |
| 13 | gap-detect | 3 | 否 | 极低 | → synthesize |
| 14 | report-strategic | 3 | 是 | 中 | 保留独立 |

---

## 十二、与 PM Bee / Strategic Bee 的接口

```
Worker Bee → World Bee → Strategic Bee
                │
                ├─ 驳回 → Commander → 重试 Worker
                └─ 通过 → 证据链 → 结论+假设 → Strategic Bee

PM Bee 的 PLAN.md 定义执行范围
  → World Bee 的 gap-detect 参考 PLAN.md 判断"哪些领域完全没有数据"
  → Strategic Bee 的 horizon-scan 参考 World Bee 的假设列表
```

**World Bee 不直接和 Worker Bee 通信**——只通过 Commander 发重试指令。**不直接和 PM Bee 通信**——只参考 PLAN.md 做 gap 检测。**唯一的外部消费者是 Strategic Bee**。
