#!/usr/bin/env python3
"""
Todo Ball Machine查询功能CLI - 新增的查询命令
"""

import sys
import argparse
import json
from pathlib import Path

# 添加当前路径到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from todo_use_cases import UseCaseFactory


def print_query_result(result, box_name):
    """打印查询结果"""
    print("=" * 80)
    print(f"📊 查询结果 - {box_name}")
    print(f"   {result['message']}")
    print("=" * 80)
    
    if result['success'] and result['results']:
        print()
        for i, item in enumerate(result['results'], 1):
            block = item['block']
            status_emoji = {
                'completed': '✅',
                'planned': '📋',
                'cancelled': '❌'
            }.get(block['status'], '❓')
            
            print(f"{i}. {item['date_display']} ({item['session_display']})")
            print(f"   {status_emoji} {block['content']}")
            print(f"   难度: {block['difficulty']} | 时长: {block['duration']}h")
            print()
    else:
        print("\n   暂无记录")
    
    print("=" * 80)


def print_boxes_list(result):
    """打印盒子列表"""
    print("=" * 80)
    print("📦 已使用的盒子列表")
    print(f"   {result['message']}")
    print("=" * 80)
    print()
    
    for i, box in enumerate(result['boxes'], 1):
        print(f"  {i}. {box}")
    
    print()
    print("=" * 80)


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="Todo Ball Machine查询功能 - 按盒子查询历史记录"
    )
    
    subparsers = parser.add_subparsers(title="命令", dest="command")
    
    # 查询盒子记录
    query_parser = subparsers.add_parser("query", help="查询指定盒子的记录")
    query_parser.add_argument("box_name", help="盒子名称（支持别名）")
    query_parser.add_argument("--all", action="store_true", help="包含所有类型的Block")
    query_parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    
    # 列出盒子
    list_parser = subparsers.add_parser("list", help="列出所有使用过的盒子")
    list_parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    use_case_factory = UseCaseFactory()
    
    if args.command == "list":
        result = use_case_factory.list_used_boxes.execute()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_boxes_list(result)
    
    elif args.command == "query":
        result = use_case_factory.query_blocks_by_box.execute(
            args.box_name,
            include_all_types=args.all
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_query_result(result, args.box_name)


if __name__ == "__main__":
    main()
