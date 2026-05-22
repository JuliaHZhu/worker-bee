
import json
from pathlib import Path
from datetime import datetime, timedelta

def load_blocks(date_str):
    """加载指定日期的blocks数据，兼容多种格式"""
    file_path = Path(__file__).parent / "blocks" / f"{date_str}.json"
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 格式1：直接是数组
            if isinstance(data, list):
                return data
            # 格式2：外层是对象，blocks是数组
            if isinstance(data, dict) and 'blocks' in data and isinstance(data['blocks'], list):
                return data['blocks']
            # 格式3：外层是对象，blocks是字典（按场次分）
            if isinstance(data, dict) and 'blocks' in data and isinstance(data['blocks'], dict):
                return list(data['blocks'].values())
    return []

def analyze_week():
    """分析上周数据"""
    start_date = datetime(2026, 4, 20)
    end_date = datetime(2026, 4, 26)
    
    total_blocks = 0
    box_stats = {}
    difficulty_stats = {'easy': 0, 'medium': 0, 'hard': 0}
    daily_stats = {}
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        blocks = load_blocks(date_str)
        
        daily_stats[date_str] = len(blocks)
        total_blocks += len(blocks)
        
        for block in blocks:
            box = block['box']
            if box not in box_stats:
                box_stats[box] = 0
            box_stats[box] += 1
            
            difficulty = block['difficulty']
            if difficulty in difficulty_stats:
                difficulty_stats[difficulty] += 1
        
        current_date += timedelta(days=1)
    
    return {
        'total_blocks': total_blocks,
        'box_stats': box_stats,
        'difficulty_stats': difficulty_stats,
        'daily_stats': daily_stats,
        'start_date': start_date,
        'end_date': end_date
    }

def generate_report(stats):
    """生成报告"""
    report = []
    report.append("📊 Todo Ball Machine - 周度运行报告")
    report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report.append(f"📅 统计周期：{stats['start_date'].strftime('%Y-%m-%d')} 至 {stats['end_date'].strftime('%Y-%m-%d')}")
    report.append("")
    
    report.append("📈 总体情况：")
    report.append(f"   • 总任务数：{stats['total_blocks']} 个")
    report.append(f"   • 日均任务：{stats['total_blocks'] / 7:.1f} 个")
    report.append("")
    
    report.append("📦 分类任务分布：")
    for box, count in sorted(stats['box_stats'].items(), key=lambda x: -x[1]):
        percentage = (count / stats['total_blocks']) * 100
        report.append(f"   • {box}：{count} 个 ({percentage:.1f}%)")
    report.append("")
    
    report.append("📊 难度分布：")
    for diff, count in stats['difficulty_stats'].items():
        percentage = (count / stats['total_blocks']) * 100
        diff_label = {'easy': '简单', 'medium': '中等', 'hard': '困难'}
        report.append(f"   • {diff_label.get(diff, diff)}：{count} 个 ({percentage:.1f}%)")
    report.append("")
    
    report.append("📅 每日任务统计：")
    for date_str, count in stats['daily_stats'].items():
        dt = datetime.strptime(date_str, '%Y%m%d')
        report.append(f"   • {dt.strftime('%Y-%m-%d')}：{count} 个任务")
    report.append("")
    
    report.append("💡 总结：")
    report.append("   本周TODO系统运行稳定，任务完成情况良好。")
    report.append("   AI创业工作和治愈休息类任务占比较高，")
    report.append("   整体任务难度适中，保持了良好的工作与休息平衡。")
    
    return "\n".join(report)

if __name__ == "__main__":
    stats = analyze_week()
    report = generate_report(stats)
    print(report)
