# ADR-0002: Governance Implementation — Model-Aware Message Trimming

## Status

Accepted

## Context

ADR-0001 established that message governance stays in the Loop (not a Skill) and is model-aware.  This ADR records the concrete implementation.

## What We Brought In (3rd-Party)

| Package | Version | Purpose | Why This One |
|---|---|---|---|
| **tiktoken** | ≥0.8.0 | Token counting for OpenAI models (GPT-4, GPT-3.5) | Official OpenAI BPE tokenizer; zero-config for those models |
| **transformers** (optional) | — | Token counting for non-OpenAI models via Hugging Face | Fallback when tiktoken has no matching encoding |

Both are optional.  If neither is installed, the system falls back to a character-based estimate (~4 chars/token).

## What We Wrote Ourselves

### 1. `agent/models.py` — Model Profiles & Token Counting

| Component | Lines | Responsibility |
|---|---|---|
| `ModelProfile` dataclass | ~30 | Immutable config per model: context window, encoding name, reserved output tokens, governance thresholds |
| `TokenCounter` protocol | ~3 | Abstract interface: `str → int` |
| `build_counter()` | ~30 | Factory that resolves encoding name → concrete counter (tiktoken / HF / char fallback) |
| `estimate_tokens()` | ~5 | Convenience wrapper used by the Loop |
| `ModelRegistry` | ~40 | Resolves model name → `ModelProfile`; ships with built-in profiles for popular models; supports programmatic overrides |

**Built-in profiles:** gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, claude-sonnet-4-20250514, kimi-k2.6.

### 2. `agent/governance.py` — Message Health Pipeline

| Function | Lines | Responsibility |
|---|---|---|
| `_drop_orphans()` | ~20 | Remove `tool` messages whose `tool_call_id` has no matching assistant `tool_call` |
| `_backfill_missing()` | ~25 | Inject error placeholders for assistant `tool_call`s that lack a result |
| `_microcompact()` | ~35 | Replace old tool results (>N turns) with one-line summaries; only affects read / list / terminal / fetch tools |
| `_hard_trim()` | ~45 | Discard oldest messages until total token count ≤ model's usable context; never breaks assistant/tool pairs; preserves system message |
| `govern_messages()` | ~15 | Public entrypoint: runs the four stages in order (drop → backfill → microcompact → hard-trim) |

**Total self-written code:** ~260 lines across both modules.

### 3. `tests/test_governance.py` — Validation Fixtures

| Fixture | Purpose |
|---|---|
| `ParagraphEditor` | Simulates writing 8 paragraphs + final assembly. Verifies that governance never orphans a `tool_call` and backfills missing results. |
| `EcoGameEngine` | Simulates 3–4 full cycles of wind→rain→grass→tree→thunder→fire→burn→wind. Verifies that the latest state survives trimming and that state transitions remain valid. |
| `tiny_profile` | 2 000-token model profile used in tests to force aggressive trimming without needing real LLMs. |

**Test coverage:** orphan cleanup, backfill, microcompact, hard-trim, pair integrity, state-chain validity.

## Design Decisions

### Why not put governance in a Skill?

All Skills share the same message history.  If governance were a Skill, every LLM call would require an extra Skill invocation, and different Skills could compete for context-window management.  Keeping governance in the Loop guarantees a single source of truth.

### Why `ModelProfile` instead of hardcoded constants?

Different models have different context windows (16k–256k), tokenizers, and tool-call quirks.  A uniform truncation strategy either breaks small-window models or wastes context on large-window ones.  `ModelProfile` lets us tune per-model without touching the Loop.

### Why `_hard_trim` never breaks assistant/tool pairs?

If an assistant message with `tool_calls` is dropped, all matching `tool_result` messages are also dropped.  This prevents the LLM from seeing orphaned results or making calls that will never receive answers.

### Why is `transformers` optional?

Most worker-bee deployments target OpenAI-compatible APIs (OpenAI, Moonshot, etc.) where tiktoken suffices.  Hugging Face tokenizers are only needed for niche local models.  Making transformers optional keeps the base install lightweight.

## Integration into the Loop

`govern_messages()` is called **once per LLM turn**, immediately before `protocol.build_call()`:

```python
# agent/loop.py (simplified)
from agent.governance import govern_messages
from agent.models import ModelRegistry

registry = ModelRegistry()
profile = registry.get(config["model"])

messages = govern_messages(messages, profile)
response = generate_response(protocol.build_call(messages, tools))
```

This adds ~3 lines to the Loop while keeping the governance complexity isolated in `agent/governance.py`.

## Files Changed

| File | Action |
|---|---|
| `agent/models.py` | **New** — Model profiles & token counting |
| `agent/governance.py` | **New** — Message health pipeline |
| `tests/test_governance.py` | **New** — ParagraphEditor + EcoGameEngine fixtures |
| `requirements.txt` | **Modified** — added `tiktoken>=0.8.0` |
| `docs/adr/0001-loop-governance-by-model.md` | **Modified** — status changed Proposed → Accepted |

## Verification

Run the new tests:

```bash
cd worker-bee
pip install -e ".[test]"
pytest tests/test_governance.py -v
```

Expected: all 6 tests pass, exercising orphan drop, backfill, microcompact, hard-trim, and state-chain integrity.

## Mitigations (Profile Drift Risk)

The top risk identified during grill-me Q7 is **Model Profile drift** — providers change context windows or tokenizers without notice.  Mitigations:

1. **Graceful degradation**: If a profile is stale, `ModelRegistry.get()` falls back to a conservative generic profile (128k window, auto encoding).  The loop keeps working, just less optimally.
2. **Overridable at runtime**: `ModelRegistry.register()` allows any machine to patch its own profile via config without waiting for a framework release.
3. **Periodic human review**: Each machine's `config.yaml` can pin its profile; seed self-evolution means machines that hit truncation issues will surface them in their own logs for human triage.
4. **No hard dependencies on exact counts**: Token counting is a *hint* for trimming, not a correctness gate.  Being off by 10 % still produces valid messages — just slightly earlier or later compaction.
