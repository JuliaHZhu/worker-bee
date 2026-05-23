---
name: podcast-agent
category: productivity
description: Generate podcast-style dialogue scripts from source documents (PDF, MD, TXT, web pages)
triggers:
  - podcast
  - 播客
  - 生成播客
  - 讲讲这篇
  - 转成音频
tools:
  - podcast_agent
---

# Podcast Agent Skill

Generate natural two-person dialogue podcast scripts from source documents.
Inspired by Google NotebookLM's Audio Overview feature.

## What It Does

Takes any document (PDF, Markdown, plain text) and generates a structured podcast
script with two hosts discussing the content. The output is a JSON file containing
dialogue turns, a title, and a summary.

## How It Works

1. **Parse**: Extract text from PDF (pymupdf) or read MD/TXT files
2. **Chunk**: If text is very long, condense into key points via LLM
3. **Script**: LLM generates a natural dialogue following strict rules:
   - Each line ≤ 100 characters (~5-8 seconds spoken)
   - Natural spoken language, not written style
   - Transition phrases ("Let me think...", "That's fascinating!")
   - No verbatim reading — restructure and interpret
4. **Output**: JSON with title, summary, and dialogue array

## Usage

### Standalone

```bash
python tools/podcast_agent.py --source ~/paper.pdf --tone educational --lang zh
python tools/podcast_agent.py --source ~/notes.md --tone casual --lang en
```

### As a Skill (via Hermes)

```
User: 把这篇论文转成播客脚本
Hermes: [执行 podcast_agent.py --source <uploaded_file> --tone educational --lang zh]
Hermes: ✅ 已生成播客脚本，共16轮对话...
```

## Configuration

`~/.hermes/podcast_agent_config.json`

```json
{
  "provider": "moonshot",
  "base_url": "https://api.moonshot.cn/v1",
  "model": "moonshot-v1-32k",
  "moonshot_api_key": "sk-...",
  "voice_a": "alloy",
  "voice_b": "nova"
}
```

Auto-detects API keys from environment: `OPENAI_API_KEY`, `MOONSHOT_API_KEY`.

## Prompt Engineering

The system prompt is adapted from gabrielchua/open-notebooklm with these
key constraints learned from the open-source implementation:

- **100-char limit per line**: Controls podcast rhythm (5-8s per turn)
- **Strict JSON output**: No markdown fences, direct JSON
- **Three configurable dimensions**:
  - `tone`: professional | casual | humorous | educational
  - `lang`: output language
  - `length`: short (1-2min) | medium (3-5min)

## Composability

### Upstream (feeds into this skill)
- **research-agent**: Auto-collect sources → podcast-agent → script
- **wiki-sync**: Detect new wiki notes → podcast-agent → knowledge update podcast
- **todo-ball-machine**: Morning brief → podcast-agent → daily audio brief

### Downstream (this skill feeds into)
- **feishu**: Push script as message or send generated audio
- **email**: Attach script + audio
- **tts-agent**: Convert script to actual MP3 audio

## Architecture

```
Source → Parse → Chunk → LLM Script Gen → JSON Output
                    ↓
              [Optional: condense long docs]
```

## Design Notes

- **No TTS included**: This skill stops at script generation. Audio synthesis
  is a separate concern (can be added via tts-agent or ElevenLabs/OpenAI TTS).
- **Multi-provider**: Works with any OpenAI-compatible API (OpenAI, Moonshot,
  Together AI, etc.) via config.
- **Local-first**: Documents are parsed locally, only LLM calls go to API.
- **Chunking for long docs**: If document exceeds ~12k tokens, it is first
  condensed into bullet points before script generation.

## References

- [Google NotebookLM](https://notebooklm.google.com) — Product inspiration
- [gabrielchua/open-notebooklm](https://github.com/gabrielchua/open-notebooklm) —
  Open-source reference (2.6k stars). Key learnings: prompts.py constraints,
  JSON schema design, app.py pipeline structure.
