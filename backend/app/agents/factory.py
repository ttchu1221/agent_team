from __future__ import annotations

"""Agent 工厂 - 创建和管理 Agent 实例 (数据库 + 搜索集成)"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.base import BaseAgent
from app.agents.chief.agent import ChiefAgent
from app.agents.career.agent import CareerAgent
from app.agents.research.agent import ResearchAgent
from app.agents.life.agent import LifeAgent
from app.agents.study.agent import StudyAgent
from app.agents.finance.agent import FinanceAgent
from app.agents.travel.agent import TravelAgent
from app.agents.health.agent import HealthAgent
from app.core.llm_router import LLMRouter


# 所有 Agent 都支持数据库注入（用于任务记录和数据持久化）
_ALL_AGENTS = {"chief", "career", "research", "life", "study", "finance", "travel", "health"}


class AgentFactory:
    """Agent 工厂 - 根据类型创建 Agent 实例，注入 LLMRouter 和数据库"""

    _agent_map: dict[str, type[BaseAgent]] = {
        "chief": ChiefAgent,
        "career": CareerAgent,
        "research": ResearchAgent,
        "life": LifeAgent,
        "study": StudyAgent,
        "finance": FinanceAgent,
        "travel": TravelAgent,
        "health": HealthAgent,
    }

    @classmethod
    def create(
        cls,
        agent_type: str,
        router: LLMRouter | None = None,
        db: AsyncIOMotorDatabase | None = None,
    ) -> BaseAgent:
        """创建 Agent 实例，注入数据库连接"""
        agent_class = cls._agent_map.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # 所有 agent 都支持数据库注入
        return agent_class(router=router, db=db)

    @classmethod
    def list_agents(cls) -> list[dict]:
        """列出所有可用的 Agent"""
        return [
            {"name": name, "description": agent_cls(router=None).description}
            for name, agent_cls in cls._agent_map.items()
            if name != "chief"
        ]
