#!/bin/bash
# 两台机的 NATS 集群配置
# 后续加机：在 routes 里加 IP，改 server_name，三台都重启

# ═══════════════════════════════════════════
# 机 1 (43.134.10.180)   → bee-01
# 机 2 (43.134.232.158)  → bee-02
# ═══════════════════════════════════════════

# ========== 机 1 ==========
cat > /tmp/nats-bee01.conf << 'EOF'
server_name: "bee-01"
port: 4222
http_port: 8222
max_payload: 1MB
max_pending: 10MB

cluster {
  name: worker-bee-cluster
  listen: 0.0.0.0:6222
  routes = [
    nats://43.134.232.158:6222
  ]
}

jetstream {
  store_dir: "/home/ubuntu/.worker-bee/nats-jetstream"
  max_memory_store: 256MB
  max_file_store: 2GB
}

debug: false
trace: false
logtime: true
EOF

# ========== 机 2 ==========
cat > /tmp/nats-bee02.conf << 'EOF'
server_name: "bee-02"
port: 4222
http_port: 8222
max_payload: 1MB
max_pending: 10MB

cluster {
  name: worker-bee-cluster
  listen: 0.0.0.0:6222
  routes = [
    nats://43.134.10.180:6222
  ]
}

jetstream {
  store_dir: "/home/ubuntu/.worker-bee/nats-jetstream"
  max_memory_store: 256MB
  max_file_store: 2GB
}

debug: false
trace: false
logtime: true
EOF

echo "✅ 配置已生成到 /tmp/nats-bee01.conf 和 /tmp/nats-bee02.conf"
echo ""
echo "机 1 (43.134.10.180) 执行:"
echo "  scp /tmp/nats-bee01.conf ubuntu@43.134.10.180:~/.worker-bee/nats-server.conf"
echo ""
echo "机 2 (43.134.232.158) 执行:"
echo "  scp /tmp/nats-bee02.conf ubuntu@43.134.232.158:~/.worker-bee/nats-server.conf"
