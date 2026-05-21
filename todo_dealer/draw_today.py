#!/usr/bin/env python3
"""
简单的今日抽球脚本
"""

import json
import random
from datetime import datetime
from pathlib import Path

BASE_PATH = Path(__file__).parent


def load_color_balls():
    """加载色球配置"""
    with open(BASE_PATH / "color_balls.json", 'r', encoding='utf-8') as f:
        return json.load(f)


def draw_ball(box_name, color_balls_data):
    """从指定盒子抽取一个球"""
    box = color_balls_data['boxes'].get(box_name, {})
    balls = box.get('balls', [])
    if not balls:
        return None
    return random.choice(balls)


def create_today_draw():
    """创建今日抽奖记录"""
    today = datetime.now().strftime("%Y-%m-%d")
    today_file = BASE_PATH / "daily_draws" / f"{today.replace('-', '')}_draw.json"
    
    # 检查是否已经存在
    if today_file.exists():
        print(f"今日抽奖记录已存在: {today_file}")
        return
    
    color_balls_data = load_color_balls()
    
    # 可用盒子列表
    available_boxes = list(color_balls_data['boxes'].keys())
    
    # 随机抽取三个场次
    draws = {}
    sessions = ['am', 'pm', 'evening']
    
    for session in sessions:
        box_name = random.choice(available_boxes)
        ball = draw_ball(box_name, color_balls_data)
        
        if ball:
            draws[session] = {
                "box": box_name,
                "content": ball.get('content', box_name),
                "difficulty": ball.get('difficulty', 'medium'),
                "duration": ball.get('duration', 2.5),
                "status": "planned"
            }
        else:
            draws[session] = {
                "box": box_name,
                "content": box_name,
                "difficulty": "medium",
                "duration": 2.5,
                "status": "planned"
            }
    
    # 保存抽奖记录
    result = {
        "date": today,
        "draws": draws
    }
    
    with open(today_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"🎉 今日抽奖完成！已保存到: {today_file}")
    print("\n📋 今日安排:")
    for session, data in draws.items():
        session_name = {'am': '上午场', 'pm': '下午场', 'evening': '晚间场'}[session]
        print(f"  {session_name}: {data['content']} [{data['box']}]")


if __name__ == "__main__":
    create_today_draw()
