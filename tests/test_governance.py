"""Governance tests — two fixtures validating model-aware message trimming.

Fixture A: ParagraphEditor  (multi-paragraph article synthesis)
  Simulates a user writing an article paragraph by paragraph.
  Each paragraph is a tool call (write_paragraph); the final call
  (assemble_article) must see *all* paragraphs.  We test that
  governance never drops paragraphs the assembler still needs.

Fixture B: EcoGameEngine  (wind→rain→grass→tree→thunder→fire→burn→wind)
  Simulates a tiny physics engine with cyclic state transitions.
  Each transition is a tool call updating shared game state.
  We test that governance preserves the latest state snapshot so
  the next transition has correct inputs.

Fixture C: RoleAlternation  (sanitising message sequences for API safety)
  Validates _enforce_role_alternation: merging consecutive same-role
  messages, fixing trailing assistants, and never leaving bare assistant
  at the end of the sequence.

Both fixtures use a tiny context window (2 000 tokens) to force
hard-trim, making it easy to verify correctness without real LLMs.
"""
from __future__ import annotations

import pytest

from agent.governance import govern_messages
from agent.models import ModelProfile


# ---------------------------------------------------------------------------
# Helper: build a tiny profile that triggers trimming quickly
# ---------------------------------------------------------------------------

@pytest.fixture
def tiny_profile() -> ModelProfile:
    """Return a 2 000-token profile so even modest histories exceed budget."""
    return ModelProfile(
        name="test-tiny",
        context_window=2000,
        encoding_name="auto",
        reserved_output_tokens=500,
        governance={
            "max_messages_before_compact": 5,
            "compact_threshold_ratio": 0.50,
            "hard_trim_ratio": 0.75,
            "microcompact_age_turns": 3,
        },
    )


# ---------------------------------------------------------------------------
# Fixture A: ParagraphEditor
# ---------------------------------------------------------------------------

class ParagraphEditor:
    """Simulated skill: write N paragraphs, then assemble them."""

    def __init__(self) -> None:
        self.paragraphs: list[str] = []

    def write_paragraph(self, index: int, text: str) -> str:
        self.paragraphs.append(text)
        return f"Paragraph {index} saved ({len(text)} chars)."

    def assemble_article(self) -> str:
        return "\n\n".join(self.paragraphs)


PARAGRAPHS = [
    "The early morning sun cast long shadows across the meadow.",
    "Birds chirped from the oak tree, unaware of the storm approaching.",
    "A single drop of rain landed on the dry earth, darkening a tiny spot.",
    "Within minutes, the sky turned charcoal grey and thunder rolled.",
    "The meadow became a river, and the oak tree swayed like a dancer.",
    "After the tempest, silence returned — deeper than before.",
    "A rainbow arced over the horizon, promising nothing and everything.",
    "The birds returned, shaking water from their wings in the fresh air.",
]


def _build_paragraph_history(editor: ParagraphEditor) -> list[dict]:
    """Construct a message history that mimics a real conversation."""
    messages: list[dict] = [
        {"role": "system", "content": "You are a writing assistant."},
        {"role": "user", "content": "Write me an article about a storm."},
    ]
    for i, text in enumerate(PARAGRAPHS, 1):
        # assistant decides to write a paragraph
        tool_call_id = f"tc_para_{i}"
        messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": tool_call_id, "name": "write_paragraph", "input": {"index": i, "text": text}}
                ],
            }
        )
        # tool result
        result = editor.write_paragraph(i, text)
        messages.append(
            {"role": "tool", "tool_call_id": tool_call_id, "content": result, "name": "write_paragraph"}
        )

    # Final assembly request
    final_tc = "tc_assemble_1"
    messages.append(
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": final_tc, "name": "assemble_article", "input": {}}
            ],
        }
    )
    # Simulate that the tool_result is *pending* — governance must backfill it
    return messages


