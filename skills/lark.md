---
name: lark
description: Feishu/Lark operations via lark-cli — messaging, docs, calendar, contacts, drive, base, mail, tasks, OKR
trigger: feishu, lark, 飞书, 发消息, 查文档, 日程, 通讯录, 云空间, 多维表格, 邮箱, 任务, OKR, 发送, send message, calendar, contact
tools:
  - feishu_lark
category: feishu
---

# Lark — 飞书操作

All Feishu operations go through `feishu_lark` → `lark-cli`. No direct API calls.

## Command Patterns

### Messaging (IM)
```
# Send a message
im +messages-send --chat-id oc_xxx --content "text"

# Search chat history
im +messages-search --query "keyword"

# List recent messages in a group
im +messages-list --chat-id oc_xxx --limit 20
```

### Contacts
```
contact +search-user --query "name"
contact +get-user --user-id ou_xxx
```

### Calendar
```
calendar +agenda                          # today's schedule
calendar +agenda --date 2026-06-15        # specific date
calendar events instance_view --params '{"calendar_id":"primary","start_time":"1700000000","end_time":"1700086400"}'
```

### Docs
```
docs +fetch --token doc_xxx               # read a doc
docs +search --query "keyword"             # search docs
```

### Drive (files)
```
drive +search --query "filename"
drive +upload --path /local/file.pdf --parent token_xxx
drive +download --token file_xxx --path /local/dest.pdf
```

### Base (multidimensional tables)
```
base +search --query "table name"
base +get-records --base-token xxx --table-id xxx
```

### Tasks
```
task +list
task +create --summary "task name"
```

### Generic API
```
api GET /open-apis/calendar/v4/calendars --params '{"page_size":10}'
```

## Safety

- Read commands always work
- Write commands require `lark_allow_write: true` in `~/.worker-bee/config.json`
- Enable during setup: `wb setup` → answer y to lark writes, or edit config.json manually
- lark-cli's own auth/scopes handle actual permission enforcement

## Pitfalls

- Chat IDs look like `oc_xxxxxxxx` (group) or `ou_xxxxxxxx` (user open_id)
- Doc tokens look like `doc_xxxxxxxx` or `wiki_xxxxxxxx`
- Calendar events use Unix timestamps for start_time/end_time
- Use `--params` for JSON parameters, `--query` for search terms
- The `+` prefix on shortcuts (e.g., `+search-user`) is required
