# Worker-Bee 蜂群装机检查清单

> 逐台手动执行，不要批量跑。每完成一步打勾。

---

## 节点清单

| 角色 | IP | 当前状态 | 完成时间 |
|------|-----|---------|---------|
| PM | 43.156.129.115 | ☐ | |
| Worker | 43.134.10.180 | ☐ | |
| Aristotle | 43.134.232.158 | ☐ | |
| Skeleton | 43.163.112.179 | ☐ | |
| World | 129.226.202.39 | ☐ | |
| Cardmaster | 43.163.91.125 | ☐ | |
| Strategy | 43.134.68.111 | ☐ | |
| Centurion | 43.160.206.124 | ☐ | |

---

## 阶段 A：PM Bee（邮局机）必须先完成

**连上 PM：ssh ubuntu@43.156.129.115**

### A1 代码同步
```bash
sudo -i
cd ~/worker-bee 2>/dev/null || git clone https://github.com/JuliaHZhu/worker-bee.git ~/worker-bee
cd ~/worker-bee
git stash 2>/dev/null; git pull origin main
git log --oneline -1   # 确认是 c64bb02 或更新
```

### A2 虚拟环境 + wb
```bash
cd ~/worker-bee
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -e "."
wb --version
```

### A3 NATS Server
```bash
# 检查是否在跑
pgrep -x nats-server && echo "RUNNING" || echo "NOT RUNNING"

# 如果没在跑，启动：
mkdir -p ~/.worker-bee/nats-jetstream
cat > ~/.worker-bee/nats-server.conf <<'EOF'
port: 4222
jetstream: {
  store_dir: "/home/ubuntu/.worker-bee/nats-jetstream"
  max_memory_store: 1GB
  max_file_store: 10GB
}
max_payload: 8MB
EOF
nohup nats-server -c ~/.worker-bee/nats-server.conf >> ~/.worker-bee/nats.log 2>&1 &
sleep 2
pgrep -x nats-server
```

### A4 验证 NATS 可对外连通
```bash
nc -zv 43.156.129.115 4222
# 期望输出：Connection succeeded
```

### A5 飞书 CLI 测试（PM 节点）
```bash
wb lark who 2>/dev/null || echo "需配置: wb lark login"
```

---

## 阶段 B：Worker 节点（逐台执行，不要并行）

**以 Worker (43.134.10.180) 为例，其他6台同理。**

**连上 Worker：ssh ubuntu@43.134.10.180**

### B1 代码同步
```bash
sudo -i
cd ~/worker-bee 2>/dev/null || git clone https://github.com/JuliaHZhu/worker-bee.git ~/worker-bee
cd ~/worker-bee
git stash 2>/dev/null; git pull origin main
git log --oneline -1
```

### B2 虚拟环境 + wb
```bash
cd ~/worker-bee
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -e "."
ln -sf ~/worker-bee/.venv/bin/wb /usr/local/bin/wb 2>/dev/null
wb --version
```

### B3 连通性验证
```bash
# NATS 通不通？
nc -zv 43.156.129.115 4222

# SSH 免密到 PM？
ssh -o ConnectTimeout=3 -o BatchMode=yes ubuntu@43.156.129.115 "echo OK" 2>/dev/null || echo "SSH FAIL — 需 ssh-copy-id"
```

### B4 启动 Listener
```bash
mkdir -p ~/.worker-bee/mailbox/inbox

# 杀掉旧 listener（如有）
pkill -f "swarm/listener.py" 2>/dev/null || true

# 启动新 listener
nohup ~/worker-bee/.venv/bin/python ~/worker-bee/swarm/listener.py \
  nats://43.156.129.115:4222 >> ~/.worker-bee/listener.log 2>&1 &

sleep 2
cat ~/.worker-bee/listener.pid 2>/dev/null
```

### B5 验证 Listener
```bash
# 看日志
tail -n 5 ~/.worker-bee/listener.log

# 看进程
pgrep -af "listener.py"

# 看 mailbox 是否收到消息
ls ~/.worker-bee/mailbox/inbox/ | wc -l
```

### B6 飞书 CLI（Worker 节点）
```bash
wb lark who 2>/dev/null || echo "需配置: wb lark login"
```

---

## 阶段 C：端到端验证（PM 上执行）

### C1 NATS pub/sub 测试
```bash
sudo -i
cd ~/worker-bee
source .venv/bin/activate

python3 <<'PY'
import asyncio, nats

async def test():
    nc = await nats.connect("nats://43.156.129.115:4222")
    inbox = []
    async def cb(msg):
        inbox.append(msg.data.decode())
        await msg.ack()
    sub = await nc.subscribe("deploy.test", cb=cb)
    await nc.publish("deploy.test", b"HELLO")
    await asyncio.sleep(1)
    print("RECEIVED:", inbox)
    await sub.unsubscribe()
    await nc.close()

asyncio.run(test())
PY
```
**期望输出包含 `RECEIVED: ['HELLO']`**

### C2 跨节点消息测试（PM → Worker）
```bash
# 在 PM 上发消息
python3 -c "import asyncio, nats; asyncio.run(nats.connect('nats://43.156.129.115:4222').publish('worker.tasks', b'test'))"

# 然后在 Worker 上检查 mailbox
ssh ubuntu@43.134.10.180 'ls ~/.worker-bee/mailbox/inbox/ | wc -l'
```

### C3 飞书端到端
```bash
# 从任意节点发送测试消息
wb lark send --target ou_1244443176cd057b1a00a5b16d860873 \
  --message "🐝 蜂群 $(hostname) $(date +%H:%M) 上线"
```

---

## 阶段 D：SSH 免密修复（如 B3 失败）

**在 SSH 失败的节点上执行：**

```bash
# 生成密钥（如果没有）
[[ -f ~/.ssh/id_rsa ]] || ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa

# 分发到 PM
ssh-copy-id -i ~/.ssh/id_rsa.pub ubuntu@43.156.129.115

# 验证
ssh -o BatchMode=yes ubuntu@43.156.129.115 "echo SSH_OK"
```

---

## 完成标准

| # | 检查项 | 验证命令 |
|---|-------|---------|
| 1 | NATS 在跑且可达 | `nc -zv 43.156.129.115 4222` |
| 2 | 8 节点代码同步 | `git log --oneline -1` 一致 |
| 3 | SSH 免密 | `ssh ubuntu@PM "echo OK"` |
| 4 | wb / lark CLI 可用 | `wb --version && wb lark who` |
| 5 | Listener 在跑 | `pgrep -f listener.py` |
| 6 | NATS 端到端 | pub/sub 测试成功 |
| 7 | 飞书通知 | 收到测试消息 |

---

## 常见问题速查

**Q: git pull 冲突**
```bash
git stash
git pull origin main
```

**Q: pip install 失败（权限）**
```bash
pip install -e "." --break-system-packages
```

**Q: nats-server 找不到**
```bash
# 下载
wget https://github.com/nats-io/nats-server/releases/download/v2.10.24/nats-server-v2.10.24-linux-amd64.tar.gz
tar -xzf nats-server-v2.10.24-linux-amd64.tar.gz
sudo mv nats-server-v2.10.24-linux-amd64/nats-server /usr/local/bin/
```

**Q: listener 启动后立刻退出**
```bash
# 看日志
tail ~/.worker-bee/listener.log
# 常见原因：nats-py 没装 → pip install nats-py
```

**Q: wb 命令找不到**
```bash
export PATH="$HOME/worker-bee/.venv/bin:$PATH"
# 或永久添加：echo 'export PATH="$HOME/worker-bee/.venv/bin:$PATH"' >> ~/.bashrc
```
