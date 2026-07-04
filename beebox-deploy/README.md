# BeeBox Deploy — 分体式 Agent 批量部署工具

用于在多台云服务器上批量部署、更新和管理 JuliaHZhu 的 **分体式 Bee 生态**（worker-bee / commander-bee / world-bee / writer-bee / hermes-lite / openclaw-lite / newspaper 等）。

## 核心功能

| 脚本 | 功能 |
|------|------|
| `scripts/deploy.py` | 批量克隆仓库、安装依赖、配置 NATS 集群 |
| `scripts/update.py` | 批量 `git pull`、重装依赖、记录更新日志 |
| `scripts/collect_logs.py` | 收集各节点的 git 更新日志 + 运行日志 + NATS 日志 |
| `scripts/sync_skills.py` | 从独立 skills 仓库按需同步技能到各节点 |

## 快速开始

### 1. 准备服务器清单

复制示例清单并填入你的实际服务器信息：

```bash
cp inventory.yaml inventory.private.yaml
```

编辑 `inventory.private.yaml`：
- 替换 `host` 为你的云服务器 IP
- 按需分配 `roles`（如 `[worker, hermes]`）
- 填入 API Key 等环境变量
- 标记 `nats_server: true` 的节点会启动 NATS 服务

> `inventory.private.yaml` 已加入 `.gitignore`，不会被提交到 Git。

### 2. 配置 Bee 角色映射（通常无需修改）

`config/bees.yaml` 定义了每个角色对应的 GitHub 仓库、默认 skills 等。如需添加新 bee，在此文件中注册。

### 3. 一键部署

```bash
cd beebox-deploy

# 首次部署（所有节点）
python scripts/deploy.py --inventory inventory.private.yaml

# 仅查看将要执行的命令（不实际执行）
python scripts/deploy.py --inventory inventory.private.yaml --dry-run
```

部署后，各节点的代码位于 `~/.beebox/apps/{role}/`，虚拟环境位于 `~/.beebox/venvs/{role}/`。

### 4. 配置后台持久化（systemd）

`deploy.py` 会在远程生成 systemd 服务文件到 `/tmp/bee-{role}.service`。如需后台运行，请在各节点执行：

```bash
sudo mv /tmp/bee-{role}.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bee-{role}
```

> 未来版本将支持自动 systemd 配置（需 sudo 权限）。

### 5. 批量更新

```bash
# 更新所有节点
python scripts/update.py --inventory inventory.private.yaml

# 仅更新 worker 角色
python scripts/update.py --inventory inventory.private.yaml --role worker
```

更新日志会自动保存到 `logs/updates/update-{timestamp}.json`。

### 6. 同步 Skills

```bash
python scripts/sync_skills.py --inventory inventory.private.yaml
```

此脚本会：
1. 本地克隆/更新 [JuliaHZhu/skills](https://github.com/JuliaHZhu/skills) 仓库
2. 根据 `bees.yaml` 中每个角色定义的 `default_skills`，按需 rsync 到对应节点
3. 在节点上生成 `~/.beebox/skills/.index` 索引文件

### 7. 收集日志

```bash
# 收集过去 1 小时的运行日志
python scripts/collect_logs.py --inventory inventory.private.yaml

# 收集过去 24 小时
python scripts/collect_logs.py --inventory inventory.private.yaml --since "24 hours ago"
```

收集结果保存到 `logs/collected/`（包含 JSON 和可读 TXT 两种格式）。

## 目录结构

```
beebox-deploy/
├── inventory.yaml              # 服务器清单示例
├── inventory.private.yaml      # 你的私有清单（gitignored）
├── config/
│   └── bees.yaml               # Bee 角色定义与仓库映射
├── scripts/
│   ├── deploy.py               # 批量部署
│   ├── update.py               # 批量更新
│   ├── collect_logs.py         # 日志收集
│   └── sync_skills.py          # Skills 同步
├── logs/                       # 本地日志存档（gitignored）
└── README.md
```

## 网络架构

```
         ┌─────────────────┐
         │  Commander Bee  │  ← 任务分发、监控
         │  + NATS Seed    │
         └────────┬────────┘
                  │ NATS Cluster
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────┐
│ Worker │  │  World   │  │  Writer  │
│  Bee   │  │   Bee    │  │   Bee    │
│+Hermes │  │          │  │          │
└────────┘  └──────────┘  └──────────┘
```

- 所有节点通过 NATS 集群互联（端口 4222/6222）
- 大文件传输通过 HTTP File Server（端口 8080）
- Skills 按需分发，各节点只接收自己需要的技能

## 环境要求

- **控制端**（你本地）：Python 3.10+、SSH 客户端、`rsync`（用于 skills 同步）
- **目标服务器**：Python 3.10+、Git、`nats-server`（自动安装）

## 未来扩展

- [ ] 自动 systemd 服务安装
- [ ] Docker / Docker Compose 部署模式
- [ ] GitHub Actions 集成（Webhook 触发自动更新）
- [ ] 节点健康检查与自动故障恢复
