# Skill 自检清单

> 写完 SKILL.md 后，逐条打勾，再跑 `wb skill lint <name>` 验证。

## 前置

- [ ] 文件名和 frontmatter `name` 一致（如 `web-research.md` ↔ `name: web-research`）
- [ ] 文件放在 `skills/` 根目录，不嵌套子目录

## Frontmatter

- [ ] `name` — 和文件名匹配
- [ ] `description` — 一句话说明用途
- [ ] `trigger` — 至少一个关键词，逗号分隔
- [ ] `tools` — 非空列表，每个工具在 `wb deck list` 中存在
- [ ] `category` — 已存在分类或新分类（搜索 `grep "category:" skills/*.md` 看现有）
- [ ] `version` — 语义化版本，如 `"1.0.0"`
- [ ] `composability` — `atomic` | `composable`，不填默认视为 atomic

## Body 结构（按顺序）

- [ ] `# Title` — 和 `name` 对应
- [ ] 功能说明 — 一段，说清这个 skill 解决什么问题
- [ ] `## Input` — 列出每个参数名、类型、是否可选、默认值
- [ ] `## Output` — 说明返回什么格式、什么内容
- [ ] `## Error Handling` — 至少列出 2 种失败场景及应对方式
- [ ] `## Safety` — 如果用了危险工具，必须写；纯读操作可以写 "read-only — safe"
- [ ] `## Examples` — 至少 2 个：一个正常场景，一个错误/边界场景

## 安全（如果 tools 包含以下任一）

| 工具 | 必须写的安全声明 |
|---|---|
| `fs_write_file` | 什么情况下写入、是否需要用户确认、是否会覆盖 |
| `fs_delete_file` / `fs_move_file` | 操作前是否确认、影响范围 |
| `sys_terminal` | ALLOWLIST（允许命令清单）、禁止命令、确认策略 |
| `deck_manage` | 什么条件下切换 deck、是否会改变可用工具集 |

## 禁止项

- [ ] 没有 `rm -rf /` 或类似破坏性命令示例
- [ ] 没有 `curl ... \| sh` 或 `wget ... \| sh` 模式
- [ ] 没有 sudo 配合危险操作的示例
- [ ] body 长度 > 200 字（信息密度检查）

## 验证

```bash
# 1. 结构检查
wb skill lint my-skill

# 2. 执行测试
wb skill test my-skill --levels unit,integration

# 3. 全部通过后再提交
```

## 评分目标

| 等级 | lint score | test score | 说明 |
|---|---|---|---|
| 🥇 优秀 | ≥ 0.95 | 1.00 | 可直接合并 |
| 🥈 合格 | ≥ 0.85 | ≥ 0.90 | 修完 WARN 后合并 |
| 🥉 需改 | < 0.85 | < 0.90 | 重写或拆分 |
