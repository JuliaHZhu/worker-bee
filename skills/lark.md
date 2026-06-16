---
name: lark
description: Feishu/Lark operations via lark-cli — messaging, docs, calendar, contacts, drive, base, mail, tasks, OKR
trigger: feishu, lark, 飞书, 发消息, 查文档, 日程, 通讯录, 云空间, 多维表格, 邮箱, 任务, OKR, 发送, send message, calendar, contact
tools:
  - _lark
category: feishu
---

# Lark — 飞书操作

All Feishu operations go through `_lark` → `lark-cli`. No direct API calls.

## Command Patterns

### Messaging (IM)
```
# Send a message
lark im +messages-send --chat-id oc_xxx --content "text"

# Search chat history
lark im +messages-search --query "keyword"

# List recent messages in a group
lark im +messages-list --chat-id oc_xxx --limit 20
```

### Contacts
```
lark contact +search-user --query "name"
lark contact +get-user --user-id ou_xxx
```

### Calendar
```
lark calendar +agenda                          # today's schedule
lark calendar +agenda --date 2026-06-15        # specific date
lark calendar events instance_view --params '{"calendar_id":"primary","start_time":"1700000000","end_time":"1700086400"}'
```

### Docs
```
lark docs +fetch --token doc_xxx               # read a doc
lark docs +search --query "keyword"             # search docs
```

### Drive (files)
```
lark drive +search --query "filename"
lark drive +upload --path /local/file.pdf --parent token_xxx
lark drive +download --token file_xxx --path /local/dest.pdf
```

### Base (multidimensional tables)
```
lark base +search --query "table name"
lark base +get-records --base-token xxx --table-id xxx
```

### Tasks
```
lark task +list
lark task +create --summary "task name"
```

### Generic API
```
lark api GET /open-apis/calendar/v4/calendars --params '{"page_size":10}'
```

## Safety

- Read commands run immediately
- Write commands (send, create, update, delete) require `require_confirmation=True`
- Auth/config commands are blocked — only run manually
- Output truncated at 4000 chars

## Pitfalls

- Chat IDs look like `oc_xxxxxxxx` (group) or `ou_xxxxxxxx` (user open_id)
- Doc tokens look like `doc_xxxxxxxx` or `wiki_xxxxxxxx`
- Calendar events use Unix timestamps for start_time/end_time
- Use `--params` for JSON parameters, `--query` for search terms
- The `+` prefix on shortcuts (e.g., `+search-user`) is required
