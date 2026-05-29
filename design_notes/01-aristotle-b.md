# Aristotle Bee — Definition Master

> *Words drift. Meaning must be anchored.*

## Problem

The same word means different things in different sessions. "沉浸感" today is flow, tomorrow it is sensory. The LLM does not notice the drift — it just generates the next token based on whatever context it has.

## First Principle

**LLM does not "understand" words. It matches patterns.** If you want precision, you must externalize definitions and force the LLM to look them up before use. The dictionary is a **shared mental model** between human and LLM.

## Behavior

1. When the user mentions a term, check `~/.worker-bee/dict/<project>.md`
2. If the term exists — quote its definition at the start of the reply in a `[Definition: term]` block
3. If the current context differs from the recorded usage — raise a **drift warning**
4. If the term does not exist — ask: "What do you mean by 'X'? Suggest writing it into the dictionary."
5. If the user is coining a new term — record it with `[New term]` label, ask for exact definition

## Exogenous Pheromone Format

File: `~/.worker-bee/dict/<project>.md`

```markdown
# 术语词典：游戏策划

## 沉浸感
- **Definition**: 玩家暂时忘记现实，全身心投入游戏状态
- **Variants**:
  - 心流沉浸 (Flow): 技能与挑战平衡时的忘我
  - 感官沉浸 (Sensory): 视听包裹感
  - 叙事沉浸 (Narrative): 与角色共情
- **Context**: Session e5f6g7h8 — 指叙事沉浸
- **Drift warning**: Session a1b2c3d4 used it for 感官沉浸

## 叙事弧
- **Definition**: 玩家情感体验的三幕结构（起-承-转-合）
- **Game context**: 关卡节奏曲线，非剧情事件序列
- **Related**: [[故事线]] (事件序列) ≠ 叙事弧 (情感节奏)
- **Usage**: Session b2c3d4e5 — 指关卡节奏
```

Each term is an H2 block. Fields are bullet lists with bold keys. Both human and LLM read the same file.

## Drift Warning Format

```
[Drift] You said "沉浸感". Last session (e5f6g7h8) this meant "心流沉浸".
Current context suggests "感官沉浸". Clarify which one?
```

## Skill Contract

See `worker_bee/skills/aristotle.md`

## Why It Works

- The dictionary is **human-editable** — you can open it in any text editor
- The LLM does not "learn" the terms — it **looks them up** via `read_file`
- Drift is caught because the LLM compares current context against recorded usage
- New terms are **explicitly coined**, not silently invented

## Use Cases

- Game design teams with domain-specific jargon ("战斗节奏", "循环经济")
- Research projects with abstract constructs that need precise operationalization
- Any domain where words are slippery and precision matters
