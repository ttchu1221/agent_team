from __future__ import annotations

"""Chief Agent - 任务调度中心 (支持数据库)"""

import json
import uuid
import structlog

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.base import BaseAgent, AgentResult
from app.models.task import TaskPlan, SubTaskPlan

logger = structlog.get_logger()

CHIEF_AGENT_SYSTEM_PROMPT = """你是一个任务调度专家。你的职责是理解用户指令，并将其分解为可执行的任务计划。

## 工作流程：
1. 分析用户指令，识别核心意图
2. 评估任务复杂度，决定是否拆解
3. 选择合适的专业Agent执行子任务
4. 生成结构化的任务计划

## 可用Agent：
- career: 职业发展相关 (求职、简历、面试、JD分析)
- research: 学术研究相关 (论文、科研日报、文献检索、ArXiv搜索)
- life: 生活管理相关 (文件、邮件、日程、Todo)
- study: 学习规划相关 (学习目标、路径规划、资源推荐、进度跟踪)
- finance: 财务管理相关 (消费记录、支出分析、预算管理、订阅管理)
- travel: 旅行规划相关 (行程规划、住宿推荐、交通方案、预算估算)
- health: 健康管理相关 (健康记录、趋势分析、目标追踪、健身计划)

## 输出格式（严格JSON）：
{
  "intent": "用户的核心意图",
  "complexity": "简单/中等/复杂",
  "tasks": [
    {
      "id": "task_<uuid>",
      "agent": "agent_name",
      "description": "任务描述",
      "inputs": {"key": "value"},
      "dependencies": []
    }
  ],
  "execution_order": "sequential/parallel"
}

## 注意事项：
- 优先使用最专业Agent处理特定任务
- 避免过度拆解，保持任务粒度适中
- 考虑任务间的依赖关系
- 如果是简单对话（打招呼、闲聊），返回空tasks列表，intent设为"chat"
- 对于通用问题，可以直接回答，不需要分配给Agent
- 学术搜索相关任务使用research agent
"""


class ChiefAgent(BaseAgent):
    """Chief Agent - 理解意图、拆解任务、调度Agent"""

    name = "chief"
    description = "任务调度中心，负责意图理解和任务分发"
    preferred_task_type = "reasoning"

    async def execute(self, task_input: dict, context: dict | None = None) -> AgentResult:
        """解析用户指令并生成任务计划"""
        user_message = task_input.get("message", "")
        conversation_history = task_input.get("history", [])

        messages = [
            {"role": "system", "content": CHIEF_AGENT_SYSTEM_PROMPT},
        ]

        # 加入对话历史
        for msg in conversation_history[-6:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        messages.append({"role": "user", "content": user_message})

        try:
            result = await self._structured_chat(messages)

            # 为没有 ID 的任务生成 UUID
            for task in result.get("tasks", []):
                if not task.get("id"):
                    task["id"] = f"task_{uuid.uuid4().hex[:8]}"

            plan = TaskPlan(
                intent=result.get("intent", "unknown"),
                complexity=result.get("complexity", "简单"),
                tasks=[
                    SubTaskPlan(
                        id=t["id"],
                        agent=t["agent"],
                        description=t["description"],
                        inputs=t.get("inputs", {}),
                        dependencies=t.get("dependencies", []),
                    )
                    for t in result.get("tasks", [])
                ],
                execution_order=result.get("execution_order", "sequential"),
            )

            logger.info(
                "chief_agent_planned",
                intent=plan.intent,
                complexity=plan.complexity,
                task_count=len(plan.tasks),
            )

            return AgentResult(
                success=True,
                data=plan.model_dump(),
                metadata={"intent": plan.intent, "complexity": plan.complexity},
            )

        except Exception as e:
            logger.error("chief_agent_error", error=str(e))
            return AgentResult(success=False, error=str(e))
