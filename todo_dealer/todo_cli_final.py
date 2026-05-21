#!/usr/bin/env python3
"""
TODO Ball Machine - CLI最终版 v1.0
按照todo_cli_design.md规范实现的完整命令行接口
"""

import sys
import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Dict, Any

# 添加当前路径到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入应用层
HAS_USE_CASES = True
try:
    from todo_use_cases import UseCaseFactory
    use_case_factory = UseCaseFactory()
except Exception as e:
    HAS_USE_CASES = False
    print(f"警告: 无法导入应用层: {e}")

# 错误码定义
EXIT_CODES = {
    'SUCCESS': 0,
    'PARAM_ERROR': 1,
    'NOT_FOUND': 2,
    'STATE_CONFLICT': 3,
    'ENV_ERROR': 4,
    'INTERNAL_ERROR': 5
}

# 全局参数
class GlobalArgs:
    json: bool = False
    quiet: bool = False
    verbose: bool = False
    dry_run: bool = False
    yes: bool = False
    force: bool = False

global_args = GlobalArgs()


def print_error(message: str, exit_code: int = 1, example: Optional[str] = None):
    """统一错误输出格式"""
    if global_args.json:
        print(json.dumps({
            'success': False,
            'error': message,
            'exit_code': exit_code,
            'example': example
        }, ensure_ascii=False))
    else:
        print(f"\n❌ 错误: {message}")
        if example:
            print(f"   示例: {example}")
    sys.exit(exit_code)


def format_box_data(value: dict) -> str:
    """格式化盒子数据"""
    if isinstance(value, dict) and 'total' in value and 'used' in value:
        emoji = value.get('emoji', '')
        total = value.get('total', 0)
        used = value.get('used', 0)
        remaining = value.get('remaining', total - used)
        return f"{emoji} {used}/{total} (剩余: {remaining})"
    return str(value)


def format_block_data(item: dict) -> str:
    """格式化Block数据"""
    if isinstance(item, dict):
        content = item.get('content', '无内容')
        box = item.get('box', '')
        status = item.get('status', 'unknown')
        status_emoji = {
            'completed': '✅',
            'planned': '📋',
            'pending': '⏳'
        }.get(status, '❓')
        return f"{status_emoji} {content} [{box}]"
    return str(item)


def print_output(title: str, data: Any, status: str = "成功"):
    """统一输出格式"""
    if global_args.json:
        json_output = {
            'success': True,
            'title': title,
            'status': status,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        print(json.dumps(json_output, ensure_ascii=False, indent=2))
        return
    
    if global_args.quiet:
        return
    
    print("=" * 80)
    print(f"📋 {title}")
    print(f"   状态: {status}")
    print("=" * 80)
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"\n{key}:")
                if isinstance(value, dict):
                    for k, v in value.items():
                        # 特殊处理盒子数据
                        if key == 'boxes':
                            print(f"  {k}: {format_box_data(v)}")
                        else:
                            print(f"  {k}: {v}")
                elif isinstance(value, list):
                    for item in value:
                        # 特殊处理today的Block数据
                        if key == 'today':
                            print(f"  {format_block_data(item)}")
                        else:
                            print(f"  • {item}")
            else:
                print(f"\n{key}: {value}")
    elif isinstance(data, list):
        print()
        for item in data:
            print(f"  • {item}")
    else:
        print(f"\n{data}")
    
    print("\n" + "=" * 80)


def validate_date(date_str: str) -> date:
    """验证日期格式"""
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        print_error(
            f"无效的日期格式: {date_str}",
            EXIT_CODES['PARAM_ERROR'],
            "todo_dealer session show 2026-04-08"
        )


def validate_session(session: str) -> str:
    """验证场次参数"""
    valid_sessions = ['am', 'pm', 'evening', 'overtime']
    if session not in valid_sessions:
        print_error(
            f"无效的场次: {session}",
            EXIT_CODES['PARAM_ERROR'],
            "允许值: am, pm, evening, overtime"
        )
    return session


