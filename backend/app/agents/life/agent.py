from __future__ import annotations

"""Life Agent - 生活管理助手 (MongoDB + 搜索集成)"""

import uuid
import structlog
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.base import BaseAgent, AgentResult
from app.models.task import TaskDocument, TaskStatus, AgentType
from app.tools.search.search import SearchTool

logger = structlog.get_logger()

LIFE_SYSTEM_PROMPT = """你是一位生活管理助手，擅长：
1. Todo管理 - 创建、更新、跟踪待办事项
2. 文件整理 - 提供文件整理建议和方案
3. 日程安排 - 帮助规划和优化日程
4. 信息归档 - 整理和归档各类信息

请以简洁、实用的方式提供建议，输出使用Markdown格式。
"""


class LifeAgent(BaseAgent):
    """Life Agent - 生活管理相关任务"""

    name = "life"
    description = "生活管理助手：Todo管理、文件整理、日程安排、信息搜索"
    preferred_task_type = "chat"

    def __init__(self, router=None, db: AsyncIOMotorDatabase | None = None):
        super().__init__(router=router)
        self.db = db
        self.search_tool = SearchTool()

    async def execute(self, task_input: dict, context: dict | None = None) -> AgentResult:
        """执行生活管理相关任务"""
        task_type = task_input.get("task_type", "general")
        content = task_input.get("content", "")

        if task_type == "todo_create":
            return await self._create_todo(content, task_input.get("priority", "medium"))
        elif task_type == "todo_list":
            return await self._list_todos()
        elif task_type == "search_info":
            return await self._search_info(content, task_input.get("max_results", 5))
        elif task_type == "file_organize":
            return await self._organize_files(content)
        elif task_type == "schedule":
            return await self._plan_schedule(content)
        else:
            return await self._general_life(content)

    async def _search_info(self, query: str, max_results: int = 5) -> AgentResult:
        """搜索生活相关信息"""
        try:
            search_result = await self.search_tool.execute(query, max_results=max_results)

            if not search_result.success:
                return AgentResult(success=False, error=search_result.error)

            papers = search_result.data
            papers_text = "\n".join([
                f"- {p['title']} ({p.get('year', 'N/A')})"
                for p in papers
            ])

            messages = [
                {"role": "system", "content": LIFE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"""根据搜索结果，回答关于 "{query}" 的问题：

{papers_text}

请提供实用的建议和信息。""",
                },
            ]

            result = await self._chat(messages, temperature=0.5)

            # 保存到数据库
            if self.db:
                record_id = str(uuid.uuid4())
                task = TaskDocument(
                    task_id=record_id,
                    user_input=query,
                    agent_type=AgentType.LIFE,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    description=f"[信息搜索] {query}",
                )
                await self.db["tasks"].insert_one(task.model_dump())

            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _create_todo(self, content: str, priority: str = "medium") -> AgentResult:
        """创建Todo项 - 存入 MongoDB"""
        if not self.db:
            return AgentResult(success=False, error="数据库未初始化")

        todo_id = str(uuid.uuid4())
        task = TaskDocument(
            task_id=todo_id,
            user_input=content,
            agent_type=AgentType.LIFE,
            status=TaskStatus.PENDING,
            description=f"[TODO][{priority}] {content}",
        )
        await self.db["tasks"].insert_one(task.model_dump())

        logger.info("todo_created", todo_id=todo_id, content=content[:50])

        return AgentResult(
            success=True,
            data={
                "todo_id": todo_id,
                "content": content,
                "priority": priority,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            metadata={"action": "todo_created"},
        )

    async def _list_todos(self) -> AgentResult:
        """列出所有Todo项"""
        if not self.db:
            return AgentResult(success=False, error="数据库未初始化")

        cursor = (
            self.db["tasks"]
            .find(
                {
                    "agent_type": AgentType.LIFE.value,
                    "description": {"$regex": "^\\[TODO\\]"},
                }
            )
            .sort("created_at", -1)
            .limit(50)
        )
        docs = await cursor.to_list(length=50)

        todo_list = [
            {
                "id": doc["task_id"],
                "content": doc.get("description", ""),
                "status": doc.get("status", "pending"),
                "created_at": doc["created_at"].isoformat() if doc.get("created_at") else None,
            }
            for doc in docs
        ]

        return AgentResult(
            success=True,
            data=todo_list,
            metadata={"count": len(todo_list)},
        )

    async def _organize_files(self, directory_info: str) -> AgentResult:
        """文件整理建议"""
        messages = [
            {"role": "system", "content": LIFE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请为以下目录/文件提供整理方案：

{directory_info}

请提供：
1. **当前状态分析**：文件分布情况
2. **分类建议**：推荐的目录结构
3. **整理步骤**：具体的操作步骤
4. **命名规范**：推荐的文件命名规则""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.4)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _plan_schedule(self, schedule_info: str) -> AgentResult:
        """日程规划"""
        messages = [
            {"role": "system", "content": LIFE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请帮我规划以下日程安排：

{schedule_info}

请提供：
1. **时间表**：按时间排列的任务列表
2. **优先级建议**：哪些任务应该优先处理
3. **时间估算**：每项任务的预计耗时
4. **优化建议**：如何提高效率""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.5)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _general_life(self, query: str) -> AgentResult:
        """通用生活咨询"""
        messages = [
            {"role": "system", "content": LIFE_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        try:
            result = await self._chat(messages)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))
