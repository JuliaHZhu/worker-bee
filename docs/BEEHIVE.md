# Worker Bee Hive — 蜂群架构设计

> 蜂群不是万能蜂，是多只专精蜂。每只穿一件 skill 衣服，产出外源信息素，用 git 管理。人是养蜂人/指挥官，也是免疑记忆库。

---

## 一、总论：免疫系统比喻

| 免疫学 | 蜂群 |
|---------|------|
| 免疫记忆库 | 人类 — 定义标记物与标记空间 |
| 树突状细胞 | SupervisorBee — 采样信息素，决定下一步激活哪些蜂 |
| B/T 细胞 | 执行蜂 — 穿上 skill，执行单一任务 |
| 抗原/信息素 | Markdown 文件 — 人工可读，可编辑，可审查 |
| 组织液 | Git — 信息素扩散的介质 |
| 亲和力成熟 | 人的经验积累 — 标记物从粗糙变得精确 |

---

## 二、蜂的分类

### 2.1 生产蜂（执行线）

生产蜂的工作流是**序列化**的，下一只蜂的输入是上一只蜂的产出。

| 蜂名 | 角色 | 产出 |
|------|------|-------|
| **StyleDeconstructorBee** | 文风拆解蜂 | `句式模板库.md` |
| **MaterialCuratorBee** | 素材分类蜂 | `素材标签库.md` |
| **EssayArchitectBee** | 结构搭建蜂 | `五段三分大纲.md` |
| **EssayDrafterBee** | 初稿写作蜂 | `初稿.md` |
| **StyleValidatorBee** | 风格检验蜂 | `风格检查报告.md` |
| **LogicReviewerBee** | 论证审查蜂 | `逻辑审查报告.md` |
| **PolishBee** | 润色蜂 | `润色稿.md` |
| **GradeBee** | 评分蜂 | `评分细则.md` |
| **CoachBee** | 教学蜂 | `写作指南.md` |

### 2.2 探路蜂（DoctorBee）

探路蜂**不生产端产品**，只产出地图。

| 蜂名 | 产出 | 需要人拍板 |
|------|-------|------------|
| **ResearchBee** | `知识地图.md` — 把"不懂"变成"懂了" | 审阅、标注缺失 |
| **IdeaBee** | `方案比选.md` — 先盘点现有 skills 再组合 | 选择方案 |
| **ArchBee** | `架构图纸.md` — 核心变动或大 feature | 拍板是否重构 |

### 2.3 副官蜂（AideBee）

**不执行**，只追问。

| 蜂名 | 产出 |
|------|-------|
| **AideBee** | 人的清晰决策 |

**模式：grill me**
- 产出不是代码/文档
- 产出是**人在追问中自己形成的决定**
- 帮助人发现真正的需求
- 引导人去清晰地定义"这件事到底是什么"

### 2.4 调度蜂（SupervisorBee = 树突状细胞）

**不执行生产任务**，只**采样信息素并激活下一批蜂**。

**核心机制：**
1. **采样**— 读取 workspace 里所有 `.md` 文件
2. **检测**— 判断哪些信息素浓度足够高（例如：多只蜂共同提及的发现）
3. **呈递**— 根据信息素类型，决定激活下一只/下一批蜂
4. **消散**— 本轮任务完成，session 清空

### 2.5 调研蜂（SwarmResearchBee）

**蚁群式探索**—多模型并行搜索，成功的探索自动放大。

| 蜂名 | 产出 |
|------|-------|
| **SwarmResearchBee** | `蚁群调研报告.md` — 区分多蜂共识与单蜂发现 |

---

## 三、信息素协议（Pheromone Protocol）

### 3.1 信息素就是 Markdown

每只蜂的产出都是一个或多个 `.md` 文件，存在 git repo 里。

```
workspace/
├── pheromones/                    # 信息素库
│   ├── 2026-05-24-style-deconstructor/
│   │   └── 句式模板库.md
│   ├── 2026-05-24-material-curator/
│   │   └── 素材标签库.md
│   └── ...
├── standards/                    # 人定义的标记空间
│   ├── 申论评分标准-v1.md
│   ├── 人民日报文风特征-v2.md
│   └── 素材分类体系-v1.md
└── decisions/                    # 人的决策记录
    └── 2026-05-24-重构决策.md
```

### 3.2 信息素的命运

