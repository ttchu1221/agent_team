from __future__ import annotations

"""工具基类 - 统一工具接口"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import structlog

logger = structlog.get_logger()


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)


class BaseTool(ABC):
    """工具基类 - 所有工具继承此类"""

    name: str = "base_tool"
    description: str = ""

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """统一执行接口"""
        pass

    def to_function_schema(self) -> dict:
        """返回工具的函数描述（用于 LLM function calling）"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._get_parameters_schema(),
        }

    @abstractmethod
    def _get_parameters_schema(self) -> dict:
        """返回参数的 JSON Schema"""
        pass


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """注册工具"""
        self._tools[tool.name] = tool
        logger.info("tool_registered", tool_name=tool.name)

    def get(self, name: str) -> BaseTool | None:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """列出所有已注册的工具"""
        return [tool.to_function_schema() for tool in self._tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """执行指定工具"""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found",
            )

        try:
            logger.info("tool_executing", tool_name=tool_name)
            result = await tool.execute(**kwargs)
            logger.info(
                "tool_executed",
                tool_name=tool_name,
                success=result.success,
            )
            return result
        except Exception as e:
            logger.error("tool_error", tool_name=tool_name, error=str(e))
            return ToolResult(success=False, error=str(e))


# 全局工具注册中心
tool_registry = ToolRegistry()