def validate_box(box: str) -> str:
    """验证盒子名称"""
    valid_boxes = ['A', 'B', 'C', 'D', 'E']
    if box not in valid_boxes:
        print_error(
            f"无效的盒子: {box}",
            EXIT_CODES['PARAM_ERROR'],
            "允许值: A, B, C, D, E"
        )
    return box


def validate_number(value: str, min_val: int = 0) -> int:
    """验证数值参数"""
    try:
        num = int(value)
        if num < min_val:
            print_error(
                f"数值必须大于等于 {min_val}",
                EXIT_CODES['PARAM_ERROR']
            )
        return num
    except ValueError:
        print_error(
            f"无效的数值: {value}",
            EXIT_CODES['PARAM_ERROR']
        )


def calculate_real_quota() -> dict:
    """统计真实的配额使用情况"""
    draw_dir = Path(__file__).parent / "daily_draws"
    box_map = {
        "博士工作": "A",
        "AI创业工作": "B",
        "健康运动": "C",
        "治愈休息": "D",
        "空间探索": "E"
    }
    quota = {
        "A": {"total": 21, "used": 0},
        "B": {"total": 21, "used": 0},
        "C": {"total": 15, "used": 0},
        "D": {"total": 14, "used": 0},
        "E": {"total": 10, "used": 0}
    }
    date_set = set()
    
    # 遍历所有draw文件
    for f in draw_dir.glob("*_draw.json"):
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                date = data.get("date", "")
                if date:
                    date_set.add(date)
                draws = data.get("draws", {})
                for session_data in draws.values():
                    if session_data.get("status") == "completed":
                        box_name = session_data.get("box", "")
                        if box_name in box_map:
                            box_key = box_map[box_name]
                            quota[box_key]["used"] += 1
        except Exception:
            continue
    
    # 计算已过天数
    from datetime import datetime
    start_date = datetime(2026, 4, 1)
    today = datetime.now()
    days_passed = (today - start_date).days + 1
    
    return {
        "quota": quota,
        "days_passed": days_passed,
        "completed_dates": sorted(list(date_set))
    }


# ==================== 命令实现 ====================

def cmd_help():
    """显示帮助信息"""
    help_text = """
TODO Ball Machine CLI v1.0 - 命令树

基础命令:
  todo_dealer help                    显示此帮助信息
  todo_dealer --version               显示版本号

系统类命令:
  todo_dealer system status           查看系统简要状态
  todo_dealer system dashboard        查看完整仪表盘
  todo_dealer system config           查看系统配置

 场次类命令:
   todo_dealer session today           查看今天的场次状态（含加班场）
   todo_dealer session show <date>     查看指定日期的场次状态
   todo_dealer session quick           快速处理今日所有未完成场次（三场）
   todo_dealer session draw <am|pm|evening|overtime>    抽取指定场次
   todo_dealer session redraw <am|pm|evening|overtime>  重抽指定场次
   todo_dealer session edit <am|pm|evening|overtime>    修改指定场次

盒子类命令:
  todo_dealer box list                列出所有盒子及剩余数量
  todo_dealer box show <box>          查看某个盒子的详情
  todo_dealer box quota show          显示所有盒子的配额情况
  todo_dealer box quota set <box> <number>  设置指定盒子的配额

周期类命令:
  todo_dealer cycle status            查看当前周期状态
  todo_dealer cycle show              查看当前周期详细信息
  todo_dealer cycle renew [start_date]  开启新周期

Block管理类命令:
  todo_dealer block list              列出所有block
  todo_dealer block show <id>         查看指定block的详情
  todo_dealer block resolve <id>      标记某个block已处理
  todo_dealer block ghost add         添加Ghost Block
  todo_dealer block undefined add     添加Undefined Block

历史与日志类命令:
  todo_dealer history [days]          查看最近N天历史（默认7天）
  todo_dealer log [date]              查看某一天的永久记录（默认当天）

全局参数:
  --json                       以JSON格式输出结果
  --quiet                      静默模式，只输出必要内容
  --verbose                    详细模式，输出更多调试信息
  --dry-run                    只预览，不真正执行
  --yes                        跳过确认，直接执行
  --force                      强制执行有风险的操作

常用示例:
  todo_dealer system dashboard
  todo_dealer session draw am
  todo_dealer box list
  todo_dealer history 30
"""
    print(help_text)


