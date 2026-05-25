#!/usr/bin/env python3
"""
podcast_agent.py — NotebookLM-style podcast script generator

Flow: source → parse → chunk → script (LLM) → JSON output
TTS synthesis functions are defined but NOT wired into main flow.
Designed for Hermes integration: can be called as a tool or standalone script.

Usage:
    python podcast_agent.py --source ~/docs/paper.pdf --tone casual --lang zh
    python podcast_agent.py --source ~/docs/notes.md --tone educational --lang en

Config: ~/.worker-bee/podcast_agent_config.json (auto-created on first run)
"""

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import List, Dict

# Hermes registry integration
try:
    from registry import registry
except ImportError:
    registry = None

# ── Optional deps ──────────────────────────────────────────────────────────
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

try:
    import pymupdf  # fitz
except ImportError:
    pymupdf = None

# ── Constants ──────────────────────────────────────────────────────────────
CONFIG_PATH = Path.home() / ".worker-bee" / "podcast_agent_config.json"
DEFAULT_SPEAKER_A = "alloy"      # OpenAI TTS voices
DEFAULT_SPEAKER_B = "nova"
MAX_CHARS_PER_LINE = 100         # ~5-8s spoken, from open-notebooklm prompts.py
DEFAULT_MODEL = "gpt-4o"

# ── Prompts ────────────────────────────────────────────────────────────────
SCRIPT_SYSTEM_PROMPT = """You are a professional podcast scriptwriter.

Generate a natural two-person dialogue podcast based on the provided source material.

## Characters
- Host A (Xiao Ming): curious, asks questions, expresses surprise, keeps energy high
- Host B (Xiao Hong): knowledgeable, explains deeply, provides insights, occasionally interrupts to add detail

## Rules
1. Each line of dialogue MUST be no more than {max_chars} characters (finishes in ~5-8 seconds)
2. Use natural spoken language, NOT written/essay style
3. Include transition phrases: "Let me think...", "That's fascinating!", "So in other words..."
4. Do NOT read the source verbatim — restructure, explain, and interpret
5. Start with an engaging hook or question
6. The dialogue should feel like a real conversation with back-and-forth, not alternating monologues

## Style
{tone_modifier}

## Output Language
{language_modifier}

## Output Format
Return STRICTLY valid JSON without markdown code blocks. Begin directly with the JSON:
{{
  "title": "Compelling podcast title",
  "summary": "One-sentence summary of the episode",
  "dialogue": [
    {{"speaker": "Host A", "text": "..."}},
    {{"speaker": "Host B", "text": "..."}}
  ]
}}
"""

TONE_MAP = {
    "professional": "The tone should be professional, authoritative, and precise.",
    "casual": "The tone should be casual, friendly, and conversational like friends chatting over coffee.",
    "humorous": "The tone should be light, humorous, with occasional witty remarks and playful banter.",
    "educational": "The tone should be educational but engaging, like a great teacher explaining to curious students.",
}

LANG_MAP = {
    "zh": "Chinese (中文)",
    "en": "English",
    "zh-CN": "Chinese (简体中文)",
    "zh-TW": "Chinese (繁體中文)",
}


# ── Config management ──────────────────────────────────────────────────────
def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def ensure_config() -> dict:
    cfg = load_config()
    changed = False

    # Auto-detect available API keys
    if "openai_api_key" not in cfg:
        key = os.environ.get("OPENAI_API_KEY", "")
        if key:
            cfg["openai_api_key"] = key
            cfg["base_url"] = "https://api.openai.com/v1"
            cfg["provider"] = "openai"
            changed = True

    if "moonshot_api_key" not in cfg and "provider" not in cfg:
        key = os.environ.get("MOONSHOT_API_KEY", "")
        if key:
            cfg["moonshot_api_key"] = key
            cfg["base_url"] = "https://api.moonshot.cn/v1"
            cfg["provider"] = "moonshot"
            changed = True

    if "model" not in cfg:
        # Default model depends on provider
        cfg["model"] = "gpt-4o" if cfg.get("provider") == "openai" else "moonshot-v1-32k"
        changed = True
    if "voice_a" not in cfg:
        cfg["voice_a"] = DEFAULT_SPEAKER_A
        changed = True
    if "voice_b" not in cfg:
        cfg["voice_b"] = DEFAULT_SPEAKER_B
        changed = True
    if changed:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    return cfg


