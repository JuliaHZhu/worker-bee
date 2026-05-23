---
name: tagged-session
description: Use when the user wants to save, tag, find, archive, or resume a session as a markdown note. Replaces the old /task workflow.
trigger: tag, tagged session, save session, find session, archive session, resume session, 打标签, 保存会话, 搜索会话, 归档, 恢复会话
tools:
  - tagged_session
category: tagged_session
phase: implement
---

# Tagged Session Skill

> Phase: **implement** — the user is organizing or retrieving session knowledge.
>
> Tagged session = save live session → markdown note → tag → find → archive → resume.
> This replaces the old `/task` table. Tasks are now expressed as **session purpose + message tags**.

## When This Skill Activates

- User says "save this session", "保存这次对话", "extract to wiki"
- User says "tag this as #design", "给这个打标签"
- User says "find my #design sessions", "找出带某标签的会话"
- User says "archive this", "归档", "close and archive"
- User says "resume session abc123", "回顾上次讨论", "load previous session"
- User mentions organizing, searching, or retrieving past conversation notes

## Workflow

### 1. Save a session

When the user wants to preserve the current (or a past) session:

1. Call `tagged_session(action='save', session=<session_id>, content=<optional title>)`
2. The tool reads all messages from SQLite, builds a markdown note with YAML frontmatter, and writes to `~/wiki-hermes-lite/sessions/{session_id}.md`
3. Report: "已保存到 ... (共 N 条消息)"

If `content` is omitted, the tool uses the session's existing title or purpose.

### 2. Tag a saved note

When the user wants to add or remove labels on an existing note:

1. Call `tagged_session(action='tag', session=<session_id>, content=<tag expression>)`
2. Tag expression formats:
   - `+#design` — add #design
   - `-#draft` — remove #draft
   - `#design,#coding` — add multiple
   - `+#design,-#draft,#review` — mixed
3. Report the updated tag list

### 3. Find sessions by tag

When the user wants to search past notes:

1. Call `tagged_session(action='find', content=<comma-separated tags>)`
2. The tool searches the active pool (`~/wiki-hermes-lite/sessions/*.md`, excluding `archive/`)
3. Returns a list of matching sessions with title and tags

Tag matching uses **intersection** — a note must have ALL requested tags to match.

### 4. Archive a note

When the user wants to move a note out of the active pool:

1. Call `tagged_session(action='archive', session=<session_id>)`
2. The tool moves the file to `archive/` and sets `archived: true` in frontmatter
3. Archived notes are excluded from `find` and `list` but can still be `resume`d

### 5. Resume a note

When the user wants to bring a past session back into context:

1. Call `tagged_session(action='resume', session=<session_id>)`
2. The tool reads the markdown body and returns the content (truncated to ~3000 chars)
3. Present the content to the user or use it to seed the current discussion

### 6. List active notes

When the user wants an overview:

1. Call `tagged_session(action='list')`
2. Returns all non-archived notes with session_id, title, tags, and creation date

## Input Parsing Rules

### Tag expression
```
+#tag          # add
-#tag          # remove
#tag           # add (shorthand)
+#tag1,-#tag2  # mixed batch
```

### Find query
```
#design                 # single tag
#design,#architecture   # intersection
```

## Anti-Patterns

- **Don't save without a session ID.** The tool needs to know which session to export.
- **Don't guess tags.** If the user says "tag this", ask which tags or confirm your assumption.
- **Don't archive without confirming.** Ask "Archive this session note?" before calling.
- **Don't mix live DB tagging with note tagging.** Message-level tags (via `#prefix` in chat) live in SQLite and are collected at `save` time. Note-level tags (via `tagged_session action=tag`) live in the markdown frontmatter.

## Composability

- After `save`, the **llm-wiki** ingest flow can pick up `sessions/xxx.md` and create concept pages.
- Pairs well with **wiki** skill when the user wants to turn a session into structured knowledge.
- Pairs well with **learn-from-doing** when reviewing archived sessions for insights.
