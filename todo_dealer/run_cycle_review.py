#!/usr/bin/env python3
"""
单独执行30天周期盘点
"""
import json
from datetime import datetime, date
from pathlib import Path

# 完全独立的路径定义 - 基于当前文件位置
BASE_DIR = Path(__file__).parent.resolve()
SCHEDULER_CONFIG = BASE_DIR / 'scheduler_config.json'
HEARTBEAT_STATUS = BASE_DIR / 'heartbeat_tasks.json'
STATS_FILE = BASE_DIR / 'cycle_stats.json'
BLOCKS_DIR = BASE_DIR / 'blocks'
DAILY_DRAWS_DIR = BASE_DIR / 'daily_draws'
CONFIG_FILE = BASE_DIR / '90blocks_config.json'
POOL_STATE = BASE_DIR / 'pool_state.json'


def load_json(path):
    """安全加载JSON文件"""
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_json(path, data):
    """安全保存JSON文件"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_blocks_stats():
    """从实际blocks目录获取统计数据"""
    config = load_json(CONFIG_FILE)
    boxes = config.get('boxes', {})
    
    box_stats = {}
    total_completed = 0
    
    for box_name, box_config in boxes.items():
        quota = box_config.get('quota', 0)
        box_stats[box_name] = {
            'quota': quota,
            'used': 0,
            'rate': 0.0,
            'emoji': box_config.get('emoji', '')
        }
    
    if BLOCKS_DIR.exists():
        for block_file in BLOCKS_DIR.glob('*.json'):
            block_data = load_json(block_file)
            if isinstance(block_data, list):
                for block in block_data:
                    if block.get('status') == 'completed':
                        box_name = block.get('box')
                        if box_name in box_stats:
                            box_stats[box_name]['used'] += 1
                            total_completed += 1
    
    total_quota = sum(b['quota'] for b in box_stats.values())
    for box_name in box_stats:
        if box_stats[box_name]['quota'] > 0:
            box_stats[box_name]['rate'] = (box_stats[box_name]['used'] / box_stats[box_name]['quota']) * 100
    
    return {
        'total_quota': total_quota,
        'total_completed': total_completed,
        'box_stats': box_stats
    }


def get_cycle_info():
    """获取当前周期信息"""
    today = date.today()
    cycle_name = f"{today.year}年{today.month:02d}月周期"
    start_date = date(today.year, today.month, 1)
    
    if today.month == 12:
        end_date = date(today.year, today.month, 31)
    else:
        end_date = date(today.year, today.month + 1, 1) - date.resolution
    
    total_days = (end_date - start_date).days + 1
    days_passed = (today - start_date).days + 1
    cycle_progress = min(100, max(0, round(days_passed / total_days * 100, 1)))
    
    return {
        'cycle': cycle_name,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'cycle_progress': cycle_progress
    }


def cycle_review():
    """30天周期盘点"""
    print("📊 执行30天周期盘点...")
    
    cycle_info = get_cycle_info()
    blocks_stats = get_blocks_stats()
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'version': 'v2.0',
        'cycle': cycle_info['cycle'],
        'start_date': cycle_info['start_date'],
        'end_date': cycle_info['end_date'],
        'total_blocks': blocks_stats['total_quota'],
        'completed_count': blocks_stats['total_completed'],
        'completion_rate': round((blocks_stats['total_completed'] / blocks_stats['total_quota'] * 100) if blocks_stats['total_quota'] > 0 else 0, 2),
        'box_stats': blocks_stats['box_stats'],
        'cycle_progress': cycle_info['cycle_progress']
    }
    
    stats = load_json(STATS_FILE)
    cycle_key = cycle_info['cycle']
    if cycle_key not in stats:
        stats[cycle_key] = []
    stats[cycle_key].append(report)
    save_json(STATS_FILE, stats)
    
    print(f"📅 周期: {report['cycle']}")
    print(f"📊 周期进度: {report['cycle_progress']}%")
    print(f"🎯 Blocks完成率: {report['completion_rate']}% ({blocks_stats['total_completed']}/{blocks_stats['total_quota']})")
    print("📦 各盒子完成情况:")
    for box_name, box_stat in blocks_stats['box_stats'].items():
        print(f"   {box_stat['emoji']} {box_name}: {box_stat['used']}/{box_stat['quota']} ({box_stat['rate']:.1f}%)")
    
    # 更新last_run时间
    status = load_json(HEARTBEAT_STATUS)
    status['last_run']['cycle_review'] = datetime.now().isoformat()
    save_json(HEARTBEAT_STATUS, status)
    
    print("✅ 30天周期盘点完成，报告已保存 (v2.0)")
    return report


if __name__ == '__main__':
    print("="*60)
    print("📊 TODO Ball Machine - 30天周期盘点 (手动执行)")
    print(f"🕐 {datetime.now().isoformat()}")
    print("="*60)
    cycle_review()
    print("="*60)
