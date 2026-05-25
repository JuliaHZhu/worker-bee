# NotebookLM × Hermes 完整玩法手册

> 从“调研”到“跑通”的完整路径

---

## 一、NotebookLM 是什么？（1分钟理解）

不是“带 AI 的笔记软件”，而是**以源文档为中心的多模态认知空间**。

你把资料“放”进去，AI 帮你“住”进去理解，然后用多种方式还给你：
- 问答（带原文引用）
- 结构化 Studio（时间线、FAQ、思维导图）
- **Audio Overview：双人对话播客** ← 最杀手

---

## 二、Audio Overview 为什么牛？

不是 TTS（文本转语音）。是：

```
文档 → AI 理解 → 提炼要点 → 重新组织成对话 → 语音化
```

两个 AI “主持人”会：
- 互相提问、打断、附和
- 用自然口语重新阐释（不是朗读原文）
- 每句 5-8 秒，轮流对话

---

## 三、为什么要用 Hermes 做？

NotebookLM 是**被动的**：你上传文档，它等着你来问。
Hermes 是**主动的**：能搜索、执行代码、编排流程、定时任务。

结合后 = **自动化的、可扩展的、可交互的 AI 知识工作站**

---

## 四、实际跑通的代码

### 4.1 单机工具：文档 → 播客脚本

```bash
cd /path/to/worker-bee
python3 tools/podcast_agent.py \
  --source ~/docs/paper.pdf \
  --tone casual \
  --lang zh
```

**输出**：`paper.pdf.podcast.json` — 含 title、summary、dialogue array

**Config** (`~/.worker-bee/podcast_agent_config.json`)：自动检测 `OPENAI_API_KEY` / `MOONSHOT_API_KEY`

### 4.2 组合工流：Todo Ball Machine → 播客

```bash
python3 tools/brief_to_podcast.py
```

**做什么**：
1. 调用 `todo_ball_machine(action="dashboard")` 获取今日状态
2. 调用 `todo_ball_machine(action="today")` 获取今日安排
3. 合并为一份简报文本
4. 调用 `podcast_agent.py` 生成播客脚本

**验证结果**：
```
309 字符简报 → 16 轮自然对话
主题：“探索 Todo Ball Machine 的一天”
内容准确反映了真实数据：4 个剩余场次、周期进度 4%
```

---

## 五、技术架构

```
┌───────────────────────────────────────────────────────────┐
│  Podcast Agent Skill                                   │
├───────────────────────────────────────────────────────────┤
│                                                       │
│  Source (PDF/MD/TXT/Feishu Doc)                        │
│       │                                               │
│       ▼                                               │
│  Parse (pymupdf / marker)                             │
│       │                                               │
│       ▼                                               │
│  Chunk + Condense (if >12k tokens)                    │
│       │                                               │
│       ▼                                               │
│  LLM Script Generation                                │
│  - System Prompt: 开源项目改良版                     │
│  - Constraints: 每行≤100字符、JSON输出、自然口语   │
│  - Provider: OpenAI / Moonshot / 其他兼容 API          │
│       │                                               │
│       ▼                                               │
│  JSON Output: {title, summary, dialogue[]}            │
│       │                                               │
│       ▼                                               │
│  [Optional] TTS 合成 → MP3                          │
│  [Optional] 飞书推送 / 邮件分发                     │
└───────────────────────────────────────────────────────────┘
```

---

## 六、开源参考

| 项目 | 作用 | 星标 |
|------|------|------|
| [gabrielchua/open-notebooklm](https://github.com/gabrielchua/open-notebooklm) | 核心参考，提供了 prompts.py 的关键约束设计 | 2.6k |
| [marker](https://github.com/fictionpress/Marker) | 高精度 PDF 解析 | — |
| [pydub](https://github.com/jiaaro/pydub) | 音频拼接后处理 | — |

---

## 七、后续可扩展方向

- [ ] 加 TTS：接入 ElevenLabs / OpenAI TTS 生成真实音频
- [ ] 飞书集成：解析飞书文档链接为源
- [ ] Cron 定时：每日自动生成播客
- [ ] 多 Agent：Researcher → Scriptwriter → Voice 分工
