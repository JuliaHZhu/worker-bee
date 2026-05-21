---
name: web-research
description: Research topics on the web and summarize findings
trigger: search, look up, research, find online, what is, who is, how to
tools:
  - net_web_search
  - net_web_extract
category: research
---

# Web Research Skill

When the user asks to research something online:

1. Formulate a precise search query
2. Call `net_web_search` to get results
3. If needed, call `net_web_extract` on promising URLs
4. Synthesize findings into a concise summary
5. Cite sources with URLs

## Input
- Research question or topic

## Output
- Summarized findings with citations
