#!/usr/bin/env python3
"""
TODO Ball Machine - 管理器层
包含配额管理、球池管理、Block管理等核心业务逻辑
"""

import json
import os
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any

from todo_models import (
    ColorBall, BoxConfig, Block, CycleConfig,
    Difficulty, BlockType, BlockStatus, Session, DataValidator,
    BlockQueryResult
)


BASE_PATH = Path(os.environ.get("ENTP_BASE_PATH", Path(__file__).parent))


class QuotaManager:
    """配额管理器"""
    
    def __init__(self, cycle_config: CycleConfig):
        self._cycle_config = cycle_config
    
    def get_valid_boxes(self) -> List[str]:
        """获取所有有效盒子名称"""
        return [box.name for box in self._cycle_config.boxes]
    
    def get_box_total(self, box_name: str) -> int:
        """获取指定盒子的总配额"""
        DataValidator.validate_box_name(box_name, self.get_valid_boxes())
        for box in self._cycle_config.boxes:
            if box.name == box_name:
                return box.quota
        return 0
    
    def get_box_used_count(self, box_name: str, all_blocks: List[Block]) -> int:
        """统计指定盒子已完成的Normal Block数量"""
        DataValidator.validate_box_name(box_name, self.get_valid_boxes())
        used = 0
        
        cycle_start = self._cycle_config.start_date
        for day_offset in range(30):
            check_date = cycle_start + timedelta(days=day_offset)
            day_blocks = [b for b in all_blocks if b.date == check_date]
            
            for block in day_blocks:
                if (block.type == BlockType.NORMAL 
                    and block.status == BlockStatus.COMPLETED 
                    and block.box == box_name):
                    used += 1
        
        return used
    
    def get_box_remaining(self, box_name: str, all_blocks: List[Block]) -> int:
        """获取指定盒子的剩余配额"""
        used = self.get_box_used_count(box_name, all_blocks)
        total = self.get_box_total(box_name)
        return max(0, total - used)
    
    def get_duration(self, difficulty: Difficulty) -> float:
        """获取指定难度的时长"""
        return self._cycle_config.duration_map.get(difficulty, 2.5)


class BallPoolManager:
    """球池管理器"""
    
    def __init__(self, color_balls_data: Dict, pool_state_data: Dict = None):
        self._color_balls_data = color_balls_data
        self._pool_state = pool_state_data or self._initialize_pool_state()
        self._pool_path = BASE_PATH / "pool_state.json"
    
    def _initialize_pool_state(self) -> Dict:
        """初始化球池状态"""
        pool_state = {'boxes': {}}
        
        for box_name, box_config in self._color_balls_data.get('boxes', {}).items():
            balls = box_config.get('balls', [])
            pool_state['boxes'][box_name] = {
                'available': [ball['id'] for ball in balls],
                'used': []
            }
        
        return pool_state
    
    def _save_pool_state(self):
        """保存球池状态"""
        with open(self._pool_path, 'w', encoding='utf-8') as f:
            json.dump(self._pool_state, f, ensure_ascii=False, indent=2)
    
    def get_valid_boxes(self) -> List[str]:
        """获取所有有效盒子名称"""
        return list(self._color_balls_data.get('boxes', {}).keys())
    
    def get_ball_by_id(self, box_name: str, ball_id: str) -> Optional[ColorBall]:
        """根据ID获取球"""
        DataValidator.validate_box_name(box_name, self.get_valid_boxes())
        balls = self._color_balls_data.get('boxes', {}).get(box_name, {}).get('balls', [])
        for ball in balls:
            if ball['id'] == ball_id:
                return ColorBall.from_dict(ball)
        return None
    
    def draw_ball(self, box_name: str) -> ColorBall:
        """从球池堆栈顶部抽取一个球"""
        DataValidator.validate_box_name(box_name, self.get_valid_boxes())
        
        if box_name not in self._pool_state['boxes']:
            raise Exception(f"盒子 {box_name} 不存在于球池中！")
        
        available_ball_ids = self._pool_state['boxes'][box_name]['available']
        if not available_ball_ids:
            raise Exception(f"盒子 {box_name} 没有可用的球！")
        
        # 从堆栈顶部取球（列表最后一个）
        ball_id = available_ball_ids.pop()
        
        # 标记为已使用
        self._pool_state['boxes'][box_name]['used'].append(ball_id)
        self._save_pool_state()
        
        ball = self.get_ball_by_id(box_name, ball_id)
        if not ball:
            raise Exception(f"找不到球 {ball_id} 的信息！")
        
        return ball
    
    def return_ball(self, box_name: str, ball_id: str):
        """将球放回球池（堆栈退回机制）"""
        DataValidator.validate_box_name(box_name, self.get_valid_boxes())
        
        if box_name in self._pool_state['boxes']:
            if ball_id in self._pool_state['boxes'][box_name]['used']:
                self._pool_state['boxes'][box_name]['used'].remove(ball_id)
            if ball_id not in self._pool_state['boxes'][box_name]['available']:
                self._pool_state['boxes'][box_name]['available'].append(ball_id)  # 放回堆栈顶部
            self._save_pool_state()
    
    def sync_with_blocks(self, all_blocks: List[Block]):
        """根据已有Blocks同步球池状态"""
        # 这个方法暂时保留，用于兼容历史数据
        pass
    
    def get_pool_state(self) -> Dict:
        """获取球池状态（只读）"""
        return json.loads(json.dumps(self._pool_state))


