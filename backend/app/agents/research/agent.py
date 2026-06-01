from __future__ import annotations

"""Research Agent - 学术研究助手 (数据库 + 搜索集成)"""

import uuid
import structlog
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agents.base import BaseAgent, AgentResult
from app.models.task import TaskDocument, TaskStatus, AgentType
from app.tools.search.search import SearchTool
from app.tools.obsidian.obsidian import ObsidianTool

logger = structlog.get_logger()

RESEARCH_SYSTEM_PROMPT = """你是一位学术研究助手，擅长：
1. 论文摘要生成 - 提炼论文核心贡献和方法
2. 科研日报 - 整理近期研究进展
3. 文献综述 - 梳理领域研究脉络
4. Idea生成 - 基于现有研究提出新方向

请以学术严谨的态度提供分析，输出使用Markdown格式。
"""


class ResearchAgent(BaseAgent):
    """Research Agent - 学术研究相关任务"""

    name = "research"
    description = "学术研究助手：论文搜索、论文摘要、科研日报、文献分析"
    preferred_task_type = "reasoning"

    def __init__(self, router=None, db: AsyncIOMotorDatabase | None = None):
        super().__init__(router=router, db=db)
        self.search_tool = SearchTool()
        self.obsidian_tool = ObsidianTool()

    async def execute(self, task_input: dict, context: dict | None = None) -> AgentResult:
        """执行学术研究相关任务"""
        task_type = task_input.get("task_type", "general")
        content = task_input.get("content", "")
        save_to_obsidian = task_input.get("save_to_obsidian", False)

        result = None
        if task_type == "paper_summary":
            result = await self._summarize_paper(content)
        elif task_type == "search_papers":
            result = await self._search_papers(content, task_input.get("max_results", 5))
        elif task_type == "research_daily":
            topic = task_input.get("topic", content)
            result = await self._generate_research_daily(topic)
        elif task_type == "literature_review":
            result = await self._literature_review(content)
        elif task_type == "idea_generation":
            result = await self._generate_ideas(content)
        else:
            result = await self._general_research(content)

        # 如果需要保存到 Obsidian
        if save_to_obsidian and result and result.success:
            obsidian_result = await self._save_to_obsidian(
                content=result.data if isinstance(result.data, str) else result.data.get("analysis", str(result.data)),
                title=task_input.get("obsidian_title", content[:50]),
                tags=task_input.get("obsidian_tags", ["research", "agent"]),
                source=task_input.get("obsidian_source", ""),
            )
            if obsidian_result.success:
                result.metadata = result.metadata or {}
                result.metadata["obsidian"] = obsidian_result.data

        return result

    async def _save_to_obsidian(
        self,
        content: str,
        title: str,
        tags: list[str] | None = None,
        source: str = "",
    ) -> ToolResult:
        """保存内容到 Obsidian Vault"""
        return await self.obsidian_tool.execute(
            title=title,
            content=content,
            tags=tags or ["research", "agent"],
            source=source,
        )

    async def _search_papers(self, query: str, max_results: int = 5) -> AgentResult:
        """搜索学术论文"""
        try:
            search_result = await self.search_tool.execute(query, max_results=max_results)

            if not search_result.success:
                return AgentResult(success=False, error=search_result.error)

            papers = search_result.data

            # 格式化搜索结果
            papers_text = "\n\n".join([
                f"**{i+1}. {p['title']}**\n"
                f"- 作者: {', '.join(p['authors'][:3])}\n"
                f"- 年份: {p.get('year', 'N/A')}\n"
                f"- 引用: {p.get('citation_count', 0)}\n"
                f"- DOI: {p.get('doi', p.get('arxiv_id', 'N/A'))}\n"
                f"- 摘要: {p.get('abstract', '')[:200]}..."
                for i, p in enumerate(papers)
            ])

            messages = [
                {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"""我搜索了 "{query}"，找到以下论文：

{papers_text}

请对这些论文进行简要分析：
1. **研究趋势** - 这些论文反映了什么研究趋势
2. **关键发现** - 主要研究成果
3. **研究空白** - 可能的研究空白
4. **推荐阅读** - 最值得阅读的论文及原因""",
                },
            ]

            analysis = await self._chat(messages, temperature=0.5)

            # 保存到数据库
            if self.db is not None:
                record_id = str(uuid.uuid4())
                task = TaskDocument(
                    task_id=record_id,
                    user_input=query,
                    agent_type=AgentType.RESEARCH,
                    status=TaskStatus.COMPLETED,
                    result=analysis,
                    description=f"[论文搜索] {query}",
                )
                await self.db["tasks"].insert_one(task.model_dump())

            return AgentResult(
                success=True,
                data={
                    "papers": papers,
                    "analysis": analysis,
                },
                metadata={"query": query, "paper_count": len(papers)},
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _summarize_paper(self, paper_content: str) -> AgentResult:
        """生成论文摘要"""
        messages = [
            {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请对以下论文内容进行结构化摘要：

{paper_content}

请按以下格式输出：
## 📄 论文摘要

### 基本信息
- **标题**: 
- **作者**: 
- **发表**: 

### 核心贡献
（列出2-3个主要贡献）

### 研究方法
（简述方法论）

### 关键发现
（列出主要实验结果）

### 局限性与未来方向

### 个人笔记
（对我的研究可能有什么启发？）""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.4)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _generate_research_daily(self, topic: str) -> AgentResult:
        """生成科研日报（集成搜索）"""
        today = datetime.now().strftime("%Y-%m-%d")

        # 先搜索最新论文
        search_result = await self.search_tool.execute(topic, max_results=5)
        papers_context = ""
        if search_result.success and search_result.data:
            papers_list = "\n".join([
                f"- {p['title']} ({p.get('year', 'N/A')}, 引用: {p.get('citation_count', 0)})"
                for p in search_result.data
            ])
            papers_context = f"\n\n最新相关论文:\n{papers_list}"

        messages = [
            {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请围绕以下研究主题，生成一份科研日报（日期：{today}）：

**研究主题**: {topic}
{papers_context}

请按以下格式输出：
# 🔬 科研日报 - {today}

## 📌 今日焦点
（基于搜索结果，最值得关注的研究动态）

## 📚 推荐阅读
（推荐3-5篇相关论文，包含简要说明）

## 💡 研究灵感
（基于当前进展的2-3个研究想法）

## ✅ 待办事项
（建议的研究推进任务）

## 📊 进展回顾
（对当前研究进度的评估）""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.6)
            return AgentResult(
                success=True,
                data=result,
                metadata={"topic": topic, "papers_found": len(search_result.data) if search_result.success else 0},
            )
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _literature_review(self, topic: str) -> AgentResult:
        """文献综述"""
        messages = [
            {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请对以下研究方向进行文献综述：

{topic}

请提供：
1. **研究背景**：该领域的起源和发展
2. **关键里程碑**：重要的突破性工作
3. **当前主流方法**：现有的技术路线对比
4. **开放问题**：尚未解决的挑战
5. **未来趋势**：可能的发展方向""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.5)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _generate_ideas(self, research_context: str) -> AgentResult:
        """生成研究想法"""
        messages = [
            {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""基于以下研究背景，请生成5个有潜力的研究方向/Idea：

{research_context}

对每个Idea请提供：
1. **方向名称**
2. **核心思路**（2-3句话）
3. **可行性评估**（高/中/低）
4. **预期影响**
5. **所需资源**""",
            },
        ]

        try:
            result = await self._chat(messages, temperature=0.8)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))

    async def _general_research(self, query: str) -> AgentResult:
        """通用研究咨询"""
        messages = [
            {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        try:
            result = await self._chat(messages)
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))
