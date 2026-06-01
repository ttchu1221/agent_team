from __future__ import annotations

"""Career Agent - 职业发展助手 (数据库 + 搜索集成)"""

import uuid
import structlog
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.base import BaseAgent, AgentResult
from app.models.task import TaskDocument, TaskStatus, AgentType
from app.tools.search.search import SearchTool

logger = structlog.get_logger()

CAREER_SYSTEM_PROMPT = """你是一位资深的职业发展顾问，擅长：
1. JD（职位描述）分析 - 提取关键要求、匹配度评估
2. 简历优化 - 针对特定JD优化简历内容
3. 面试准备 - 生成常见问题和建议回答
4. 求职策略 - 提供求职建议和市场分析

请根据用户的需求，提供专业、详细的分析和建议。
输出使用Markdown格式，结构清晰。
"""


class CareerAgent(BaseAgent):
    """Career Agent - 职业发展相关任务"""

    name = "career"
    description = "职业发展助手：JD分析、简历优化、面试准备、职位搜索"
    preferred_task_type = "chat"

    def __init__(self, router=None, db: AsyncIOMotorDatabase | None = None):
        super().__init__(router=router)
        self.db = db
        self.search_tool = SearchTool()

    async def execute(self, task_input: dict, context: dict | None = None) -> AgentResult:
        """执行职业发展相关任务"""
        task_type = task_input.get("task_type", "general")
        content = task_input.get("content", "")

        if task_type == "jd_analysis":
            return await self._analyze_jd(content)
        elif task_type == "search_jobs":
            return await self._search_jobs(content, task_input.get("max_results", 5))
        elif task_type == "resume_optimize":
            resume = task_input.get("resume", "")
            jd = task_input.get("jd", content)
            return await self._optimize_resume(resume, jd)
        elif task_type == "interview_prep":
            return await self._prepare_interview(content)
        else:
            return await self._general_career_advice(content)

    async def _search_jobs(self, query: str, max_results: int = 5) -> AgentResult:
        """搜索职位信息（通过论文搜索获取行业趋势）"""
        try:
            search_result = await self.search_tool.execute(
                f"{query} job market career", max_results=max_results
            )

            if not search_result.success:
                return AgentResult(success=False, error=search_result.error)

            papers = search_result.data
            papers_text = "\n".join([
                f"- {p['title']} ({p.get('year', 'N/A')})"
                for p in papers
            ])

            messages = [
                {"role": "system", "content": CAREER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"""根据以下搜索结果，分析 "{query}" 相关的职业市场：

{papers_text}

请提供：
1. **行业趋势** - 该领域的发展趋势
2. **热门技能** - 当前市场需求的技能
3. **薪资参考** - 薪资范围估算
4. **求职建议** - 如何进入该领域""",
                },
            ]

            result = await self._chat(messages, temperature=0.5)

            # 保存到数据库
            if self.db:
                record_id = str(uuid.uuid4())
                task = TaskDocument(
                    task_id=record_id,
                    user_input=query,
                    agent_type=AgentType.CAREER,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    description=f"[职位搜索] {query}",
                )
                await self.db["tasks"].insert_one(task.model_dump())

            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _analyze_jd(self, jd_text: str) -> AgentResult:
        """分析职位描述"""
        messages = [
            {"role": "system", "content": CAREER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请分析以下职位描述，提供：
1. **核心要求**：必须具备的技能和经验
2. **加分项**：优先考虑的条件
3. **岗位职责**：主要工作内容总结
4. **薪资参考**：根据市场行情的薪资范围估计
5. **匹配建议**：求职者应该重点准备什么

职位描述：
{jd_text}""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.5)

            # 保存到数据库
            if self.db:
                record_id = str(uuid.uuid4())
                task = TaskDocument(
                    task_id=record_id,
                    user_input=jd_text[:100],
                    agent_type=AgentType.CAREER,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    description=f"[JD分析] {jd_text[:50]}...",
                )
                await self.db["tasks"].insert_one(task.model_dump())

            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _optimize_resume(self, resume: str, jd: str) -> AgentResult:
        """针对JD优化简历"""
        messages = [
            {"role": "system", "content": CAREER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请根据目标职位的JD，优化我的简历内容。

## 目标职位JD：
{jd}

## 我的简历：
{resume}

请提供：
1. **匹配度分析**：当前简历与JD的匹配程度
2. **关键词优化**：建议加入的关键词
3. **内容调整建议**：具体每段经历的优化方向
4. **优化后的简历版本**：给出优化后的简历内容""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.5)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _prepare_interview(self, job_info: str) -> AgentResult:
        """面试准备"""
        messages = [
            {"role": "system", "content": CAREER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请为以下职位准备面试材料：

{job_info}

请提供：
1. **高频面试问题**（10个）及建议回答思路
2. **技术面试重点**：可能考察的知识点
3. **行为面试问题**：STAR法则回答模板
4. **反问面试官的问题**：5个高质量反问""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.6)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _general_career_advice(self, query: str) -> AgentResult:
        """通用职业咨询"""
        messages = [
            {"role": "system", "content": CAREER_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        try:
            result = await self._chat(messages)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))
