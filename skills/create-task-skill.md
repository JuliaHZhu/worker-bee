---
name: create-task-skill
description: Use when creating a lightweight skill for information retrieval, summarization, or workflow guidance. No custom code needed — just tool composition and prompt design.
trigger: create task skill, lightweight skill, search summary skill, workflow skill, information skill, 创建任务skill, 轻量skill, 搜索总结skill, 工作流skill
tools:
  - fs_read_file
  - fs_write_file
  - fs_search_files
  - skill_test
category: skill-authoring
phase: implement
---

# Create Task Skill

> Phase: **implement** — you have decided to build. Now follow the pattern.
>
> 任务型 skill = 精准 trigger + 工具组合 + 固定工作流 + 明确输出格式

## 前置判断

**适合任务型 skill：**
- 信息检索 + 总结（web-research）
- 文件分析 + 建议（code-review）
- 工作流指导（gstack-ship）
- 搜索 + 格式化输出

**不适合，需要机制型 skill：**
- 需要自定义 Python 逻辑
- 需要状态持久化
- 需要用户可配置的数据结构

## 五元组检查清单

| 元素 | 必须回答的问题 |
|------|---------------|
| trigger | 用户说什么关键词时激活？具体还是抽象？ |
| kernel | 核心工作流是什么？固定几步？ |
| input | 用户需要提供什么？（一句话？一个文件？） |
| output | 期望什么格式？纯文本 / 表格 / diff / 检查清单？ |
| composability | 是否推荐和某些 skill 组合使用？ |

## 实现步骤（固定模式）

### Step 1: 设计 Trigger

**原则：具体 > 抽象，多词 > 少词。**

```yaml
# ✅ 好：具体、多词、不易误触
trigger: search, look up, research, find online, what is, who is

# ❌ 差：太泛，容易误匹配
trigger: web

# ✅ 好：带动作词
trigger: review, code review, check code, review this
```

Trigger 会被子字符串匹配。每个词独立触发，所以不要用短词。

### Step 2: 选择 Tools

查看现有可用 tools：

```bash
python -c "from registry import registry; print('\n'.join(f'  {t}' for t in registry.list_tools()))"
```

**原则：只选必要的，2-4 个最佳。**

Deck 会自动加 3 个冗余基础工具，但核心 tools 必须显式声明。

常用组合：
| 场景 | Tools |
|------|-------|
| 网页研究 | net_web_search, net_web_extract |
| 代码审查 | fs_read_file, fs_search_files, fs_write_file |
| 发布流程 | sys_terminal, fs_read_file, fs_search_files |

### Step 3: 设计工作流

工作流必须是**编号步骤**，每步明确：
1. 调用什么 tool
2. 拿到结果后做什么判断
3. 下一步是什么

```markdown
1. 用 `fs_search_files` 找到相关文件
2. 用 `fs_read_file` 读取内容
3. 分析：...
4. 输出：...
```

**反模式：**
- "先搜索再分析再输出"（没有 tool 名，LLM 自由发挥）
- 步骤超过 10 步（任务型 skill 应该轻量）

### Step 4: 定义输出格式

在 skill body 中明确 output 格式：

```markdown
## Output

- 总结报告（带引用 URL）
- 行动项检查清单
- 代码 diff（如适用）
```

格式越具体，LLM 输出越一致。

### Step 5: 撰写 Skill Markdown

```yaml
---
name: <skill-name>
description: Use when ...
trigger: ...
tools:
  - tool_a
  - tool_b
category: ...
---

# <Title>

## 工作流

1. ...
2. ...

## Input

- ...

## Output

- ...
```

## 最小完整模板

```yaml
---
name: web-research
description: Research topics on the web and summarize findings
trigger: search, look up, research, find online
tools:
  - net_web_search
  - net_web_extract
category: research
---

# Web Research

When the user asks to research something online:

1. Formulate a precise search query
2. Call `net_web_search` to get results
3. If needed, call `net_web_extract` on promising URLs
4. Synthesize findings into a concise summary
5. Cite sources with URLs

## Input
- Research question or topic

## Output
- Summarized findings with citations
```

### Step 6: 运行 skill_test 验证

```bash
skill_test(target="<skill_name>", verbose=True)
```

验证清单：
- frontmatter 格式正确
- trigger 不与现有 skill 冲突
- tools 都在 registry 中存在
- match simulation 通过

Score ≥ 8/10 才可部署。

## 常见陷阱

1. **Trigger 太泛** → 频繁误匹配，干扰其他对话
2. **Tools 列表太长** → Deck 膨胀，context 浪费
3. **工作流步骤模糊** → LLM 自由发挥，结果不一致
4. **没有定义输出格式** → 每次输出风格不同
5. **和现有 skill 重复** → 创建前先用 `ls skills/` 检查
6. **Description 写成了功能说明** → 应该是触发条件，用 "Use when..."
