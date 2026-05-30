from __future__ import annotations

"""Agent 工厂 - 创建和管理 Agent 实例"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.base import BaseAgent
from app.agents.chief.agent import ChiefAgent
from app.agents.career.agent import CareerAgent
from app.agents.research.agent import ResearchAgent
from app.agents.life.agent import LifeAgent
from app.core.llm_router import LLMRouter


class AgentFactory:
    """Agent 工厂 - 根据类型创建 Agent 实例，注入 LLMRouter"""

    _agent_map: dict[str, type[BaseAgent]] = {
        "chief": ChiefAgent,
        "career": CareerAgent,
        "research": ResearchAgent,
        "life": LifeAgent,
    }

    @classmethod
    def create(
        cls,
        agent_type: str,
        router: LLMRouter | None = None,
        db: AsyncIOMotorDatabase | None = None,
    ) -> BaseAgent:
        """创建 Agent 实例"""
        agent_class = cls._agent_map.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")

        if agent_type == "life":
            return LifeAgent(router=router, db=db)
        return agent_class(router=router)

    @classmethod
    def list_agents(cls) -> list[dict]:
        """列出所有可用的 Agent"""
        return [
            {"name": name, "description": agent_cls(router=None).description}
            for name, agent_cls in cls._agent_map.items()
            if name != "chief"
        ]
