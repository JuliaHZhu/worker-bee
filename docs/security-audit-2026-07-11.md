# 🔐 Worker-Bee 安全隐私审计

> 审计日期：2026-07-11  
> 审计 commit：`eeca1b0`  
> 审计范围：全仓库逐文件审查（`agent/` `tools/` `network/gateway/` `network/transport/` `beebox/` `scripts/` `cron/`）

---

## 问题分级

| 标记 | 含义 |
|------|------|
| 🔴 | 严重 — 公网暴露 / 凭据泄露 / 零认证 |
| 🟡 | 高 — 可能导致信息泄露或权限绕过 |
| 🟢 | 中 — 加固建议，不直接产生漏洞 |

---

## 🔴 严重问题

### 1. 硬编码公网 IP 地址（多处泄露）

以下文件中直接写入了生产环境的公网 IP：

| 文件 | 行号 | 泄露内容 |
|------|------|---------|
| `network/gateway/run.py` | 21 | `DEFAULT_SWARM_NATS_URL = "nats://<REDACTED_IP>:4222"` |
| `scripts/swarm-node.sh` | 8 | `PM_IP="<REDACTED_IP>"` |
| `scripts/swarm-node.sh` | 24-31 | 全部 8 台机 IP + 角色映射（pm/worker/aristotle/skeleton/world/cardmaster/strategy/centurion） |
| `DEPLOY-CHECKLIST.md` | 9-18 | 完整 8 节点 IP 表 + 角色 |
| `beebox/nats_configs.sh` | 1-8 | 两台 NATS 集群节点 IP |

**影响**：任何人读 GitHub 即可获得完整基础设施拓扑，可直接对所有 IP 进行端口扫描和攻击尝试。

**建议**：
- 所有 IP 改为占位符（如 `X.X.X.X`）或环境变量引用
- `DEPLOY-CHECKLIST.md` 和 `beebox/nats_configs.sh` 加 `.gitignore` 或移到私有仓库
- `network/gateway/run.py` 默认值改 `localhost`，生产值通过环境变量注入

---

### 2. NATS 集群零认证 + 零加密 + 公网监听

**NATS Server 配置现状**（`network/transport/server.conf`、`DEPLOY-CHECKLIST.md:51-59`、`swarm-node.sh:91-99`）：

- 端口 4222（客户端接入）：**无认证，无 TLS**
- 端口 6222（集群通信）：`listen: 0.0.0.0`，**无认证**
- 端口 8222（HTTP 监控）：**暴露**
- `network/transport/server.conf:6` 注释自证："生产环境：加上 authorization 和 TLS / 内网开发：裸跑即可"
- JetStream 持久化数据存储在 `~/.worker-bee/nats-jetstream/`，连上即可读取所有蜂群消息历史

**影响**：公网任意机器 `nc <IP> 4222` 即可接入蜂群消息总线——可发布任意消息、窃听所有 swarm 通信、操控 JetStream 数据。

**建议**：
- NATS 加 `authorization { token: "..." }`，所有客户端传 token
- 集群端口 `listen` 改为内网 IP 或 `127.0.0.1`
- 生产环境加 TLS（`tls { ... }`）
- 监控端口 8222 绑定 `127.0.0.1` 或加认证

---

### 3. 文件服务器默认全开放

`network/transport/file_server.py:18`：
```python
FILE_SERVER_TOKEN = os.environ.get("FILE_SERVER_TOKEN", "")
```
- 未设 token 时默认端口 9999 **完全不设防**
- `file_server.py:51-53` 打印 WARNING 但照常启动
- 即使设了 token，也是 HTTP 明文传输，X-Token 可被中间人截获
- 暴露整个 `~/.worker-bee/mailbox/` 目录

**建议**：
- `FILE_SERVER_TOKEN` 未设时直接拒绝启动（`sys.exit(1)`），不要 OPEN 运行
- 加 HTTPS / TLS 支持

---

### 4. 飞书 Webhook Token 非恒定时间比较（时序攻击向量）

`network/gateway/platforms/feishu.py:125`：
```python
if self.verification_token and header_token != self.verification_token:
```
使用 `!=` 字符串比较而非 `hmac.compare_digest()`。

**影响**：攻击者可以通过测量响应时间逐字节猜测飞书验证 token。

**建议**：
```python
import hmac
if self.verification_token and not hmac.compare_digest(header_token, self.verification_token):
```

---

## 🟡 高优先级

### 5. Gateway 默认监听 0.0.0.0

