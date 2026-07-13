"""Protocol layer tests — schema normalisation, provider adapters."""
import pytest

from agent.protocols import (
    normalize_schema,
    ProviderAdapter,
    _truncate_description,
    _flatten_anyof_oneof,
    _normalize_schema_props,
)


class TestTruncateDescription:
    def test_short_description_unchanged(self):
        text = "Short description."
        assert _truncate_description(text) == text

    def test_long_description_truncated(self):
        text = "x" * 2000
        result = _truncate_description(text)
        assert len(result) <= 1536
        assert result.endswith("...")


class TestFlattenAnyOf:
    def test_flatten_simple_anyof(self):
        node = {"anyOf": [{"type": "string"}, {"type": "integer"}]}
        out = _flatten_anyof_oneof(node)
        assert out.get("type") == ["string", "integer"]
        assert "anyOf" not in out

    def test_flatten_oneof(self):
        node = {"oneOf": [{"type": "boolean"}, {"type": "null"}]}
        out = _flatten_anyof_oneof(node)
        assert out.get("type") == ["boolean", "null"]

    def test_non_dict_passthrough(self):
        assert _flatten_anyof_oneof("string") == "string"


class TestNormalizeSchemaProps:
    def test_nested_properties_flattened(self):
        props = {
            "name": {"type": "string"},
            "age": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        }
        out = _normalize_schema_props(props)
        assert out["name"]["type"] == "string"
        assert out["age"]["type"] == ["integer", "null"]

    def test_additional_properties_default(self):
        props = {"data": {"type": "object", "properties": {"x": {"type": "string"}}}}
        out = _normalize_schema_props(props)
        assert out["data"]["additionalProperties"] is False


class TestNormalizeSchema:
    def test_description_truncated(self):
        schema = {
            "name": "test_tool",
            "description": "x" * 2000,
            "parameters": {"type": "object", "properties": {}},
        }
        out = normalize_schema(schema)
        assert len(out["description"]) <= 1536

    def test_anyof_in_parameters(self):
        schema = {
            "name": "test_tool",
            "description": "A tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"anyOf": [{"type": "string"}, {"type": "number"}]},
                },
            },
        }
        out = normalize_schema(schema)
        props = out["parameters"]["properties"]
        assert props["value"]["type"] == ["string", "number"]
        assert "anyOf" not in props["value"]

    def test_preserves_input_schema_key(self):
        schema = {
            "name": "test_tool",
            "description": "A tool.",
            "input_schema": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
            },
        }
        out = normalize_schema(schema)
        assert "input_schema" in out
        assert "parameters" not in out


class TestProviderAdapter:
    def test_reasoning_model_drops_temperature(self):
        adapter = ProviderAdapter("openai", "o1-preview")
        assert adapter.filter_temperature(0.7) is None

    def test_normal_model_keeps_temperature(self):
        adapter = ProviderAdapter("openai", "gpt-4")
        assert adapter.filter_temperature(0.7) == 0.7

    def test_deepseek_supports_reasoning(self):
        adapter = ProviderAdapter("deepseek", "deepseek-chat")
        assert adapter.supports_reasoning_content() is True

    def test_openai_no_reasoning_content(self):
        adapter = ProviderAdapter("openai", "gpt-4")
        assert adapter.supports_reasoning_content() is False

    def test_for_model_heuristic(self):
        assert ProviderAdapter.for_model("claude-3-opus").provider == "anthropic"
        assert ProviderAdapter.for_model("deepseek-chat").provider == "deepseek"
        assert ProviderAdapter.for_model("gpt-4").provider == "openai"

    def test_system_prompt_stripped(self):
        adapter = ProviderAdapter("openai", "gpt-4")
        assert adapter.prepare_system_prompt("  hello  ") == "hello"
