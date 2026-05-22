
#!/usr/bin/env python3
"""
Todo Ball Machine - 应用层（Use Case Layer）
负责具体业务用例实现，是命令背后的真正执行者
"""

from datetime import date
import random

from todo_models import (
    CycleConfig,
    BlockType, Session, DataValidator
)
from todo_managers import QuotaManager, BallPoolManager, BlockManager, BASE_PATH
from todo_infrastructure import (
    audit_logger, config_manager, _storage
)


class UseCaseBase:
    """用例基类"""
    
    def __init__(self, quota_manager, ball_pool_manager, 
                 block_manager, cycle_config):
        self.quota_manager = quota_manager
        self.ball_pool_manager = ball_pool_manager
        self.block_manager = block_manager
        self.cycle_config = cycle_config


class StatusUseCase(UseCaseBase):
    """查看系统状态用例"""
    
    def execute(self):
        """执行查看状态用例"""
        status = {
            'boxes': {},
            'today': [],
            'cycle_progress': 0,
            'cycle_info': {
                'name': self.cycle_config.name,
                'start_date': self.cycle_config.start_date.isoformat(),
                'end_date': self.cycle_config.end_date.isoformat()
            }
        }
        
        # 获取配额状态
        all_blocks = self.block_manager.load_all_blocks(self.cycle_config.start_date)
        for box_name in self.quota_manager.get_valid_boxes():
            total = self.quota_manager.get_box_total(box_name)
            used = self.quota_manager.get_box_used_count(box_name, all_blocks)
            remaining = self.quota_manager.get_box_remaining(box_name, all_blocks)
            box_config = next((b for b in self.cycle_config.boxes if b.name == box_name), None)
            
            status['boxes'][box_name] = {
                'total': total,
                'used': used,
                'remaining': remaining,
                'emoji': box_config.emoji if box_config else ''
            }
        
        # 获取今日Blocks
        today_blocks = self.block_manager.load_blocks(date.today())
        status['today'] = [block.to_dict() for block in today_blocks]
        
        # 计算周期进度
        if self.cycle_config.start_date and self.cycle_config.end_date:
            total_days = (self.cycle_config.end_date - self.cycle_config.start_date).days + 1
            elapsed_days = (date.today() - self.cycle_config.start_date).days + 1
            status['cycle_progress'] = min(100, max(0, int((elapsed_days / total_days) * 100)))
        
        return status


class DrawSessionUseCase(UseCaseBase):
    """抽取某场次用例"""
    
    def execute(self, session_name, box_name=None):
        """执行抽取场次用例"""
        session = Session.from_string(session_name)
        today = date.today()
        
        # 检查是否已抽取
        existing_blocks = self.block_manager.load_blocks(today)
        existing_block = self.block_manager.find_block_by_session(existing_blocks, session)
        
        if existing_block:
            return {
                'success': False,
                'message': f"{session.display_name}已抽取过了",
                'block': existing_block.to_dict()
            }
        
        # 选择可用盒子
        all_blocks = self.block_manager.load_all_blocks(self.cycle_config.start_date)
        if box_name:
            DataValidator.validate_box_name(box_name, self.quota_manager.get_valid_boxes())
            available_boxes = [box_name]
        else:
            available_boxes = [
                b for b in self.quota_manager.get_valid_boxes()
                if self.quota_manager.get_box_remaining(b, all_blocks) > 0
            ]
        
        if not available_boxes:
            return {
                'success': False,
                'message': "所有盒子配额已用完！"
            }
        
        # 抽取球
        selected_box = random.choice(available_boxes)
        ball = self.ball_pool_manager.draw_ball(selected_box)
        
        # 创建Block
        duration = self.quota_manager.get_duration(ball.difficulty)
        block = self.block_manager.create_block(
            block_type=BlockType.NORMAL,
            box=selected_box,
            content=ball.content,
            difficulty=ball.difficulty,
            duration=duration,
            session=session,
            ball_id=ball.id
        )
        
        # 保存
        all_today_blocks = existing_blocks + [block]
        self.block_manager.save_blocks(all_today_blocks, today)
        
        # 记录审计日志
        audit_logger.log_action(
            action='draw_session',
            operator='cli',
            details={
                'session': session_name,
                'box': selected_box,
                'ball_id': ball.id
            }
        )
        
        return {
            'success': True,
            'message': f"成功抽取{session.display_name}",
            'block': block.to_dict()
        }


