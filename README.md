# Hermes Lite

> 🤖 **This repository is automatically maintained by an AI agent.**  
> Commits, documentation, and code changes are authored through human-AI collaboration.

A minimal, standalone AI agent framework inspired by [Hermes Agent](https://github.com/nousresearch/hermes-agent). It preserves the core architecture — skill contracts, trigger matching, and immutable tool boundaries — in a single-repo, zero-dependency package.

**Use this if you want a minimal Hermes to study, fork, or embed.**  
For the full design evolution, see [DESIGN.md](./DESIGN.md).

---

## Key Differences from Hermes

| | Hermes | Hermes Lite |
|---|---|---|
| **Size** | ~35,900 lines | **~1,700 lines** |
| **Platforms** | 15+ (Discord, Telegram, Feishu, etc.) | **Linux CLI** (webhook-opt-in) |
| **Skill trigger** | Passive listing — LLM pulls from a flat index | **Active matching** — system pushes skills via `trigger` field |
| **Tool boundary** | Macro toolsets (4–40 tools per call) | **Immutable Deck** (1–5 tools per task) |
| **Registry** | Toolset-centric, static YAML config | **Dynamic loading** — `fs_*`, `net_*`, `sys_*`, `agent_*` namespace |
| **Message format** | Unified to OpenAI internally | **Dual protocol** — Anthropic + OpenAI |
| **Philosophy** | Full-featured production system | **Study-friendly minimal core** |

---

## Quick Start

```bash
git clone https://github.com/JuliaHZhu/hermes-lite.git
cd hermes-lite
pip install -e .
hermes-lite setup          # creates ./config.json (gitignored)
hermes-lite -m "hello"     # verify model connectivity
hermes-lite                # start interactive session
```

---

## Architecture

```
hermes-lite/
├── main.py              # CLI entry
├── agent.py             # Agent loop (dual protocol)
├── deck.py              # Immutable tool boundary
├── registry.py          # Tool registry with metadata
├── skills.py            # Skill loader + trigger matching
├── memory.py            # SQLite persistence
├── DESIGN.md            # Full design evolution
└── tools/               # fs_*, net_*, sys_*, agent_*
```

---

## License

MIT — see [LICENSE](./LICENSE).

Hermes Lite is derived from the architecture of [Hermes Agent](https://github.com/nousresearch/hermes-agent) by Nous Research. Not affiliated or endorsed.
