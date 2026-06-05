---
influence:
  search:
    # Meta verbs to strip from job title when building search queries
    strip_verbs:
      - "调研"
      - "研究"
      - "research"
      - "search"
      - "调查"
      - "查找"
      - "了解"
      - "分析"
      - "review"
      - "investigate"
    # Domains to prioritize (higher = earlier in extract list)
    preferred_domains:
      - "baike.baidu.com"
      - "zh.wikipedia.org"
      - "zhihu.com"
      - "weread.qq.com"
      - "douban.com"
      - "gov.cn"
    # Query construction style
    query_style: "entity_only"  # entity_only | with_context
  extract:
    max_length: 1500
    timeout: 15
---

# Agent Influence — Search Strategy

## Query Construction

1. Start from job title
2. Strip all meta verbs listed in `strip_verbs`
3. Use the remaining entity as the search query
4. **Never** append description text — it contains meta-verbs that pollute search

## Domain Preference

When extracting content from search results, prioritize domains in order.
Skip domains that return 403/empty.

## Output

- Save extracts individually: `{skill}-{YYYY-MM-DD}-extract-{domain}.md`
- Save final report: `{skill}-{YYYY-MM-DD}-report.md`
