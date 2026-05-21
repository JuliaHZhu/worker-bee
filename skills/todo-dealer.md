---
name: todo-dealer
description: TODO Ball Machine人生操作系统 — 基于抽球机制的个人日常任务管理系统
triggers:
  - TODO Ball Machine
  - ball machine
  - todo_dealer
  - 人生系统
  - 抽球
  - block
  - 今日安排
  - 场次
  - 盒子配额
tools:
  - todo_dealer
---

# TODO Ball Machine 人生操作系统 v2.0

## 系统概述

TODO Ball Machine 人生操作系统是一个基于"抽彩球"机制的个人日常任务管理系统。

### 核心概念

- **彩球**: 每个任务是一个彩球，从对应盒子里随机抽取
- **盒子**: 6 个任务分类（A-F），每个盒子有配额限制
- **场次**: 一天 3+1 个场次（am/pm/evening/overtime）
- **Block**: 一个具体的任务执行单元

### 6 个盒子

| 代号 | 名称     | 配额 | Emoji |
|------|----------|------|-------|
| A    | 博士工作 | 21   | 🎓    |
| B    | AI 创业  | 21   | 🤖    |
| C    | 健康运动 | 15   | 💪    |
| D    | 治愈休息 | 14   | 🧘    |
| E    | 空间探索 | 10   | 🌍    |
| F    | 家务整理 | -    | 🏠    |

## Tool 用法

使用 `todo_dealer` tool，通过 `action` 参数指定操作：

### 只读操作

- `dashboard` — 系统仪表盘（今日安排 + 配额概览）
- `today` — 今日场次状态
- `box_list` — 盒子配额列表
- `cycle_status` — 周期状态统计

### 写入操作

- `draw` + `session` — 抽取指定场次（am/pm/evening/overtime）
- `quick_draw` — 快速抽取三场（am+pm+evening）
- `redraw` + `session` — 重抽指定场次（退回旧球 + 抽取新球）
- `edit` + `session` + `content` — 编辑场次内容
- `complete` + `block_id` — 标记 block 为已完成

### 示例

```
todo_dealer(action="today")
todo_dealer(action="draw", session="pm")
todo_dealer(action="quick_draw")
todo_dealer(action="complete", block_id="BLOCK-20260406-123456-ABCDE")
todo_dealer(action="edit", session="am", content="修改后的任务内容")
```

## 工作流

1. **晨间**: 用 `quick_draw` 抽取三场
2. **执行中**: 完成一个 block 后用 `complete` 标记
3. **傍晚**: 查看 `today` 了解完成度
4. **周期回顾**: 用 `cycle_status` 看整体进度

## 约束

- 30 天一个周期，每个盒子有固定配额
- 抽取后球从池子中移除（不重复）
- 重抽会将旧球退回球池