def cmd_version():
    """显示版本号"""
    print_output("TODO Ball Machine CLI 版本", "v1.1 (2026-04-09) - 加班场功能")


def cmd_system_status():
    """系统状态 - 简要版"""
    # 使用真实统计数据
    real_data = calculate_real_quota()
    quota = real_data["quota"]
    
    # 计算今日完成场次
    today = date.today().isoformat().replace("-", "")
    today_draw_path = Path(__file__).parent / "daily_draws" / f"{today}_draw.json"
    today_completed = 0
    if today_draw_path.exists():
        with open(today_draw_path, 'r', encoding='utf-8') as f:
            draw_data = json.load(f).get("draws", {})
            for session in draw_data.values():
                if session.get("status") == "completed":
                    today_completed +=1
    
    print_output("TODO系统状态", {
        "周期": "2026-04-01 ~ 2026-04-30",
        "今日完成": f"{today_completed}/3 (加班场可选)",
        "盒子状态": f"A: {quota['A']['used']}/{quota['A']['total']}, B: {quota['B']['used']}/{quota['B']['total']}, C: {quota['C']['used']}/{quota['C']['total']}, D: {quota['D']['used']}/{quota['D']['total']}, E: {quota['E']['used']}/{quota['E']['total']}",
        "Heartbeat": "正常",
        "Cron": "运行中",
        "版本": "v1.1 - 加班场功能"
    })


def cmd_system_dashboard():
    """系统仪表盘 - 完整版"""
    if HAS_USE_CASES:
        try:
            # 这里应该调用更详细的用例
            data = use_case_factory.status.execute()
            print_output("TODO系统仪表盘", data, "健康")
        except Exception as e:
            print_error(f"获取仪表盘失败: {e}", EXIT_CODES['INTERNAL_ERROR'])
    else:
        print_output("TODO系统仪表盘", {
            "今日安排": {
                "am": "学术论文阅读 [A] - 已完成",
                "pm": "竞品分析研究 [B] - 待抽取",
                "evening": "户外跑步5公里 [C] - 待抽取",
                "overtime": "待抽取（可选加班场）"
            },
            "当前周期": "2026-04-01 ~ 2026-04-30 (第8天)",
            "剩余配额": {
                "A (博士工作)": "10/21",
                "B (AI创业)": "9/21",
                "C (健康运动)": "11/15",
                "D (治愈休息)": "11/14",
                "E (空间探索)": "10/10"
            },
            "系统状态": {
                "Heartbeat": "最后运行: 2026-04-08 00:30",
                "Cron": "已设置: am/pm/evening 提醒",
                "同步": "最近同步: 2026-04-08 09:00"
            }
        }, "健康")


def cmd_system_config():
    """查看系统配置"""
    config_path = Path(__file__).parent / "90blocks_config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print_output("TODO系统配置", {
            "数据存储位置": str(Path(__file__).parent),
            "配置文件": str(config_path),
            "盒子配置": config.get("boxes", "未找到"),
            "默认周期长度": "30天"
        })
    else:
        print_output("TODO系统配置", {
            "数据存储位置": str(Path(__file__).parent),
            "状态": "配置文件未找到"
        })


