# ADR-0001: Loop Governance Differentiated by Model

## Status

Proposed

## Context

Worker-bee's core loop was a minimal `while` cycle (~200 lines) with only message-count-based truncation (`_trim_messages`). After comparing with nanobot's industrial-grade context governance (6 layers: orphan drop, backfill, microcompact, tool-result budget, history snip, checkpoint), we needed to decide:

1. Should governance be extracted into a Skill (pluggable strategy per use-case)?
2. Should governance be a fixed part of the Loop?
3. If part of the Loop, should it be uniform across all models or model-aware?

## Decision

**Governance stays in the Loop (not a Skill) and is model-aware.**

Specifically:

- The Loop owns message health: orphan tool_result cleanup, missing-result backfill, token budget enforcement, and compaction.
- Governance parameters (context window size, compaction thresholds, truncation strategy) are loaded from a **Model Profile**, not hardcoded.
- Skills never touch message governance. They receive a clean message history and return tool results.
- The Loop remains under ~250 lines; model-specific logic is delegated to the Model Profile, not inlined.

## Consequences

### What gets better

- **Correctness**: Different models have different context windows, reasoning formats, and tool-call quirks. A uniform truncation strategy breaks some models while over-conservatively limiting others.
- **Simplicity**: Skills do not need to know about message governance. They focus on orchestration and business logic.
- **Maintainability**: Adding a new model only requires adding a Model Profile, not changing every Skill.

### What gets harder

- **Model Profile maintenance**: Every new model requires a verified profile (context window, token encoding, reasoning support). Profiles can become stale as providers update their APIs.
- **Testing surface**: Governance behavior now varies by model, increasing the test matrix.
- **Risk of drift**: If a model's actual behavior diverges from its Profile, the Loop may truncate too aggressively or too leniently.

## Alternatives considered

1. **Extract governance into a Skill** — Rejected. Every LLM call would require an extra Skill invocation overhead, and governance is fundamentally a Loop concern (all Skills share the same message history).

2. **Uniform governance regardless of model** — Rejected. A single truncation threshold either wastes context on large-window models or breaks small-window models. This was the root cause of nanobot's `_sanitize_messages` complexity.

3. **Per-Skill governance override** — Rejected. Skills should not compete for context window management; this creates coordination problems and violates the invariant that the Loop owns message health.
