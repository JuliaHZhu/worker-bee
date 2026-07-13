#!/bin/bash
# 两台机的 NATS 集群配置
# 配置来源：环境变量 BEE_01_IP / BEE_02_IP（默认 127.0.0.1）
# 推荐：使用 beebox/setup_nats.py 生成完整集群配置（支持 8 台机）

BEE_01_IP="${BEE_01_IP:-127.0.0.1}"
BEE_02_IP="${BEE_02_IP:-127.0.0.1}"

# NATS 认证：优先从 config.yaml 读取，回退到环境变量
_read_yaml_auth() {
  python3 -c "
import yaml, sys
from pathlib import Path
for p in [Path('config.yaml'), Path.home() / '.worker-bee' / 'config.yaml']:
    if p.exists():
        try:
            cfg = yaml.safe_load(p.read_text()) or {}
            auth = cfg.get('nats_auth', {})
            user = auth.get('user', '')
            password = auth.get('password', '')
            if user:
                print(user)
                print(password)
                sys.exit(0)
        except Exception:
            pass
sys.exit(1)
" 2>/dev/null
}

if [[ -z "${NATS_USER:-}" ]]; then
  mapfile -t _auth < <(_read_yaml_auth)
  if [[ ${#_auth[@]} -ge 2 ]]; then
    NATS_USER="${_auth[0]}"
    NATS_PASSWORD="${_auth[1]}"
  fi
fi

NATS_USER="${NATS_USER:-}"
NATS_PASSWORD="${NATS_PASSWORD:-}"

if [[ -n "$NATS_USER" && -n "$NATS_PASSWORD" ]]; then
  AUTH_BLOCK="authorization {\\n  user: $NATS_USER\\n  password: $NATS_PASSWORD\\n  timeout: 2\\n}"
else
  AUTH_BLOCK="# authorization 未配置（config.yaml 的 nats_auth 或环境变量 NATS_USER / NATS_PASSWORD 未设置）"
fi

echo "生成 NATS 配置 — bee-01: $BEE_01_IP, bee-02: $BEE_02_IP"

_generate_nats_conf() {
  local name="$1"
  local peer_ip="$2"
  cat << EOF
server_name: "$name"
port: 4222
http_port: 8222
max_payload: 1MB
max_pending: 10MB

$AUTH_BLOCK

cluster {
  name: worker-bee-cluster
  listen: 0.0.0.0:6222
  routes = [
    nats://\${peer_ip}:6222
  ]
}

jetstream {
  store_dir: "~/.worker-bee/nats-jetstream"
  max_memory_store: 256MB
  max_file_store: 2GB
}

debug: false
trace: false
logtime: true
EOF
}

_generate_nats_conf "bee-01" "$BEE_02_IP" > /tmp/nats-bee01.conf
_generate_nats_conf "bee-02" "$BEE_01_IP" > /tmp/nats-bee02.conf

echo "✅ 配置已生成到 /tmp/nats-bee01.conf 和 /tmp/nats-bee02.conf"
echo ""
echo "机 1 ($BEE_01_IP) 执行:"
echo "  scp /tmp/nats-bee01.conf ubuntu@$BEE_01_IP:~/.worker-bee/nats-server.conf"
echo ""
echo "机 2 ($BEE_02_IP) 执行:"
echo "  scp /tmp/nats-bee02.conf ubuntu@$BEE_02_IP:~/.worker-bee/nats-server.conf"
