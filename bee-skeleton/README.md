# Skeleton Bee — 总工程师/CAO

> 版本：MVP v3.1（红队修订版）

## 目录结构

```
bee-skeleton/
├── arch/<project>/   # 宪法：蓝图文件（带批准元数据）
├── patterns.md       # 经人 merge 的结构模式
├── anti-patterns.md  # 经人 merge 的踩坑记录
└── drafts/           # AI 唯一可写目录
```

## 用法

```bash
cd bee-skeleton

# 运行 Campaign 5步
python skeleton.py campaign my-project \
    --need "做一个自动化报告系统" \
    --by "厂长"

# 运行收尾
python skeleton.py closure my-project \
    --by "厂长" \
    --time "O(3天)" \
    --patches "2轮" \
    --pitfalls "需求模糊导致返工" \
    --patterns pipeline-linear

# 三倍扫描
python skeleton.py triple-scan
```

## 核心约束

`safe_write(path, content, approved_by="")`：写 `arch/` 必须传 `approved_by`，否则抛 `PermissionError`。
