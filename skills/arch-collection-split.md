---
name: arch-collection-split
description: 短篇集专用——先把集子拆成单篇，再对每篇跑 arch-novel-split。福尔摩斯、短篇合集、连作集。
trigger: 拆短篇集, 拆合集, 拆集子, 短篇, collection split, 分篇, 拆故事
tools:
  - fs_read_file
  - fs_write_file
  - fs_search_files
category: architecture
---

# 短篇集拆分

短篇集不是长篇——每篇是独立叙事。先拆篇，再切原子。

## 存储位置

```
~/.worker-bee/arch/texts/<合集名>/
├── index.md              ← 篇目列表
├── <篇名-slug>/
│   ├── source.md
│   └── atoms.md          ← arch-novel-split 产出
├── <篇名-slug>/
│   ├── source.md
│   └── atoms.md
└── ...
```

## Phase 1: 拆篇

1. 识别篇目边界：篇目标题、编号、明确的故事结尾+新开头
2. 逐篇提取到 `<slug>/source.md`
3. 写 index.md：

```markdown
# 合集: 福尔摩斯探案全集
## 篇数: 56
## 已分析: 0/56

| # | 篇名 | slug | 字数 | 状态 |
|---|------|------|------|------|
| 1 | 血字的研究 | study-in-scarlet | 42,000 | pending |
| 2 | 四签名 | sign-of-four | 38,000 | pending |
| ... | ... | ... | ... | ... |
```

## Phase 2: 逐篇切原子

对每篇跑 arch-novel-split。Agent 按 index.md 里的 `pending` 逐篇处理，切完更新状态为 `atoms-ready`。

## Phase 3: 逐篇打标签

对每篇跑 arch-novel-tag。更新状态为 `tagged`。

## 跨篇分析

多篇标完后出合集级统计：

```
✓ 合集统计: 56篇, 总字数 1,042,000
  平均每篇: 72原子 / 18,600字
  线索密度区间: 8% (波希米亚丑闻) ~ 35% (斑点带子)
  转折频率: 0.3次/篇（大多数短篇没有真正的转折）
  收束密度: 稳定 5-8%，全合集一致
```

## 约束

- 每篇独立目录，不混原子
- slug 全小写、连字符
- 极短篇（<2,000字）可能只有 10-15 原子——正常
- index.md 追踪进度，每次操作后更新
- 超过 50 篇的合集每 10 篇报告一次进度
