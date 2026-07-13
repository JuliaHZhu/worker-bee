---
name: api-resilience
description: API 断线/超时/限流时的自动恢复与降级策略
trigger: api 断了, api 超时, 限流, rate limit, 429, connection error, 网络错误, api error, 调用失败, 模型没响应, api 不稳定, 服务不可用, 502, 503, 断线重连, 重试任务
tools:
  - sys_terminal
  - send_message
  - deck_manage
category: infra
composability: atomic
---

# API 韧性 — 断线自动恢复

## 什么时候触发

Agent 调用 LLM API 时出现以下任一情况：
- 超时（timeout，无响应超过 30s）
- 限流（429 Too Many Requests）
- 连接断开（connection reset / broken pipe）
- 服务端错误（502/503 Service Unavailable）
- 任何非 200 的 API 错误导致对话中断

## 自动恢复机制（代码层已内置）

`agent/loop.py` 已配置自动重试：
- **最多 3 次重试**
- **指数退避**：第 1 次等 1s，第 2 次等 2s，第 3 次等 4s
- **限流特殊处理**：遇到 429 时，优先读取 Retry-After header，否则默认等 60s
- **异常分类**：超时 vs 限流 vs 服务端错误，分别记录不同日志

## Skill 层的恢复动作

当代码层 3 次重试全部失败后，Agent 按以下顺序执行：

### 1. 立即检查状态

```python
# 检查当前有多少任务因限流暂停
result = sys_terminal("worker-bee retry-rate-limited", require_confirmation=False)
# 检查网络连通性
result2 = sys_terminal("curl -s -o /dev/null -w '%{http_code}' https://api.moonshot.cn/v1 || echo 'FAIL'", require_confirmation=False)
```

### 2. 按错误类型处理

| 错误类型 | 动作 |
|---|---|
| **429 限流** | 通知用户"当前限流，已自动排队，预计 X 分钟后恢复"；调用 `worker-bee retry-rate-limited` 恢复 cron job；建议用户稍后重试 |
| **超时/连接断开** | 通知用户"网络波动，正在重连"；等待 5s 后自动重试一次；如果仍失败，保存当前对话上下文到 handoff |
| **5xx 服务端错误** | 通知用户"模型服务暂时不可用"；建议切换到备用模型或降低 temperature 重试 |
| **认证失败（401/403）** | 通知用户"API Key 可能失效或余额不足"；建议 `worker-bee setup` 重新配置 |

### 3. 上下文保护

如果恢复失败，确保不丢失用户当前任务：

```python
# 导出当前会话 handoff
sys_terminal("echo '[API中断恢复] 当前任务需继续' >> ~/.worker-bee/handoff_queue.txt", require_confirmation=False)
```

### 4. 降级建议

如果 API 持续不稳定，主动建议用户：
- 切换到 **focus 模式** 减少工具调用频率 → `deck_manage(action="set_focus")`
- 降低 temperature 减少模型计算量
- 将大任务拆分为多个小任务，分批执行

## 回复模板

**限流场景：**
```
API 限流了（429）。已自动重试 3 次，仍被节流。

已做的事：
- 恢复了 X 个因限流暂停的 cron 任务
- 下次自动重试时间：X 分钟后

建议：稍等 1-2 分钟再发消息，或换用轻量模型。
```

**超时/断线场景：**
```
API 连接超时。已自动重试并退避，仍未恢复。

已保存当前对话上下文。你可以：
1. 直接重试同一句话
2. 用 /export 导出 handoff，稍后继续
3. 检查网络：curl -I https://api.moonshot.cn/v1
```

## Pitfalls

1. **不要无限重试。** 代码层已限制 3 次，skill 层不要再加循环。
2. **不要把 API Key 暴露给用户。** 错误日志里如果有 key，用 `***` 替换。
3. **区分"API 断了"和"工具执行失败"。** 工具失败是 `registry.call()` 的问题，走 tool error 路径；API 断了是 `protocol.api_call()` 的问题，走本 skill。
4. **cron job 的限流和交互式会话的限流是两套系统。** 交互式会话断线不会自动恢复 cron job，需要显式调用 `worker-bee retry-rate-limited`。
