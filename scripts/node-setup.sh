#!/bin/bash
# Worker-Bee 单节点装机脚本
# 用法: 保存为 node-setup.sh，然后 bash node-setup.sh
set -e

PM_IP="43.156.129.115"
ROLE="${1:-}"
REPO="https://github.com/JuliaHZhu/worker-bee.git"

# 自动识别角色
[[ -z "$ROLE" ]] && ROLE=$(hostname -I | awk '{print $1}' | sed \
  -e 's/43.156.129.115/pm/' \
  -e 's/43.134.10.180/worker/' \
  -e 's/43.134.232.158/aristotle/' \
  -e 's/43.163.112.179/skeleton/' \
  -e 's/129.226.202.39/world/' \
  -e 's/43.163.91.125/cardmaster/' \
  -e 's/43.134.68.111/strategy/' \
  -e 's/43.160.206.124/centurion/')

echo "=== 角色: $ROLE ==="

# 1. 代码
cd ~
if [[ -d worker-bee/.git ]]; then
  cd worker-bee && git pull origin main && echo "[OK] 代码已更新"
else
  git clone "$REPO" worker-bee && cd worker-bee && echo "[OK] 代码已克隆"
fi

# 2. 虚拟环境
[[ -d .venv ]] || python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[swarm]" 2>/dev/null || pip install -e ".[swarm]" --break-system-packages 2>/dev/null
echo "[OK] 依赖就绪"

# 3. wb 命令
ln -sf ~/worker-bee/.venv/bin/wb /usr/local/bin/wb 2>/dev/null || true
echo "[OK] wb: $(wb --version 2>/dev/null || echo 'installed')"

# 4. PM → NATS, Worker → Listener
if [[ "$ROLE" == "pm" ]]; then
  if ! pgrep -x nats-server >/dev/null; then
    mkdir -p ~/.worker-bee/nats-jetstream
    [[ -f ~/.worker-bee/nats-server.conf ]] || printf 'port: 4222\njetstream: { store_dir: "%s", max_memory_store: 1GB, max_file_store: 10GB }\nmax_payload: 8MB\n' "$HOME/.worker-bee/nats-jetstream" > ~/.worker-bee/nats-server.conf
    nohup nats-server -c ~/.worker-bee/nats-server.conf >> ~/.worker-bee/nats.log 2>&1 &
    sleep 2
  fi
  echo "[OK] NATS: $(pgrep -x nats-server >/dev/null && echo RUNNING || echo FAILED)"
else
  mkdir -p ~/.worker-bee/mailbox/inbox
  if ! [[ -f ~/.worker-bee/listener.pid ]] || ! kill -0 "$(cat ~/.worker-bee/listener.pid)" 2>/dev/null; then
    nohup ~/worker-bee/.venv/bin/python ~/worker-bee/swarm/listener.py "nats://${PM_IP}:4222" >> ~/.worker-bee/listener.log 2>&1 &
    sleep 2
  fi
  echo "[OK] NATS→PM: $(nc -zv "$PM_IP" 4222 >/dev/null 2>&1 && echo OK || echo FAIL)"
  echo "[OK] Listener: $( [[ -f ~/.worker-bee/listener.pid ]] && kill -0 "$(cat ~/.worker-bee/listener.pid)" 2>/dev/null && echo RUNNING || echo NOT_RUNNING)"
fi

# 5. SSH 抽查
echo "[OK] SSH→PM: $(ssh -o ConnectTimeout=3 -o BatchMode=yes "ubuntu@${PM_IP}" "echo OK" 2>/dev/null || echo FAIL)"

# 6. 汇总
echo ""
echo "=== $ROLE 完成 ==="
echo "代码: $(git log --oneline -1 | cut -d' ' -f1)"
echo "wb:   $(which wb 2>/dev/null || echo '未找到')"
echo "NATS: $(nc -zv "$PM_IP" 4222 >/dev/null 2>&1 && echo 连通 || echo 不通)"
