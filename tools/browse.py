"""Browser tool — wraps gstack's headless Chromium for hermes-lite.

Architecture:
  hermes-lite (Python) → subprocess → gstack browse binary (Bun)
                          ↓ HTTP POST
                   browse daemon → Playwright → Chromium

Commands: navigate, snapshot, click, fill, screenshot, js, etc.
See: https://github.com/garrytan/gstack

Requires: gstack browse binary built (bun run build in gstack/)
Env: GSTACK_BROWSE_BIN (default: auto-detect)
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from registry import registry

# ── Binary detection ──────────────────────────────────────────────────────

def _find_browse_bin() -> Optional[str]:
    """Auto-detect the gstack browse binary."""
    candidates = [
        os.environ.get("GSTACK_BROWSE_BIN", ""),
        # gstack cloned alongside hermes-lite
        str(Path(__file__).parent.parent.parent / "gstack" / "browse" / "dist" / "browse"),
        # gstack in home
        str(Path.home() / "gstack" / "browse" / "dist" / "browse"),
        # gstack in claude skills
        str(Path.home() / ".claude" / "skills" / "gstack" / "browse" / "dist" / "browse"),
        # system PATH
        shutil.which("browse") or "",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


_BROWSE_BIN = _find_browse_bin()


def _run_browse(*args: str, timeout: int = 30) -> str:
    """Run a browse command and return its output."""
    if not _BROWSE_BIN:
        return json.dumps({
            "error": "gstack browse binary not found. "
                     "Run 'bun run build' in gstack/ or set GSTACK_BROWSE_BIN."
        }, ensure_ascii=False)

    env = dict(os.environ)
    # Required on Linux servers without user namespace sandboxing
    if not env.get("GSTACK_CHROMIUM_NO_SANDBOX"):
        env["GSTACK_CHROMIUM_NO_SANDBOX"] = "1"

    cmd = [_BROWSE_BIN] + list(args)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        output = result.stdout + result.stderr
        return output[:8000] + ("\n... (truncated)" if len(output) > 8000 else output)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Browse command timed out after {timeout}s"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool functions (flat, one per concept) ────────────────────────────────

def browse_navigate(url: str) -> str:
    """Navigate to a URL."""
    return _run_browse("goto", url)


def browse_snapshot(annotate: bool = False) -> str:
    """Get a text snapshot of the current page with interactive element refs.
    
    Returns compact page structure with @e1, @e2... refs for clicks/fills.
    Set annotate=True to also get an annotated screenshot.
    """
    args = ["snapshot", "-i"]
    if annotate:
        args.append("-a")
    return _run_browse(*args)


def browse_click(ref: str) -> str:
    """Click an element by snapshot ref (e.g. @e5)."""
    return _run_browse("click", ref)


def browse_fill(ref: str, value: str) -> str:
    """Fill an input by snapshot ref."""
    return _run_browse("fill", ref, value)


def browse_type(text: str) -> str:
    """Type text into the focused element."""
    return _run_browse("type", text)


def browse_screenshot() -> str:
    """Take a screenshot and return the file path."""
    return _run_browse("screenshot")


def browse_scroll(ref: str = "") -> str:
    """Scroll the page or a specific element."""
    if ref:
        return _run_browse("scroll", ref)
    return _run_browse("scroll")


def browse_js(expression: str) -> str:
    """Execute JavaScript in the page and return the result."""
    return _run_browse("js", expression)


def browse_get_text() -> str:
    """Get the visible text content of the page."""
    return _run_browse("text")


def browse_get_html(selector: str = "") -> str:
    """Get the HTML of the page or a specific element."""
    if selector:
        return _run_browse("html", selector)
    return _run_browse("html")


def browse_back() -> str:
    """Navigate back."""
    return _run_browse("back")


def browse_reload() -> str:
    """Reload the current page."""
    return _run_browse("reload")


def browse_status() -> str:
    """Get browser status (tabs, URL, etc.)."""
    return _run_browse("status")


# ── Registry registration ─────────────────────────────────────────────────

def _register():
    tools = [
        ("browse_navigate", browse_navigate, "Navigate to a URL in the headless browser.",
         {"url": {"type": "string", "description": "Full URL to navigate to"}}, ["url"]),
        
        ("browse_snapshot", browse_snapshot, 
         "Get a text snapshot of the current page. Shows interactive elements as @e1, @e2 refs. "
         "Use this after navigation to see what's on the page and find elements to interact with.",
         {"annotate": {"type": "boolean", "description": "If true, also capture annotated screenshot", "default": False}},
         []),
        
        ("browse_click", browse_click,
         "Click an element identified by snapshot ref (e.g. @e5). Run browse_snapshot first to get refs.",
         {"ref": {"type": "string", "description": "Element reference from snapshot (e.g. @e5)"}}, ["ref"]),
        
        ("browse_fill", browse_fill,
         "Type text into an input field identified by snapshot ref.",
         {"ref": {"type": "string", "description": "Element reference (e.g. @e4)"},
          "value": {"type": "string", "description": "Text to fill"}}, ["ref", "value"]),
        
        ("browse_type", browse_type,
         "Type text into the currently focused element.",
         {"text": {"type": "string", "description": "Text to type"}}, ["text"]),
        
        ("browse_screenshot", browse_screenshot,
         "Take a screenshot of the current page. Returns the file path.",
         {}, []),
        
        ("browse_scroll", browse_scroll,
         "Scroll the page or a specific element.",
         {"ref": {"type": "string", "description": "Optional element ref to scroll", "default": ""}}, []),
        
        ("browse_js", browse_js,
         "Execute JavaScript in the browser context and return the result.",
         {"expression": {"type": "string", "description": "JavaScript code to execute"}}, ["expression"]),
        
        ("browse_get_text", browse_get_text,
         "Extract all visible text from the current page.",
         {}, []),
        
        ("browse_get_html", browse_get_html,
         "Get HTML source of the current page or a specific element.",
         {"selector": {"type": "string", "description": "Optional CSS selector", "default": ""}}, []),
        
        ("browse_back", browse_back, "Navigate back in browser history.", {}, []),
        
        ("browse_reload", browse_reload, "Reload the current page.", {}, []),
        
        ("browse_status", browse_status, "Get browser status info (tabs, current URL, etc.).", {}, []),
    ]

    for name, handler, desc, props, required in tools:
        registry.register(
            name=name,
            description=desc,
            parameters={
                "type": "object",
                "properties": {k: v for k, v in props.items()},
                "required": required,
            },
            handler=handler,
            tags=["browser", "gstack"],
            category="browser",
        )


# Auto-register on import
_register()