| 状态 | 含义 | 处理 |
|------|------|-------|
| 新鲜（刚生成） | 未被 SupervisorBee 采样 | 等待采样 |
| 浓度高（多蜂共识） | 多只蜂跳过同一个发现 | 被 SupervisorBee 优先呈递 |
| 浓度低（单蜂发现） | 只有一只蜂提及 | 标记为"待验证"，不优先跟进 |
| 蒸发（失败） | 蜂崩溃或产出空白 | 自动消失，不需人删除 |

### 3.3 信息素的形式

每个信息素文件必须包含：

```markdown
---
produced_by: EssayDrafterBee
model: kimi-k2.6
timestamp: 2026-05-24T14:32:00
inputs:
  - style-template-2026-05-24.md
  - material-tags-2026-05-24.md
  - outline-2026-05-24.md
status: fresh  # fresh | high-density | low-density | stale
---

# 初稿：乡村振兴

...

## 人的批注区
- [ ] 这段不够政策
- [x] 开头可以
```

---

## 四、人的角色：免疑记忆库

### 4.1 标记物（Marker）

人定义**什么值得关注**。

例如申论作业的标记物：
- 政策契合度
- 逻辑严密性
- 文风一致性
- 论据新颖性

这些标记物就是评价坐标系的**基矢**。

### 4.2 标记空间（Marker Space）

人定义**评价的维度**。

新手养蜂人：
```
标记空间 = {关键词命中率}  # 1维
```

老手养蜂人：
```
标记空间 = {
  政策契合度: 0.4,
  语气流向: 0.3,
  数据源立场: 0.2,
  民众可读性: 0.1
}  # 4维，含权重
```

**人不改蜂的工作方式，只改评价坐标系。**

### 4.3 AideBee 帮人发现标记物

人以为自己在乎"逻辑严密性"→ AideBee 追问 → 人发现自己更在乎"打动考官" → 标记空间从 4 维扩展到 5 维，新增"感染力"

---

## 五、部署模型：快速展开 / 快速收回

不需要 Docker，不需要常驻进程。

```bash
# 展开一只蜂
git clone https://github.com/JuliaHZhu/worker-bee-hive.git
cd worker-bee-hive
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 main.py --skill essay-drafter --input outline.md
# 跑完
git add output/ && git commit -m "bee: essay-drafter output" && git push
cd .. && rm -rf worker-bee-hive  # 收回
```

**蜂的生命周期 = 一次 clone → run → push → rm -rf**。

云服务器只是执行环境，不是家。崩溃就重装，信息素在 git 里。

---

## 六、工作流示例

### 6.1 单蜂序列流

```
人: 我想写一篇乡村振兴的申论

SupervisorBee: 采样 → 发现空白 → 激活 StyleDeconstructorBee

StyleDeconstructorBee: 读人民日报 → 输出 句式模板库.md

SupervisorBee: 采样 → 发现新鲜信息素 → 激活 MaterialCuratorBee

MaterialCuratorBee: 整理素材 → 输出 素材标签库.md

...

人: 读 GradeBee 的 评分细则.md → 批注“这篇需要再练” → 写入 decisions/
```

### 6.2 蚁群并行流

```
人: 我想研究短视频脚本生成

SupervisorBee: 激活 SwarmResearchBee

SwarmResearchBee: 并行启动 5 只不同模型的蜂 → 输出 5 份笔记

SupervisorBee: 采样 5 份笔记 → 检测浓度 → 发现"悬念+数字"是多蜂共识

SupervisorBee: 激活 IdeaBee → IdeaBee 组合方案 → 输出 方案比选.md

人: 选择方案 B → 写入 decisions/
```

### 6.3 探索流

```
人: 我想做一个小红书标题生成器

AideBee: grill me → 人发现自己并不是要标题，而是要"可复用的短文案生成 skill"

SupervisorBee: 激活 ArchBee

ArchBee: 读现有代码 → 发现当前系统单线程 → 输出 架构图纸.md

人: 拍板“重构” → 写入 decisions/
```

---

## 七、总结

> **Worker Bee 蜂群 = 没有身体的免疫系统**
>
> 人定义"什么是入侵者"（标记物），信息素自动引导蜂群去处理。失败的探索自动沉没，成功的探索自动放大。
>
> 人不指挥每个 T 细胞，只定义"入侵者长什么样"。