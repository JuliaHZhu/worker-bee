---
name: tagged-session
description: Use when the user wants to tag, rewind (archive), close, or organize session messages. Replaces the old /task workflow.
trigger: tag, tagged session, tag this, rewind, archive, close session, 打标签, 归档, 回滚, 关闭会话, purpose, set purpose, 设置意图
tools:
  - session_list_messages
  - session_tag_message
  - session_untag_message
  - session_archive_after
  - session_archive_from
  - session_unarchive_all
  - session_set_purpose
  - session_get_meta
  - session_close
category: tagged_session
phase: implement
---

# Tagged Session Skill

> Phase: **implement** — the user is actively shaping the session, not just chatting.
>
> Tagged session = semantic labels on messages + soft rewind (archive) + close → wiki extraction.
> This replaces the old `/task` table. Tasks are now expressed as **session purpose + message tags**.

## When This Skill Activates

- User says "tag this", "给这句话打个标签", "mark as design"
- User says "rewind", "go back", "回滚到之前", "archive the last few"
- User says "close this session", "结束这次讨论", "extract to wiki"
- User says "what's the purpose of this session", "set purpose"
- User mentions tagging, organizing, or archiving conversation history

## Workflow

### 1. Tag messages

**Always start by listing messages** so the user can pick by ID.

1. Call `session_list_messages` with `session_id=<Current session ID>`
2. Show the numbered list to the user
3. Wait for user reply in format: `1 #design` or `1,3 #coding` or `1 #design, 3 #question`
4. Parse the reply:
   - Split by comma to get individual `id #tag` pairs
   - For each pair, call `session_tag_message(session_id, message_id, tag)`
5. Confirm: "Tagged message 1 with #design, message 3 with #coding"

**User shortcut:** If the user prefixes their input with `#tag` (e.g. `#design how should the state machine work?`), the tag is automatically extracted at the CLI level. You don't need to do anything in that case.

### 2. Rewind (archive)

When the user wants to discard or backtrack part of the conversation:

1. Call `session_list_messages` to show IDs
2. Ask user: "Rewind after which message? Reply with the ID."
3. User replies with a number (e.g. `5`)
4. Call `session_archive_after(session_id, message_id)`
5. Confirm: "Archived all messages after [5]. The conversation continues from there."

**Important:** Archived messages are hidden from LLM context but preserved in the database. They appear in `/history --all` and are included when the session is extracted to wiki.

### 3. Set purpose

When the user wants to declare what this session is for:

1. Call `session_set_purpose(session_id, purpose)`
2. Confirm: "Session purpose set to: ..."

This replaces the old `/task add` concept. Instead of creating a separate task row, you simply label the session.

### 4. Close session

When the user says the discussion is done:

1. Call `session_get_meta(session_id)` to check current state
2. Ask: "Close this session? Also extract transcript to wiki? [y/n/wiki]"
3. Based on reply:
   - `y` or `yes` → `session_close(session_id, extract_to_wiki=False)`
   - `wiki` → `session_close(session_id, extract_to_wiki=True)`
   - `n` or `no` → do nothing
4. If extracted, report the wiki file path

## Input Parsing Rules

### Tag reply format
```
<id> <#tag>                 # single
<id1> <#tag1>, <id2> <#tag2>   # multiple
```

Examples:
- `1 #design`
- `2 #coding, 5 #question`
- `1 #design, 2 #design, 4 #bug`

If the user replies without an ID (just `#design`), assume they mean the **most recent user message**.

### Rewind reply format
```
<id>          # archive everything AFTER this message
from <id>     # archive this message and everything after
```

## Anti-Patterns

- **Don't guess message IDs.** Always list first.
- **Don't tag without user confirmation** unless they explicitly said "tag the last message as #design".
- **Don't close without asking** if wiki extraction is desired.
- **Don't mix archive and tag in one step.** Archive changes context; tag does not. Separate them.

## Composability

- Pairs well with **create-task-skill** when tagging is part of a larger workflow (e.g. "research this topic, tag the key findings #research").
- After `session_close(extract_to_wiki=True)`, the **llm-wiki** ingest flow can pick up `raw/sessions/session-xxx.md` and create concept pages.
