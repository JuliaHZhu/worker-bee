
#!/usr/bin/env python3
"""
TODO Ball Machine - Heartbeat任务运行器 v2.0 (完全独立版)
- 无硬编码路径依赖
- 完全独立于life_record
"""
import json
from datetime import datetime, date, timedelta
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
    """获取当前周期信息 - 7天周度周期，周一为周期开始"""
    today = date.today()
    # 计算本周周一的日期
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=6)
    cycle_name = f"{start_date.year}年{start_date.month:02d}月{start_date.day:02d}日周度周期"
    
    total_days = 7
    days_passed = (today - start_date).days + 1
    cycle_progress = min(100, max(0, round(days_passed / total_days * 100, 1)))
    
    return {
        'cycle': cycle_name,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'cycle_progress': cycle_progress
    }


def daily_todo_check():
    """每日TODO Ball Machine状态检查"""
    print("🔍 执行每日TODO Ball Machine状态检查...")
    
    today = date.today().isoformat()
    today_draw_file = DAILY_DRAWS_DIR / f"draw_{today}.json"
    
    if today_draw_file.exists():
        print("   ✅ 今日已抽取色球")
    else:
        print("   ⚠️ 今日尚未抽取色球")
    
    if BLOCKS_DIR.exists():
        completed_today = 0
        for block_file in BLOCKS_DIR.glob('*.json'):
            block_data = load_json(block_file)
            if isinstance(block_data, list):
                for block in block_data:
                    if block.get('status') == 'completed' and block.get('date') == today:
                        completed_today += 1
        print(f"   🎯 今日已完成Blocks: {completed_today}个")
    
    print("✅ 每日TODO Ball Machine状态检查完成")


def cycle_review():
    """7天周度周期盘点"""
    print("📊 执行7天周度周期盘点...")
    
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
    
    print("✅ 7天周度周期盘点完成，报告已保存 (v2.0)")


def ball_pool_maintenance():
    """抽彩球池维护"""
    print("🎲 执行抽彩球池维护...")
    
    pool_state = load_json(POOL_STATE)
    
    if pool_state:
        print(f"   ✅ 球池状态正常")
    
    print("✅ 抽彩球池维护完成")


def is_time_to_run(task_config, last_run_str):
    """检查是否是任务执行时间"""
    now = datetime.now()
    
    # 检查指定时间的任务
    if 'time' in task_config:
        target_time = task_config['time']  # 格式 "HH:MM"
        target_hour, target_min = map(int, target_time.split(':'))
        
        # 检查是否在目标时间的±30分钟窗口内
        if now.hour == target_hour and abs(now.minute - target_min) <= 30:
            # 检查今天是否已经运行过
            if last_run_str:
                last_run = datetime.fromisoformat(last_run_str)
                if last_run.date() == now.date():
                    return False  # 今天已经运行过了
            return True
    
    return False


def main():
    """主函数 - 执行所有Heartbeat任务"""
    print("="*60)
    print("🚀 TODO Ball Machine - Heartbeat任务运行器 v2.0")
    print("   完全独立版 | 无硬编码依赖")
    print(f"🕐 {datetime.now().isoformat()}")
    print("="*60)
    
    config = load_json(SCHEDULER_CONFIG)
    if not config.get('heartbeat', {}).get('enabled', True):
        print("⚠️ Heartbeat已禁用，跳过执行")
        return
    
    status = load_json(HEARTBEAT_STATUS)
    if 'last_run' not in status:
        status['last_run'] = {}
    
    tasks = config.get('heartbeat', {}).get('tasks', {})
    
    if tasks.get('daily_todo_check', {}).get('enabled', False):
        daily_todo_check()
        status['last_run']['daily_todo_check'] = datetime.now().isoformat()
    
    if tasks.get('cycle_review', {}).get('enabled', True):
        last_run = status['last_run'].get('cycle_review', '')
        if is_time_to_run(tasks['cycle_review'], last_run):
            cycle_review()
            status['last_run']['cycle_review'] = datetime.now().isoformat()
        else:
            print(f"⏭️  跳过cycle_review（非执行时间或今日已执行）")
    
    if tasks.get('ball_pool_maintenance', {}).get('enabled', False):
        ball_pool_maintenance()
        status['last_run']['ball_pool_maintenance'] = datetime.now().isoformat()
    
    save_json(HEARTBEAT_STATUS, status)
    
    print("="*60)
    print("✅ Heartbeat任务检查完成 (v2.0)")
    print("="*60)


if __name__ == '__main__':
    main()