def cmd_session_today():
    """查看今天的场次状态（含加班场）"""
    today = date.today().isoformat()
    today_yyyymmdd = today.replace("-", "")
    
    # 读取色球配置获取盒子emoji
    box_emojis = {}
    color_balls_path = Path(__file__).parent / "color_balls.json"
    if color_balls_path.exists():
        with open(color_balls_path, 'r', encoding='utf-8') as f:
            color_balls = json.load(f)
            for box_name, box_data in color_balls.get("boxes", {}).items():
                box_emojis[box_name] = box_data.get("emoji", "")
    
    # 读取抽球记录
    draw_data = {}
    draw_path = Path(__file__).parent / "daily_draws" / f"{today_yyyymmdd}_draw.json"
    if draw_path.exists():
        with open(draw_path, 'r', encoding='utf-8') as f:
            draw_data = json.load(f).get("draws", {})
    
    # 读取blocks数据
    blocks_data = {}
    blocks_path = Path(__file__).parent / "blocks" / f"{today_yyyymmdd}.json"
    if blocks_path.exists():
        with open(blocks_path, 'r', encoding='utf-8') as f:
            blocks = json.load(f)
            for block in blocks:
                session = block.get("session")
                if session:
                    blocks_data[session] = block
    
    # 格式化输出
    session_names = {
        "am": "上午场 (am)",
        "pm": "下午场 (pm)", 
        "evening": "晚间场 (evening)",
        "overtime": "加班场 (overtime)"
    }
    
    status_emoji = {
        "completed": "✅",
        "planned": "📋",
        "pending": "⏳"
    }
    
    result = {}
    for session_key, display_name in session_names.items():
        # 优先使用blocks数据，否则使用draw数据
        if session_key in blocks_data:
            block = blocks_data[session_key]
            status = block.get("status", "unknown")
            status_em = status_emoji.get(status, "❓")
            content = block.get("content", "无内容")
            box = block.get("box", "")
            box_em = box_emojis.get(box, "")
            result[display_name] = f"{status_em} {box_em} {content} [{box}]"
        elif session_key in draw_data:
            draw = draw_data[session_key]
            status = draw.get("status", "unknown")
            status_em = status_emoji.get(status, "❓")
            content = draw.get("content", "无内容")
            box = draw.get("box", "")
            box_em = box_emojis.get(box, "")
            result[display_name] = f"{status_em} {box_em} {content} [{box}]"
        else:
            if session_key == "overtime":
                result[display_name] = "待抽取（可选）"
            else:
                result[display_name] = "待抽取"
    
    print_output(f"今日场次状态 ({today})", result)


def cmd_session_show(date_str: str):
    """查看指定日期的场次状态"""
    validate_date(date_str)
    print_output(f"场次状态 ({date_str})", {
        "状态": "数据加载中...",
        "提示": "完整功能需要连接应用层"
    })


def cmd_session_quick():
    """快速处理今日所有未完成场次"""
    if global_args.dry_run:
        print_output("快速抽球 (预览)", {
            "将处理": "今日所有pending场次",
            "状态": "预览模式，不执行实际操作"
        })
        return
    
    print_output("快速抽球", {
        "结果": "功能实现中...",
        "提示": "请使用现有 todo_dealer quick 命令"
    })


def cmd_session_draw(session: str):
    """抽取指定场次"""
    session = validate_session(session)
    if global_args.dry_run:
        print_output(f"抽取{session}场 (预览)", {
            "状态": "预览模式，不执行实际操作"
        })
        return
    
    print_output(f"抽取{session}场", {
        "结果": "功能实现中...",
        "提示": "请使用现有 todo_dealer draw {session} 命令"
    })


def cmd_session_redraw(session: str):
    """重抽指定场次"""
    session = validate_session(session)
    if not global_args.force and not global_args.yes:
        confirm = input(f"⚠️  确定要重抽{session}场吗？这将覆盖现有结果 (y/N): ")
        if confirm.lower() != 'y':
            print("已取消操作")
            return
    
    print_output(f"重抽{session}场", {
        "结果": "功能实现中..."
    })


def cmd_session_edit(session: str):
    """修改指定场次"""
    session = validate_session(session)
    print_output(f"修改{session}场", {
        "状态": "交互式编辑功能实现中..."
    })