`network/gateway/config.py:21`：`host: str = "0.0.0.0"` — 除非显式覆盖，Feishu webhook 接收器绑定所有网卡。虽然后续有 token 验证（问题 4 削弱了它），但端口 8080 的 HTTP 服务本身公网可达。

**建议**：默认值改 `127.0.0.1`，显式配置才暴露。

---

### 6. Subagent 工具暴露 API Key 参数给 LLM

`tools/subagent.py:72,234`：`agent_delegate_task()` 接受 `api_key` 作为参数，schema 暴露为 `{"type": "string"}`。

**影响**：如果 agent 的 system prompt 被注入攻击（通过飞书消息或网页内容），LLM 可能被诱导传递或泄露 API key。

**建议**：从 tool schema 中移除 `api_key`/`base_url` 参数，subagent 始终用父 agent 的配置。

---

### 7. 终端输出无敏感信息脱敏

`tools/terminal.py:22`：stdout+stderr 原样拼接返回。如果命令意外输出 `.env` 或 `config.json` 内容，API key 会直接出现在 agent 回复中。

**建议**：对终端输出做简单正则脱敏——匹配 `sk-` / `Bearer ` / `api_key` 等模式打码。

---

### 8. Feishu Token 缓存无并发保护

三处独立的模块级全局 token 缓存，无锁：
- `tools/send_message.py:29` — `_FEISHU_TOKEN_CACHE`
- `network/gateway/platforms/feishu.py:23-25` — `_feishu_token` + `_feishu_token_expires` + `_token_lock`（这个有锁，但前两个没有）
- `tools/lark.py` — 依赖 `lark-cli` 自身的认证

**建议**：统一 Feishu token 缓存到一处，加 `threading.Lock()`。

---

## 🟢 中优先级

### 9. `wb config set` 不设置 `0o600`

`agent/main.py:183` 只在 `wb setup` 时设置 `os.chmod(path, 0o600)`。通过 `wb config set` 或其他方式创建的 `config.json` 不会有此保护。

---

### 10. `no_agent=True` 的 Cron 脚本绕过终端安全过滤器

`cron/scheduler.py:403`：`no_agent=True` 的脚本直接通过 `subprocess.run()` 执行，不经 `tools/terminal.py` 的安全检查。虽然脚本路径有 workspace 门禁，但脚本内容无审查。

---

### 11. 搜索无频率限制

`tools/web.py:77`：Bing 搜索无频率控制，持续高频调用可能触发反爬或 IP 封禁。

---

## ✅ 做得好的安全措施

| 模块 | 措施 | 评价 |
|------|------|------|
| `tools/web.py` | SSRF 防护：阻止 10 类内网 IP 段 + AWS/GCP metadata endpoint + `file://` 协议 | 完整 |
| `agent/safety.py` | 四层安全模型：文件写禁单 → 危险命令封禁 → git checkpoint → 自修改锁 | 完整 |
| `tools/terminal.py` | 危险命令检测优于白名单；`shell=True` 永不启用 | 完整 |
| `tools/file.py` | workspace 边界 + 敏感路径拦截 + 自修改保护 + 写入前快照 | 完整 |
| `agent/main.py` | `wb config` 显示时 API key 自动脱敏（`sk-xx...xxxx`） | 良好 |
| `network/gateway/platforms/feishu.py` | 飞书 webhook 有 token 验证 + challenge handshake | 良好（除问题 4） |
| `cron/scheduler.py` | tick 锁（fcntl）+ 脚本 workspace 门禁 | 良好 |
| `tools/file.py` | 文件快照 / 回滚机制（5 版本轮转） | 良好 |
| `agent/safety.py` | agent 自修改锁（`WORKER_BEE_ALLOW_SELF_MODIFY` 环境变量门控） | 良好 |
| `.gitignore` | `config.json` 和 `.env.*` 已排除 | 良好 |

---

## 修复优先级

```
🔴 立即（阻塞性安全风险）
   1. 全部 IP 从仓库移除 → 用占位符/环境变量
   2. NATS 加认证（至少 token auth）
   3. 文件服务器默认关闭
   4. 飞书 webhook 用 hmac.compare_digest

🟡 短期（2 周内）
   5. Gateway 默认 host 改 127.0.0.1
   6. Subagent schema 移除 api_key 参数
   7. 终端输出加敏感信息脱敏
   8. 统一 Feishu token 缓存加锁

🟢 长期（架构演进）
   9. NATS TLS + mTLS
   10. Gateway HTTPS
   11. config.json 写权限统一加固
```
