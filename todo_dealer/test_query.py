#!/usr/bin/env python3
"""
测试按盒子查询Block的新功能
"""

import sys
from pathlib import Path

# 添加当前路径到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from todo_managers import BlockManager
from todo_use_cases import UseCaseFactory


def test_manager_query():
    """测试Manager层的查询功能"""
    print("=" * 80)
    print("测试 Manager 层查询功能")
    print("=" * 80)
    
    block_manager = BlockManager()
    
    # 测试获取所有使用过的盒子
    print("\n1. 获取所有使用过的盒子:")
    boxes = block_manager.get_all_used_boxes()
    print(f"   找到 {len(boxes)} 个盒子: {boxes}")
    
    # 测试查询某个盒子
    if boxes:
        test_box = boxes[0]
        print(f"\n2. 查询盒子 '{test_box}' 的记录:")
        results = block_manager.query_blocks_by_box(test_box)
        
        if results:
            print(f"   找到 {len(results)} 条记录:")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result.date_display} {result.session_display}: {result.block.content} [{result.status_display}]")
        else:
            print("   未找到记录")
    
    print()


def test_use_case_query():
    """测试Use Case层的查询功能"""
    print("=" * 80)
    print("测试 Use Case 层查询功能")
    print("=" * 80)
    
    use_case_factory = UseCaseFactory()
    
    # 测试列出所有使用过的盒子
    print("\n1. 列出所有使用过的盒子:")
    result = use_case_factory.list_used_boxes.execute()
    print(f"   {result['message']}")
    print(f"   盒子列表: {result['boxes']}")
    
    # 测试查询某个盒子
    if result['boxes']:
        test_box = result['boxes'][0]
        print(f"\n2. 查询盒子 '{test_box}' 的记录:")
        query_result = use_case_factory.query_blocks_by_box.execute(test_box)
        
        if query_result['success']:
            print(f"   {query_result['message']}")
            for i, item in enumerate(query_result['results'], 1):
                block = item['block']
                print(f"   {i}. {item['date_display']} {item['session_display']}: "
                      f"{block['content']} [{item['status_display']}]")
        else:
            print(f"   {query_result['message']}")
    
    print()


def test_with_alias():
    """测试别名支持"""
    print("=" * 80)
    print("测试别名支持功能")
    print("=" * 80)
    
    use_case_factory = UseCaseFactory()
    
    # 测试一些别名
    alias_tests = [
        "探索",
        "运动", 
        "学习",
        "休息"
    ]
    
    for alias in alias_tests:
        print(f"\n尝试使用别名 '{alias}' 查询:")
        result = use_case_factory.query_blocks_by_box.execute(alias)
        if result['success']:
            print(f"   ✅ {result['message']}")
        else:
            print(f"   ❌ {result['message']}")
    
    print()


if __name__ == "__main__":
    test_manager_query()
    test_use_case_query()
    test_with_alias()
    print("✅ 测试完成！")
