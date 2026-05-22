
#!/usr/bin/env python3
"""
Todo Ball Machine - 基础设施层
负责与外部系统交互：文件存储、Cron调度、日志管理、配置管理
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


BASE_PATH = Path(os.environ.get("ENTP_BASE_PATH", Path(__file__).parent))


class StorageManager:
    """数据存储管理器 - 负责所有文件读写操作"""
    
    def __init__(self, base_path: Path = None):
        self._base_path = base_path or BASE_PATH
    
    def read_json(self, relative_path: str, default: Any = None) -> Any:
        """读取JSON文件"""
        file_path = self._base_path / relative_path
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    
    def write_json(self, relative_path: str, data: Any, indent: int = 2):
        """写入JSON文件"""
        file_path = self._base_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
    
    def append_log(self, relative_path: str, entry: Dict[str, Any]):
        """追加日志条目"""
        logs = self.read_json(relative_path, [])
        entry['timestamp'] = datetime.now().isoformat()
        logs.append(entry)
        self.write_json(relative_path, logs)


class AuditLogger:
    """审计日志管理器"""
    
    def __init__(self, storage: StorageManager):
        self._storage = storage
        self._log_path = "audit_logs/audit.json"
    
    def log_action(self, action: str, operator: str, details: Dict[str, Any] = None):
        """记录操作日志"""
        log_entry = {
            'action': action,
            'operator': operator,
            'details': details or {}
        }
        self._storage.append_log(self._log_path, log_entry)


class CronManager:
    """Cron定时任务管理器"""
    
    def __init__(self, storage: StorageManager):
        self._storage = storage
        self._config_path = "scheduler_config.json"
    
    def get_current_crontab(self) -> str:
        """获取当前crontab内容"""
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""
    
    def set_crontab(self, content: str) -> bool:
        """设置crontab内容"""
        try:
            subprocess.run(['crontab', '-'], input=content.encode('utf-8'), check=True)
            return True
        except Exception:
            return False
    
    def add_job(self, schedule: str, command: str, comment: str = "") -> bool:
        """添加Cron任务"""
        current_crontab = self.get_current_crontab()
        job_line = f"{schedule} {command}"
        if comment:
            job_line += f" # {comment}"
        
        if job_line in current_crontab:
            return True
        
        new_crontab = current_crontab.rstrip('\n') + '\n' + job_line + '\n'
        return self.set_crontab(new_crontab)
    
    def remove_job(self, command: str) -> bool:
        """移除Cron任务"""
        current_crontab = self.get_current_crontab()
        lines = current_crontab.split('\n')
        new_lines = [line for line in lines if command not in line]
        return self.set_crontab('\n'.join(new_lines))
    
    def load_scheduler_config(self) -> Dict[str, Any]:
        """加载调度器配置"""
        return self._storage.read_json(self._config_path, {
            'enabled': True,
            'jobs': []
        })
    
    def save_scheduler_config(self, config: Dict[str, Any]):
        """保存调度器配置"""
        self._storage.write_json(self._config_path, config)


class HeartbeatManager:
    """Heartbeat心跳管理器"""
    
    def __init__(self, storage: StorageManager):
        self._storage = storage
        self._tasks_path = "heartbeat_tasks.json"
        self._status_path = "heartbeat_status.json"
    
    def load_tasks(self) -> List[Dict[str, Any]]:
        """加载Heartbeat任务列表"""
        return self._storage.read_json(self._tasks_path, [])
    
    def save_tasks(self, tasks: List[Dict[str, Any]]):
        """保存Heartbeat任务列表"""
        self._storage.write_json(self._tasks_path, tasks)
    
    def update_status(self, is_smooth: bool, last_run_at: datetime = None, last_error: str = None):
        """更新Heartbeat状态"""
        status = {
            'last_run_at': (last_run_at or datetime.now()).isoformat(),
            'is_smooth': is_smooth,
            'last_error': last_error
        }
        self._storage.write_json(self._status_path, status)
    
    def get_status(self) -> Dict[str, Any]:
        """获取Heartbeat状态"""
        return self._storage.read_json(self._status_path, {
            'last_run_at': None,
            'is_smooth': True,
            'last_error': None
        })


class ConfigManager:
    """配置管理器 - 管理系统级配置"""
    
    def __init__(self, storage: StorageManager):
        self._storage = storage
        self._config_path = "90blocks_config.json"
    
    def load_config(self) -> Dict[str, Any]:
        """加载系统配置"""
        return self._storage.read_json(self._config_path, self._get_default_config())
    
    def save_config(self, config: Dict[str, Any]):
        """保存系统配置"""
        self._storage.write_json(self._config_path, config)
    
    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "cycle_name": "默认30天周期",
            "cycle_start": "",
            "cycle_end": "",
            "duration_map": {
                "hard": 3.0,
                "medium": 2.5,
                "easy": 2.0
            },
            "boxes": {
                "博士工作": {"emoji": "📚", "quota": 21},
                "AI创业工作": {"emoji": "💼", "quota": 21},
                "健康运动": {"emoji": "🏃", "quota": 15},
                "治愈休息": {"emoji": "😴", "quota": 14},
                "空间探索": {"emoji": "🌌", "quota": 10}
            }
        }


# 全局基础设施实例
_storage = StorageManager()
audit_logger = AuditLogger(_storage)
cron_manager = CronManager(_storage)
heartbeat_manager = HeartbeatManager(_storage)
config_manager = ConfigManager(_storage)