class QuickDrawUseCase(UseCaseBase):
    """快速抽取（三场全自动）用例"""
    
    def execute(self):
        """执行快速抽取用例"""
        today = date.today()
        existing_blocks = self.block_manager.load_blocks(today)
        
        # 检查已抽取的场次
        drawn_sessions = set()
        normal_blocks = [b for b in existing_blocks if b.type == BlockType.NORMAL]
        for block in normal_blocks:
            if block.session:
                drawn_sessions.add(block.session)
        
        # 需要抽取的场次（仅标准三场，不含加班场）
        sessions_to_draw = [s for s in Session.get_standard_sessions() if s not in drawn_sessions]
        
        if not sessions_to_draw:
            return {
                'success': True,
                'message': "今日三场都已抽取完成",
                'blocks': [b.to_dict() for b in normal_blocks]
            }
        
        # 抽取剩余场次
        all_blocks = self.block_manager.load_all_blocks(self.cycle_config.start_date)
        used_boxes = [b.box for b in normal_blocks]
        new_blocks = []
        
        for session in sessions_to_draw:
            # 优先选择未使用过的盒子
            available_boxes = [
                b for b in self.quota_manager.get_valid_boxes()
                if b not in used_boxes 
                and self.quota_manager.get_box_remaining(b, all_blocks) > 0
            ]
            
            if not available_boxes:
                # 如果没有未使用的盒子，选择所有还有配额的盒子
                available_boxes = [
                    b for b in self.quota_manager.get_valid_boxes()
                    if self.quota_manager.get_box_remaining(b, all_blocks) > 0
                ]
            
            if not available_boxes:
                continue
            
            selected_box = random.choice(available_boxes)
            ball = self.ball_pool_manager.draw_ball(selected_box)
            duration = self.quota_manager.get_duration(ball.difficulty)
            
            block = self.block_manager.create_block(
                block_type=BlockType.NORMAL,
                box=selected_box,
                content=ball.content,
                difficulty=ball.difficulty,
                duration=duration,
                session=session,
                ball_id=ball.id
            )
            
            new_blocks.append(block)
            used_boxes.append(selected_box)
        
        # 保存所有Blocks
        all_today_blocks = existing_blocks + new_blocks
        self.block_manager.save_blocks(all_today_blocks, today)
        
        # 记录审计日志
        audit_logger.log_action(
            action='quick_draw',
            operator='cli',
            details={'sessions_drawn': [s.value for s in sessions_to_draw]}
        )
        
        return {
            'success': True,
            'message': f"成功抽取{len(new_blocks)}场",
            'blocks': [b.to_dict() for b in normal_blocks + new_blocks]
        }


class QueryBlocksByBoxUseCase(UseCaseBase):
    """按盒子查询Blocks用例"""
    
    def execute(self, box_name, include_all_types=False):
        """
        执行按盒子查询用例
        
        Args:
            box_name: 盒子名称
            include_all_types: 是否包含所有类型
        
        Returns:
            查询结果字典
        """
        results = self.block_manager.query_blocks_by_box(
            box_name=box_name,
            cycle_start=self.cycle_config.start_date,
            include_all_types=include_all_types,
            sort_by_date=True
        )
        
        if not results:
            return {
                'success': False,
                'message': f"未找到盒子 '{box_name}' 的相关记录",
                'results': []
            }
        
        return {
            'success': True,
            'message': f"找到 {len(results)} 条记录",
            'results': [result.to_dict() for result in results]
        }


class ListUsedBoxesUseCase(UseCaseBase):
    """列出所有使用过的盒子用例"""
    
    def execute(self):
        """执行列出使用过的盒子用例"""
        boxes = self.block_manager.get_all_used_boxes(
            cycle_start=self.cycle_config.start_date
        )
        
        return {
            'success': True,
            'message': f"找到 {len(boxes)} 个使用过的盒子",
            'boxes': boxes
        }


class UseCaseFactory:
    """用例工厂 - 创建所有用例实例"""
    
    def __init__(self):
        # 加载数据
        self._config_data = config_manager.load_config()
        self._color_balls_data = _storage.read_json('color_balls.json', {})
        self._pool_state_data = _storage.read_json('pool_state.json', None)
        
        # 创建数据模型
        self._cycle_config = CycleConfig.from_dict(self._config_data)
        
        # 初始化管理器
        self._quota_manager = QuotaManager(self._cycle_config)
        self._ball_pool_manager = BallPoolManager(self._color_balls_data, self._pool_state_data)
        self._block_manager = BlockManager(BASE_PATH)
    
    def _create_use_case(self, use_case_class):
        """创建用例实例"""
        return use_case_class(
            self._quota_manager,
            self._ball_pool_manager,
            self._block_manager,
            self._cycle_config
        )
    
    @property
    def status(self):
        return self._create_use_case(StatusUseCase)
    
    @property
    def draw_session(self):
        return self._create_use_case(DrawSessionUseCase)
    
    @property
    def quick_draw(self):
        return self._create_use_case(QuickDrawUseCase)
    
    @property
    def query_blocks_by_box(self):
        return self._create_use_case(QueryBlocksByBoxUseCase)
    
    @property
    def list_used_boxes(self):
        return self._create_use_case(ListUsedBoxesUseCase)


# 全局用例工厂
use_case_factory = UseCaseFactory()

