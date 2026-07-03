# Commander Bee — 前线小队长

> *菜谱是死的，执行是活的。拿到菜谱后创造性地利用它。缺什么就回头要。*

---

## 一、Commander Bee 在蜂群中的位置

```
Cardmaster Bee（战役总指挥室）
    │ 标的物规格书（做什么）
    ▼
Chef Bee（主厨）
    │ PLAN.md（大阶段 + 菜谱级 task）
    ▼
Commander Bee ← 你在这里
    │
    │ 创造性利用菜谱
    │ 缺信息 → 回头向 Chef 要
    │ 派发 Job + 回收结果
    ▼
Worker Bees（执行）
```

**Commander 不写菜谱，不选动作，不验证结果。** 它只做一件事：**把菜谱变成现实**。菜谱是完美的，现实是不完美的。Commander 弥合这个差距。

---

## 二、核心能力：有效利用

### 什么是"有效利用"

Chef 的 PLAN.md 是过饱和的——所有 task、容错路径、资源估算全在里面。Commander 拿到后不是照单全发，而是：

1. **判断可执行性**: 这个 task 的前置条件现在满足吗？真能做还是纸面上能做？
2. **分批派发**: 不一次性全发。按依赖关系分批，前一批有结果再发下一批
3. **缺信息就回头要**: "T-002 需要 T-001 的产出才能开始，但 T-001 的产出里缺了某个数据——Chef，你菜谱里没写这个数据去哪找，给我补一下"
4. **现场调整**: Worker 交了结果但和预期有偏差 → 判断偏差在可接受范围内就放行，继续下一个 task。不因为小偏差卡住整条流水线

**Commander 的创造力不是"发明新计划"——是"让计划在现实中跑通"**。

---

## 三、7 个 Skill

```
PLAN.md
    │
    ▼
[1] plan-ingest      → 提取当前可执行的大阶段
[2] gap-assess       → 检查信息是否充足 → 不够 → 向 Chef 要
[3] task-batch       → 分组（并行组 + 串行组）
[4] task-dispatch    → 写入 Job Board
    │
    ▼
[5] progress-monitor → 追踪执行状态
[6] result-recover   → 回收结果，比对验收标准
    │
    ├─ 通过 → 下一批
    ├─ 偏差可接受 → 放行
    └─ 严重偏差 → 重试 or [7] escalate → Cardmaster
```

### [1] plan-ingest — 读菜谱

| 字段 | 内容 |
|------|------|
| **Input** | Chef Bee 的 `PLAN.md` |
| **Output** | 当前可执行的大阶段列表 + 阻塞项识别 |
| **工具** | `fs_read_file` |
| **调 LLM** | 否（纯规则） |

**操作**: 扫描 PLAN.md，提取每个 task 的状态（backlog / ready / doing / done）和前置依赖。找出所有"前置全部 done，当前状态 backlog"的 task——这些是可以立即执行的。

```
PLAN.md → 
  可执行: [T-001, T-002]（无前置）
  等待中: [T-003]（依赖 T-001, T-002）
  已阻塞: []
```

### [2] gap-assess — 信息缺口评估

| 字段 | 内容 |
|------|------|
| **Input** | 可执行 task 列表 + 每个 task 的 Input 字段 |
| **Output** | 缺口清单（缺什么，向谁要）or 就绪 |
| **工具** | `fs_read_file`（检查 Input 文件是否存在），LLM 辅助判断 |
| **调 LLM** | 是（判断"缺的信息能自己解决还是必须问 Chef"） |

**这个 skill 是 Commander 创造性的核心体现。** 它不只是检查文件在不在——它判断**信息是否充分到可以开始执行**。

```
T-002 Input: "T-001 的产出 + 窗口回复"
  T-001 的产出: ✅ 存在（research/法规.md）
  窗口回复: ❌ 文件不存在
  → 缺口: 窗口回复缺失
  → 判断: 这个缺口 Commander 自己解决不了（需要人去打电话）
  → 动作: 向 Chef Bee 发请求：'T-002 需要窗口回复数据，但 PLAN.md 中 T-002 的容错路径已走到头。
           请 Chef 更新 T-002 的容错方案，或标记为"等待外部数据"并解锁 PLAN'
```

**请求格式**（Commander → Chef）:
```markdown
# Info Request: T-002 执行受阻

## 阻塞原因
T-002 的 Input 中"窗口回复"文件缺失（`research/窗口回复.md` 不存在）

## 已尝试的容错路径
- 容错 A: 电话 → 打不通
- 容错 B: 邮件 → 已发 3 天无回复
- 容错 C: 网络搜索 → 信息可信度低

## 需要 Chef 做什么
1. 更新 T-002 的容错方案（加入替代数据源）
2. 或者标记 T-002 为"等待外部数据"，更新依赖图
3. 同时确认 T-003（填表）是否可以先用低可信度信息开始
```

### [3] task-batch — 任务分组

| 字段 | 内容 |
|------|------|
| **Input** | 可执行 task 列表 + PLAN.md 的依赖图 |
| **Output** | 分组方案：并行组 + 串行组 |
| **工具** | 纯规则 |
| **调 LLM** | 否 |

**分批原则**:
1. 无相互依赖的 task → 同一批，并行派发
2. 同一批内如果有限资源冲突（如都是"自己"做）→ 按阻塞项优先级排序
3. 上一批全部 done 后，才发下一批

