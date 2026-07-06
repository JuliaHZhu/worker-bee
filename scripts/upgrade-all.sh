#!/bin/bash
# 批量升级所有 swarm 节点的 worker-bee 到 GitHub 最新版
# 前提：每台机 ~/worker-bee 是 git clone（不是 pip install）
PM_IP="43.156.129.115"
NODES=(
"43.156.129.115:pm"
"43.134.10.180:worker"
"43.134.232.158:aristotle"
"43.163.112.179:skeleton"
"129.226.202.39:world"
"43.163.91.125:cardmaster"
"43.134.68.111:strategy"
"43.160.206.124:centurion"
)

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
