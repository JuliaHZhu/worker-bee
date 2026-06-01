"""InfraToolSet — 平台基础设施工具集。

职责边界（与 Skill 严格区分）：
  - InfraToolSet 决定「环境允许用什么」（厨房有什么食材）
  - Skill 决定「对话应该用什么」（菜谱需要什么食材）
  - Registry 存放「有什么可用」（食材库目录）

用法：
  1. 启动时 detect_platform() → 知道当前跑在哪个平台上
  2. get_available_tools() → 该平台物理可用的工具列表
  3. 对话前 filter_tools(active_tools, infra_available) → 取交集

只支持飞书(Feishu)和Discord，别的平台不管。
"""
import os
from typing import Dict, List, Optional


class InfraToolSet:
    """平台基础设施工具集。不是给 LLM 看的，是给系统看的。"""

    # 平台定义：{平台名: {tools: [工具名列表], requires_env: [必需环境变量]}}
    _PLATFORMS: Dict[str, dict] = {
        "linux": {
            "description": "本地 Linux 运行 — 所有工具默认可用",
            "tools": [],  # 本地不限制，全部放行
            "requires_env": [],
        },
        "feishu": {
            "description": "飞书/Lark — 通过 webhook bot 发送消息",
            "tools": ["send_message"],
            "requires_env": ["FEISHU_WEBHOOK_URL"],
        },
        "discord": {
            "description": "Discord — 通过 webhook 发送消息",
            "tools": ["send_message"],
            "requires_env": ["DISCORD_WEBHOOK_URL"],
        },
    }

    def __init__(self):
        self._platform: Optional[str] = None
        self._available_cache: Optional[List[str]] = None

    def detect_platform(self) -> str:
        """根据环境变量检测当前运行平台。"""
        if self._platform:
            return self._platform

        # 优先级：App Bot > Webhook > Discord > linux
        if os.environ.get("FEISHU_APP_ID") and os.environ.get("FEISHU_APP_SECRET"):
            self._platform = "feishu"
        elif os.environ.get("FEISHU_WEBHOOK_URL"):
            self._platform = "feishu"
        elif os.environ.get("DISCORD_WEBHOOK_URL"):
            self._platform = "discord"
        else:
            self._platform = "linux"
        return self._platform

    @property
    def platform(self) -> str:
        return self.detect_platform()

    def get_available_tools(self) -> List[str]:
        """返回当前平台物理可用的工具列表。"""
        if self._available_cache is not None:
            return list(self._available_cache)

        plat = self.detect_platform()
        pinfo = self._PLATFORMS.get(plat, {})

        # 检查环境变量
        for env in pinfo.get("requires_env", []):
            if not os.environ.get(env):
                self._available_cache = []
                return []

        tools = list(pinfo.get("tools", []))
        self._available_cache = tools
        return tools

    def is_tool_available(self, tool_name: str) -> bool:
        """检查某个工具在当前平台是否物理可用。"""
        return tool_name in self.get_available_tools()

    def filter_tools(self, tool_names: List[str]) -> List[str]:
        """从给定工具列表中过滤出当前平台可用的。

        linux 平台：不过滤，全部放行（本地工具没有环境门槛）
        Feishu/Discord：只保留平台支持的工具
        """
        plat = self.detect_platform()
        if plat == "linux":
            return list(tool_names)

        available = set(self.get_available_tools())
        return [t for t in tool_names if t in available]

    def describe(self) -> str:
        """返回当前平台的描述，用于日志或调试。"""
        plat = self.detect_platform()
        pinfo = self._PLATFORMS.get(plat, {})
        available = self.get_available_tools()
        return (
            f"Platform: {plat}\n"
            f"  {pinfo.get('description', '')}\n"
            f"  Available infra tools: {', '.join(available) if available else '(none)'}"
        )

    def invalidate(self) -> None:
        """清空缓存，用于环境变量变化后重新检测。"""
        self._platform = None
        self._available_cache = None


# 模块级单例
infra = InfraToolSet()
