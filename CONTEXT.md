# Context: Worker-Bee Function Call

## Glossary

- **Loop** — The core agent conversation loop. Responsible for: receiving messages, matching skills, delegating execution to skills, and returning results. Never contains business logic.
- **Skill** — An orchestration layer that declares its required tools, defines call sequencing, and embeds business logic. A skill is a subroutine / workflow, not a cross-cutting interceptor.
- **Tool** — A single atomic capability exposed to the LLM (e.g., `fs_read_file`, `net_web_search`). Fixed at the infrastructure layer; evolution is forbidden.
- **Governance** — The set of strategies applied by the Loop to maintain message health: orphan cleanup, missing-result backfill, token budget enforcement, and model-aware compaction.
- **Model Profile** — A per-model configuration that declares context window size, reasoning support, tool-call format quirks, and recommended governance thresholds.
- **Deck** — A runtime snapshot of available tools and active tool boundaries. Acts as the tool-level access control gate.
- **Protocol** — The adapter that translates between the Loop's internal OpenAI-format messages and a specific provider's API shape.
- **Checkpoint** — A persisted snapshot of a skill's execution state, managed by the skill itself, not the Loop.

## Invariants

- The Loop never contains business logic. All orchestration decisions belong to Skills.
- Tool registration is fixed at infrastructure layer. Tool behavior does not evolve at runtime.
- Message governance (orphan cleanup, backfill, compaction) is the Loop's responsibility and is model-aware.
- A Skill may request concurrent tool execution, but the Loop decides the actual scheduling strategy.
- A Skill decides whether to checkpoint itself; the Loop does not enforce or manage checkpoints.
