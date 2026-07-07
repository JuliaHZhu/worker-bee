---
name: my-skill
description: One-sentence description of what this skill does
trigger: keyword1, keyword2, keyword3
tools:
  - fs_read_file
  - net_web_search
category: general
version: "1.0.0"
composability: atomic
---

# My Skill

Explain what this skill does, when to use it, and what problem it solves.
Keep it concise — one paragraph.

## Input

- `query` (string): What the user wants to search for
- `max_results` (int, optional): Maximum results to return, default 10

## Output

- Markdown summary of findings
- Source URLs for each finding

## Error Handling

- If the search returns no results, report "No results found" and stop
- If a source is unreachable, skip it and continue with remaining sources
- If the query is too broad, ask for clarification (but do not loop forever)

## Safety

- `fs_read_file` is read-only — safe to use without confirmation
- `net_web_search` only reads public data — safe without confirmation
- If this skill included `fs_write_file` or `sys_terminal`, you MUST document:
  - What commands are allowed (ALLOWLIST)
  - When confirmation is required
  - What the user must review before approving

## Examples

```markdown
<!-- Example 1: normal case -->
User: "Search for recent papers on distributed systems"
→ net_web_search(query="distributed systems papers 2024")
→ Return markdown list with titles and URLs

<!-- Example 2: error case -->
User: "Search for xyzabc123"
→ net_web_search(query="xyzabc123")
→ No results → report "No results found"
```

## Notes

- Keep examples realistic and copy-pasteable
- Document edge cases explicitly
- If this skill is composable, explain how it fits into larger workflows
