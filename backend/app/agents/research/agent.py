from __future__ import annotations

"""Research Agent - 学术研究助手"""

import structlog
from datetime import datetime

from app.agents.base import BaseAgent, AgentResult

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
    description = "学术研究助手：论文摘要、科研日报、文献分析"
    preferred_task_type = "reasoning"

    async def execute(self, task_input: dict, context: dict | None = None) -> AgentResult:
        """执行学术研究相关任务"""
        task_type = task_input.get("task_type", "general")
        content = task_input.get("content", "")

        if task_type == "paper_summary":
            return await self._summarize_paper(content)
        elif task_type == "research_daily":
            topic = task_input.get("topic", content)
            return await self._generate_research_daily(topic)
        elif task_type == "literature_review":
            return await self._literature_review(content)
        elif task_type == "idea_generation":
            return await self._generate_ideas(content)
        else:
            return await self._general_research(content)

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
        """生成科研日报"""
        today = datetime.now().strftime("%Y-%m-%d")
        messages = [
            {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""请围绕以下研究主题，生成一份科研日报（日期：{today}）：

**研究主题**: {topic}

请按以下格式输出：
# 🔬 科研日报 - {today}

## 📌 今日焦点
（今天最值得关注的研究动态）

## 📚 推荐阅读
（推荐3-5篇相关论文/文章，包含简要说明）

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
            return AgentResult(success=True, data=result)
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