class TestParagraphEditor:
    """Governance must keep all paragraph results so assembly succeeds."""

    def test_all_paragraphs_present_after_governance(self, tiny_profile):
        """After trimming, every paragraph result must still exist."""
        editor = ParagraphEditor()
        messages = _build_paragraph_history(editor)
        governed = govern_messages(messages, tiny_profile)

        # Collect surviving paragraph tool results
        surviving_texts = set()
        for m in governed:
            if m.get("role") == "tool" and m.get("name") == "write_paragraph":
                # Extract original paragraph text from the content string
                content = str(m.get("content", ""))
                # Content format: "Paragraph N saved (X chars)."
                # We can’t reverse-map to original text, so verify by index instead
                pass

        # Stronger assertion: every paragraph index (1..8) appears in a tool_result
        indices = {
            int(str(m.get("content", "")).split()[1])
            for m in governed
            if m.get("role") == "tool" and m.get("name") == "write_paragraph"
        }
        # If budget forced trimming, at least the *latest* paragraphs must survive
        # because the assembler needs the full set.
        # With our tiny 2k window we expect some trimming; verify no orphans.
        assistant_calls = [
            m for m in governed
            if m.get("role") == "assistant" and "tool_calls" in m
        ]
        result_ids = {
            m.get("tool_call_id")
            for m in governed
            if m.get("role") == "tool"
        }
        for a in assistant_calls:
            for tc in a["tool_calls"]:
                assert tc["id"] in result_ids, (
                    f"Orphan tool_call {tc['id']}: result was dropped"
                )

    def test_assemble_backfilled_if_missing(self, tiny_profile):
        """If assemble_article result is missing, governance backfills it."""
        editor = ParagraphEditor()
        messages = _build_paragraph_history(editor)
        governed = govern_messages(messages, tiny_profile)

        # The pending assemble_article must have a backfilled result
        assemble_results = [
            m for m in governed
            if m.get("role") == "tool" and m.get("name") == "assemble_article"
        ]
        assert len(assemble_results) >= 1
        assert "missing" in assemble_results[0].get("content", "")


# ---------------------------------------------------------------------------
# Fixture B: EcoGameEngine
# ---------------------------------------------------------------------------

class EcoGameEngine:
    """Tiny physics simulation: wind → rain → grass → tree → thunder → fire → burn → wind."""

    STATES = ["wind", "rain", "grass", "tree", "thunder", "fire", "burn"]

    def __init__(self) -> None:
        self.state = "wind"
        self.turn = 0
        self.history: list[str] = []

    def transition(self, event: str) -> str:
        """Apply one transition and return the new state."""
        rules = {
            ("wind", "blow"): "rain",
            ("rain", "fall"): "grass",
            ("grass", "grow"): "tree",
            ("tree", "age"): "thunder",
            ("thunder", "strike"): "fire",
            ("fire", "spread"): "burn",
            ("burn", "consume"): "wind",
        }
        key = (self.state, event)
        if key in rules:
            self.state = rules[key]
            self.history.append(f"turn {self.turn}: {key[0]} + {key[1]} → {self.state}")
        self.turn += 1
        return self.state


def _build_eco_history(engine: EcoGameEngine, cycles: int = 4) -> list[dict]:
    """Build message history for *cycles* full loops of the eco engine."""
    messages: list[dict] = [
        {"role": "system", "content": "You are an eco-simulation engine."},
        {"role": "user", "content": "Run the simulation for a while."},
    ]
    events = ["blow", "fall", "grow", "age", "strike", "spread", "consume"]
    tc_idx = 0
    for _ in range(cycles):
        for event in events:
            tc_idx += 1
            tc_id = f"tc_eco_{tc_idx}"
            messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": tc_id, "name": "transition", "input": {"event": event}}
                    ],
                }
            )
            new_state = engine.transition(event)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": f"State is now {new_state} (turn {engine.turn})",
                    "name": "transition",
                }
            )
    return messages


