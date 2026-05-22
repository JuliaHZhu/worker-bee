
#!/usr/bin/env python3
"""
TODO Ball Machine - 数据模型层
定义所有核心数据类和验证器
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from enum import Enum


class Difficulty(Enum):
    """任务难度枚举"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    
    @classmethod
    def from_string(cls, value) -> 'Difficulty':
        """从字符串创建枚举"""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError:
            valid_values = [d.value for d in cls]
            raise ValueError(f"无效的难度: {value}，有效选项: {valid_values}")


class BlockType(Enum):
    """Block类型枚举"""
    NORMAL = "normal"
    GHOST = "ghost"
    UNDEFINED = "undefined"
    
    @classmethod
    def from_string(cls, value: any) -> 'BlockType':
        """从字符串创建枚举"""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError:
            valid_values = [t.value for t in cls]
            raise ValueError(f"无效的Block类型: {value}，有效选项: {valid_values}")


class BlockStatus(Enum):
    """Block状态枚举"""
    PLANNED = "planned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    
    @classmethod
    def from_string(cls, value: any) -> 'BlockStatus':
        """从字符串创建枚举"""
        # 如果已经是枚举，直接返回
        if isinstance(value, cls):
            return value
        
        # 兼容性别名映射
        aliases = {
            "done": "completed",
            "finished": "completed"
        }
        
        value_str = str(value).lower()
        
        # 处理兼容性别名
        if value_str in aliases:
            value_str = aliases[value_str]
        
        try:
            return cls(value_str)
        except ValueError:
            valid_values = [s.value for s in cls]
            aliases_str = ', '.join([f"{k}->{v}" for k, v in aliases.items()])
            raise ValueError(f"无效的Block状态: {value}，有效选项: {valid_values} (兼容别名: {aliases_str})")


class Session(Enum):
    """场次枚举"""
    AM = "am"
    PM = "pm"
    EVENING = "evening"
    OVERTIME = "overtime"
    
    @classmethod
    def from_string(cls, value: any) -> 'Session':
        """从字符串创建枚举"""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError:
            valid_values = [s.value for s in cls]
            raise ValueError(f"无效的场次: {value}，有效选项: {valid_values}")
    
    @property
    def display_name(self) -> str:
        """获取显示名称"""
        names = {
            self.AM: "上午场",
            self.PM: "下午场",
            self.EVENING: "晚间场",
            self.OVERTIME: "加班场"
        }
        return names.get(self, self.value)
    
    @classmethod
    def get_standard_sessions(cls) -> List['Session']:
        """获取标准场次（不含加班场）"""
        return [cls.AM, cls.PM, cls.EVENING]
    
    @classmethod
    def get_all_sessions(cls) -> List['Session']:
        """获取所有场次（含加班场）"""
        return [cls.AM, cls.PM, cls.EVENING, cls.OVERTIME]


class CycleStatus(Enum):
    """周期状态枚举"""
    ACTIVE = "active"
    EXPIRED = "expired"
    PENDING = "pending"
    
    @classmethod
    def from_string(cls, value: any) -> 'CycleStatus':
        """从字符串创建枚举"""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError:
            valid_values = [s.value for s in cls]
            raise ValueError(f"无效的周期状态: {value}，有效选项: {valid_values}")


class SessionStatus(Enum):
    """场次状态枚举"""
    PENDING = "pending"
    DRAWN = "drawn"
    REDRAWN = "redrawn"
    EDITED = "edited"
    BLOCKED = "blocked"
    
    @classmethod
    def from_string(cls, value: any) -> 'SessionStatus':
        """从字符串创建枚举"""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError:
            valid_values = [s.value for s in cls]
            raise ValueError(f"无效的场次状态: {value}，有效选项: {valid_values}")


class ActionType(Enum):
    """动作类型枚举"""
    DRAW = "draw"
    REDRAW = "redraw"
    EDIT = "edit"
    
    @classmethod
    def from_string(cls, value: any) -> 'ActionType':
        """从字符串创建枚举"""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError:
            valid_values = [a.value for a in cls]
            raise ValueError(f"无效的动作类型: {value}，有效选项: {valid_values}")


