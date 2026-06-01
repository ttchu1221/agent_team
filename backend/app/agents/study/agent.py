from __future__ import annotations

"""Study Agent - 学习规划助手 (数据库 + 搜索集成)"""

import uuid
import structlog
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.base import BaseAgent, AgentResult
from app.models.task import TaskDocument, TaskStatus, AgentType
from app.tools.search.search import SearchTool

logger = structlog.get_logger()

STUDY_SYSTEM_PROMPT = """你是一位专业的学习规划教练，擅长：
1. 学习目标拆解 - 将大目标分解为可执行的小步骤
2. 学习路径规划 - 设计科学的学习路径图
3. 学习资源推荐 - 推荐高质量的学习资料
4. 进度跟踪与复盘 - 帮助用户坚持学习并巩固知识

你的特点：
- 善于根据用户水平定制个性化学习计划
- 注重实践，强调动手练习
- 使用间隔重复等科学学习方法
- 输出结构清晰、可执行的学习方案

请以Markdown格式输出，包含清晰的标题和列表。
"""


class StudyAgent(BaseAgent):
    """Study Agent - 学习规划相关任务"""

    name = "study"
    description = "学习规划助手：目标拆解、路径规划、资源推荐、进度跟踪、学习资料搜索"
    preferred_task_type = "chat"

    def __init__(self, router=None, db: AsyncIOMotorDatabase | None = None):
        super().__init__(router=router, db=db)
        self.search_tool = SearchTool()

    async def execute(self, task_input: dict, context: dict | None = None) -> AgentResult:
        """执行学习规划相关任务"""
        task_type = task_input.get("task_type", "general")
        content = task_input.get("content", "")

        if task_type == "create_plan":
            return await self._create_learning_plan(
                content,
                task_input.get("level", "beginner"),
                task_input.get("hours_per_week", 10),
            )
        elif task_type == "decompose_goal":
            return await self._decompose_goal(content)
        elif task_type == "search_resources":
            return await self._search_resources(content, task_input.get("max_results", 5))
        elif task_type == "recommend_resources":
            return await self._recommend_resources(content)
        elif task_type == "review":
            return await self._generate_review(content)
        else:
            return await self._general_study(content)

    async def _search_resources(self, topic: str, max_results: int = 5) -> AgentResult:
        """搜索学习资源"""
        try:
            search_result = await self.search_tool.execute(
                f"{topic} tutorial learning", max_results=max_results
            )

            if not search_result.success:
                return AgentResult(success=False, error=search_result.error)

            papers = search_result.data
            papers_text = "\n".join([
                f"- {p['title']} ({p.get('year', 'N/A')}) - {', '.join(p['authors'][:2])}"
                for p in papers
            ])

            messages = [
                {"role": "system", "content": STUDY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"""根据搜索结果，为 "{topic}" 推荐学习资源：

{papers_text}

请分析这些资源并提供：
1. **推荐学习路径** - 建议的学习顺序
2. **重点资源** - 最值得学习的资源
3. **学习建议** - 如何高效学习""",
                },
            ]

            result = await self._chat(messages, temperature=0.5)

            # 保存到数据库
            if self.db is not None:
                record_id = str(uuid.uuid4())
                task = TaskDocument(
                    task_id=record_id,
                    user_input=topic,
                    agent_type=AgentType.STUDY,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    description=f"[资源搜索] {topic}",
                )
                await self.db["tasks"].insert_one(task.model_dump())

            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _create_learning_plan(
        self, goal: str, level: str = "beginner", hours_per_week: int = 10
    ) -> AgentResult:
        """创建完整学习计划"""
        messages = [
            {"role": "system", "content": STUDY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请为我制定一个学习计划：

**学习目标**: {goal}
**当前水平**: {level}
**每周可用时间**: {hours_per_week}小时

请提供：
1. **学习路径图** - 按阶段划分的学习路径
2. **知识模块拆解** - 每个模块的核心知识点
3. **时间规划** - 每周/每日学习安排
4. **推荐资源** - 每个模块推荐的学习资料
5. **里程碑** - 阶段性检验点
6. **学习建议** - 提高学习效率的建议""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.5)

            # 存入数据库
            if self.db is not None:
                plan_id = str(uuid.uuid4())
                task = TaskDocument(
                    task_id=plan_id,
                    user_input=goal,
                    agent_type=AgentType.STUDY,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    description=f"[学习计划] {goal}",
                )
                await self.db["tasks"].insert_one(task.model_dump())
                logger.info("learning_plan_created", plan_id=plan_id)

            return AgentResult(
                success=True,
                data=result,
                metadata={"action": "learning_plan_created", "goal": goal},
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _decompose_goal(self, goal: str) -> AgentResult:
        """拆解学习目标为子任务"""
        messages = [
            {"role": "system", "content": STUDY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请将以下学习目标拆解为可执行的子任务：

**目标**: {goal}

请使用思维树(ToT)方式拆解：
1. 列出所有需要掌握的知识点
2. 按依赖关系排序
3. 标注每个知识点的难度(高/中/低)
4. 估算每个知识点所需学时
5. 生成学习顺序建议

输出格式使用Markdown表格。""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.3)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _recommend_resources(self, topic: str) -> AgentResult:
        """推荐学习资源"""
        messages = [
            {"role": "system", "content": STUDY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请为以下主题推荐学习资源：

**主题**: {topic}

请推荐以下类型的资源：
1. **官方文档** - 权威参考资料
2. **视频教程** - YouTube/B站优质教程
3. **在线课程** - Coursera/Udemy/慕课等
4. **书籍** - 经典书籍推荐
5. **实战项目** - 动手练习建议
6. **社区** - 学习交流平台

每个资源请标注：难度、时长、是否免费。""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.5)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _generate_review(self, learning_content: str) -> AgentResult:
        """生成学习复盘报告"""
        messages = [
            {"role": "system", "content": STUDY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请帮我进行学习复盘：

**学习内容**:
{learning_content}

请提供：
1. **知识点回顾** - 核心知识点总结
2. **掌握度自评** - 关键问题检测清单
3. **薄弱环节** - 需要加强的部分
4. **巩固建议** - 间隔重复练习题
5. **下一步计划** - 后续学习建议""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.4)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _general_study(self, query: str) -> AgentResult:
        """通用学习咨询"""
        messages = [
            {"role": "system", "content": STUDY_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        try:
            result = await self._chat(messages)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))