# ── Document parsing ───────────────────────────────────────────────────────
def parse_file(path: Path) -> str:
    """Parse PDF, MD, TXT into plain text."""
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Not a file: {path}")
    # Guard against reading system-sensitive files
    forbidden_prefixes = ("/etc/", "/proc/", "/sys/", "/dev/")
    if str(path).startswith(forbidden_prefixes):
        raise PermissionError(f"Access denied to system path: {path}")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        if pymupdf is None:
            raise RuntimeError("pymupdf not installed. Run: pip install pymupdf")
        doc = pymupdf.open(path)
        parts = []
        for page in doc:
            parts.append(page.get_text())
        return "\n\n".join(parts)
    elif suffix in (".md", ".txt", ".markdown", ".rst"):
        return path.read_text(encoding="utf-8")
    else:
        # Try as plain text
        return path.read_text(encoding="utf-8")


def chunk_text(text: str, max_tokens: int = 12000) -> List[str]:
    """Character-based chunking. CJK ~1.5-2 chars/token (Gemini/Moonshot tokenizer)."""
    max_chars = int(max_tokens * 1.5)  # conservative for CJK
    if len(text) <= max_chars:
        return [text]
    chunks = []
    for i in range(0, len(text), max_chars):
        chunks.append(text[i:i + max_chars])
    return chunks


# ── Script generation ──────────────────────────────────────────────────────
def generate_script(source_text: str, tone: str, lang: str, model: str, cfg: dict) -> dict:
    if OpenAI is None:
        raise RuntimeError("openai package not installed. Run: pip install openai")

    provider = cfg.get("provider", "openai")
    base_url = cfg.get("base_url")
    if provider == "openai":
        api_key = cfg.get("openai_api_key")
    elif provider == "moonshot":
        api_key = cfg.get("moonshot_api_key")
    else:
        api_key = cfg.get("openai_api_key") or cfg.get("moonshot_api_key")

    if not api_key:
        raise RuntimeError(f"No API key configured for provider: {provider}")

    client = OpenAI(api_key=api_key, base_url=base_url)

    tone_modifier = TONE_MAP.get(tone, TONE_MAP["educational"])
    language_modifier = LANG_MAP.get(lang, LANG_MAP.get("zh", "Chinese"))

    system_prompt = SCRIPT_SYSTEM_PROMPT.format(
        max_chars=MAX_CHARS_PER_LINE,
        tone_modifier=tone_modifier,
        language_modifier=language_modifier,
    )

    # If text is very long, summarize first then script
    chunks = chunk_text(source_text)
    if len(chunks) > 1:
        condensed = condense_chunks(client, model, chunks)
        source_for_script = condensed
    else:
        source_for_script = source_text

    user_prompt = f"Source material:\n\n{source_for_script}\n\nGenerate the podcast script now."

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=4000,
    )

    raw = resp.choices[0].message.content.strip()
    # Strip possible markdown fences
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"```\s*$", "", raw)

    try:
        script = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM returned invalid JSON:\n{raw[:500]}\nError: {e}")

    # Validate structure
    if "dialogue" not in script or not isinstance(script["dialogue"], list):
        raise RuntimeError("Invalid script structure: missing 'dialogue' array")

    return script