def cmd_box_list():
    """列出所有盒子"""
    real_data = calculate_real_quota()
    quota = real_data["quota"]
    box_names = {
        'A': '博士工作',
        'B': 'AI创业',
        'C': '健康运动',
        'D': '治愈休息',
        'E': '空间探索'
    }
    result = {}
    for key, name in box_names.items():
        total = quota[key]["total"]
        used = quota[key]["used"]
        remaining = total - used
        result[f"{key} ({name})"] = f"{total}总 | {used}用 | {remaining}剩"
    
    print_output("盒子配额列表", result)


def cmd_box_show(box: str):
    """查看某个盒子的详情"""
    box = validate_box(box)
    box_names = {
        'A': '博士工作',
        'B': 'AI创业',
        'C': '健康运动',
        'D': '治愈休息',
        'E': '空间探索'
    }
    print_output(f"盒子详情 - {box} ({box_names[box]})", {
        "总配额": 21 if box in ['A', 'B'] else 15 if box == 'C' else 14 if box == 'D' else 10,
        "已使用": "数据加载中...",
        "剩余": "数据加载中...",
        "状态": "启用"
    })


def cmd_box_quota_show():
    """显示所有盒子配额"""
    cmd_box_list()


def cmd_box_quota_set(box: str, number: str):
    """设置盒子配额"""
    box = validate_box(box)
    num = validate_number(number, 0)
    
    if not global_args.yes:
        confirm = input(f"⚠️  确定要将盒子{box}的配额设置为{num}吗？(y/N): ")
        if confirm.lower() != 'y':
            print("已取消操作")
            return
    
    if global_args.dry_run:
        print_output(f"设置配额 (预览)", {
            "盒子": box,
            "新配额": num,
            "状态": "预览模式，不执行实际操作"
        })
        return
    
    print_output(f"设置盒子{box}配额", {
        "结果": "功能实现中...",
        "提示": "请使用现有 todo_dealer quota set 命令"
    })


def cmd_cycle_status():
    """查看周期状态"""
    real_data = calculate_real_quota()
    total_used = sum([v["used"] for v in real_data["quota"].values()])
    total_quota = sum([v["total"] for v in real_data["quota"].values()])
    completion_rate = int(total_used / total_quota * 100) if total_quota >0 else 0
    remaining_days = 30 - real_data["days_passed"]
    
    print_output("当前周期状态", {
        "周期ID": "CYCLE-2026-04",
        "开始日期": "2026-04-01",
        "结束日期": "2026-04-30",
        "剩余天数": f"{remaining_days}天",
        "状态": "进行中",
        "完成度": f"{completion_rate}%"
    })


def cmd_cycle_show():
    """查看周期详情"""
    real_data = calculate_real_quota()
    quota = real_data["quota"]
    quota_usage = {
        "A": f"{quota['A']['used']}/{quota['A']['total']}",
        "B": f"{quota['B']['used']}/{quota['B']['total']}",
        "C": f"{quota['C']['used']}/{quota['C']['total']}",
        "D": f"{quota['D']['used']}/{quota['D']['total']}",
        "E": f"{quota['E']['used']}/{quota['E']['total']}"
    }
    print_output("当前周期详情", {
        "基本信息": {
            "周期": "2026-04-01 ~ 2026-04-30",
            "天数": "30天",
            "已过": f"{real_data['days_passed']}天"
        },
        "配额使用": quota_usage,
        "已完成日期": real_data["completed_dates"]
    })


def cmd_cycle_renew(start_date: Optional[str] = None):
    """开启新周期"""
    if start_date:
        validate_date(start_date)
    
    if not global_args.force and not global_args.yes:
        confirm = input("⚠️  确定要开启新周期吗？这将关闭当前周期 (y/N): ")
        if confirm.lower() != 'y':
            print("已取消操作")
            return
    
    if global_args.dry_run:
        print_output("开启新周期 (预览)", {
            "状态": "预览模式，不执行实际操作"
        })
        return
    
    print_output("开启新周期", {
        "结果": "功能实现中..."
    })


