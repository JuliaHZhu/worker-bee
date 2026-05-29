# Architecture Prototype Bee — 结构规约器

> *架构是规约，不是建造。*

## 问题

你脑子里有一个模糊的想法（"我想做一个战斗有深度的 roguelike"）。它"将出未出" — 还没有成型。在写代码之前，需要先规约到不可再分的约束。

## 第一原理

**代码很贵，结构很便宜。**如果结构还没清晰就开始写代码，你会无穷无尽地重构。LLM 应该逼你剥光模糊，直到只剩约束。

## 行为

1. **质询** — 问什么，不是问怎么
   - "目标是什么？"而不是"用什么框架？"
   - "必须为真的是什么？"而不是"怎么实现？"
2. **规约** — 一直问"为什么"，直到碰到不能再拆的约束
   - 停在"因为这就是物理现实"或"因为这就是用户需要"的答案
   - 如果一个约束还能拆，它就不是核心约束
3. **估算** — 给每个模块画大 O 的直觉
   - 时间 vs 空间权衡
   - 什么操作在大规模时占主导？
4. **输出** — 模块拆分成一组正交基底
   - 高内聚：每个模块只做一件事
   - 低耦合：模块通过窄接口交流
   - 每个模块的接口就是它的契约

## 外源信息素格式

文件路径：`~/.worker-bee/arch/<project>.md`

```markdown
# Architecture: Simple Roguelike

## Goal
A turn-based roguelike where combat depth comes from positional tactics, not stat grinding.

## Core Constraints
- **Constraint 1**: 必须在 2015 年笔记本上跑 60fps（无需 GPU）
- **Constraint 2**: 不升级也能通关（靠技巧）
- **Constraint 3**: 地图生成必须产生可通关的地牢（没有死锁）

## Modules

### Map Generator
- **Responsibility**: 程序化地牢布局 + 敌人配置
- **Interface**: Input(种子, 难度) → Output(地图, 实体列表)
- **Algorithm**: 细胞自动机 + A* 可通性检查
- **Complexity**: O(n²) 对于 n×n 网格，n≤50 可接受
- **Dependencies**: 无

### Combat Engine
- **Responsibility**: 回合制解算、视野、伤害计算
- **Interface**: Input(玩家动作, 实体状态) → Output(新状态, 事件)
- **Algorithm**: BFS 算视野，事件队列排行动顺序
- **Complexity**: O(e log e) 对于 e 个实体
- **Dependencies**: Map Generator (读取地图)

### Renderer
- **Responsibility**: 带颜色的 ASCII 显示
- **Interface**: Input(实体位置, 地图) → Output(终端缓冲区)
- **Algorithm**: 双缓冲终端输出
- **Complexity**: O(n²) 对于 n×n 视口
- **Dependencies**: Map Generator, Combat Engine

## Tradeoffs
- 选择 ASCII 而非 sprite：降低美术依赖，满足约束 1
- 选择 BFS 而非 raycasting 算视野：更简单、确定性、网格足够用
```

## 正交基底 = 高内聚 + 低耦合

在线性代数里，正交基底是一组向量：
- 每个向量指向独特方向（无冗余）
- 它们张成整个空间（完整覆盖）
- 可以组合表达空间中任意点

在架构中：
- **每个模块 = 一个基底向量** — 只处理问题的一个维度
- **无重叠** — 两个模块共享责任 = 基底不正交
- **完整覆盖** — 每个需求都有人负责
- **可组合** — 模块通过接口组合（点积）

## Skill 契约

见 `worker_bee/skills/architect.md`

## 为什么能用

- LLM 不做设计 — 它**质询**并记录
- 大 O 估算强迫早期思考瓶颈
- Tradeoff 部分记录决策，免得以后忘了为什么这么做
- 架构文档是人和 LLM 之间的**契约**：结构先确认，代码后写

## 使用场景

- 需要结构清晰化才实现的游戏原型
- 数据流复杂的研究系统
- 任何"模糊想法 → 代码"跳跃太大的项目
