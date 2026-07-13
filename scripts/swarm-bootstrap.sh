#!/bin/bash
# =============================================================================
# Worker-Bee 8-Node Swarm Bootstrap
# 一键检查 + 修复 + 验证，在 PM Bee（或跳板机）上执行
# =============================================================================
# 用法：
#   bash swarm-bootstrap.sh check    # 只检查，不改动
#   bash swarm-bootstrap.sh deploy   # 全量部署/修复
#   bash swarm-bootstrap.sh nats     # 只启动/修复 NATS
# =============================================================================
set -euo pipefail

source "$(dirname "$0")/common.sh"
NATS_PORT=4222
NATS_CONF="${NATS_CONF:-$HOME/.worker-bee/nats-server.conf}"
STORE_DIR="${STORE_DIR:-$HOME/.worker-bee/nats-jetstream}"
REPO_URL="https://github.com/JuliaHZhu/worker-bee.git"
USER="${USER:-ubuntu}"
VENV_PYTHON="${VENV_PYTHON:-$HOME/worker-bee/.venv/bin/python}"

# 节点清单（role:ip）
# 动态加载节点列表（环境变量 / ~/.worker-bee/nodes.yaml）
declare -A NODES
NODES_STR=$(python3 -c "import sys; sys.path.insert(0, '.'); from beebox.nodes import all_nodes; [print(f'{r}:{ip}') for r, ip in all_nodes()]" 2>/dev/null || echo '')
if [[ -z "$NODES_STR" ]]; then
  echo '⚠️ 未能加载节点配置'
  exit 1
fi
while IFS=':' read -r role ip; do
  NODES[$role]="$ip"
done <<< "$NODES_STR"

# ── 颜色 ────────────────────────────────────────────────────────────────────
G='\033[0;32m'  # green
Y='\033[1;33m'  # yellow
R='\033[0;31m'  # red
C='\033[0;36m'  # cyan
N='\033[0m'     # reset

ok()  { echo -e "${G}[OK]${N}  $*"; }
warn(){ echo -e "${Y}[WARN]${N} $*"; }
err() { echo -e "${R}[ERR]${N}  $*"; }
info(){ echo -e "${C}[INFO]${N} $*"; }
sep() { echo -e "${C}────────────────────────────────────────${N}"; }

# ── 工具函数 ────────────────────────────────────────────────────────────────
remote() {
  local ip="$1"; shift
  ssh -o ConnectTimeout=8 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
      "${USER}@${ip}" "$@"
}

nats_installed() {
  command -v nats-server >/dev/null 2>&1
}

nats_running() {
  pgrep -x nats-server >/dev/null 2>&1
}

# ── Phase 1: NATS Server（仅 PM）───────────────────────────────────────────
phase1_nats() {
  sep; info "Phase 1 — NATS Server on PM"

  # 1.1 检查 nats-server 二进制
  if nats_installed; then
    ok "nats-server: $(nats-server --version 2>/dev/null || echo 'installed')"
  else
    warn "nats-server 未安装，尝试下载..."
    # 优先用清华镜像
    local dl_url="https://mirrors.tuna.tsinghua.edu.cn/github-release/nats-io/nats-server/LatestRelease/nats-server-v2.10.24-linux-amd64.tar.gz"
    if ! curl -sfIL "$dl_url" >/dev/null 2>&1; then
      dl_url="https://github.com/nats-io/nats-server/releases/latest/download/nats-server-v2.10.24-linux-amd64.tar.gz"
    fi
    local tmpdir=$(mktemp -d)
    curl -sL "$dl_url" | tar -xzf - -C "$tmpdir" --strip-components=1
    sudo mv "$tmpdir/nats-server" /usr/local/bin/
    sudo chmod +x /usr/local/bin/nats-server
    rm -rf "$tmpdir"
    ok "nats-server 安装完成"
  fi

  # 1.2 配置文件
  mkdir -p "$(dirname "$NATS_CONF")" "$STORE_DIR"
  if [[ ! -f "$NATS_CONF" ]]; then
    warn "生成默认 NATS 配置: $NATS_CONF"
    cat > "$NATS_CONF" <<EOF
port: 4222
jetstream: {
  store_dir: "$STORE_DIR"
  max_memory_store: 1GB
  max_file_store: 10GB
}
max_payload: 8MB
EOF
  fi

  # 1.3 启动/重启
  if nats_running; then
    local pid=$(pgrep -x nats-server)
    warn "NATS 已在运行 (PID $pid)，尝试热重载配置..."
    kill -HUP "$pid" 2>/dev/null || true
    sleep 1
  else
    warn "启动 NATS Server..."
    nohup nats-server -c "$NATS_CONF" >> "$HOME/.worker-bee/nats.log" 2>&1 &
    sleep 2
  fi

  # 1.4 验证（用 python socket 替代 nc，避免 nc 未安装）
  if python3 -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('$PM_IP', $NATS_PORT)); s.close()" 2>/dev/null; then
    ok "NATS 监听 ${PM_IP}:${NATS_PORT} ✅"
  else
    err "NATS 端口未通，查看日志:"
    tail -n 20 "$HOME/.worker-bee/nats.log" 2>/dev/null || true
    return 1
  fi
}

