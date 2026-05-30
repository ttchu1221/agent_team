from __future__ import annotations

"""Agent 基类 - 通过 LLMRouter 调用模型"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.llm_router import LLMRouter

logger = structlog.get_logger()


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)


class BaseAgent(ABC):
    """Agent 基类 - 所有专业 Agent 继承此类"""

    name: str = "base"
    description: str = ""
    # 子类可覆盖，指定该 Agent 偏好的任务类型（用于路由）
    preferred_task_type: str | None = None

    def __init__(self, router: LLMRouter | None = None):
        self.router = router

    @abstractmethod
    async def execute(self, task_input: dict, context: dict | None = None) -> AgentResult:
        """执行任务，子类必须实现"""
        pass

    async def _chat(
        self,
        messages: list[dict],
        task_type: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        response_format: dict | None = None,
    ) -> str:
        """调用 LLM（通过路由器自动选择提供商）"""
        if not self.router:
            raise RuntimeError("LLMRouter 未初始化，请确保 router 已注入")

        return await self.router.chat(
            messages=messages,
            task_type=task_type or self.preferred_task_type,
            provider=provider,
            model=model,
            temperature=temperature,
            response_format=response_format,
        )

    async def _structured_chat(
        self, messages: list[dict], task_type: str | None = None
    ) -> dict:
        """调用 LLM 并返回结构化 JSON"""
        if not self.router:
            raise RuntimeError("LLMRouter 未初始化")

        return await self.router.chat_json(
            messages=messages,
            task_type=task_type or self.preferred_task_type,
            temperature=0.3,
        )