def condense_chunks(client, model: str, chunks: List[str]) -> str:
    """When source is too long, condense each chunk to key points, then join."""
    summaries = []
    for i, chunk in enumerate(chunks[:5]):  # cap at 5 chunks
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Summarize the following text into key bullet points. Keep all important facts, names, numbers, and arguments."},
                {"role": "user", "content": chunk},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        summaries.append(resp.choices[0].message.content)
    return "\n\n".join(summaries)


# ── TTS synthesis ──────────────────────────────────────────────────────────
def synthesize_dialogue(dialogue: List[Dict], voice_a: str, voice_b: str, api_key: str) -> List[Path]:
    if OpenAI is None:
        raise RuntimeError("openai package not installed")

    client = OpenAI(api_key=api_key)
    segment_files = []

    voice_map = {"Host A": voice_a, "Host B": voice_b}

    for i, turn in enumerate(dialogue):
        speaker = turn.get("speaker", "Host A")
        text = turn.get("text", "").strip()
        if not text:
            continue

        voice = voice_map.get(speaker, voice_a)
        # OpenAI TTS supports: alloy, echo, fable, onyx, nova, shimmer
        # If user configured ElevenLabs, we'd call that instead.

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = Path(f.name)

        resp = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
        )
        resp.stream_to_file(str(tmp_path))
        segment_files.append(tmp_path)

    return segment_files


