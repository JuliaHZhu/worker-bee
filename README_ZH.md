# Hermes Lite — 快速索引

> 完整文档见 [README.md](./README.md)

---

## 是什么

一台 Agent + 一块 Job Board = 可管理的任务执行。没有 Symphony，没有多 Agent。

## 快速开始

```bash
git clone https://github.com/JuliaHZhu/hermes-lite.git
cd hermes-lite
pip install -e .
cp config.example.json config.json
# 填 API key
python -m pytest tests/ -q  # 299 passed
python main.py
```

## 三个核心概念

| 概念 | 作用 |
|------|------|
| **Deck** | 运行时工具边界——每次任务只暴露相关 tools |
| **Skill** | 契约——trigger + tools，声明式激活 |
| **Job Board** | 文本信息素场——Markdown 文件 = 状态 |

## 常用 Skill

| Skill | Trigger | 用途 |
|-------|---------|------|
| job-supervisor | 监工、工单 | 任务管理、进度跟踪 |
| todo-ball-machine | 抽球、场次 | 人生任务抽球系统 |
| podcast-agent | 播客 | 文档转播客脚本 |
| code-review | 审代码 | 代码审查 |

## 为什么不要 Symphony

- Agent 自己就是 dispatcher
- 顺序执行，简单可预测
- 状态在 Markdown 里，人随时可改

## 完整文档

详见 [README.md](./README.md)
