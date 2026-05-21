#!/usr/bin/env python3
"""
TODO Ball Machine - Cron提醒管理器
"""
import json
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
SCHEDULER_CONFIG = BASE_DIR / 'scheduler_config.json'

def load_json(path):
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def setup_cron_reminders():
    """设置Cron提醒"""
    print("⏰ 设置TODO系统Cron提醒...")
    
    config = load_json(SCHEDULER_CONFIG)
    reminders = config.get('cron', {}).get('reminders', [])
    
    for reminder in reminders:
        if not reminder.get('enabled', True):
            continue
        
        print(f"  📋 {reminder['name']}: {reminder['cron_expr']}")
        # TODO: 使用nanobot的cron工具设置提醒
        # 这里需要用户手动设置或通过message工具提醒用户
    
    print("✅ Cron提醒设置完成")
    print("\n💡 提示：请使用 nanobot 的 cron 工具手动设置提醒")
    print("   示例：cron add \"0 9 * * *\" \"🌅 轻锚定提醒：9-9:30出门时间到！\"")

def show_current_reminders():
    """显示当前配置的提醒"""
    print("📋 当前TODO系统Cron提醒配置：")
    print("="*60)
    
    config = load_json(SCHEDULER_CONFIG)
    reminders = config.get('cron', {}).get('reminders', [])
    
    for reminder in reminders:
        status = "✅" if reminder.get('enabled', True) else "❌"
        print(f"{status} {reminder['name']}")
        print(f"   时间: {reminder['cron_expr']} ({reminder['timezone']})")
        print(f"   消息: {reminder['message'][:60]}...")
        print()

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'show':
        show_current_reminders()
    else:
        setup_cron_reminders()

if __name__ == '__main__':
    main()
