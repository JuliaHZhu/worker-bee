# Feishu Gateway

飞书 ↔ Worker-Bee 双向桥接。补全蜂群架构中缺失的"收消息"能力。

## 背景

- `lark-cli` 扫码认证 = **只能发消息**（客户端模式）
- 飞书 webhook 事件订阅 = **能收消息**（服务端模式）
- Gateway 把两者桥接起来，让蜂群可以"听到"飞书用户在说什么

## 架构

```
[你在飞书发消息给 Bot]
        ↓
[飞书服务器] —HTTP POST→ [Gateway on PM:8080]
        ↓
[Gateway] publish → NATS: swarm.incoming.feishu
        ↓
[蜂群任意节点] subscribe → 走 Agent 循环处理
        ↓
[处理结果] publish → NATS: swarm.outgoing.feishu
        ↓
[Gateway] 调用飞书 API 发回复
        ↓
[飞书] 你收到回复
```

## 配置

创建 `~/.worker-bee/gateway.json`：

```json
{
  "app_id": "cli_xxxxxxxxxxxxxxxx",
  "app_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

> 获取方式：飞书开放平台 https://open.feishu.cn/app/ → 创建企业自建应用（机器人）→ 凭证与基础信息

## 运行

```bash
python gateway/feishu_gateway.py
```

或后台运行：

```bash
nohup python gateway/feishu_gateway.py >> ~/.worker-bee/gateway.log 2>&1 &
```

## 飞书应用设置

1. 事件订阅 → 请求地址：`http://43.156.129.115:8080/webhook/feishu`
2. 添加事件：`im.message.receive_v1`（单聊消息）
3. 权限管理：开通 `im:message:send_as_bot`
4. 发布版本 → 审核通过
5. 在飞书里找到这个机器人，发消息测试

## 测试

发消息给机器人后，检查 PM 上的 Gateway 日志应有输出：

```
[GW] From ou_xxxxx: 你好
```

同时任意 listener 节点可查看 NATS 消息：

```bash
python -c "
import asyncio, json
from nats import connect

async def t():
    nc = await connect('nats://43.156.129.115:4222')
    sub = await nc.subscribe('swarm.incoming.feishu')
    async for m in sub.messages:
        print(json.loads(m.data))
asyncio.run(t())
"
```
