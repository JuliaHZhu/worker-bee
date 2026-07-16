# Aristotle — 术语管理员

> **10 个 skills × 5 个 tools × 1 条铁律**
>
> 唯一铁律：AI 只能写 `drafts/`，人审阅后 merge 进 `dict.md` 或 `decisions/` 。

---

## 目录结构

```
bee-knowledge/
├── aristotle.py      # 本文件：10 skills + 5 tools
├── dict.md           # 术语词典（人维护）
├── decisions/        # 决策档案（人维护）
└── drafts/           # AI 草稿篮（AI 只能写这里）
```

---

## 怎么用

### 1. 作为模块引用

```python
from aristotle import define, drift_watch, dict_reader

# 写一个定义草稿
define("swarm", "在今天的讨论中，我们说 swarm 是...")

# 扫描日志里的漂移
drift_watch(open("chat.log").read())

# 查词典
print(dict_reader())
```

### 2. 作为 CLI

```bash
cd bee-knowledge

# 定义
python aristotle.py define "swarm" "上下文文本"

# 漂移检测
python aristotle.py drift_watch "日志内容"

# 清算草稿债务
python aristotle.py audit_debt
```

---

## Skills 一览

### Campaign Mode（7 个）

| Skill | 用途 | 输出文件 |
|-------|------|----------|
| `define` | 新词定义草稿 | `drafts/define-<term>.md` |
| `fork` | 一词多义记录 | `drafts/fork-<term>.md` |
| `resolve` | 解决 fork | `drafts/resolve-<term>.md` |
| `align` | 用词不当纠正 | `drafts/align-<term>.md` |
| `decide` | 争议拍板 | `drafts/decide-<NNNN>-<slug>.md` |
| `grill` | 定义追问 | `drafts/grill-<term>.md` |
| `relate` | 术语关系注解 | 返回文本（调用方自己插入 draft） |

### Research Mode（3 个）

| Skill | 用途 | 输出文件 |
|-------|------|----------|
| `drift_watch` | 检测术语漂移 | `drafts/drift-YYYY-MM-DD.md` |
| `ammo_prep` | 为其他 Bee 准备术语包 | `drafts/ammo-<topic>.md` |
| `audit_debt` | 清算草稿债务 | `drafts/audit-YYYY-MM-DD.md` |

---

## Tools 一览

| Tool | 功能 | 权限 |
|------|------|------|
| `dict_reader` | 读 `dict.md` | 只读 |
| `decision_reader` | 读 `decisions/` | 只读 |
| `draft_writer` | 写 `drafts/*.md` | **唯一可写入口** |
| `log_scanner` | 在文本中检索术语 | 只读 |
| `git_commit` | 提交 drafts/ 变更 | 只提交 drafts/ |

---

## 人的工作

AI 不会做的事：
- 把 draft merge 进 `dict.md`
- 把 decide draft 移进 `decisions/`
- 删除已审阅的 draft

这些只能由人执行。

---

## 设计文档

详见 `docs/design/aristotle-v4.md`
