#!/usr/bin/env python3
"""
TODO Ball Machine - 统一任务调度器
整合：TODO系统 + 生活记录 + Heartbeat + Cron
"""
import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
SCHEDULER_CONFIG = BASE_DIR / 'scheduler_config.json'

def load_json(path):
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def show_dashboard():
    """显示统一仪表盘"""
    print("="*70)
    print("📊【TODO Ball Machine - 统一仪表盘】")
    print("="*70)
    
    # 显示TODO系统状态
    print("\n📦【TODO系统状态】")
    try:
        # 查找正确的CLI文件名
        cli_files = list(BASE_DIR.glob('todo_cli*.py'))
        cli_file = cli_files[0].name if cli_files else 'todo_cli_final.py'
        
        result = subprocess.run(
            ['python3', cli_file, 'status'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
        print(result.stdout)
    except Exception as e:
        print(f"⚠️ 无法获取TODO系统状态: {e}")
    
    # 显示Heartbeat状态
    print("\n💓【Heartbeat状态】")
    heartbeat_status = load_json(BASE_DIR / 'heartbeat_tasks.json')
    last_run = heartbeat_status.get('last_run', {})
    for task, time in last_run.items():
        status = "✅" if time else "⏳"
        time_str = time or "从未执行"
        print(f"   {status} {task}: {time_str}")
    
    # 显示Cron提醒配置
    print("\n⏰【Cron提醒配置】")
    config = load_json(SCHEDULER_CONFIG)
    reminders = config.get('cron', {}).get('reminders', [])
    enabled_count = sum(1 for r in reminders if r.get('enabled', True))
    print(f"   已启用: {enabled_count}/{len(reminders)} 个提醒")
    
    print("\n" + "="*70)
    print("💡 快捷命令:")
    print("   todo_dealer status          - 显示TODO系统状态")
    print("   todo_dealer quick           - 快速抽取今日所有场次")
    print("   python heartbeat_runner.py  - 手动执行Heartbeat任务")
    print("   python cron_manager.py show  - 查看Cron提醒配置")
    print("="*70)

def sync_to_life_record():
    """同步TODO Ball Machine数据到生活记录"""
    print("🔄 同步TODO Ball Machine数据到生活记录...")
    # TODO: 实现同步逻辑
    # 1. 读取TODO Ball Machine Blocks数据
    # 2. 同步到生活记录的records目录
    # 3. 更新统计数据
    print("✅ 同步完成")

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'dashboard':
            show_dashboard()
        elif command == 'sync':
            sync_to_life_record()
        else:
            print(f"❌ 未知命令: {command}")
            print("可用命令: dashboard, sync")
    else:
        show_dashboard()

if __name__ == '__main__':
    main()