# ── Phase 2: 代码同步（全部节点）─────────────────────────────────────────────
phase2_sync() {
  sep; info "Phase 2 — 同步代码到最新 main"
  local failed=()

  for role in "${!NODES[@]}"; do
    local ip="${NODES[$role]}"
    printf "  %-10s %-18s ... " "$role" "$ip"

    if ! remote "$ip" "test -d ~/worker-bee/.git" >/dev/null 2>&1; then
      echo -e "${R}MISSING${N}"
      warn "$role 上无 worker-bee，准备克隆..."
      if remote "$ip" "git clone '$REPO_URL' ~/worker-bee" >/dev/null 2>&1; then
        ok "$role 克隆完成"
      else
        err "$role 克隆失败"
        failed+=("$role")
        continue
      fi
    fi

    # pull 最新
    local out
    out=$(remote "$ip" "cd ~/worker-bee && git pull origin main 2>&1") || true
    if echo "$out" | grep -qE "Already up to date|Fast-forward"; then
      echo -e "${G}SYNCED${N}"
    else
      echo -e "${Y}CHECK${N}"
      warn "$role: $out"
    fi

    # 安装/更新依赖
    remote "$ip" "cd ~/worker-bee && (pip install -e . >/dev/null 2>&1 || pip install -e . --break-system-packages >/dev/null 2>&1)" || true
  done

  if ((${#failed[@]})); then
    err "同步失败节点: ${failed[*]}"
    return 1
  fi
  ok "全部节点代码同步完成"
}

# ── Phase 3: SSH 免密矩阵验证 ───────────────────────────────────────────────
phase3_ssh() {
  sep; info "Phase 3 — 8x8 SSH 免密矩阵抽查"
  local broken=0

  # 抽查：每个节点 → PM
  for role in "${!NODES[@]}"; do
    local ip="${NODES[$role]}"
    if remote "$ip" "ssh -o ConnectTimeout=5 -o BatchMode=yes ${USER}@${PM_IP} echo SSH_OK" >/dev/null 2>&1; then
      ok "$role → PM 免通"
    else
      warn "$role → PM SSH 失败"
      ((broken++))
    fi
  done

  # 关键路径：PM → Worker（抽查一条）
  if remote "$PM_IP" "ssh -o ConnectTimeout=5 -o BatchMode=yes ${USER}@${NODES[worker]} echo SSH_OK" >/dev/null 2>&1; then
    ok "PM → Worker 免通"
  else
    warn "PM → Worker SSH 失败（Centurion调度Worker时需要）"
    ((broken++))
  fi

  if ((broken)); then
    warn "有 $broken 条 SSH 路径不通，建议运行 ssh-copy-id 修复"
  else
    ok "SSH 矩阵抽查通过"
  fi
}

# ── Phase 4: Listener 启动（非PM节点）────────────────────────────────────────
phase4_listeners() {
  sep; info "Phase 4 — 启动 swarm listener（非PM节点）"
  local nats_url="nats://${PM_IP}:${NATS_PORT}"

  for role in "${!NODES[@]}"; do
    [[ "$role" == "pm" ]] && continue
    local ip="${NODES[$role]}"

    # 检查是否已在运行
    if remote "$ip" "test -f ~/.worker-bee/listener.pid && kill -0 \$(cat ~/.worker-bee/listener.pid) 2>/dev/null"; then
      ok "$role listener 已在运行"
      continue
    fi

    warn "$role listener 未运行，启动中..."
    local cmd="cd ~/worker-bee && nohup $VENV_PYTHON swarm/listener.py '$nats_url' >> ~/.worker-bee/listener.log 2>&1 &"
    if remote "$ip" "$cmd"; then
      sleep 1
      if remote "$ip" "test -f ~/.worker-bee/listener.pid && kill -0 \$(cat ~/.worker-bee/listener.pid) 2>/dev/null"; then
        ok "$role listener 启动成功"
      else
        err "$role listener 启动失败，查看日志:"
        remote "$ip" "tail -n 10 ~/.worker-bee/listener.log" 2>/dev/null || true
      fi
    fi
  done
}

# ── Phase 5: 端到端验证 ─────────────────────────────────────────────────────
phase5_verify() {
  sep; info "Phase 5 — 端到端验证"
  local nats_url="nats://${PM_IP}:${NATS_PORT}"

  # 5.1 安装 nats-py CLI（如有需要）
  if ! python3 -c "import nats" 2>/dev/null; then
    pip install nats-py >/dev/null 2>&1 || true
  fi

  # 5.2 用一个小脚本做 pub/sub 验证
  local verify_script='
import asyncio, json, sys, uuid
import nats

async def main():
    nc = await nats.connect("'"$nats_url"'")
    result = []
    async def handler(msg):
        result.append(msg.data.decode())
        await msg.ack()
    sub = await nc.subscribe("test.deploy.verify", cb=handler)
    await nc.publish("test.deploy.verify", b"PING")
    await asyncio.sleep(1)
    await sub.unsubscribe()
    await nc.close()
    print("PONG" if result else "TIMEOUT")
asyncio.run(main())
'

  # 在 Worker 上发布，PM 上订阅（交叉验证）
  info "测试 PM → Worker NATS 消息..."
  local out
  out=$(remote "${NODES[worker]}" "python3 -c '$verify_script'" 2>&1) || true
  if [[ "$out" == *"PONG"* ]]; then
    ok "NATS 端到端消息验证通过 ✅"
  else
    warn "NATS 端到端验证异常: $out"
  fi

  # 5.3 检查 mailbox 是否有文件产生
  for role in worker aristotle skeleton world cardmaster strategy centurion; do
    local ip="${NODES[$role]}"
    local count
    count=$(remote "$ip" "ls ~/.worker-bee/mailbox/inbox/ 2>/dev/null | wc -l" || echo 0)
    info "$role mailbox 消息数: $count"
  done
}

# ── Phase 6: 飞书通知测试 ───────────────────────────────────────────────────
phase6_lark() {
  sep; info "Phase 6 — 飞书通知链路"
  info "从 PM 节点尝试发送测试消息..."
  # 优先用环境变量 $LARK_NOTIFY_TARGET 指定接收人 open_id，否则跳过
  local target="${LARK_NOTIFY_TARGET:-}"
  if [[ -z "$target" ]]; then
    warn "未设置 LARK_NOTIFY_TARGET（export LARK_NOTIFY_TARGET=ou_xxx），跳过飞书通知测试"
    return 0
  fi
  if remote "$PM_IP" "command -v lark-cli >/dev/null 2>&1" >/dev/null 2>&1; then
    remote "$PM_IP" "lark-cli im +messages-send --user-id '$target' --text '🐝 蜂群部署测试 $(date +%H:%M)'" 2>&1 || warn "飞书消息发送失败，请检查 lark-cli auth"
  else
    warn "PM 上未安装 lark-cli，跳过飞书通知（安装: pip install lark-cli && lark-cli auth login）"
  fi
}

# ── 主控 ────────────────────────────────────────────────────────────────────
main() {
  local cmd="${1:-check}"
  info "Worker-Bee Swarm Bootstrap"
  info "模式: $cmd"

  case "$cmd" in
    check)
      phase1_nats
      phase2_sync
      phase3_ssh
      phase4_listeners
      phase5_verify
      sep; ok "检查完成，上方 [WARN] 项需要手动修复"
      ;;
    deploy)
      phase1_nats
      phase2_sync
      phase3_ssh
      phase4_listeners
      phase5_verify
      phase6_lark
      sep; ok "部署流程执行完毕"
      ;;
    nats)
      phase1_nats
      ;;
    *)
      echo "用法: $0 {check|deploy|nats}"
      exit 1
      ;;
  esac
}

main "$@"
