---
name: skill-creating-trainer
description: Use when the user has drafted a skill markdown and wants review, validation, or feedback on structure and content.
trigger: check skill, review skill, skill格式, skill写得对吗, 帮我看看skill, skill review, validate skill
tools:
  - fs_read_file
  - fs_search_files
category: skill-authoring
---

# Skill Creating Trainer

Review the skill markdown the user provides. Use this checklist.

## Frontmatter (Hard Rules)

- [ ] `name`: lowercase, hyphens only, ≤64 chars
- [ ] `description`: starts with "Use when...", ≤1024 chars, third person
- [ ] `trigger`: specific multi-word phrases, no single-word triggers like "web" or "help"
- [ ] `tools`: 2-4 items, each must exist in the registry
- [ ] `category`: matches an existing category or "skill-authoring"

## Body Structure

- [ ] Title matches the skill's purpose
- [ ] Overview in 1-2 sentences
- [ ] "When to Use" with both positive triggers and counter-examples ("Don't use for...")
- [ ] Workflow: numbered steps, each names a specific tool
- [ ] Common Pitfalls or Red Flags section

## Content Quality

- [ ] No hard-coded business constants (categories, quotas, magic numbers)
- [ ] No state stored in the skill file itself
- [ ] No narrative storytelling ("In session 2025-10-03, we found...")
- [ ] One excellent example beats five mediocre ones

## Anti-Pattern Scan

| Pattern | Status |
|---------|--------|
| Trigger is a single common word | ❌ Fail |
| Tools list > 5 items | ❌ Fail |
| Workflow steps are vague ("analyze it") | ❌ Fail |
| No "Output" section defined | ❌ Fail |
| Description summarizes workflow instead of trigger | ❌ Fail |

## Feedback Format

```
Score: X/10

Pass: [list]
Fail: [list with fix instructions]
Suggested rewrite: [if applicable]
```
