#!/bin/bash
# =============================================================================
# Worker-Bee 单节点自检/自修脚本
# 在每台机器上执行：bash swarm-node.sh
# =============================================================================
set -euo pipefail

PM_IP="43.156.129.115"
ROLE="${1:-}"  # 手动传入 role，如 pm, worker, centurion 等
REPO_URL="https://github.com/JuliaHZhu/worker-bee.git"

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; N='\033[0m'
ok()  { echo -e "${G}[OK]${N} $*"; }
warn(){ echo -e "${Y}[WARN]${N} $*"; }
err() { echo -e "${R}[ERR]${N} $*"; }
info(){ echo -e "${C}[INFO]${N} $*"; }
sep() { echo -e "${C}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"; }

# ── 自动识别角色 ────────────────────────────────────────────────────────────
auto_detect_role() {
  local ip
  ip=$(hostname -I | awk '{print $1}')
  case "$ip" in
    43.156.129.115)  echo "pm" ;;
    43.134.10.180)   echo "worker" ;;
    43.134.232.158)  echo "aristotle" ;;
    43.163.112.179)  echo "skeleton" ;;
    129.226.202.39)  echo "world" ;;
    43.163.91.125)   echo "cardmaster" ;;
    43.134.68.111)   echo "strategy" ;;
    43.160.206.124)  echo "centurion" ;;
    *) echo "unknown" ;;
  esac
}

[[ -z "$ROLE" ]] && ROLE=$(auto_detect_role)
info "当前角色: $ROLE"

# ── 1. 代码检查 ─────────────────────────────────────────────────────────────
sep; info "① 代码状态"
if [[ -d ~/worker-bee/.git ]]; then
  cd ~/worker-bee
  git fetch origin main --depth=1 2>/dev/null || true
  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse origin/main 2>/dev/null || echo "$LOCAL")
  if [[ "$LOCAL" == "$REMOTE" ]]; then
    ok "代码已是最新 ($LOCAL)"
  else
    warn "代码落后，拉取中..."
    git pull origin main
    ok "代码已更新到 $REMOTE"
  fi
else
  warn "无代码，克隆中..."
  git clone "$REPO_URL" ~/worker-bee
  ok "克隆完成"
fi

# ── 2. 虚拟环境 ─────────────────────────────────────────────────────────────
sep; info "② 虚拟环境"
cd ~/worker-bee
if [[ ! -d .venv ]]; then
  warn "创建虚拟环境..."
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -e . >/dev/null 2>&1 || pip install -e . --break-system-packages >/dev/null 2>&1
ok "依赖已安装"

# ── 3. wb CLI ───────────────────────────────────────────────────────────────
sep; info "③ wb CLI"
if wb --version >/dev/null 2>&1; then
  ok "wb 可用: $(wb --version 2>/dev/null || echo 'installed')"
else
  warn "wb 未在 PATH，尝试软链接..."
  ln -sf ~/worker-bee/.venv/bin/wb /usr/local/bin/wb 2>/dev/null || true
  export PATH="$HOME/worker-bee/.venv/bin:$PATH"
  wb --version >/dev/null 2>&1 && ok "wb 可用" || warn "wb 仍不可用，请手动检查"
fi

# ── 4. NATS / Listener ──────────────────────────────────────────────────────
sep; info "④ NATS / Listener"
if [[ "$ROLE" == "pm" ]]; then
  # PM: 启动 NATS Server
  if command -v nats-server >/dev/null 2>&1; then
    if pgrep -x nats-server >/dev/null 2>&1; then
      ok "NATS Server 已在运行"
    else
      warn "启动 NATS Server..."
      mkdir -p ~/.worker-bee/nats-jetstream
      [[ -f ~/.worker-bee/nats-server.conf ]] || cat > ~/.worker-bee/nats-server.conf <<EOF
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
      pgrep -x nats-server >/dev/null 2>&1 && ok "NATS 启动成功" || err "NATS 启动失败"
    fi
  else
    err "nats-server 未安装！请手动下载到 /usr/local/bin"
  fi
else
  # Worker: 检查 NATS 连通 + Listener
  if python3 -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('$PM_IP', 4222)); s.close()" >/dev/null 2>&1; then
    ok "NATS  broker 可连通"
  else
    err "NATS broker ($PM_IP:4222) 不可达！"
  fi

  if [[ -f ~/.worker-bee/listener.pid ]] && kill -0 "$(cat ~/.worker-bee/listener.pid)" 2>/dev/null; then
    ok "Listener 已在运行 (PID $(cat ~/.worker-bee/listener.pid))"
  else
    warn "启动 Listener..."
    mkdir -p ~/.worker-bee/mailbox/inbox ~/.worker-bee/mailbox/outbox
    nohup ~/worker-bee/.venv/bin/python ~/worker-bee/swarm/listener.py "nats://${PM_IP}:4222" >> ~/.worker-bee/listener.log 2>&1 &
    sleep 2
    [[ -f ~/.worker-bee/listener.pid ]] && kill -0 "$(cat ~/.worker-bee/listener.pid)" 2>/dev/null && ok "Listener 启动成功" || err "Listener 启动失败"
  fi
fi

# ── 5. SSH 免密抽查 ─────────────────────────────────────────────────────────
sep; info "⑤ SSH 免密"
if ssh -o ConnectTimeout=5 -o BatchMode=yes "ubuntu@${PM_IP}" "echo SSH_OK" >/dev/null 2>&1; then
  ok "→ PM 免密通过"
else
  warn "→ PM SSH 免密失败（不影响本地运行，但影响 git push/pull 协作）"
fi

# ── 6. 飞书 CLI ─────────────────────────────────────────────────────────────
sep; info "⑥ 飞书 CLI"
if command -v lark-cli >/dev/null 2>&1; then
  ok "lark-cli 已安装"
  # 轻量验证 auth（不实际发消息）
  if lark-cli contact +search-user --query test >/dev/null 2>&1; then
    ok "lark-cli auth 正常"
  else
    warn "lark-cli 未登录，运行: lark-cli auth login"
  fi
else
  warn "lark-cli 未安装（pip install lark-cli）"
fi

# ── 7. 汇总 ─────────────────────────────────────────────────────────────────
sep
ok "$ROLE 节点自检完成"
echo ""
echo "关键路径:"
echo "  代码:   ~/worker-bee ($(cd ~/worker-bee && git log --oneline -1 | cut -d' ' -f1))"
echo "  wb:     $(which wb 2>/dev/null || echo '未找到')"
if [[ "$ROLE" == "pm" ]]; then
  echo "  NATS:   $(pgrep -x nats-server >/dev/null 2>&1 && echo '运行中' || echo '未运行')"
else
  echo "  NATS:   $(python3 -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('$PM_IP', 4222)); s.close()" >/dev/null 2>&1 && echo '连通' || echo '不可达')"
  echo "  Listener: $( [[ -f ~/.worker-bee/listener.pid ]] && kill -0 "$(cat ~/.worker-bee/listener.pid)" 2>/dev/null && echo "运行中(PID $(cat ~/.worker-bee/listener.pid))" || echo '未运行')"
fi
echo "  SSH→PM: $(ssh -o ConnectTimeout=3 -o BatchMode=yes "ubuntu@${PM_IP}" "echo OK" 2>/dev/null || echo '失败')"