class BoxName(Enum):
    """盒子名称枚举 - 标准盒子名称"""
    PHD_WORK = "博士工作"
    AI_ENTREPRENEURSHIP = "AI创业工作"
    HEALTH_EXERCISE = "健康运动"
    REST_HEALING = "治愈休息"
    SPACE_EXPLORATION = "空间探索"
    HOUSEWORK = "家务整理"
    
    @classmethod
    def from_string(cls, value: any) -> 'BoxName':
        """从字符串创建枚举"""
        if isinstance(value, cls):
            return value
        
        # 兼容性别名映射
        aliases = {
            "运动健身": "健康运动",
            "健身运动": "健康运动",
            "锻炼": "健康运动",
            "运动": "健康运动",
            "AI工作": "AI创业工作",
            "创业": "AI创业工作",
            "博士": "博士工作",
            "学习": "博士工作",
            "休息": "治愈休息",
            "探索": "空间探索",
            "家务": "家务整理"
        }
        
        value_str = str(value)
        
        # 处理兼容性别名
        if value_str in aliases:
            value_str = aliases[value_str]
        
        try:
            return cls(value_str)
        except ValueError:
            valid_values = [b.value for b in cls]
            aliases_str = ', '.join([f"{k}→{v}" for k, v in aliases.items()])
            raise ValueError(f"无效的盒子名称: {value}，有效选项: {valid_values} (兼容别名: {aliases_str})")
    
    @classmethod
    def get_all_names(cls) -> List[str]:
        """获取所有标准盒子名称"""
        return [b.value for b in cls]


@dataclass
class ColorBall:
    """色球数据类"""
    id: str
    content: str
    difficulty: Difficulty
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'content': self.content,
            'difficulty': self.difficulty.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColorBall':
        """从字典创建"""
        return cls(
            id=data['id'],
            content=data['content'],
            difficulty=Difficulty.from_string(data['difficulty'])
        )


@dataclass
class BoxConfig:
    """盒子配置数据类"""
    name: str
    emoji: str
    quota: int
    balls: List[ColorBall] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'emoji': self.emoji,
            'quota': self.quota,
            'balls': [ball.to_dict() for ball in self.balls]
        }
    
    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any], balls: List[ColorBall] = None) -> 'BoxConfig':
        """从字典创建"""
        return cls(
            name=name,
            emoji=data.get('emoji', ''),
            quota=data.get('quota', 0),
            balls=balls or []
        )