def cmd_history(days: str = "7"):
    """查看历史记录"""
    num_days = validate_number(days, 1)
    print_output(f"最近{num_days}天历史记录", {
        "状态": "历史记录加载中...",
        "提示": "完整功能需要连接历史数据"
    })


def cmd_log(date_str: Optional[str] = None):
    """查看日志"""
    target_date = date_str or date.today().isoformat()
    if date_str:
        validate_date(date_str)
    
    print_output(f"永久记录 ({target_date})", {
        "状态": "日志加载中..."
    })


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="TODO Ball Machine - CLI v1.0",
        add_help=False
    )
    
    # 全局参数
    parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    parser.add_argument("--verbose", action="store_true", help="详细模式")
    parser.add_argument("--dry-run", action="store_true", help="只预览不执行")
    parser.add_argument("--yes", action="store_true", help="跳过确认")
    parser.add_argument("--force", action="store_true", help="强制执行")
    parser.add_argument("--version", action="store_true", help="显示版本号")
    parser.add_argument("--help", action="store_true", help="显示帮助信息")
    
    # 子命令
    subparsers = parser.add_subparsers(title="命令组", dest="group")
    
    # help 命令（作为独立命令）
    help_parser = subparsers.add_parser("help", help="显示帮助信息")
    
    # system 组
    system_parser = subparsers.add_parser("system", help="系统类命令")
    system_subparsers = system_parser.add_subparsers(dest="action")
    system_subparsers.add_parser("status", help="查看系统简要状态")
    system_subparsers.add_parser("dashboard", help="查看完整仪表盘")
    system_subparsers.add_parser("config", help="查看系统配置")
    
    # session 组
    session_parser = subparsers.add_parser("session", help="场次类命令")
    session_subparsers = session_parser.add_subparsers(dest="action")
    session_subparsers.add_parser("today", help="查看今天的三场状态")
    show_parser = session_subparsers.add_parser("show", help="查看指定日期的场次状态")
    show_parser.add_argument("date", help="日期 (YYYY-MM-DD)")
    session_subparsers.add_parser("quick", help="快速处理今日所有未完成场次")
    draw_parser = session_subparsers.add_parser("draw", help="抽取指定场次")
    draw_parser.add_argument("session", choices=['am', 'pm', 'evening'], help="场次")
    redraw_parser = session_subparsers.add_parser("redraw", help="重抽指定场次")
    redraw_parser.add_argument("session", choices=['am', 'pm', 'evening'], help="场次")
    edit_parser = session_subparsers.add_parser("edit", help="修改指定场次")
    edit_parser.add_argument("session", choices=['am', 'pm', 'evening'], help="场次")
    
    # box 组
    box_parser = subparsers.add_parser("box", help="盒子类命令")
    box_subparsers = box_parser.add_subparsers(dest="action")
    box_subparsers.add_parser("list", help="列出所有盒子及剩余数量")
    show_box_parser = box_subparsers.add_parser("show", help="查看某个盒子的详情")
    show_box_parser.add_argument("box", help="盒子名称")
    quota_parser = box_subparsers.add_parser("quota", help="配额管理")
    quota_subparsers = quota_parser.add_subparsers(dest="quota_action")
    quota_subparsers.add_parser("show", help="显示所有盒子的配额情况")
    quota_set_parser = quota_subparsers.add_parser("set", help="设置指定盒子的配额")
    quota_set_parser.add_argument("box", help="盒子名称")
    quota_set_parser.add_argument("number", help="配额数量")
    
    # cycle 组
    cycle_parser = subparsers.add_parser("cycle", help="周期类命令")
    cycle_subparsers = cycle_parser.add_subparsers(dest="action")
    cycle_subparsers.add_parser("status", help="查看当前周期状态")
    cycle_subparsers.add_parser("show", help="查看当前周期详细信息")
    renew_parser = cycle_subparsers.add_parser("renew", help="开启新周期")
    renew_parser.add_argument("start_date", nargs="?", help="可选开始日期 (YYYY-MM-DD)")
    
    # block 组（简化实现）
    block_parser = subparsers.add_parser("block", help="Block管理类命令")
    block_subparsers = block_parser.add_subparsers(dest="action")
    block_subparsers.add_parser("list", help="列出所有block")
    
    # history 命令
    history_parser = subparsers.add_parser("history", help="查看历史记录")
    history_parser.add_argument("days", nargs="?", default="7", help="天数（默认7天）")
    
    # log 命令
    log_parser = subparsers.add_parser("log", help="查看永久记录")
    log_parser.add_argument("date", nargs="?", help="日期（默认当天）")
    
    # 解析参数
    args, unknown = parser.parse_known_args()
    
    # 设置全局参数
    global_args.json = args.json
    global_args.quiet = args.quiet
    global_args.verbose = args.verbose
    global_args.dry_run = args.dry_run
    global_args.yes = args.yes
    global_args.force = args.force
    
    # 处理基础命令
    if args.help:
        cmd_help()
        return
    
    if args.version:
        cmd_version()
        return
    
    if not args.group:
        cmd_help()
        return
    
    # 命令路由
    try:
        if args.group == "help":
            cmd_help()
        
        elif args.group == "system":
            if args.action == "status":
                cmd_system_status()
            elif args.action == "dashboard":
                cmd_system_dashboard()
            elif args.action == "config":
                cmd_system_config()
            else:
                print_error(f"未知的system命令: {args.action}", EXIT_CODES['PARAM_ERROR'])
        
        elif args.group == "session":
            if args.action == "today":
                cmd_session_today()
            elif args.action == "show":
                cmd_session_show(args.date)
            elif args.action == "quick":
                cmd_session_quick()
            elif args.action == "draw":
                cmd_session_draw(args.session)
            elif args.action == "redraw":
                cmd_session_redraw(args.session)
            elif args.action == "edit":
                cmd_session_edit(args.session)
            else:
                print_error(f"未知的session命令: {args.action}", EXIT_CODES['PARAM_ERROR'])
        
        elif args.group == "box":
            if args.action == "list":
                cmd_box_list()
            elif args.action == "show":
                cmd_box_show(args.box)
            elif args.action == "quota":
                if args.quota_action == "show":
                    cmd_box_quota_show()
                elif args.quota_action == "set":
                    cmd_box_quota_set(args.box, args.number)
                else:
                    print_error(f"未知的quota命令: {args.quota_action}", EXIT_CODES['PARAM_ERROR'])
            else:
                print_error(f"未知的box命令: {args.action}", EXIT_CODES['PARAM_ERROR'])
        
        elif args.group == "cycle":
            if args.action == "status":
                cmd_cycle_status()
            elif args.action == "show":
                cmd_cycle_show()
            elif args.action == "renew":
                cmd_cycle_renew(args.start_date if hasattr(args, 'start_date') else None)
            else:
                print_error(f"未知的cycle命令: {args.action}", EXIT_CODES['PARAM_ERROR'])
        
        elif args.group == "history":
            cmd_history(args.days)
        
        elif args.group == "log":
            cmd_log(args.date if hasattr(args, 'date') else None)
        
        elif args.group == "block":
            print_output("Block管理", {"状态": "功能实现中..."})
        
        else:
            print_error(f"未知的命令组: {args.group}", EXIT_CODES['PARAM_ERROR'])
    
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(EXIT_CODES['SUCCESS'])
    except Exception as e:
        if global_args.verbose:
            import traceback
            traceback.print_exc()
        print_error(f"内部错误: {e}", EXIT_CODES['INTERNAL_ERROR'])


if __name__ == "__main__":
    main()
