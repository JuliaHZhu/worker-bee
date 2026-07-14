#!/usr/bin/env python3
"""为每台 bee 创建独立 GitHub repo 并推送。

用法：在任意一台已装 worker-bee + gh 登录的机上跑：
    python3 beebox/setup_repos.py

前提：
    - gh auth login 已登录（每台机的 GitHub PAT 不同）
    - worker-bee 已安装在工作目录
"""

import subprocess, sys, os, json

# ═══════════════════════════════════════════
# 8 台机：IP → bee name
MACHINES = {
    "bee-01": "192.168.1.101",
    "bee-02": "192.168.1.102",
    "bee-03": "192.168.1.103",
    "bee-04": "192.168.1.104",
    "bee-05": "192.168.1.105",
    "bee-06": "192.168.1.106",
    "bee-07": "192.168.1.107",
    "bee-08": "192.168.1.108",
}
# ═══════════════════════════════════════════

SSH_USER = "ubuntu"
GITHUB_ORG = "JuliaHZhu"  # 改你的 GitHub 用户名/组织


def run_ssh(ip: str, cmd: str, timeout=30) -> tuple[bool, str, str]:
    full = f"ssh -o StrictHostKeyChecking=no {SSH_USER}@{ip} '{cmd}'"
    print(f"  [{ip}] {cmd[:100]}...")
    r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode == 0, r.stdout.strip(), r.stderr.strip()


def main():
    print(f"为 {len(MACHINES)} 台创建 GitHub repo:\n")
    for name, ip in MACHINES.items():
        print(f"  {name:8s}  {ip}")
    print()

    mode = "all"
    if len(sys.argv) > 1:
        mode = sys.argv[1]

    for name, ip in MACHINES.items():
        if mode == "dry-run":
            print(f"\n── {name} ({ip}) ── [DRY RUN]")
            print(f"  cd ~/worker-bee")
            print(f"  gh repo create {GITHUB_ORG}/worker-bee-{name} --private --source=. --remote=origin --push")
            print(f"  git branch -M main")
            continue

        print(f"\n── {name} ({ip}) ──")

        # 1. 确认 gh 已登录
        ok, out, err = run_ssh(ip, "gh auth status")
        if not ok:
            print(f"  ❌ gh 未登录，请先 SSH 到 {ip} 运行: gh auth login")
            continue
        print(f"  ✅ gh 已登录: {out.split(chr(10))[0] if out else 'OK'}")

        # 2. 创建 repo（gh repo create 自动设置 remote 并 push）
        ok, out, err = run_ssh(
            ip,
            (
                f"cd ~/worker-bee && gh repo create {GITHUB_ORG}/worker-bee-{name} "
                f"--private --source=. --remote=origin --push"
            ),
            timeout=60
        )
        if ok:
            print(f"  ✅ repo 创建成功: github.com/{GITHUB_ORG}/worker-bee-{name}")
        else:
            print(f"  ❌ 创建失败: {err[:200]}")
            # Fallback：手动设置
            run_ssh(
                ip,
                (
                    f"cd ~/worker-bee && git remote remove origin 2>/dev/null; "
                    f"git remote add origin https://github.com/{GITHUB_ORG}/worker-bee-{name}.git"
                ),
            )
            run_ssh(ip, "cd ~/worker-bee && git push -u origin main", timeout=60)

    if mode != "dry-run":
        print("\n── 验证 ──")
        for name, ip in MACHINES.items():
            subprocess.run(f"curl -sI https://github.com/{GITHUB_ORG}/worker-bee-{name} | head -1", shell=True)


if __name__ == "__main__":
    main()
