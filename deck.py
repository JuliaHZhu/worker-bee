"""Deck — Tool procurement before execution.

Philosophy:
  Like gathering tools before making something.
  1. LLM selects relevant skills from the skill library
  2. Each skill declares its tools
  3. All tools are collected into a Deck
  4. During execution, the agent draws ONLY from this Deck
  5. If a tool in the Deck cannot complete the task → halt, ask human

  No ad-hoc tool shopping mid-execution. If the initial procurement
  was insufficient, the approach itself may be wrong.

Skill-to-skill routing (composable skills) is separate:
  - Some skills are atomic (like a remote button)
  - Some skills are procedural (macro/scripts)
  - LLM decides procedural routing via semantic analysis
  - This happens inside execution, but still within the Deck boundary
"""
import json
import re
from typing import Dict, List, Optional, Set


class Deck:
    """An immutable curated set of tools for one task.

    Once built, execution draws ONLY from these tools.
    """

    def __init__(self, tool_names: List[str], registry):
        self._registry = registry
        self._tool_names: List[str] = []
        self._missing: List[str] = []
        self._schemas: List[dict] = []
        self._name_to_schema: Dict[str, dict] = {}

        for name in tool_names:
            schema = registry.get_schema(name)
            if schema:
                self._tool_names.append(name)
                self._schemas.append(schema)
                self._name_to_schema[name] = schema
            else:
                self._missing.append(name)

    @property
    def tool_names(self) -> List[str]:
        return list(self._tool_names)

    @property
    def schemas(self) -> List[dict]:
        return list(self._schemas)

    @property
    def missing(self) -> List[str]:
        """Tools declared by skills but not found in registry."""
        return list(self._missing)

    def has_tool(self, name: str) -> bool:
        return name in self._name_to_schema

    def get_schema(self, name: str) -> Optional[dict]:
        return self._name_to_schema.get(name)

    def get_schemas_for_protocol(self, protocol: str) -> List[dict]:
        """Return schemas converted for Anthropic or OpenAI."""
        if protocol == "openai":
            converted = []
            for s in self._schemas:
                converted.append({
                    "type": "function",
                    "function": {
                        "name": s["name"],
                        "description": s["description"],
                        "parameters": s.get("input_schema", {"type": "object"})
                    }
                })
            return converted
        return self._schemas

    def __repr__(self) -> str:
        return f"Deck({self._tool_names}, missing={self._missing})"


class DeckBuilder:
    """LLM-driven skill selection → tool procurement."""

    def __init__(self, skill_manager, registry, client, protocol="anthropic", model=None):
        self.skill_manager = skill_manager
        self.registry = registry
        self.client = client
        self.protocol = protocol
        self.model = model

    def build(self, user_input: str) -> Deck:
        """Procure a Deck for this user input.

        Steps:
          1. Enumerate all available skills
          2. Ask LLM: which skills are relevant?
          3. Collect tools from selected skills
          4. Verify each tool exists in registry
          5. Return Deck (immutable)
        """
        all_skills = self.skill_manager.list_skills()
        if not all_skills:
            # No skills → fallback to all registered tools
            all_tools = list(self.registry.list_tools().keys())
            return Deck(all_tools, self.registry)

        # 1. Let LLM pick relevant skills
        selected = self._select_skills(user_input, all_skills)

        # 2. Gather tools
        tool_names: Set[str] = set()
        for skill_name in selected:
            skill = self.skill_manager.get_skill(skill_name)
            if skill:
                for t in skill.get("tools", []):
                    tool_names.add(t)

        # 3. Also include any tools the user might have in config
        # (e.g. always-available tools like terminal on linux)
        # This is handled outside DeckBuilder by the caller merging.

        return Deck(list(tool_names), self.registry)

    def _select_skills(self, user_input: str, skills: Dict[str, dict]) -> List[str]:
        """Ask LLM to choose relevant skills from the library.

        We send a compact summary (name, description, triggers, tools)
        and let the LLM do semantic matching.
        """
        summaries = []
        for name, meta in skills.items():
            summaries.append({
                "name": name,
                "description": meta.get("description", ""),
                "triggers": meta.get("triggers", []),
                "tools": meta.get("tools", [])
            })

        prompt = (
            f"User request: {user_input}\n\n"
            f"Available skills:\n"
            f"{json.dumps(summaries, ensure_ascii=False, indent=2)}\n\n"
            "Select the skills relevant to this request. "
            "Return ONLY a JSON array of skill names, e.g.: [\"skill1\", \"skill2\"]. "
            "Return [] if none are relevant."
        )

        try:
            raw = self._quick_llm_call(prompt)
            # Try to extract JSON array from response
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            if match:
                selected = json.loads(match.group(0))
                if isinstance(selected, list):
                    # Validate names exist
                    return [s for s in selected if s in skills]
        except Exception:
            pass

        # Fallback: use keyword-based trigger matching
        return self.skill_manager.match_skills(user_input)

    def _quick_llm_call(self, prompt: str) -> str:
        """Lightweight LLM call without tools."""
        if self.protocol == "openai":
            resp = self.client.chat.completions.create(
                model=self.model or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
                temperature=0.1,
            )
            return resp.choices[0].message.content or "[]"
        else:
            resp = self.client.messages.create(
                model=self.model or "claude-sonnet-4",
                max_tokens=256,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            texts = []
            for block in resp.content:
                if hasattr(block, "text"):
                    texts.append(block.text)
            return "\n".join(texts) or "[]"