def merge_audio_segments(segment_files: List[Path], output_path: Path, crossfade_ms: int = 300) -> Path:
    if AudioSegment is None:
        raise RuntimeError("pydub not installed. Run: pip install pydub")

    if not segment_files:
        raise RuntimeError("No audio segments to merge")

    combined = AudioSegment.from_mp3(str(segment_files[0]))
    for seg_path in segment_files[1:]:
        seg = AudioSegment.from_mp3(str(seg_path))
        # Simple append with tiny crossfade for naturalness
        combined = combined.append(seg, crossfade=crossfade_ms)

    combined.export(str(output_path), format="mp3")

    # Cleanup temp files
    for p in segment_files:
        p.unlink(missing_ok=True)

    return output_path


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate a podcast from source documents")
    parser.add_argument("--source", "-s", required=True, help="Path to source file (PDF, MD, TXT)")
    parser.add_argument("--tone", "-t", default="educational", choices=list(TONE_MAP.keys()), help="Podcast tone")
    parser.add_argument("--lang", "-l", default="zh", choices=list(LANG_MAP.keys()), help="Output language")
    parser.add_argument("--output", "-o", default=None, help="Output MP3 path")
    parser.add_argument("--model", "-m", default=None, help="LLM model (default from config)")
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Error: source file not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    cfg = ensure_config()
    provider = cfg.get("provider", "moonshot")
    api_key = cfg.get("openai_api_key") or cfg.get("moonshot_api_key")
    if not api_key:
        print("Error: No API key configured (checked OPENAI_API_KEY, MOONSHOT_API_KEY).", file=sys.stderr)
        print(f"Set it in env or edit {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    model = args.model or cfg.get("model", DEFAULT_MODEL)
    # Fix stale model when provider switched
    if provider == "moonshot" and model.startswith("gpt-"):
        model = "moonshot-v1-32k"
    elif provider == "openai" and model.startswith("moonshot-"):
        model = "gpt-4o"

    # 1. Parse
    print(f"[1/2] Parsing {source_path} ...")
    raw_text = parse_file(source_path)
    print(f"      Extracted {len(raw_text)} chars")

    # 2. Generate script
    print(f"[2/2] Generating script (provider={provider}, model={model}, tone={args.tone}, lang={args.lang}) ...")
    try:
        script = generate_script(raw_text, args.tone, args.lang, model, cfg)
    except Exception as e:
        print(f"Error: Podcast generation failed: {e}", file=sys.stderr)
        sys.exit(1)
    title = script.get("title", "Untitled Podcast")
    dialogue = script["dialogue"]
    print(f"      Title: {title}")
    print(f"      Dialogue turns: {len(dialogue)}")

    # Save script
    script_path = source_path.with_suffix(".podcast.json")
    script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      Script saved: {script_path}")

    # Report
    print("\n" + "=" * 50)
    print("✅ Podcast script generated!")
    print(f"   Title:  {title}")
    print(f"   Turns:  {len(dialogue)}")
    print(f"   Script: {script_path}")
    print("=" * 50)

    # Preview
    print("\n--- Preview ---")
    for turn in dialogue[:6]:
        speaker = turn.get("speaker", "?")
        text = turn.get("text", "")
        print(f"{speaker}: {text}")
    if len(dialogue) > 6:
        print(f"... ({len(dialogue) - 6} more turns)")
    print("---------------")


if __name__ == "__main__":
    main()


# ── Hermes Tool Registration ─────────────────────────────────────────────
def podcast_agent(
    source: str,
    tone: str = "educational",
    lang: str = "zh",
    model: str = "",
) -> str:
    """Generate a podcast-style dialogue script from a source document.

    Args:
        source: Path to source file (PDF, MD, TXT)
        tone: Podcast tone - professional, casual, humorous, educational
        lang: Output language - zh, en, zh-CN, zh-TW
        model: LLM model override (optional)
    Returns:
        JSON podcast script with title, summary, and dialogue array.
    """
    source_path = Path(source)
    if not source_path.exists():
        return f"Error: source file not found: {source}"

    cfg = ensure_config()
    provider = cfg.get("provider", "moonshot")
    api_key = cfg.get("openai_api_key") or cfg.get("moonshot_api_key")
    if not api_key:
        return "Error: No API key configured. Set OPENAI_API_KEY or MOONSHOT_API_KEY."

    use_model = model or cfg.get("model", DEFAULT_MODEL)
    if provider == "moonshot" and use_model.startswith("gpt-"):
        use_model = "moonshot-v1-32k"
    elif provider == "openai" and use_model.startswith("moonshot-"):
        use_model = "gpt-4o"

    raw_text = parse_file(source_path)
    try:
        script = generate_script(raw_text, tone, lang, use_model, cfg)
    except Exception as e:
        return f"Error: Podcast generation failed: {e}"

    # Save script
    script_path = source_path.with_suffix(".podcast.json")
    script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    title = script.get("title", "Untitled")
    dialogue = script["dialogue"]
    preview = "\n".join(
        f"{t.get('speaker', '?')}: {t.get('text', '')}"
        for t in dialogue[:6]
    )
    more = f"\n... ({len(dialogue) - 6} more turns)" if len(dialogue) > 6 else ""

    return (
        f"✅ Podcast script generated!\n"
        f"Title: {title}\n"
        f"Turns: {len(dialogue)}\n"
        f"Saved: {script_path}\n\n"
        f"--- Preview ---\n"
        f"{preview}{more}\n"
        f"---------------"
    )


registry.register(
    name="podcast_agent",
    description=(
        "NotebookLM-style podcast script generator.\n"
        "Convert any document (PDF, MD, TXT) into a natural two-person dialogue podcast script.\n"
        "Outputs JSON with title, summary, and dialogue array.\n"
        "Supports OpenAI and Moonshot (Kimi) APIs."
    ),
    parameters={
        "properties": {
            "source": {
                "type": "string",
                "description": "Path to source file (PDF, MD, TXT)",
            },
            "tone": {
                "type": "string",
                "description": "Podcast tone",
                "enum": ["professional", "casual", "humorous", "educational"],
                "default": "educational",
            },
            "lang": {
                "type": "string",
                "description": "Output language",
                "enum": ["zh", "en", "zh-CN", "zh-TW"],
                "default": "zh",
            },
            "model": {
                "type": "string",
                "description": "LLM model override (optional)",
                "default": "",
            },
        },
        "required": ["source"]
    },
    handler=podcast_agent,
    tags=["content", "podcast", "notebooklm"],
    category="productivity"
) if registry is not None else None
