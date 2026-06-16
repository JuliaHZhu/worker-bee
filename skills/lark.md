---
name: lark
description: Feishu/Lark 飞书操作入口 — 路由层，判断用户意图后加载具体子 skill
trigger: feishu, lark, 飞书, 发消息, 查文档, 日程, 通讯录, 云空间, 多维表格, 邮箱, 任务, OKR, 发送, send message, calendar, contact, 文件, 上传, 下载
tools:
  - feishu_lark
category: feishu
---

# Lark — 飞书操作路由

你 **不直接执行具体操作**。你的任务是判断用户要做什么，然后加载对应的子 skill。

## 意图路由表

| 用户说什么 | 加载哪个 skill | 为什么 |
|-----------|---------------|--------|
| "发给张三"、"通知团队"、"看看群里说了什么" | `lark-messaging` | 收发消息 |
| "找一下李四"、"搜群"、"查一下 open_id" | `lark-contact` | 名字 ↔ ID 解析 |
| "传个文件"、"下载附件"、"分享文档" | `lark-drive` | 文件上传/下载/分享 |
| 直接给了一串 lark-cli 命令 | `feishu_lark` tool | 用户已知命令，直接执行 |

## 组合场景

很多时候一个任务需要 **多个 skill 协作**。典型的组合模式：

**"发文件给张三"**
1. `lark-contact` → 搜"张三"拿 open_id
2. `lark-drive` → 上传文件拿 file_token
3. `lark-messaging` → 发一条带文件的消息

**"把群里那个文件下载下来"**
1. `lark-contact` → 搜群名拿 chat_id
2. `lark-messaging` → 拉最近消息，找到文件 token
3. `lark-drive` → 下载文件到本地

## 什么时候不用 agent loop

用户如果已经在用 `wb lark` CLI（如 `wb lark send --to 张三 hello`），说明他在直接操作，不需要你介入。只有**通过自然语言请求**时才走 skill 流程。

## 底线

- 用户给了名字 → 必须先解析成 ID，不能直接传名字给 lark-cli
- 涉及发消息/传文件 → 先确认目标（发给谁、传到哪）
- 不确定是私聊还是群聊 → 问用户，不要猜