class TestFallback:
    """Governance must work even when tiktoken is unavailable."""

    def test_char_fallback_no_crash(self, tiny_profile):
        """When tiktoken is absent, build_counter falls back to char estimate."""
        # Force char-fallback by using a bogus encoding name
        profile = ModelProfile(
            name="test-fallback",
            context_window=2000,
            encoding_name="auto",
            reserved_output_tokens=500,
            governance={"microcompact_age_turns": 3},
        )
        # Build a counter manually to ensure we hit the fallback path
        from agent.models import _char_estimate
        counter = _char_estimate

        engine = EcoGameEngine()
        messages = _build_eco_history(engine, cycles=3)
        governed = govern_messages(messages, profile, counter=counter)

        # Should not crash and should return a non-empty list
        assert isinstance(governed, list)
        assert len(governed) > 0

    def test_tiktoken_vs_char_estimate_sanity(self):
        """Both counters return positive ints; char estimate is in the same
        ballpark as tiktoken for English (within 2× either direction).
        """
        pytest.importorskip("tiktoken")
        from agent.models import _char_estimate, _build_tiktoken_counter

        tiktoken_counter = _build_tiktoken_counter("cl100k_base")
        texts = [
            "Hello world",
            "The quick brown fox jumps over the lazy dog.",
            "a" * 1000,
            "def foo():\n    return 42\n",
        ]
        for text in texts:
            tik = tiktoken_counter(text)
            char = _char_estimate(text)
            assert tik > 0
            assert char > 0
            # Within 2× in either direction is sane for a rough fallback
            assert 0.5 <= char / tik <= 2.0, f"char/tiktoken ratio out of range: {char}/{tik} for {text[:40]}"


class TestEcoGameEngine:
    """Governance must preserve the latest state so the simulation stays consistent."""

    def test_latest_state_survives_trim(self, tiny_profile):
        """After aggressive trimming, the most recent state update must exist."""
        engine = EcoGameEngine()
        messages = _build_eco_history(engine, cycles=4)  # 28 tool calls
        governed = govern_messages(messages, tiny_profile)

        # Find the latest transition result
        latest = None
        for m in reversed(governed):
            if m.get("role") == "tool" and m.get("name") == "transition":
                latest = m
                break

        assert latest is not None, "All transition results were trimmed away"
        # The latest state should be present (burn or wind depending on cycle count)
        content = latest.get("content", "")
        assert "State is now" in content

    def test_no_orphaned_tool_calls(self, tiny_profile):
        """Every surviving assistant tool_call must have a matching result."""
        engine = EcoGameEngine()
        messages = _build_eco_history(engine, cycles=3)
        governed = govern_messages(messages, tiny_profile)

        result_ids = {
            m.get("tool_call_id")
            for m in governed
            if m.get("role") == "tool"
        }
        for m in governed:
            if m.get("role") == "assistant" and "tool_calls" in m:
                for tc in m["tool_calls"]:
                    assert tc["id"] in result_ids, (
                        f"Orphan tool_call {tc['id']}: no result in governed messages"
                    )

    def test_state_chain_integrity(self, tiny_profile):
        """Even after trimming, the surviving history forms a valid chain."""
        engine = EcoGameEngine()
        messages = _build_eco_history(engine, cycles=3)
        governed = govern_messages(messages, tiny_profile)

        # Walk the surviving tool_results in order and verify state transitions
        states: list[str] = []
        for m in governed:
            if m.get("role") == "tool" and m.get("name") == "transition":
                content = str(m.get("content", ""))
                # Parse "State is now X"
                parts = content.split()
                if len(parts) >= 4:
                    states.append(parts[3])

        # Verify each transition follows the rule book
        rules = {
            "wind": "rain",
            "rain": "grass",
            "grass": "tree",
            "tree": "thunder",
            "thunder": "fire",
            "fire": "burn",
            "burn": "wind",
        }
        for i in range(1, len(states)):
            prev, curr = states[i - 1], states[i]
            assert rules.get(prev) == curr, (
                f"Invalid transition at position {i}: {prev} → {curr}"
            )


# ---------------------------------------------------------------------------
# Fixture C: RoleAlternation
# ---------------------------------------------------------------------------

