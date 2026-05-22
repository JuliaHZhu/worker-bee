---
name: create-mechanism-skill
description: Use when creating a skill that requires custom Python tooling, state persistence, or data management. For backend-engine skills like todo-ball-machine.
trigger: create mechanism skill, build system skill, skill with state, custom tool skill, persistent data skill, 创建机制skill, 有状态的skill, 底层skill, 带数据持久化的skill
tools:
  - fs_read_file
  - fs_write_file
  - fs_search_files
  - sys_terminal
category: skill-authoring
---

# Create Mechanism Skill

> 机制型 skill = 自定义 Python 后端 + 状态持久化 + 配置驱动

## 前置判断

**需要机制型 skill 的信号：**
- 需要自定义逻辑（不是简单组合现有 tool）
- 需要状态跨会话保留（抽球进度、历史记录）
- 需要用户可配置分类/配额/规则

**不需要机制型 skill，用任务型 skill 即可：**
- 搜索 + 总结
- 文件读写 + 分析
- 调用现有 tools 的组合（无自定义逻辑）

## 五元组检查清单

| 元素 | 必须回答的问题 |
|------|---------------|
| trigger | 用户说什么关键词时激活？是否足够具体？ |
| kernel | 核心机制是什么？数据如何流转？ |
| tech stack | Python tool？JSON state？SQLite？配置怎么放？ |
| input | tool 接收什么参数？action 怎么分派？ |
| output | 返回纯文本？JSON？表格？ |
| composability | 是否依赖其他 skill？能否被 cron 调用？ |

## 实现步骤（固定模式）

### Step 1: 设计数据模型

**原则：单文件 JSON 优先。**

```
<skill_name>_data/
  state.json      ← 运行时状态（自动读写）
  config.json     ← 用户可编辑的配置（分类、配额、规则）
```

**反模式：**
- 用 SQLite 存简单配置
- 把状态拆成多个小文件
- 在代码里硬编码分类/配额

### Step 2: 创建 Python Tool

在 `tools/<skill_name>.py` 创建：

```python
import json
import os
from registry import registry

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "<skill_name>_data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

def _load_json(path, default=None):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}

def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def <skill_name>(action: str, ...):
    state = _load_json(STATE_FILE, {})
    config = _load_json(CONFIG_FILE, {})
    # ... 业务逻辑 ...
    _save_json(STATE_FILE, state)
    return result

registry.register(
    name="<skill_name>",
    description="...",
    parameters={
        "properties": {
            "action": {"type": "string", "enum": [...], "description": "..."},
            # ...
        },
        "required": ["action"]
    },
    handler=<skill_name>,
    tags=[...],
    category="..."
)
```

### Step 3: 配置驱动

所有可变业务常量放入 `config.json`：

```json
{
  "categories": ["学习", "工作", "运动"],
  "quotas": {"学习": 21, "工作": 21, "运动": 15}
}
```

代码只读配置，不硬编码任何业务值。

### Step 4: 确保 Import 触发注册

在 `main.py` 的 import 区加入：

```python
from tools.<skill_name> import <skill_name>  # noqa: F401
```

**验证：**
```bash
python -c "from registry import registry; print('<skill_name>' in registry.list_tools())"
```

### Step 5: 撰写 Skill Markdown

在 `skills/<skill_name>.md` 创建：

```yaml
---
name: <skill-name>
description: ...
trigger: ...
tools:
  - <skill_name>
category: ...
---
```

body 必须包含：
1. 核心概念（一句话）
2. 操作清单（表格）
3. 常用示例（代码块）
4. 工作流（编号步骤）
5. 约束（边界规则）

## 最小完整模板

参考 `tools/todo_ball_machine.py` + `skills/todo-ball-machine.md`：
- ~300 行 Python（含注册）
- ~100 行 markdown（含 frontmatter）
- 单文件 JSON 状态
- JSON 配置驱动

## 常见陷阱

1. **硬编码分类/配额** → 用户无法自定义，改需求必须改代码
2. **复杂数据库替代 JSON** → 增加部署负担，无实际收益
3. **忘记 import 触发注册** → skill markdown 写了，但 tool 不存在
4. **skill tools 列表漏写** → Deck 构建时遗漏，LLM 无法调用
5. **非原子写入** → 崩溃后 state.json 损坏，应写临时文件再 rename
6. **action 分派用 if-elif** → 超过 5 个 action 改用 dict 映射