class BlockManager:
    """Block管理器"""
    
    def __init__(self, base_path: Path = None):
        self._base_path = base_path or BASE_PATH
    
    def _get_blocks_path(self, target_date: date = None) -> Path:
        """获取指定日期的Blocks存储路径"""
        if target_date is None:
            target_date = date.today()
        date_str = target_date.strftime("%Y%m%d")
        return self._base_path / "blocks" / f"{date_str}.json"
    
    def load_blocks(self, target_date: date = None) -> List[Block]:
        """加载指定日期的Blocks"""
        blocks_path = self._get_blocks_path(target_date)
        if blocks_path.exists():
            with open(blocks_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 兼容：某些旧文件是 dict 格式（非 Block 列表），跳过
            if isinstance(data, list):
                return [Block.from_dict(item) for item in data]
        return []
    
    def load_all_blocks(self, cycle_start: date = None) -> List[Block]:
        """加载周期内所有Blocks"""
        if cycle_start is None:
            cycle_start = date.today()
        
        all_blocks = []
        for day_offset in range(30):
            check_date = cycle_start + timedelta(days=day_offset)
            all_blocks.extend(self.load_blocks(check_date))
        
        return all_blocks
    
    def save_blocks(self, blocks: List[Block], target_date: date = None):
        """保存Blocks到指定日期"""
        blocks_path = self._get_blocks_path(target_date)
        blocks_path.parent.mkdir(parents=True, exist_ok=True)
        with open(blocks_path, 'w', encoding='utf-8') as f:
            json.dump([block.to_dict() for block in blocks], f, ensure_ascii=False, indent=2)
    
    def generate_block_id(self) -> str:
        """生成Block ID"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        random_suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=5))
        return f"BLOCK-{timestamp}-{random_suffix}"
    
    def create_block(
        self,
        block_type: BlockType = BlockType.NORMAL,
        box: str = None,
        content: str = None,
        difficulty: Difficulty = Difficulty.MEDIUM,
        duration: float = 2.5,
        session: Session = None,
        ball_id: str = None,
        target_date: date = None
    ) -> Block:
        """创建一个Block"""
        if target_date is None:
            target_date = date.today()
        
        return Block(
            id=self.generate_block_id(),
            type=block_type,
            box=box,
            content=content,
            difficulty=difficulty,
            duration=duration,
            date=target_date,
            session=session,
            status=BlockStatus.PLANNED,
            output=None,
            ball_id=ball_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def update_block(self, blocks: List[Block], block_id: str, **kwargs) -> Optional[Block]:
        """更新Block"""
        for block in blocks:
            if block.id == block_id:
                # 更新字段
                for key, value in kwargs.items():
                    if hasattr(block, key):
                        setattr(block, key, value)
                block.updated_at = datetime.now()
                return block
        return None
    
    def find_block_by_id(self, blocks: List[Block], block_id: str) -> Optional[Block]:
        """根据ID查找Block"""
        for block in blocks:
            if block.id == block_id:
                return block
        return None
    
    def find_block_by_session(self, blocks: List[Block], session: Session) -> Optional[Block]:
        """根据场次查找Block"""
        for block in blocks:
            if block.session == session and block.type == BlockType.NORMAL:
                return block
        return None
    
    def query_blocks_by_box(
        self, 
        box_name: str, 
        cycle_start: date = None,
        include_all_types: bool = False,
        sort_by_date: bool = True
    ) -> List[BlockQueryResult]:
        """
        按盒子名称查询所有相关Blocks
        
        Args:
            box_name: 盒子名称（支持自动别名转换）
            cycle_start: 周期开始日期，默认今天
            include_all_types: 是否包含所有类型（normal/ghost/undefined），默认只包含normal
            sort_by_date: 是否按日期排序，默认升序
        
        Returns:
            BlockQueryResult列表
        """
        from todo_models import BoxName
        
        # 验证并标准化盒子名称
        try:
            box_name_enum = BoxName.from_string(box_name)
            validated_box_name = box_name_enum.value
        except ValueError:
            # 如果不是标准盒子名称，使用原始输入（可能是自定义盒子）
            validated_box_name = box_name
        
        # 加载所有Blocks
        all_blocks = self.load_all_blocks(cycle_start)
        
        # 过滤Blocks
        filtered_blocks = []
        for block in all_blocks:
            # 盒子名称匹配
            if block.box != validated_box_name:
                continue
            
            # 类型过滤
            if not include_all_types and block.type != BlockType.NORMAL:
                continue
            
            filtered_blocks.append(block)
        
        # 排序
        if sort_by_date:
            filtered_blocks.sort(key=lambda x: (x.date, x.session.value if x.session else ""))
        
        # 转换为查询结果
        results = [BlockQueryResult(block=block) for block in filtered_blocks]
        
        return results
    
    def get_all_used_boxes(self, cycle_start: date = None) -> List[str]:
        """
        获取周期内所有使用过的盒子名称
        
        Args:
            cycle_start: 周期开始日期，默认今天
        
        Returns:
            盒子名称列表
        """
        all_blocks = self.load_all_blocks(cycle_start)
        boxes = set()
        
        for block in all_blocks:
            if block.box:
                boxes.add(block.box)
        
        return sorted(list(boxes))
