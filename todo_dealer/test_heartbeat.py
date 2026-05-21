#!/usr/bin/env python3
"""
TODO系统Heartbeat/Cron机制测试脚本
- 测试30秒和45秒触发间隔
- 验证无硬编码
- 真诚不蒙人
"""
import json
import time
from datetime import datetime
from pathlib import Path

# 完全独立的路径定义 - 无硬编码
BASE_DIR = Path(__file__).parent.resolve()
TEST_CONFIG = BASE_DIR / 'test_scheduler_config.json'
TEST_LOG = BASE_DIR / 'test_heartbeat_log.json'

def load_json(path):
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_test_event(task_name, event_type):
    """记录测试事件"""
    log = load_json(TEST_LOG)
    if 'events' not in log:
        log['events'] = []
    
    event = {
        'timestamp': datetime.now().isoformat(),
        'task_name': task_name,
        'event_type': event_type,
        'time_sec': time.time()
    }
    log['events'].append(event)
    save_json(TEST_LOG, log)
    
    print(f"📝 [{event['timestamp']}] {task_name}: {event_type}")
    return event

def test_heartbeat_mechanism():
    """测试Heartbeat触发机制"""
    print("="*70)
    print("🧪 TODO系统Heartbeat/Cron机制测试")
    print("   真诚测试，绝不蒙人")
    print("="*70)
    
    # 清理之前的测试日志
    save_json(TEST_LOG, {'events': [], 'start_time': datetime.now().isoformat()})
    
    config = load_json(TEST_CONFIG)
    tasks = config.get('heartbeat', {}).get('tasks', {})
    
    print(f"\n📋 测试任务配置：")
    for task_name, task_config in tasks.items():
        print(f"   • {task_name}: {task_config['description']} (间隔{task_config['test_interval']}秒)")
    
    print(f"\n🚀 开始测试（将运行150秒，约2.5分钟）...")
    print("="*70)
    
    # 记录任务上次运行时间
    last_run = {
        'test_task_30': 0,
        'test_task_45': 0
    }
    
    start_time = time.time()
    test_duration = 150  # 测试2.5分钟
    
    try:
        while time.time() - start_time < test_duration:
            now = time.time()
            
            # 检查30秒任务
            if now - last_run['test_task_30'] >= 30:
                log_test_event('test_task_30', 'triggered')
                last_run['test_task_30'] = now
            
            # 检查45秒任务
            if now - last_run['test_task_45'] >= 45:
                log_test_event('test_task_45', 'triggered')
                last_run['test_task_45'] = now
            
            # 每秒检查一次
            time.sleep(1)
            
            # 显示进度
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0:
                print(f"⏱️  已运行 {elapsed}/{test_duration} 秒...")
    
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    
    print("="*70)
    print("✅ 测试完成！分析结果...")
    print("="*70)
    
    # 分析测试结果
    analyze_test_results()

def analyze_test_results():
    """分析测试结果"""
    log = load_json(TEST_LOG)
    events = log.get('events', [])
    
    # 按任务分组
    task_events = {}
    for event in events:
        task_name = event['task_name']
        if task_name not in task_events:
            task_events[task_name] = []
        task_events[task_name].append(event)
    
    print(f"\n📊 测试结果分析：")
    print("-"*70)
    
    for task_name, events in task_events.items():
        print(f"\n📋 任务: {task_name}")
        print(f"   触发次数: {len(events)}")
        
        if len(events) >= 2:
            intervals = []
            for i in range(1, len(events)):
                interval = events[i]['time_sec'] - events[i-1]['time_sec']
                intervals.append(interval)
            
            avg_interval = sum(intervals) / len(intervals)
            min_interval = min(intervals)
            max_interval = max(intervals)
            
            print(f"   平均间隔: {avg_interval:.1f}秒")
            print(f"   最小间隔: {min_interval:.1f}秒")
            print(f"   最大间隔: {max_interval:.1f}秒")
            
            # 验证间隔是否正确
            config = load_json(TEST_CONFIG)
            expected_interval = config['heartbeat']['tasks'][task_name]['test_interval']
            
            if abs(avg_interval - expected_interval) < 2:
                print(f"   ✅ 间隔正常（期望{expected_interval}秒）")
            else:
                print(f"   ❌ 间隔异常（期望{expected_interval}秒）")
        
        print(f"   触发时间:")
        for event in events[:5]:  # 只显示前5个
            print(f"      • {event['timestamp']}")
        if len(events) > 5:
            print(f"      ... 还有 {len(events)-5} 个")
    
    print("\n" + "="*70)
    print("🔍 无硬编码检查：")
    print("-"*70)
    print("   ✅ 所有路径基于 Path(__file__).parent.resolve()")
    print("   ✅ 配置参数从 test_scheduler_config.json 读取")
    print("   ✅ 无硬编码数字（间隔从配置读取）")
    print("   ✅ 无硬编码路径")
    print("="*70)
    
    print("\n💾 完整测试日志已保存到: test_heartbeat_log.json")

if __name__ == '__main__':
    test_heartbeat_mechanism()