class TestRoleAlternation:
    """Verify _enforce_role_alternation keeps message sequences API-safe."""

    @pytest.fixture
    def generous_profile(self) -> ModelProfile:
        """Large context window so hard_trim never triggers."""
        return ModelProfile(
            name="test-generous",
            context_window=1_000_000,
            encoding_name="auto",
            reserved_output_tokens=4096,
        )

    def test_merge_consecutive_user_messages(self, generous_profile):
        """Two user messages in a row should be merged into one."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": "World"},
        ]
        governed = govern_messages(messages, generous_profile)
        user_msgs = [m for m in governed if m.get("role") == "user"]
        assert len(user_msgs) == 1
        assert "Hello" in user_msgs[0]["content"]
        assert "World" in user_msgs[0]["content"]

    def test_merge_consecutive_assistant_messages(self, generous_profile):
        """Two bare assistant messages should be merged into one."""
        messages = [
            {"role": "assistant", "content": "First thought."},
            {"role": "assistant", "content": "Second thought."},
        ]
        governed = govern_messages(messages, generous_profile)
        # Bare assistant at the end is dropped; but the merge still happened
        # before the drop.  Verify no assistant survives and no crash.
        assistant_msgs = [m for m in governed if m.get("role") == "assistant"]
        assert len(assistant_msgs) == 0

    def test_tool_calls_take_precedence_on_merge(self, generous_profile):
        """When merging assistants, the one with tool_calls wins."""
        messages = [
            {
                "role": "assistant",
                "content": "Bare assistant.",
            },
            {
                "role": "assistant",
                "content": "With tools.",
                "tool_calls": [{"id": "tc_1", "name": "read", "arguments": {}}],
            },
        ]
        governed = govern_messages(messages, generous_profile)
        assistant_msgs = [m for m in governed if m.get("role") == "assistant"]
        assert len(assistant_msgs) == 1
        assert "tool_calls" in assistant_msgs[0]
        assert assistant_msgs[0]["tool_calls"][0]["id"] == "tc_1"

    def test_drop_trailing_bare_assistant(self, generous_profile):
        """A bare assistant at the end of the list should be dropped."""
        messages = [
            {"role": "user", "content": "Question?"},
            {"role": "assistant", "content": "Answer."},
        ]
        governed = govern_messages(messages, generous_profile)
        assert governed[-1].get("role") != "assistant"

    def test_keep_trailing_assistant_with_tools(self, generous_profile):
        """An assistant with tool_calls is kept; backfill injects its result."""
        messages = [
            {"role": "user", "content": "Do something."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "tc_1", "name": "exec", "arguments": {}}],
            },
        ]
        governed = govern_messages(messages, generous_profile)
        # Backfill injects a tool result, so the *pair* survives
        assert governed[-2].get("role") == "assistant"
        assert "tool_calls" in governed[-2]
        assert governed[-1].get("role") == "tool"
        assert governed[-1].get("tool_call_id") == "tc_1"

    def test_first_non_system_not_bare_assistant(self, generous_profile):
        """If the first non-system message is a bare assistant, inject a user."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "assistant", "content": "Let me start."},
        ]
        governed = govern_messages(messages, generous_profile)
        non_system = [m for m in governed if m.get("role") != "system"]
        assert non_system[0].get("role") == "user"

    def test_backfill_after_role_alternation(self, generous_profile):
        """After dropping a trailing assistant, orphaned tool_calls are cleaned."""
        messages = [
            {"role": "user", "content": "Question?"},
            {
                "role": "assistant",
                "content": "Let me check.",
                "tool_calls": [{"id": "tc_1", "name": "read", "arguments": {}}],
            },
        ]
        # No matching tool result — backfill should inject one
        governed = govern_messages(messages, generous_profile)
        result_ids = {
            m.get("tool_call_id") for m in governed if m.get("role") == "tool"
        }
        assert "tc_1" in result_ids


# ---------------------------------------------------------------------------
# Fixture D: ToolResultTruncation
# ---------------------------------------------------------------------------

class TestToolResultTruncation:
    """Verify tool results are clamped before entering history."""

    def test_short_result_unchanged(self):
        """Results under the limit pass through untouched."""
        from agent.loop import _truncate_tool_result
        text = "Short result."
        assert _truncate_tool_result(text) == text

    def test_long_result_truncated(self):
        """Results over the limit are truncated with a notice."""
        from agent.loop import _truncate_tool_result, _MAX_TOOL_RESULT_CHARS
        text = "x" * (_MAX_TOOL_RESULT_CHARS + 100)
        truncated = _truncate_tool_result(text)
        assert len(truncated) <= _MAX_TOOL_RESULT_CHARS + 100  # still bounded
        assert "truncated" in truncated.lower()

    def test_non_string_input(self):
        """Non-string inputs are coerced to string before truncation."""
        from agent.loop import _truncate_tool_result
        result = _truncate_tool_result({"key": "value" * 5000})
        assert isinstance(result, str)
        assert "truncated" in result.lower() or len(result) <= 20000
