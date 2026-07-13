#!/bin/bash
# 批量升级所有 swarm 节点的 worker-bee 到 GitHub 最新版
# 前提：每台机 ~/worker-bee 是 git clone（不是 pip install）
set -euo pipefail

source "$(dirname "$0")/common.sh"
REPO_URL="https://github.com/JuliaHZhu/worker-bee.git"

# 从 Python 配置加载节点列表
NODES_STR=$(python3 -c "
import sys; sys.path.insert(0, '.')
from beebox.nodes import all_nodes
for role, ip in all_nodes():
    print(f'{ip}:{role}')
" 2>/dev/null || echo "")

if [[ -z "$NODES_STR" ]]; then
    echo "⚠️ 未能加载节点配置，请确保 ~/.worker-bee/nodes.yaml 存在或设置环境变量"
    exit 1
fi

mapfile -t NODES <<< "$NODES_STR"

echo "=========================================="
echo "批量升级 worker-bee → GitHub 最新版"
echo "=========================================="

PASS=0
FAIL=0

for entry in "${NODES[@]}"; do
    ip="${entry%%:*}"
    role="${entry##*:}"
    echo ""
    echo ">>> [$role] $ip"

    result=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no ubuntu@"$ip" bash -s 2>&1 <<'REMOTECMD'
set -e
cd ~/worker-bee
git pull --ff-only 2>&1 || { echo "  (非 ff，强制同步)"; git fetch origin && git reset --hard origin/main 2>&1; }
.venv/bin/pip install --upgrade -e . -q 2>&1
VER=$(.venv/bin/python -c "from agent.main import VERSION; print(VERSION)" 2>/dev/null || echo "?")
COMMIT=$(git log --oneline -1)
echo "  ✅ v$VER  @ $COMMIT"
REMOTECMD
)

    if [ $? -eq 0 ]; then
        echo "$result"
        ((PASS++))
    else
        echo "  ❌ $result"
        ((FAIL++))
    fi
done

echo ""
echo "=========================================="
echo "升级完成: $PASS 成功 / $FAIL 失败"
echo "=========================================="