@dataclass
class Block:
    """Block数据类"""
    id: str
    type: BlockType
    box: str
    content: str
    difficulty: Difficulty
    duration: float
    date: date
    session: Optional[Session] = None
    status: BlockStatus = BlockStatus.PLANNED
    output: Optional[str] = None
    ball_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'type': self.type.value,
            'box': self.box,
            'content': self.content,
            'difficulty': self.difficulty.value,
            'duration': self.duration,
            'date': self.date.isoformat(),
            'session': self.session.value if self.session else None,
            'status': self.status.value,
            'output': self.output,
            'ball_id': self.ball_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """从字典创建"""
        return cls(
            id=data['id'],
            type=BlockType.from_string(data['type']),
            box=data['box'],
            content=data['content'],
            difficulty=Difficulty.from_string(data['difficulty']),
            duration=data.get('duration', 2.5),
            date=date.fromisoformat(data['date']) if data.get('date') else date.today(),
            session=Session.from_string(data['session']) if data.get('session') else None,
            status=BlockStatus.from_string(data.get('status', 'planned')),
            output=data.get('output'),
            ball_id=data.get('ball_id'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now()
        )


@dataclass
class CycleConfig:
    """周期配置数据类"""
    name: str
    start_date: date
    end_date: date
    duration_map: Dict[Difficulty, float]
    boxes: List[BoxConfig]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'cycle_name': self.name,
            'cycle_start': self.start_date.isoformat(),
            'cycle_end': self.end_date.isoformat(),
            'duration_map': {k.value: v for k, v in self.duration_map.items()},
            'boxes': {box.name: {'emoji': box.emoji, 'quota': box.quota} for box in self.boxes}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CycleConfig':
        """从字典创建"""
        duration_map = {}
        for k, v in data.get('duration_map', {}).items():
            try:
                duration_map[Difficulty.from_string(k)] = v
            except ValueError:
                continue
        
        boxes = []
        for box_name, box_data in data.get('boxes', {}).items():
            boxes.append(BoxConfig(
                name=box_name,
                emoji=box_data.get('emoji', ''),
                quota=box_data.get('quota', 0)
            ))
        
        return cls(
            name=data.get('cycle_name', '默认周期'),
            start_date=date.fromisoformat(data['cycle_start']) if data.get('cycle_start') else date.today(),
            end_date=date.fromisoformat(data['cycle_end']) if data.get('cycle_end') else date.today(),
            duration_map=duration_map,
            boxes=boxes
        )


@dataclass
class Cycle:
    """周期数据类 - 30天一个周期"""
    cycle_id: str
    start_date: date
    end_date: date
    status: CycleStatus = CycleStatus.ACTIVE
    quota_map: Dict[str, int] = field(default_factory=dict)
    used_count_map: Dict[str, int] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'cycle_id': self.cycle_id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'status': self.status.value,
            'quota_map': self.quota_map,
            'used_count_map': self.used_count_map,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Cycle':
        """从字典创建"""
        return cls(
            cycle_id=data['cycle_id'],
            start_date=date.fromisoformat(data['start_date']),
            end_date=date.fromisoformat(data['end_date']),
            status=CycleStatus.from_string(data.get('status', 'active')),
            quota_map=data.get('quota_map', {}),
            used_count_map=data.get('used_count_map', {}),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now()
        )


@dataclass
class SessionRecord:
    """场次记录数据类 - 一天内的三场之一"""
    date: date
    session_name: Session
    status: SessionStatus = SessionStatus.PENDING
    result: Optional[str] = None
    drawn_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'date': self.date.isoformat(),
            'session_name': self.session_name.value,
            'status': self.status.value,
            'result': self.result,
            'drawn_at': self.drawn_at.isoformat() if self.drawn_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionRecord':
        """从字典创建"""
        return cls(
            date=date.fromisoformat(data['date']),
            session_name=Session.from_string(data['session_name']),
            status=SessionStatus.from_string(data.get('status', 'pending')),
            result=data.get('result'),
            drawn_at=datetime.fromisoformat(data['drawn_at']) if data.get('drawn_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )


@dataclass
class DrawRecord:
    """抽取记录数据类 - 历史抽取记录"""
    record_id: str
    date: date
    session_name: Session
    action_type: ActionType
    before_result: Optional[str] = None
    after_result: Optional[str] = None
    box_used: Optional[str] = None
    operator: str = "system"
    timestamp: datetime = field(default_factory=datetime.now)
    note: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'record_id': self.record_id,
            'date': self.date.isoformat(),
            'session_name': self.session_name.value,
            'action_type': self.action_type.value,
            'before_result': self.before_result,
            'after_result': self.after_result,
            'box_used': self.box_used,
            'operator': self.operator,
            'timestamp': self.timestamp.isoformat(),
            'note': self.note
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DrawRecord':
        """从字典创建"""
        return cls(
            record_id=data['record_id'],
            date=date.fromisoformat(data['date']),
            session_name=Session.from_string(data['session_name']),
            action_type=ActionType.from_string(data['action_type']),
            before_result=data.get('before_result'),
            after_result=data.get('after_result'),
            box_used=data.get('box_used'),
            operator=data.get('operator', 'system'),
            timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else datetime.now(),
            note=data.get('note')
        )


@dataclass
class GhostBlock:
    """Ghost Block数据类 - 预留但未完成"""
    block_id: str
    target_date: date
    session_name: Session
    reason: str
    type: str = "ghost"
    status: str = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'block_id': self.block_id,
            'type': self.type,
            'target_date': self.target_date.isoformat(),
            'session_name': self.session_name.value,
            'reason': self.reason,
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GhostBlock':
        """从字典创建"""
        return cls(
            block_id=data['block_id'],
            type=data.get('type', 'ghost'),
            target_date=date.fromisoformat(data['target_date']),
            session_name=Session.from_string(data['session_name']),
            reason=data['reason'],
            status=data.get('status', 'active')
        )


@dataclass
class UndefinedBlock:
    """Undefined Block数据类 - 暂不明确但需要保留"""
    block_id: str
    content: str
    type: str = "undefined"
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'block_id': self.block_id,
            'type': self.type,
            'content': self.content,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UndefinedBlock':
        """从字典创建"""
        return cls(
            block_id=data['block_id'],
            type=data.get('type', 'undefined'),
            content=data['content'],
            status=data.get('status', 'pending'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )


@dataclass
class HeartbeatState:
    """心跳状态数据类 - 监控系统健康"""
    last_run_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error: Optional[str] = None
    is_smooth: bool = True
    checked_items: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'last_success_at': self.last_success_at.isoformat() if self.last_success_at else None,
            'last_error': self.last_error,
            'is_smooth': self.is_smooth,
            'checked_items': self.checked_items
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HeartbeatState':
        """从字典创建"""
        return cls(
            last_run_at=datetime.fromisoformat(data['last_run_at']) if data.get('last_run_at') else None,
            last_success_at=datetime.fromisoformat(data['last_success_at']) if data.get('last_success_at') else None,
            last_error=data.get('last_error'),
            is_smooth=data.get('is_smooth', True),
            checked_items=data.get('checked_items', [])
        )


@dataclass
class CronConfig:
    """定时任务配置数据类"""
    enabled: bool = True
    schedule: str = ""
    command: str = ""
    last_modified_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'enabled': self.enabled,
            'schedule': self.schedule,
            'command': self.command,
            'last_modified_at': self.last_modified_at.isoformat() if self.last_modified_at else None,
            'next_run_at': self.next_run_at.isoformat() if self.next_run_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CronConfig':
        """从字典创建"""
        return cls(
            enabled=data.get('enabled', True),
            schedule=data.get('schedule', ''),
            command=data.get('command', ''),
            last_modified_at=datetime.fromisoformat(data['last_modified_at']) if data.get('last_modified_at') else None,
            next_run_at=datetime.fromisoformat(data['next_run_at']) if data.get('next_run_at') else None
        )


@dataclass
class BlockQueryResult:
    """Block查询结果数据类 - 用于按盒子查询的结果展示"""
    block: Block
    date_display: str = ""
    session_display: str = ""
    status_display: str = ""
    
    def __post_init__(self):
        """初始化显示字段"""
        self.date_display = self.block.date.strftime("%Y-%m-%d")
        self.session_display = self.block.session.display_name if self.block.session else "未知场次"
        self.status_display = self._get_status_display()
    
    def _get_status_display(self) -> str:
        """获取状态显示名称"""
        status_names = {
            BlockStatus.PLANNED: "计划中",
            BlockStatus.COMPLETED: "已完成",
            BlockStatus.CANCELLED: "已取消"
        }
        return status_names.get(self.block.status, self.block.status.value)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'block': self.block.to_dict(),
            'date_display': self.date_display,
            'session_display': self.session_display,
            'status_display': self.status_display
        }


class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_box_name(box_name: str, valid_boxes: List[str] = None) -> str:
        """验证盒子名称 - 使用BoxName枚举，支持自动别名转换"""
        if not box_name:
            raise ValueError("盒子名称不能为空")
        
        # 使用BoxName枚举验证并自动处理别名
        box_name_enum = BoxName.from_string(box_name)
        validated_name = box_name_enum.value
        
        # 如果提供了valid_boxes，额外验证
        if valid_boxes and validated_name not in valid_boxes:
            raise ValueError(f"无效的盒子名称: {box_name}，有效选项: {valid_boxes}")
        
        # 如果输入和标准名称不同，提示转换
        if box_name != validated_name:
            print(f"💡 盒子名称 '{box_name}' 已自动转换为标准名称 '{validated_name}'")
        
        return validated_name
    
    @staticmethod
    def validate_difficulty(difficulty: str) -> Difficulty:
        """验证难度"""
        return Difficulty.from_string(difficulty)
    
    @staticmethod
    def validate_date(date_str: str) -> date:
        """验证日期格式"""
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            raise ValueError(f"无效的日期格式: {date_str}，请使用 YYYY-MM-DD 格式")
    
    @staticmethod
    def validate_quota(quota: int) -> int:
        """验证配额"""
        if not isinstance(quota, int):
            raise TypeError("配额必须是整数")
        if quota < 0:
            raise ValueError("配额不能为负数")
        return quota
    
    @staticmethod
    def validate_session(session: str) -> Session:
        """验证场次"""
        return Session.from_string(session)
    
    @staticmethod
    def validate_block_type(block_type: str) -> BlockType:
        """验证Block类型"""
        return BlockType.from_string(block_type)
    
    @staticmethod
    def validate_block_status(status: str) -> BlockStatus:
        """验证Block状态"""
        return BlockStatus.from_string(status)