```
批次 1（并行）: T-001（查阅法规）∥ T-002（联系窗口）
批次 2（串行）: T-003（填表）← 依赖 T-001 + T-002
批次 3（串行）: T-004（提交）← 依赖 T-003
```

### [4] task-dispatch — 派发到 Job Board

| 字段 | 内容 |
|------|------|
| **Input** | 当前批次的 task 列表 + PLAN.md 的 task 菜谱 |
| **Output** | Job Board 上创建 N 个 Issue |
| **工具** | `sys_terminal`（wb job create） |
| **调 LLM** | 否（纯规则） |

每个 Job 包含：标题（从 Chef 的 task 标题）、描述（从 Chef 的 task 菜谱提取可执行部分）、验收标准、前置 Job ID。

### [5] progress-monitor — 进度追踪

| 字段 | 内容 |
|------|------|
| **Input** | Job Board 状态 |
| **Output** | 进度报告：哪些 done、哪些 blocked、哪些超时 |
| **工具** | `sys_terminal`（wb job status） |
| **调 LLM** | 否（纯规则） |

**异常检测**:
- Task 预计 45min，超过 2h 未完成 → 标记异常
- Worker 连续 3 次失败同一个 task → 触发 escalate
- 阻塞项超时（等外部回复超过预期天数）→ 触发 gap-assess 重新评估

### [6] result-recover — 回收结果

| 字段 | 内容 |
|------|------|
| **Input** | Job Board 上 status=done 的 task + 交付物文件 |
| **Output** | 验收判定：通过 / 可接受偏差 / 重试 |
| **工具** | `fs_read_file` + LLM 辅助验收 |
| **调 LLM** | 是（判断偏差是否可接受） |

**这是 Commander 创造性的第二个体现点。** Chef 的验收标准是理想的（"≥3 条条款，每条标注日期"），现实交付物可能有偏差（"只有 2 条有日期标注"）。Commander 需要判断：这个偏差能不能放行？

```
Chef 验收标准: ≥3 条相关条款，每条标注发布日期

Worker 交付: 3 条条款，2 条有日期，1 条日期标注为"2026年"（只有年份）
  → 偏差: 日期精度不足
  → Commander 判断: 可接受（年份够用了，填表不需要精确到日）
  → 放行 ✓

Worker 交付: 1 条条款（另外 2 条不相关）
  → 偏差: 数量不达标
  → Commander 判断: 不可接受
  → 重试（附说明"需要 ≥3 条直接相关的条款"）
  → 重试上限 3 次，第 4 次失败 → escalate
```

**放行标准**: 偏差不影响下游 task 的执行。填表需要的"注册资本数额"有了就行，日期精确到年够了。

### [7] escalate — 升级

| 字段 | 内容 |
|------|------|
| **Input** | 重试耗尽仍失败的 task + 失败日志 |
| **Output** | 升级报告 → Cardmaster Bee |
| **工具** | `fs_write_file` |
| **调 LLM** | 是（写升级报告） |

**Commander 不上报给 Strategic Bee——上报给 Cardmaster。** 因为这是战役层面的问题，不是战略层面的。

```markdown
# 升级报告: T-002 执行失败

## 失败 task
T-002: 联系工商局确认执行口径 — 已重试 3 次，全部失败

## 已尝试路径
1. 电话 → 无人接听
2. 邮件 → 无回复（5天）
3. 社交媒体搜索 → 信息矛盾不可用

## 阻塞影响
- T-003（填表）无法开始（依赖 T-002）
- 整条生产线停滞

## 建议（Cardmaster 决策）
- 选项 A: 放弃窗口确认，用低可信度数据填表（风险: 被驳回）
- 选项 B: 替换策略——改为委托代理公司（新动作类型: 交易）
- 选项 C: 等待（预期还需 N 天）
```

---

## 四、Commander 与其他 Bee 的关系

| 从谁接收 | 接收什么 | 做什么 |
|---------|---------|--------|
| Chef Bee | PLAN.md | 读菜谱，提取可执行 task |
| Chef Bee | 信息补充 | gap-assess 后回头要的 |
| Worker Bees | 交付物 | 回收结果，验收 |
| Cardmaster Bee | 标的物规格书（间接，通过 Chef） | — |

| 发给谁 | 发什么 | 何时发 |
|--------|--------|--------|
| Worker Bees | Job（到 Job Board） | task-dispatch |
| Chef Bee | 信息请求 | gap-assess 发现缺口 |
| Cardmaster Bee | 升级报告 | escalate |

---

## 五、设计原则

1. **菜谱是起点不是终点** — Commander 不质疑菜谱的内容，但有权判断"这个 task 现在能不能做"
2. **偏差可接受就放行** — 不等完美。Chef 的标准是目标，Commander 的标准是"能推动下一 task 就行"
3. **缺信息就喊** — 不硬撑。喊 Chef 补，不自己编
4. **不越级上报** — 升级给 Cardmaster（战役层），不直接找 Strategic（战略层）
5. **创造性不等于幻觉** — Commander 的创造力是"让计划在现实中跑通"的实战智慧，不是"发明不存在的数据"

---

## 六、信息素文件

```
~/.worker-bee/commander/<project>/
├── plan-snapshot.md      ← plan-ingest 时保存的菜谱快照
├── gap-log.md            ← 所有向 Chef 发出的信息请求记录
├── batch-log.md          ← 每批 task 的派发记录
├── progress.json         ← 当前进度（可执行/等待/阻塞/完成）
└── escalation-log.md     ← 升级报告存档
```
